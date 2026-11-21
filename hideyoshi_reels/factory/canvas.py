"""描画キャンバス: 日本語テキストの正確な配置、強調（**語**）、グラデーション文字、配置の記録。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFilter

from .fonts import Fonts

EMPH = re.compile(r"\*\*(.+?)\*\*")


def parse_emphasis(text: str) -> list[tuple[str, bool]]:
    """'**過去問**を解く' → [('過去問', True), ('を解く', False)]"""
    out, pos = [], 0
    for m in EMPH.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return [(t, e) for t, e in out if t]


def plain(text: str) -> str:
    return text.replace("**", "")


def hex2rgb(c, alpha: int | None = None):
    if isinstance(c, tuple):
        return c if alpha is None else (*c[:3], alpha)
    c = c.lstrip("#")
    if len(c) == 3:  # "#000" 形式
        c = "".join(ch * 2 for ch in c)
    rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return rgb if alpha is None else (*rgb, alpha)


def gradient(size: tuple[int, int], stops: list, horizontal: bool = False) -> Image.Image:
    """stops: ['#fff', '#aaa'] または [(0.0, '#fff'), (1.0, '#aaa')]"""
    if not (isinstance(stops[0], tuple) and len(stops[0]) == 2 and isinstance(stops[0][0], float)):
        stops = [(i / max(1, len(stops) - 1), s) for i, s in enumerate(stops)]
    stops = [(p, hex2rgb(c)) for p, c in stops]
    n = size[0] if horizontal else size[1]
    line = Image.new("RGB", (n, 1))
    for i in range(n):
        t = i / max(1, n - 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= t <= p1:
                k = (t - p0) / max(1e-6, p1 - p0)
                line.putpixel((i, 0), tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3)))
                break
    if horizontal:
        return line.resize(size)
    return line.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT).resize(size)


@dataclass
class TextBox:
    name: str
    box: tuple[int, int, int, int]
    text: str
    role: str


@dataclass
class Canvas:
    width: int
    height: int
    fonts: Fonts
    image: Image.Image = None
    boxes: list[TextBox] = field(default_factory=list)

    def __post_init__(self):
        if self.image is None:
            self.image = Image.new("RGBA", (self.width, self.height), (255, 255, 255, 255))

    # 1080px 幅を基準にした寸法を実サイズへ
    def u(self, v: float) -> int:
        return int(round(v * self.width / 1080))

    @property
    def draw(self) -> ImageDraw.ImageDraw:
        return ImageDraw.Draw(self.image)

    def paste(self, layer: Image.Image, xy=(0, 0)) -> None:
        self.image.alpha_composite(layer.convert("RGBA"), (int(xy[0]), int(xy[1])))

    def blur_paste(self, layer: Image.Image, radius: float) -> None:
        """レイヤーの描かれた部分だけをぼかして合成する（全面をぼかすより高速）。"""
        bbox = layer.getbbox()
        if not bbox:
            return
        pad = int(radius * 3) + 2
        x0, y0 = max(0, bbox[0] - pad), max(0, bbox[1] - pad)
        x1, y1 = min(layer.width, bbox[2] + pad), min(layer.height, bbox[3] + pad)
        region = layer.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(radius))
        self.image.alpha_composite(region, (x0, y0))

    def layer(self) -> Image.Image:
        return Image.new("RGBA", self.image.size, (0, 0, 0, 0))

    def record(self, name: str, box, text: str, role: str = "") -> None:
        x0, y0, x1, y1 = (int(v) for v in box)
        self.boxes.append(TextBox(name, (x0, y0, x1, y1), plain(text), role))

    # ---------- 文字サイズの自動調整 ----------
    def text_width(self, text: str, role: str, size: int, emph_scale: float = 1.0) -> float:
        total = 0.0
        for seg, emph in parse_emphasis(text):
            total += self.fonts.get(role, size * (emph_scale if emph else 1)).getlength(seg)
        return total

    def fit(self, text: str, role: str, max_width: float, max_size: int, min_size: int = 20,
            emph_scale: float = 1.0) -> int:
        size = max_size
        while size > min_size and self.text_width(text, role, size, emph_scale) > max_width:
            size -= 2
        return size

    # ---------- 強調つき1行テキスト ----------
    def rich_text(self, text: str, xy: tuple[float, float], role: str, size: int, color, emph_color=None,
                  align: str = "center", emph_scale: float = 1.0, emph_role: str | None = None,
                  stroke: tuple[int, object] | None = None, highlight=None, shadow=None,
                  name: str = "text") -> tuple[int, int, int, int]:
        """xy の y は行の中心。align: left / center / right（x の基準）。"""
        segs = parse_emphasis(text)
        fonts = [self.fonts.get(emph_role or role if e else role, size * (emph_scale if e else 1)) for _, e in segs]
        widths = [f.getlength(s) for (s, _), f in zip(segs, fonts)]
        total = sum(widths)
        x, cy = xy
        if align == "center":
            x -= total / 2
        elif align == "right":
            x -= total
        # 日本語の字面は「ベースラインから上に約0.88em、下に約0.12em」なので、その中心を cy に合わせる
        baseline = cy + 0.38 * size
        top = baseline - 0.9 * size * max(1, emph_scale)
        bottom = baseline + 0.14 * size
        d = self.draw
        sw = stroke[0] if stroke else 0
        fake = self.fonts.fake_bold.get(role, False)
        if shadow:
            sh = self.layer()
            sd = ImageDraw.Draw(sh)
            cx = x
            for (seg, emph), f, w in zip(segs, fonts, widths):
                sd.text((cx + shadow[0], baseline + shadow[1]), seg, font=f, anchor="ls", fill=hex2rgb(shadow[2]),
                        stroke_width=sw, stroke_fill=hex2rgb(shadow[2]))
                cx += w
            self.blur_paste(sh, shadow[3] if len(shadow) > 3 else 4)
        cx = x
        for (seg, emph), f, w in zip(segs, fonts, widths):
            if emph and highlight:
                d.rectangle([cx - 2, baseline - f.size * 0.38, cx + w + 2, baseline + f.size * 0.08],
                            fill=hex2rgb(highlight))
            fill = hex2rgb(emph_color if (emph and emph_color) else color)
            kwargs = {}
            if stroke:
                kwargs = {"stroke_width": sw, "stroke_fill": hex2rgb(stroke[1])}
            elif fake:
                kwargs = {"stroke_width": max(1, f.size // 30), "stroke_fill": fill}
            d.text((cx, baseline), seg, font=f, anchor="ls", fill=fill, **kwargs)
            cx += w
        box = (x - sw, top - sw, x + total + sw, bottom + sw)
        self.record(name, box, text, role)
        return tuple(int(v) for v in box)

    # ---------- 見出し用の装飾文字（グラデーション＋多重フチ） ----------
    def display_text(self, text: str, center: tuple[float, float], role: str, size: int, fill,
                     strokes: list[tuple[int, object]] = (), shadow=None, glow=None,
                     name: str = "display", spacing: float = 0.0) -> tuple[int, int, int, int]:
        """fill は色、またはグラデーションの色リスト。strokes は外側から順に (太さ, 色)。"""
        text = plain(text)
        font = self.fonts.get(role, size)
        pad = max([w for w, _ in strokes] + [0]) + size // 4 + (glow[0] if glow else 0)
        widths = [font.getlength(ch) for ch in text]
        tw = sum(widths) + spacing * size * max(0, len(text) - 1)
        asc, desc = font.getmetrics()
        lw, lh = int(tw + pad * 2), int(asc + desc + pad * 2)

        def text_layer(stroke_w: int, color) -> Image.Image:
            lay = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            x = pad
            for ch, w in zip(text, widths):
                d.text((x, pad + asc), ch, font=font, anchor="ls", fill=color, stroke_width=stroke_w, stroke_fill=color)
                x += w + spacing * size
            return lay

        out = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        if glow:
            g = text_layer(glow[0], hex2rgb(glow[1], 255)).filter(ImageFilter.GaussianBlur(glow[0]))
            out.alpha_composite(g)
        if shadow:
            s = text_layer(strokes[0][0] if strokes else 0, hex2rgb(shadow[2], 255))
            s = s.filter(ImageFilter.GaussianBlur(shadow[3] if len(shadow) > 3 else 6))
            out.alpha_composite(s, (int(shadow[0]), int(shadow[1])))
        for w, color in strokes:
            out.alpha_composite(text_layer(w, hex2rgb(color, 255)))
        mask = text_layer(0, (255, 255, 255, 255)).getchannel("A")
        if isinstance(fill, (list, tuple)) and not isinstance(fill[0], int):
            # グラデーションは字面（ベースライン上0.9em〜下0.12em）の範囲にかける
            glyph_top = int(pad + asc - 0.9 * size)
            ink_h = int(1.04 * size)
            ink = Image.new("RGBA", (lw, lh), hex2rgb(list(fill)[-1] if not isinstance(list(fill)[-1], tuple)
                                                       else list(fill)[-1][1], 255))
            ink.paste(gradient((lw, ink_h), list(fill)).convert("RGBA"), (0, max(0, glyph_top)))
        else:
            ink = Image.new("RGBA", (lw, lh), hex2rgb(fill, 255))
        out.paste(ink, (0, 0), mask)
        baseline = center[1] + 0.38 * size
        x0 = int(center[0] - lw / 2)
        y0 = int(baseline - pad - asc)
        self.paste(out, (x0, y0))
        outer = strokes[0][0] if strokes else 0
        box = (x0 + pad - outer, baseline - 0.9 * size - outer, x0 + pad + tw + outer, baseline + 0.14 * size + outer)
        self.record(name, box, text, role)
        return tuple(int(v) for v in box)

    def wrap(self, text: str, role: str, size: int, max_width: float) -> list[str]:
        """日本語の折り返し（行頭禁則つき）。強調記号はそのまま保持する。"""
        no_start = set("、。，．・：；？！ー～）」』】!?…")
        lines, cur = [], ""
        font = self.fonts.get(role, size)
        for ch in text:
            if font.getlength(plain(cur + ch)) <= max_width or not plain(cur) or ch in no_start or ch == "*":
                cur += ch
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
        # 強調記号が行をまたいだら補正
        fixed, open_ = [], False
        for line in lines:
            if open_:
                line = "**" + line
            open_ = line.count("**") % 2 == 1
            fixed.append(line + ("**" if open_ else ""))
        return fixed

    def paragraph(self, text: str, box, role: str, size: int, color, emph_color=None, line_gap: float = 1.5,
                  align: str = "left", name: str = "paragraph", min_size: int = 20) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = box
        while True:
            lines = self.wrap(text, role, size, x1 - x0)
            height = len(lines) * size * line_gap
            if height <= (y1 - y0) or size <= min_size:
                break
            size -= 2
        y = y0 + size * line_gap / 2
        xs = {"left": x0, "center": (x0 + x1) / 2, "right": x1}[align]
        boxes = []
        for line in lines:
            boxes.append(self.rich_text(line, (xs, y), role, size, color, emph_color, align=align, name=name))
            y += size * line_gap
        self.boxes = [b for b in self.boxes if not (b.name == name and b.box in boxes)]
        bx = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        self.record(name, bx, text, role)
        return bx
