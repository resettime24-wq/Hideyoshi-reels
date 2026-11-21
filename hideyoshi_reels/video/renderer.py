"""FFmpeg による動画レンダリング。"""

from __future__ import annotations

import logging
from pathlib import Path

from ..models import Timeline, TimelineScene
from ..utils import run_cmd

logger = logging.getLogger(__name__)

MOTIONS = ("punch", "zoom_in", "zoom_out")


def zoom_expr(motion: str, frames: int, fps: int) -> str:
    n = max(frames - 1, 1)
    if motion == "punch":  # 冒頭: 寄りから素早く引いて勢いを出す
        return f"if(lt(on,{int(fps * 0.35)}),1.14-0.12*on/{int(fps * 0.35)},1.02+0.03*(on-{int(fps * 0.35)})/{n})"
    if motion == "zoom_out":
        return f"1.08-0.07*on/{n}"
    return f"1.01+0.07*on/{n}"


def render_scene(scene: TimelineScene, subtitle_images: list[tuple[Path, float, float]],
                 out_path: Path, width: int, height: int, fps: int) -> Path:
    duration = scene.end - scene.start
    frames = round(duration * fps)
    pre_w = int(width * 1.25) // 2 * 2
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps),
           "-t", f"{duration:.3f}", "-i", scene.image]
    for img, _, _ in subtitle_images:
        cmd += ["-i", str(img)]
    z = zoom_expr(scene.motion, frames, fps)
    graph = [f"[0:v]scale={pre_w}:-2,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
             f":d=1:s={width}x{height}:fps={fps},setsar=1[v0]"]
    for i, (_, start, end) in enumerate(subtitle_images, 1):
        graph.append(f"[v{i - 1}][{i}:v]overlay=0:0:enable='between(t,{start:.3f},{end:.3f})'[v{i}]")
    last = f"[v{len(subtitle_images)}]"
    cmd += ["-filter_complex", ";".join(graph), "-map", last, "-frames:v", str(frames),
            "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(out_path)]
    run_cmd(cmd, f"場面{scene.index + 1}の動画化")
    return out_path


def concat_and_mux(scene_videos: list[Path], audio: Path, out_path: Path, work_dir: Path) -> Path:
    list_file = work_dir / "concat.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in scene_videos), encoding="utf-8")
    silent = work_dir / "video_silent.mp4"
    run_cmd(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(list_file),
             "-c", "copy", str(silent)], "場面の結合")
    run_cmd(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(audio),
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-ar", "44100", "-shortest", "-movflags", "+faststart", str(out_path)], "音声の合成")
    return out_path


def render_video(timeline: Timeline, subtitle_map: dict[int, list[tuple[Path, float, float]]],
                 audio: Path, out_path: Path, work_dir: Path) -> Path:
    clips = []
    for scene in timeline.scenes:
        clip = work_dir / f"scene_{scene.index + 1:02d}.mp4"
        logger.info("場面 %d/%d をレンダリング中（%.1f秒, %s）", scene.index + 1, len(timeline.scenes),
                    scene.end - scene.start, scene.motion)
        render_scene(scene, subtitle_map.get(scene.index, []), clip, timeline.width, timeline.height, timeline.fps)
        clips.append(clip)
    return concat_and_mux(clips, audio, out_path, work_dir)
