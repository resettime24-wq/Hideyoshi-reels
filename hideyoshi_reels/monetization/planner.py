"""Monetization: 投稿内容に合った note・アフィリエイトへの収益化導線を設計する。

方針:
- 今はフォロワーとの信頼構築を最優先。押し売りはしない
- note の URL（NOTE_URL）が設定されていない間は、キャプションにリンク誘導を入れない
- アフィリエイトは「商品の種類」と検索キーワードの提案のみ。実在URLや価格は生成しない
- 広告を含む投稿には「PR」等の表示が必要（2023年10月施行のステルスマーケティング規制）
"""

from __future__ import annotations

import logging

from ..models import AffiliateIdea, MonetizationPlan, NoteOffer, Plan, PostContent
from ..trend import prompts
from ..trend.planner import plan_to_json

logger = logging.getLogger(__name__)

COMPLIANCE = [
    "アフィリエイトリンクや提供を含む投稿は、キャプション冒頭などに「PR」「広告」と分かりやすく表示する（ステマ規制）",
    "Amazonアソシエイト等を使う場合は各プログラムの規約に従い、必要な表記をプロフィール等に記載する",
    "合格保証・成績保証と受け取られる表現は使わない",
    "早稲田大学の公式アカウントと誤認される表現・ロゴの無断使用をしない",
]

AFFILIATE_BY_CATEGORY = {
    "勉強計画": [("学習計画手帳", "計画を書き出して管理できる", "受験 勉強 計画 手帳")],
    "習慣": [("学習タイマー", "時間を区切る勉強に使える", "勉強 タイマー 学習用"),
             ("単語カード", "毎日の暗記を続けやすい", "単語カード リング")],
    "勉強法": [("学習タイマー", "時間を区切る勉強に使える", "勉強 タイマー 学習用")],
    "合格者の特徴": [("早稲田大学の過去問題集", "早めに過去問を見る習慣づくりに", "早稲田大学 過去問 学部名")],
    "学部比較": [("大学・学部ガイド本", "学部ごとの学びを比較できる", "大学 学部 ガイド 受験")],
}
DEFAULT_AFFILIATE = [("英単語帳", "多くの受験生が毎日使う基本教材", "大学受験 英単語帳")]


def plan_monetization(llm, plan: Plan, content: PostContent, note_url: str = "") -> MonetizationPlan:
    if llm is not None:
        result = llm.structured(prompts.ACCOUNT_BRIEF, prompts.MONETIZATION_INSTRUCTIONS.format(
            plan_json=plan_to_json(plan), post_text=content.all_text(), note_url=note_url or "（未設定）"),
            MonetizationPlan)
    else:
        result = _mock_plan(plan, content, note_url)
    for note in COMPLIANCE:  # 必須の注意点は必ず含める
        if note not in result.compliance_notes:
            result.compliance_notes.append(note)
    if not note_url:  # URL未設定の間はリンク誘導をしない
        result.caption_cta = _strip_link_talk(result.caption_cta)
    return result


def _strip_link_talk(text: str) -> str:
    if any(w in text for w in ("リンク", "URL", "プロフ")):
        return "もっと詳しい早稲田対策も、このアカウントで順番に紹介していくぞ。"
    return text


def _mock_plan(plan: Plan, content: PostContent, note_url: str) -> MonetizationPlan:
    ideas = next((v for k, v in AFFILIATE_BY_CATEGORY.items() if k in plan.category), DEFAULT_AFFILIATE)
    cta = ("この続きの『詳しいやり方』はプロフィールのリンク（note）にまとめておるぞ。" if note_url
           else "もっと詳しい早稲田対策も、このアカウントで順番に紹介していくぞ。")
    return MonetizationPlan(
        stage="信頼構築期" if not note_url else "note告知期",
        caption_cta=cta,
        profile_link_text="早稲田合格への道しるべ📘 詳しい対策noteはこちら" if note_url else "（note公開後に設定）",
        note_offer=NoteOffer(
            title=f"【早稲田志望専用】{plan.title}・完全実践ガイド",
            summary=f"投稿で紹介した「{'・'.join(content.items[i].text.replace('**', '') for i in range(min(3, len(content.items))))}」"
                    "を、具体的な手順と週ごとの計画例つきで詳しく解説する。",
            relation="今回の投稿の詳細版（画像では要点のみ、noteで実践方法まで）",
        ),
        affiliate_ideas=[AffiliateIdea(product_type=p, reason=r, search_keyword=k) for p, r, k in ideas],
        compliance_notes=[],
    )
