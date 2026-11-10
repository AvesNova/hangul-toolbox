from itertools import combinations

from hanbox.similar import pairs
from hanbox.similar.pairs import Word


def test_decompose_and_distance():
    assert pairs.decompose("가") == (0, 0, 0)
    assert pairs.jamo_distance("년", "녀") == 1  # final consonant only
    assert pairs.jamo_distance("자", "바") == 1  # initial only
    assert pairs.jamo_distance("가", "나") == 1
    assert pairs.jamo_distance("가", "뉴") == 2


def test_is_minimal_pair():
    assert pairs.is_minimal_pair("소년", "소녀")
    assert pairs.is_minimal_pair("자라다", "바라다")
    assert not pairs.is_minimal_pair("소년", "소년")  # identical
    assert not pairs.is_minimal_pair("소년", "소녀들")  # different length
    assert not pairs.is_minimal_pair("가나", "다라")  # two positions
    assert not pairs.is_minimal_pair("가", "뉴")  # two jamo apart
    assert not pairs.is_minimal_pair("가a", "나a")  # non-Hangul


def test_find_pairs_matches_brute_force():
    texts = [
        "소년",
        "소녀",
        "자라다",
        "바라다",
        "가다",
        "나다",
        "마다",
        "사다",
        "가나",
        "소리",
        "수리",
    ]
    words = [Word(t, i + 1) for i, t in enumerate(texts)]
    expected = {
        frozenset((a.text, b.text))
        for a, b in combinations(words, 2)
        if pairs.is_minimal_pair(a.text, b.text)
    }
    found = {frozenset((a.text, b.text)) for a, b in pairs.find_pairs(words)}
    assert found == expected and expected


def test_pairs_sorted_most_common_first_and_deduped():
    words = [
        Word("가다", 1),
        Word("나다", 2),
        Word("소년", 100),
        Word("소녀", 200),
        Word("가다", 50),
    ]
    result = pairs.find_pairs(words)
    assert [(a.text, b.text) for a, b in result] == [("가다", "나다"), ("소년", "소녀")]
    assert result[0][0].rank == 1  # duplicate kept its best rank


def test_load_known_formats(tmp_path):
    new = tmp_path / "new.tsv"
    new.write_text("그러나\tbut\tx\n이런\tthis kind of\ty\n", encoding="utf-8")
    legacy = tmp_path / "old.tsv"
    legacy.write_text("5\t그러나\tbut\n7\t이런\tthis kind of\n", encoding="utf-8")
    assert pairs.load_known(new)["이런"] == Word("이런", 2, "this kind of")
    assert pairs.load_known(legacy)["이런"] == Word("이런", 7, "this kind of")
