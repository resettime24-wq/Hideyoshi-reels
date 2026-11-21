"""パイプライン全体で使うデータ構造（Pydantic モデル）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Expression = Literal["happy", "surprised", "angry", "thinking", "explaining"]
Section = Literal["hook", "problem", "explanation", "conclusion"]
SfxName = Literal["none", "pop", "whoosh", "ding", "boing", "drum", "sparkle"]

EXPRESSIONS: tuple[str, ...] = ("happy", "surprised", "angry", "thinking", "explaining")
EXPRESSION_LABELS_JA = {
    "happy": "喜ぶ",
    "surprised": "驚く",
    "angry": "怒る",
    "thinking": "考える",
    "explaining": "解説する",
}


# ---------- 工程① 企画 ----------
class PlanDraft(BaseModel):
    """LLM が出力する企画案。"""

    title: str = Field(description="企画タイトル（20文字前後）")
    category: str = Field(description="カテゴリ（例: 勉強法, 学部比較, あるある, 合格者の特徴, 計画）")
    target: str = Field(description="主なターゲット（例: 高2・偏差値50台の早稲田志望）")
    hook: str = Field(description="冒頭2秒で使うフック文（20文字以内）")
    value_points: list[str] = Field(description="保存したくなる具体的な有益ポイント（3つ）")
    retention_device: str = Field(description="最後まで見たくなる工夫（例: 3つ目が一番大事と予告）")
    factual_claims: list[str] = Field(
        default_factory=list,
        description="入試制度・偏差値・倍率など事実確認が必要な主張。無ければ空配列",
    )
    keywords: list[str] = Field(description="企画を表すキーワード（3〜5個）")
    appeal_score: int = Field(description="フック・保存性・完走率の総合自己評価（1〜10）")


class PlanCandidates(BaseModel):
    candidates: list[PlanDraft]


class Plan(PlanDraft):
    plan_id: str
    created_at: str


# ---------- ファクトチェック ----------
class ClaimCheck(BaseModel):
    claim: str
    status: Literal["verified", "unverified", "incorrect"]
    safe_wording: str = Field(description="動画で使ってよい表現。未確認なら断定しない言い回しにする")
    sources: list[str] = Field(default_factory=list, description="確認に使った資料のURL")
    note: str = ""


class FactCheckReport(BaseModel):
    method: str
    checked_at: str
    checks: list[ClaimCheck] = Field(default_factory=list)

    @property
    def unverified(self) -> list[ClaimCheck]:
        return [c for c in self.checks if c.status != "verified"]


# ---------- 工程② 台本 ----------
class Scene(BaseModel):
    section: Section
    narration: str = Field(description="ナレーション（秀吉のセリフ）")
    subtitle: str = Field(description="画面下の字幕。基本はナレーションと同じ文")
    telop: str = Field(description="画面上部に大きく出す見出し（12文字以内）")
    expression: Expression
    image_prompt: str = Field(description="背景画像の指示（英語、人物なし）")
    sfx: SfxName = "none"
    target_seconds: float = Field(description="この場面の目安秒数")


class ScriptDraft(BaseModel):
    title: str
    opening_phrase: str = Field(description="今回使った呼びかけ・言い出しのフレーズ")
    closing_phrase: str = Field(description="今回使った締めのフレーズ")
    scenes: list[Scene]


class Script(ScriptDraft):
    plan_id: str

    @property
    def full_narration(self) -> str:
        return "".join(s.narration for s in self.scenes)


# ---------- 工程⑤ 投稿用テキスト ----------
class CaptionDraft(BaseModel):
    caption: str = Field(description="Instagram投稿キャプション本文（ハッシュタグ除く）")
    hashtags: list[str] = Field(description="ハッシュタグ（#付き、10〜15個）")


# ---------- タイムライン（音声合成後に確定） ----------
class SubtitleCue(BaseModel):
    start: float
    end: float
    text: str


class SfxEvent(BaseModel):
    at: float
    name: str


class TimelineScene(BaseModel):
    index: int
    section: str
    start: float
    end: float
    expression: str
    telop: str
    narration: str
    image: str
    audio: str
    motion: str
    cues: list[SubtitleCue]


class Timeline(BaseModel):
    width: int
    height: int
    fps: int
    duration: float
    scenes: list[TimelineScene]
    sfx: list[SfxEvent]
