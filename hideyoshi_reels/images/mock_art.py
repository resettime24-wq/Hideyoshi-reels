"""APIキー無しで使える「仮のオリジナルキャラクター素材」と背景をプログラムで描画する。

外部素材を一切使わず Pillow の図形描画だけで作るため、著作権上の問題がありません。
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

S = 2  # 2倍サイズで描いて縮小し、線を滑らかにする
W, H = 1024, 1280

GOLD = (242, 194, 48)
GOLD_DARK = (201, 148, 22)
RED = (200, 50, 43)
RED_DARK = (150, 32, 30)
BLACK = (43, 43, 51)
SKIN = (255, 217, 184)
LINE = (52, 36, 30)
WHITE = (255, 255, 255)
BLUSH = (255, 150, 150)


def _p(*coords):
    return [c * S for c in coords]


def _rot_ellipse(cx, cy, rx, ry, angle, n=48):
    a = math.radians(angle)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append(((cx + x * math.cos(a) - y * math.sin(a)) * S, (cy + x * math.sin(a) + y * math.cos(a)) * S))
    return pts


def _sparkle(d: ImageDraw.ImageDraw, x, y, r, color=(255, 236, 120)):
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.35
        pts.append(((x + rr * math.cos(ang)) * S, (y + rr * math.sin(ang)) * S))
    d.polygon(pts, fill=color, outline=LINE, width=3 * S)


ARM_POSES = {
    # (手の位置 左, 右), 手が顔の前に来るか, 軍配の向き(度) / None
    "happy": {"left": (300, 960), "right": (790, 640), "front": set(), "fan": None},
    "surprised": {"left": (250, 700), "right": (774, 700), "front": set(), "fan": None},
    "angry": {"left": (330, 1000), "right": (780, 880), "front": set(), "fan": -55},
    "thinking": {"left": (440, 790), "right": (700, 990), "front": {"left"}, "fan": 110},
    "explaining": {"left": (320, 990), "right": (800, 800), "front": set(), "fan": -70},
}


def _arm(d, shoulder, hand):
    d.line([shoulder[0] * S, shoulder[1] * S, hand[0] * S, hand[1] * S], fill=LINE, width=74 * S)
    d.line([shoulder[0] * S, shoulder[1] * S, hand[0] * S, hand[1] * S], fill=RED, width=60 * S)
    d.ellipse(_p(hand[0] - 36, hand[1] - 36, hand[0] + 36, hand[1] + 36), fill=SKIN, outline=LINE, width=6 * S)


def _fan(d, hand, angle):
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    tip = (hand[0] + dx * 90, hand[1] + dy * 90)
    d.line([hand[0] * S, hand[1] * S, tip[0] * S, tip[1] * S], fill=LINE, width=22 * S)
    d.line([hand[0] * S, hand[1] * S, tip[0] * S, tip[1] * S], fill=GOLD_DARK, width=12 * S)
    cx, cy = hand[0] + dx * 160, hand[1] + dy * 160
    d.polygon(_rot_ellipse(cx, cy, 95, 80, angle), fill=BLACK, outline=LINE)
    d.line(_rot_ellipse(cx, cy, 95, 80, angle) + [_rot_ellipse(cx, cy, 95, 80, angle)[0]], fill=LINE, width=6 * S)
    d.ellipse(_p(cx - 38, cy - 38, cx + 38, cy + 38), fill=RED)
    d.ellipse(_p(cx - 52, cy - 52, cx + 52, cy + 52), outline=GOLD, width=8 * S)


def draw_character(expression: str, seed: int = 0) -> Image.Image:
    """ちび秀吉（仮素材）を1枚描く。背景は透過。"""
    rng = random.Random(seed)
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pose = ARM_POSES.get(expression, ARM_POSES["explaining"])
    shoulders = {"left": (400, 840), "right": (624, 840)}

    # --- 後光のような金の放射飾り（兜の後立） ---
    cx, cy = 512, 380
    for i in range(23):
        ang = math.radians(-180 + i * (180 / 22))
        w = math.radians(3.2)
        r = 400 if i % 2 == 0 else 340
        pts = [(cx * S, cy * S),
               ((cx + r * math.cos(ang - w)) * S, (cy + r * math.sin(ang - w)) * S),
               ((cx + r * math.cos(ang + w)) * S, (cy + r * math.sin(ang + w)) * S)]
        d.polygon(pts, fill=GOLD, outline=GOLD_DARK)
        d.line(pts + [pts[0]], fill=LINE, width=3 * S)

    # --- 体（袴・陣羽織） ---
    d.polygon([_p(400, 960)[0], _p(400, 960)[1], *_p(624, 960), *_p(690, 1170), *_p(334, 1170)],
              fill=BLACK, outline=LINE, width=6 * S)
    d.line(_p(512, 990, 512, 1170), fill=(70, 70, 82), width=6 * S)
    d.ellipse(_p(330, 1150, 480, 1210), fill=BLACK, outline=LINE, width=6 * S)
    d.ellipse(_p(544, 1150, 694, 1210), fill=BLACK, outline=LINE, width=6 * S)
    d.rounded_rectangle(_p(380, 780, 644, 990), radius=60 * S, fill=RED, outline=LINE, width=6 * S)
    d.polygon([*_p(470, 790), *_p(554, 790), *_p(512, 880)], fill=WHITE, outline=LINE, width=4 * S)
    d.rectangle(_p(384, 905, 640, 950), fill=GOLD, outline=LINE, width=5 * S)
    for x in (430, 594):  # 家紋風の丸（オリジナル意匠）
        d.ellipse(_p(x - 18, 828, x + 18, 864), fill=GOLD, outline=LINE, width=3 * S)

    for side in ("left", "right"):
        if side not in pose["front"]:
            _arm(d, shoulders[side], pose[side])
    if pose["fan"] is not None:
        _fan(d, pose["right"], pose["fan"])

    # --- 頭 ---
    d.ellipse(_p(212, 300, 812, 830), fill=SKIN, outline=LINE, width=7 * S)
    d.ellipse(_p(190, 560, 250, 650), fill=SKIN, outline=LINE, width=6 * S)  # 耳
    d.ellipse(_p(774, 560, 834, 650), fill=SKIN, outline=LINE, width=6 * S)
    d.ellipse(_p(212, 300, 812, 830), outline=LINE, width=7 * S)

    # --- 兜 ---
    d.chord(_p(196, 240, 828, 720), start=180, end=360, fill=GOLD, outline=LINE, width=7 * S)
    for x in range(260, 800, 70):
        d.line(_p(x, 300 if 330 < x < 700 else 380, 512 + (x - 512) * 1.15, 478), fill=GOLD_DARK, width=4 * S)
    d.rounded_rectangle(_p(150, 455, 874, 515), radius=28 * S, fill=GOLD_DARK, outline=LINE, width=7 * S)
    d.ellipse(_p(472, 330, 552, 410), fill=RED, outline=LINE, width=5 * S)  # 前立の赤い日輪

    # --- 顔 ---
    ex_l, ex_r, ey = 400, 624, 615
    d.ellipse(_p(320, 660, 390, 700), fill=BLUSH)
    d.ellipse(_p(634, 660, 704, 700), fill=BLUSH)

    def round_eye(x, look=(0, 0), big=False):
        rx, ry = (50, 62) if not big else (56, 70)
        d.ellipse(_p(x - rx, ey - ry, x + rx, ey + ry), fill=BLACK)
        hx, hy = x - 16 + look[0], ey - 24 + look[1]
        d.ellipse(_p(hx - 17, hy - 17, hx + 17, hy + 17), fill=WHITE)
        d.ellipse(_p(x + 14 + look[0], ey + 18 + look[1], x + 26 + look[0], ey + 30 + look[1]), fill=WHITE)

    def arc_eye(x, up=True):
        box = _p(x - 48, ey - 30, x + 48, ey + 40) if up else _p(x - 48, ey - 50, x + 48, ey + 20)
        d.arc(box, start=200 if up else 20, end=340 if up else 160, fill=LINE, width=12 * S)

    def brow(x, tilt, raise_=0):
        y = 552 - raise_
        d.line(_p(x - 45, y + tilt, x + 45, y - tilt), fill=LINE, width=12 * S)

    if expression == "happy":
        arc_eye(ex_l); arc_eye(ex_r)
        brow(ex_l, 0, 8); brow(ex_r, 0, 8)
        d.chord(_p(450, 690, 574, 790), start=0, end=180, fill=(190, 40, 50), outline=LINE, width=6 * S)
        d.ellipse(_p(488, 745, 536, 782), fill=(255, 120, 130))
        for _ in range(4):
            _sparkle(d, rng.choice([140, 170, 860, 890]), rng.randint(250, 700), rng.randint(26, 40))
    elif expression == "surprised":
        for x in (ex_l, ex_r):
            d.ellipse(_p(x - 56, ey - 64, x + 56, ey + 64), fill=WHITE, outline=LINE, width=7 * S)
            d.ellipse(_p(x - 20, ey - 20, x + 20, ey + 20), fill=BLACK)
        brow(ex_l, -6, 34); brow(ex_r, 6, 34)
        d.ellipse(_p(486, 710, 538, 778), fill=(190, 40, 50), outline=LINE, width=6 * S)
        d.polygon([*_p(800, 470), *_p(830, 540), *_p(770, 540)], fill=(140, 200, 255))
        d.ellipse(_p(768, 515, 832, 575), fill=(140, 200, 255), outline=LINE, width=4 * S)
        for i in range(3):  # 驚きの集中線
            d.line(_p(150 - i * 30, 330 + i * 60, 210 - i * 30, 370 + i * 60), fill=LINE, width=8 * S)
            d.line(_p(874 + i * 30, 330 + i * 60, 814 + i * 30, 370 + i * 60), fill=LINE, width=8 * S)
    elif expression == "angry":
        for x in (ex_l, ex_r):
            d.chord(_p(x - 50, ey - 50, x + 50, ey + 62), start=0, end=180, fill=BLACK)
        brow(ex_l, -18, -10); brow(ex_r, 18, -10)
        d.rounded_rectangle(_p(458, 715, 566, 760), radius=14 * S, fill=WHITE, outline=LINE, width=6 * S)
        d.line(_p(458, 737, 566, 737), fill=LINE, width=4 * S)
        mx, my = 770, 330  # 怒りマーク
        for a in (45, 135, 225, 315):
            r = math.radians(a)
            d.arc(_p(mx + 30 * math.cos(r) - 26, my + 30 * math.sin(r) - 26,
                     mx + 30 * math.cos(r) + 26, my + 30 * math.sin(r) + 26),
                  start=a + 90, end=a + 270, fill=(220, 30, 40), width=10 * S)
        d.ellipse(_p(250, 650, 330, 700), fill=(255, 120, 120))
        d.ellipse(_p(694, 650, 774, 700), fill=(255, 120, 120))
    elif expression == "thinking":
        round_eye(ex_l, look=(10, -14)); round_eye(ex_r, look=(10, -14))
        brow(ex_l, 6, 0); brow(ex_r, -10, 18)
        d.line(_p(480, 745, 548, 735), fill=LINE, width=10 * S)
        qx, qy = 860, 300
        d.arc(_p(qx - 45, qy - 60, qx + 45, qy + 20), start=180, end=90, fill=(70, 110, 220), width=16 * S)
        d.line(_p(qx, qy + 20, qx, qy + 55), fill=(70, 110, 220), width=16 * S)
        d.ellipse(_p(qx - 11, qy + 75, qx + 11, qy + 97), fill=(70, 110, 220))
    else:  # explaining
        round_eye(ex_l); arc_eye(ex_r, up=True)
        brow(ex_l, 0, 6); brow(ex_r, 0, 10)
        d.arc(_p(455, 680, 569, 770), start=10, end=170, fill=LINE, width=10 * S)
        _sparkle(d, 880, 520, 34)

    # 口ひげ（細く上向き）
    d.arc(_p(430, 650, 512, 700), start=200, end=330, fill=LINE, width=8 * S)
    d.arc(_p(512, 650, 594, 700), start=210, end=340, fill=LINE, width=8 * S)

    for side in pose["front"]:
        _arm(d, shoulders[side], pose[side])

    return img.resize((W, H), Image.LANCZOS)


# ---------------- 背景 ----------------
SECTION_COLORS = {
    "hook": ((255, 214, 92), (255, 120, 60)),
    "problem": ((92, 104, 168), (52, 52, 96)),
    "explanation": ((255, 248, 226), (250, 226, 180)),
    "conclusion": ((255, 222, 232), (255, 176, 200)),
}


def _gradient(size, top, bottom) -> Image.Image:
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return grad.resize((w, h))


def draw_background(section: str, size=(1080, 1920), seed: int = 0) -> Image.Image:
    rng = random.Random(seed)
    top, bottom = SECTION_COLORS.get(section, SECTION_COLORS["explanation"])
    img = _gradient(size, top, bottom).convert("RGBA")
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    w, h = size
    if section == "hook":  # 集中線・放射
        cx, cy = w / 2, h * 0.45
        for i in range(36):
            a1, a2 = 2 * math.pi * i / 36, 2 * math.pi * (i + 0.5) / 36
            d.polygon([(cx, cy), (cx + 2000 * math.cos(a1), cy + 2000 * math.sin(a1)),
                       (cx + 2000 * math.cos(a2), cy + 2000 * math.sin(a2))], fill=(255, 255, 255, 50))
    elif section == "problem":  # 青海波（和柄）
        r = 70
        for row in range(-1, h // (r // 2) + 2):
            for col in range(-1, w // (r * 2) + 2):
                x = col * r * 2 + (r if row % 2 else 0)
                y = row * r // 2
                for k in (1.0, 0.72, 0.44):
                    d.ellipse([x - r * k, y - r * k, x + r * k, y + r * k], outline=(255, 255, 255, 34), width=4)
    elif section == "explanation":  # ノート罫線
        for y in range(0, h, 64):
            d.line([0, y, w, y], fill=(120, 160, 210, 70), width=3)
        d.line([110, 0, 110, h], fill=(230, 120, 120, 90), width=4)
    else:  # 桜の花びら
        for _ in range(60):
            x, y, r = rng.randint(0, w), rng.randint(0, h), rng.randint(10, 26)
            d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(255, 255, 255, rng.randint(70, 150)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(1.2))
    return Image.alpha_composite(img, overlay).convert("RGB")
