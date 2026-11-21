"""投稿・分析機能の拡張ポイント（今回は自動投稿を行いません）。

将来 Instagram Graph API による自動投稿やインサイト分析を追加するときは、
ここのインターフェースを実装したクラスを作り、pipeline から呼び出します。
投稿は必ず人間の承認（approval.json の status が approved）を経てから行う設計です。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


class NotApprovedError(RuntimeError):
    pass


@dataclass
class PostPackage:
    """投稿に必要なものをひとまとめにしたもの。output フォルダから作れる。"""

    post_format: str  # reel / feed / carousel
    media: list[Path]  # reel: [reel.mp4] / feed: [post_image.png] / carousel: [slide_01.png, ...]
    caption: str
    hashtags: list[str]
    output_dir: Path
    approval_status: str = "pending"

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> "PostPackage":
        design = json.loads((output_dir / "design.json").read_text(encoding="utf-8"))
        fmt = design["format"]
        if fmt == "reel":
            media = [output_dir / "reel.mp4"]
        elif fmt == "carousel":
            media = sorted((output_dir / "carousel").glob("slide_*.png"))
        else:
            media = [output_dir / "post_image.png"]
        approval = json.loads((output_dir / "approval.json").read_text(encoding="utf-8"))
        return cls(fmt, media, (output_dir / "caption.txt").read_text(encoding="utf-8"),
                   (output_dir / "hashtags.txt").read_text(encoding="utf-8").split(), output_dir,
                   approval.get("status", "pending"))

    def ensure_approved(self) -> None:
        if self.approval_status != "approved":
            raise NotApprovedError("人間の承認前です。approval.json の status を approved にしてください。")


class Publisher(ABC):
    @abstractmethod
    def publish(self, package: PostPackage) -> str:
        """投稿して投稿IDを返す（実装時は最初に package.ensure_approved() を呼ぶこと）。"""


class InsightsClient(ABC):
    @abstractmethod
    def fetch(self, media_id: str) -> dict:
        """再生数・保存数などの指標を取得する。"""
