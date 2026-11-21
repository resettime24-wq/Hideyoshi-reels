from hideyoshi_reels.history import History
from hideyoshi_reels.models import EXPRESSIONS, FactCheckReport, ClaimCheck
from hideyoshi_reels.stages import caption, factcheck, planner, scriptwriter


def test_mock_plan_and_script(settings):
    history = History(settings.history_path)
    plan, src = planner.generate_plan(None, history, settings.data_dir)
    assert plan.title and plan.plan_id and len(plan.value_points) == 3
    script = scriptwriter.write_script(None, plan, history, settings, src, seed=1)
    sections = [s.section for s in script.scenes]
    assert sections[0] == "hook" and sections[-1] == "conclusion"
    assert sections.count("explanation") == 3
    assert all(s.expression in EXPRESSIONS for s in script.scenes)
    # 日本語ナレーション 1秒約7文字として 20〜35秒前後に収まる長さ
    assert 120 <= len(script.full_narration) <= 280


def test_history_prevents_duplicate_topics(settings):
    history = History(settings.history_path)
    plan1, _ = planner.generate_plan(None, history, settings.data_dir)
    history.add({"title": plan1.title, "keywords": plan1.keywords})
    history.save()
    reloaded = History(settings.history_path)
    plan2, _ = planner.generate_plan(None, reloaded, settings.data_dir)
    assert plan2.title != plan1.title
    assert reloaded.is_duplicate(plan1.title + "！")


def test_phrases_vary_from_recent_history(settings):
    history = History(settings.history_path)
    plan, src = planner.generate_plan(None, history, settings.data_dir)
    first = scriptwriter.write_script(None, plan, history, settings, src, seed=3)
    history.add({"title": "x", "opening_phrase": first.opening_phrase, "closing_phrase": first.closing_phrase})
    second = scriptwriter.write_script(None, plan, history, settings, src, seed=3)
    assert second.opening_phrase != first.opening_phrase
    assert second.closing_phrase != first.closing_phrase


def test_topic_filter(settings):
    plan, _ = planner.generate_plan(None, History(settings.history_path), settings.data_dir, topic="集中力")
    assert "集中" in plan.title


def test_detect_risky_sentences():
    text = "早稲田の倍率は5倍じゃ。毎日コツコツやるのじゃ。偏差値は気にするな。"
    found = factcheck.detect_risky_sentences(text)
    assert "早稲田の倍率は5倍じゃ。" in found
    assert "偏差値は気にするな。" in found
    assert all("コツコツ" not in s for s in found)


def test_local_factcheck_marks_unverified_and_softens(settings):
    history = History(settings.history_path)
    plan, src = planner.generate_plan(None, history, settings.data_dir, topic="学部選び")
    script = scriptwriter.write_script(None, plan, history, settings, src, seed=1)
    script.scenes[2].narration += "合格率は30%じゃ。"
    report = factcheck.fact_check(None, plan, script, settings.data_dir)
    statuses = {c.claim: c.status for c in report.checks}
    assert plan.factual_claims[0] in statuses
    assert all(v == "unverified" for v in statuses.values())
    assert any("30%" in c for c in statuses)
    md = factcheck.review_checklist_markdown(report, [])
    assert "未確認" in md


def test_apply_fact_check_replaces_text(settings):
    history = History(settings.history_path)
    plan, src = planner.generate_plan(None, history, settings.data_dir)
    script = scriptwriter.write_script(None, plan, history, settings, src, seed=1)
    script.scenes[1].narration = "早稲田は倍率が10倍じゃ。"
    script.scenes[1].subtitle = script.scenes[1].narration
    report = FactCheckReport(method="test", checked_at="now", checks=[ClaimCheck(
        claim="倍率が10倍じゃ", status="unverified", safe_wording="倍率は年度で変わるのじゃ")])
    changes = factcheck.apply_fact_check(script, report)
    assert changes and "10倍" not in script.scenes[1].narration
    assert "10倍" not in script.scenes[1].subtitle


def test_verified_facts_file(settings):
    (settings.data_dir / "verified_facts.yaml").write_text(
        "facts:\n  - claim: 早稲田大学は学部ごとに入試科目や配点が異なる\n"
        "    source: https://www.waseda.jp/inst/admission/\n    verified_on: 2099-01-01\n", encoding="utf-8")
    history = History(settings.history_path)
    plan, src = planner.generate_plan(None, history, settings.data_dir, topic="学部選び")
    script = scriptwriter.write_script(None, plan, history, settings, src)
    report = factcheck.fact_check(None, plan, script, settings.data_dir)
    assert report.checks[0].status == "verified"


def test_caption_and_hashtags(settings, monkeypatch):
    monkeypatch.setenv("HASHTAG_LIMIT", "5")
    history = History(settings.history_path)
    plan, src = planner.generate_plan(None, history, settings.data_dir)
    script = scriptwriter.write_script(None, plan, history, settings, src)
    text, tags, extended = caption.make_caption(None, plan, script, credits=["VOICEVOX:青山龍星"])
    assert "公式サイト" in text and "VOICEVOX" in text
    assert len(tags) == 5 and all(t.startswith("#") for t in tags)
    assert len(set(tags)) == len(tags)
    assert len(extended) >= len(tags)
