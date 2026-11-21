"""工程⑤ 投稿用キャプションとハッシュタグ。"""

from __future__ import annotations

import logging
import os

from ..models import CaptionDraft, Plan, Script
from . import prompts
from .planner import plan_to_json

logger = logging.getLogger(__name__)

BASE_TAGS = ["#早稲田", "#早稲田大学", "#早稲田志望", "#大学受験", "#受験生", "#受験勉強",
             "#勉強法", "#逆転合格", "#高校生", "#浪人生", "#勉強垢", "#ちび秀吉"]
DISCLAIMER = "※入試情報は必ず大学公式サイト・募集要項で最新情報を確認してください。"


def hashtag_limit() -> int:
    try:
        return max(1, int(os.environ.get("HASHTAG_LIMIT", "5")))
    except ValueError:
        return 5


def normalize_tags(tags: list[str], limit: int) -> list[str]:
    result: list[str] = []
    for tag in tags:
        tag = tag.strip().replace(" ", "").replace("＃", "#")
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag
        if tag not in result:
            result.append(tag)
    return result[:limit]


def make_caption(llm, plan: Plan, script: Script, credits: list[str] | None = None) -> tuple[str, list[str], list[str]]:
    """(キャプション本文, 投稿用ハッシュタグ, 予備のハッシュタグ候補) を返す。"""
    limit = hashtag_limit()
    if llm is None:
        caption, tags = _mock_caption(plan)
    else:
        draft = llm.structured(prompts.ACCOUNT_BRIEF, prompts.CAPTION_INSTRUCTIONS.format(
            plan_json=plan_to_json(plan), narration=script.full_narration, limit=limit), CaptionDraft)
        caption, tags = draft.caption.strip(), draft.hashtags
    if DISCLAIMER not in caption and "公式サイト" not in caption:
        caption += "\n\n" + DISCLAIMER
    if credits:
        caption += "\n\n" + "\n".join(credits)
    extended = normalize_tags(tags + BASE_TAGS + [f"#{k}" for k in plan.keywords], 30)
    return caption, normalize_tags(tags + BASE_TAGS, limit), extended


def _mock_caption(plan: Plan) -> tuple[str, list[str]]:
    bullets = "\n".join(f"✔ {p}" for p in plan.value_points)
    caption = (
        f"{plan.hook}🏯\n\n"
        f"今日のテーマは「{plan.title}」じゃ。\n\n"
        f"{bullets}\n\n"
        "あとで見返せるように保存しておくのじゃ。\n"
        "早稲田を目指すおぬしを、わしが全力で応援するぞ。フォローもお忘れなく！"
    )
    tags = ["#早稲田志望", "#大学受験"] + [f"#{k}" for k in plan.keywords[:2]] + ["#受験生"]
    return caption, tags
