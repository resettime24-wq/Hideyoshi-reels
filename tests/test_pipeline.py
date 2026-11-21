"""モックモードで投稿を作るエンドツーエンドテスト。"""

import json
import shutil

import pytest

from hideyoshi_reels.history import History
from hideyoshi_reels.pipeline import Pipeline
from hideyoshi_reels.publishers.base import NotApprovedError, PostPackage
from hideyoshi_reels.publishers.instagram import InstagramPublisher
from hideyoshi_reels.utils import media_duration

COMMON = ("plan.json", "post_content.json", "trend_report.json", "design.json", "layout_check.json",
          "factcheck.json", "review_checklist.md", "monetization.json", "caption.txt", "hashtags.txt", "post.txt",
          "approval.json", "production_log.json", "run.log")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg が必要です")
def test_reel_end_to_end(settings):
    settings.post_format = "reel"
    result = Pipeline(settings).run()
    out = result.output_dir
    for name in COMMON + ("post_image.png", "reel.mp4"):
        assert (out / name).exists(), name
    assert abs(media_duration(out / "reel.mp4") - 10.0) < 0.1
    assert json.loads((out / "design.json").read_text(encoding="utf-8"))["size"] == [1080, 1920]
    assert json.loads((out / "layout_check.json").read_text(encoding="utf-8")) == {"cover": []}
    assert json.loads((out / "approval.json").read_text(encoding="utf-8"))["status"] == "pending"
    assert History(settings.history_path).entries[-1]["format"] == "reel"
    assert not list(settings.output_dir.glob("_running_*"))

    # 投稿パッケージは作れるが、承認前は投稿できない・自動投稿は未実装
    package = PostPackage.from_output_dir(out)
    assert package.media == [out / "reel.mp4"]
    with pytest.raises(NotApprovedError):
        InstagramPublisher().publish(package)
    package.approval_status = "approved"
    with pytest.raises(NotImplementedError):
        InstagramPublisher().publish(package)

    # 2本目は別の企画
    assert Pipeline(settings).run().title != result.title


def test_feed_and_carousel(settings):
    settings.post_format = "feed"
    feed = Pipeline(settings).run()
    assert feed.video_path is None and not (feed.output_dir / "reel.mp4").exists()
    from PIL import Image

    assert Image.open(feed.images[0]).size == (1080, 1350)

    settings.post_format = "carousel"
    settings.design_style = "D"
    car = Pipeline(settings, save_history=False).run()
    assert car.design == "D"
    slides = sorted((car.output_dir / "carousel").glob("slide_*.png"))
    assert len(slides) >= 4 and all(Image.open(p).size == (1080, 1350) for p in slides)
    assert PostPackage.from_output_dir(car.output_dir).media == slides


def test_preview_all_designs(settings):
    out = Pipeline(settings, topic="夏休み", save_history=False).preview(("reel", "feed"))
    for key in "ABCD":
        assert (out / f"{key}_reel.png").exists() and (out / f"{key}_feed.png").exists()
    assert (out / "compare_reel.png").exists() and (out / "compare_feed.png").exists()
    report = json.loads((out / "preview_report.json").read_text(encoding="utf-8"))
    assert report["auto_selected"] in "ABCD"
    assert all(not report["designs"][k][f]["issues"] for k in "ABCD" for f in ("reel", "feed"))
    assert not History(settings.history_path).entries  # プレビューは履歴に残さない


def test_invalid_format_rejected(settings):
    settings.post_format = "story"
    with pytest.raises(ValueError):
        Pipeline(settings)
