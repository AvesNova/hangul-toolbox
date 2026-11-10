"""LLM backend factory."""

from __future__ import annotations

import os

from .anthropic_client import DEFAULT_MODEL, AnthropicLLM
from .base import LLMClient, LLMError

__all__ = ["LLMClient", "LLMError", "create_llm", "DEFAULT_MODEL"]


def create_llm(
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> LLMClient:
    """Instantiate an LLM backend by provider name.

    Providers:
        anthropic  — Claude via the official SDK (default model claude-sonnet-5-5)
        openai     — any OpenAI-compatible /chat/completions endpoint
    """
    if provider == "anthropic":
        return AnthropicLLM(model=model or DEFAULT_MODEL)
    if provider == "openai":
        if not model:
            raise ValueError("--llm-model is required for the openai provider")
        from .openai_compatible import OpenAICompatibleLLM

        return OpenAICompatibleLLM(
            model=model,
            base_url=base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
        )
    raise ValueError(f"Unknown LLM provider: {provider!r}")
