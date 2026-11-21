"""投稿・分析機能の拡張ポイント（今回は自動投稿を行いません）。

将来 Instagram Graph API による自動投稿やインサイト分析を追加するときは、
ここのインターフェースを実装したクラスを作り、pipeline から呼び出します。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReelPackage:
    """投稿に必要なものをひとまとめにしたもの。output フォルダから作れる。"""

    video_path: Path
    caption: str
    hashtags: list[str]
    output_dir: Path

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> "ReelPackage":
        caption = (output_dir / "caption.txt").read_text(encoding="utf-8")
        hashtags = (output_dir / "hashtags.txt").read_text(encoding="utf-8").split()
        return cls(output_dir / "reel.mp4", caption, hashtags, output_dir)


class Publisher(ABC):
    @abstractmethod
    def publish(self, package: ReelPackage) -> str:
        """投稿して投稿IDを返す。"""


class InsightsClient(ABC):
    @abstractmethod
    def fetch(self, media_id: str) -> dict:
        """再生数・保存数などの指標を取得する。"""
