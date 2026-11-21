"""Trend: 画像に載せる文字原稿（台本）の作成。"""

from __future__ import annotations

import logging
import re

from ..history import History
from ..models import Plan, PostContent, PostItem
from . import prompts
from .planner import plan_to_json

logger = logging.getLogger(__name__)

# 画像に載せる文字の上限（デザインが崩れないよう、超えた分は自動で詰める）
LIMITS = {"kicker": 14, "title_top": 10, "title_main": 7, "title_bottom": 10, "badge": 4,
          "list_heading": 16, "action_line": 16, "caption_cta": 18, "save_cta": 14}
ITEM_LIMIT = 18
DETAIL_LIMIT = 70


def visible_len(text: str) -> int:
    return len(text.replace("**", ""))


def clip(text: str, limit: int) -> str:
    """強調記号 ** を壊さずに文字数を limit 以内にする。"""
    if visible_len(text) <= limit:
        return text
    out, count, emph = "", 0, False
    i = 0
    while i < len(text) and count < limit:
        if text.startswith("**", i):
            emph = not emph
            out += "**"
            i += 2
            continue
        out += text[i]
        count += 1
        i += 1
    if emph:
        out += "**"
    return out


def normalize(content: PostContent) -> list[str]:
    """文字数制限を適用し、調整した内容を返す。"""
    changes = []
    for field, limit in LIMITS.items():
        value = getattr(content, field) or ""
        if visible_len(value) > limit:
            setattr(content, field, clip(value, limit))
            changes.append(f"{field} を {limit} 文字に短縮")
    if len(content.items) > 4:
        content.items = content.items[:4]
        changes.append("箇条書きを4項目に削減")
    for item in content.items:
        if visible_len(item.text) > ITEM_LIMIT:
            item.text = clip(item.text, ITEM_LIMIT)
            changes.append(f"項目「{item.text}」を短縮")
        if len(item.detail) > DETAIL_LIMIT:
            item.detail = item.detail[:DETAIL_LIMIT]
        if item.text.count("**") % 2:
            item.text = item.text.replace("**", "")
    if content.info_box and visible_len(content.info_box.value) > 16:
        content.info_box.value = clip(content.info_box.value, 16)
    for c in changes:
        logger.info("原稿を調整: %s", c)
    return changes


def write_post(llm, plan: Plan, history: History, post_format: str, mock_source: dict | None = None) -> PostContent:
    if llm is None:
        content = _mock_post(plan, mock_source or {})
    else:
        hooks = " / ".join(history.recent_phrases(10)["hooks"]) or "なし"
        content = llm.structured(prompts.ACCOUNT_BRIEF, prompts.POST_INSTRUCTIONS.format(
            post_format=post_format, plan_json=plan_to_json(plan), recent_hooks=hooks), PostContent)
    if len(content.items) < 2:
        raise ValueError("箇条書きが少なすぎます")
    normalize(content)
    return content


def _mock_post(plan: Plan, src: dict) -> PostContent:
    post = dict(src.get("post") or {})
    if not post:  # ネタ帳に原稿が無い場合は企画から組み立てる
        post = {"kicker": "早稲田志望は**必見**", "title_top": plan.title[:9], "title_main": "コツ",
                "badge": f"{len(plan.value_points)}選",
                "items": [{"text": p[:16], "detail": p} for p in plan.value_points]}
    post["items"] = [PostItem(**i) if isinstance(i, dict) else i for i in post.get("items", [])]
    return PostContent(**post)


def strip_emphasis(text: str) -> str:
    return re.sub(r"\*\*", "", text)
