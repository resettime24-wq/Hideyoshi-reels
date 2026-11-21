"""ファクトチェック工程。

- 本番: Claude が Web 検索で一次資料を確認し、確認できない記述を断定しない表現に置き換える
- モック: data/verified_facts.yaml に人が登録した事実だけを「確認済み」とする
- 共通: 数値（偏差値・倍率・%など）を含む文をルールで検出し、要確認リストに必ず載せる
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path

import yaml

from ..history import similarity
from ..models import ClaimCheck, FactCheckReport, Plan, Script
from ..utils import now_jst
from . import prompts

logger = logging.getLogger(__name__)

RISKY_PATTERN = re.compile(
    r"(偏差値|倍率|合格率|合格最低点|配点|定員|募集人員|共通テスト|\d+\s*(%|％|点|倍|人|名|校|年|月|日|位))"
)


def detect_risky_sentences(text: str) -> list[str]:
    """事実確認が必要そうな文（数値や入試用語を含む文）を抜き出す。"""
    sentences = [s for s in re.split(r"(?<=[。！？!?])", text) if s.strip()]
    return [s.strip() for s in sentences if RISKY_PATTERN.search(s)]


def load_verified_facts(data_dir: Path, max_age_days: int = 365) -> list[dict]:
    path = data_dir / "verified_facts.yaml"
    if not path.exists():
        return []
    facts = yaml.safe_load(path.read_text(encoding="utf-8")).get("facts") or []
    fresh = []
    for f in facts:
        try:
            verified_on = date.fromisoformat(str(f.get("verified_on")))
        except ValueError:
            continue
        if date.today() - verified_on <= timedelta(days=max_age_days):
            fresh.append(f)
        else:
            logger.warning("確認から1年以上経った事実情報です（要再確認）: %s", f.get("claim"))
    return fresh


def fact_check(llm, plan: Plan, script: Script, data_dir: Path, use_web_search: bool = True) -> FactCheckReport:
    if llm is not None and use_web_search:
        try:
            return _llm_fact_check(llm, plan, script)
        except Exception as exc:  # noqa: BLE001 - 失敗してもルールベースで続行
            logger.error("Web検索によるファクトチェックに失敗しました: %s", exc)
    return _local_fact_check(plan, script, data_dir)


def _llm_fact_check(llm, plan: Plan, script: Script) -> FactCheckReport:
    narration = "\n".join(f"[{i}] {s.narration}" for i, s in enumerate(script.scenes))
    claims = "\n".join(f"- {c}" for c in plan.factual_claims) or "（なし）"
    text = llm.research(prompts.FACTCHECK_SYSTEM,
                        prompts.FACTCHECK_INSTRUCTIONS.format(narration=narration, claims=claims))
    from ..llm.claude import extract_json

    try:
        data = extract_json(text)
    except ValueError:
        data = {"checks": []}
        logger.warning("ファクトチェック結果のJSONを読み取れませんでした。生テキストを保存します。")
    checks = []
    for raw in data.get("checks", []):
        try:
            checks.append(ClaimCheck(**raw))
        except Exception:  # noqa: BLE001
            logger.debug("無効なチェック項目をスキップ: %s", raw)
    report = FactCheckReport(method="claude_web_search", checked_at=now_jst().isoformat(timespec="seconds"),
                             checks=checks)
    _add_rule_based(report, script, verified_claims=[c.claim for c in checks])
    return report


def _local_fact_check(plan: Plan, script: Script, data_dir: Path) -> FactCheckReport:
    facts = load_verified_facts(data_dir)
    checks = []
    for claim in plan.factual_claims:
        match = next((f for f in facts if similarity(claim, f["claim"]) >= 0.8), None)
        if match:
            checks.append(ClaimCheck(claim=claim, status="verified", safe_wording=claim,
                                     sources=[match.get("source", "")], note="verified_facts.yaml に登録済み"))
        else:
            checks.append(ClaimCheck(
                claim=claim, status="unverified",
                safe_wording=f"{claim}と言われておる。最新の募集要項で必ず確認じゃ",
                note="一次資料で未確認。台本では断定しない表現にしています"))
    report = FactCheckReport(method="local_rules", checked_at=now_jst().isoformat(timespec="seconds"),
                             checks=checks)
    _add_rule_based(report, script, verified_claims=[f["claim"] for f in facts])
    return report


def _add_rule_based(report: FactCheckReport, script: Script, verified_claims: list[str]) -> None:
    known = [c.claim for c in report.checks] + verified_claims
    for sentence in detect_risky_sentences(script.full_narration):
        if any(k and (k in sentence or similarity(k, sentence) >= 0.8) for k in known):
            continue
        report.checks.append(ClaimCheck(
            claim=sentence, status="unverified", safe_wording=sentence,
            note="数値・入試用語を含むため自動検出。投稿前に人が確認してください"))


def apply_fact_check(script: Script, report: FactCheckReport) -> list[str]:
    """未確認・誤りの記述を安全な表現に置き換える。置換した内容を返す。"""
    changes = []
    for check in report.checks:
        if check.status == "verified" or not check.safe_wording or check.safe_wording == check.claim:
            continue
        for scene in script.scenes:
            for attr in ("narration", "subtitle"):
                value = getattr(scene, attr)
                if check.claim in value:
                    setattr(scene, attr, value.replace(check.claim, check.safe_wording))
                    if attr == "narration":
                        changes.append(f"「{check.claim}」→「{check.safe_wording}」")
    for c in changes:
        logger.info("ファクトチェックにより修正: %s", c)
    return changes


def review_checklist_markdown(report: FactCheckReport, changes: list[str]) -> str:
    lines = ["# 投稿前チェックリスト", "",
             f"- チェック方法: {report.method}", f"- 実施日時: {report.checked_at}", ""]
    if not report.checks:
        lines.append("事実確認が必要な記述は検出されませんでした（念のため動画を一度見て確認してください）。")
    for c in report.checks:
        mark = {"verified": "✅ 確認済み", "unverified": "⚠️ 未確認", "incorrect": "❌ 誤り"}[c.status]
        lines += [f"## {mark}", f"- 記述: {c.claim}", f"- 使用した表現: {c.safe_wording}"]
        if c.sources:
            lines.append("- 資料: " + ", ".join(c.sources))
        if c.note:
            lines.append(f"- メモ: {c.note}")
        lines.append("")
    if changes:
        lines += ["## 自動修正した箇所", *[f"- {c}" for c in changes], ""]
    lines += ["---", "入試情報は年度によって変わります。投稿前に大学公式サイト・募集要項で最新情報を確認してください。"]
    return "\n".join(lines)


def report_to_json(report: FactCheckReport) -> str:
    return json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
