"""Trend: 伸びている画像リール・フィード投稿の分析。

情報源:
  1. data/trend_signals.yaml … 運営者が記録した「伸びた投稿」のメモ（他アカウントの観察・自分の実績）
  2. Claude + Web検索 … 公開記事などから最近の傾向を抽出（ANTHROPIC_API_KEY 設定時）
  3. 将来: Instagram インサイトAPIで自分の投稿の保存数などを自動取得（publishers/ に拡張ポイントあり）

※ Instagram の他アカウントの数値を自動で収集（スクレイピング）することは利用規約上の問題があるため行いません。
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from ..models import TrendReport
from . import prompts

logger = logging.getLogger(__name__)


def load_signals(data_dir: Path) -> dict:
    path = data_dir / "trend_signals.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _signals_text(signals: dict) -> str:
    lines = []
    for post in signals.get("observed_posts") or []:
        metrics = ", ".join(f"{k}={v}" for k, v in (post.get("metrics") or {}).items())
        lines.append(f"- [{post.get('format', '?')}] {post.get('hook', '')} / 型: {post.get('pattern', '')} {metrics}")
    for note in signals.get("notes") or []:
        lines.append(f"- メモ: {note}")
    return "\n".join(lines) or "（記録なし）"


def analyze_trends(llm, data_dir: Path, use_web_search: bool = True) -> TrendReport:
    signals = load_signals(data_dir)
    if llm is not None and use_web_search:
        try:
            from ..llm.claude import extract_json

            text = llm.research(prompts.TREND_SYSTEM, prompts.TREND_INSTRUCTIONS.format(signals=_signals_text(signals)),
                                max_searches=6)
            data = extract_json(text)
            report = TrendReport(method="claude_web_search+signals_file", **{
                k: data.get(k, [] if k != "caveats" else "") for k in
                ("insights", "winning_patterns", "topic_ideas", "sources", "caveats")})
            logger.info("トレンド分析: Web検索で %d 件の傾向を抽出", len(report.insights))
            return report
        except Exception as exc:  # noqa: BLE001 - 失敗しても手元データで続行
            logger.error("Web検索によるトレンド分析に失敗したため、手元のデータで続行します: %s", exc)
    return TrendReport(
        method="signals_file",
        insights=list(signals.get("baseline_insights") or []),
        winning_patterns=list(signals.get("winning_patterns") or []),
        topic_ideas=list(signals.get("topic_ideas") or []),
        sources=["data/trend_signals.yaml"],
        caveats="手元の記録と一般的な傾向（仮説）に基づく分析です。実績データが増えるほど精度が上がります。",
    )


def trend_to_prompt(report: TrendReport) -> str:
    def block(title, items):
        return f"{title}:\n" + ("\n".join(f"- {i}" for i in items) if items else "- なし")

    return "\n".join([block("伸びている傾向", report.insights), block("伸びる型", report.winning_patterns),
                      block("狙い目のテーマ", report.topic_ideas)])
