"""工程② 台本生成。"""

from __future__ import annotations

import logging
import random

from ..history import History, similarity
from ..models import Plan, Scene, Script, ScriptDraft
from . import prompts
from .planner import plan_to_json

logger = logging.getLogger(__name__)

SECTION_ORDER = ["hook", "problem", "explanation", "conclusion"]

# モック用の言い回しプール（毎回同じにならないよう、最近使ったものを避けて選ぶ）
OPENINGS = [
    "おぬし、", "受験生よ、聞くのじゃ。", "待たれよ！", "そこの早稲田志望！",
    "ちょっと耳を貸すのじゃ。", "わしから大事な話じゃ。", "よいか、", "おお、そこのおぬし！",
]
HOOK_ENDINGS = ["ぞ！", "のじゃ！", "かもしれんぞ！", "！"]
CLOSINGS = [
    "役に立ったら保存して、何度も見返すのじゃ。",
    "忘れぬうちに保存じゃ。続きが気になる者はフォローせよ。",
    "保存しておけば、迷った時の道しるべになるぞ。",
    "フォローしておけば、早稲田への道をわしが案内するぞ。",
    "友にも教えてやるがよい。保存も忘れずにのう。",
    "見返せるよう保存して、明日の勉強に生かすのじゃ。",
]
POINT_EXPRESSIONS = ["explaining", "happy", "explaining"]
BG_PROMPTS = {
    "hook": "dramatic radiant golden light rays over a japanese castle silhouette, festive mood",
    "problem": "a messy study desk at night with piles of textbooks and a desk lamp, slightly gloomy",
    "explanation": "a bright japanese classroom with a green chalkboard, warm sunlight",
    "conclusion": "cherry blossoms in full bloom in front of a university gate, hopeful spring morning",
}


def _pick_fresh(pool: list[str], recent: list[str], rng: random.Random) -> str:
    fresh = [p for p in pool if all(similarity(p, r) < 0.7 for r in recent)]
    return rng.choice(fresh or pool)


def write_script(llm, plan: Plan, history: History, settings, mock_source: dict | None = None,
                 seed: int | None = None) -> Script:
    if llm is None:
        script = _mock_script(plan, history, mock_source or {}, random.Random(seed))
    else:
        script = _llm_script(llm, plan, history, settings)
    _validate(script, settings)
    return script


def _llm_script(llm, plan: Plan, history: History, settings) -> Script:
    phrases = history.recent_phrases(10)
    prompt = prompts.SCRIPT_INSTRUCTIONS.format(
        plan_json=plan_to_json(plan),
        min_s=settings.min_seconds, max_s=settings.max_seconds,
        recent_openings=" / ".join(phrases["openings"]) or "なし",
        recent_closings=" / ".join(phrases["closings"]) or "なし",
        recent_hooks=" / ".join(phrases["hooks"]) or "なし",
    )
    draft = llm.structured(prompts.ACCOUNT_BRIEF, prompt, ScriptDraft)
    return Script(**draft.model_dump(), plan_id=plan.plan_id)


def _mock_script(plan: Plan, history: History, src: dict, rng: random.Random) -> Script:
    phrases = history.recent_phrases(6)
    opening = _pick_fresh(OPENINGS, phrases["openings"], rng)
    closing = _pick_fresh(CLOSINGS, phrases["closings"], rng)
    telops = src.get("telops") or [plan.title[:12]] * 6
    points = src.get("points") or [f"{p}。" for p in plan.value_points]
    is_ng = "NG" in plan.title or "やってはいけない" in plan.category

    scenes = [
        Scene(section="hook", narration=f"{opening}{plan.hook}{rng.choice(HOOK_ENDINGS)}",
              subtitle="", telop=telops[0], expression="surprised",
              image_prompt=BG_PROMPTS["hook"], sfx="drum", target_seconds=2.5),
        Scene(section="problem", narration=src.get("problem", "その悩み、わしにはよう分かるぞ。"),
              subtitle="", telop=telops[1], expression="thinking",
              image_prompt=BG_PROMPTS["problem"], sfx="boing", target_seconds=5),
    ]
    for i, point in enumerate(points[:3]):
        expr = "angry" if is_ng and i == 0 else POINT_EXPRESSIONS[i]
        scenes.append(Scene(section="explanation", narration=point, subtitle="",
                            telop=telops[2 + i] if len(telops) > 2 + i else f"ポイント{i + 1}",
                            expression=expr, image_prompt=BG_PROMPTS["explanation"],
                            sfx="pop" if i < 2 else "ding", target_seconds=5.5))
    scenes.append(Scene(section="conclusion",
                        narration=f"{src.get('conclusion', '今日から一歩ずつ進むのじゃ。')}{closing}",
                        subtitle="", telop=telops[-1], expression="happy",
                        image_prompt=BG_PROMPTS["conclusion"], sfx="sparkle", target_seconds=7))
    for s in scenes:
        s.subtitle = s.narration
    return Script(title=plan.title, opening_phrase=opening, closing_phrase=closing,
                  scenes=scenes, plan_id=plan.plan_id)


def _validate(script: Script, settings) -> None:
    if not script.scenes:
        raise ValueError("台本に場面がありません")
    order = [SECTION_ORDER.index(s.section) for s in script.scenes]
    if order != sorted(order):
        logger.warning("場面の順番が想定と異なります: %s", [s.section for s in script.scenes])
    for s in script.scenes:
        if not s.subtitle.strip():
            s.subtitle = s.narration
        if len(s.telop) > 14:
            s.telop = s.telop[:14]
    chars = len(script.full_narration)
    est = chars / 7.0
    logger.info("台本: %d 場面 / %d 文字（推定 %.1f 秒）", len(script.scenes), chars, est)
    if est > settings.max_seconds * 1.3:
        logger.warning("台本が長めです。音声を少し速めて %.0f 秒以内に収めます。", settings.max_seconds)
