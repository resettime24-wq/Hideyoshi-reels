"""画像生成プロバイダ。新しいAPIを追加する場合は ImageProvider を継承してください。"""

from __future__ import annotations

import base64
import io
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class ImageProvider(ABC):
    name = "base"
    is_mock = False

    @abstractmethod
    def generate(self, prompt: str, size: str = "1024x1536", transparent: bool = False) -> Image.Image:
        """プロンプトから画像を生成する。"""

    def edit(self, references: list[Path], prompt: str, size: str = "1024x1536",
             transparent: bool = False) -> Image.Image:
        """参照画像をもとに画像を生成する（キャラの一貫性維持用）。未対応なら generate を使う。"""
        return self.generate(prompt, size=size, transparent=transparent)


class OpenAIImageProvider(ImageProvider):
    """OpenAI 画像API（gpt-image-1 など）。"""

    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-image-1", quality: str = "medium"):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, max_retries=3, timeout=300)
        self.model = model
        self.quality = quality
        self.images_generated = 0

    @staticmethod
    def _decode(result) -> Image.Image:
        data = result.data[0]
        if getattr(data, "b64_json", None):
            return Image.open(io.BytesIO(base64.b64decode(data.b64_json))).convert("RGBA")
        import requests

        resp = requests.get(data.url, timeout=60)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")

    def generate(self, prompt, size="1024x1536", transparent=False):
        logger.info("画像生成API呼び出し（%s, %s）", self.model, size)
        result = self.client.images.generate(
            model=self.model, prompt=prompt, size=size, quality=self.quality, n=1,
            background="transparent" if transparent else "opaque",
        )
        self.images_generated += 1
        return self._decode(result)

    def edit(self, references, prompt, size="1024x1536", transparent=False):
        logger.info("参照画像つき画像生成API呼び出し（参照 %d 枚）", len(references))
        files = [open(p, "rb") for p in references]
        try:
            result = self.client.images.edit(
                model=self.model, image=files, prompt=prompt, size=size, quality=self.quality, n=1,
                background="transparent" if transparent else "opaque",
            )
        finally:
            for f in files:
                f.close()
        self.images_generated += 1
        return self._decode(result)


class MockImageProvider(ImageProvider):
    """APIを使わずプログラムで描画する（テスト・デモ用）。"""

    name = "mock"
    is_mock = True

    def generate(self, prompt, size="1024x1536", transparent=False):
        from .mock_art import draw_background

        w, h = (int(v) for v in size.split("x"))
        return draw_background("explanation", size=(w, h)).convert("RGBA")


def create_image_provider(settings) -> ImageProvider:
    if settings.resolved_image_provider() == "openai":
        return OpenAIImageProvider(settings.openai_api_key, settings.openai_image_model, settings.image_quality)
    return MockImageProvider()
