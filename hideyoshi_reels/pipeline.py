"""5工程を順番に実行するパイプライン本体。

① 企画生成 → ② 台本生成（＋ファクトチェック）→ ③ 画像生成 → ④ 音声・動画制作 → ⑤ 出力
"""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .audio import sfx as sfx_mod
from .audio.tts import MockTTS, create_tts
from .audio.wav import SAMPLE_RATE, normalize_audio, read_wav, write_wav
from .config import Settings
from .history import History
from .images.character import CharacterManager
from .images.compose import SceneComposer
from .images.providers import MockImageProvider, create_image_provider
from .llm import create_llm
from .models import SfxEvent, Timeline, TimelineScene
from .stages import caption as caption_stage
from .stages import factcheck as fc_stage
from .stages import planner, scriptwriter
from .utils import find_font, now_jst, require_ffmpeg, setup_logging, slugify, timestamp, write_json
from .video import renderer
from .video.subtitles import time_cues, to_srt

logger = logging.getLogger(__name__)

LEAD = 0.12  # 場面の頭の間（秒）
GAP = 0.30  # 場面の終わりの間（秒）
END_TAIL = 1.2  # 最後の余韻（秒）
MAX_TEMPO = 1.35


@dataclass
class RunResult:
    output_dir: Path
    video_path: Path
    title: str
    duration: float
    log: dict = field(default_factory=dict)


class Pipeline:
    def __init__(self, settings: Settings, topic: str | None = None, save_history: bool = True,
                 keep_work: bool = False, seed: int | None = None):
        self.s = settings
        self.topic = topic
        self.save_history = save_history
        self.keep_work = keep_work
        self.seed = seed if seed is not None else int(time.time())
        self.log: dict = {"steps": [], "fallbacks": [], "warnings": [], "providers": {}}

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

    # ---------- 実行 ----------
    def run(self) -> RunResult:
        require_ffmpeg()
        s = self.s
        font = find_font(s.font_path)
        run_started = time.time()
        history = History(s.history_path)

        temp_dir = s.output_dir / f"_running_{timestamp()}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(temp_dir / "run.log")
        logger.info("=== ちび秀吉リール生成を開始（モード: %s）===", s.mode)
        logger.info("フォント: %s", font)

        llm = create_llm(s)
        self.log["providers"]["llm"] = f"claude ({s.claude_model})" if llm else "mock"

        # ① 企画
        t = time.time()
        logger.info("【工程① 企画生成】")
        try:
            plan, mock_src = planner.generate_plan(llm, history, s.data_dir, self.topic)
        except Exception as exc:  # noqa: BLE001
            self._fallback("企画生成", exc)
            llm = None
            plan, mock_src = planner.generate_plan(None, history, s.data_dir, self.topic)
        logger.info("企画: %s（%s）", plan.title, plan.category)
        self._step("① 企画生成", t)

        # ② 台本 + ファクトチェック
        t = time.time()
        logger.info("【工程② 台本生成】")
        try:
            script = scriptwriter.write_script(llm, plan, history, s, mock_src, seed=self.seed)
        except Exception as exc:  # noqa: BLE001
            self._fallback("台本生成", exc)
            if mock_src is None:
                mock_src = {}
            script = scriptwriter.write_script(None, plan, history, s, mock_src, seed=self.seed)
        report = fc_stage.fact_check(llm, plan, script, s.data_dir, s.factcheck_web_search)
        changes = fc_stage.apply_fact_check(script, report)
        if report.unverified:
            self.log["warnings"].append(f"未確認の事実情報が {len(report.unverified)} 件あります（review_checklist.md を確認）")
        self._step("② 台本生成・ファクトチェック", t)

        # ③ 画像
        t = time.time()
        logger.info("【工程③ 画像生成】")
        provider = create_image_provider(s)
        self.log["providers"]["image"] = provider.name
        character = CharacterManager(s.character_dir, provider)
        try:
            sprites = character.ensure_all()
        except Exception as exc:  # noqa: BLE001
            self._fallback("キャラクター画像生成", exc)
            provider = MockImageProvider()
            character = CharacterManager(s.character_dir, provider)
            sprites = character.ensure_all()
        if any("mock" in str(p.parent.name) for p in sprites.values()):
            logger.info("キャラクター: 仮のオリジナル素材を使用（assets/character/mock）")
        bg_spec = character.spec.get("background_prompt_suffix", "")
        composer = SceneComposer(s.width, s.height, font, s.account_handle, provider,
                                 s.resolved_background_mode() if not provider.is_mock else "procedural", bg_spec)
        self.log["providers"]["background"] = composer.background_mode
        images_dir = temp_dir / "images"
        scene_images = []
        for i, scene in enumerate(script.scenes):
            path = composer.compose_scene(scene.section, scene.image_prompt, sprites[scene.expression],
                                          scene.telop, images_dir / f"scene_{i + 1:02d}.png", seed=self.seed + i)
            scene_images.append(path)
        char_out = images_dir / "character"
        char_out.mkdir(parents=True, exist_ok=True)
        for expr, path in sprites.items():
            shutil.copy(path, char_out / f"{expr}.png")
        self._step("③ 画像生成", t)

        # ④ 音声・動画
        t = time.time()
        logger.info("【工程④ 音声・動画制作】")
        work = temp_dir / "_work"
        work.mkdir(exist_ok=True)
        tts = create_tts(s)
        self.log["providers"]["tts"] = tts.name
        speech = self._synthesize(tts, script, work)
        timeline, subtitle_map, all_cues = self._build_timeline(script, speech, scene_images, composer, work)
        mix_path = self._mix_audio(timeline, speech, work)
        video_path = temp_dir / "reel.mp4"
        renderer.render_video(timeline, subtitle_map, mix_path, video_path, work)
        self._step("④ 音声・動画制作", t)

        # ⑤ 出力
        t = time.time()
        logger.info("【工程⑤ 出力】")
        credits = [tts.credit] if tts.credit else []
        try:
            caption_text, hashtags, extended = caption_stage.make_caption(llm, plan, script, credits)
        except Exception as exc:  # noqa: BLE001
            self._fallback("キャプション生成", exc)
            caption_text, hashtags, extended = caption_stage.make_caption(None, plan, script, credits)

        write_json(temp_dir / "plan.json", plan)
        write_json(temp_dir / "script.json", {
            **script.model_dump(mode="json"),
            "image_instructions": [{"scene": i + 1, "expression": sc.expression, "image_prompt": sc.image_prompt,
                                    "telop": sc.telop} for i, sc in enumerate(script.scenes)],
        })
        write_json(temp_dir / "timeline.json", timeline)
        write_json(temp_dir / "factcheck.json", report)
        (temp_dir / "review_checklist.md").write_text(fc_stage.review_checklist_markdown(report, changes), encoding="utf-8")
        (temp_dir / "subtitles.srt").write_text(to_srt(all_cues), encoding="utf-8")
        (temp_dir / "narration.txt").write_text(self._narration_text(script, timeline), encoding="utf-8")
        (temp_dir / "caption.txt").write_text(caption_text, encoding="utf-8")
        (temp_dir / "hashtags.txt").write_text(" ".join(hashtags) + "\n", encoding="utf-8")
        (temp_dir / "hashtags_extended.txt").write_text(" ".join(extended) + "\n", encoding="utf-8")
        (temp_dir / "post.txt").write_text(f"{caption_text}\n\n{' '.join(hashtags)}\n", encoding="utf-8")

        # 最終フォルダ名に変更
        final_dir = s.output_dir / f"{timestamp()}_{slugify(plan.title)}"
        if not self.keep_work:
            shutil.rmtree(work, ignore_errors=True)
        self._step("⑤ 出力", t)

        self.log.update({
            "plan_id": plan.plan_id, "title": plan.title, "mode": s.mode,
            "created_at": now_jst().isoformat(timespec="seconds"),
            "duration_seconds": round(timeline.duration, 2),
            "total_seconds": round(time.time() - run_started, 1),
            "usage": {
                "claude_tokens": getattr(llm, "usage", None),
                "images_generated": getattr(provider, "images_generated", 0),
                "new_character_sprites": character.generated,
            },
            "estimated_cost_jpy": self._estimate_cost(llm, provider, tts, script),
        })
        write_json(temp_dir / "production_log.json", self.log)
        logging.getLogger("hideyoshi_reels").handlers[-1].close()
        temp_dir.rename(final_dir)
        setup_logging(None)

        if self.save_history:
            history.add({
                "id": plan.plan_id, "created_at": plan.created_at, "title": plan.title,
                "category": plan.category, "keywords": plan.keywords, "hook": plan.hook,
                "opening_phrase": script.opening_phrase, "closing_phrase": script.closing_phrase,
                "duration": round(timeline.duration, 2), "output_dir": final_dir.name,
                "providers": self.log["providers"],
            })
            history.save()

        logger.info("=== 完成: %s（%.1f 秒）===", final_dir / "reel.mp4", timeline.duration)
        for w in self.log["warnings"] + self.log["fallbacks"]:
            logger.warning("注意: %s", w)
        return RunResult(final_dir, final_dir / "reel.mp4", plan.title, timeline.duration, self.log)

    # ---------- 音声 ----------
    def _synthesize(self, tts, script, work: Path) -> list[Path]:
        raw_paths = []
        for i, scene in enumerate(script.scenes):
            raw = work / f"tts_raw_{i:02d}.wav"
            try:
                tts.synthesize(scene.narration, raw)
            except Exception as exc:  # noqa: BLE001
                self._fallback(f"音声合成（場面{i + 1}）", exc)
                MockTTS().synthesize(scene.narration, raw)
            raw_paths.append(raw)
        normalized = [normalize_audio(p, work / f"tts_{i:02d}.wav") for i, p in enumerate(raw_paths)]
        total = sum(len(read_wav(p)) / SAMPLE_RATE for p in normalized)
        overhead = len(normalized) * (LEAD + GAP) + END_TAIL
        limit = self.s.max_seconds - 0.3
        if total + overhead > limit:
            tempo = min(MAX_TEMPO, total / max(1.0, limit - overhead))
            logger.info("ナレーションが長いため話速を %.2f 倍にして %.0f 秒以内に収めます", tempo, self.s.max_seconds)
            normalized = [normalize_audio(p, work / f"tts_{i:02d}.wav", tempo=tempo) for i, p in enumerate(raw_paths)]
            if tempo >= MAX_TEMPO:
                self.log["warnings"].append("台本が長すぎるため、規定秒数を超えている可能性があります")
        return normalized

    def _build_timeline(self, script, speech, scene_images, composer, work):
        fps = self.s.fps
        lengths = [len(read_wav(p)) / SAMPLE_RATE for p in speech]
        durations = [LEAD + d + GAP for d in lengths]
        durations[-1] += END_TAIL
        shortfall = self.s.min_seconds - sum(durations)
        if shortfall > 0:
            durations[-1] += shortfall
        durations = [round(d * fps) / fps for d in durations]  # フレーム単位に揃えてズレを防ぐ

        scenes, sfx_events, subtitle_map, all_cues = [], [], {}, []
        t = 0.0
        for i, (scene, dur, speech_len) in enumerate(zip(script.scenes, durations, lengths)):
            motion = "punch" if i == 0 else ("zoom_in" if i % 2 else "zoom_out")
            local_cues = time_cues(scene.subtitle, LEAD, LEAD + speech_len)
            overlays = []
            for j, cue in enumerate(local_cues):
                img = composer.subtitle_overlay(cue.text, work / f"sub_{i:02d}_{j:02d}.png")
                start = 0.0 if j == 0 else cue.start  # 最初の字幕は場面の頭から表示（ちらつき防止）
                end = dur if j == len(local_cues) - 1 else cue.end  # 最後の字幕は場面終わりまで表示
                overlays.append((img, start, end))
            subtitle_map[i] = overlays
            global_cues = [type(c)(start=round(t + c.start, 3), end=round(t + c.end, 3), text=c.text) for c in local_cues]
            all_cues.extend(global_cues)
            scenes.append(TimelineScene(
                index=i, section=scene.section, start=round(t, 3), end=round(t + dur, 3),
                expression=scene.expression, telop=scene.telop, narration=scene.narration,
                image=str(scene_images[i]), audio=str(speech[i]), motion=motion, cues=global_cues))
            if scene.sfx != "none":
                sfx_events.append(SfxEvent(at=round(t, 3), name=scene.sfx))
            elif i > 0:
                sfx_events.append(SfxEvent(at=round(t, 3), name="whoosh"))
            t += dur
        timeline = Timeline(width=self.s.width, height=self.s.height, fps=fps, duration=round(t, 3),
                            scenes=scenes, sfx=sfx_events)
        return timeline, subtitle_map, all_cues

    def _mix_audio(self, timeline: Timeline, speech: list[Path], work: Path) -> Path:
        n = int(timeline.duration * SAMPLE_RATE) + SAMPLE_RATE
        voice = np.zeros(n)
        for scene, path in zip(timeline.scenes, speech):
            data = read_wav(path)
            start = int((scene.start + LEAD) * SAMPLE_RATE)
            voice[start:start + len(data)] += data[: n - start]
        peak = np.max(np.abs(voice)) or 1.0
        mix = voice * (0.9 / peak)
        for ev in timeline.sfx:
            snd = sfx_mod.make_sfx(ev.name)
            if snd is None:
                continue
            start = int(ev.at * SAMPLE_RATE)
            mix[start:start + len(snd)] += 0.45 * snd[: n - start]
        if self.s.bgm_enabled:
            bgm = sfx_mod.make_bgm(timeline.duration, seed=self.seed)
            # ナレーション中は BGM を下げる（簡易ダッキング）
            envelope = np.convolve(np.abs(voice) > 0.02, np.ones(4410) / 4410, mode="same")
            duck = 1.0 - 0.6 * np.clip(envelope[: len(bgm)] * 3, 0, 1)
            mix[: len(bgm)] += 0.55 * bgm * duck
        mix = mix[: int(timeline.duration * SAMPLE_RATE)]
        mix *= 0.95 / max(np.max(np.abs(mix)), 1e-6)
        return write_wav(work / "mix.wav", mix)

    # ---------- 出力用 ----------
    @staticmethod
    def _narration_text(script, timeline: Timeline) -> str:
        labels = {"hook": "フック", "problem": "問題提起", "explanation": "解説", "conclusion": "結論"}
        lines = [f"# {script.title}", ""]
        for sc, tl in zip(script.scenes, timeline.scenes):
            lines.append(f"[{tl.start:05.2f}s - {tl.end:05.2f}s] {labels[sc.section]}（表情: {sc.expression} / 効果音: {sc.sfx}）")
            lines.append(f"  見出し: {sc.telop}")
            lines.append(f"  ナレーション: {sc.narration}")
            lines.append("")
        return "\n".join(lines)

    def _estimate_cost(self, llm, provider, tts, script) -> dict:
        """おおよその費用（円）。為替 1ドル=150円で計算した目安です。"""
        usd = 0.0
        if llm is not None:
            usd += llm.usage["input_tokens"] / 1e6 * 4 + llm.usage["output_tokens"] / 1e6 * 20
            if self.s.factcheck_web_search:
                usd += 8 * 0.01  # Web検索（最大8回 × $10/1000回）
        per_image = {"low": 0.016, "medium": 0.063, "high": 0.25}.get(self.s.image_quality, 0.063)
        usd += getattr(provider, "images_generated", 0) * per_image
        if tts.name == "openai":
            usd += len(script.full_narration) / 7 / 60 * 0.015
        return {"usd": round(usd, 3), "jpy": round(usd * 150), "note": "目安（1ドル=150円換算）"}

