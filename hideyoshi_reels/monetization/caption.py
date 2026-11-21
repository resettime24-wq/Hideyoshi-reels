"""投稿用キャプションとハッシュタグ。画像で要点を見せ、キャプションで詳しく解説する。"""

from __future__ import annotations

import logging
import os

from ..models import CaptionDraft, MonetizationPlan, Plan, PostContent
from ..trend import prompts
from ..trend.planner import plan_to_json

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


def make_caption(llm, plan: Plan, content: PostContent, monetization: MonetizationPlan | None = None,
                 note_url: str = "", affiliate_enabled: bool = False) -> tuple[str, list[str], list[str]]:
    """(キャプション本文, 投稿用ハッシュタグ, 予備のハッシュタグ候補) を返す。"""
    limit = hashtag_limit()
    cta = monetization.caption_cta if monetization else ""
    if llm is None:
        caption, tags = _mock_caption(plan, content, cta)
    else:
        draft = llm.structured(prompts.ACCOUNT_BRIEF, prompts.CAPTION_INSTRUCTIONS.format(
            plan_json=plan_to_json(plan), post_text=content.all_text(), monetization_cta=cta or "なし",
            limit=limit), CaptionDraft)
        caption, tags = draft.caption.strip(), draft.hashtags
        if cta and cta not in caption:
            caption += "\n\n" + cta
    if note_url and note_url not in caption:
        caption += f"\n{note_url}"
    if affiliate_enabled and monetization and monetization.affiliate_ideas:
        caption = "【PR】本投稿には広告（アフィリエイト）を含む場合があります。\n\n" + caption
    if DISCLAIMER not in caption and "公式サイト" not in caption:
        caption += "\n\n" + DISCLAIMER
    extended = normalize_tags(tags + BASE_TAGS + [f"#{k}" for k in plan.keywords], 30)
    return caption, normalize_tags(tags + BASE_TAGS, limit), extended


def _mock_caption(plan: Plan, content: PostContent, cta: str) -> tuple[str, list[str]]:
    lines = [f"{plan.hook}🏯", "", f"今日のテーマは「{plan.title}」じゃ。", ""]
    for k, item in enumerate(content.items, 1):
        lines.append(f"{k}️⃣ {item.text.replace('**', '')}")
        if item.detail:
            lines.append(f"　→ {item.detail}")
    lines += ["", "あとで見返せるように保存しておくのじゃ。", "早稲田を目指すおぬしを、わしが全力で応援するぞ。フォローもお忘れなく！"]
    if cta:
        lines += ["", cta]
    tags = ["#早稲田志望", "#大学受験"] + [f"#{k}" for k in plan.keywords[:2]] + ["#受験生"]
    return "\n".join(lines), tags
