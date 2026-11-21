"""パイプライン全体で使うデータ構造（Pydantic モデル）。

文字列中の **語句** は「強調（赤字など）」として各デザインで描画されます。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Expression = Literal["happy", "surprised", "angry", "thinking", "explaining"]
DesignStyle = Literal["A", "B", "C", "D"]
IconName = Literal["book", "pencil", "calendar", "note", "chart", "card", "clock", "star", "check", "target"]

EXPRESSIONS: tuple[str, ...] = ("happy", "surprised", "angry", "thinking", "explaining")


# ---------- Trend: トレンド分析 ----------
class TrendReport(BaseModel):
    method: str = Field(description="分析方法（web_search / signals_file など）")
    insights: list[str] = Field(default_factory=list, description="伸びている投稿の傾向")
    winning_patterns: list[str] = Field(default_factory=list, description="真似すべき型（見出しの型・構成など）")
    topic_ideas: list[str] = Field(default_factory=list, description="今狙い目のテーマ")
    sources: list[str] = Field(default_factory=list, description="参考にした資料のURLなど")
    caveats: str = ""


# ---------- Trend: 企画 ----------
class PlanDraft(BaseModel):
    title: str = Field(description="企画タイトル（20文字前後）")
    category: str = Field(description="カテゴリ（例: 勉強法, 学部比較, あるある, 合格者の特徴, 計画）")
    target: str = Field(description="主なターゲット（例: 高2・偏差値50台の早稲田志望）")
    hook: str = Field(description="1秒で指が止まるフック（20文字以内）")
    value_points: list[str] = Field(description="保存したくなる具体的な有益ポイント（3〜4つ）")
    retention_device: str = Field(description="最後まで読みたくなる工夫・キャプションへ誘導する工夫")
    factual_claims: list[str] = Field(default_factory=list,
                                      description="入試制度・偏差値・倍率など事実確認が必要な主張。無ければ空配列")
    keywords: list[str] = Field(description="企画を表すキーワード（3〜5個）")
    trend_basis: str = Field(default="", description="この企画が伸びると考える根拠（トレンド分析との対応）")
    appeal_score: int = Field(description="フック・保存性の総合自己評価（1〜10）")


class PlanCandidates(BaseModel):
    candidates: list[PlanDraft]


class Plan(PlanDraft):
    plan_id: str
    created_at: str


# ---------- Trend: 投稿原稿（画像に載せる文字） ----------
class PostItem(BaseModel):
    text: str = Field(description="箇条書き1項目（16文字以内。強調したい語は **語** で囲む）")
    detail: str = Field(default="", description="カルーセルの詳細ページ用の補足（60文字以内）")
    icon: IconName = "check"


class InfoBox(BaseModel):
    label: str = Field(description="補足ボックスの見出し（例: まず目指す目安）")
    value: str = Field(description="補足ボックスの中身（14文字以内。未確認の数値は書かない）")


class PostContent(BaseModel):
    kicker: str = Field(description="最上部の帯の短い呼びかけ（12文字以内、例: 早稲田志望は**保存必須**）")
    title_top: str = Field(description="見出し1行目（9文字以内）")
    title_main: str = Field(description="最も大きく見せる語（2〜6文字）")
    title_bottom: str = Field(default="", description="見出し3行目（9文字以内。無ければ空）")
    badge: str = Field(default="", description="強調バッジ（例: 3選 / 完全版 / 保存版。4文字以内）")
    list_heading: str = Field(default="", description="箇条書きの上の小見出し（14文字以内）")
    items: list[PostItem] = Field(description="箇条書き（3〜4項目）")
    info_box: InfoBox | None = None
    action_line: str = Field(default="", description="行動を後押しする一言（14文字以内、例: まずは**1つ**だけでもOK）")
    caption_cta: str = Field(default="詳しくはキャプションで解説！", description="キャプションへの誘導（16文字以内）")
    save_cta: str = Field(default="保存して後で見返す", description="保存の促し（12文字以内）")
    expression: Expression = "explaining"
    design_hint: DesignStyle | None = Field(default=None, description="合いそうなデザイン A/B/C/D")

    def all_text(self) -> str:
        parts = [self.kicker, self.title_top, self.title_main, self.title_bottom, self.badge,
                 self.list_heading, self.action_line, self.caption_cta, self.save_cta]
        parts += [i.text for i in self.items] + [i.detail for i in self.items]
        if self.info_box:
            parts += [self.info_box.label, self.info_box.value]
        return "\n".join(p for p in parts if p)


# ---------- ファクトチェック ----------
class ClaimCheck(BaseModel):
    claim: str
    status: Literal["verified", "unverified", "incorrect"]
    safe_wording: str = Field(description="投稿で使ってよい表現。未確認なら断定しない言い回しにする")
    sources: list[str] = Field(default_factory=list, description="確認に使った資料のURL")
    note: str = ""


class FactCheckReport(BaseModel):
    method: str
    checked_at: str
    checks: list[ClaimCheck] = Field(default_factory=list)

    @property
    def unverified(self) -> list[ClaimCheck]:
        return [c for c in self.checks if c.status != "verified"]


# ---------- Monetization ----------
class AffiliateIdea(BaseModel):
    product_type: str = Field(description="紹介する商品の種類（例: 英単語帳, 学習タイマー）")
    reason: str = Field(description="投稿内容との関連")
    search_keyword: str = Field(description="商品を探すための検索キーワード（実在のURLは書かない）")


class NoteOffer(BaseModel):
    title: str = Field(description="将来販売するnoteのタイトル案")
    summary: str = Field(description="内容の要約（100文字以内）")
    relation: str = Field(description="今回の投稿との関係（投稿の続き・詳細版など）")


class MonetizationPlan(BaseModel):
    stage: str = Field(description="現在の収益化段階（例: 信頼構築期 / note告知期）")
    caption_cta: str = Field(description="キャプション末尾に入れる自然な導線（押し売りしない）")
    profile_link_text: str = Field(description="プロフィールのリンク欄の文言案")
    note_offer: NoteOffer
    affiliate_ideas: list[AffiliateIdea] = Field(default_factory=list)
    compliance_notes: list[str] = Field(default_factory=list, description="表示義務などの注意点")


class CaptionDraft(BaseModel):
    caption: str = Field(description="Instagram投稿キャプション本文（ハッシュタグ除く）")
    hashtags: list[str] = Field(description="ハッシュタグ（#付き）")
