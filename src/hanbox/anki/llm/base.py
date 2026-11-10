"""LLM backend interface."""

from __future__ import annotations

from typing import Protocol


class LLMError(Exception):
    """A request to the LLM backend failed or was refused."""


class LLMClient(Protocol):
    """Minimal text-in/text-out interface every LLM backend implements."""

    def generate(self, system: str, user: str) -> str:
        """Return the model's text response for a system + user prompt."""
        ...
