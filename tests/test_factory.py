"""Factory（デザインテンプレート A〜D・画像・10秒リール動画）のテスト。"""

import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from hideyoshi_reels.factory.canvas import Canvas, parse_emphasis
from hideyoshi_reels.factory.render import render_post
from hideyoshi_reels.factory.templates import TEMPLATES, choose_design, get_template
from hideyoshi_reels.factory.video import still_to_mp4
from hideyoshi_reels.images.character import CharacterManager
from hideyoshi_reels.images.mock_art import draw_character
from hideyoshi_reels.images.providers import MockImageProvider
from hideyoshi_reels.models import EXPRESSIONS, Plan, PostContent, PostItem

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg が必要です")


@pytest.fixture(scope="module")
def sprite(tmp_path_factory):
    path = tmp_path_factory.mktemp("sprite") / "explaining.png"
    draw_character("explaining").save(path)
    return path


def test_parse_emphasis():
    assert parse_emphasis("**過去問**を解く") == [("過去問", True), ("を解く", False)]
    assert parse_emphasis("強調なし") == [("強調なし", False)]


def test_four_templates_registered():
    assert sorted(TEMPLATES) == ["A", "B", "C", "D"]
    for t in TEMPLATES.values():
        assert t.name and t.description
    with pytest.raises(ValueError):
        get_template("E")


@pytest.mark.parametrize("fmt,size", [("reel", (1080, 1920)), ("feed", (1080, 1350))])
@pytest.mark.parametrize("style", ["A", "B", "C", "D"])
def test_all_mock_posts_fit_every_template(style, fmt, size, mock_contents, sprite, fonts):
    """全ネタ × 全デザインで、安全領域のはみ出し・文字の重なり・文字欠けが無いこと。"""
    for content in mock_contents:
        slides = render_post(content, style, fmt, sprite, fonts)
        assert len(slides) == 1
        assert slides[0].image.size == size
        assert slides[0].issues == [], f"{content.title_main}: {slides[0].issues}"
        # 日本語はプログラムで配置したテキストとして記録されている（AIに文字を描かせない）
        placed = "".join(b.text for b in slides[0].boxes)
        assert content.title_main.replace("**", "") in placed


@pytest.mark.parametrize("style", ["A", "B", "C", "D"])
def test_carousel_slides(style, mock_contents, sprite, fonts):
    content = mock_contents[3]  # 4項目のネタ
    slides = render_post(content, style, "carousel", sprite, fonts, max_slides=6)
    assert [s.name for s in slides] == ["cover", "detail_1", "detail_2", "detail_3", "detail_4", "closing"]
    assert all(s.image.size == (1080, 1350) for s in slides)
    assert all(s.issues == [] for s in slides), [s.issues for s in slides]
    limited = render_post(content, style, "carousel", sprite, fonts, max_slides=4)
    assert len(limited) == 4


def test_reel_text_avoids_instagram_ui(mock_contents, sprite, fonts):
    for style in "ABCD":
        slide = render_post(mock_contents[0], style, "reel", sprite, fonts)[0]
        for b in slide.boxes:
            x0, y0, x1, y1 = b.box
            assert y0 >= 244 and y1 <= 1586, (style, b.name)  # 上部ヘッダー・下部キャプション領域を避ける


def test_missing_glyph_detection(fonts):
    assert fonts.missing_glyphs("早稲田合格", "black") == set()
    assert fonts.missing_glyphs("\U000F0000", "black")  # 私用領域の文字は含まれない


def _content(**kw):
    base = dict(kicker="早稲田志望は**必見**", title_top="受験生の", title_main="勉強法",
                items=[PostItem(text="a"), PostItem(text="b"), PostItem(text="c")])
    base.update(kw)
    return PostContent(**base)


def _plan(category):
    return Plan(title="t", category=category, target="x", hook="h", value_points=["a"], retention_device="r",
                keywords=["k"], appeal_score=5, plan_id="p", created_at="now")


def test_auto_design_selection():
    assert choose_design(_content(title_main="NG勉強法", expression="angry"), _plan("やってはいけない勉強法"),
                         "reel")[0] == "A"
    assert choose_design(_content(title_main="共通点", badge="3選"), _plan("合格者の特徴"), "reel")[0] == "B"
    assert choose_design(_content(title_main="計画術", info_box={"label": "a", "value": "b"}), _plan("勉強計画"),
                         "feed")[0] == "C"
    items = [PostItem(text=t) for t in "abcd"]
    assert choose_design(_content(title_main="今すぐ", items=items, action_line="まずは1つ"), _plan("習慣"),
                         "reel")[0] == "D"
    # 手動指定が最優先
    assert choose_design(_content(), None, "reel", manual="B") == ("B", "手動指定", {})


def test_character_manager_mock(tmp_path, project_root):
    char_dir = tmp_path / "character"
    char_dir.mkdir()
    shutil.copy(project_root / "assets/character/character.yaml", char_dir / "character.yaml")
    manager = CharacterManager(char_dir, MockImageProvider())
    sprites = manager.ensure_all()
    assert set(sprites) == set(EXPRESSIONS) and all(p.exists() for p in sprites.values())


def test_registered_expression_has_priority(tmp_path, project_root):
    char_dir = tmp_path / "character"
    (char_dir / "expressions").mkdir(parents=True)
    shutil.copy(project_root / "assets/character/character.yaml", char_dir / "character.yaml")
    draw_character("happy").save(char_dir / "expressions" / "happy.png")
    manager = CharacterManager(char_dir, MockImageProvider())
    assert manager.sprite_path("happy") == char_dir / "expressions" / "happy.png"


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,nb_frames",
                          "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    import json

    return json.loads(out)


def _frame(path, select):
    raw = subprocess.run(["ffmpeg", "-v", "error", *select, "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).astype(np.float64)


@needs_ffmpeg
def test_still_to_mp4_spec(tmp_path, mock_contents, sprite, fonts):
    slide = render_post(mock_contents[0], "B", "reel", sprite, fonts)[0]
    img = tmp_path / "post.png"
    slide.image.save(img)
    out = still_to_mp4(img, tmp_path / "reel.mp4", seconds=10, fps=30)
    info = _probe(out)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p"
    assert (video["width"], video["height"]) == (1080, 1920)
    assert video["r_frame_rate"] == "30/1" and int(video["nb_frames"]) == 300
    assert abs(float(info["format"]["duration"]) - 10.0) < 0.1
    assert any(s["codec_type"] == "audio" for s in info["streams"])  # 無音トラック
    # 最初と最後のフレームが同じ絵（ズーム・切り替え等のアニメーションが無い）
    first, last = _frame(out, []), _frame(out, ["-sseof", "-0.1"])
    mse = np.mean((first - last) ** 2)
    psnr = 10 * np.log10(255 ** 2 / max(mse, 1e-9))
    assert psnr > 38, psnr
    original = np.asarray(Image.open(img).convert("RGB"), dtype=np.float64).ravel()
    # 元画像とほぼ同じ（色差はYUV 4:2:0 圧縮による誤差のみ）
    assert 10 * np.log10(255 ** 2 / max(np.mean((first - original) ** 2), 1e-9)) > 34


def test_canvas_records_text(fonts):
    c = Canvas(1080, 1350, fonts)
    box = c.rich_text("**保存**して見返す", (540, 600), "black", 60, "#000", "#c00")
    assert c.boxes[-1].text == "保存して見返す"
    assert box[2] - box[0] > 300
