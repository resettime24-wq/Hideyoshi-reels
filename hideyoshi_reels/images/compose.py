"""場面画像（背景＋キャラ＋見出し）と字幕画像の合成。"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .mock_art import draw_background
from .providers import ImageProvider

logger = logging.getLogger(__name__)

NO_LINE_START = set("、。，．・：；？！ー～）」』】〉》ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ!?…")
DARK = (40, 28, 24)


def wrap_japanese(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """日本語を指定幅で改行する（簡易禁則処理つき・行の長さをなるべく均等にする）。"""
    lines = _greedy_wrap(text, font, max_width)
    if len(lines) > 1 and "\n" not in text:
        balanced_width = font.getlength(text) / len(lines) * 1.08
        balanced = _greedy_wrap(text, font, int(balanced_width))
        if len(balanced) == len(lines):
            return balanced
    return lines


def _greedy_wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        if ch == "\n":
            lines.append(current)
            current = ""
            continue
        if font.getlength(current + ch) <= max_width or not current:
            current += ch
        elif ch in NO_LINE_START:
            current += ch  # 行頭禁則: 句読点などは前の行にぶら下げる
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def fit_font(text: str, font_path: str, max_width: int, max_lines: int, start: int, minimum: int):
    size = start
    while size >= minimum:
        font = ImageFont.truetype(font_path, size)
        lines = wrap_japanese(text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
        size -= 4
    font = ImageFont.truetype(font_path, minimum)
    return font, wrap_japanese(text, font, max_width)


def cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS)


class SceneComposer:
    def __init__(self, width: int, height: int, font_path: str, account_handle: str,
                 provider: ImageProvider, background_mode: str, bg_suffix: str = ""):
        self.w, self.h = width, height
        self.font_path = font_path
        self.handle = account_handle
        self.provider = provider
        self.background_mode = background_mode
        self.bg_suffix = bg_suffix
        self._bg_cache: dict[str, Image.Image] = {}
        self.ai_backgrounds = 0

    def k(self, v: float) -> int:  # 1080幅基準の座標を実サイズへ
        return int(v * self.w / 1080)

    # ---------- 背景 ----------
    def background(self, section: str, prompt: str, seed: int) -> Image.Image:
        key = hashlib.md5(f"{self.background_mode}|{section}|{prompt}".encode()).hexdigest()
        if key in self._bg_cache:
            return self._bg_cache[key]
        if self.background_mode == "ai" and not self.provider.is_mock:
            try:
                img = self.provider.generate(f"{prompt}. {self.bg_suffix}", size="1024x1536")
                img = cover(img, (self.w, self.h)).filter(ImageFilter.GaussianBlur(self.k(2)))
                self.ai_backgrounds += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("背景画像の生成に失敗したため、プログラム描画の背景を使います: %s", exc)
                img = draw_background(section, (self.w, self.h), seed)
        else:
            img = draw_background(section, (self.w, self.h), seed)
        self._bg_cache[key] = img
        return img

    # ---------- 場面画像 ----------
    def compose_scene(self, section: str, image_prompt: str, sprite_path: Path, telop: str,
                      out_path: Path, seed: int = 0) -> Path:
        canvas = self.background(section, image_prompt, seed).convert("RGBA")
        d = ImageDraw.Draw(canvas)

        # ブランドタグ（左上）
        tag_font = ImageFont.truetype(self.font_path, self.k(34))
        tag = f"早稲田受験 × ちび秀吉  {self.handle}"
        tw = tag_font.getlength(tag)
        d.rounded_rectangle([self.k(40), self.k(120), self.k(40) + tw + self.k(40), self.k(180)],
                            radius=self.k(30), fill=(0, 0, 0, 110))
        d.text((self.k(60), self.k(150)), tag, font=tag_font, fill="white", anchor="lm")

        # キャラクター
        sprite = Image.open(sprite_path).convert("RGBA")
        target_h = self.k(980)
        scale = min(target_h / sprite.height, self.k(900) / sprite.width)
        sprite = sprite.resize((int(sprite.width * scale), int(sprite.height * scale)), Image.LANCZOS)
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        cx, base_y = self.w // 2, self.k(1500)
        sd.ellipse([cx - self.k(300), base_y - self.k(40), cx + self.k(300), base_y + self.k(40)], fill=(0, 0, 0, 70))
        canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(self.k(14))))
        canvas.alpha_composite(sprite, (cx - sprite.width // 2, base_y - sprite.height))

        # 見出し（上部の帯）
        self._telop(canvas, telop)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(out_path, quality=95)
        return out_path

    def _telop(self, canvas: Image.Image, telop: str) -> None:
        d = ImageDraw.Draw(canvas)
        font, lines = fit_font(telop, self.font_path, self.k(880), 2, self.k(110), self.k(64))
        line_h = int(font.size * 1.18)
        box_h = line_h * len(lines) + self.k(70)
        top = self.k(230)
        d.rounded_rectangle([self.k(50), top, self.w - self.k(50), top + box_h], radius=self.k(36),
                            fill=(200, 50, 43, 240), outline=(242, 194, 48, 255), width=self.k(10))
        y = top + self.k(35) + line_h // 2
        for line in lines:
            d.text((self.w // 2, y), line, font=font, fill="white", anchor="mm",
                   stroke_width=self.k(8), stroke_fill=DARK)
            y += line_h

    # ---------- 字幕画像 ----------
    def subtitle_overlay(self, text: str, out_path: Path) -> Path:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        font, lines = fit_font(text, self.font_path, self.k(860), 2, self.k(66), self.k(48))
        line_h = int(font.size * 1.35)
        box_h = line_h * len(lines) + self.k(56)
        top = self.k(1330)
        d.rounded_rectangle([self.k(60), top, self.w - self.k(60), top + box_h], radius=self.k(28),
                            fill=(255, 255, 255, 235), outline=(40, 28, 24, 255), width=self.k(6))
        y = top + self.k(28) + line_h // 2
        for line in lines:
            d.text((self.w // 2, y), line, font=font, fill=DARK, anchor="mm",
                   stroke_width=max(1, self.k(2)), stroke_fill=DARK)
            y += line_h
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return out_path
