"""D-53: ana sayfa SSR alanlari (home_fields) — hisse sayfasi kanonuyla parite + havuz kurali."""
import itertools
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import home_fields as hf  # noqa: E402


# ── fin_answer: hisse.html makrosuyla birebir ────────────────────────────────
def _macro():
    jinja2 = pytest.importorskip("jinja2")
    src = open(os.path.join(ROOT, "templates", "hisse.html"), encoding="utf-8").read()
    m = re.search(r"\{%- macro fin_answer\(hs, hs_available\) -%\}.*?\{%- endmacro -%\}", src, re.S)
    assert m, "fin_answer makrosu hisse.html'de bulunamadi"
    env = jinja2.Environment()
    return env.from_string(m.group(0) + "{{ fin_answer(hs, ok) }}")


def _jinja(tpl, hs):
    return tpl.render(hs=hs, ok=True).strip()


_GRID = [None, 20, 49, 50, 69, 70, 95]


def test_fin_answer_hisse_makrosuyla_tum_izgara():
    tpl = _macro()
    keys = ["karlilik", "nakit_akisi", "kaldirac", "degerleme_buyume"]
    n = 0
    for combo in itertools.product(_GRID, repeat=4):
        cats = {k: v for k, v in zip(keys, combo) if v is not None}
        if not cats:
            continue
        exp = _jinja(tpl, {"categories": cats, "temel_v2": None})
        assert hf.fin_answer({"categories": cats}) == exp, cats
        n += 1
    assert n > 2000


def test_fin_answer_v2_cevap_ve_sinirli_veri():
    tpl = _macro()
    hs = {"categories": {"karlilik": 80}, "temel_v2": {"cevap": "Kalite güçlü, değerleme makul"}}
    assert hf.fin_answer(hs) == _jinja(tpl, hs) == "Kalite güçlü, değerleme makul"
    hs = {"categories": {"karlilik": 80}, "temel_v2": {"limited_data": True}}
    assert hf.fin_answer(hs) == _jinja(tpl, hs) == "Sınırlı veri"


def test_fin_answer_kayit_yok():
    assert hf.fin_answer(None) is None
    assert hf.fin_answer({}) is None
    assert hf.fin_answer({"categories": {}}) is None


# ── valuation: hisse.html tvValuation kanonu ────────────────────────────────
def _fund(fk=None, pd=None, med_fk=None, med_pd=None, var=True):
    return {
        "kap_durum": "var" if var else "hazirlaniyor",
        "kap": {"degerleme_simdi": {"fk": fk, "pd_dd": pd}} if var else None,
        "sektor_ortanca": {"fk": {"deger": med_fk} if med_fk else None,
                           "pd_dd": {"deger": med_pd} if med_pd else None},
        "pe_ratio": 9.0, "pb_ratio": 0.5,
    }


def test_valuation_esikler():
    assert hf.valuation(None, _fund(fk=7.9, med_fk=10)) == "ucuz"        # 0,79
    assert hf.valuation(None, _fund(fk=8.0, med_fk=10)) == "makul"       # 0,80 sinirda makul
    assert hf.valuation(None, _fund(fk=12.5, med_fk=10)) == "makul"      # 1,25 sinirda makul
    assert hf.valuation(None, _fund(fk=12.6, med_fk=10)) == "pahali"


def test_valuation_iki_oran_ve_karisik():
    assert hf.valuation(None, _fund(fk=5, pd=1, med_fk=10, med_pd=2)) == "ucuz"
    assert hf.valuation(None, _fund(fk=5, pd=3, med_fk=10, med_pd=2)) == "karisik"
    assert hf.valuation(None, _fund(fk=5, pd=2, med_fk=10, med_pd=2)) == "ucuz"    # -1 + 0
    assert hf.valuation(None, _fund(fk=15, pd=2, med_fk=10, med_pd=2)) == "pahali"  # +1 + 0


def test_valuation_hukum_yok():
    assert hf.valuation(None, _fund(fk=5)) is None                       # ortanca yok
    assert hf.valuation(None, _fund(fk=-3, med_fk=10)) is None           # zarar: F/K tanimsiz
    assert hf.valuation(None, None) is None
    # pay uyumsuz -> kap oranlari kullanilmaz, kayit var oldugu icin Yahoo'ya da dusmez
    f = _fund(fk=5, med_fk=10)
    f["kap"]["degerleme_simdi"]["pay_uyumsuz"] = True
    assert hf.valuation(None, f) is None
    # kayit yok -> bugunku Yahoo alanlari
    assert hf.valuation(None, _fund(med_fk=10, med_pd=1, var=False)) == "ucuz"


def test_valuation_v2_hukmu_tek_kaynak():
    assert hf.valuation({"temel_v2": {"degerleme": {"hukum": "pahali"}}}, _fund(fk=1, med_fk=10)) == "pahali"
    assert hf.valuation({"temel_v2": {"degerleme": {}}}, _fund(fk=1, med_fk=10)) is None


# ── featured_pool ───────────────────────────────────────────────────────────
def _s(t, bp, sig="AL", comp=0.9, **kw):
    d = {"ticker": t, "signal": sig, "borsapusula_skoru": bp, "hs_available": True, "data_completeness": comp}
    d.update(kw)
    return d


def test_featured_pool_kurallari():
    rows = [_s("B", 80), _s("A", 80), _s("C", 90, sig="SAT"), _s("D", 95, comp=0.79),
            _s("E", 99, stale_reason="insufficient_history:49<120"), _s("F", 99, data_quality="stale"),
            _s("G", None), _s("H", 70, sig="BEKLE"), dict(_s("I", 99), hs_available=False),
            _s("J", 60, comp=None)]
    out = hf.featured_pool(rows, 5)
    assert [s["ticker"] for s in out] == ["A", "B", "H"]      # BP azalan, esitlikte kod artan
    assert len(hf.featured_pool([_s("T%02d" % i, i) for i in range(20)], 5)) == 5


# ── app.py ince baglanti (yerelde 3.9'da atlanir, VPS venv'de kosar) ─────────
def _row(t, bp, sig="AL", **kw):
    d = {"ticker": t, "name": t + " A.S.", "sector": "Sanayi", "signal": sig, "signal_strength": 80,
         "price": 100.0, "change_pct": 1.0, "signal_date": "25.09.2026"}
    d.update(kw)
    return d


def _hs(bp, comp=0.9, cats=None):
    return {"data": {"borsapusula_skoru": bp, "data_completeness": comp, "partial": False,
                     "categories": cats or {"karlilik": 80, "nakit_akisi": 40, "kaldirac": 60, "degerleme_buyume": 55}},
            "ts": 0}


@pytest.fixture
def home_state(app_module, monkeypatch):
    app = app_module
    rows = [_row("AAA", 0), _row("BBB", 0), _row("CCC", 0, sig="SAT"), _row("DDD", 0),
            _row("EEE", 0, price=110.0, change_pct=10.0)]
    monkeypatch.setitem(app._cache, "data", rows)
    monkeypatch.setattr(app, "_financial_health_cache", {
        "AAA": _hs(90), "BBB": _hs(85), "CCC": _hs(99), "DDD": _hs(70, comp=0.5), "EEE": _hs(60)})
    monkeypatch.setattr(app, "_home_extras_cache", {})
    monkeypatch.setattr(app, "_fundamentals_kap", lambda t, d: d)
    monkeypatch.setattr(app, "_get_fundamentals", lambda t: {"pe_ratio": 5.0, "pb_ratio": 0.5})
    monkeypatch.setattr(app, "_fundamentals_temel_v2", lambda t, d: dict(
        d, kap_durum="var", kap={"degerleme_simdi": {"fk": 5.0, "pd_dd": 0.5}},
        sektor_ortanca={"fk": {"deger": 10.0}, "pd_dd": {"deger": 1.0}}))
    return app


def test_ssr_baglami_featured_ve_gundem(home_state):
    ctx = home_state._compute_index_ssr_context()
    assert [r["ticker"] for r in ctx["featured"]] == ["AAA", "BBB", "EEE"]   # SAT ve tamlik<0,8 disarida
    r = ctx["featured"][0]
    assert r["valuation"] == "ucuz" and r["fin_answer"] == "Kârlılık güçlü, nakit akışı zayıf"
    assert r["borsapusula_skoru"] == 90 and r["bps_partial"] is False and r["data_completeness"] == 0.9
    assert set(ctx["gundem"]) == {"new_signals", "eod_date", "eod_label", "closed_message"}
    assert all(t["fin_answer"] and t["borsapusula_skoru"] is not None for t in ctx["top_signals"])
    assert "date" in ctx["bist_level"]


def test_api_data_alanlari(home_state):
    client = home_state.app.test_client()
    d = client.get("/api/data").get_json()
    by = {s["ticker"]: s for s in d["stocks"]}
    assert "xu100_date" in d
    assert by["AAA"]["valuation"] == "ucuz" and by["AAA"]["fin_answer"].startswith("Kârlılık")
    assert by["EEE"]["lim"] == "tavan" and "lim" not in by["AAA"]
    # havuz disi satirda alan yok (yerinde silinir, onceki cagridan kalmaz)
    assert "valuation" not in by["CCC"] and "fin_answer" not in by["DDD"]
    d2 = client.get("/api/data").get_json()
    assert {s["ticker"] for s in d2["stocks"] if "valuation" in s} == {"AAA", "BBB", "EEE"}
