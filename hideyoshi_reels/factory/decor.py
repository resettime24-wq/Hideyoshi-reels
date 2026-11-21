"""装飾パーツ（筆の帯・破れ紙・和柄・月桂樹・アイコンなど）。すべてプログラム描画の自作素材です。"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from .canvas import Canvas, gradient, hex2rgb


# ---------------- 背景・質感 ----------------
def fill_gradient(c: Canvas, stops, box=None, horizontal=False) -> None:
    x0, y0, x1, y1 = box or (0, 0, c.width, c.height)
    c.paste(gradient((x1 - x0, y1 - y0), stops, horizontal).convert("RGBA"), (x0, y0))


def radial_glow(c: Canvas, center, radius, color, alpha=160) -> None:
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    x, y = center
    d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=hex2rgb(color, alpha))
    c.blur_paste(lay, radius * 0.45)


def paper_noise(c: Canvas, strength=10, seed=0) -> None:
    """和紙のようなざらつき。"""
    rng = random.Random(seed)
    small = Image.new("L", (c.width // 6, c.height // 6))
    small.putdata([128 + rng.randint(-strength, strength) for _ in range(small.width * small.height)])
    noise = small.resize(c.image.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(1))
    lay = Image.new("RGBA", c.image.size, (0, 0, 0, 0))
    dark = Image.new("RGBA", c.image.size, (90, 70, 40, 255))
    lay.paste(dark, (0, 0), noise.point(lambda v: max(0, 128 - v) * 3))
    c.paste(lay)


def seigaiha(c: Canvas, box, color, alpha=50, r=None, width=None) -> None:
    """青海波（和柄）。"""
    x0, y0, x1, y1 = box
    r = r or c.u(46)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    col = hex2rgb(color, alpha)
    row = 0
    y = y0
    while y < y1 + r:
        off = r if row % 2 else 0
        x = x0 - r + off
        while x < x1 + r:
            for k in (1.0, 0.7, 0.4):
                d.ellipse([x - r * k, y - r * k, x + r * k, y + r * k], outline=col, width=width or max(2, c.u(4)))
            x += 2 * r
        y += r // 2
        row += 1
    mask = Image.new("L", c.image.size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", c.image.size, 0), mask))
    c.paste(lay)


def checker(c: Canvas, box, color, cell=None, alpha=255) -> None:
    """市松模様。"""
    x0, y0, x1, y1 = box
    cell = cell or c.u(44)
    d = c.draw
    for j, y in enumerate(range(y0, y1, cell)):
        for i, x in enumerate(range(x0, x1, cell)):
            if (i + j) % 2 == 0:
                d.rectangle([x, y, min(x + cell, x1), min(y + cell, y1)], fill=hex2rgb(color, alpha))


def particles(c: Canvas, box, color, n=120, seed=1, max_r=None) -> None:
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    max_r = max_r or c.u(5)
    for _ in range(n):
        x, y = rng.randint(x0, x1), rng.randint(y0, y1)
        r = rng.uniform(1, max_r)
        d.ellipse([x - r, y - r, x + r, y + r], fill=hex2rgb(color, rng.randint(90, 255)))
    c.blur_paste(lay, 0.6)


def flare(c: Canvas, center, size, color="#fff6c8") -> None:
    """キラッと光る十字のフレア。"""
    x, y = center
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    for (dx, dy), length in (((1, 0), size), ((0, 1), size), ((0.7, 0.7), size * 0.45), ((0.7, -0.7), size * 0.45)):
        d.polygon([(x - dx * length, y - dy * length), (x + dy * size * 0.05, y - dx * size * 0.05),
                   (x + dx * length, y + dy * length), (x - dy * size * 0.05, y + dx * size * 0.05)],
                  fill=hex2rgb(color, 230))
    d.ellipse([x - size * 0.12, y - size * 0.12, x + size * 0.12, y + size * 0.12], fill=hex2rgb("#ffffff", 255))
    c.blur_paste(lay, max(1, size // 40))
    radial_glow(c, center, size * 0.35, color, 120)


def gold_streaks(c: Canvas, n=7, seed=3, alpha=150) -> None:
    """金色の筆の流れ（斜めのストローク）。"""
    rng = random.Random(seed)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    w, h = c.width, c.height
    for _ in range(n):
        y = rng.uniform(-0.1, 1.0) * h
        thick = rng.uniform(0.01, 0.05) * h
        pts_top, pts_bot = [], []
        for i in range(13):
            x = -w * 0.1 + i * w * 1.2 / 12
            yy = y + math.sin(i / 12 * math.pi * rng.uniform(0.6, 1.4)) * h * 0.08 - i * h * 0.012
            t = thick * math.sin(i / 12 * math.pi)
            pts_top.append((x, yy - t))
            pts_bot.append((x, yy + t * rng.uniform(0.4, 1.0)))
        d.polygon(pts_top + pts_bot[::-1], fill=hex2rgb(rng.choice(["#f5c84c", "#d99a21", "#ffe08a"]), alpha))
    c.blur_paste(lay, c.u(5))
    lay2 = c.layer()
    d2 = ImageDraw.Draw(lay2)
    for _ in range(n * 6):  # 細い筆跡
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        length = rng.uniform(0.1, 0.35) * w
        d2.line([x, y, x + length, y - length * 0.25], fill=hex2rgb("#f8d777", rng.randint(60, 160)),
                width=max(1, c.u(rng.uniform(1, 3))))
    c.blur_paste(lay2, 0.8)


def light_polygons(c: Canvas, color="#e9e6df", n=8, seed=4, alpha=110) -> None:
    rng = random.Random(seed)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y = rng.uniform(-0.2, 1.1) * c.width, rng.uniform(-0.1, 1.0) * c.height
        s = rng.uniform(0.3, 0.8) * c.width
        d.polygon([(x, y), (x + s, y + s * 0.2), (x + s * 0.4, y + s * 0.9)], fill=hex2rgb(color, alpha))
    c.blur_paste(lay, c.u(2))


def petals(c: Canvas, box, color="#ffc1d3", n=25, seed=5) -> None:
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y, r = rng.randint(x0, x1), rng.randint(y0, y1), c.u(rng.uniform(8, 18))
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.random()
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            d.ellipse([px - r * 0.6, py - r * 0.6, px + r * 0.6, py + r * 0.6], fill=hex2rgb(color, 200))
        d.ellipse([x - r * 0.3, y - r * 0.3, x + r * 0.3, y + r * 0.3], fill=hex2rgb("#ff8fb0", 230))
    c.blur_paste(lay, 0.8)


def clouds(c: Canvas, center, width, color="#e8c873", alpha=170) -> None:
    """和風の雲（すやり霞風）。"""
    x, y = center
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    col = hex2rgb(color, alpha)
    h = width * 0.18
    d.rounded_rectangle([x - width / 2, y - h / 2, x + width / 2, y + h / 2], radius=h / 2, fill=col)
    for dx, r in ((-0.25, 0.16), (0.0, 0.2), (0.22, 0.14)):
        cx = x + dx * width
        d.ellipse([cx - width * r, y - h / 2 - width * r * 0.9, cx + width * r, y - h / 2 + width * r * 0.6], fill=col)
    c.blur_paste(lay, 1)


# ---------------- 帯・枠 ----------------
def brush_band(c: Canvas, box, color, seed=0, roughness=0.18, alpha=255, streaks=True) -> None:
    """筆で塗ったような帯（端がかすれる）。"""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    h = y1 - y0
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    top, bot = [], []
    steps = 24
    for i in range(steps + 1):
        x = x0 + (x1 - x0) * i / steps
        top.append((x, y0 + rng.uniform(0, roughness) * h))
        bot.append((x, y1 - rng.uniform(0, roughness) * h))
    left = [(x0 - rng.uniform(0, h * 0.5), y0 + h * k / 6) for k in range(1, 6)]
    right = [(x1 + rng.uniform(0, h * 0.6), y1 - h * k / 6) for k in range(1, 6)]
    d.polygon(top + right + bot[::-1] + left[::-1], fill=hex2rgb(color, alpha))
    if streaks:
        for _ in range(14):  # かすれ
            yy = rng.uniform(y0, y1)
            xs = rng.uniform(x1 - (x1 - x0) * 0.2, x1 + h * 0.5)
            d.line([xs, yy, xs + rng.uniform(h * 0.3, h * 1.2), yy + rng.uniform(-4, 4)],
                   fill=hex2rgb(color, rng.randint(80, 200)), width=max(1, int(h * rng.uniform(0.02, 0.06))))
            xs = rng.uniform(x0 - h * 0.4, x0 + (x1 - x0) * 0.1)
            d.line([xs - rng.uniform(h * 0.2, h * 0.8), yy, xs, yy], fill=hex2rgb(color, rng.randint(80, 200)),
                   width=max(1, int(h * rng.uniform(0.02, 0.06))))
    c.blur_paste(lay, 0.8)


def torn_paper(c: Canvas, box, color="#f4f1ea", seed=0, angle=-2.5, shadow=True) -> None:
    """破れた紙の帯（少し傾ける）。"""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    pad = int(h * 0.5)
    lay = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = []
    n = 30
    for i in range(n + 1):
        pts.append((pad + w * i / n, pad + rng.uniform(-0.06, 0.06) * h))
    for i in range(6):
        pts.append((pad + w + rng.uniform(-0.03, 0.03) * w, pad + h * i / 5))
    for i in range(n, -1, -1):
        pts.append((pad + w * i / n, pad + h + rng.uniform(-0.06, 0.06) * h))
    for i in range(5, -1, -1):
        pts.append((pad + rng.uniform(-0.03, 0.03) * w, pad + h * i / 5))
    d.polygon(pts, fill=hex2rgb(color, 255))
    for _ in range(40):  # 紙の繊維
        x, y = rng.uniform(pad, pad + w), rng.uniform(pad, pad + h)
        d.line([x, y, x + rng.uniform(5, 30), y + rng.uniform(-3, 3)], fill=(200, 192, 178, 90), width=1)
    lay = lay.rotate(angle, resample=Image.BICUBIC, expand=False)
    if shadow:
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 150), (0, 0), lay.getchannel("A"))
        c.paste(sh.filter(ImageFilter.GaussianBlur(c.u(10))), (x0 - pad + c.u(6), y0 - pad + c.u(10)))
    c.paste(lay, (x0 - pad, y0 - pad))


def ribbon(c: Canvas, box, color, slant=None) -> None:
    """平行四辺形のリボン帯。"""
    x0, y0, x1, y1 = box
    s = slant if slant is not None else (y1 - y0) * 0.35
    c.draw.polygon([(x0, y0), (x1 + s, y0), (x1, y1), (x0 - s, y1)], fill=hex2rgb(color))


def framed_box(c: Canvas, box, fill, border, width, radius, inner=None, shadow=True) -> None:
    x0, y0, x1, y1 = box
    if shadow:
        lay = c.layer()
        ImageDraw.Draw(lay).rounded_rectangle([x0 + c.u(6), y0 + c.u(10), x1 + c.u(6), y1 + c.u(10)], radius=radius,
                                              fill=(0, 0, 0, 90))
        c.blur_paste(lay, c.u(10))
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle(box, radius=radius, fill=hex2rgb(fill) if isinstance(fill, str) else fill,
                        outline=hex2rgb(border), width=width)
    if inner:
        m = width + c.u(6)
        d.rounded_rectangle([x0 + m, y0 + m, x1 - m, y1 - m], radius=max(1, radius - m), outline=hex2rgb(inner),
                            width=max(1, width // 3))
    c.paste(lay)


def speech_bubble(c: Canvas, box, fill, border, width, tail="bottom", radius=None) -> None:
    x0, y0, x1, y1 = box
    r = radius if radius is not None else (y1 - y0) // 4
    d = c.draw
    tw = (y1 - y0) * 0.35
    if tail == "bottom":
        tx = x0 + (x1 - x0) * 0.62
        tri = [(tx - tw / 2, y1 - width), (tx + tw / 2, y1 - width), (tx + tw * 0.1, y1 + tw * 0.8)]
    else:
        tx = x0 + (x1 - x0) * 0.25
        tri = [(tx - tw / 2, y0 + width), (tx + tw / 2, y0 + width), (tx, y0 - tw * 0.8)]
    d.polygon(tri, fill=hex2rgb(border))
    d.rounded_rectangle(box, radius=r, fill=hex2rgb(fill), outline=hex2rgb(border), width=width)
    inner = [(tri[0][0] + width, tri[0][1]), (tri[1][0] - width, tri[1][1]),
             (tri[2][0], tri[2][1] - width * 1.6 * (1 if tail == "bottom" else -1))]
    d.polygon(inner, fill=hex2rgb(fill))


def laurel(c: Canvas, center, size, color, mirror=False) -> None:
    """月桂樹の飾り（ランキング感）。"""
    x, y = center
    d = c.draw
    sgn = -1 if mirror else 1
    col = hex2rgb(color)
    pts = []
    for i in range(7):
        t = i / 6
        a = math.pi * (0.95 - 0.75 * t)
        px = x + sgn * math.cos(a) * size * 0.45
        py = y + size * 0.5 - math.sin(a) * size * 0.05 - t * size
        pts.append((px, py))
    d.line(pts, fill=col, width=max(2, int(size * 0.05)))
    for i, (px, py) in enumerate(pts[1:], 1):
        lw = size * 0.16
        ang = math.radians(-35 if not mirror else 215) + i * 0.05 * sgn
        for side in (-1, 1):
            a2 = ang + side * 0.6
            ex, ey = px + math.cos(a2) * lw * sgn, py + math.sin(a2) * lw
            d.ellipse([min(px, ex) - lw * 0.18, min(py, ey) - lw * 0.18, max(px, ex) + lw * 0.18,
                       max(py, ey) + lw * 0.18], fill=col)


def burst_lines(c: Canvas, origin, size, color, n=3, angle=-50, spread=30) -> None:
    """「///」のような注目線。"""
    x, y = origin
    d = c.draw
    for i in range(n):
        a = math.radians(angle - spread / 2 + spread * i / max(1, n - 1))
        d.line([x + math.cos(a) * size * 0.35, y + math.sin(a) * size * 0.35, x + math.cos(a) * size,
                y + math.sin(a) * size], fill=hex2rgb(color), width=max(3, int(size * 0.12)))


def banner_flag(c: Canvas, box, color, emblem="#d4a63a", seed=0) -> None:
    """戦国の幟（のぼり）風の旗。"""
    x0, y0, x1, y1 = box
    d = c.draw
    d.line([x0, y0 - c.u(20), x0, y1 + c.u(120)], fill=hex2rgb("#7a5a2a"), width=c.u(10))
    d.line([x0, y0, x1, y0], fill=hex2rgb("#7a5a2a"), width=c.u(8))
    d.polygon([(x0, y0), (x1, y0), (x1, y1), ((x0 + x1) / 2, y1 - c.u(40)), (x0, y1)], fill=hex2rgb(color))
    cx, cy, r = (x0 + x1) / 2, y0 + (y1 - y0) * 0.35, (x1 - x0) * 0.28
    for k in range(5):  # 花形の紋（オリジナル意匠）
        a = 2 * math.pi * k / 5 - math.pi / 2
        px, py = cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55
        d.ellipse([px - r * 0.42, py - r * 0.42, px + r * 0.42, py + r * 0.42], fill=hex2rgb(emblem))
    d.ellipse([cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3], fill=hex2rgb(color))


# ---------------- アイコン ----------------
def checkbox(c: Canvas, box, border, fill=None, check_color=None, width=None) -> None:
    x0, y0, x1, y1 = box
    s = x1 - x0
    w = width or max(3, int(s * 0.1))
    c.draw.rounded_rectangle(box, radius=int(s * 0.12), outline=hex2rgb(border), width=w,
                             fill=hex2rgb(fill) if fill else None)
    if check_color:
        d = c.draw
        d.line([x0 + s * 0.18, y0 + s * 0.5, x0 + s * 0.42, y0 + s * 0.74, x0 + s * 1.05, y0 - s * 0.08],
               fill=hex2rgb(check_color), width=max(4, int(s * 0.17)), joint="curve")


def number_badge(c: Canvas, center, r, number: str, fill, text_color, fonts_role="serif") -> None:
    x, y = center
    c.draw.ellipse([x - r, y - r, x + r, y + r], fill=hex2rgb(fill), outline=hex2rgb("#ffffff"), width=max(2, r // 9))
    font = c.fonts.get(fonts_role, int(r * 1.35))
    c.draw.text((x, y + r * 0.05), number, font=font, anchor="mm", fill=hex2rgb(text_color))


def bookmark(c: Canvas, box, color, inner="#ffffff") -> None:
    x0, y0, x1, y1 = box
    d = c.draw
    d.rounded_rectangle(box, radius=(x1 - x0) // 6, fill=hex2rgb(color))
    w = (x1 - x0) * 0.42
    cx = (x0 + x1) / 2
    d.polygon([(cx - w / 2, y0 + (y1 - y0) * 0.22), (cx + w / 2, y0 + (y1 - y0) * 0.22),
               (cx + w / 2, y1 - (y1 - y0) * 0.18), (cx, y1 - (y1 - y0) * 0.36), (cx - w / 2, y1 - (y1 - y0) * 0.18)],
              fill=hex2rgb(inner))


def icon(c: Canvas, name: str, box, ink="#3a2a20", accent="#c8202f", paper="#ffffff") -> None:
    """内容に合わせた小さなイラスト（文字は描かない）。"""
    x0, y0, x1, y1 = box
    s = min(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d = c.draw
    lw = max(3, int(s * 0.06))
    ink, accent, paper = hex2rgb(ink), hex2rgb(accent), hex2rgb(paper)
    if name == "book":
        d.polygon([(cx, cy - s * 0.28), (cx - s * 0.48, cy - s * 0.38), (cx - s * 0.48, cy + s * 0.3), (cx, cy + s * 0.4)],
                  fill=paper, outline=ink, width=lw)
        d.polygon([(cx, cy - s * 0.28), (cx + s * 0.48, cy - s * 0.38), (cx + s * 0.48, cy + s * 0.3), (cx, cy + s * 0.4)],
                  fill=paper, outline=ink, width=lw)
        for k in range(3):
            yy = cy - s * 0.16 + k * s * 0.15
            d.line([cx - s * 0.38, yy - s * 0.04, cx - s * 0.1, yy], fill=ink, width=max(2, lw // 2))
            d.line([cx + s * 0.1, yy, cx + s * 0.38, yy - s * 0.04], fill=ink, width=max(2, lw // 2))
    elif name == "pencil":
        a = math.radians(-40)
        L, W = s * 0.9, s * 0.16
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        bx, by = cx - dx * L / 2, cy - dy * L / 2
        tx, ty = cx + dx * L / 2, cy + dy * L / 2
        body = [(bx + px * W / 2, by + py * W / 2), (tx - dx * W + px * W / 2, ty - dy * W + py * W / 2),
                (tx - dx * W - px * W / 2, ty - dy * W - py * W / 2), (bx - px * W / 2, by - py * W / 2)]
        d.polygon(body, fill=(52, 140, 80), outline=ink)
        d.polygon([body[1], (tx, ty), body[2]], fill=(240, 210, 160), outline=ink)
    elif name == "calendar":
        d.rounded_rectangle([cx - s * 0.42, cy - s * 0.34, cx + s * 0.42, cy + s * 0.4], radius=s * 0.06, fill=paper,
                            outline=ink, width=lw)
        d.rectangle([cx - s * 0.42, cy - s * 0.34, cx + s * 0.42, cy - s * 0.16], fill=accent)
        for k in (-0.22, 0.22):
            d.line([cx + s * k, cy - s * 0.44, cx + s * k, cy - s * 0.26], fill=ink, width=lw)
        for r in range(3):
            for q in range(4):
                gx, gy = cx - s * 0.3 + q * s * 0.2, cy - s * 0.04 + r * s * 0.14
                d.rectangle([gx - s * 0.05, gy - s * 0.04, gx + s * 0.05, gy + s * 0.04], fill=(200, 190, 170))
    elif name == "note":
        d.rounded_rectangle([cx - s * 0.32, cy - s * 0.42, cx + s * 0.36, cy + s * 0.42], radius=s * 0.05, fill=paper,
                            outline=ink, width=lw)
        for k in range(5):
            yy = cy - s * 0.32 + k * s * 0.16
            d.ellipse([cx - s * 0.4, yy - s * 0.04, cx - s * 0.28, yy + s * 0.04], outline=ink, width=max(2, lw // 2))
        for k in range(3):
            yy = cy - s * 0.18 + k * s * 0.2
            d.line([cx - s * 0.08, yy, cx + s * 0.04, yy + s * 0.08, cx + s * 0.2, yy - s * 0.1], fill=accent,
                   width=max(2, lw // 2))
            d.line([cx + s * 0.06, yy + s * 0.02, cx + s * 0.28, yy + s * 0.02], fill=ink, width=max(2, lw // 3))
    elif name == "chart":
        for k, hgt in enumerate((0.25, 0.45, 0.65, 0.85)):
            bx = cx - s * 0.42 + k * s * 0.22
            d.rectangle([bx, cy + s * 0.42 - s * hgt * 0.8, bx + s * 0.14, cy + s * 0.42], fill=accent)
        d.line([cx - s * 0.45, cy + s * 0.15, cx - s * 0.1, cy - s * 0.05, cx + s * 0.05, cy + s * 0.05,
                cx + s * 0.42, cy - s * 0.38], fill=ink, width=lw)
        d.polygon([(cx + s * 0.46, cy - s * 0.44), (cx + s * 0.3, cy - s * 0.4), (cx + s * 0.42, cy - s * 0.28)], fill=ink)
    elif name == "card":
        for k in (2, 1, 0):
            off = k * s * 0.07
            d.rounded_rectangle([cx - s * 0.42 + off, cy - s * 0.26 + off, cx + s * 0.4 + off, cy + s * 0.22 + off],
                                radius=s * 0.05, fill=paper, outline=ink, width=lw)
        d.ellipse([cx - s * 0.48, cy - s * 0.14, cx - s * 0.3, cy + s * 0.04], outline=(200, 160, 60), width=lw)
        d.line([cx - s * 0.15, cy - s * 0.06, cx + s * 0.28, cy - s * 0.06], fill=accent, width=lw)
        d.line([cx - s * 0.15, cy + s * 0.06, cx + s * 0.18, cy + s * 0.06], fill=ink, width=max(2, lw // 2))
    elif name == "clock":
        d.ellipse([cx - s * 0.42, cy - s * 0.42, cx + s * 0.42, cy + s * 0.42], fill=paper, outline=ink, width=lw)
        d.line([cx, cy, cx, cy - s * 0.28], fill=ink, width=lw)
        d.line([cx, cy, cx + s * 0.2, cy + s * 0.08], fill=accent, width=lw)
    elif name == "star":
        pts = []
        for k in range(10):
            r = s * (0.45 if k % 2 == 0 else 0.2)
            a = math.pi / 5 * k - math.pi / 2
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        d.polygon(pts, fill=(245, 196, 60), outline=ink)
    elif name == "target":
        for k, col in enumerate((accent, paper, accent, paper)):
            r = s * (0.44 - k * 0.1)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col, outline=ink, width=max(2, lw // 2))
        d.line([cx, cy, cx + s * 0.45, cy - s * 0.45], fill=ink, width=lw)
    else:  # check
        d.ellipse([cx - s * 0.42, cy - s * 0.42, cx + s * 0.42, cy + s * 0.42], fill=accent)
        d.line([cx - s * 0.2, cy, cx - s * 0.04, cy + s * 0.18, cx + s * 0.24, cy - s * 0.18], fill=paper, width=lw * 2)


def emphasis_accent(c: Canvas, origin, size, color) -> None:
    """吹き出し横の「ﾋﾟｶｯ」線。"""
    burst_lines(c, origin, size, color, n=3, angle=-60, spread=60)


def blur_shadow_rect(c: Canvas, box, radius, alpha=90) -> None:
    lay = c.layer()
    ImageDraw.Draw(lay).rounded_rectangle(box, radius=radius, fill=(0, 0, 0, alpha))
    c.blur_paste(lay, c.u(12))
