"""D-23b — sektör düzeltme tablosu (Ozan 02.10: "FROTO, TOASO metal eşya ve makine sektöründe, bu
doğru mu?").

KAP sınıfı yatırımcıya yanlış görünen hisseler açık, gerekçeli tabloyla (sector_taxonomy.OVERRIDES)
sıradan yatırımcının "bu şirketin sektörü" diyeceği kovaya taşınır; kalan her hisse KAP'tan.
Sektör ortancası küçülen kovada KAP sektörü havuzuna yedeklenir (ortanca D-23'ten geri gitmez).

Yerel (py3.9): sector_taxonomy + heatmap + kap_temel_v2 + kesfet, repo tohumu universe_seed.json
ve kap_sirket_bilgileri.json. VPS (py3.10+): app bağlantısı ve canlı KAP kayıtlarıyla ortanca yedeği.
"""
import ast
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import heatmap as hm  # noqa: E402
import kap_temel_v2 as kt  # noqa: E402
import kesfet  # noqa: E402
import sector_taxonomy as st  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
SEED = json.load(open(os.path.join(ROOT, "universe_seed.json"), encoding="utf-8"))
KAP = json.load(open(os.path.join(ROOT, "kap_sirket_bilgileri.json"), encoding="utf-8"))
COMP = SEED["companies"]
AUTO, DUR, HOLD = "Otomotiv", "Dayanıklı Tüketim", "Holding ve Yatırım"


def _universe():
    tree = ast.parse(open(os.path.join(ROOT, "app.py"), encoding="utf-8").read())
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "BIST100"):
            return [t for t in ast.literal_eval(node.value) if t not in ("XU030", "XU100")]
    raise AssertionError("BIST100 literal'i bulunamadı")


UNI = _universe()


# ── düzeltme tablosu ────────────────────────────────────────────────────────
def test_override_table_is_explicit_and_reasoned():
    assert 15 <= len(st.OVERRIDES) <= 30                        # kısa liste: KAP temel, düzeltme istisna
    for t, (group, why) in st.OVERRIDES.items():
        assert re.fullmatch(r"[A-Z0-9]{3,6}", t), t
        assert group in st.LABELS and group != st.OTHER, (t, group)
        assert why and why == why.strip() and "\n" not in why and 15 <= len(why) <= 110, (t, why)
        assert t in COMP, t                                     # KAP'ta işlem gören şirket
        # tablo yalnız gerçekten farklı olanı taşır (KAP zaten doğruysa satır yok)
        assert st.kap_bucket_for(t, COMP, KAP) != group, (t, group)
        for bad in ("AL", "SAT", "hedef", "bugün", "Ücretsiz"):
            assert bad not in why.split(), (t, why)


@pytest.mark.parametrize("ticker,bucket", [
    # araç üreticileri ve yan sanayi: "Metal Eşya ve Makine" değil
    ("FROTO", AUTO), ("TOASO", AUTO), ("OTKAR", AUTO), ("ASUZU", AUTO), ("KARSN", AUTO), ("TTRAK", AUTO),
    ("TMSN", AUTO), ("EGEEN", AUTO), ("FMIZP", AUTO), ("JANTS", AUTO), ("PARSN", AUTO), ("DOAS", AUTO),
    ("ARCLK", DUR), ("VESTL", DUR), ("VESBE", DUR), ("ARZUM", DUR), ("YATAS", DUR),
    ("SISE", "Taş ve Toprak"), ("TAVHL", "Ulaştırma"), ("THYAO", "Ulaştırma"), ("PGSUS", "Ulaştırma"),
    ("TABGD", "Gıda ve İçecek"),
    ("GENIL", "İlaç ve Sağlık"), ("SELEC", "İlaç ve Sağlık"), ("MEDTR", "İlaç ve Sağlık"), ("MPARK", "İlaç ve Sağlık"),
    # KAP'ta kalanlar: gerçek holdingler ve makine/elektrikli ekipman üreticileri
    ("KCHOL", HOLD), ("SAHOL", HOLD), ("DOHOL", HOLD), ("AGHOL", HOLD), ("TKFEN", HOLD), ("ALARK", HOLD),
    ("ASTOR", "Metal Eşya ve Makine"), ("PRKAB", "Metal Eşya ve Makine"), ("KATMR", "Metal Eşya ve Makine"),
    ("BIMAS", "Ticaret"), ("MGROS", "Ticaret"), ("TUPRS", "Kimya, Petrol ve Plastik"),
])
def test_named_stocks(ticker, bucket):
    t2b, _, _ = st.build(UNI, COMP, KAP)
    assert t2b[ticker] == bucket
    assert st.bucket_for(ticker, COMP, KAP) == bucket


def test_sise_and_tavhl_not_holding_holdings_are_diversified():
    t2b, by, _ = st.build(UNI, COMP, KAP)
    assert "SISE" not in by[HOLD] and "TAVHL" not in by[HOLD]
    assert not set(by[HOLD]) & set(st.OVERRIDES)
    assert "Metal Eşya ve Makine" in by and not {"FROTO", "TOASO", "ARCLK", "VESTL"} & set(by["Metal Eşya ve Makine"])


def test_brisa_has_a_bucket():
    """BRISA KAP'ta sektörlü (Kimya, Lastik) ama 233 hisselik kapsamda değil; tabloda Otomotiv."""
    assert "BRISA" not in UNI
    assert st.bucket_for("BRISA", COMP, KAP) == AUTO
    assert st.build(["BRISA"], COMP, KAP) == ({"BRISA": AUTO}, {AUTO: ["BRISA"]}, [])
    assert st.bucket_for("BRISA", {}, {}, default=None) == AUTO     # KAP verisi olmasa da kovası var


# ── kabul: sektörsüz yok, boyut sınırı, okunur sayı ─────────────────────────
def test_no_sectorless_and_size_caps():
    t2b, by, problems = st.build(UNI, COMP, KAP)
    n = len(UNI)
    assert n == 233 and problems == [] and len(t2b) == n
    assert all(t2b[t] and t2b[t] in by for t in UNI)                 # sektörsüz hisse 0
    assert max(len(v) for v in by.values()) <= 0.15 * n              # hiçbir kova %15'i aşmaz (≤34)
    assert len(by.get(st.OTHER, [])) <= 2 and sorted(by[st.OTHER]) == ["ADEL", "AGROT"]
    assert 24 <= len([b for b in by if b != st.OTHER]) <= 28
    assert len(by[AUTO]) == 12 and len(by[DUR]) == 5 and len(by[HOLD]) == 26
    # KAP'ın 584 şirketi + tablo: tanınmayan yok
    assert st.build(sorted(set(COMP) | set(st.OVERRIDES)), COMP, KAP)[2] == []


def test_labels_readable_no_abbreviation():
    for label in st.LABELS:
        assert not re.search(r"\bGYO\b|/|&|\.|\bX[A-Z]{3,4}\b", label), label
    assert "Sağlık" not in st.LABELS and "İlaç ve Sağlık" in st.LABELS
    assert st.LABELS.index("Metal Eşya ve Makine") < st.LABELS.index(AUTO) < st.LABELS.index(DUR)


def test_overrides_precede_kap_everywhere():
    comp = {"FROTO": {"sector": "BİLİŞİM"}}
    assert st.bucket_for("FROTO", comp, {}) == AUTO
    assert st.kap_bucket_for("FROTO", comp, {}) == "Bilişim"
    assert st.bucket_of_ticker("FROTO", "BİLİŞİM") == AUTO and st.bucket_of_ticker(None, "BİLİŞİM") == "Bilişim"
    assert st.kap_bucket_for("YOK", {}, {}, default=None) is None


# ── ısı haritası ────────────────────────────────────────────────────────────
def test_heatmap_uses_overrides_and_hides_contradicting_sub():
    assert hm.group_of("HOLDİNGLER VE YATIRIM ŞİRKETLERİ", "TAVHL") == "Ulaştırma"
    assert hm.group_of("HOLDİNGLER VE YATIRIM ŞİRKETLERİ") == HOLD
    assert hm.sub_of("HOLDİNGLER VE YATIRIM ŞİRKETLERİ", "TAVHL") is None
    assert hm.sub_of("ULAŞTIRMA VE DEPOLAMA", "THYAO") == "Ulaştırma ve Depolama"
    rows = [{"t": "FROTO", "g": "Metal Eşya ve Makine", "sub": "Metal Eşya Makine", "p": 1.0},
            {"t": "THYAO", "g": "Ulaştırma", "sub": "Ulaştırma ve Depolama"}]
    n = hm.regroup(rows, lambda t: st.bucket_for(t, COMP, KAP, default=None))
    assert n == 1 and rows[0]["g"] == AUTO and rows[0]["sub"] is None and rows[0]["p"] == 1.0
    assert rows[1] == {"t": "THYAO", "g": "Ulaştırma", "sub": "Ulaştırma ve Depolama"}


def test_heatmap_build_groups_xu100_like_site():
    members = SEED["indices"]["XU100"]
    sectors = {t: st.kap_sector(t, COMP, KAP) for t in members}
    official = {"stocks": {t: {"close": 10.0, "prev_close": 10.0} for t in members}, "indices": {}}
    snap = hm.build("2026-10-01", members, official, {}, {}, {}, sectors, {}, [], "x")
    g = {r["t"]: r for r in snap["rows"]}
    for t in members:
        assert g[t]["g"] == st.bucket_for(t, COMP, KAP)
        assert (g[t]["sub"] is None) == (t in st.OVERRIDES)
    if "FROTO" in g:
        assert g["FROTO"]["g"] == AUTO


# ── sektör ortancası: küçülen kovada KAP sektörü yedeği ─────────────────────
def _km(vals):
    return {t: {"fk": fk, "pd_dd": pd, "ozsermaye_karliligi": roe} for t, (fk, pd, roe) in vals.items()}


def test_sector_median_falls_back_to_kap_pool_only_when_peers_short():
    km = _km({"A1": (10, 1.0, 5), "A2": (12, 1.2, 6), "A3": (None, 0.8, -2),
              "B1": (20, 2.0, 9), "B2": (22, 2.2, 8), "B3": (24, 2.4, 7), "B4": (26, 2.6, 6), "B5": (None, 3.0, -1)})
    site = {"A1": "Yeni", "A2": "Yeni", "A3": "Yeni", "B1": "Eski", "B2": "Eski", "B3": "Eski", "B4": "Eski", "B5": "Eski"}
    kapb = {t: "Eski" for t in site}
    plain = kt.sector_medians(km, site.get, "Yeni")
    assert plain == {"fk": None, "pd_dd": None, "ozsermaye_karliligi": None}      # 3 akran < 5
    fb = kt.sector_medians(km, site.get, "Yeni", kapb.get, "Eski")
    assert fb["fk"] == {"deger": 21.0, "n": 6, "kapsam": "sektor", "havuz": "kap"}
    assert fb["pd_dd"]["n"] == 8 and fb["pd_dd"]["havuz"] == "kap"
    # kovada yeterli akran varsa kendi kovası (yedek işaretsiz); metrik başına karar
    own = kt.sector_medians(km, site.get, "Eski", kapb.get, "Eski")
    assert own["pd_dd"] == {"deger": 2.4, "n": 5, "kapsam": "sektor"}                # 5 akran: kendi kovası
    assert own["fk"] == {"deger": 21.0, "n": 6, "kapsam": "sektor", "havuz": "kap"}  # 4 akran: KAP havuzu
    # 'Diğer' ve belirsiz kova: yedek de yok
    assert kt.sector_medians(km, site.get, "Diğer", kapb.get, "Eski")["pd_dd"] is None
    assert kt.sector_medians(km, site.get, "Yeni", kapb.get, "Diğer")["pd_dd"] is None
    assert kt.sector_medians(km, site.get, "Yeni") == kt.sector_medians(km, site.get, "Yeni", None, None)


def test_kesfet_with_fallback_fills_only_missing():
    med = {"fk": None, "pd_dd": {"deger": 1.0, "n": 6, "kapsam": "sektor"}, "roe_ust": None}
    kapm = {"fk": {"deger": 9.0, "n": 7, "kapsam": "sektor"}, "pd_dd": {"deger": 2.0, "n": 9, "kapsam": "sektor"},
            "roe_ust": None}
    out = kesfet.with_fallback(med, kapm)
    assert out["fk"] == {"deger": 9.0, "n": 7, "kapsam": "sektor", "havuz": "kap"}
    assert out["pd_dd"] == med["pd_dd"] and out["roe_ust"] is None
    assert kesfet.with_fallback(med, None) == med and kesfet.with_fallback(None, None) == {}
    assert med["fk"] is None                                                          # girdi değişmez


def test_kesfet_build_keeps_d23_lists_when_bucket_shrinks():
    """Gerçek KAP kaydıyla (D-59 fikstürü): iki şirket 2 kişilik yeni kovaya taşınınca kendi kovasında
    ortanca yok; kap_bucket_of verilince listeler D-23'teki (tek KAP kovası) ile birebir aynı."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import test_d59_kesfet as d59
    stocks, entries, recs, bucket = d59._universe()
    base = kesfet.build(stocks, entries, recs, {}, bucket, {}, d59.TODAY)["listeler"]
    site = dict(bucket, K1="Yeni Kova", K2="Yeni Kova")
    no_fb = kesfet.build(stocks, entries, recs, {}, site, {}, d59.TODAY)["listeler"]
    fb = kesfet.build(stocks, entries, recs, {}, site, {}, d59.TODAY, kap_bucket_of=bucket)["listeler"]
    ucuz = [r["ticker"] for r in base["sektorune_gore_ucuz"]]
    assert {"K1", "K2"} <= set(ucuz)
    assert not {"K1", "K2"} & {r["ticker"] for r in no_fb["sektorune_gore_ucuz"]}   # yedeksiz: kayıp
    rows = lambda ls, ts: {(k, r["ticker"], r["degerleme"], r["neden"]) for k, v in ls.items()
                           for r in v if r["ticker"] in ts}
    assert rows(fb, {"K1", "K2"}) == rows(base, {"K1", "K2"})                       # yedekle: D-23 ortancası
    assert {k: {r["ticker"] for r in v} for k, v in fb.items()} == {k: {r["ticker"] for r in v} for k, v in base.items()}
    assert {r["ticker"]: r["sector"] for r in fb["sektorune_gore_ucuz"]}["K1"] == "Yeni Kova"


# ── VPS: app bağlantısı + canlı KAP kayıtlarıyla "ortanca geri gitmez" ──────
@PY310
def test_app_overrides_and_median_never_regresses():
    import app
    t2b, by, _ = st.build(UNI, COMP, KAP)
    if app.UNIVERSE.get("companies"):
        assert app.SECTORS == by and app._TICKER_TO_SECTOR == t2b
    assert app._get_sector("FROTO") == AUTO and app._get_kap_bucket("FROTO") == "Metal Eşya ve Makine"
    assert app._get_sector("SISE") == "Taş ve Toprak" and app._get_kap_bucket("SISE") == HOLD
    km = app._kap_sector_metrics()
    lost = []
    for t in UNI:
        kb = app._get_kap_bucket(t)
        before = kt.sector_medians(km, app._get_kap_bucket, kb)                     # D-23 (yalnız KAP)
        after = kt.sector_medians(km, app._get_sector, app._get_sector(t), app._get_kap_bucket, kb)
        lost += [(t, k) for k in before if before[k] and not after[k]]
    assert lost == []
