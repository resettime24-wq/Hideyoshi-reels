"""リール用: 静止画像1枚を指定秒数そのまま表示するMP4に変換する。

画像の切り替え・スライドショー・ズーム・パンなどのアニメーションは一切行いません。
"""

from __future__ import annotations

from pathlib import Path

from ..utils import media_duration, require_ffmpeg, run_cmd


def still_to_mp4(image: Path, out: Path, seconds: float = 10.0, fps: int = 30, silent_audio: bool = True) -> Path:
    """1080×1920 の静止画 → H.264 / yuv420p / 30fps / 約10秒の MP4（無音の音声トラック付き）。"""
    require_ffmpeg()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps), "-i", str(image)]
    if silent_audio:  # 音声トラックが無いと一部のアップロードで扱いにくいため無音を入れる
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += ["-t", f"{seconds:.3f}", "-frames:v", str(int(round(seconds * fps))), "-r", str(fps),
            # スマホは HD 動画を BT.709 として表示するため、BT.709 で変換して色情報も付ける（色ズレ防止）
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2:out_color_matrix=bt709:out_range=tv,format=yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", "18", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-movflags", "+faststart"]
    if silent_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd.append(str(out))
    run_cmd(cmd, "静止画からMP4への変換")
    duration = media_duration(out)
    if abs(duration - seconds) > 0.5:
        raise RuntimeError(f"MP4の長さが想定と違います: {duration:.2f}秒")
    return out
