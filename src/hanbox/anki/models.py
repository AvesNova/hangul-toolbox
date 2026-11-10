"""Core data types shared across pipeline stages."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

_TRAILING_DIGITS = re.compile(r"\d+$")


@dataclass(frozen=True)
class WordEntry:
    """One row of the TOPIK vocabulary list."""

    index: int
    rank: int
    word: str  # raw form, may carry a homograph suffix, e.g. "맞다01"
    pos: str  # part of speech (명, 동, 형, ...)
    hint: str  # disambiguation hint from the list, e.g. "답이 ~"
    level: str  # TOPIK level: A, B or C

    @property
    def display_word(self) -> str:
        """The word without the trailing homograph number (것01 -> 것)."""
        return _TRAILING_DIGITS.sub("", self.word.strip())


@dataclass
class Chunk:
    """A short example phrase for a word, with translation and audio."""

    korean: str
    english: str
    audio_file: str = ""  # basename of the generated audio file, "" if missing


@dataclass
class EnrichedWord:
    """A word entry after LLM enrichment (and optionally audio generation)."""

    entry: WordEntry
    english: str
    chunks: list[Chunk] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnrichedWord:
        return cls(
            entry=WordEntry(**data["entry"]),
            english=data["english"],
            chunks=[Chunk(**c) for c in data["chunks"]],
        )
