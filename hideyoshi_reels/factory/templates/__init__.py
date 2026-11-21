"""デザインテンプレート A〜D の登録と自動選択。

A: 黒×金 強フック / B: 赤×金 ランキング / C: 白×紺 インフォグラフィック / D: 和紙×緑 行動チェックリスト
参考画像: design_references/ （配色・装飾・配置の参考。文字や数値は流用しない）
"""

from __future__ import annotations

import re

from ...models import Plan, PostContent
from .a_dark_gold import DarkGoldTemplate
from .b_red_gold import RedGoldTemplate
from .base import Template
from .c_white_navy import WhiteNavyTemplate
from .d_warm_checklist import WarmChecklistTemplate

TEMPLATES: dict[str, Template] = {t.key: t for t in (DarkGoldTemplate(), RedGoldTemplate(), WhiteNavyTemplate(),
                                                     WarmChecklistTemplate())}

RULES = {
    "A": (r"NG|やめ|危険|ダメ|ワナ|罠|落とし穴|保存必須|完全版|逆転|後悔|警告|知らないと|損", ("やってはいけない", "逆転")),
    "B": (r"\d+選|共通点|ランキング|TOP|ベスト|特徴|比較", ("合格者の特徴", "ランキング", "学部比較")),
    "C": (r"計画|手順|ステップ|スケジュール|まとめ|一覧|方法|勉強法|選び方|仕組み", ("計画", "勉強計画", "学部", "勉強法")),
    "D": (r"今日|今すぐ|習慣|チェック|やること|毎日|始め|行動|できること", ("習慣", "行動", "メンタル")),
}


def get_template(key: str) -> Template:
    key = key.upper()
    if key not in TEMPLATES:
        raise ValueError(f"デザインは A/B/C/D から選んでください: {key}")
    return TEMPLATES[key]


def choose_design(content: PostContent, plan: Plan | None, post_format: str, manual: str = "auto"
                  ) -> tuple[str, str, dict[str, float]]:
    """投稿テーマに合わせてデザインを選ぶ。(選んだキー, 理由, 各デザインの点数) を返す。"""
    if manual and manual != "auto":
        return manual.upper(), "手動指定", {}
    text = content.all_text() + " " + (plan.title + " " + plan.category if plan else "")
    category = plan.category if plan else ""
    scores = {k: 0.0 for k in TEMPLATES}
    reasons: dict[str, list[str]] = {k: [] for k in TEMPLATES}
    for key, (pattern, cats) in RULES.items():
        hits = set(re.findall(pattern, text))
        if hits:
            scores[key] += 1.0 + 0.5 * min(len(hits), 3)
            reasons[key].append("キーワード: " + "・".join(sorted(hits))[:30])
        if any(c in category for c in cats):
            scores[key] += 1.5
            reasons[key].append(f"カテゴリ: {category}")
    if content.expression == "angry":
        scores["A"] += 1.0
    if content.info_box:
        scores["C"] += 1.0
        reasons["C"].append("補足ボックスあり")
    if post_format in ("feed", "carousel"):
        scores["C"] += 1.0
        reasons["C"].append("フィード向き")
    if len(content.items) >= 4 and content.action_line:
        scores["D"] += 1.0
        reasons["D"].append("行動リスト4項目")
    if content.design_hint:
        scores[content.design_hint] += 1.5
        reasons[content.design_hint].append("原稿作成時の推奨")
    best = max(scores, key=lambda k: (scores[k], k == content.design_hint))
    return best, " / ".join(reasons[best]) or "既定", scores


__all__ = ["TEMPLATES", "Template", "choose_design", "get_template"]
