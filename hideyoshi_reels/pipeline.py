"""投稿制作パイプライン本体。

Trend（分析・企画・原稿・事実確認）→ Factory（デザイン選択・静止画生成・リールのみ10秒MP4）
→ Monetization（収益化導線・キャプション）→ 出力（人間の承認待ち）
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .factory.fonts import Fonts
from .factory.render import contact_sheet, render_post
from .factory.templates import TEMPLATES, choose_design
from .factory.video import still_to_mp4
from .history import History
from .images.character import CharacterManager
from .images.providers import MockImageProvider, create_image_provider
from .llm import create_llm
from .models import FactCheckReport, Plan, PostContent, TrendReport
from .monetization import caption as caption_stage
from .monetization.planner import plan_monetization
from .trend import factcheck as fc_stage
from .trend.analyzer import analyze_trends
from .trend.planner import generate_plan
from .trend.writer import normalize, write_post
from .utils import now_jst, require_ffmpeg, setup_logging, slugify, timestamp, write_json

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    output_dir: Path
    title: str
    post_format: str
    design: str
    images: list[Path]
    video_path: Path | None
    log: dict = field(default_factory=dict)


@dataclass
class TrendResult:
    trend: TrendReport
    plan: Plan
    content: PostContent
    report: FactCheckReport
    changes: list[str]


class Pipeline:
    def __init__(self, settings: Settings, topic: str | None = None, save_history: bool = True):
        settings.validate()
        self.s = settings
        self.topic = topic
        self.save_history = save_history
        self.log: dict = {"steps": [], "fallbacks": [], "warnings": [], "providers": {}}
        self.llm = None

    # ---------- 共通 ----------
    def _step(self, name: str, started: float) -> None:
        elapsed = round(time.time() - started, 2)
        self.log["steps"].append({"step": name, "seconds": elapsed})
        logger.info("✔ %s 完了（%.1f 秒）", name, elapsed)

    def _fallback(self, stage: str, exc: Exception) -> None:
        if self.s.strict:
            raise exc
        msg = f"{stage}: 本番APIでエラーが発生したためモックで続行しました ({type(exc).__name__}: {exc})"
        logger.error(msg)
        self.log["fallbacks"].append(msg)

    # ---------- Trend ----------
    def run_trend(self, history: History) -> TrendResult:
        s = self.s
        t = time.time()
        logger.info("【Trend】トレンド分析・企画・原稿")
        trend = analyze_trends(self.llm, s.data_dir, s.trend_web_search)
        try:
            plan, mock_src = generate_plan(self.llm, history, s.data_dir, trend, s.post_format, self.topic)
            content = write_post(self.llm, plan, history, s.post_format, mock_src)
        except Exception as exc:  # noqa: BLE001
            self._fallback("企画・原稿作成", exc)
            self.llm = None
            plan, mock_src = generate_plan(None, history, s.data_dir, trend, s.post_format, self.topic)
            content = write_post(None, plan, history, s.post_format, mock_src)
        logger.info("企画: %s（%s）", plan.title, plan.category)
        report = fc_stage.fact_check(self.llm, plan, content, s.data_dir, s.factcheck_web_search)
        changes = fc_stage.apply_fact_check(content, report)
        normalize(content)
        if report.unverified:
            self.log["warnings"].append(f"未確認の事実情報が {len(report.unverified)} 件あります（review_checklist.md を確認）")
        self._step("Trend", t)
        return TrendResult(trend, plan, content, report, changes)

    def character_sprite(self, expression: str) -> tuple[Path, object, CharacterManager]:
        provider = create_image_provider(self.s)
        manager = CharacterManager(self.s.character_dir, provider)
        try:
            return manager.sprite_path(expression), provider, manager
        except Exception as exc:  # noqa: BLE001
            self._fallback("キャラクター画像生成", exc)
            provider = MockImageProvider()
            manager = CharacterManager(self.s.character_dir, provider)
            return manager.sprite_path(expression), provider, manager

    # ---------- 1投稿を制作 ----------
    def run(self) -> RunResult:
        s = self.s
        if s.post_format == "reel":
            require_ffmpeg()
        fonts = Fonts(s.font_path)
        started = time.time()
        history = History(s.history_path)
        temp_dir = s.output_dir / f"_running_{timestamp()}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(temp_dir / "run.log")
        logger.info("=== ちび秀吉 Instagram投稿の制作を開始（形式: %s / デザイン: %s / モード: %s）===",
                    s.post_format, s.design_style, s.mode)
        self.llm = create_llm(s)
        self.log["providers"]["llm"] = f"claude ({s.claude_model})" if self.llm else "mock"

        tr = self.run_trend(history)

        # Factory
        t = time.time()
        logger.info("【Factory】デザイン選択・画像生成")
        style, reason, scores = choose_design(tr.content, tr.plan, s.post_format, s.design_style)
        logger.info("デザイン: %s（%s）理由: %s", style, TEMPLATES[style].name, reason)
        sprite, provider, manager = self.character_sprite(tr.content.expression)
        self.log["providers"]["character"] = provider.name
        slides = render_post(tr.content, style, s.post_format, sprite, fonts, s.account_handle,
                             s.carousel_max_slides)
        images: list[Path] = []
        if s.post_format == "carousel":
            (temp_dir / "carousel").mkdir()
            for i, slide in enumerate(slides, 1):
                path = temp_dir / "carousel" / f"slide_{i:02d}.png"
                slide.image.save(path)
                images.append(path)
        else:
            path = temp_dir / "post_image.png"
            slides[0].image.save(path)
            images.append(path)
        video = None
        if s.post_format == "reel":
            video = still_to_mp4(images[0], temp_dir / "reel.mp4", s.reel_seconds, s.fps)
            logger.info("リール動画: 静止画1枚 × %.0f秒（%dfps）", s.reel_seconds, s.fps)
        layout = {slide.name: slide.issues for slide in slides}
        n_issues = sum(len(v) for v in layout.values())
        if n_issues:
            self.log["warnings"].append(f"レイアウトの注意点が {n_issues} 件あります（layout_check.json を確認）")
        self._step("Factory", t)

        # Monetization
        t = time.time()
        logger.info("【Monetization】収益化導線・キャプション")
        try:
            monet = plan_monetization(self.llm, tr.plan, tr.content, s.note_url)
            caption_text, hashtags, extended = caption_stage.make_caption(
                self.llm, tr.plan, tr.content, monet, s.note_url, s.affiliate_enabled)
        except Exception as exc:  # noqa: BLE001
            self._fallback("収益化・キャプション", exc)
            monet = plan_monetization(None, tr.plan, tr.content, s.note_url)
            caption_text, hashtags, extended = caption_stage.make_caption(
                None, tr.plan, tr.content, monet, s.note_url, s.affiliate_enabled)
        self._step("Monetization", t)

        # 出力
        write_json(temp_dir / "trend_report.json", tr.trend)
        write_json(temp_dir / "plan.json", tr.plan)
        write_json(temp_dir / "post_content.json", tr.content)
        write_json(temp_dir / "design.json", {"style": style, "name": TEMPLATES[style].name, "reason": reason,
                                             "scores": scores, "format": s.post_format,
                                             "size": list(slides[0].image.size)})
        write_json(temp_dir / "layout_check.json", layout)
        write_json(temp_dir / "factcheck.json", tr.report)
        write_json(temp_dir / "monetization.json", monet)
        (temp_dir / "review_checklist.md").write_text(
            fc_stage.review_checklist_markdown(tr.report, tr.changes), encoding="utf-8")
        (temp_dir / "caption.txt").write_text(caption_text, encoding="utf-8")
        (temp_dir / "hashtags.txt").write_text(" ".join(hashtags) + "\n", encoding="utf-8")
        (temp_dir / "hashtags_extended.txt").write_text(" ".join(extended) + "\n", encoding="utf-8")
        (temp_dir / "post.txt").write_text(f"{caption_text}\n\n{' '.join(hashtags)}\n", encoding="utf-8")
        write_json(temp_dir / "approval.json", {
            "status": "pending",
            "note": "投稿前に人が内容を確認し、問題なければ status を approved にしてください（自動投稿は未実装）",
            "checklist": ["画像の文字に誤字・欠けがないか", "review_checklist.md の未確認情報", "キャプションの内容",
                          "公式アカウントと誤認されない表現か"],
        })
        self.log.update({
            "plan_id": tr.plan.plan_id, "title": tr.plan.title, "mode": s.mode, "format": s.post_format,
            "design": style, "created_at": now_jst().isoformat(timespec="seconds"),
            "total_seconds": round(time.time() - started, 1),
            "usage": {"claude_tokens": getattr(self.llm, "usage", None),
                      "images_generated": getattr(provider, "images_generated", 0),
                      "new_character_sprites": manager.generated},
            "estimated_cost_jpy": self._estimate_cost(provider),
        })
        write_json(temp_dir / "production_log.json", self.log)
        for h in list(logging.getLogger("hideyoshi_reels").handlers):
            if isinstance(h, logging.FileHandler):
                h.close()
        final_dir = s.output_dir / f"{timestamp()}_{s.post_format}_{style}_{slugify(tr.plan.title)}"
        temp_dir.rename(final_dir)
        setup_logging(None)

        if self.save_history:
            history.add({
                "id": tr.plan.plan_id, "created_at": tr.plan.created_at, "title": tr.plan.title,
                "category": tr.plan.category, "keywords": tr.plan.keywords, "hook": tr.plan.hook,
                "format": s.post_format, "design": style, "output_dir": final_dir.name,
                "providers": self.log["providers"],
            })
            history.save()

        logger.info("=== 完成: %s ===", final_dir)
        for w in self.log["warnings"] + self.log["fallbacks"]:
            logger.warning("注意: %s", w)
        rel = [final_dir / p.relative_to(temp_dir) for p in images]
        return RunResult(final_dir, tr.plan.title, s.post_format, style, rel,
                         final_dir / "reel.mp4" if video else None, self.log)

    # ---------- デザインプレビュー（A〜Dを同じテーマで試作） ----------
    def preview(self, formats: tuple[str, ...] = ("reel", "feed")) -> Path:
        s = self.s
        fonts = Fonts(s.font_path)
        out = s.output_dir / "previews" / f"{timestamp()}"
        out.mkdir(parents=True, exist_ok=True)
        setup_logging(out / "run.log")
        self.llm = create_llm(s)
        tr = self.run_trend(History(s.history_path))
        sprite, _, _ = self.character_sprite(tr.content.expression)
        auto, reason, scores = choose_design(tr.content, tr.plan, formats[0])
        report = {"title": tr.plan.title, "auto_selected": auto, "reason": reason, "scores": scores, "designs": {}}
        sheet_items = []
        for fmt in formats:
            for key, template in TEMPLATES.items():
                slides = render_post(tr.content, key, fmt, sprite, fonts, s.account_handle, s.carousel_max_slides)
                for i, slide in enumerate(slides):
                    name = f"{key}_{fmt}.png" if len(slides) == 1 else f"{key}_{fmt}_{i + 1:02d}.png"
                    slide.image.save(out / name)
                report["designs"].setdefault(key, {"name": template.name})[fmt] = {
                    "issues": [i for sl in slides for i in sl.issues]}
                sheet_items.append((f"{key} {fmt}" + (" ★自動選択" if key == auto and fmt == formats[0] else ""),
                                    slides[0].image))
        for fmt in formats:
            contact_sheet([x for x in sheet_items if f" {fmt}" in x[0]], fonts).save(out / f"compare_{fmt}.png")
        write_json(out / "post_content.json", tr.content)
        write_json(out / "preview_report.json", report)
        setup_logging(None)
        logger.info("プレビューを保存しました: %s", out)
        return out

    def _estimate_cost(self, provider) -> dict:
        """おおよその費用（円）。為替 1ドル=150円で計算した目安です。"""
        usd = 0.0
        if self.llm is not None:
            usd += self.llm.usage["input_tokens"] / 1e6 * 4 + self.llm.usage["output_tokens"] / 1e6 * 20
            usd += 0.01 * ((6 if self.s.trend_web_search else 0) + (8 if self.s.factcheck_web_search else 0))
        per_image = {"low": 0.016, "medium": 0.063, "high": 0.25}.get(self.s.image_quality, 0.063)
        usd += getattr(provider, "images_generated", 0) * per_image
        return {"usd": round(usd, 3), "jpy": round(usd * 150), "note": "目安（1ドル=150円換算）"}

