"""D-04: resmi kapanış — bülten ayrıştırma, kapılar, bar bindirme (saf modül; py3.9 uyumlu)."""
import io
import os
import sys
import zipfile
from datetime import date, datetime

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import official_close as oc  # noqa: E402

HDR = ("TARIH;ISLEM  KODU;PAZAR;YAPISAL BAZDA PIYASA ALT BOLUMU;ENSTRUMAN GRUBU;"
       "ONCEKI KAPANIS FIYATI;ACILIS FIYATI;EN DUSUK FIYAT;EN YUKSEK FIYAT;KAPANIS FIYATI;"
       "DEGISIM (%);TOPLAM ISLEM ADEDI")


def _zip(rows, date_s="2026-09-23", extra_header=True):
    lines = [HDR] + (["TRADE DATE;X;X;X;X;X;X;X;X;X;X;X"] if extra_header else [])
    for code, grp, sub, prev, o, lo, hi, cl, chg, vol in rows:
        lines.append(";".join([date_s, code, "Z", sub, grp, prev, o, lo, hi, cl, chg, vol]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("thb202609231.csv", "\n".join(lines))
    return buf.getvalue()


ROWS = [
    ("THYAO.E", "EQT", "MSPOT", "298", "298.75", "297.25", "302.25", "298.5", "0.168", "34210549"),
    ("SAHOL.E", "EQT", "MSPOT", "91.15", "91.2", "90.7", "92.15", "91.1", "-0.055", "29515463"),
    ("THYAO.C", "EQT", "MSPOT", "1", "1", "1", "1", "1", "0", "1"),       # .E değil
    ("XYZ.E", "DBT", "MSPOT", "1", "1", "1", "1", "1", "0", "1"),         # pay değil
    ("HALT.E", "EQT", "MSPOT", "5", "0", "0", "0", "0", "0", "0"),        # kapanış 0
]


def test_parse_picks_only_equities_and_reads_by_header_name():
    p = oc.parse_bulletin(_zip(ROWS))
    assert p["date"] == "2026-09-23"
    assert sorted(p["stocks"]) == ["SAHOL", "THYAO"]
    t = p["stocks"]["THYAO"]
    assert (t["close"], t["prev_close"], t["high"], t["low"], t["open"]) == (298.5, 298.0, 302.25, 297.25, 298.75)
    assert t["volume"] == 34210549.0 and t["change_pct"] == 0.168


def test_parse_rejects_missing_column_and_multi_date():
    bad = _zip(ROWS).replace(b"", b"")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.csv", "TARIH;ISLEM  KODU\n2026-09-23;X.E")
    with pytest.raises(ValueError):
        oc.parse_bulletin(buf.getvalue())
    two = _zip(ROWS[:1], "2026-09-22") + b""
    p1 = oc.parse_bulletin(two)
    assert p1["date"] == "2026-09-22"


def test_gates():
    p = oc.parse_bulletin(_zip(ROWS))
    ok, why = oc.check_gates(p, date(2026, 9, 23), ["THYAO", "SAHOL"])
    assert not ok and "pay satırı" in why           # 2 < 600
    big = {"date": "2026-09-23", "stocks": {"T%d" % i: {} for i in range(650)}}
    assert oc.check_gates(big, date(2026, 9, 23), ["T1", "T2"])[0]
    assert not oc.check_gates(big, date(2026, 9, 24), ["T1"])[0]              # tarih
    assert not oc.check_gates(big, date(2026, 9, 23), ["T1", "NOPE"])[0]      # kapsama %50


def _df(closes, start="2026-09-15"):
    idx = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame({"Open": closes, "High": [c + 1 for c in closes], "Low": [c - 1 for c in closes],
                         "Close": closes, "Volume": [1000.0] * len(closes)}, index=idx)


REC = {"date": "2026-09-23", "stocks": {"AAA": {"close": 100.0, "prev_close": 98.0, "open": 99.0,
                                                "high": 101.0, "low": 97.0, "volume": 555.0}}}


def test_overlay_replaces_same_day_bar_and_fixes_prev():
    df = _df([97.0, 98.5, 99.0])           # 15,16,17 Eylül… son gün ayarla
    df.index = pd.to_datetime(["2026-09-21", "2026-09-22", "2026-09-23"])
    out, ok = oc.overlay_official_bar(df, REC, "AAA")
    assert ok
    assert out["Close"].iloc[-1] == 100.0 and out["High"].iloc[-1] == 101.0 and out["Volume"].iloc[-1] == 555.0
    assert out["Close"].iloc[-2] == 98.0                      # önceki kapanış bültene eşitlendi
    assert df["Close"].iloc[-1] == 99.0                        # girdi df değişmedi


def test_overlay_appends_when_last_bar_older():
    df = _df([97.0, 98.5])
    df.index = pd.to_datetime(["2026-09-21", "2026-09-22"])
    out, ok = oc.overlay_official_bar(df, REC, "AAA")
    assert ok and len(out) == 3 and out.index[-1] == pd.Timestamp("2026-09-23")
    assert out["Close"].iloc[-1] == 100.0 and out["Close"].iloc[-2] == 98.0


def test_overlay_skips_split_like_break_newer_bar_and_unknown_ticker():
    df = _df([200.0, 200.0])
    df.index = pd.to_datetime(["2026-09-21", "2026-09-22"])
    assert oc.overlay_official_bar(df, REC, "AAA")[1] is False           # prev 98 vs 200: kırılma
    df2 = _df([97.0, 98.0])
    df2.index = pd.to_datetime(["2026-09-22", "2026-09-24"])
    assert oc.overlay_official_bar(df2, REC, "AAA")[1] is False          # resmi tarihten yeni bar var
    assert oc.overlay_official_bar(df2, REC, "ZZZ")[1] is False


def test_overlay_tz_aware_index():
    df = _df([97.0, 98.5])
    df.index = pd.to_datetime(["2026-09-21", "2026-09-22"]).tz_localize("Europe/Istanbul")
    out, ok = oc.overlay_official_bar(df, REC, "AAA")
    assert ok and out.index[-1].tzinfo is not None and out["Close"].iloc[-1] == 100.0


def test_archive_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "ARCHIVE_DIR", str(tmp_path))
    oc.reset_memory()
    assert oc.load_archive(date(2026, 9, 23)) is None
    oc.save_archive(oc.parse_bulletin(_zip(ROWS)), "Wed, 23 Sep 2026 15:27:00 GMT")
    rec = oc.load_archive(date(2026, 9, 23))
    assert rec["source"] == oc.SOURCE_LABEL and rec["stocks"]["SAHOL"]["close"] == 91.1
    oc.reset_memory()


@pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister — VPS venv'de çalıştır")
def test_official_pass_window():
    import app
    tr = app._TZ_TR
    assert not app._official_pass_window(datetime(2026, 9, 24, 18, 34, tzinfo=tr))
    assert app._official_pass_window(datetime(2026, 9, 24, 18, 35, tzinfo=tr))
    assert not app._official_pass_window(datetime(2026, 9, 24, 19, 30, tzinfo=tr))
    assert not app._official_pass_window(datetime(2026, 9, 26, 18, 40, tzinfo=tr))   # Cumartesi


# ── D-04b: endeks resmi kapanışı + grafik ucu ────────────────────────────────
IDX_CSV = ("1;XU100;BIST 100;BIST 100;TRY;23/09/2026;13251.85;13152.37;13152.37;13357.33\n"
           "7;XU030;BIST 30;BIST 30;TRY;23/09/2026;16370.07;16214.13;16214.13;16506.25\n"
           "9;XBANK;BIST BANKA;BIST BANKING;TRY;23/09/2026;1;1;1;1\n")


def _idx_zip(csv_text=IDX_CSV):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("FiyatEndeksleri_PriceIndices.csv", csv_text)
        zf.writestr("GetiriEndeksleri_ReturnIndices.csv", "x;y")
    return buf.getvalue()


def test_parse_indices_reads_xu100_xu030_only():
    p = oc.parse_indices(_idx_zip())
    assert p["date"] == "2026-09-23"
    assert sorted(p["indices"]) == ["XU030", "XU100"]
    assert p["indices"]["XU100"] == {"close": 13251.85, "open": 13152.37, "low": 13152.37, "high": 13357.33}


def test_parse_indices_rejects_missing_and_mixed_dates():
    with pytest.raises(ValueError):
        oc.parse_indices(_idx_zip("9;XBANK;A;B;TRY;23/09/2026;1;1;1;1\n"))
    with pytest.raises(ValueError):
        oc.parse_indices(_idx_zip(IDX_CSV.replace("23/09/2026;16370", "22/09/2026;16370")))


def test_index_prev_close_comes_from_previous_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "ARCHIVE_DIR", str(tmp_path))
    oc.reset_memory()
    day1 = {"date": "2026-09-23", "stocks": {}}
    oc.save_archive(day1, indices=oc.parse_indices(_idx_zip()))
    assert "prev_close" not in oc.load_archive(date(2026, 9, 23))["indices"]["XU100"]   # arşivin ilk günü
    csv2 = IDX_CSV.replace("23/09/2026", "24/09/2026").replace("13251.85", "13300.00")
    oc.save_archive({"date": "2026-09-24", "stocks": {}}, indices=oc.parse_indices(_idx_zip(csv2)))
    oc.reset_memory()
    r = oc.load_archive(date(2026, 9, 24))["indices"]
    assert r["XU100"]["close"] == 13300.0 and r["XU100"]["prev_close"] == 13251.85
    assert r["XU030"]["prev_close"] == 16370.07


def test_index_date_mismatch_is_not_archived(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "ARCHIVE_DIR", str(tmp_path))
    oc.save_archive({"date": "2026-09-24", "stocks": {}}, indices=oc.parse_indices(_idx_zip()))
    oc.reset_memory()
    assert "indices" not in oc.load_archive(date(2026, 9, 24))


def test_overlay_index_uses_series_prev_close_when_no_archive_prev():
    idx = pd.to_datetime(["2026-09-21", "2026-09-22", "2026-09-23"])
    df = pd.DataFrame({"Open": [16000.0, 16100.0, 16000.0], "High": [16100.0, 16200.0, 16100.0],
                       "Low": [15900.0, 16000.0, 15900.0], "Close": [16000.0, 16050.0, 16100.0]}, index=idx)
    rec = {"date": "2026-09-23", "stocks": {}, "indices": {"XU030": {"close": 16370.07, "open": 16214.13, "high": 16506.25, "low": 16214.13}}}
    out, ok = oc.overlay_official_bar(df, rec, "XU030")
    assert ok and out["Close"].iloc[-1] == 16370.07 and out["Close"].iloc[-2] == 16050.0


def test_patch_chart_last_bar_replaces_or_appends():
    rec = {"date": "2026-09-23", "stocks": {"THYAO": {"close": 298.5, "prev_close": 298.0, "open": 298.75,
                                                       "high": 302.25, "low": 297.25}}}
    d = {"ohlc": [{"time": "2026-09-22", "open": 300, "high": 301, "low": 297, "close": 298.0},
                  {"time": "2026-09-23", "open": 298, "high": 300, "low": 297, "close": 299.0}], "summary": {"price": 298.5}}
    assert oc.patch_chart_last_bar(d, rec, "THYAO")
    assert d["ohlc"][-1] == {"time": "2026-09-23", "open": 298.75, "high": 302.25, "low": 297.25, "close": 298.5}
    assert d["summary"]["close"] == 298.5 and d["summary"]["close_status"] == "resmi"
    d2 = {"ohlc": d["ohlc"][:1], "summary": {}}
    assert oc.patch_chart_last_bar(d2, rec, "THYAO") and len(d2["ohlc"]) == 2 and d2["ohlc"][-1]["close"] == 298.5
    d3 = {"ohlc": d["ohlc"] + [{"time": "2026-09-24", "open": 1, "high": 1, "low": 1, "close": 1}], "summary": {}}
    assert not oc.patch_chart_last_bar(d3, rec, "THYAO")          # resmi tarihten sonraki mum
    assert not oc.patch_chart_last_bar({"ohlc": d["ohlc"][:1], "summary": {}}, rec, "YOKTUR")


def _e(tk, old, new, ts="2026-09-24T18:11:00+03:00"):
    return {"ticker": tk, "old": old, "new": new, "stock": {}, "ts": ts}


def test_collapse_pending_round_trip_and_chain():
    buf = [_e("A", "BEKLE", "SAT"), _e("B", "AL", "BEKLE"), _e("A", "SAT", "BEKLE", "2026-09-24T18:36:00+03:00"),
           _e("C", "AL", "BEKLE"), _e("C", "BEKLE", "SAT", "2026-09-24T18:40:00+03:00"),
           _e("D", "AL", "SAT", "2026-09-23T18:11:00+03:00")]
    out, n = oc.collapse_pending(buf, "2026-09-24")
    assert n == 3
    assert [(x["ticker"], x["old"], x["new"]) for x in out] == [("B", "AL", "BEKLE"), ("C", "AL", "SAT"), ("D", "AL", "SAT")]
    out2, n2 = oc.collapse_pending(buf, "2026-09-24", tickers={"C"})
    assert n2 == 1 and len(out2) == 5
    assert oc.collapse_pending([], "2026-09-24") == ([], 0)
