"""本番API用コードの結合テスト。

実際の Anthropic / OpenAI サーバーの代わりに偽のHTTPサーバー（httpx.MockTransport）を使うので、
APIキー不要・無料で「正しい形式でリクエストを送り、レスポンスを処理できるか」を確認できます。
"""

import base64
import io
import json
import shutil

import httpx2 as httpx
import pytest

from hideyoshi_reels.images.mock_art import draw_character
from hideyoshi_reels.pipeline import Pipeline

PLAN = {"candidates": [
    {"title": "早稲田志望の英単語の覚え方", "category": "科目別対策", "target": "高2", "hook": "単語、覚えても忘れる？",
     "value_points": ["毎日同じ範囲を回す", "音読で覚える", "週末にテスト"], "retention_device": "詳しくはキャプション",
     "factual_claims": [], "keywords": ["英単語", "暗記", "音読"], "trend_basis": "暗記系は保存されやすい",
     "appeal_score": 8},
    {"title": "早稲田に受かる人の3つの共通点", "category": "合格者の特徴", "target": "高3", "hook": "x",
     "value_points": ["a", "b", "c"], "retention_device": "x", "factual_claims": [],
     "keywords": ["合格者", "共通点", "習慣"], "trend_basis": "", "appeal_score": 10},
]}
POST = {"kicker": "単語が苦手な人は**保存**", "title_top": "忘れない", "title_main": "英単語", "title_bottom": "暗記術",
        "badge": "3選", "list_heading": "この3つで定着する",
        "items": [{"text": "毎日**同じ範囲**を回す", "detail": "一度に覚えようとせず毎日繰り返す。", "icon": "card"},
                  {"text": "**音読**で覚えやすいと言われる", "detail": "声に出すと覚えやすいと言われる。", "icon": "book"},
                  {"text": "週末に**テスト**する", "detail": "忘れた単語を洗い出す。", "icon": "check"}],
        "info_box": None, "action_line": "まずは**10個**から", "caption_cta": "詳しくはキャプションで解説！",
        "save_cta": "保存して毎日見返す", "expression": "happy", "design_hint": "B"}
MONET = {"stage": "信頼構築期", "caption_cta": "続きはプロフィールのリンクから", "profile_link_text": "x",
         "note_offer": {"title": "英単語暗記の完全ガイド", "summary": "s", "relation": "詳細版"},
         "affiliate_ideas": [{"product_type": "英単語帳", "reason": "r", "search_keyword": "大学受験 英単語帳"}],
         "compliance_notes": []}
CAPTION = {"caption": "単語、覚えても忘れてない？📚\n\n1️⃣ 毎日同じ範囲を回す",
           "hashtags": ["#早稲田志望", "#英単語", "#大学受験", "#勉強法", "#受験生"]}
TREND_TEXT = ('```json\n{"insights": ["チェックリスト型が保存されやすい"], "winning_patterns": ["〇選"], '
              '"topic_ideas": ["英単語"], "sources": ["https://example.com/article"], "caveats": "推測を含む"}\n```')
FACTCHECK_TEXT = ('```json\n{"checks": [{"claim": "音読で覚えやすいと言われる", "status": "unverified", '
                  '"safe_wording": "音読も試す価値あり", "sources": [], "note": ""}]}\n```')


def _message(text):
    return {"id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 500}}


def _png_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class FakeServers:
    def __init__(self):
        self.requests = []

    def anthropic(self, request: httpx.Request):
        body = json.loads(request.content)
        self.requests.append(("anthropic", request, body))
        system = body.get("system", "")
        if body.get("tools"):
            return httpx.Response(200, json=_message(TREND_TEXT if "アナリスト" in system else FACTCHECK_TEXT))
        props = json.dumps(body["output_config"]["format"]["schema"], ensure_ascii=False)
        for key, payload in (('"candidates"', PLAN), ('"kicker"', POST), ('"note_offer"', MONET)):
            if key in props:
                return httpx.Response(200, json=_message(json.dumps(payload, ensure_ascii=False)))
        return httpx.Response(200, json=_message(json.dumps(CAPTION, ensure_ascii=False)))

    def openai(self, request: httpx.Request):
        self.requests.append(("openai", request, None))
        return httpx.Response(200, json={"created": 0, "data": [{"b64_json": _png_b64(draw_character("happy"))}]})


@pytest.fixture
def fake_apis(monkeypatch):
    import anthropic
    import openai

    servers = FakeServers()
    real_anthropic, real_openai = anthropic.Anthropic, openai.OpenAI
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: real_anthropic(
        **kw, http_client=httpx.Client(transport=httpx.MockTransport(servers.anthropic))))
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: real_openai(
        **kw, http_client=httpx.Client(transport=httpx.MockTransport(servers.openai))))
    return servers


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg が必要です")
def test_pipeline_with_real_provider_code(settings, fake_apis, tmp_path, project_root):
    settings.mode = "auto"
    settings.strict = True  # モックへの切り替えを禁止して、本番コードが最後まで動くことを確認
    settings.anthropic_api_key = "sk-ant-test"
    settings.openai_api_key = "sk-test"
    settings.note_url = "https://note.com/example/n/abc"
    assets = tmp_path / "assets"
    (assets / "character").mkdir(parents=True)
    shutil.copy(project_root / "assets/character/character.yaml", assets / "character/character.yaml")
    settings.assets_dir = assets

    result = Pipeline(settings).run()
    out = result.output_dir
    assert result.title == "早稲田に受かる人の3つの共通点"  # 自己評価が最も高い案
    assert result.log["providers"] == {"llm": "claude (claude-opus-5-5)", "character": "openai"}
    assert result.log["fallbacks"] == []
    assert result.design == "B"

    calls = [b for kind, _, b in fake_apis.requests if kind == "anthropic"]
    assert all(b["model"] == "claude-opus-5-5" and b["fallbacks"] == "default" for b in calls)
    assert all(b["output_config"]["effort"] == "medium" for b in calls)
    searches = [b for b in calls if b.get("tools")]
    assert len(searches) == 2 and all(b["tools"][0]["type"] == "web_search_20260209" for b in searches)
    headers = [r.headers.get("anthropic-beta", "") for k, r, _ in fake_apis.requests if k == "anthropic"]
    assert all("server-side-fallback-2026-07-01" in h for h in headers)

    trend = json.loads((out / "trend_report.json").read_text(encoding="utf-8"))
    assert trend["method"].startswith("claude_web_search") and trend["sources"]
    post = json.loads((out / "post_content.json").read_text(encoding="utf-8"))
    assert post["items"][1]["text"] == "音読も試す価値あり"  # 未確認表現が置き換わった
    caption = (out / "caption.txt").read_text(encoding="utf-8")
    assert "プロフィールのリンク" in caption and settings.note_url in caption and "公式サイト" in caption
    assert json.loads((out / "layout_check.json").read_text(encoding="utf-8")) == {"cover": []}

    # キャラクター素材: 参照画像を作り、指定の表情を保存（次回以降は使い回し）
    assert (assets / "character/expressions/happy.png").exists()
    assert (assets / "character/reference/auto_reference.png").exists()

    fake_apis.requests.clear()
    settings.post_format = "feed"
    Pipeline(settings, topic="英単語").run()
    assert not [r for k, r, _ in fake_apis.requests if k == "openai"]  # 同じ表情は再生成しない
