from pathlib import Path

from hanbox.anki.audio import audio_filename, clean_tts_text
from hanbox.anki.export import build_row, write_apkg, write_tsv
from hanbox.anki.models import Chunk, EnrichedWord, WordEntry


def record() -> EnrichedWord:
    return EnrichedWord(
        entry=WordEntry(index=1, rank=1, word="것01", pos="의", hint="", level="A"),
        english="thing",
        chunks=[
            Chunk(korean="좋은 *것*", english="good thing", audio_file="topik_ab.wav"),
            Chunk(korean="먹을 *것*", english="something to eat", audio_file=""),
        ],
    )


def test_build_row_matches_spec():
    row = build_row(record())
    assert row[0] == "것"  # homograph suffix stripped
    assert row[1] == "thing"
    assert row[2] == "좋은 *것*|먹을 *것*"
    assert row[3] == "good thing|something to eat"
    # missing audio still keeps pipe counts aligned across chunk columns
    assert row[4] == "[sound:topik_ab.wav]|"


def test_write_tsv(tmp_path: Path):
    out = tmp_path / "deck.tsv"
    write_tsv([record()], out)
    line = out.read_text(encoding="utf-8").rstrip("\n")
    assert line.count("\t") == 4


def test_write_apkg(tmp_path: Path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "topik_ab.wav").write_bytes(b"RIFF")
    out = tmp_path / "deck.apkg"
    write_apkg([record()], media_dir, out, deck_name="Test Deck")
    assert out.exists() and out.stat().st_size > 0


def test_audio_filename_is_deterministic_and_voice_scoped():
    a = audio_filename("sohee", "좋은 것", "wav")
    assert a == audio_filename("sohee", "좋은 것", "wav")
    assert a != audio_filename("aiden", "좋은 것", "wav")
    assert a.startswith("topik_") and a.endswith(".wav")


def test_clean_tts_text():
    assert clean_tts_text("좋은 *것* ") == "좋은 것"
