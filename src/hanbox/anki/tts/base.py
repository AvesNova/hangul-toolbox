"""TTS backend interface."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TTSError(Exception):
    """Speech synthesis failed."""


class TTSEngine(Protocol):
    """Interface every TTS backend implements."""

    file_ext: str  # audio file extension without the dot, e.g. "wav"

    def synthesize(self, text: str, voice: str, out_path: Path) -> None:
        """Synthesize `text` with `voice` and write the audio to `out_path`."""
        ...
