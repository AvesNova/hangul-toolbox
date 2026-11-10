"""Local TTS via Qwen3-TTS (install with the `qwen` extra)."""

from __future__ import annotations

from pathlib import Path

from .base import TTSError

DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"


class QwenLocalTTS:
    """Runs Qwen3-TTS on the local machine (GPU strongly recommended).

    The model is loaded lazily on the first synthesize() call so that
    pipeline runs with all audio already generated never touch torch.
    """

    file_ext = "wav"

    def __init__(self, model_id: str = DEFAULT_MODEL_ID, language: str = "Korean"):
        self._model_id = model_id
        self._language = language
        self._model = None
        self._soundfile = None

    def _load(self) -> None:
        try:
            import soundfile as sf
            import torch
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise TTSError(
                "Qwen TTS dependencies missing — install with: uv sync --extra qwen"
            ) from exc

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        try:
            import flash_attn  # noqa: F401

            attn = "flash_attention_2" if torch.cuda.is_available() else "eager"
        except ImportError:
            attn = "eager"

        self._model = Qwen3TTSModel.from_pretrained(
            self._model_id,
            device_map=device,
            dtype=dtype,
            attn_implementation=attn,
        )
        self._soundfile = sf

    def synthesize(self, text: str, voice: str, out_path: Path) -> None:
        if self._model is None:
            self._load()
        try:
            wavs, sample_rate = self._model.generate_custom_voice(
                text=text, language=self._language, speaker=voice
            )
            self._soundfile.write(out_path, wavs[0], sample_rate)
        except Exception as exc:
            raise TTSError(f"Qwen TTS failed for {text!r}: {exc}") from exc
