from hanbox.vocab import yonsei


def test_is_noise():
    for noise in ["", "  ", "12", "3과", "2항", "3<2>", "ㄱ", "색인 A", "대화"]:
        assert yonsei.is_noise(noise), noise
    for word in ["가게", "공원", "ㅋㅋ"]:
        assert not yonsei.is_noise(word), word


def test_is_suspicious():
    for bad in ["바람이", "전화를", "먹었어요", "먹는", "물", "ㅋㅋㅋ", "abc", "", "가게2"]:
        assert yonsei.is_suspicious(bad), bad
    for ok in ["가게", "공원", "자르다"]:
        assert not yonsei.is_suspicious(ok), ok


def test_book_order_sorts_numerically():
    from pathlib import Path

    names = ["2-1.csv", "1-2.csv", "10-1.csv", "notes.csv", "1-1.csv"]
    ordered = sorted((Path(n) for n in names), key=yonsei.book_order)
    assert [p.name for p in ordered] == ["1-1.csv", "1-2.csv", "2-1.csv", "10-1.csv", "notes.csv"]


def test_clean_combine_fix_pipeline(tmp_path):
    raw, clean = tmp_path / "raw", tmp_path / "clean"
    raw.mkdir()
    (raw / "1-1.csv").write_text("\n가게\n12\nㄱ\n바람이\n가게\n", encoding="utf-8")
    (raw / "1-2.csv").write_text("바람\n공원\n", encoding="utf-8")
    assert yonsei.clean_books(raw, clean) == 2
    rows = yonsei.combine_books(clean)
    assert rows == [
        ("가게", "1-1.csv"),
        ("바람이", "1-1.csv"),
        ("바람", "1-2.csv"),
        ("공원", "1-2.csv"),
    ]
    fixed = yonsei.apply_fixes(rows, {"바람이": "바람"})
    assert fixed == [("가게", "1-1.csv"), ("바람", "1-1.csv"), ("공원", "1-2.csv")]  # dup dropped
    assert yonsei.find_suspects(rows) == [("바람이", "1-1.csv")]


def test_shuffle_is_reproducible(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "1-1.csv").write_text(
        "\n".join(f"단어{c}" for c in "가나다라마바사") + "\n", encoding="utf-8"
    )
    yonsei.clean_books(raw, tmp_path / "a", shuffle_seed=1)
    yonsei.clean_books(raw, tmp_path / "b", shuffle_seed=1)
    assert (tmp_path / "a" / "1-1.csv").read_text() == (tmp_path / "b" / "1-1.csv").read_text()
