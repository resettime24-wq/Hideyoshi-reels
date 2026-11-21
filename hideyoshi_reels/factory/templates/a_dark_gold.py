"""テンプレートA: 黒地 × 金の輝き × 赤い大見出し（強いフック・危機感・完全版）。"""

from __future__ import annotations

from ... import models
from .. import decor
from ..canvas import plain
from .base import Block, Palette, Template, draw_item_text, emphasize_first, flow, place_sprite, safe_area

GOLD = ["#fff6c9", "#f7d25c", "#d29a22", "#fbe08a"]
RED = ["#ff7a5c", "#e3261f", "#9c0f0f", "#5e0606"]
SILVER = ["#ffffff", "#e6e6e6", "#a6a6a6", "#f2f2f2"]


class DarkGoldTemplate(Template):
    key = "A"
    name = "黒×金 強フック"
    description = "黒地に金の輝き、赤い立体見出し。危機感・注目喚起・『完全版』系の1枚リール向き"
    best_for = "NG行動・逆転・保存必須・完全版"
    palette = Palette(text="#ffffff", emph="#f7d25c", accent="#c4161c", panel_fill=(14, 10, 8, 225),
                      panel_border="#d4a63a", heading_fill=GOLD, heading_strokes=[(14, "#140904"), (6, "#6b4510")],
                      heading_role="serif", sub="#f3e6c4", icon_ink="#f3e6c4", icon_paper="#2a1d12")

    def background(self, c, fmt):
        decor.fill_gradient(c, [(0.0, "#140d08"), (0.45, "#20140b"), (1.0, "#060404")])
        decor.radial_glow(c, (c.width * 0.75, c.height * 0.3), c.u(520), "#8a5a16", 150)
        decor.radial_glow(c, (c.width * 0.2, c.height * 0.75), c.u(420), "#5a1a0c", 120)
        decor.gold_streaks(c, n=6, seed=11, alpha=85)
        decor.particles(c, (0, 0, c.width, c.height), "#ffd76a", n=170, seed=2)
        for x, y, s in ((0.88, 0.1, 120), (0.12, 0.42, 90), (0.9, 0.52, 110), (0.3, 0.06, 70)):
            decor.flare(c, (c.width * x, c.height * y), c.u(s))
        if fmt == "detail":  # カルーセルの詳細ページでは旗を出さない（見出しと重なるため）
            return
        top = c.u(90) if fmt == "reel" else c.u(20)
        decor.banner_flag(c, (c.u(18), top, c.u(122), top + c.u(430 if fmt == "reel" else 300)), "#9e1712")

    def render_cover(self, c, content: models.PostContent, sprite, fmt):
        self.background(c, fmt)
        area = safe_area(fmt, c.width, c.height)
        list_x1 = 700
        blocks = [Block("kicker", 130, lambda cv, b, s: self._kicker(cv, b, content.kicker), x0=150, x1=990)]
        if content.title_top:
            blocks.append(Block("title_top", 135, lambda cv, b, s: self._display(cv, content.title_top, b, GOLD,
                                                                                  [(14, "#140904"), (6, "#6b4510")])))
        blocks.append(Block("title_main", 265, lambda cv, b, s: self._display(
            cv, content.title_main, b, RED, [(28, "#120604"), (15, "#f2c23e"), (6, "#7a4b0e")], glow=(22, "#f5b83a"),
            ratio=0.86)))
        if content.title_bottom:
            blocks.append(Block("title_bottom", 135, lambda cv, b, s: self._display(
                cv, content.title_bottom, b, SILVER, [(14, "#0c0c0c"), (5, "#5a5a5a")])))
        if content.badge:
            blocks.append(Block("badge", 165, lambda cv, b, s: self._badge(cv, content.badge, b)))
        n = len(content.items)
        blocks.append(Block("list", 60 + n * 84, lambda cv, b, s: self._list(cv, content, b), x1=list_x1, gap=14))
        if content.caption_cta:
            blocks.append(Block("caption_cta", 74, lambda cv, b, s: self._cta(cv, content.caption_cta, b), x1=list_x1))
        boxes, _ = flow(c, blocks, area, max_extra_gap=30)
        lst = boxes["list"]
        bottom = c.height if fmt == "reel" else c.height - c.u(10)
        place_sprite(c, sprite, (c.u(690), lst[1] - c.u(120), c.width + c.u(30), min(bottom, lst[3] + c.u(330))))

    # ----- パーツ -----
    def _kicker(self, c, box, text):
        x0, y0, x1, y1 = box
        decor.torn_paper(c, box, "#f3efe6", seed=3, angle=-2.5)
        size = c.fit(text, "serif", (x1 - x0) * 0.86, int((y1 - y0) * 0.5), 24)
        c.rich_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), "serif", size, "#171310", "#c4161c", name="kicker")

    def _display(self, c, text, box, fill, strokes, glow=None, ratio=0.82):
        x0, y0, x1, y1 = box
        outer = max(w for w, _ in strokes)
        # フチの太さ込みで行の高さに収まる最大サイズ
        max_h = (y1 - y0) / (1.04 + 2 * outer / 150)
        size = c.fit(plain(text), "serif", (x1 - x0) * 0.86, int(min((y1 - y0) * ratio, max_h)), 30)
        k = size / 150
        c.display_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), "serif", size, fill,
                       strokes=[(max(1, int(c.u(w) * k)), col) for w, col in strokes],
                       shadow=(c.u(6), c.u(10), "#000000", c.u(10)),
                       glow=(int(c.u(glow[0]) * k), glow[1]) if glow else None, name="display")

    def _badge(self, c, text, box):
        x0, y0, x1, y1 = box
        chars = list(plain(text))
        s = min((y1 - y0), (x1 - x0) * 0.9 / max(1, len(chars)))
        gap = s * 0.06
        total = len(chars) * s + (len(chars) - 1) * gap
        x = (x0 + x1) / 2 - total / 2
        for ch in chars:
            sq = (int(x), int(y0 + (y1 - y0 - s) / 2), int(x + s), int(y0 + (y1 - y0 + s) / 2))
            decor.framed_box(c, sq, "#8e1111", "#e9bf4a", max(3, int(s * 0.06)), int(s * 0.06), inner="#f8df8a")
            size = int(s * 0.74)
            c.display_text(ch, ((sq[0] + sq[2]) / 2, (sq[1] + sq[3]) / 2), "serif", size, GOLD,
                           strokes=[(max(2, int(size * 0.07)), "#3a0a05")], name="badge")
            x += s + gap

    def _list(self, c, content, box):
        x0, y0, x1, y1 = box
        decor.framed_box(c, box, (12, 9, 7, 215), "#d4a63a", c.u(4), c.u(14), inner="#8a6420")
        n = len(content.items)
        pad = (y1 - y0) * 0.06
        row = (y1 - y0 - pad * 2) / n
        for k, item in enumerate(content.items):
            cy = y0 + pad + row * (k + 0.5)
            s = row * 0.5
            decor.checkbox(c, (x0 + c.u(34), cy - s / 2, x0 + c.u(34) + s, cy + s / 2), "#e9c25a",
                           check_color="#f7d25c")
            draw_item_text(c, item.text, (x0 + c.u(34) + s + c.u(26), cy - row / 2, x1 - c.u(24), cy + row / 2), "bold",
                           "#ffffff", "#f7d25c", int(row * 0.52), name=f"item_{k}", two_lines=False)
            if k < n - 1:
                yy = y0 + pad + row * (k + 1)
                c.draw.line([x0 + c.u(30), yy, x1 - c.u(30), yy], fill=(212, 166, 58, 110), width=max(1, c.u(2)))

    def _cta(self, c, text, box):
        x0, y0, x1, y1 = box
        c.draw.rounded_rectangle(box, radius=(y1 - y0) // 2, fill=(156, 18, 18, 235), outline="#e9c25a",
                                 width=max(2, c.u(3)))
        size = c.fit(text, "black", (x1 - x0) * 0.8, int((y1 - y0) * 0.5), 22)
        c.rich_text(emphasize_first(text, "キャプション"), ((x0 + x1) / 2, (y0 + y1) / 2), "black", size, "#ffffff",
                    "#f7d25c", name="caption_cta")
