"""D-43a — BIST100 tam kapsam + O18=A kapsam dışı paylar (KONTR/MEGAP/KLNMA/MARKA).

Yerel (py3.9): kapsam.py metinleri + app.py literal'i AST ile. VPS (py3.10+): route'lar.
"""
import ast
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import kapsam  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
PLAN_11 = ["CVKMD", "ENTRA", "GLRMK", "GRSEL", "GWIND", "OBAMS", "PAHOL", "RGYAS", "TRENJ", "TRGYO", "TRMET"]
OUT = ["KONTR", "MEGAP", "KLNMA", "MARKA"]
# Ürün dili (kanon §2-3): AL/SAT, hedef/stop dili, göreli zaman, "Ücretsiz" yok.
FORBIDDEN = re.compile(r"\b(AL|SAT|TP1|TP2|LONG|SHORT)\b|hedef|stop|kâr al|bugün|dün|yarın|günün|ücretsiz",
                       re.IGNORECASE)


def _app_literals():
    tree = ast.parse(open(os.path.join(ROOT, "app.py"), encoding="utf-8").read())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("BIST100", "STOCK_NAMES"):
                out[name] = ast.literal_eval(node.value)
    return out


def test_note_texts_follow_product_language():
    for t in OUT:
        n = kapsam.note(t)
        assert n["etiket"] == "Kapsam dışı" and t in n["metin"]
        assert "sinyal ve skor" in n["metin"]
        assert not FORBIDDEN.search(n["metin"]), n["metin"]
        assert kapsam.faq(t)["a"] == n["metin"]
    assert kapsam.note("THYAO") is None and kapsam.note(None) is None and kapsam.faq("THYAO") is None
    assert kapsam.note("kontr")["metin"].startswith("KONTR, Gözaltı Pazarı'nda")


def test_portfolio_flags_only_for_out_of_scope_positions():
    pos = [{"ticker": "THYAO"}, {"ticker": "kontr"}, {"ticker": 5}, "bozuk", {"ticker": "MARKA"}]
    flags = kapsam.portfolio_flags(pos)
    assert set(flags) == {"KONTR", "MARKA"}
    assert flags["KONTR"]["etiket"] == "Kapsam dışı"
    assert kapsam.portfolio_flags(None) == {}


def test_universe_covers_bist100_and_drops_out_of_scope():
    lit = _app_literals()
    uni = set(lit["BIST100"])
    seed = json.load(open(os.path.join(ROOT, "universe_seed.json"), encoding="utf-8"))
    xu100 = seed["indices"]["XU100"]
    assert len(xu100) == 100
    assert set(xu100) <= uni, sorted(set(xu100) - uni)          # KAP güncel dönem 100/100
    assert set(PLAN_11) <= uni                                    # 01.10 dönemi girenler
    assert not set(OUT) & uni
    assert lit["BIST100"][-1] == "XU030" and len(lit["BIST100"]) == len(uni)
    # BIST30_LITERAL yedeği (dosya yoksa BIST100[:30]) yeni hisselerden etkilenmez
    assert not set(PLAN_11) & set(lit["BIST100"][:30])
    # D-23: sektör artık elle SECTORS değil, KAP alt sektöründen (sector_taxonomy); her hisse
    # tanınan bir KAP sektörüyle kovalanır (sorun listesi boş)
    import sector_taxonomy
    kap = json.load(open(os.path.join(ROOT, "kap_sirket_bilgileri.json"), encoding="utf-8"))
    t2b, _, problems = sector_taxonomy.build(sorted(uni - {"XU030"}), seed["companies"], kap)
    assert not problems, problems
    for t in uni - {"XU030"}:
        assert lit["STOCK_NAMES"].get(t), "ad eksik: %s" % t
        assert t2b.get(t), "sektör eksik: %s" % t
    for t in PLAN_11:
        assert seed["companies"][t]["sector"], t   # ısı haritası grubu KAP sektöründen


@PY310
def test_routes_out_of_scope_page_portfolio_alerts_sitemap_api_data():
    import app
    c = app.app.test_client()
    for t in OUT:
        r = c.get("/hisse/%s" % t)
        assert r.status_code == 200, t
        body = r.get_data(as_text=True)
        assert kapsam.faq(t)["q"] in body            # FAQPage SSS'i notu taşır
        assert "Teknik Güç Skoru" not in body.split("</head>")[0]
    assert c.get("/hisse/ZZZZZ").status_code == 404
    assert c.get("/hisse/XU030").status_code == 404
    assert "TRMET" in app.BIST100 and "KONTR" not in app.BIST100
    assert "KONTR" in app._PF_VALID_TICKERS            # portföy kaydında silinmez
    sm = c.get("/sitemap.xml").get_data(as_text=True)
    assert "/hisse/KONTR<" not in sm and "/hisse/TRMET<" in sm
    with app._lock:
        _old = list(app._cache["data"])
        app._cache["data"] = [app._enrich_stock({"ticker": "THYAO", "price": 1.0, "change_pct": 0.0}),
                              app._enrich_stock({"ticker": "ADEL", "price": 1.0, "change_pct": 0.0}),
                              {"ticker": "XU030", "price": 1.0, "change_pct": 0.0}]
    try:
        d = c.get("/api/data").get_json()
    finally:
        with app._lock:
            app._cache["data"] = _old
    tick = {s["ticker"]: s for s in d["stocks"]}
    assert "XU030" not in tick
    assert tick["THYAO"]["bist100"] is True and tick["ADEL"]["bist100"] is False
    assert len(app.BIST100_MEMBERS) == 100
