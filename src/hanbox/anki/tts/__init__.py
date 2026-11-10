"""TTS backend factory."""

from __future__ import annotations

import os

from .base import TTSEngine, TTSError

__all__ = ["TTSEngine", "TTSError", "create_tts", "DEFAULT_VOICES"]

# Default speaker rotation for Qwen3-TTS: sohee is the native Korean voice;
# aiden and vivian speak fluent Korean, giving each chunk a different speaker.
DEFAULT_VOICES = ["sohee", "aiden", "vivian"]


def create_tts(
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> TTSEngine:
    """Instantiate a TTS backend by provider name.

    Providers:
        qwen    — local Qwen3-TTS (install with the `qwen` extra)
        openai  — any OpenAI-compatible /audio/speech endpoint
    """
    if provider == "qwen":
        from .qwen_local import DEFAULT_MODEL_ID, QwenLocalTTS

        return QwenLocalTTS(model_id=model or DEFAULT_MODEL_ID)
    if provider == "openai":
        from .openai_compatible import OpenAICompatibleTTS

        return OpenAICompatibleTTS(
            model=model or "tts-1",
            base_url=base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
        )
    raise ValueError(f"Unknown TTS provider: {provider!r}")
