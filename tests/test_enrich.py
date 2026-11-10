import json

from hanbox.anki.enrich import parse_response
from hanbox.anki.models import WordEntry


def entry(index: int, word: str, pos: str = "명") -> WordEntry:
    return WordEntry(index=index, rank=index, word=word, pos=pos, hint="", level="A")


def item(word: str, english: str = "meaning", n_chunks: int = 2) -> dict:
    return {
        "word": word,
        "english": english,
        "chunks": [{"ko": f"*{word}* {i}", "en": f"chunk {i}"} for i in range(n_chunks)],
    }


def test_parse_valid_response():
    batch = [entry(1, "학교"), entry(2, "친구")]
    text = json.dumps([item("학교"), item("친구")], ensure_ascii=False)
    successes, failed = parse_response(text, batch, chunk_count=2)
    assert [s.entry.word for s in successes] == ["학교", "친구"]
    assert not failed
    assert len(successes[0].chunks) == 2


def test_parse_strips_markdown_fences():
    batch = [entry(1, "학교")]
    text = "```json\n" + json.dumps([item("학교")]) + "\n```"
    successes, failed = parse_response(text, batch, chunk_count=2)
    assert len(successes) == 1 and not failed


def test_duplicate_words_assigned_in_order():
    batch = [entry(1, "맞다01", "동"), entry(2, "맞다01", "동")]
    text = json.dumps([item("맞다01", "to be correct"), item("맞다01", "to greet")])
    successes, failed = parse_response(text, batch, chunk_count=2)
    assert not failed
    assert {s.entry.index for s in successes} == {1, 2}
    assert successes[0].english == "to be correct"


def test_missing_and_malformed_entries_marked_failed():
    batch = [entry(1, "학교"), entry(2, "친구"), entry(3, "나라")]
    text = json.dumps(
        [
            item("학교"),
            {"word": "친구", "english": "", "chunks": []},  # incomplete
            # 나라 missing entirely
        ]
    )
    successes, failed = parse_response(text, batch, chunk_count=2)
    assert [s.entry.word for s in successes] == ["학교"]
    assert {e.word for e in failed} == {"친구", "나라"}


def test_garbage_response_fails_whole_batch():
    batch = [entry(1, "학교")]
    successes, failed = parse_response("Sorry, I can't do that.", batch, chunk_count=2)
    assert not successes
    assert failed == batch


def test_chunks_truncated_to_chunk_count():
    batch = [entry(1, "학교")]
    text = json.dumps([item("학교", n_chunks=5)])
    successes, _ = parse_response(text, batch, chunk_count=3)
    assert len(successes[0].chunks) == 3
