"""テンプレートC: 白地 × 紺・赤の見出し × チェックリスト（情報整理・フィード向き）。"""

from __future__ import annotations

import re

from ... import models
from .. import decor
from ..canvas import plain
from .base import Block, Palette, Template, draw_item_text, flow, place_sprite, safe_area

NAVY = "#14213d"
RED = "#a8172b"
YELLOW = (246, 214, 110, 200)


class WhiteNavyTemplate(Template):
    key = "C"
    name = "白×紺 インフォグラフィック"
    description = "白地に紺と赤の見出し、チェックリストと補足ボックス。情報を整理して見せるフィード向きの型"
    best_for = "情報整理・計画・学部比較・手順"
    palette = Palette(text=NAVY, emph=RED, accent=RED, panel_fill="#ffffff", panel_border="#d8d2c4",
                      heading_fill=NAVY, heading_strokes=[], heading_role="black", sub="#6b7280",
                      highlight=YELLOW, icon_ink=NAVY, icon_paper="#ffffff")

    def background(self, c, fmt):
        decor.fill_gradient(c, [(0.0, "#fbfaf7"), (1.0, "#efebe2")])
        decor.light_polygons(c, "#ffffff", n=9, seed=21, alpha=150)
        decor.light_polygons(c, "#e4dfd3", n=5, seed=22, alpha=70)

    def render_cover(self, c, content: models.PostContent, sprite, fmt):
        self.background(c, fmt)
        area = safe_area(fmt, c.width, c.height)
        blocks = [Block("kicker", 110, lambda cv, b, s: self._kicker(cv, b, content.kicker), x0=40, x1=780)]
        if content.title_top:
            blocks.append(Block("title_top", 95, lambda cv, b, s: self._sub(cv, content.title_top, b)))
        blocks.append(Block("title_main", 190, lambda cv, b, s: self._main(cv, content.title_main, b), gap=8))
        if content.title_bottom or content.badge:
            blocks.append(Block("title_row", 185, lambda cv, b, s: self._row(cv, content.title_bottom, content.badge, b)))
        n = len(content.items)
        blocks.append(Block("list", 110 + n * 104, lambda cv, b, s: self._list(cv, content, b), gap=26))
        blocks.append(Block("info", 200, lambda cv, b, s: self._info(cv, content, b), x1=650))
        if content.caption_cta:
            blocks.append(Block("cta", 120, lambda cv, b, s: self._cta(cv, content.caption_cta, b, fmt)))
        boxes, _ = flow(c, blocks, area, max_extra_gap=24)
        info = boxes["info"]
        place_sprite(c, sprite, (c.u(680), info[1] - c.u(90), c.u(1000), info[3] + c.u(10)))

    def _kicker(self, c, box, text):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.ribbon(c, (0, y0, x1, y1), NAVY)
        c.draw.line([0, y1 - h * 0.12, x1 - h * 0.05, y1 - h * 0.12], fill="#c9a24a", width=max(2, c.u(3)))
        decor.laurel(c, (x0 + h * 0.75, (y0 + y1) / 2), h * 0.7, "#c9a24a")
        decor.laurel(c, (x1 - h * 0.5, (y0 + y1) / 2), h * 0.7, "#c9a24a", mirror=True)
        size = c.fit(text, "black", (x1 - x0) - h * 2.4, int(h * 0.5), 22)
        c.rich_text(text, ((x0 + x1) / 2 + h * 0.1, (y0 + y1) / 2), "black", size, "#ffffff", "#f3dc8a",
                    name="kicker")

    def _sub(self, c, text, box):
        x0, y0, x1, y1 = box
        line = f"＼ {text} ／"
        size = c.fit(line, "black", (x1 - x0) * 0.9, int((y1 - y0) * 0.62), 24)
        c.rich_text(line if "**" in text else f"＼ **{text}** ／", ((x0 + x1) / 2, (y0 + y1) / 2), "black", size,
                    NAVY, RED, name="title_top")

    def _main(self, c, text, box):
        x0, y0, x1, y1 = box
        size = c.fit(plain(text), "black", (x1 - x0) * 0.92, int((y1 - y0) * 0.86), 30)
        w = c.text_width(plain(text), "black", size)
        cx = (x0 + x1) / 2
        decor.brush_band(c, (int(cx - w / 2), int(y0 + (y1 - y0) * 0.62), int(cx + w / 2 + c.u(20)),
                             int(y1 - (y1 - y0) * 0.02)), "#f3d77a", seed=31, alpha=210, streaks=False)
        c.display_text(text, (cx, (y0 + y1) / 2), "black", size, NAVY, strokes=[], name="title_main")

    def _row(self, c, bottom, badge, box):
        x0, y0, x1, y1 = box
        h = y1 - y0
        m = re.match(r"^(\d+)(.*)$", plain(badge or ""))
        num, rest = (m.group(1), m.group(2)) if m else ("", plain(badge or ""))
        squares = bool(bottom) and len(plain(bottom)) <= 4
        sq = h * 0.82
        bottom_w = (len(plain(bottom)) * (sq + c.u(8)) if squares else
                    c.text_width(plain(bottom), "black", int(h * 0.62))) if bottom else 0
        num_size, rest_size = int(h * 1.0), int(h * 0.6)
        badge_w = (c.text_width(num, "serif", num_size) if num else 0) + (
            c.text_width(rest, "black", rest_size) if rest else 0)
        total = bottom_w + (c.u(20) if bottom and badge else 0) + badge_w
        k = min(1.0, (x1 - x0) * 0.94 / max(1, total))
        sq, num_size, rest_size = sq * k, int(num_size * k), int(rest_size * k)
        x = (x0 + x1) / 2 - total * k / 2
        cy = (y0 + y1) / 2
        if bottom:
            if squares:
                for ch in plain(bottom):
                    decor.framed_box(c, (int(x), int(cy - sq / 2), int(x + sq), int(cy + sq / 2)), RED, "#7a0f1e",
                                     max(2, c.u(3)), int(sq * 0.05), shadow=False)
                    c.display_text(ch, (x + sq / 2, cy), "black", int(sq * 0.74), "#ffffff", name="title_bottom")
                    x += sq + c.u(8) * k
            else:
                bx = c.rich_text(plain(bottom), (x, cy), "black", int(h * 0.62 * k), RED, align="left",
                                 name="title_bottom")
                x = bx[2]
            x += c.u(20) * k
        x_start = x
        if num:
            bx = c.rich_text(num, (x, cy - h * 0.04), "serif", num_size, RED, align="left", name="badge_num")
            x = bx[2]
        if rest:
            c.rich_text(rest, (x, cy + h * 0.1), "black", rest_size, NAVY, align="left", name="badge_rest")
        if badge:  # 赤いスウッシュ
            c.draw.line([x_start - c.u(20), y1 + h * 0.02, x1 - c.u(40), y1 - h * 0.1], fill=RED, width=max(3, c.u(7)))

    def _list(self, c, content, box):
        x0, y0, x1, y1 = box
        label_h = c.u(92) * ((y1 - y0) / max(1, c.u(110 + len(content.items) * 104)))
        card = (x0, int(y0 + label_h * 0.55), x1, y1)
        decor.framed_box(c, card, "#fffdf8", "#d8d2c4", max(2, c.u(3)), c.u(18))
        label = content.list_heading or "ここがポイント"
        lsize = c.fit(label, "black", (x1 - x0) * 0.7, int(label_h * 0.5), 20)
        lw = c.text_width(label, "black", lsize) + c.u(80)
        lx0 = (x0 + x1) / 2 - lw / 2
        decor.speech_bubble(c, (int(lx0), int(y0), int(lx0 + lw), int(y0 + label_h)), NAVY, NAVY, 2, radius=c.u(10))
        c.rich_text(label, ((x0 + x1) / 2, y0 + label_h / 2), "black", lsize, "#ffffff", "#f6d66e",
                    name="list_heading")
        n = len(content.items)
        top = card[1] + label_h * 0.6
        row = (card[3] - top - c.u(16)) / n
        for k, item in enumerate(content.items):
            cy = top + row * (k + 0.5)
            s = row * 0.46
            decor.checkbox(c, (x0 + c.u(44), cy - s / 2, x0 + c.u(44) + s, cy + s / 2), "#3b3b3b",
                           check_color=RED)
            draw_item_text(c, item.text, (x0 + c.u(44) + s + c.u(30), cy - row / 2, x1 - c.u(30), cy + row / 2),
                           "black", NAVY, RED, int(row * 0.46), highlight=YELLOW, name=f"item_{k}", two_lines=False)
            if k < n - 1:
                yy = top + row * (k + 1)
                for xx in range(int(x0 + c.u(40)), int(x1 - c.u(40)), c.u(14)):
                    c.draw.line([xx, yy, xx + c.u(6), yy], fill="#b9b2a3", width=max(1, c.u(2)))

    def _info(self, c, content, box):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.framed_box(c, box, "#fffdf2", "#e2dccb", max(2, c.u(3)), c.u(10))
        for k in range(5):  # スパイラルリング
            yy = y0 + h * (0.15 + k * 0.175)
            c.draw.ellipse([x0 - c.u(14), yy - c.u(9), x0 + c.u(14), yy + c.u(9)], outline="#8b8b8b",
                           width=max(2, c.u(3)))
        info = content.info_box
        label = info.label if info else "今日のひとこと"
        value = info.value if info else plain(content.action_line or content.save_cta)
        ic = h * 0.32
        decor.icon(c, "calendar", (x0 + c.u(40), y0 + h * 0.1, x0 + c.u(40) + ic, y0 + h * 0.1 + ic), ink=NAVY,
                   accent="#3c5a9a")
        lsize = c.fit(label, "black", (x1 - x0) - ic - c.u(110), int(h * 0.2), 18)
        c.rich_text(label, (x0 + c.u(64) + ic, y0 + h * 0.1 + ic / 2), "black", lsize, NAVY, align="left",
                    name="info_label")
        vsize = c.fit(value, "black", (x1 - x0) - c.u(90), int(h * 0.32), 20)
        c.rich_text(value if "**" in value else f"**{value}**", (x0 + c.u(44), y0 + h * 0.7), "black", vsize, RED, RED,
                    align="left", highlight=YELLOW, name="info_value")

    def _cta(self, c, text, box, fmt):
        x0, y0, x1, y1 = box
        h = y1 - y0
        c.draw.rectangle([0, y0, c.width, y1], fill="#9e1b32")
        c.draw.line([0, y0 + c.u(6), c.width, y0 + c.u(6)], fill="#c9a24a", width=max(1, c.u(3)))
        size = c.fit(text, "black", (x1 - x0) - h * 1.8, int(h * 0.42), 20)
        bx = c.rich_text(text.replace("キャプション", "**キャプション**", 1) if "**" not in text else text,
                         ((x0 + x1) / 2 - h * 0.5, (y0 + y1) / 2), "black", size, "#ffffff", "#ffe08a", name="cta")
        decor.icon(c, "book", (bx[2] + c.u(30), y0 + h * 0.15, bx[2] + c.u(30) + h * 0.7, y1 - h * 0.15),
                   ink="#ffffff", accent="#ffe08a", paper="#9e1b32")
