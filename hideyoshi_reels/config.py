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

    # --- Claude（企画・台本・ファクトチェック） ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "medium"
    factcheck_web_search: bool = True

    # --- 画像生成 ---
    openai_api_key: str = ""
    image_provider: str = "auto"  # auto / openai / mock
    openai_image_model: str = "gpt-image-1"
    image_quality: str = "medium"  # low / medium / high
    background_mode: str = "auto"  # auto / ai / procedural

    # --- 音声 ---
    tts_provider: str = "auto"  # auto / openai / voicevox / mock
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "onyx"
    voicevox_url: str = ""
    voicevox_speaker: int = 13  # 13 = 青山龍星（ノーマル）
    voicevox_credit: str = "VOICEVOX:青山龍星"
    bgm_enabled: bool = True

    # --- 動画 ---
    width: int = 1080
    height: int = 1920
    fps: int = 30
    min_seconds: float = 20.0
    max_seconds: float = 35.0
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

    def resolved_background_mode(self) -> str:
        if self.background_mode in {"ai", "procedural"}:
            if self.background_mode == "ai" and self.resolved_image_provider() == "mock":
                return "procedural"
            return self.background_mode
        return "ai" if self.resolved_image_provider() != "mock" else "procedural"

    def resolved_tts_provider(self) -> str:
        if self.mode == "mock":
            return "mock"
        provider = self.tts_provider
        if provider == "auto":
            if self.voicevox_url:
                return "voicevox"
            return "openai" if self.openai_api_key else "mock"
        if provider == "openai" and not self.openai_api_key:
            return "mock"
        if provider == "voicevox" and not self.voicevox_url:
            return "mock"
        return provider


def load_settings(env_file: str | Path | None = None, **overrides) -> Settings:
    """環境変数から Settings を作る。overrides でテストやCLIから上書き可能。"""
    if load_dotenv is not None:
        load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)

    settings = Settings(
        mode=_env("HR_MODE", "auto").lower(),
        strict=_env_bool("HR_STRICT", False),
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        claude_model=_env("CLAUDE_MODEL", "claude-opus-5-5"),
        claude_effort=_env("CLAUDE_EFFORT", "medium"),
        factcheck_web_search=_env_bool("FACTCHECK_WEB_SEARCH", True),
        openai_api_key=_env("OPENAI_API_KEY"),
        image_provider=_env("IMAGE_PROVIDER", "auto").lower(),
        openai_image_model=_env("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        image_quality=_env("IMAGE_QUALITY", "medium"),
        background_mode=_env("BACKGROUND_MODE", "auto").lower(),
        tts_provider=_env("TTS_PROVIDER", "auto").lower(),
        openai_tts_model=_env("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        openai_tts_voice=_env("OPENAI_TTS_VOICE", "onyx"),
        voicevox_url=_env("VOICEVOX_URL").rstrip("/"),
        voicevox_speaker=int(_env("VOICEVOX_SPEAKER", "13")),
        voicevox_credit=_env("VOICEVOX_CREDIT", "VOICEVOX:青山龍星"),
        bgm_enabled=_env_bool("BGM_ENABLED", True),
        min_seconds=_env_float("MIN_SECONDS", 20.0),
        max_seconds=_env_float("MAX_SECONDS", 35.0),
        font_path=_env("FONT_PATH"),
        account_handle=_env("ACCOUNT_HANDLE", "@waseda.jyukengoukaku"),
    )
    if _env("OUTPUT_DIR"):
        settings.output_dir = Path(_env("OUTPUT_DIR"))
    for key, value in overrides.items():
        if value is not None:
            setattr(settings, key, value)
    return settings
