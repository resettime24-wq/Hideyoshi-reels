import numpy as np
import pytest
from PIL import ImageFont

from hideyoshi_reels.audio import sfx
from hideyoshi_reels.audio.tts import MockTTS
from hideyoshi_reels.audio.wav import SAMPLE_RATE, read_wav
from hideyoshi_reels.images.character import CharacterManager
from hideyoshi_reels.images.compose import SceneComposer, wrap_japanese
from hideyoshi_reels.images.mock_art import draw_background, draw_character
from hideyoshi_reels.images.providers import MockImageProvider
from hideyoshi_reels.models import EXPRESSIONS
from hideyoshi_reels.utils import find_font
from hideyoshi_reels.video.subtitles import split_subtitle, time_cues, to_srt


def test_all_expressions_draw():
    for expr in EXPRESSIONS:
        img = draw_character(expr)
        assert img.mode == "RGBA"
        alpha = np.array(img.getchannel("A"))
        assert alpha[0, 0] == 0  # 背景は透過
        assert (alpha > 0).mean() > 0.2  # キャラがしっかり描かれている


def test_character_manager_mock(tmp_path, project_root):
    import shutil

    char_dir = tmp_path / "character"
    char_dir.mkdir()
    shutil.copy(project_root / "assets/character/character.yaml", char_dir / "character.yaml")
    manager = CharacterManager(char_dir, MockImageProvider())
    sprites = manager.ensure_all()
    assert set(sprites) == set(EXPRESSIONS)
    assert all(p.exists() and p.parent.name == "mock" for p in sprites.values())


def test_registered_expression_has_priority(tmp_path, project_root):
    import shutil

    char_dir = tmp_path / "character"
    (char_dir / "expressions").mkdir(parents=True)
    shutil.copy(project_root / "assets/character/character.yaml", char_dir / "character.yaml")
    draw_character("happy").save(char_dir / "expressions" / "happy.png")
    manager = CharacterManager(char_dir, MockImageProvider())
    assert manager.sprite_path("happy") == char_dir / "expressions" / "happy.png"


def test_backgrounds():
    for section in ("hook", "problem", "explanation", "conclusion"):
        assert draw_background(section, size=(270, 480)).size == (270, 480)


def test_wrap_japanese_kinsoku():
    font = ImageFont.truetype(find_font(), 40)
    lines = wrap_japanese("受かる者は過去問を早めに解いて、敵の正体を知る。", font, 400)
    assert all(not line.startswith(("、", "。")) for line in lines)
    assert "".join(lines) == "受かる者は過去問を早めに解いて、敵の正体を知る。"


def test_split_and_time_cues():
    text = "まず一つ目。受かる者は過去問を早めに解いて、敵の正体を先に知っておるのじゃ。"
    chunks = split_subtitle(text)
    assert "".join(chunks) == text
    assert all(len(c) <= 26 for c in chunks)
    cues = time_cues(text, 0.1, 4.1)
    assert cues[0].start == pytest.approx(0.1) and cues[-1].end == pytest.approx(4.1)
    assert all(a.end <= b.start + 1e-6 for a, b in zip(cues, cues[1:]))
    srt = to_srt(cues)
    assert "00:00:00,100 -->" in srt


def test_mock_tts_duration(tmp_path):
    out = MockTTS().synthesize("受験生よ、聞くのじゃ。", tmp_path / "a.wav")
    dur = len(read_wav(out)) / SAMPLE_RATE
    assert 1.0 < dur < 3.0


def test_sfx_and_bgm():
    for name in sfx.SFX:
        snd = sfx.make_sfx(name)
        assert snd is not None and len(snd) > 0 and np.max(np.abs(snd)) <= 1.5
    assert sfx.make_sfx("none") is None
    bgm = sfx.make_bgm(5.0)
    assert len(bgm) == 5 * SAMPLE_RATE


def test_scene_composer(tmp_path, project_root):
    composer = SceneComposer(540, 960, find_font(), "@test", MockImageProvider(), "procedural")
    sprite = tmp_path / "s.png"
    draw_character("explaining").save(sprite)
    out = composer.compose_scene("hook", "x", sprite, "受かる人の共通点", tmp_path / "scene.png")
    sub = composer.subtitle_overlay("おぬし、受かる人は実はここが違うのじゃ！", tmp_path / "sub.png")
    from PIL import Image

    assert Image.open(out).size == (540, 960)
    assert Image.open(sub).mode == "RGBA"


def test_voicevox_requests(tmp_path, monkeypatch):
    import requests

    from hideyoshi_reels.audio.tts import VoicevoxTTS

    calls = []
    wav_bytes = MockTTS().synthesize("テスト", tmp_path / "v.wav").read_bytes()

    class Resp:
        def __init__(self, data=None, content=b""):
            self._data, self.content = data, content

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append((url, params, json))
        return Resp({"speedScale": 1.0}) if url.endswith("/audio_query") else Resp(content=wav_bytes)

    monkeypatch.setattr(requests, "post", fake_post)
    tts = VoicevoxTTS("http://localhost:50021", 13, "VOICEVOX:青山龍星")
    out = tts.synthesize("おぬし", tmp_path / "out.wav")
    assert out.read_bytes() == wav_bytes
    assert calls[0][1] == {"text": "おぬし", "speaker": 13}
    assert calls[1][2]["speedScale"] == 1.1
