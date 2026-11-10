"""Anthropic (Claude) LLM backend."""

from __future__ import annotations

import anthropic

from .base import LLMError

DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicLLM:
    """Claude via the official Anthropic SDK.

    Reads credentials from the environment (ANTHROPIC_API_KEY or an
    `ant auth login` profile). The system prompt is cached with
    `cache_control` so repeated batches only pay for the varying word list.
    """

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 8000):
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def generate(self, system: str, user: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        if response.stop_reason == "refusal":
            raise LLMError("Anthropic request was refused by the model.")
        if response.stop_reason == "max_tokens":
            raise LLMError("Response hit max_tokens; reduce --batch-size or raise max_tokens.")

        text = "".join(b.text for b in response.content if b.type == "text")
        if not text:
            raise LLMError("Anthropic response contained no text.")
        return text
