"""D-42 — BIST100 ısı haritası: treemap geometrisi, PD sanity bandı, dönem getirileri,
tavan/taban + bayat bayrakları, donmuş görüntü, sözleşme şeması ve boyut.

Fikstür (tests/fixtures/heatmap_20260923.json): 01.10 listesi + 23.09 resmi kapanış +
VPS temel önbellek + canlı /api/data (24.09 salt-okur GET'lerle bir kez üretildi).
"""
import gzip
import json
import os
import sys
from datetime import date, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import heatmap as hm  # noqa: E402

FX = json.load(open(os.path.join(ROOT, "tests", "fixtures", "heatmap_20260923.json"), encoding="utf-8"))
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
EPS = 2e-3   # çıktı 3 haneye yuvarlı


def _snap(**over):
    rows = {t: dict(r, bar_date=FX["asof"]) for t, r in FX["rows"].items()}
    kw = dict(asof_iso=FX["asof"], members=FX["members"], official=FX["official"], rows=rows,
              fund=FX["fund"], scores=FX["bp"], sectors=FX["sectors"], names=FX["names"],
              xu100_series=FX["xu100"], updated_at="2026-09-23T18:40:12+03:00")
    kw.update(over)
    return hm.build(**kw)


# ── geometri ──────────────────────────────────────────────────────────────────
def _inside(a, b):
    return (a["x"] >= b["x"] - EPS and a["y"] >= b["y"] - EPS and
            a["x"] + a["w"] <= b["x"] + b["w"] + EPS and a["y"] + a["h"] <= b["y"] + b["h"] + EPS)


def _overlap(a, b):
    ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return ox > EPS and oy > EPS


def test_layout_properties_on_real_100():
    snap = _snap()
    groups, tiles = hm.layout(snap["rows"])
    assert len(tiles) == 100 and len({t["t"] for t in tiles}) == 100
    box = {"x": 0, "y": 0, "w": 100, "h": 100}
    gi = {g["g"]: g for g in groups}
    for g in groups:
        assert _inside(g, box), g
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            assert not _overlap(a, b), (a, b)
    for t in tiles:
        assert _inside(t, gi[t["g"]]), t
    for i, a in enumerate(tiles):
        for b in tiles[i + 1:]:
            assert not _overlap(a, b), (a["t"], b["t"])
    # alan ∝ PD (%1): yüzde kutuda alan payı = w*h/10000
    mc = {r["t"]: r["mcap"] for r in snap["rows"]}
    total = sum(mc.values())
    for t in tiles:
        share = t["w"] * t["h"] / 1e4
        assert abs(share / (mc[t["t"]] / total) - 1) < 0.01, t["t"]
    assert abs(sum(g["w"] * g["h"] for g in groups) / 1e4 - 1) < 1e-3   # kutu tam dolu
    # sıra: gruplar toplam PD'ye, grup içi kutular PD'ye göre azalan
    gsum = [sum(mc[t["t"]] for t in tiles if t["g"] == g["g"]) for g in groups]
    assert gsum == sorted(gsum, reverse=True)
    for g in groups:
        seq = [mc[t["t"]] for t in tiles if t["g"] == g["g"]]
        assert seq == sorted(seq, reverse=True)
    assert groups[0]["g"] in ("Bankacılık", "Holding ve Yatırım")


def test_squarify_simple_and_empty():
    rects = hm.squarify([6, 6, 4, 3, 2, 2, 1], 0, 0, 6, 4)
    assert abs(sum(w * h for _, _, w, h in rects) - 24) < 1e-9
    assert [round(w * h, 9) for _, _, w, h in rects] == [6, 6, 4, 3, 2, 2, 1]
    assert hm.layout([]) == ([], [])


# ── PD sanity bandı ──────────────────────────────────────────────────────────
def test_mcap_sanity_band():
    assert hm.mcap_tl(10.0, 100.0, 1100.0) == (1000.0, None)            # oran 1,10 bant içi
    m, why = hm.mcap_tl(10.0, 100.0, 1460.0)                              # KRDMD benzeri 1,46×
    assert m == 1000.0 and why == "PD sanity 1.46 -> adet*fiyat"
    assert hm.mcap_tl(10.0, 100.0, 700.0)[1] == "PD sanity 0.70 -> adet*fiyat"
    assert hm.mcap_tl(10.0, None, 900.0) == (900.0, "pay adedi yok -> PD")
    assert hm.mcap_tl(10.0, None, None) == (None, "PD yok")
    assert hm.reported_mcap({"market_cap": {"value": 5e9, "currency": "TRY"}}) == 5e9
    assert hm.reported_mcap({"market_cap": {"value": 5e9, "currency": "USD"}}) is None
    snap = _snap()
    assert any(n.startswith("KRDMD: PD sanity") for n in snap["notes"])
    krdmd = next(r for r in snap["rows"] if r["t"] == "KRDMD")
    f = FX["fund"]["KRDMD"]
    assert abs(krdmd["mcap"] - FX["official"]["stocks"]["KRDMD"]["close"] * f["shares"] / 1e9) < 0.01


# ── dönem getirileri ─────────────────────────────────────────────────────────
def _daily(start, end, f):
    d, out = start, []
    while d <= end:
        if d.weekday() < 5:
            out.append((d.isoformat(), f(d)))
        d += timedelta(days=1)
    return out


def test_period_returns_reference_dates_and_gaps():
    s = _daily(date(2025, 9, 1), date(2026, 9, 23), lambda d: 100.0 + (d - date(2025, 9, 1)).days)
    r = hm.period_returns(s)
    last = s[-1][1]
    assert r["w1"] == round((last / (last - 7) - 1) * 100, 2)            # 16.09 kapanışı
    ref_m1 = [c for t, c in s if t <= "2026-08-23"][-1]                   # 23.08 Pazar → 21.08
    assert r["m1"] == round((last / ref_m1 - 1) * 100, 2)
    assert r["ytd"] == round((last / [c for t, c in s if t <= "2025-12-31"][-1] - 1) * 100, 2)
    assert r["y1"] == round((last / [c for t, c in s if t <= "2025-09-23"][-1] - 1) * 100, 2)
    short = [p for p in s if p[0] >= "2026-06-01"]                         # 1 yıllık seri yok
    assert hm.period_returns(short)["y1"] is None and hm.period_returns(short)["ytd"] is None
    gap = [p for p in s if not ("2026-08-01" <= p[0] <= "2026-09-18")]    # önbellek boşluğu
    rg = hm.period_returns(gap)
    assert rg["w1"] is None and rg["m1"] is None and rg["ytd"] is not None
    assert hm.period_returns([]) == dict.fromkeys(hm.PERIODS)
    assert hm._minus_months(date(2024, 2, 29), 12) == date(2023, 2, 28)
    assert hm._minus_months(date(2026, 3, 31), 1) == date(2026, 2, 28)


def test_xu100_official_close_and_series_returns():
    snap = _snap()
    x = snap["xu100"]
    assert x["close"] == 13251.85
    assert x["ch"]["d1"] == round((13251.85 / 13220.49 - 1) * 100, 2)   # önceki bar = 22.09 resmi
    assert all(x["ch"][k] is not None for k in hm.PERIODS)
    assert hm.patch_series([("2026-09-22", 1.0), ("2026-09-24", 9.0)], "2026-09-23", 2.0) == \
        [("2026-09-22", 1.0), ("2026-09-23", 2.0)]


# ── tavan/taban ve bayat ─────────────────────────────────────────────────────
@pytest.mark.parametrize("prev,close,want", [
    # 23.09 resmi bülten örnekleri
    (51.75, 56.9, "tavan"), (2.31, 2.54, "tavan"), (5155.0, 5670.0, "tavan"), (457.75, 503.5, "tavan"),
    (4.85, 4.37, "taban"), (2.08, 1.88, "taban"), (1.25, 1.13, "taban"), (2945.0, 2652.5, "taban"),
    (2660.0, 2394.0, "taban"), (1608.0, 1448.0, "taban"), (374.75, 337.5, "taban"),
    (11.70, 10.57, None),   # BIOEN −%9,66: limit 10,53 idi, limitte DEĞİL
    (7.57, 6.90, None), (17.86, 19.49, None), (34.92, 31.72, None), (100.0, 100.0, None),
])
def test_limit_flag_uses_price_ticks(prev, close, want):
    assert hm.limit_flag(close, prev) == want


def test_stale_flags_and_counts():
    rows = {t: dict(r, bar_date=FX["asof"]) for t, r in FX["rows"].items()}
    rows["THYAO"]["bar_date"] = "2026-09-22"                     # son bar ≠ son EOD günü
    off = json.loads(json.dumps(FX["official"]))
    off["stocks"]["ASELS"]["prev_close"] = off["stocks"]["ASELS"]["close"] / 1.2   # |d1| > %10,5
    del off["stocks"]["AKBNK"]                                    # bültende yok
    snap = _snap(rows=rows, official=off)
    r = {x["t"]: x for x in snap["rows"]}
    assert r["THYAO"]["stale"] and r["ASELS"]["stale"] and r["AKBNK"]["stale"]
    assert r["AKBNK"]["ch"]["d1"] is None and r["AKBNK"]["lim"] is None
    assert not r["GARAN"]["stale"]
    c = snap["counts"]
    assert c["up"] + c["down"] + c["flat"] == sum(1 for x in snap["rows"] if x["ch"]["d1"] is not None)


def test_stale_accepts_d06_bar_date_format():
    """D-54 bulgusu: analyze() `bar_date` GG.AA.YYYY yayınlıyor (D-06); ISO ile kıyas 25.09'da
    100/100 satırı bayat yaptı. Canlı biçimle bayat yalnız gerçekten eski bar."""
    rows = {t: dict(r, bar_date="23.09.2026") for t, r in FX["rows"].items()}
    rows["THYAO"]["bar_date"] = "22.09.2026"
    rows["GARAN"]["bar_date"] = None
    base = {x["t"] for x in _snap()["rows"] if x["stale"]}          # ISO bar_date ile (başka nedenler)
    assert "THYAO" not in base and "GARAN" not in base and len(base) < 20
    r = {x["t"]: x for x in _snap(rows=rows)["rows"]}
    assert {t for t, x in r.items() if x["stale"]} == base | {"THYAO", "GARAN"}
    assert hm.iso_day("23.09.2026") == hm.iso_day("2026-09-23") == "2026-09-23"
    assert hm.iso_day("2026-09-23T18:00:00") == "2026-09-23" and hm.iso_day("23/09/2026") is None


# ── sözleşme şeması + boyut ──────────────────────────────────────────────────
def test_payload_schema_and_size():
    snap = _snap()
    assert list(snap) == ["asof", "asof_label", "universe", "n", "counts", "xu100", "rows", "notes",
                          "updated_at", "frozen"]
    assert snap["asof"] == "2026-09-23" and snap["asof_label"] == "23 Eylül"
    assert snap["universe"] == "BIST100" and snap["n"] == 100 and snap["frozen"] is True
    assert set(snap["counts"]) == {"up", "down", "flat"}
    assert set(snap["xu100"]) == {"close", "ch"} and set(snap["xu100"]["ch"]) == {"d1", "w1", "m1", "ytd", "y1"}
    for r in snap["rows"]:
        assert list(r) == ["t", "n", "g", "sub", "mcap", "p", "ch", "bp", "tr", "days", "lim", "stale"]
        assert list(r["ch"]) == ["d1", "w1", "m1", "ytd", "y1"]
        assert isinstance(r["mcap"], float) and r["mcap"] > 0
        assert r["tr"] in ("guclu", "yatay", "bozuk", None) and r["lim"] in ("tavan", "taban", None)
        assert r["days"] is None or isinstance(r["days"], int)
        assert r["bp"] is None or 0 <= r["bp"] <= 100
        assert r["g"] and r["n"]
    aefes = next(r for r in snap["rows"] if r["t"] == "AEFES")
    # D-23: grup = sitenin sektör taksonomisi (sector_taxonomy), /hisse etiketiyle aynı ad
    assert aefes["g"] == "Gıda ve İçecek" and aefes["sub"] == "Gıda, İçecek ve Tütün"
    assert next(r for r in snap["rows"] if r["t"] == "GARAN")["g"] == "Bankacılık"
    assert sum(1 for r in snap["rows"] if r["g"] == hm.OTHER) <= 3
    assert hm.quality(snap) == (True, "ok")
    raw = json.dumps(snap).encode()                     # app.safe_json ile aynı (ensure_ascii)
    assert len(gzip.compress(raw, 9)) <= 25 * 1024      # brotli ≤ gzip → ≤25 KB br
    try:
        import brotli
        assert len(brotli.compress(raw)) <= 25 * 1024
    except ImportError:
        pass
    text = json.dumps(snap, ensure_ascii=False)
    for bad in ("bugün", "dün", "Ücretsiz", "TP1", "hedef"):
        assert bad not in text


def test_quality_gate_blocks_thin_snapshot():
    fund = {t: {} for t in FX["members"]}
    ok, why = hm.quality(_snap(fund=fund))
    assert not ok and "PD ve d1" in why


# ── donmuş görüntü ───────────────────────────────────────────────────────────
def test_frozen_snapshot_is_not_recomputed(tmp_path):
    d = str(tmp_path / "heatmap")
    snap = _snap()
    p = hm.save_frozen(snap, d)
    assert p and p.endswith("2026-09-23.json")
    # ertesi gün aynı asof ile yeniden hesap (ör. Yahoo seriyi kaydırdı) diske YAZILMAZ
    later = _snap(updated_at="2026-09-24T12:40:00+03:00")
    later["rows"][0]["p"] = 1.0
    assert hm.save_frozen(later, d) is None
    on_disk = json.load(open(p, encoding="utf-8"))
    assert on_disk["updated_at"] == "2026-09-23T18:40:12+03:00" and on_disk == json.loads(json.dumps(snap))
    assert not [n for n in os.listdir(d) if n.endswith(".tmp")]
    nxt = dict(snap, asof="2026-09-24", asof_label="24 Eylül")
    assert hm.save_frozen(nxt, d).endswith("2026-09-24.json")
    assert hm.latest_path(d).endswith("2026-09-24.json")
    assert hm.latest_path(str(tmp_path / "yok")) is None


def test_frozen_snapshot_has_no_nan_or_numpy(tmp_path):
    class _NpInt:            # numpy skaleri benzeri (item())
        def item(self):
            return 7
    snap = _snap()
    snap["rows"][0]["p"] = float("nan")
    snap["rows"][1]["mcap"] = float("inf")
    snap["rows"][2]["days"] = _NpInt()
    p = hm.save_frozen(snap, str(tmp_path / "hm"))
    raw = open(p, encoding="utf-8").read()
    assert "NaN" not in raw and "Infinity" not in raw
    rows = json.loads(raw)["rows"]
    assert rows[0]["p"] is None and rows[1]["mcap"] is None and rows[2]["days"] == 7


@PY310
def test_app_route_and_index_context(tmp_path, monkeypatch):
    import app
    d = str(tmp_path / "heatmap")
    hm.save_frozen(_snap(), d)
    monkeypatch.setattr(app, "_HEATMAP_DIR", d)
    c = app.app.test_client()
    r = c.get("/api/heatmap?universe=bist100")
    assert r.status_code == 200 and r.mimetype == "application/json"
    assert r.get_json()["asof"] == "2026-09-23" and r.get_json()["n"] == 100
    assert c.get("/api/heatmap?universe=xutum").status_code == 400
    ctx = app._heatmap_ssr_context()
    assert ctx["heatmap"]["asof"] == "2026-09-23"
    assert len(ctx["heatmap_tiles"]) == 100 and ctx["heatmap_groups"]
    assert c.get("/").status_code == 200
    monkeypatch.setattr(app, "_HEATMAP_DIR", str(tmp_path / "bos"))
    assert c.get("/api/heatmap").status_code == 503
    assert app._heatmap_ssr_context() == {"heatmap": None, "heatmap_groups": [], "heatmap_tiles": []}
