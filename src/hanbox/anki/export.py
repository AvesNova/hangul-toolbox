"""Stage 3 — export to an Anki-importable TSV and a ready-made .apkg deck.

TSV columns (tab-separated, pipe-separated lists inside the chunk columns):
    Word_Korean | Word_English | Chunks_Korean | Chunks_English | Chunks_Audio
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import genanki

from .models import EnrichedWord

logger = logging.getLogger(__name__)

# Fixed IDs so re-importing an updated .apkg updates notes instead of
# duplicating them. Never change these once a deck is in circulation.
ANKI_MODEL_ID = 1_708_395_142
ANKI_DECK_ID = 1_842_016_573

_CARD_CSS = """\
.card {
  font-family: "Noto Sans KR", "Malgun Gothic", sans-serif;
  font-size: 22px;
  text-align: center;
  color: #222;
  background-color: #fdfdfd;
}
.word { font-size: 42px; font-weight: 700; margin: 20px 0; }
.chunk { font-size: 26px; margin: 14px 0; }
.chunk b { color: #c0392b; }
.translation { font-size: 26px; color: #2c3e50; margin: 12px 0; }
.chunk-en { font-size: 20px; color: #555; margin: 8px 0; }
.audio { margin-top: 16px; }
"""

# The front picks one chunk at random and stores the choice so the back can
# show the matching translation. Field data is read from hidden divs rather
# than interpolated into JS literals, so quotes in content can't break the
# script. All audio stays on the back, where Anki renders the [sound:...]
# tags as play buttons.
_FRONT_TEMPLATE = """\
<div class="word">{{Word_Korean}}</div>
<div class="chunk" id="chunk-ko"></div>
<div id="data-ko" style="display:none">{{Chunks_Korean}}</div>
<script>
  var chunks = document.getElementById("data-ko").textContent.split("|");
  var idx = Math.floor(Math.random() * chunks.length);
  sessionStorage.setItem("topikChunkIdx", idx);
  document.getElementById("chunk-ko").innerHTML =
    chunks[idx].replace(/\\*(.+?)\\*/g, "<b>$1</b>");
</script>
"""

_BACK_TEMPLATE = """\
{{FrontSide}}
<hr id="answer">
<div class="translation">{{Word_English}}</div>
<div class="chunk-en" id="chunk-en"></div>
<div class="audio">{{Chunks_Audio}}</div>
<div id="data-en" style="display:none">{{Chunks_English}}</div>
<script>
  var ens = document.getElementById("data-en").textContent.split("|");
  var idx = parseInt(sessionStorage.getItem("topikChunkIdx") || "0", 10);
  document.getElementById("chunk-en").textContent = ens[idx] || ens[0] || "";
</script>
"""


def build_row(record: EnrichedWord) -> list[str]:
    """One TSV/note row. The three chunk columns always have equal pipe counts."""
    return [
        record.entry.display_word,
        record.english,
        "|".join(c.korean for c in record.chunks),
        "|".join(c.english for c in record.chunks),
        "|".join(f"[sound:{c.audio_file}]" if c.audio_file else "" for c in record.chunks),
    ]


def write_tsv(records: list[EnrichedWord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for record in records:
            writer.writerow(build_row(record))
    logger.info("Wrote %d rows to %s.", len(records), path)


def write_apkg(
    records: list[EnrichedWord],
    media_dir: Path,
    path: Path,
    deck_name: str = "TOPIK Vocabulary",
) -> None:
    model = genanki.Model(
        ANKI_MODEL_ID,
        "Korean Chunk Randomizer",
        fields=[
            {"name": "Word_Korean"},
            {"name": "Word_English"},
            {"name": "Chunks_Korean"},
            {"name": "Chunks_English"},
            {"name": "Chunks_Audio"},
        ],
        templates=[
            {
                "name": "Recognition",
                "qfmt": _FRONT_TEMPLATE,
                "afmt": _BACK_TEMPLATE,
            }
        ],
        css=_CARD_CSS,
    )

    deck = genanki.Deck(ANKI_DECK_ID, deck_name)
    media_files: set[str] = set()
    for record in records:
        deck.add_note(
            genanki.Note(
                model=model,
                fields=build_row(record),
                # Stable per word+POS so re-imports update instead of duplicate.
                guid=genanki.guid_for(record.entry.word, record.entry.pos),
            )
        )
        for chunk in record.chunks:
            if chunk.audio_file and (media_dir / chunk.audio_file).exists():
                media_files.add(str(media_dir / chunk.audio_file))

    path.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(deck, media_files=sorted(media_files)).write_to_file(str(path))
    logger.info(
        "Wrote deck %r (%d notes, %d media files) to %s.",
        deck_name,
        len(records),
        len(media_files),
        path,
    )
