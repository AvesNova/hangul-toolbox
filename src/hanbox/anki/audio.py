"""Stage 2 — synthesize audio for every Korean chunk."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from .models import EnrichedWord
from .tts import TTSEngine, TTSError

logger = logging.getLogger(__name__)


def audio_filename(voice: str, text: str, ext: str) -> str:
    """Deterministic, collision-safe filename for a (voice, text) pair.

    Content-addressed so reruns and reordered word lists reuse existing files,
    and identical phrases are synthesized only once. The `topik_` prefix keeps
    the files identifiable inside Anki's flat media folder.
    """
    digest = hashlib.sha1(f"{voice}|{text}".encode()).hexdigest()[:16]
    return f"topik_{digest}.{ext}"


def clean_tts_text(korean_chunk: str) -> str:
    """Strip the emphasis asterisks before sending text to the TTS engine."""
    return korean_chunk.replace("*", "").strip()


def generate_audio(
    records: list[EnrichedWord],
    tts: TTSEngine,
    media_dir: Path,
    voices: list[str],
) -> int:
    """Fill in `chunk.audio_file` for every chunk, synthesizing missing files.

    Chunks rotate through `voices` so each example is heard from a different
    speaker. Returns the number of files newly synthesized; failures are
    logged and leave the chunk without audio rather than aborting the run.
    """
    media_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for record in records:
        for chunk_idx, chunk in enumerate(record.chunks):
            text = clean_tts_text(chunk.korean)
            if not text:
                chunk.audio_file = ""
                continue
            voice = voices[chunk_idx % len(voices)]
            filename = audio_filename(voice, text, tts.file_ext)
            path = media_dir / filename
            if not path.exists():
                logger.info("Synthesizing [%s] %s", voice, text)
                try:
                    tts.synthesize(text, voice, path)
                    generated += 1
                except TTSError as exc:
                    logger.error("%s", exc)
                    chunk.audio_file = ""
                    continue
            chunk.audio_file = filename
    logger.info("Audio complete: %d new files in %s.", generated, media_dir)
    return generated
