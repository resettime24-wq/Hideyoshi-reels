"""設定値の読み込み。

すべての設定は環境変数（または .env ファイル）から読み込みます。
APIキーはコードに直接書かず、必ず環境変数 / GitHub Secrets で渡してください。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # python-dotenv が無くても動くようにする
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent

POST_FORMATS = ("reel", "feed", "carousel")
DESIGN_STYLES = ("auto", "A", "B", "C", "D")

# 投稿形式ごとの画像サイズ
SIZES = {"reel": (1080, 1920), "feed": (1080, 1350), "carousel": (1080, 1350)}


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name, "")
    return value.strip() if value.strip() else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


@dataclass
class Settings:
    # --- 動作モード ---
    # auto: APIキーがあるものは本番API、無いものはモック / mock: すべてモック
    mode: str = "auto"
    strict: bool = False  # True: API失敗時にモックへ切り替えず停止する

    # --- 投稿形式・デザイン ---
    post_format: str = "reel"  # reel / feed / carousel
    design_style: str = "auto"  # auto / A / B / C / D
    reel_seconds: float = 10.0
    fps: int = 30
    carousel_max_slides: int = 6

    # --- Claude（Trend: 分析・企画・原稿 / Monetization） ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "medium"
    factcheck_web_search: bool = True
    trend_web_search: bool = True

    # --- キャラクター画像生成 ---
    openai_api_key: str = ""
    image_provider: str = "auto"  # auto / openai / mock
    openai_image_model: str = "gpt-image-1"
    image_quality: str = "medium"  # low / medium / high

    # --- 収益化 ---
    note_url: str = ""  # 有料note等のURL（未設定ならキャプションに誘導文を入れない）
    affiliate_enabled: bool = False  # True: アフィリエイト導線の提案をキャプションに反映

    # --- 文字 ---
    font_path: str = ""

    # --- パス ---
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "output")
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    assets_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "assets")

    # --- アカウント情報 ---
    account_handle: str = "@waseda.jyukengoukaku"

    @property
    def character_dir(self) -> Path:
        return self.assets_dir / "character"

    @property
    def history_path(self) -> Path:
        return self.data_dir / "history.json"

    @property
    def size(self) -> tuple[int, int]:
        return SIZES[self.post_format]

    def validate(self) -> None:
        if self.post_format not in POST_FORMATS:
            raise ValueError(f"POST_FORMAT は {POST_FORMATS} のいずれかにしてください: {self.post_format}")
        if self.design_style not in DESIGN_STYLES:
            raise ValueError(f"DESIGN_STYLE は {DESIGN_STYLES} のいずれかにしてください: {self.design_style}")

    # --- 各工程で実際に使うプロバイダを判定 ---
    def llm_provider(self) -> str:
        if self.mode == "mock" or not self.anthropic_api_key:
            return "mock"
        return "claude"

    def resolved_image_provider(self) -> str:
        if self.mode == "mock":
            return "mock"
        if self.image_provider == "auto":
            return "openai" if self.openai_api_key else "mock"
        if self.image_provider == "openai" and not self.openai_api_key:
            return "mock"
        return self.image_provider


def load_settings(env_file: str | Path | None = None, **overrides) -> Settings:
    """環境変数から Settings を作る。overrides でテストやCLIから上書き可能。"""
    if load_dotenv is not None:
        load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)

    design = _env("DESIGN_STYLE", "auto")
    settings = Settings(
        mode=_env("HR_MODE", "auto").lower(),
        strict=_env_bool("HR_STRICT", False),
        post_format=_env("POST_FORMAT", "reel").lower(),
        design_style=design.upper() if design.lower() != "auto" else "auto",
        reel_seconds=_env_float("REEL_SECONDS", 10.0),
        carousel_max_slides=int(_env_float("CAROUSEL_MAX_SLIDES", 6)),
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        claude_model=_env("CLAUDE_MODEL", "claude-opus-5-5"),
        claude_effort=_env("CLAUDE_EFFORT", "medium"),
        factcheck_web_search=_env_bool("FACTCHECK_WEB_SEARCH", True),
        trend_web_search=_env_bool("TREND_WEB_SEARCH", True),
        openai_api_key=_env("OPENAI_API_KEY"),
        image_provider=_env("IMAGE_PROVIDER", "auto").lower(),
        openai_image_model=_env("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        image_quality=_env("IMAGE_QUALITY", "medium"),
        note_url=_env("NOTE_URL"),
        affiliate_enabled=_env_bool("AFFILIATE_ENABLED", False),
        font_path=_env("FONT_PATH"),
        account_handle=_env("ACCOUNT_HANDLE", "@waseda.jyukengoukaku"),
    )
    if _env("OUTPUT_DIR"):
        settings.output_dir = Path(_env("OUTPUT_DIR"))
    for key, value in overrides.items():
        if value is not None:
            setattr(settings, key, value)
    return settings
