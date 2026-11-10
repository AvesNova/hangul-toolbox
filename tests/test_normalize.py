from hanbox.vocab.normalize import build_normalization_map, parse_word_number


def test_parse_word_number():
    assert parse_word_number("하다") == ("하다", None)
    assert parse_word_number("하다01") == ("하다", 1)
    assert parse_word_number("수2") == ("수", 2)
    assert parse_word_number("하다00") == ("하다00", None)


def test_unnumbered_words_take_lowest_topik_number():
    topik = ["하다01", "수2", "수3", "사람"]
    mapping = build_normalization_map(topik, ["하다", "수", "수3", "책"])
    assert mapping["하다"] == "하다1"  # TOPIK's 01 normalises to 1
    assert mapping["수"] == "수2"  # lowest number TOPIK uses
    assert mapping["수3"] == "수3"
    assert mapping["책"] == "책"  # unknown to TOPIK: unchanged
    assert mapping["사람"] == "사람"


def test_topik_words_win_over_other_lists():
    mapping = build_normalization_map(["수2"], ["수2"])
    assert mapping["수2"] == "수2"
