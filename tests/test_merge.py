from hanbox.vocab.merge import KimchiWord, TopikWord, YonseiWord, merge, write_master


def test_round_robin_order_and_dedup():
    kimchi = [KimchiWord("가", "1"), KimchiWord("나", "2"), KimchiWord("다", "3")]
    topik = [TopikWord("나", "명", "", "A"), TopikWord("라", "명", "", "B")]
    yonsei = [YonseiWord("가", "1-1.csv"), YonseiWord("마", "1-2.csv")]
    rows = merge(kimchi, topik, yonsei)
    # Kimchi 가, TOPIK 나, Yonsei (가 already seen) -> 마, then Kimchi 다, TOPIK 라
    assert [r["Word"] for r in rows] == ["가", "나", "마"]
    by = {r["Word"]: r for r in rows}
    assert by["가"]["Kimchi Rank"] == "1" and by["가"]["Yonsei Book"] == "1-1.csv"
    assert by["나"]["TOPIK Level"] == "A" and by["나"]["Kimchi Rank"] == "2"


def test_homographs_unify_across_lists():
    kimchi = [KimchiWord("하다", "1")]
    topik = [TopikWord("하다01", "동", "", "A")]
    yonsei = [YonseiWord("하다", "1-1.csv")]
    rows = merge(kimchi, topik, yonsei)
    assert len(rows) == 1
    assert rows[0]["Word"] == "하다1"
    assert rows[0]["TOPIK POS"] == "동" and rows[0]["Yonsei Book"] == "1-1.csv"


def test_write_master_uses_lf_and_header(tmp_path):
    out = tmp_path / "m.csv"
    write_master(merge([KimchiWord("가", "1")], [], [YonseiWord("가", "1-1.csv")]), out)
    text = out.read_bytes().decode()
    assert "\r" not in text
    assert (
        text.splitlines()[0]
        == "Word|Kimchi Rank|TOPIK POS|TOPIK Definition|TOPIK Level|Yonsei Book"
    )
