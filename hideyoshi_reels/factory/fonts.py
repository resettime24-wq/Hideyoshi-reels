"""日本語フォントの管理。

日本語の文字は画像生成AIに描かせず、ここで選んだフォントでプログラムが正確に配置します。
役割（role）ごとにフォントを選びます:
  black … 見出し用の極太ゴシック（Noto Sans CJK JP Black）
  bold  … 本文・箇条書き用の太字ゴシック
  serif … 和風・迫力系の見出し用（Noto Serif CJK JP Black）
いずれも SIL Open Font License のフォントです（Ubuntu: apt install fonts-noto-cjk fonts-noto-cjk-extra）。
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from ..utils import find_font

logger = logging.getLogger(__name__)

NOTO_DIRS = ["/usr/share/fonts/opentype/noto", "/usr/share/fonts/noto-cjk", "/usr/share/fonts/truetype/noto",
             "/opt/homebrew/share/fonts", str(Path.home() / "Library/Fonts"), "/Library/Fonts"]
CANDIDATES = {
    "black": ["NotoSansCJK-Black.ttc", "NotoSansCJKjp-Black.otf", "NotoSansJP-Black.ttf", "NotoSansCJK-Bold.ttc",
              "NotoSansCJKjp-Bold.otf", "NotoSansJP-Bold.ttf"],
    "bold": ["NotoSansCJK-Bold.ttc", "NotoSansCJKjp-Bold.otf", "NotoSansJP-Bold.ttf", "NotoSansCJK-Black.ttc"],
    "serif": ["NotoSerifCJK-Black.ttc", "NotoSerifCJKjp-Black.otf", "NotoSerifJP-Black.otf", "NotoSerifCJK-Bold.ttc",
              "NotoSerifCJKjp-Bold.otf", "NotoSansCJK-Black.ttc"],
}


class Fonts:
    def __init__(self, preferred: str = "", project_root: Path | None = None):
        self.paths: dict[str, str] = {}
        self.fake_bold: dict[str, bool] = {}
        user_dir = (project_root or Path(__file__).resolve().parents[2]) / "assets" / "fonts"
        fallback = find_font(preferred)
        for role, names in CANDIDATES.items():
            path = self._find(role, names, user_dir)
            self.paths[role] = path or fallback
            # 太字フォントが無い環境では、縁取りで擬似的に太くする
            self.fake_bold[role] = path is None
        if any(self.fake_bold.values()):
            logger.warning("太字の日本語フォントが見つからないため代替フォントを使います（README『フォント』参照）: %s",
                           fallback)

    @staticmethod
    def _find(role: str, names: list[str], user_dir: Path) -> str | None:
        # ユーザーが assets/fonts/<role>.ttf などを置いた場合は最優先
        for ext in (".ttf", ".otf", ".ttc"):
            p = user_dir / f"{role}{ext}"
            if p.exists():
                return str(p)
        for name in names:
            for d in NOTO_DIRS:
                p = Path(d) / name
                if p.exists():
                    return str(p)
        return None

    def get(self, role: str, size: int) -> ImageFont.FreeTypeFont:
        return _load(self.paths[role], max(8, int(size)))

    def missing_glyphs(self, text: str, role: str) -> set[str]:
        """フォントに含まれない文字（豆腐になる文字）を返す。"""
        cmap = _cmap(self.paths[role])
        if cmap is None:
            return set()
        return {ch for ch in text if not ch.isspace() and ord(ch) not in cmap}


@lru_cache(maxsize=256)
def _load(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=0)


@lru_cache(maxsize=8)
def _cmap(path: str):
    try:
        from fontTools.ttLib import TTFont
    except ImportError:  # pragma: no cover
        return None
    font = TTFont(path, fontNumber=0, lazy=True)
    return set(font.getBestCmap().keys())
