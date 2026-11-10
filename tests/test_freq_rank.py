from hanbox.freq import rank


def test_load_ranks_both_formats(tmp_path):
    plain = tmp_path / "plain.csv"
    plain.write_text("있다\n하다\n것\n", encoding="utf-8")
    table = tmp_path / "table.csv"
    table.write_text("Rank|Word\n1|있다\n2.1|것\n2.2|것\n", encoding="utf-8")
    assert rank.load_ranks(plain) == {"있다": 0, "하다": 1, "것": 2}
    assert rank.load_ranks(table) == {"있다": 1, "것": 2}


def test_add_rank_column(tmp_path):
    vocab = tmp_path / "v.csv"
    vocab.write_text("Index|Korean|English\n1|하다01|to do\n2|희귀어|rare\n", encoding="utf-8")
    out = tmp_path / "out.csv"
    written, missing = rank.add_rank_column(vocab, out, {"하다": 3}, word_column="Korean")
    assert (written, missing) == (2, 1)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Index|Korean|English|Frequency"
    assert lines[1].endswith("|3") and lines[2].endswith(f"|{rank.DEFAULT_RANK}")


def test_missing_column_raises(tmp_path):
    import pytest

    vocab = tmp_path / "v.csv"
    vocab.write_text("a|b\n1|2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        rank.add_rank_column(vocab, tmp_path / "o.csv", {}, word_column="Korean")
