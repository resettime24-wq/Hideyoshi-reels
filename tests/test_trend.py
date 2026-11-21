"""Trend（分析・企画・原稿・事実確認）と Monetization のテスト。"""

from hideyoshi_reels.history import History
from hideyoshi_reels.models import ClaimCheck, FactCheckReport, PostContent, PostItem
from hideyoshi_reels.monetization import caption
from hideyoshi_reels.monetization.planner import plan_monetization
from hideyoshi_reels.trend import factcheck
from hideyoshi_reels.trend.analyzer import analyze_trends
from hideyoshi_reels.trend.planner import generate_plan
from hideyoshi_reels.trend.writer import clip, normalize, visible_len, write_post


def _plan_and_post(settings, topic=None, history=None):
    history = history or History(settings.history_path)
    trend = analyze_trends(None, settings.data_dir)
    plan, src = generate_plan(None, history, settings.data_dir, trend, "reel", topic)
    return plan, write_post(None, plan, history, "reel", src)


def test_trend_report_from_signals(settings):
    report = analyze_trends(None, settings.data_dir)
    assert report.method == "signals_file"
    assert report.insights and report.winning_patterns and report.topic_ideas


def test_mock_plan_and_post(settings):
    plan, post = _plan_and_post(settings)
    assert plan.title and plan.plan_id
    assert 2 <= len(post.items) <= 4
    assert post.title_main and post.kicker
    assert visible_len(post.kicker) <= 14


def test_history_prevents_duplicate_topics(settings):
    history = History(settings.history_path)
    plan1, _ = _plan_and_post(settings, history=history)
    history.add({"title": plan1.title, "keywords": plan1.keywords})
    history.save()
    plan2, _ = _plan_and_post(settings, history=History(settings.history_path))
    assert plan2.title != plan1.title
    assert History(settings.history_path).is_duplicate(plan1.title + "！")


def test_topic_filter(settings):
    plan, _ = _plan_and_post(settings, topic="集中力")
    assert "集中" in plan.title


def test_clip_keeps_emphasis_balanced():
    assert clip("**過去問**を早めに解いて傾向をつかむ", 6) == "**過去問**を早め"
    assert clip("あいう**えおかきく**", 5) == "あいう**えお**"
    assert visible_len("**ab**c") == 3


def test_normalize_limits_lengths():
    post = PostContent(kicker="とても長い長い長い呼びかけの文章です", title_top="見出し", title_main="あいうえおかきくけ",
                       items=[PostItem(text="あ" * 30)] * 5)
    normalize(post)
    assert visible_len(post.kicker) <= 14 and visible_len(post.title_main) <= 7
    assert len(post.items) == 4 and all(visible_len(i.text) <= 18 for i in post.items)


def test_detect_risky_sentences():
    found = factcheck.detect_risky_sentences("早稲田の倍率は5倍。毎日コツコツやる。偏差値は気にするな。")
    assert "早稲田の倍率は5倍。" in found and "偏差値は気にするな。" in found
    assert all("コツコツ" not in s for s in found)


def test_local_factcheck_flags_numbers(settings):
    plan, post = _plan_and_post(settings, topic="学部選び")
    post.info_box.value = "合格率は30%"
    report = factcheck.fact_check(None, plan, post, settings.data_dir)
    claims = [c.claim for c in report.checks]
    assert plan.factual_claims[0] in claims
    assert any("30%" in c for c in claims)
    assert all(c.status == "unverified" for c in report.checks)
    assert "未確認" in factcheck.review_checklist_markdown(report, [])


def test_apply_fact_check_replaces_text_across_emphasis(settings):
    _, post = _plan_and_post(settings)
    post.items[0].text = "倍率は**10倍**じゃ"
    report = FactCheckReport(method="t", checked_at="now", checks=[
        ClaimCheck(claim="倍率は10倍じゃ", status="unverified", safe_wording="倍率は年度で変わる")])
    changes = factcheck.apply_fact_check(post, report)
    assert changes and post.items[0].text == "倍率は年度で変わる"


def test_verified_facts_file(settings):
    (settings.data_dir / "verified_facts.yaml").write_text(
        "facts:\n  - claim: 早稲田大学は学部ごとに入試科目や配点が異なる\n"
        "    source: https://www.waseda.jp/inst/admission/\n    verified_on: 2099-01-01\n", encoding="utf-8")
    plan, post = _plan_and_post(settings, topic="学部選び")
    report = factcheck.fact_check(None, plan, post, settings.data_dir)
    assert report.checks[0].status == "verified"


def test_monetization_without_note_url(settings):
    plan, post = _plan_and_post(settings)
    m = plan_monetization(None, plan, post, note_url="")
    assert "リンク" not in m.caption_cta and m.stage == "信頼構築期"
    assert m.note_offer.title and m.affiliate_ideas
    assert any("ステマ" in n for n in m.compliance_notes)
    assert all("http" not in a.search_keyword for a in m.affiliate_ideas)  # 実在URLを作らない


def test_caption_with_note_and_affiliate(settings, monkeypatch):
    monkeypatch.setenv("HASHTAG_LIMIT", "5")
    plan, post = _plan_and_post(settings)
    m = plan_monetization(None, plan, post, note_url="https://note.com/example/n/abc")
    text, tags, extended = caption.make_caption(None, plan, post, m, "https://note.com/example/n/abc",
                                                affiliate_enabled=True)
    assert text.startswith("【PR】")
    assert "https://note.com/example/n/abc" in text and "公式サイト" in text
    assert len(tags) == 5 and len(set(tags)) == 5 and all(t.startswith("#") for t in tags)
    assert len(extended) >= len(tags)


def test_caption_without_affiliate_has_no_pr(settings):
    plan, post = _plan_and_post(settings)
    text, _, _ = caption.make_caption(None, plan, post, plan_monetization(None, plan, post))
    assert "【PR】" not in text and "http" not in text
