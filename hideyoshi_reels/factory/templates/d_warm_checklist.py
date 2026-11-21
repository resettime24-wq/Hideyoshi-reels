"""テンプレートD: 和紙の淡色ベース × 緑・赤のアクセント × 行動チェックリスト（親しみやすい武将キャラ）。"""

from __future__ import annotations

from ... import models
from .. import decor
from ..canvas import plain
from .base import Block, Palette, Template, draw_item_text, emphasize_first, flow, place_sprite, safe_area

GREEN = "#14432c"
RED = "#c81e2c"
CREAM = "#fbf3df"


class WarmChecklistTemplate(Template):
    key = "D"
    name = "和紙×緑 行動チェックリスト"
    description = "和紙風の淡色に緑と赤。チェックボックスで今日からの行動を促す、親しみやすい型"
    best_for = "今日からやること・習慣・行動促進"
    palette = Palette(text="#1f1f1f", emph=RED, accent=RED, panel_fill="#fbf6ea", panel_border="#1f4d36",
                      heading_fill=GREEN, heading_strokes=[(10, CREAM)], heading_role="black", sub="#5b4a2e",
                      icon_ink="#3a2a20", icon_paper="#ffffff")

    def background(self, c, fmt):
        decor.fill_gradient(c, [(0.0, "#f8f0dd"), (1.0, "#eee0c0")])
        decor.paper_noise(c, strength=12, seed=5)
        cell = c.u(46)
        decor.checker(c, (0, 0, c.u(230), c.u(140)), "#1d5a3c", cell)
        decor.checker(c, (c.width - c.u(230), c.height - c.u(140), c.width, c.height), "#1d5a3c", cell)
        decor.seigaiha(c, (0, c.u(140), c.u(260), c.u(420)), "#c9a24a", alpha=90)
        decor.seigaiha(c, (c.width - c.u(300), c.height - c.u(420), c.width, c.height - c.u(140)), "#c9a24a", alpha=90)
        decor.clouds(c, (c.width * 0.86, c.height * 0.08), c.u(320), "#e2c26e", 150)
        decor.clouds(c, (c.width * 0.12, c.height * 0.62), c.u(260), "#e2c26e", 110)

    def render_cover(self, c, content: models.PostContent, sprite, fmt):
        self.background(c, fmt)
        area = safe_area(fmt, c.width, c.height)
        left_x1 = 640
        blocks = [Block("kicker", 125, lambda cv, b, s: self._kicker(cv, b, content.kicker), x0=80, x1=left_x1)]
        if content.title_top:
            blocks.append(Block("title_top", 150, lambda cv, b, s: self._title(cv, content.title_top, b, GREEN),
                                x1=left_x1, gap=4))
        blocks.append(Block("title_main", 185, lambda cv, b, s: self._title(cv, content.title_main, b, RED, brush=True),
                            x1=left_x1, gap=4))
        if content.title_bottom:
            blocks.append(Block("title_bottom", 150, lambda cv, b, s: self._title(cv, content.title_bottom, b, GREEN),
                                x1=left_x1))
        if content.badge:
            blocks.append(Block("badge", 135, lambda cv, b, s: self._badge(cv, content.badge, b), x1=left_x1))
        for k, item in enumerate(content.items):
            blocks.append(Block(f"item_{k}", 122, lambda cv, b, s, k=k, item=item: self._item(cv, k, item, b), gap=14))
        if content.action_line:
            blocks.append(Block("action", 130, lambda cv, b, s: self._action(cv, content.action_line, b)))
        blocks.append(Block("save", 104, lambda cv, b, s: self._save(cv, content.save_cta, b), x0=170, x1=910))
        boxes, _ = flow(c, blocks, area, max_extra_gap=24)
        top = boxes["kicker"][1]
        head_bottom = max(v[3] for k, v in boxes.items() if k.startswith("title") or k == "badge")
        # 見出しの下に金の筆線
        decor.brush_band(c, (c.u(50), int(head_bottom + c.u(4)), c.u(700), int(head_bottom + c.u(22))), "#d6a93c",
                         seed=41, streaks=False)
        place_sprite(c, sprite, (c.u(600), top - c.u(20), c.u(1060), head_bottom + c.u(10)))
        decor.burst_lines(c, (c.u(1000), boxes["item_0"][1] - c.u(6)), c.u(70), "#d6a93c", angle=-60, spread=60)

    def _kicker(self, c, box, text):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.speech_bubble(c, (x0, y0, x1, int(y1 - h * 0.12)), CREAM, "#7a5a26", max(3, c.u(6)), radius=c.u(14))
        size = c.fit(text, "black", (x1 - x0) * 0.82, int(h * 0.46), 22)
        c.rich_text(text, ((x0 + x1) / 2, y0 + (h * 0.88) / 2), "black", size, "#2a2420", RED, name="kicker")

    def _title(self, c, text, box, fill, brush=False):
        x0, y0, x1, y1 = box
        size = c.fit(plain(text), "black", (x1 - x0) * 0.9, int((y1 - y0) * 0.86), 30)
        w = c.text_width(plain(text), "black", size)
        if brush:
            decor.brush_band(c, (int(x0 - c.u(10)), int(y0 + (y1 - y0) * 0.45), int(x0 + w + c.u(60)),
                                 int(y1 + (y1 - y0) * 0.04)), "#d8434d", seed=42, alpha=200)
        k = size / 150
        c.display_text(text, (x0 + w / 2 + c.u(10), (y0 + y1) / 2), "black", size, fill,
                       strokes=[(max(2, int(c.u(12) * k)), CREAM)], shadow=(c.u(4), c.u(6), "#6b5a3a", c.u(5)),
                       name="title")

    def _badge(self, c, text, box):
        """判子（はんこ）風の赤いスタンプ。"""
        x0, y0, x1, y1 = box
        h = y1 - y0
        t = plain(text)
        size = int(h * 0.56)
        w = c.text_width(t, "serif", size) + h * 0.5
        stamp = (int(x0 + c.u(16)), int(y0 + h * 0.06), int(x0 + c.u(16) + w), int(y1 - h * 0.06))
        decor.framed_box(c, stamp, RED, "#8a1018", max(3, c.u(6)), int(h * 0.16), inner=CREAM, shadow=True)
        c.display_text(t, ((stamp[0] + stamp[2]) / 2, (stamp[1] + stamp[3]) / 2), "serif", size, CREAM,
                       name="badge")

    def _item(self, c, k, item: models.PostItem, box):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.framed_box(c, box, "#fbf6ea", "#1f4d36", max(3, c.u(6)), int(h * 0.12), inner="#1f4d36")
        s = h * 0.46
        decor.checkbox(c, (x0 + h * 0.32, y0 + (h - s) / 2, x0 + h * 0.32 + s, y0 + (h + s) / 2), "#1f1f1f",
                       width=max(3, c.u(6)))
        ic = h * 0.66
        decor.icon(c, item.icon, (x1 - ic - h * 0.25, y0 + (h - ic) / 2, x1 - h * 0.25, y0 + (h + ic) / 2), accent=RED)
        draw_item_text(c, item.text, (x0 + h * 0.32 + s + h * 0.3, y0 + h * 0.08, x1 - ic - h * 0.4, y1 - h * 0.08),
                       "black", "#1f1f1f", RED, int(h * 0.42), name=f"item_{k}")

    def _action(self, c, text, box):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.brush_band(c, (x0 - c.u(30), y0, x1 + c.u(10), y1), "#c41e2a", seed=43, roughness=0.14)
        size = c.fit(text, "black", (x1 - x0) * 0.82, int(h * 0.5), 22, emph_scale=1.25)
        c.rich_text(text, ((x0 + x1) / 2, (y0 + y1) / 2), "black", size, "#ffffff", "#ffd84a", emph_scale=1.25,
                    stroke=(max(1, c.u(3)), "#7a0d14"), name="action")

    def _save(self, c, text, box):
        x0, y0, x1, y1 = box
        h = y1 - y0
        decor.framed_box(c, box, CREAM, "#b88a2e", max(3, c.u(5)), int(h * 0.3), inner="#e2c26e")
        decor.bookmark(c, (int(x0 + h * 0.45), int(y0 + h * 0.18), int(x0 + h * 0.45 + h * 0.55), int(y1 - h * 0.18)),
                       RED)
        size = c.fit(text, "black", (x1 - x0) - h * 1.6, int(h * 0.46), 20)
        c.rich_text(emphasize_first(text), ((x0 + x1) / 2 + h * 0.3, (y0 + y1) / 2), "black", size, "#2a2420", RED,
                    name="save")
