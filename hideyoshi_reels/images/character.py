"""キャラクター（ちび秀吉）の設定と表情素材の管理。

素材の優先順位:
  1. assets/character/expressions/<表情>.png  … 登録済みの正式素材（毎回これを使う）
  2. 画像生成APIで作成（参照画像 assets/character/reference/*.png があればそれを元に）
     → 1. に保存して次回から使い回す（＝毎回同じ見た目になる）
  3. APIが無い場合: プログラムで描いた仮のオリジナル素材（assets/character/mock/）
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from PIL import Image

from ..models import EXPRESSIONS
from .mock_art import draw_character
from .providers import ImageProvider

logger = logging.getLogger(__name__)

CONSISTENCY_PROMPT = (
    "Use the reference image as the exact same character. Keep the identical face, helmet, "
    "golden sunburst crest, outfit, colors, line style and proportions. "
    "Change only the facial expression and pose as follows: "
)


def trim_alpha(img: Image.Image, pad: int = 12) -> Image.Image:
    img = img.convert("RGBA")
    bbox = img.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    return img.crop((max(0, l - pad), max(0, t - pad), min(img.width, r + pad), min(img.height, b + pad)))


class CharacterManager:
    def __init__(self, character_dir: Path, provider: ImageProvider):
        self.dir = character_dir
        self.provider = provider
        self.spec = yaml.safe_load((character_dir / "character.yaml").read_text(encoding="utf-8"))
        self.expressions_dir = character_dir / "expressions"
        self.reference_dir = character_dir / "reference"
        self.mock_dir = character_dir / "mock"
        self.generated: list[str] = []

    def references(self) -> list[Path]:
        if not self.reference_dir.exists():
            return []
        return sorted(p for p in self.reference_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})

    def expression_prompt(self, expression: str) -> str:
        return f"{self.spec['base_prompt']}. Expression and pose: {self.spec['expressions'][expression]}"

    def sprite_path(self, expression: str) -> Path:
        registered = self.expressions_dir / f"{expression}.png"
        if registered.exists():
            return registered
        if self.provider.is_mock:
            return self._mock_sprite(expression)
        return self._generate_sprite(expression)

    def ensure_all(self) -> dict[str, Path]:
        # 参照画像が無い状態で本番生成する場合は、まず「解説」を作って参照画像にする
        order = ["explaining"] + [e for e in EXPRESSIONS if e != "explaining"]
        return {e: self.sprite_path(e) for e in order}

    def _mock_sprite(self, expression: str) -> Path:
        self.mock_dir.mkdir(parents=True, exist_ok=True)
        path = self.mock_dir / f"{expression}.png"
        if not path.exists():
            trim_alpha(draw_character(expression)).save(path)
        return path

    def _generate_sprite(self, expression: str) -> Path:
        self.expressions_dir.mkdir(parents=True, exist_ok=True)
        refs = self.references()
        prompt = self.expression_prompt(expression)
        if refs:
            img = self.provider.edit(refs[:4], CONSISTENCY_PROMPT + self.spec["expressions"][expression] +
                                     ". Transparent background, full body.", size="1024x1536", transparent=True)
        else:
            logger.info("参照画像が未登録のため、最初の1枚を生成して参照画像として保存します")
            img = self.provider.generate(prompt, size="1024x1536", transparent=True)
            self.reference_dir.mkdir(parents=True, exist_ok=True)
            img.save(self.reference_dir / "auto_reference.png")
        path = self.expressions_dir / f"{expression}.png"
        trim_alpha(img).save(path)
        self.generated.append(expression)
        logger.info("表情素材を生成・保存しました: %s", path)
        return path
