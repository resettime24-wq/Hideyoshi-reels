"""LLM（大規模言語モデル）プロバイダ。"""

from __future__ import annotations

from ..config import Settings


def create_llm(settings: Settings):
    """実際に使う LLM クライアントを返す。モックの場合は None。"""
    if settings.llm_provider() == "claude":
        from .claude import ClaudeClient

        return ClaudeClient(settings.anthropic_api_key, settings.claude_model, settings.claude_effort)
    return None
