"""モックモードで動画を1本作るエンドツーエンドテスト（FFmpeg が必要）。"""

import json
import shutil

import pytest

from hideyoshi_reels.history import History
from hideyoshi_reels.pipeline import Pipeline
from hideyoshi_reels.publishers.base import ReelPackage
from hideyoshi_reels.publishers.instagram import InstagramPublisher
from hideyoshi_reels.utils import media_duration

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg が必要です")


def test_end_to_end_mock(settings):
    settings.width, settings.height, settings.fps = 540, 960, 24
    result = Pipeline(settings, seed=42).run()
    out = result.output_dir

    for name in ("reel.mp4", "plan.json", "script.json", "timeline.json", "narration.txt", "caption.txt",
                 "hashtags.txt", "subtitles.srt", "factcheck.json", "review_checklist.md",
                 "production_log.json", "run.log"):
        assert (out / name).exists(), name
    assert len(list((out / "images").glob("scene_*.png"))) >= 5
    assert len(list((out / "images" / "character").glob("*.png"))) == 5
    assert not (out / "_work").exists()

    duration = media_duration(out / "reel.mp4")
    assert settings.min_seconds - 0.5 <= duration <= settings.max_seconds + 0.5

    timeline = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    assert timeline["scenes"][0]["start"] == 0
    assert timeline["duration"] == pytest.approx(duration, abs=0.3)
    cues = [c for s in timeline["scenes"] for c in s["cues"]]
    assert cues and all(c["start"] < c["end"] for c in cues)

    script = json.loads((out / "script.json").read_text(encoding="utf-8"))
    assert len(script["image_instructions"]) == len(script["scenes"])

    history = History(settings.history_path)
    assert history.entries[-1]["title"] == result.title

    # 2本目は別の企画になる
    result2 = Pipeline(settings, seed=7).run()
    assert result2.title != result.title

    # 投稿パッケージは作れるが、自動投稿は無効
    package = ReelPackage.from_output_dir(out)
    assert package.video_path.exists() and package.hashtags
    with pytest.raises(NotImplementedError):
        InstagramPublisher().publish(package)
