"""Anthropic Claude API クライアント（企画・台本・キャプション・ファクトチェック）。"""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-opus-5-5", effort: str = "medium"):
        import anthropic  # 遅延 import（モックモードでは不要）

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=600)
        self.model = model
        self.effort = effort
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def _track(self, response) -> None:
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.usage["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
            self.usage["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
        logger.debug("Claude request_id=%s stop=%s", getattr(response, "_request_id", "?"),
                     getattr(response, "stop_reason", "?"))

    def _check_stop(self, response) -> None:
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise RuntimeError(f"Claude が応答を拒否しました: {details}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Claude の出力が max_tokens に達して途中で切れました")

    def structured(self, system: str, prompt: str, schema: type[T], max_tokens: int = 16000) -> T:
        """Pydantic モデルの形式で JSON を返させる（構造化出力）。"""
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            output_config={"effort": self.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        self._track(response)
        self._check_stop(response)
        parsed = response.parsed_output
        if parsed is None:
            raise RuntimeError("Claude の構造化出力を解析できませんでした")
        return parsed

    def research(self, system: str, prompt: str, max_searches: int = 8, max_tokens: int = 16000) -> str:
        """Web検索ツール付きで調査させ、最終テキストを返す。"""
        tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}]
        messages: list[dict] = [{"role": "user", "content": prompt}]
        response = None
        for _ in range(5):  # pause_turn の再開は最大5回
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools,
                output_config={"effort": self.effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
            self._track(response)
            if response.stop_reason != "pause_turn":
                break
            messages = [messages[0], {"role": "assistant", "content": response.content}]
        assert response is not None
        self._check_stop(response)
        return "\n".join(b.text for b in response.content if getattr(b, "type", "") == "text")


def extract_json(text: str) -> dict:
    """テキスト中の最後の JSON オブジェクトを取り出す。"""
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidates = fenced or re.findall(r"(\{.*\})", text, flags=re.S)
    for cand in reversed(candidates):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    raise ValueError("JSON が見つかりません")
