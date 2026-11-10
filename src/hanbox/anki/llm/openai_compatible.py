"""Generic OpenAI-compatible chat-completions backend.

Works with any server exposing POST {base_url}/chat/completions — OpenAI,
OpenRouter, Groq, Ollama, LM Studio, vLLM, etc.
"""

from __future__ import annotations

import httpx

from .base import LLMError


class OpenAICompatibleLLM:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "",
        max_tokens: int = 8000,
        timeout: float = 300.0,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(headers=headers, timeout=timeout)

    def generate(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = self._http.post(f"{self._base_url}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape: {data!r:.500}") from exc
        if not content:
            raise LLMError("LLM response contained no text.")
        return content
