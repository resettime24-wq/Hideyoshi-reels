"""テンプレートB: 赤 × 金のランキング（〇選・共通点）。キャラクターを大きく配置。"""

from __future__ import annotations

from ... import models
from .. import decor
from ..canvas import plain
from .base import Block, Palette, Template, draw_item_text, emphasize_first, flow, place_sprite, safe_area

GOLD = ["#fff3b8", "#f6cd4a", "#c88d17", "#f9dc7a"]
RED = ["#ef2b3c", "#c8102e", "#8e0b1f"]


class RedGoldTemplate(Template):
    key = "B"
    name = "赤×金 ランキング"
    description = "赤と金の和風ランキング。番号つきボックスとキャラクターで、ひと目で要点をつかませる"
    best_for = "〇選・共通点・ランキング・比較"
    palette = Palette(text="#1d1412", emph="#c8102e", accent="#a3121f", panel_fill="#fffaf0",
                      panel_border="#d9a93a", heading_fill=RED, heading_strokes=[(16, "#ffffff")],
                      heading_role="black", sub="#fff3e0", icon_ink="#3a2a20", icon_paper="#ffffff")

    def background(self, c, fmt):
        decor.fill_gradient(c, [(0.0, "#fff4e6"), (0.3, "#f6d2cc"), (0.5, "#b9283a"), (0.75, "#8a1020"),
                                (1.0, "#5a0812")])
        lay_rays = c.layer()
        from PIL import ImageDraw

        d = ImageDraw.Draw(lay_rays)
        for k in range(7):  # 左上から差し込む光
            d.polygon([(0, 0), (c.width * (0.25 + k * 0.14), c.height * 0.55),
                       (c.width * (0.32 + k * 0.14), c.height * 0.55)], fill=(255, 255, 255, 40))
        c.paste(lay_rays)
        decor.seigaiha(c, (0, int(c.height * 0.5), c.width, c.height), "#f2c14e", alpha=45)
        decor.petals(c, (0, 0, int(c.width * 0.35), int(c.height * 0.22)), n=18, seed=8)
        decor.particles(c, (0, int(c.height * 0.45), c.width, c.height), "#ffd76a", n=60, seed=6)

    def render_cover(self, c, content: models.PostContent, sprite, fmt):
        self.background(c, fmt)
        area = safe_area(fmt, c.width, c.height)
        box_x1 = 690
        blocks = [Block("kicker", 115, lambda cv, b, s: self._kicker(cv, b, content.kicker), x0=170, x1=910)]
        if content.title_top:
            blocks.append(Block("title_top", 150, lambda cv, b, s: self._title(cv, content.title_top, b, RED, 0.8)))
        blocks.append(Block("title_main", 170, lambda cv, b, s: self._title(cv, content.title_main, b, "#1a1414", 0.82,
                                                                            brush=True), gap=6))
        if content.title_bottom:
            blocks.append(Block("title_bottom", 115, lambda cv, b, s: self._title(cv, content.title_bottom, b,
                                                                                  "#1a1414", 0.75)))
        if content.badge:
            blocks.append(Block("badge", 245, lambda cv, b, s: self._badge(cv, content.badge, b), x0=200, x1=880))
        for k, item in enumerate(content.items):
            blocks.append(Block(f"item_{k}", 132, lambda cv, b, s, k=k, item=item: self._item(cv, k, item, b),
                                x1=box_x1, gap=16))
        blocks.append(Block("save", 112, lambda cv, b, s: self._save(cv, content.save_cta, b), x0=90, x1=990))
        boxes, _ = flow(c, blocks, area, max_extra_gap=26)
        first = boxes["item_0"]
        place_sprite(c, sprite, (c.u(640), first[1] - c.u(150), c.width + c.u(40), boxes["save"][1] + c.u(30)))

    def _kicker(self, c, box, text):
        x0, y0, x1, y1 = box
        decor.brush_band(c, box, "#16100e", seed=4)
        h = y1 - y0
        decor.laurel(c, (x0 + h * 0.45, (y0 + y1) / 2), h * 0.75, "#e6b84a")
        decor.laurel(c, (x1 - h * 0.45, (y0 + y1) / 2), h * 0.75, "#e6b84a", mirror=True)
        size = c.fit(text, "black", (x1 - x0) - h * 2, int(h * 0.52), 22)
        c.rich_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), "black", size, "#ffffff", "#f6cd4a", name="kicker")

    def _title(self, c, text, box, fill, ratio, brush=False):
        x0, y0, x1, y1 = box
        size = c.fit(plain(text), "black", (x1 - x0) * 0.88, int((y1 - y0) * ratio), 30)
        if brush:  # 金の筆ストロークを文字の下半分に
            w = c.text_width(plain(text), "black", size)
            cx = (x0 + x1) / 2
            decor.brush_band(c, (int(cx - w / 2 - c.u(30)), int(y0 + (y1 - y0) * 0.55), int(cx + w / 2 + c.u(30)),
                                 int(y1 + (y1 - y0) * 0.05)), "#f0c040", seed=7, alpha=230)
        k = size / 150
        c.display_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), "black", size, fill,
                       strokes=[(max(2, int(c.u(17) * k)), "#ffffff")],
                       shadow=(c.u(5), c.u(8), "#4a0a10", c.u(6)), name="title")

    def _badge(self, c, text, box):
        x0, y0, x1, y1 = box
        decor.brush_band(c, (x0, int(y0 + (y1 - y0) * 0.12), x1, int(y1 - (y1 - y0) * 0.05)), "#7e0c18", seed=9,
                         roughness=0.3)
        size = c.fit(plain(text), "serif", (x1 - x0) * 0.8, int((y1 - y0) * 0.86), 30)
        k = size / 150
        bx = c.display_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), "serif", size, GOLD,
                            strokes=[(max(2, int(c.u(14) * k)), "#3d0508"), (max(1, int(c.u(5) * k)), "#fff1b8")],
                            shadow=(c.u(6), c.u(10), "#2a0306", c.u(8)), name="badge")
        decor.burst_lines(c, (bx[0] - c.u(10), (bx[1] + bx[3]) / 2), c.u(90), "#f6cd4a", angle=200, spread=60)

    def _item(self, c, k, item: models.PostItem, box):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.framed_box(c, box, "#fffaf0", "#d9a93a", max(2, c.u(5)), int(h * 0.16))
        r = h * 0.3
        decor.number_badge(c, (x0 + h * 0.48, (y0 + y1) / 2), int(r), str(k + 1), "#a3121f", "#ffffff")
        ic = h * 0.62
        decor.icon(c, item.icon, (x1 - ic - h * 0.18, y0 + (h - ic) / 2, x1 - h * 0.18, y0 + (h + ic) / 2),
                   accent="#c8102e")
        draw_item_text(c, item.text, (x0 + h * 0.95, y0 + h * 0.08, x1 - ic - h * 0.3, y1 - h * 0.08), "black",
                       "#1d1412", "#c8102e", int(h * 0.36), name=f"item_{k}")

    def _save(self, c, text, box):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.brush_band(c, box, "#f1c64e", seed=12, roughness=0.15)
        decor.bookmark(c, (int(x0 + h * 0.35), int(y0 + h * 0.18), int(x0 + h * 0.35 + h * 0.6), int(y1 - h * 0.18)),
                       "#b0141f")
        size = c.fit(text, "black", (x1 - x0) - h * 1.6, int(h * 0.5), 22)
        c.rich_text(emphasize_first(text), ((x0 + x1) / 2 + h * 0.35, (y0 + y1) / 2), "black", size, "#3a0a0a",
                    "#b0141f", name="save")
