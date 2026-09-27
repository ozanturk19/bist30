"""D-17 / A1 — pipeline/intraday.py: kapı, hesap, şema, atomik yazım, RSS (ağsız).

Yerelde (Python 3.9) ve VPS venv'de koşar; yfinance/feedparser çağrılmaz.
"""
import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from pipeline import compare_macro, intraday


def _utc(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


# TR = UTC+3. 28.09.2026 Pazartesi, 27.09 Pazar.
@pytest.mark.parametrize("now,expected", [
    (_utc(2026, 9, 28, 6, 55), True),    # Pzt 09:55 TR — seans penceresi başı, dakikalık
    (_utc(2026, 9, 28, 6, 56), True),    # 09:56
    (_utc(2026, 9, 28, 15, 15), True),   # 18:15 TR — pencere sonu
    (_utc(2026, 9, 28, 15, 16), False),  # 18:16 → 5 dk kuralı, 16 % 5 != 0
    (_utc(2026, 9, 28, 15, 20), True),   # 18:20 → 5 dk kuralı
    (_utc(2026, 9, 28, 6, 54), False),   # 09:54 → 5 dk kuralı
    (_utc(2026, 9, 27, 10, 3), False),   # Pazar 13:03 → dakika dakika DEĞİL
    (_utc(2026, 9, 27, 10, 5), True),    # Pazar 13:05
    (_utc(2026, 9, 28, 21, 0), True),    # gece 00:00 TR
])
def test_should_run_gate(now, expected):
    assert intraday.should_run(now) is expected


def test_force_ignores_gate():
    assert intraday.should_run(_utc(2026, 9, 27, 10, 3), force=True)


def test_news_due_top_of_hour_tr():
    assert intraday.news_due(_utc(2026, 9, 28, 7, 0))
    assert not intraday.news_due(_utc(2026, 9, 28, 7, 5))


def _frame(prices):
    """yf.download(group_by='ticker') benzeri: sütunlar (sembol, alan)."""
    cols, data = [], {}
    for sym, closes in prices.items():
        for field in ("Open", "Close"):
            cols.append((sym, field))
            data[(sym, field)] = closes
    df = pd.DataFrame(data)
    df.columns = pd.MultiIndex.from_tuples(cols)
    return df


def _all_prices():
    n = float("nan")
    return {
        "XU100.IS": [12000.0, 12100.0], "XU030.IS": [15900.0, 15946.95],
        "USDTRY=X": [48.8, 48.92], "EURTRY=X": [55.7, 55.74],
        "BTC-USD": [84000.0, 84454.7], "GC=F": [4300.0, 4321.2],
        "SI=F": [63.5, 64.25], "BZ=F": [106.6, 104.32],
        "^GSPC": [7700.0, 7743.41], "^IXIC": [n, 27068.72],  # NASDAQ tek geçerli bar → atlanır
    }


def test_build_items_price_change_and_delay():
    closes = intraday.fetch_closes(downloader=lambda syms: _frame(_all_prices()))
    items = {i["label"]: i for i in intraday.build_items(closes)}
    assert "NASDAQ" not in items                       # <2 bar → atlanır
    assert len(items) == 9
    assert items["XU030"]["price"] == 15946.95
    assert items["XU030"]["change"] == round((15946.95 - 15900.0) / 15900.0 * 100, 2)
    assert items["PETROL"]["change"] == round((104.32 - 106.6) / 106.6 * 100, 2)   # negatif
    assert items["XU030"]["source_delay_min"] == 15 and items["BTC"]["source_delay_min"] == 0
    assert set(items["USDTRY"]) == {"label", "price", "change", "source_delay_min"}


def test_prev_override_matches_fast_info_semantics():
    closes = intraday.fetch_closes(downloader=lambda syms: _frame(_all_prices()))
    items = {i["label"]: i for i in intraday.build_items(closes, prev_override={"BTC-USD": 84300.0})}
    assert items["BTC"]["change"] == round((84454.7 - 84300.0) / 84300.0 * 100, 2)   # override
    assert items["USDTRY"]["change"] == round((48.92 - 48.8) / 48.8 * 100, 2)         # bar tabanı


def test_load_prev_caches_one_hour(tmp_path):
    path = str(tmp_path / "prev.json")
    calls = []

    def fetcher(sym):
        calls.append(sym)
        return {"USDTRY=X": 48.8, "EURTRY=X": 55.7, "BTC-USD": 84300.0}[sym]

    p1 = intraday.load_prev(path, now=1000.0, fetcher=fetcher)
    assert p1 == {"USDTRY=X": 48.8, "EURTRY=X": 55.7, "BTC-USD": 84300.0} and len(calls) == 3
    intraday.load_prev(path, now=1000.0 + 3599, fetcher=fetcher)
    assert len(calls) == 3                                   # önbellekten
    calls.clear()

    def flaky(sym):
        if sym == "BTC-USD":
            raise RuntimeError("yahoo")
        return 1.5

    p2 = intraday.load_prev(path, now=1000.0 + 3601, fetcher=flaky)
    assert p2["BTC-USD"] == 84300.0 and p2["USDTRY=X"] == 1.5   # düşen sembol eski değerle kalır


def test_fetch_closes_empty_frame():
    assert intraday.fetch_closes(downloader=lambda s: pd.DataFrame()) == {}
    assert intraday.fetch_closes(downloader=lambda s: None) == {}


def test_run_macro_writes_schema_atomically(tmp_path):
    out = tmp_path / "last_macro.json"
    ok, msg = intraday.run_macro(str(out), downloader=lambda s: _frame(_all_prices()), now=1790477075.0,
                                 prev_path=str(tmp_path / "prev.json"), prev_fetcher=lambda s: None)
    assert ok, msg
    d = json.loads(out.read_text())
    assert set(d) == {"data", "ts"} and d["ts"] == 1790477075.0
    assert [i["label"] for i in d["data"]][:3] == ["XU100", "XU030", "USDTRY"]   # sıra = MACRO_TICKERS
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_run_macro_keeps_old_file_when_too_few_symbols(tmp_path):
    out = tmp_path / "last_macro.json"
    out.write_text('{"data": [], "ts": 1}')
    only_two = {k: v for k, v in _all_prices().items() if k in ("XU030.IS", "USDTRY=X")}
    ok, msg = intraday.run_macro(str(out), downloader=lambda s: _frame(only_two),
                                 prev_path=str(tmp_path / "prev.json"), prev_fetcher=lambda s: None)
    assert not ok and "yetersiz" in msg
    assert json.loads(out.read_text())["ts"] == 1


def test_run_macro_rejects_missing_xu030(tmp_path):
    out = tmp_path / "m.json"
    prices = {k: v for k, v in _all_prices().items() if k != "XU030.IS"}
    ok, msg = intraday.run_macro(str(out), downloader=lambda s: _frame(prices),
                                 prev_path=str(tmp_path / "prev.json"), prev_fetcher=lambda s: None)
    assert not ok and "geçersiz" in msg and not out.exists()


def test_single_source_of_symbols():
    """app.py aynı listeyi kullanır (kopya yok) — 10 sembol, etiket sırası sabit."""
    assert [l for l, _ in intraday.MACRO_TICKERS] == [
        "XU100", "XU030", "USDTRY", "EURTRY", "BTC", "ALTIN", "GUMUS", "PETROL", "SP500", "NASDAQ"]
    assert dict(intraday.MACRO_TICKERS)["PETROL"] == "BZ=F"      # D-49 Brent


class _Feed:
    def __init__(self, entries):
        self.entries = entries


def test_fetch_rss_filters_sorts_and_caps():
    now = datetime.now(timezone.utc)
    import time as _t

    def entry(title, hours_ago):
        ts = (now.timestamp() - hours_ago * 3600)
        return {"title": title, "link": "u/" + title, "published_parsed": _t.gmtime(ts)}

    feeds = {
        "a": _Feed([entry("yeni", 1), entry("eski", 30), entry("", 2)]),
        "b": _Feed([entry("ortada", 5)]),
    }

    def parse(url):
        if url == "bad":
            raise RuntimeError("ağ")
        return feeds[url]

    out = intraday.fetch_rss_once([("A", "a"), ("Bozuk", "bad"), ("B", "b")], parse=parse)
    assert [x["title"] for x in out] == ["yeni", "ortada"]     # 24 sa dışı ve başlıksız elendi, yeniden eskiye
    assert out[0]["source"] == "A" and out[0]["category"] == "makro"
    assert set(out[0]) == {"title", "url", "source", "published", "date_str", "pub_ts", "category"}


def test_compare_rows():
    old = {"data": [{"label": "X", "price": 100.0, "change": 1.0}, {"label": "Y", "price": 5.0, "change": 0.5}]}
    new = {"data": [{"label": "X", "price": 100.04, "change": 1.02}]}
    rows = {r[0]: r for r in compare_macro.diff_rows(old, new)}
    assert rows["X"][3] == 0.04 and rows["X"][4] == 0.02
    assert rows["Y"][2] is None and rows["Y"][3] is None       # yeni dosyada yok
