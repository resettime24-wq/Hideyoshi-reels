"""Trend: 企画生成。"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import yaml

from ..history import History
from ..models import Plan, PlanCandidates, PlanDraft, TrendReport
from ..utils import now_jst
from . import prompts
from .analyzer import trend_to_prompt

logger = logging.getLogger(__name__)


def load_mock_topics(data_dir: Path) -> list[dict]:
    path = data_dir / "mock_topics.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("topics", [])


def _finalize(draft: PlanDraft) -> Plan:
    data = draft.model_dump()
    data.update(plan_id=now_jst().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6],
                created_at=now_jst().isoformat(timespec="seconds"))
    return Plan(**data)


def generate_plan(llm, history: History, data_dir: Path, trend: TrendReport, post_format: str = "reel",
                  topic: str | None = None) -> tuple[Plan, dict | None]:
    """企画を1つ決めて返す。モック時は (Plan, ネタ帳の元データ) を返す。"""
    if llm is None:
        return _mock_plan(history, data_dir, topic)
    return _llm_plan(llm, history, trend, post_format, topic), None


def _llm_plan(llm, history: History, trend: TrendReport, post_format: str, topic: str | None) -> Plan:
    recent = history.recent(15)
    past_titles = "\n".join(f"- {t}" for t in history.titles()[-60:]) or "（まだありません）"
    recent_categories = ", ".join(dict.fromkeys(e.get("category", "") for e in recent)) or "なし"
    topic_hint = f"今回のテーマ指定: 「{topic}」に沿った企画にすること。" if topic else ""

    for attempt in range(2):
        prompt = prompts.PLAN_INSTRUCTIONS.format(
            n=3, post_format=post_format, trend=trend_to_prompt(trend), recent_categories=recent_categories,
            past_titles=past_titles, topic_hint=topic_hint)
        if attempt:
            prompt += "\n前回の案は過去企画と重複していました。切り口をはっきり変えてください。"
        result = llm.structured(prompts.ACCOUNT_BRIEF, prompt, PlanCandidates)
        fresh = [c for c in result.candidates if not history.is_duplicate(c.title, c.keywords)]
        logger.info("企画候補 %d 件中 %d 件が新規", len(result.candidates), len(fresh))
        if fresh:
            return _finalize(max(fresh, key=lambda c: c.appeal_score))
    raise RuntimeError("重複しない企画を作れませんでした。テーマを指定して再実行してください。")


def _mock_plan(history: History, data_dir: Path, topic: str | None) -> tuple[Plan, dict]:
    topics = load_mock_topics(data_dir)
    if topic:
        matched = [t for t in topics if topic in t["title"] or topic in t["category"]
                   or any(topic in k for k in t["keywords"])]
        topics = matched or topics
    unused = [t for t in topics if not history.is_duplicate(t["title"], t["keywords"])]
    if not unused:
        logger.warning("モック用ネタ帳をすべて使い切りました。最も古いネタを再利用します（テスト用）。")
        used_order = {e.get("title"): i for i, e in enumerate(history.entries)}
        unused = sorted(topics, key=lambda t: used_order.get(t["title"], -1))
    chosen = unused[0]
    fields = set(PlanDraft.model_fields)
    draft = PlanDraft(**{k: v for k, v in chosen.items() if k in fields},
                      trend_basis="ネタ帳（モック）より", appeal_score=7)
    return _finalize(draft), chosen


def plan_to_json(plan: Plan) -> str:
    return json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2)
