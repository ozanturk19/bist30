"""D-23 — sektör taksonomisi: KAP resmi alt sektörü → BIST sektör endeksine hizalı kova.

Yerel (py3.9): sector_taxonomy + app.py BIST100 literal'i (AST) + repo tohumu universe_seed.json
(VPS data/universe.json ile aynı içerik, 24.09) + kap_sirket_bilgileri.json. VPS (py3.10+):
SECTORS/_get_sector bağlantısı, /api/data, /hisse (hero + JSON-LD category + ilgili hisseler),
/api/tarama filtresi ve ısı haritasının donmuş görüntüyü yeniden gruplaması.
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
import sector_taxonomy as st  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
SEED = json.load(open(os.path.join(ROOT, "universe_seed.json"), encoding="utf-8"))
KAP = json.load(open(os.path.join(ROOT, "kap_sirket_bilgileri.json"), encoding="utf-8"))
COMP = SEED["companies"]
FOOD = "Gıda ve İçecek"


def _universe():
    tree = ast.parse(open(os.path.join(ROOT, "app.py"), encoding="utf-8").read())
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "BIST100"):
            return [t for t in ast.literal_eval(node.value) if t not in ("XU030", "XU100")]
    raise AssertionError("BIST100 literal'i bulunamadı")


UNI = _universe()


# ── tablo bütünlüğü ──────────────────────────────────────────────────────────
def test_bucket_table_is_one_to_one_and_readable():
    labels = [b for b, _, _ in st.BUCKETS]
    assert len(labels) == len(set(labels)) and labels[-1] == st.OTHER
    seen = {}
    for label, idx, kaps in st.BUCKETS:
        assert label == label.strip() and label[0].isupper()
        # okunur, kısaltmasız: "GYO", "/", "&" yok; BIST endeks kodu görünen ada girmez
        assert not re.search(r"\bGYO\b|/|&|\bX[A-Z]{3,4}\b", label), label
        if label != st.OTHER:
            assert re.fullmatch(r"X[A-Z]{4}( \+ X[A-Z]{4})?", idx), (label, idx)
        for k in kaps:
            assert st.norm(k) not in seen, "%s iki kovada: %s / %s" % (k, seen.get(st.norm(k)), label)
            seen[st.norm(k)] = label
    # KAP'ın 24.09 sektör listesindeki 46 alt sektörün hepsi tanınıyor
    kap_subs = {c.get("sector") for c in COMP.values() if c.get("sector")}
    assert len(kap_subs) == 46
    assert all(st.is_known(s) for s in kap_subs), sorted(s for s in kap_subs if not st.is_known(s))
    for label, _, _ in st.BUCKETS:
        for bad in ("bugün", "dün", "Ücretsiz", "AL", "SAT", "hedef"):
            assert bad not in label.split()


def test_explicit_covers_exactly_the_22_sectorless_kap_codes():
    sectorless = sorted(t for t, c in COMP.items() if not c.get("sector"))
    assert len(sectorless) == 22 and sorted(st.EXPLICIT) == sectorless
    for t, sub in st.EXPLICIT.items():
        assert st.is_known(sub)
        k = (KAP.get(t) or {}).get("kap_alt_sektor")
        assert k is None or st.norm(k) == st.norm(sub), (t, k, sub)   # KAP şirket sayfasıyla aynı
    # 584 KAP şirketinin tamamı bir kovaya oturur (tanınmayan yok)
    _, _, problems = st.build(sorted(COMP), COMP, KAP)
    assert problems == []


# ── kabul: 233 hisselik evren ───────────────────────────────────────────────
def test_universe_acceptance():
    t2b, by, problems = st.build(UNI, COMP, KAP)
    n = len(UNI)
    assert n == 233 and len(t2b) == n and problems == []
    assert all(t2b[t] in by for t in UNI)                              # her hisse bir kovada
    assert sum(len(v) for v in by.values()) == n
    biggest = max(by.items(), key=lambda kv: len(kv[1]))
    assert len(biggest[1]) <= 0.15 * n, biggest                        # hiçbir kova > %15
    assert len(by.get(st.OTHER, [])) <= 3, by.get(st.OTHER)            # "Diğer" ≤ 3
    assert 18 <= len([b for b in by if b != st.OTHER]) <= 24
    assert list(by)[-1] == st.OTHER and list(by)[:-1] == [b for b in st.LABELS if b in by and b != st.OTHER]


@pytest.mark.parametrize("ticker,bucket", [
    ("AEFES", FOOD), ("CCOLA", FOOD), ("TATGD", FOOD), ("ULKER", FOOD), ("ALKLC", FOOD),
    ("ENKAI", "İnşaat"),
    ("ISMEN", "Finansal Hizmetler"), ("DSTKF", "Finansal Hizmetler"), ("KTLEV", "Finansal Hizmetler"),
    ("GARAN", "Bankacılık"), ("ISCTR", "Bankacılık"), ("TSKB", "Bankacılık"), ("AKBNK", "Bankacılık"),
    ("KRDMD", "Ana Metal Sanayi"), ("TCKRC", "Ana Metal Sanayi"),
    ("MPARK", "Sağlık"), ("LKMNH", "Sağlık"), ("TUREX", "Ulaştırma"), ("GMTAS", "Ticaret"),
    ("DNISI", "Kimya, Petrol ve Plastik"), ("TUPRS", "Kimya, Petrol ve Plastik"),
    ("DOGUB", "Taş ve Toprak"), ("ASELS", "Savunma"), ("TCELL", "İletişim"), ("FENER", "Spor"),
    ("THYAO", "Ulaştırma"), ("EKGYO", "Gayrimenkul"), ("KCHOL", "Holding ve Yatırım"),
    # D-46b uyuşmazlık tablosunun "açıkça başka sektör" (S) satırlarının kalanı
    ("PASEU", "Ulaştırma"), ("PRKAB", "Metal Eşya ve Makine"), ("SMART", "Bilişim"),
    ("TABGD", "Turizm"), ("YESIL", "Holding ve Yatırım"), ("ADESE", "Gayrimenkul"),
    ("EGEEN", "Metal Eşya ve Makine"),
    ("ADEL", st.OTHER), ("AGROT", st.OTHER),
])
def test_named_stocks_land_in_kap_bucket(ticker, bucket):
    t2b, _, _ = st.build(UNI, COMP, KAP)
    assert t2b[ticker] == bucket


# ── kaynak sırası ve dayanıklılık ───────────────────────────────────────────
def test_source_order_universe_then_explicit_then_kap_info():
    comp = {"AAA": {"sector": "BİLİŞİM"}, "GARAN": {"sector": None}, "BBB": {"sector": ""}}
    kap = {"AAA": {"kap_alt_sektor": "BANKALAR"}, "GARAN": {"kap_alt_sektor": "BİLİŞİM"},
           "BBB": {"kap_alt_sektor": "SİGORTA ŞİRKETLERİ"}}
    assert st.kap_sector("AAA", comp, kap) == "BİLİŞİM"          # evren dosyası (haftalık KAP) önce
    assert st.kap_sector("GARAN", comp, kap) == "BANKALAR"       # sektörsüz kod → açık tablo
    assert st.kap_sector("BBB", comp, kap) == "SİGORTA ŞİRKETLERİ"
    assert st.kap_sector("YOK", comp, kap) is None


def test_unknown_or_missing_sector_falls_to_other_with_warning_never_crashes():
    comp = {"NEW1": {"sector": "UZAY MADENCİLİĞİ"}, "NEW2": None, "NEW3": "bozuk", "OK": {"sector": "bilişim"}}
    t2b, by, problems = st.build(["NEW1", "NEW2", "NEW3", "OK", "OK", "NEW4"], comp, {"NEW4": 5})
    assert t2b == {"NEW1": st.OTHER, "NEW2": st.OTHER, "NEW3": st.OTHER, "OK": "Bilişim", "NEW4": st.OTHER}
    assert problems == [("NEW1", "UZAY MADENCİLİĞİ"), ("NEW2", None), ("NEW3", None), ("NEW4", None)]
    assert list(by) == ["Bilişim", st.OTHER]
    assert st.build([], None, None) == ({}, {}, [])
    assert st.bucket(None) == st.OTHER and st.bucket("  gıda,   içecek ve  tütün ") == FOOD
    assert st.bucket_for("YOK", {}, {}, default=None) is None


def test_sort_labels_turkish_alphabet_other_last():
    got = st.sort_labels(["Ulaştırma", st.OTHER, "İnşaat", "İletişim", "Bankacılık", "Holding ve Yatırım",
                          "Gıda ve İçecek", "Çimento"])
    assert got == ["Bankacılık", "Çimento", "Gıda ve İçecek", "Holding ve Yatırım", "İletişim", "İnşaat",
                   "Ulaştırma", st.OTHER]


# ── ısı haritası: aynı taksonomi ────────────────────────────────────────────
def test_heatmap_groups_use_site_taxonomy():
    assert hm.OTHER == st.OTHER
    for label, _, kaps in st.BUCKETS:
        for k in kaps:
            assert hm.group_of(k) == label
    assert hm.group_of(None) == st.OTHER and hm.group_of("TANINMAYAN") == st.OTHER
    for t in SEED["indices"]["XU100"]:                  # harita grubu = /hisse sektör etiketi
        assert hm.group_of(st.kap_sector(t, COMP, KAP)) == st.bucket_for(t, COMP, KAP)


def test_heatmap_regroup_updates_frozen_rows_only_when_known():
    rows = [{"t": "AEFES", "g": "Gıda & İçecek", "p": 1.0}, {"t": "GARAN", "g": "Bankacılık"},
            {"t": "ZZZZ", "g": "Eski Grup"}]
    n = hm.regroup(rows, lambda t: st.bucket_for(t, COMP, KAP, default=None))
    assert n == 1 and [r["g"] for r in rows] == [FOOD, "Bankacılık", "Eski Grup"]
    assert rows[0]["p"] == 1.0 and hm.regroup(None, lambda t: "X") == 0


# ── app.py bağlantısı (yerel: modül düzeyi blok kaynaktan exec) ─────────────
def test_app_module_level_wiring_runs_on_seed(caplog):
    """app.py'deki D-23 bloğu (UNIVERSE/KAP_INFO yükleyiciler + SECTORS kurulumu + _get_sector)
    py3.9'da kaynaktan çalıştırılır: SECTORS elle liste değil, taksonomi çıktısı."""
    import logging
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    parts = [re.search(r"def _load_universe\(\):.*?\n\n\n", src, re.S).group(0),
             re.search(r"def _load_kap_info\(\):.*?\n\n\n", src, re.S).group(0),
             re.search(r"# ── Sektör sınıflandırması ─+\n.*?\n\n\n", src, re.S).group(0),
             re.search(r"def _get_sector\(ticker: str\) -> str:.*?\n\n\n", src, re.S).group(0)]
    assert not re.search(r"^SECTORS\s*=\s*\{", src, re.M)       # elle tutulan liste yok
    ns = {"os": os, "json": json, "sector_taxonomy": st, "logger": logging.getLogger("d23test"),
          "BIST100": UNI + ["XU030"], "INDEX_TICKERS": {"XU030", "XU100"},
          "__file__": os.path.join(ROOT, "app.py")}
    exec(parts[0] + "UNIVERSE = _load_universe()\n" + parts[1] + "KAP_INFO = _load_kap_info()\n"
         + parts[2] + parts[3], ns)
    t2b, by, _ = st.build(UNI, COMP, KAP)
    assert ns["SECTORS"] == by and ns["_TICKER_TO_SECTOR"] == t2b
    assert ns["_get_sector"]("AEFES") == FOOD and ns["_get_sector"]("XU030") == st.OTHER
    # eksik sektör: uyarı + "Diğer", import çökmez
    ns["BIST100"] = UNI + ["ZZNEW", "XU030"]
    with caplog.at_level(logging.WARNING, logger="d23test"):
        exec(parts[2] + parts[3], ns)
    assert ns["_get_sector"]("ZZNEW") == st.OTHER and "ZZNEW" in caplog.text


# ── VPS: app.py bağlantısı ve sayfalar ──────────────────────────────────────
@PY310
def test_app_wiring_api_data_and_pages():
    import app
    t2b, by, _ = st.build(UNI, COMP, KAP)
    if app.UNIVERSE.get("companies"):                    # VPS dosyası tohumla aynı içerikte (24.09)
        assert app.SECTORS == by and app._TICKER_TO_SECTOR == t2b
    assert app._get_sector("AEFES") == FOOD and app._get_sector("ISMEN") == "Finansal Hizmetler"
    assert app._get_sector("XU030") == st.OTHER
    c = app.app.test_client()
    with app._lock:
        _old = list(app._cache["data"])
        app._cache["data"] = [app._enrich_stock({"ticker": t, "price": 1.0, "change_pct": 0.0,
                                                  "signal": "BEKLE"}) for t in app.BIST100]
    try:
        d = c.get("/api/data").get_json()
        tr = c.get("/api/tarama?sector=" + FOOD).get_json()
        body = c.get("/hisse/AEFES").get_data(as_text=True)
        ismen = c.get("/hisse/ISMEN").get_data(as_text=True)
        hub = c.get("/hisseler").get_data(as_text=True)
    finally:
        with app._lock:
            app._cache["data"] = _old
    stocks = [s for s in d["stocks"] if s["ticker"] not in app.INDEX_TICKERS]
    assert len(stocks) == 233
    assert all(s.get("sector") and s["sector"] in d["sectors"] for s in stocks)   # her hissenin kovası var
    assert d["sectors"] == list(app.SECTORS)
    assert {r["ticker"] for r in tr["results"]} == set(app.SECTORS[FOOD])
    assert tr["sectors"] == st.sort_labels(app.SECTORS)
    # hero rozeti, JSON-LD category, ilgili hisseler başlığı ve listesi KAP kovasından
    assert 'class="hib-sector">%s<' % FOOD in body
    assert '"category": "%s"' % FOOD in body
    assert "%s Sektöründen Diğer Hisseler" % FOOD in body
    related_html = body.split("Sektöründen Diğer Hisseler", 1)[1].split("</aside>", 1)[0]
    related = re.findall(r'href="/hisse/([A-Z0-9]+)"', related_html)
    assert related and all(app._get_sector(t) == FOOD for t in related), related
    assert '"category": "Bankacılık"' not in ismen and '"category": "Finansal Hizmetler"' in ismen
    assert hub.index(">İnşaat ") < hub.index(">Kimya, Petrol ve Plastik ") < hub.index(">Ulaştırma ")


@PY310
def test_app_heatmap_serves_frozen_snapshot_with_current_groups(tmp_path, monkeypatch):
    import app
    d = str(tmp_path / "heatmap")
    snap = {"asof": "2026-09-23", "rows": [
        {"t": "AEFES", "g": "Gıda & İçecek", "mcap": 100.0},
        {"t": "GARAN", "g": "Bankacılık", "mcap": 200.0},
        {"t": "ENKAI", "g": "GYO & İnşaat", "mcap": 50.0}]}
    hm.save_frozen(snap, d)
    monkeypatch.setattr(app, "_HEATMAP_DIR", d)
    app._heatmap_mem.update(path=None, mtime=None)
    m = app._heatmap_latest()
    assert {r["t"]: r["g"] for r in m["snap"]["rows"]} == {"AEFES": FOOD, "GARAN": "Bankacılık", "ENKAI": "İnşaat"}
    assert {g["g"] for g in m["groups"]} == {FOOD, "Bankacılık", "İnşaat"}
    app._heatmap_mem.update(path=None, mtime=None)
