"""制作履歴の管理（企画の重複防止・言い回しの重複防止）。"""

from __future__ import annotations

import difflib
import logging
from pathlib import Path

from .utils import read_json, write_json

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.6


def _normalize(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum())


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


class History:
    """data/history.json に過去の企画を保存する。"""

    def __init__(self, path: Path):
        self.path = path
        data = read_json(path, default=None) or {"version": 1, "entries": []}
        self.entries: list[dict] = data.get("entries", [])

    # --- 参照 ---
    def titles(self) -> list[str]:
        return [e.get("title", "") for e in self.entries]

    def recent(self, n: int = 20) -> list[dict]:
        return self.entries[-n:]

    def recent_phrases(self, n: int = 10) -> dict[str, list[str]]:
        recent = self.recent(n)
        return {
            "hooks": [e.get("hook", "") for e in recent if e.get("hook")],
            "openings": [e.get("opening_phrase", "") for e in recent if e.get("opening_phrase")],
            "closings": [e.get("closing_phrase", "") for e in recent if e.get("closing_phrase")],
        }

    def is_duplicate(self, title: str, keywords: list[str] | None = None) -> bool:
        for entry in self.entries:
            if similarity(title, entry.get("title", "")) >= SIMILARITY_THRESHOLD:
                return True
            if keywords and entry.get("keywords"):
                a, b = set(keywords), set(entry["keywords"])
                if len(a) >= 3 and len(a & b) / len(a | b) >= 0.75:
                    return True
        return False

    # --- 追加・保存 ---
    def add(self, entry: dict) -> None:
        self.entries.append(entry)

    def save(self) -> None:
        write_json(self.path, {"version": 1, "entries": self.entries})
        logger.info("履歴を保存しました: %s（累計 %d 本）", self.path, len(self.entries))
