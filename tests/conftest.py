import shutil
from pathlib import Path

import pytest

from hideyoshi_reels.config import PROJECT_ROOT, load_settings


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """本物の APIキーや履歴に触れない、テスト専用の設定。"""
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "HR_MODE", "IMAGE_PROVIDER", "OUTPUT_DIR", "POST_FORMAT",
                "DESIGN_STYLE", "NOTE_URL", "AFFILIATE_ENABLED"):
        monkeypatch.setenv(key, "")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("mock_topics.yaml", "verified_facts.yaml", "trend_signals.yaml"):
        shutil.copy(PROJECT_ROOT / "data" / name, data_dir / name)
    s = load_settings(env_file=tmp_path / "none.env", mode="mock")
    s.data_dir = data_dir
    s.output_dir = tmp_path / "output"
    return s


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def mock_contents(project_root):
    """モック用ネタ帳の全原稿（PostContent）。"""
    import yaml

    from hideyoshi_reels.models import PostContent, PostItem

    out = []
    for t in yaml.safe_load((project_root / "data/mock_topics.yaml").read_text(encoding="utf-8"))["topics"]:
        post = dict(t["post"])
        post["items"] = [PostItem(**i) for i in post["items"]]
        out.append(PostContent(**post))
    return out


@pytest.fixture(scope="session")
def fonts():
    from hideyoshi_reels.factory.fonts import Fonts

    return Fonts()
