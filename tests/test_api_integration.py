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

from hideyoshi_reels.audio.tts import MockTTS
from hideyoshi_reels.images.mock_art import draw_background, draw_character
from hideyoshi_reels.pipeline import Pipeline

PLAN = {"candidates": [
    {"title": "早稲田志望の英単語の覚え方", "category": "科目別対策", "target": "高2", "hook": "単語、覚えても忘れる？",
     "value_points": ["毎日同じ範囲を回す", "音読で覚える", "週末にテスト"], "retention_device": "3つ目が最重要",
     "factual_claims": [], "keywords": ["英単語", "暗記", "音読"], "appeal_score": 8},
    {"title": "早稲田に受かる人の3つの共通点", "category": "合格者の特徴", "target": "高3", "hook": "x",
     "value_points": ["a", "b", "c"], "retention_device": "x", "factual_claims": [], "keywords": ["合格者", "共通点", "習慣"],
     "appeal_score": 10},
]}

SCENES = [
    ("hook", "おぬし、単語を覚えてもすぐ忘れておらぬか！", "surprised", "drum"),
    ("problem", "何度やっても覚えられぬ。それは覚え方に原因があるのじゃ。", "thinking", "boing"),
    ("explanation", "一つ目。毎日同じ範囲を何度も回すのじゃ。", "explaining", "pop"),
    ("explanation", "二つ目。声に出して読むと記憶に残りやすいと言われておる。", "happy", "pop"),
    ("explanation", "三つ目。週末に自分でテストをして、忘れた単語を洗い出すのじゃ。", "explaining", "ding"),
    ("conclusion", "忘れるのは当たり前じゃ。何度も会えば覚えられる。保存して毎日見返すのじゃ。", "happy", "sparkle"),
]
SCRIPT = {"title": "英単語の覚え方", "opening_phrase": "おぬし、", "closing_phrase": "保存して毎日見返すのじゃ。",
          "scenes": [{"section": s, "narration": n, "subtitle": n, "telop": "英単語の極意", "expression": e,
                      "image_prompt": "a desk", "sfx": x, "target_seconds": 5} for s, n, e, x in SCENES]}
CAPTION = {"caption": "単語、覚えても忘れてない？📚\n\n✔ 毎日回す\n✔ 音読\n✔ 週末テスト",
           "hashtags": ["#早稲田志望", "#英単語", "#大学受験", "#勉強法", "#受験生"]}
FACTCHECK_TEXT = ('調べた結果です。\n```json\n{"checks": [{"claim": "声に出して読むと記憶に残りやすいと言われておる", '
                  '"status": "unverified", "safe_wording": "声に出して読むのも一つの方法じゃ", "sources": [], "note": ""}]}\n```')


def _message(text):
    return {"id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 500}}


def _png_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class FakeServers:
    def __init__(self, tmp_path):
        self.requests = []
        self.tmp_path = tmp_path

    def anthropic(self, request: httpx.Request):
        body = json.loads(request.content)
        self.requests.append(("anthropic", request, body))
        if body.get("tools"):
            return httpx.Response(200, json=_message(FACTCHECK_TEXT))
        props = json.dumps(body["output_config"]["format"]["schema"])
        if '"candidates"' in props:
            return httpx.Response(200, json=_message(json.dumps(PLAN, ensure_ascii=False)))
        if '"scenes"' in props:
            return httpx.Response(200, json=_message(json.dumps(SCRIPT, ensure_ascii=False)))
        return httpx.Response(200, json=_message(json.dumps(CAPTION, ensure_ascii=False)))

    def openai(self, request: httpx.Request):
        self.requests.append(("openai", request, None))
        path = request.url.path
        if path.endswith("/audio/speech"):
            wav = MockTTS().synthesize(json.loads(request.content)["input"], self.tmp_path / "speech.wav")
            return httpx.Response(200, content=wav.read_bytes(), headers={"content-type": "audio/wav"})
        if path.endswith("/images/generations") and json.loads(request.content).get("background") == "opaque":
            img = draw_background("conclusion", (1024, 1536))
        else:
            img = draw_character("happy")
        return httpx.Response(200, json={"created": 0, "data": [{"b64_json": _png_b64(img)}]})


@pytest.fixture
def fake_apis(tmp_path, monkeypatch):
    import anthropic
    import openai

    servers = FakeServers(tmp_path)
    real_anthropic, real_openai = anthropic.Anthropic, openai.OpenAI
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: real_anthropic(
        **kw, http_client=httpx.Client(transport=httpx.MockTransport(servers.anthropic))))
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: real_openai(
        **kw, http_client=httpx.Client(transport=httpx.MockTransport(servers.openai))))
    return servers


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg が必要です")
def test_pipeline_with_real_provider_code(settings, fake_apis, tmp_path, project_root):
    # 本番モード（APIキーあり）に切り替え。素材は一時フォルダへ書き込む
    settings.mode = "auto"
    settings.strict = True  # モックへの切り替えを禁止して、本番コードが最後まで動くことを確認
    settings.anthropic_api_key = "sk-ant-test"
    settings.openai_api_key = "sk-test"
    settings.width, settings.height, settings.fps = 540, 960, 24
    assets = tmp_path / "assets"
    (assets / "character").mkdir(parents=True)
    shutil.copy(project_root / "assets/character/character.yaml", assets / "character/character.yaml")
    settings.assets_dir = assets

    result = Pipeline(settings, seed=1).run()

    # 履歴が空なので、自己評価スコアが最も高い案が採用される
    assert result.title == "早稲田に受かる人の3つの共通点"
    out = result.output_dir
    assert result.log["providers"] == {"llm": "claude (claude-opus-5-5)", "image": "openai",
                                       "background": "ai", "tts": "openai"}
    assert result.log["fallbacks"] == []

    # Claude へのリクエスト内容を確認
    calls = [b for kind, _, b in fake_apis.requests if kind == "anthropic"]
    assert all(b["model"] == "claude-opus-5-5" and b["fallbacks"] == "default" for b in calls)
    assert all(b["output_config"]["effort"] == "medium" for b in calls)
    assert any(b.get("tools", [{}])[0].get("type") == "web_search_20260209" for b in calls)
    headers = [r.headers.get("anthropic-beta", "") for k, r, _ in fake_apis.requests if k == "anthropic"]
    assert all("server-side-fallback-2026-07-01" in h for h in headers)

    # ファクトチェックで未確認表現が置き換わっている
    narration = (out / "narration.txt").read_text(encoding="utf-8")
    assert "声に出して読むのも一つの方法じゃ" in narration

    # 表情素材が生成・保存され、参照画像も作られている（次回以降は使い回し）
    assert len(list((assets / "character/expressions").glob("*.png"))) == 5
    assert (assets / "character/reference/auto_reference.png").exists()
    paths = [r.url.path for k, r, _ in fake_apis.requests if k == "openai"]
    assert paths.count("/v1/images/edits") == 4  # 2枚目以降は参照画像つき生成
    assert sum(p.endswith("/audio/speech") for p in paths) == len(SCENES)

    caption = (out / "caption.txt").read_text(encoding="utf-8")
    assert "公式サイト" in caption
    assert result.log["estimated_cost_jpy"]["jpy"] > 0

    # 2回目は表情素材を再生成しない
    fake_apis.requests.clear()
    Pipeline(settings, seed=2, topic="英単語").run()
    paths = [r.url.path for k, r, _ in fake_apis.requests if k == "openai"]
    assert "/v1/images/edits" not in paths
