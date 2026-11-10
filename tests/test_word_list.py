from pathlib import Path

from hanbox.anki.word_list import load_word_list

SAMPLE = """\
Index|순위|단어|품사|풀이|등급
1|1|것01|의||A
2|2|하다01|동||A
3|5|되다01|동|어른이 ~|A
|6|skipped-no-index|명||B
4|7|사회07|명||B
"""


def _write(tmp_path: Path) -> Path:
    path = tmp_path / "words.csv"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_load_all(tmp_path):
    entries = load_word_list(_write(tmp_path))
    assert [e.word for e in entries] == ["것01", "하다01", "되다01", "사회07"]
    assert entries[2].hint == "어른이 ~"
    assert entries[3].level == "B"


def test_display_word_strips_homograph_suffix(tmp_path):
    entries = load_word_list(_write(tmp_path))
    assert entries[0].display_word == "것"
    assert entries[3].display_word == "사회"


def test_level_filter_and_limit(tmp_path):
    path = _write(tmp_path)
    assert [e.word for e in load_word_list(path, levels={"B"})] == ["사회07"]
    assert len(load_word_list(path, limit=2)) == 2
