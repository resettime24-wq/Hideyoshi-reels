"""デザインテンプレートの共通部分。

- 1080px幅を基準に設計し、縦の要素を Flow で並べることで
  リール（1080×1920）とフィード（1080×1350）の両方に同じテンプレートで対応する
- リールは Instagram の画面UI（上部ヘッダー・下部キャプション・右側ボタン）と重ならない
  安全領域の中だけに文字を置く
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw

from ...models import PostContent, PostItem
from .. import decor
from ..canvas import Canvas, plain

# 安全領域（1080×1920 基準の座標）
REEL_SAFE = (60, 250, 1020, 1580)  # この中に文字を置く
REEL_RIGHT_UI = (930, 1000, 1080, 1920)  # 右側のいいね・コメントボタン付近
FEED_MARGIN = 48


def safe_area(fmt: str, width: int, height: int) -> tuple[int, int, int, int]:
    k = width / 1080
    if fmt == "reel":
        return tuple(int(v * k) for v in REEL_SAFE)
    m = int(FEED_MARGIN * k)
    return (m, m, width - m, height - m)


@dataclass
class Block:
    name: str
    height: float  # 1080幅基準の高さ
    draw: Callable[[Canvas, tuple[int, int, int, int], float], None]
    x0: float | None = None
    x1: float | None = None
    gap: float = 18


def flow(c: Canvas, blocks: list[Block], area: tuple[int, int, int, int], max_extra_gap: float = 40
         ) -> tuple[dict[str, tuple[int, int, int, int]], float]:
    """ブロックを上から並べる。入りきらない場合は全体を縮小する。"""
    ax0, ay0, ax1, ay1 = area
    avail = ay1 - ay0
    nominal = sum(c.u(b.height) for b in blocks) + sum(c.u(b.gap) for b in blocks[:-1])
    scale = min(1.0, avail / max(1, nominal))
    used = nominal * scale
    extra = 0.0
    if scale == 1.0 and len(blocks) > 1:  # 余白があれば行間を少し広げ、残りは上下中央寄せ
        extra = min(c.u(max_extra_gap), (avail - used) / (len(blocks) - 1))
        used += extra * (len(blocks) - 1)
    y = ay0 + (avail - used) / 2
    boxes = {}
    for b in blocks:
        h = c.u(b.height) * scale
        x0 = c.u(b.x0) if b.x0 is not None else ax0
        x1 = c.u(b.x1) if b.x1 is not None else ax1
        box = (int(x0), int(y), int(x1), int(y + h))
        b.draw(c, box, scale)
        boxes[b.name] = box
        y += h + c.u(b.gap) * scale + extra
    return boxes, scale


def place_sprite(c: Canvas, sprite_path: Path | None, box, anchor: str = "bottom", shadow: bool = True,
                 flip: bool = False) -> tuple[int, int, int, int] | None:
    if not sprite_path:
        return None
    sprite = Image.open(sprite_path).convert("RGBA")
    if flip:
        sprite = sprite.transpose(Image.FLIP_LEFT_RIGHT)
    x0, y0, x1, y1 = (int(v) for v in box)
    k = min((x1 - x0) / sprite.width, (y1 - y0) / sprite.height)
    sprite = sprite.resize((max(1, int(sprite.width * k)), max(1, int(sprite.height * k))), Image.LANCZOS)
    px = x0 + ((x1 - x0) - sprite.width) // 2
    py = y1 - sprite.height if anchor == "bottom" else y0 + ((y1 - y0) - sprite.height) // 2
    if shadow:
        lay = c.layer()
        alpha = sprite.getchannel("A").point(lambda a: int(a * 0.45))
        black = Image.new("RGBA", sprite.size, (0, 0, 0, 255))
        black.putalpha(alpha)
        lay.alpha_composite(black, (px + c.u(10), py + c.u(14)))
        c.blur_paste(lay, c.u(10))
    c.paste(sprite, (px, py))
    return (px, py, px + sprite.width, py + sprite.height)


def emphasize_first(text: str, word: str = "保存") -> str:
    if "**" in text or word not in text:
        return text
    return text.replace(word, f"**{word}**", 1)


@dataclass
class Palette:
    text: str
    emph: str
    accent: str
    panel_fill: object
    panel_border: str
    heading_fill: object
    heading_strokes: list = field(default_factory=list)  # [(1080基準の太さ, 色)]
    heading_role: str = "black"
    sub: str = "#555555"
    highlight: object = None
    icon_ink: str = "#3a2a20"
    icon_paper: str = "#ffffff"


class Template:
    key = "?"
    name = ""
    description = ""
    best_for = ""
    palette: Palette

    # ----- サブクラスで実装 -----
    def background(self, c: Canvas, fmt: str) -> None:
        raise NotImplementedError

    def render_cover(self, c: Canvas, content: PostContent, sprite: Path | None, fmt: str) -> None:
        raise NotImplementedError

    # ----- 共通ヘルパー -----
    def strokes(self, c: Canvas, scale: float = 1.0):
        return [(max(1, int(c.u(w) * scale)), col) for w, col in self.palette.heading_strokes]

    def heading(self, c: Canvas, text: str, box, scale: float = 1.0, max_ratio: float = 0.8, name="heading") -> None:
        x0, y0, x1, y1 = box
        p = self.palette
        size = c.fit(plain(text), p.heading_role, (x1 - x0) * 0.94, int((y1 - y0) * max_ratio))
        c.display_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), p.heading_role, size, p.heading_fill,
                       strokes=self.strokes(c, size / 150), name=name)

    def watermark(self, c: Canvas, handle: str, fmt: str) -> None:
        """アカウント名は Instagram 側に表示されるため、画像には入れない（デザインの邪魔をしない）。"""
        return

    def cta_pill(self, c: Canvas, text: str, box, name: str) -> None:
        """どの背景色でも読めるよう、パネル色の帯の上に文字を置く。"""
        p = self.palette
        x0, y0, x1, y1 = box
        decor.framed_box(c, box, p.panel_fill, p.panel_border, max(2, c.u(4)), (y1 - y0) // 2, shadow=False)
        size = c.fit(text, "black", (x1 - x0) * 0.86, int((y1 - y0) * 0.5), 20)
        c.rich_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), "black", size, p.text, p.emph, name=name)

    # ----- カルーセルの詳細ページ（全テンプレート共通の構成。配色・背景はテンプレートごと） -----
    def render_detail(self, c: Canvas, content: PostContent, index: int, total: int, sprite: Path | None) -> None:
        p = self.palette
        self.background(c, "detail")
        item: PostItem = content.items[index]
        x0, y0, x1, y1 = safe_area("carousel", c.width, c.height)
        c.rich_text(plain(content.kicker), (x0, y0 + c.u(30)), "bold", c.u(34), p.text, align="left", name="kicker")
        c.rich_text(f"{index + 2} / {total}", (x1, y0 + c.u(30)), "bold", c.u(34), p.text, align="right", name="page")
        cy = y0 + c.u(170)
        r = c.u(70)
        decor.number_badge(c, (x0 + r, cy), r, str(index + 1), p.accent, "#ffffff")
        size = c.fit(item.text, "black", x1 - x0 - r * 2 - c.u(40), c.u(78), c.u(40))
        lines = c.wrap(item.text, "black", size, x1 - x0 - r * 2 - c.u(40))
        for k, line in enumerate(lines[:2]):
            c.rich_text(line, (x0 + r * 2 + c.u(30), cy + (k - (len(lines[:2]) - 1) / 2) * size * 1.3), "black", size,
                        p.text, p.emph, align="left", name=f"item_title_{k}")
        panel = (x0, cy + c.u(140), x1, y1 - c.u(320))
        decor.framed_box(c, panel, p.panel_fill, p.panel_border, c.u(6), c.u(28))
        icon_s = c.u(150)
        decor.icon(c, item.icon, (panel[2] - icon_s - c.u(30), panel[1] + c.u(30), panel[2] - c.u(30),
                                  panel[1] + c.u(30) + icon_s), ink=p.icon_ink, accent=p.accent, paper=p.icon_paper)
        detail = item.detail or plain(item.text)
        c.paragraph(detail, (panel[0] + c.u(50), panel[1] + c.u(210), panel[2] - c.u(50), panel[3] - c.u(40)),
                    "bold", c.u(58), p.text, p.emph, line_gap=1.6, name="detail")
        place_sprite(c, sprite, (x1 - c.u(280), y1 - c.u(290), x1, y1 + c.u(10)))
        self.cta_pill(c, emphasize_first(content.save_cta), (x0, y1 - c.u(190), x1 - c.u(300), y1 - c.u(90)), "save")

    def render_closing(self, c: Canvas, content: PostContent, total: int, sprite: Path | None) -> None:
        p = self.palette
        self.background(c, "detail")
        x0, y0, x1, y1 = safe_area("carousel", c.width, c.height)
        c.rich_text(f"{total} / {total}", (x1, y0 + c.u(30)), "bold", c.u(34), p.text, align="right", name="page")
        self.heading(c, "まとめ", (x0, y0 + c.u(60), x1, y0 + c.u(240)), max_ratio=0.75, name="summary_heading")
        panel = (x0, y0 + c.u(280), x1, y1 - c.u(320))
        decor.framed_box(c, panel, p.panel_fill, p.panel_border, c.u(6), c.u(28))
        n = len(content.items)
        row_h = (panel[3] - panel[1] - c.u(60)) / n
        for k, item in enumerate(content.items):
            cy = panel[1] + c.u(30) + row_h * (k + 0.5)
            s = c.u(64)
            decor.checkbox(c, (panel[0] + c.u(40), cy - s / 2, panel[0] + c.u(40) + s, cy + s / 2), p.panel_border,
                           check_color=p.accent)
            size = c.fit(item.text, "bold", panel[2] - panel[0] - c.u(180), c.u(56), c.u(30))
            c.rich_text(item.text, (panel[0] + c.u(140), cy), "bold", size, p.text, p.emph, align="left",
                        name=f"summary_{k}")
        place_sprite(c, sprite, (x1 - c.u(280), y1 - c.u(290), x1, y1 + c.u(10)))
        self.cta_pill(c, content.caption_cta, (x0, y1 - c.u(290), x1 - c.u(300), y1 - c.u(200)), "caption_cta")
        self.cta_pill(c, emphasize_first(content.save_cta), (x0, y1 - c.u(180), x1 - c.u(300), y1 - c.u(90)), "save")


def draw_item_text(c: Canvas, text: str, box, role: str, color, emph, max_size: int, min_size: int = 26,
                   highlight=None, name="item", two_lines: bool = True) -> None:
    """箇条書き1項目を枠内に収める（1行で入らなければ2行に折り返す）。"""
    x0, y0, x1, y1 = box
    width = x1 - x0
    size = c.fit(text, role, width, max_size, min_size)
    if two_lines and size < max_size * 0.78:
        size2 = int(min(max_size * 0.92, (y1 - y0) / 2.5))
        lines = c.wrap(text, role, size2, width)
        if len(lines) == 2:
            for k, line in enumerate(lines):
                c.rich_text(line, (x0, (y0 + y1) / 2 + (k - 0.5) * size2 * 1.22), role, size2, color, emph,
                            align="left", highlight=highlight, name=f"{name}_{k}")
            return
    c.rich_text(text, (x0, (y0 + y1) / 2), role, size, color, emph, align="left", highlight=highlight, name=name)


def new_canvas(fonts, size, fill=(255, 255, 255, 255)) -> Canvas:
    c = Canvas(size[0], size[1], fonts)
    ImageDraw.Draw(c.image).rectangle([0, 0, size[0], size[1]], fill=fill)
    return c
