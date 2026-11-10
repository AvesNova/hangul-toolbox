"""Generic OpenAI-compatible speech backend.

Works with any server exposing POST {base_url}/audio/speech — OpenAI TTS,
Kokoro-FastAPI, openedai-speech, etc.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from .base import TTSError


class OpenAICompatibleTTS:
    file_ext = "mp3"

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "",
        timeout: float = 120.0,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(headers=headers, timeout=timeout)

    def synthesize(self, text: str, voice: str, out_path: Path) -> None:
        payload = {
            "model": self._model,
            "voice": voice,
            "input": text,
            "response_format": "mp3",
        }
        try:
            response = self._http.post(f"{self._base_url}/audio/speech", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TTSError(f"TTS request failed for {text!r}: {exc}") from exc
        out_path.write_bytes(response.content)
