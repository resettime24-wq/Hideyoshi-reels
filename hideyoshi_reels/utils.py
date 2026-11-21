"""共通ユーティリティ。"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))
logger = logging.getLogger("hideyoshi_reels")


def now_jst() -> datetime:
    return datetime.now(JST)


def timestamp() -> str:
    return now_jst().strftime("%Y%m%d_%H%M%S")


def slugify(text: str, max_len: int = 24) -> str:
    """ファイル名に使える短い文字列へ変換（日本語はそのまま残す）。"""
    text = re.sub(r"[\\/:*?\"<>|\s　！？!?。、,.「」『』（）()【】#]+", "_", text)
    return text.strip("_")[:max_len] or "reel"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def setup_logging(log_file: Path | None = None, verbose: bool = False) -> None:
    root = logging.getLogger("hideyoshi_reels")
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)


def require_ffmpeg() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise RuntimeError(
                f"{tool} が見つかりません。README の『FFmpeg のインストール』を参照してください。"
            )


def run_cmd(cmd: list[str], desc: str = "") -> None:
    logger.debug("実行: %s", " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-25:])
        raise RuntimeError(f"コマンド失敗 ({desc or cmd[0]}):\n{tail}")


def media_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"長さを取得できません: {path}\n{proc.stderr}") from exc


FONT_CANDIDATES = [
    "assets/fonts",  # ユーザーが置いたフォントを最優先
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
]


def find_font(preferred: str = "", project_root: Path | None = None) -> str:
    """日本語が表示できるフォントを探す。"""
    if preferred and Path(preferred).exists():
        return preferred
    root = project_root or Path(__file__).resolve().parent.parent
    for cand in FONT_CANDIDATES:
        p = Path(cand)
        if not p.is_absolute():
            p = root / p
        if p.is_dir():
            fonts = sorted(list(p.glob("*.ttf")) + list(p.glob("*.otf")) + list(p.glob("*.ttc")))
            if fonts:
                return str(fonts[0])
        elif p.exists():
            return str(p)
    try:  # fontconfig で探す
        out = subprocess.run(["fc-list", ":lang=ja", "file"], capture_output=True, text=True).stdout
        files = [line.split(":")[0].strip() for line in out.splitlines() if line.strip()]
        files = [f for f in files if "Emoji" not in f]
        if files:
            bold = [f for f in files if "Bold" in f or "Black" in f]
            return (bold or files)[0]
    except FileNotFoundError:
        pass
    raise RuntimeError(
        "日本語フォントが見つかりません。assets/fonts/ に .ttf/.otf を置くか、"
        "Noto Sans CJK をインストールしてください（README 参照）。"
    )
