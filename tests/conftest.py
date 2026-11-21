import shutil
from pathlib import Path

import pytest

from hideyoshi_reels.config import PROJECT_ROOT, load_settings


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """本物の APIキーや履歴に触れない、テスト専用の設定。"""
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "VOICEVOX_URL", "HR_MODE", "TTS_PROVIDER",
                "IMAGE_PROVIDER", "OUTPUT_DIR"):
        monkeypatch.setenv(key, "")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("mock_topics.yaml", "verified_facts.yaml"):
        shutil.copy(PROJECT_ROOT / "data" / name, data_dir / name)
    s = load_settings(env_file=tmp_path / "none.env", mode="mock")
    s.data_dir = data_dir
    s.output_dir = tmp_path / "output"
    return s


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT
