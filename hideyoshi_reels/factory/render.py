"""Factory: 原稿とデザインから投稿画像（リール用1枚 / フィード1枚 / カルーセル複数枚）を作る。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from ..config import SIZES
from ..models import PostContent
from .canvas import TextBox
from .fonts import Fonts
from .layout_check import check_layout
from .templates import get_template
from .templates.base import new_canvas


@dataclass
class Slide:
    name: str
    image: Image.Image
    boxes: list[TextBox]
    issues: list[str] = field(default_factory=list)


def render_post(content: PostContent, style: str, post_format: str, sprite: Path | None, fonts: Fonts,
                handle: str = "", max_slides: int = 6) -> list[Slide]:
    template = get_template(style)
    size = SIZES[post_format]
    slides = []

    def make(name, fn):
        c = new_canvas(fonts, size)
        fn(c)
        template.watermark(c, handle, post_format)
        slides.append(Slide(name, c.image.convert("RGB"), c.boxes,
                            check_layout(c.boxes, post_format, size, fonts)))

    make("cover", lambda c: template.render_cover(c, content, sprite, post_format))
    if post_format == "carousel":
        n_detail = min(len(content.items), max(0, max_slides - 2))
        total = n_detail + 2
        for i in range(n_detail):
            make(f"detail_{i + 1}", lambda c, i=i: template.render_detail(c, content, i, total, sprite))
        make("closing", lambda c: template.render_closing(c, content, total, sprite))
    return slides


def contact_sheet(images: list[tuple[str, Image.Image]], fonts: Fonts, thumb_w: int = 360) -> Image.Image:
    """複数のプレビューを横に並べた一覧画像。"""
    from PIL import ImageDraw

    thumbs = [(label, img.resize((thumb_w, int(img.height * thumb_w / img.width)), Image.LANCZOS))
              for label, img in images]
    h = max(t.height for _, t in thumbs) + 70
    sheet = Image.new("RGB", (len(thumbs) * (thumb_w + 24) + 24, h + 24), "#f2f2f2")
    d = ImageDraw.Draw(sheet)
    font = fonts.get("black", 30)
    for i, (label, t) in enumerate(thumbs):
        x = 24 + i * (thumb_w + 24)
        d.text((x + thumb_w / 2, 36), label, font=font, fill="#222222", anchor="mm")
        sheet.paste(t, (x, 70))
    return sheet
