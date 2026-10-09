"""D-40c: Temel skor v2 (temel_skor_v2) -- 5 eksen, sablonlar, veri notu, monotonluk.

Gercek KAP kayitlari: tests/fixtures/kap_temel_v2 (D-40a2 fikstürleri, VPS 25.09 uretimi).
Siralama gruplari en az 5 sirket istedigi icin gercek sirketin yanina degerleri bilinen
yapay akranlar konur (akran = ayni sablon/esas, gostergeleri elle verilmis kopya).
app.py'yi import etmez (py3.9 yerel kapida kosar).
"""
import copy
import gzip
import json
import math
import os
import random
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import financial_health_score as fhs  # noqa: E402
import tarama_fields  # noqa: E402
import temel_skor_v2 as ts  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_temel_v2")
TODAY = date(2026, 9, 25)
PRICE = {"TUPRS": 410.75, "THYAO": 288.5, "GARAN": 133.9, "BIMAS": 422.75, "ANSGR": 25.12, "EKGYO": 19.58}
SHARES = {"TUPRS": 1926795598.0, "THYAO": 1372283353.0, "GARAN": 4200000000.0, "BIMAS": 1185780000.0,
          "ANSGR": 2000000000.0, "EKGYO": 3661120138.0}
BANNED = ("AL ", "SAT ", " al", "sat.", "hedef", "potansiyel", "tavsiye", "Orta", "Zayıf şirket", "sağlam değil")


def _rec(t):
    with gzip.open(os.path.join(FIX, t + ".json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


def _inp(t, **kw):
    return ts.company_inputs(_rec(t), kw.get("price", PRICE[t]), TODAY, kw.get("shares", SHARES[t]))


def _peers(base, n=4, **vals):
    """base girdisinin kopyalari; vals: {metrik: [deger1..n]}."""
    out = []
    for i in range(n):
        p = copy.deepcopy(base)
        for m, xs in vals.items():
            p[m] = xs[i]
        out.append(p)
    return out


def _universe(target, bucket, peers):
    inputs = {target[0]: target[1]}
    buckets = {target[0]: bucket}
    for i, p in enumerate(peers):
        inputs["P%d" % i] = p
        buckets["P%d" % i] = bucket
    return inputs, buckets


# ----------------------------------------------------------------------------- yontem birimleri

def test_percent_rank_uclar_esitlik_ve_monotonluk():
    pool = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert [ts.percent_rank(v, pool) for v in pool] == [0.0, 25.0, 50.0, 75.0, 100.0]
    assert ts.percent_rank(2.0, [2.0, 2.0, 2.0, 1.0, 3.0]) == 50.0       # esitler ortalama sira
    assert ts.percent_rank(None, pool) is None and ts.percent_rank(1.0, [1.0]) is None
    others = [3.0, 7.0, 7.0, 10.0, 12.5]
    prev = -1
    for v in [x / 2.0 for x in range(0, 30)]:
        pr = ts.percent_rank(v, others + [v])
        assert pr >= prev
        prev = pr


def test_degerleme_puani_kanon_esikleri_ve_monoton():
    assert ts.valuation_points(1.0) == 50.0
    assert ts.valuation_points(0.8) == 66.1 and ts.valuation_points(1.25) == 33.9     # 0,80 / 1,25 simetrik
    assert ts.valuation_points(0.5) == 100.0 and ts.valuation_points(2.0) == 0.0
    assert ts.valuation_points(0.1) == 100.0 and ts.valuation_points(9.0) == 0.0     # sinirli
    assert ts.valuation_points(0) is None and ts.valuation_points(None) is None
    qs = [0.2 + i * 0.05 for i in range(60)]
    pts = [ts.valuation_points(q) for q in qs]
    assert all(a >= b for a, b in zip(pts, pts[1:]))


def test_hukum_kanon_kurali_d51_va_ile_ayni():
    code = {"ucuz": "u", "makul": "m", "pahali": "p", "karisik": "k", None: None}
    med = {"sector": {"S": {"pe": (10.0, 5), "pb": (1.0, 5)}}, "market": {}}
    rnd = random.Random(40)
    for _ in range(300):
        pe, pb = rnd.uniform(3, 20), rnd.uniform(0.3, 2.5)
        assert code[ts.valuation_verdict([pe / 10.0, pb / 1.0])] == tarama_fields.derive_valuation_band(pe, pb, "S", med)
    assert ts.valuation_verdict([0.7, 1.3]) == "karisik" and ts.valuation_verdict([0.7, 1.1]) == "ucuz"
    assert ts.valuation_verdict([1.3]) == "pahali" and ts.valuation_verdict([]) is None


def test_temel_agirlikli_ortalama_eksik_eksen_dagilir():
    assert sum(ts.WEIGHTS.values()) == 100
    full = {"kalite": 80.0, "degerleme": 50.0, "buyume": 60.0, "bilanco": 40.0, "temettu": 0.0}
    assert ts.weighted_temel(full) == round((80 * 30 + 50 * 20 + 60 * 20 + 40 * 20 + 0 * 10) / 100)
    missing = dict(full, degerleme=None)
    assert ts.weighted_temel(missing) == round((80 * 30 + 60 * 20 + 40 * 20) / 80)
    assert ts.weighted_temel({"kalite": 90.0, "buyume": 90.0, "degerleme": None, "bilanco": None,
                              "temettu": None}) is None          # 3 eksenden az: skor yok


def test_bayrak_yalniz_1_acar():
    assert ts.enabled({"TEMEL_V2": "1"}) and ts.enabled({"TEMEL_V2": " 1 "})
    assert not any(ts.enabled({"TEMEL_V2": v}) for v in ("", "0", "true", "yes", "2"))
    assert not ts.enabled({})


# ----------------------------------------------------------------------------- monotonluk (kabul)

def _synthetic_universe(seed, tpl="sanayi", n=8):
    rnd = random.Random(seed)
    base = _inp("TUPRS") if tpl == "sanayi" else _inp("GARAN")
    inputs, buckets = {}, {}
    for i in range(n):
        p = copy.deepcopy(base)
        for m in ts.HIGHER_BETTER:
            if m in p and p[m] is not None:
                p[m] = round(rnd.uniform(-30, 60), 2)
        p["fk"], p["pd_dd"] = round(rnd.uniform(2, 30), 2), round(rnd.uniform(0.3, 4), 2)
        p["verim"] = round(rnd.choice([0.0, rnd.uniform(0.5, 9)]), 2)
        inputs["S%d" % i] = p
        buckets["S%d" % i] = "Kova"
    return inputs, buckets


@pytest.mark.parametrize("tpl,seed", [("sanayi", 1), ("sanayi", 2), ("banka", 3)])
def test_monotonluk_daha_iyi_girdi_eksen_ve_temeli_dusurmez(tpl, seed):
    inputs, buckets = _synthetic_universe(seed, tpl)
    axis_of = {m: ax for ax, ms in ts.INPUTS[tpl].items() for m in ms}
    checked = 0
    for m in list(ts.HIGHER_BETTER) + ["fk", "pd_dd", "verim"]:
        if m not in axis_of:
            continue
        better_up = ts.HIGHER_BETTER.get(m, m == "verim")
        grid = [x / 4.0 for x in range(1, 240)] if m in ("fk", "pd_dd", "verim") else [x / 2.0 - 40 for x in range(0, 220)]
        if not better_up:
            grid = list(reversed(grid))
        prev_ax = prev_t = -1.0
        for v in grid:                     # deger "iyi" yone dogru ilerliyor
            inputs["S0"][m] = v
            r = ts.score_universe(inputs, buckets)["S0"]["detay"]
            ax = r["eksenler"][axis_of[m]]["puan"]
            assert ax is not None and ax >= prev_ax - 1e-9, (m, v, ax, prev_ax)
            assert r["temel"] >= prev_t, (m, v)
            prev_ax, prev_t = ax, r["temel"]
        checked += 1
    assert checked >= 8


# ----------------------------------------------------------------------------- sablonlar (gercek kayit)

def test_tuprs_sanayi_eksenleri_cumleler_ve_piotroski():
    t = _inp("TUPRS")
    assert (t["sablon"], t["esas"], t["roe"], t["saglamlik_ham"]) == \
        ("sanayi", "tms29", 14.8, {"yontem": "piotroski", "puan": 7, "toplam": 9})
    peers = _peers(t, roe=[5.0, 10.0, 20.0, 25.0], net_marj=[1.0, 2.0, 5.0, 8.0], fk=[8.0, 10.0, 14.0, 16.0],
                   pd_dd=[0.6, 0.9, 1.1, 1.3], gelir_deg=[-30.0, -10.0, 5.0, 10.0])
    inputs, buckets = _universe(("TUPRS", t), "Kimya", peers)
    d = ts.score_universe(inputs, buckets)["TUPRS"]["detay"]
    k = d["eksenler"]
    assert d["temel"] is not None and not d["limited_data"] and d["veri_notu"] == "A" and d["veri_tamligi"] == 1.0
    assert k["kalite"]["girdiler"]["saglamlik"]["puan"] == 77.8           # Piotroski 7/9
    assert k["kalite"]["girdiler"]["roe"]["puan"] == 50.0                 # 5 sirketin ortasi
    assert k["kalite"]["cumle"] == ("Özsermaye kârlılığı son 12 ayda %14,8; 2025 net kâr marjı %3,6; "
                                    "sağlamlık kontrolü 7/9.")
    assert k["bilanco"]["cumle"] == "Net nakit 57,0 Mrd ₺ · cari oran 1,40."
    assert k["buyume"]["cumle"].startswith("2025: hasılat −%21,7, net kâr +%23,1 · 2026 ilk yarı: hasılat +%")
    assert k["buyume"]["cumle"].endswith("(enflasyon düzeltmeli).")
    assert k["temettu"]["cumle"].startswith("Son 12 ay temettü verimi %") and "önceki 12 ayda da ödeme var" in k["temettu"]["cumle"]
    # F/K 410,75 fiyatla 11,73; kovanin ortancasi 11,73 (5 degerin ortasi) -> oran 1,0
    assert d["degerleme"]["fk"] == 11.73 and d["ortanca"]["fk"] == {"deger": 11.73, "n": 5, "kapsam": "sektor"}
    assert d["degerleme"]["oran"]["fk"] == 1.0 and d["degerleme"]["hukum"] == "pahali"   # PD/DD 1,74 / 1,1
    assert d["degerleme"]["kapsam"] == "sektor"
    assert "F/K 11,73 · sektör ortancası 11,73" in k["degerleme"]["cumle"]
    assert d["cevap"] and not any(w in d["cevap"] for w in BANNED)


def test_garan_banka_sablonu_5_madde_kap_ortancasi():
    g = _inp("GARAN")
    assert g["sablon"] == "banka" and g["kredi_mevduat"] == 86.21 and g["roe"] == 24.72
    peers = _peers(g, roe=[14.0, 18.0, 20.0, 22.0], gider_gelir=[38.0, 45.0, 50.0, 55.0],
                   fk=[4.0, 4.5, 5.0, 6.0], pd_dd=[0.7, 0.9, 1.0, 1.3])
    inputs, buckets = _universe(("GARAN", g), "Bankacılık", peers)
    d = ts.score_universe(inputs, buckets)["GARAN"]["detay"]
    k = d["eksenler"]
    assert set(k["kalite"]["girdiler"]) == {"roe", "gider_gelir", "saglamlik"}
    assert d["ortanca"]["ozsermaye_karliligi"] == {"deger": 20.0, "n": 5, "kapsam": "sektor"}
    # 5 madde: ozsermaye karliligi 24,72 > banka ortancasi 20,0 gecer -> 3/5 (D-40a2 testiyle ayni sonuc)
    assert d["saglamlik"] == {"yontem": "banka5", "puan": 3, "toplam": 5}
    assert k["kalite"]["cumle"] == ("Özsermaye kârlılığı son 12 ayda %24,7 · banka ortancası %20,0; "
                                    "2025 gider / gelir %43,5; sağlamlık kontrolü 3/5.")
    assert k["bilanco"]["cumle"].startswith("Kredi / mevduat %86,2 · özkaynak / varlık %")
    assert "faaliyet gelirleri" in k["buyume"]["cumle"] and k["buyume"]["cumle"].endswith("(nominal TL).")
    assert d["degerleme"]["hukum"] in ("ucuz", "makul", "pahali", "karisik")


def test_degerleme_kucuk_sektorde_piyasa_geneli_yedegi_cpo1828():
    """CPO-1828 (09.10): sektorde <5 akran -> hukumsuz birakilmaz, BIST geneli (piyasa)
    ortancasina duser; kapsam alani 'piyasa' olarak isaretlenir (tarama_fields ile ayni desen)."""
    t = _inp("TUPRS")
    small_peers = _peers(t, n=2, fk=[9.0, 10.0], pd_dd=[1.2, 1.3])
    inputs, buckets = _universe(("TUPRS", t), "Savunma", small_peers)
    extra = _peers(t, n=5, fk=[6.0, 7.0, 8.0, 12.0, 14.0], pd_dd=[0.8, 0.9, 1.0, 1.5, 1.6])
    for i, p in enumerate(extra):
        inputs["M%d" % i] = p
        buckets["M%d" % i] = "Diğer Sektör"
    d = ts.score_universe(inputs, buckets)["TUPRS"]["detay"]
    assert d["ortanca"]["fk"]["kapsam"] == "piyasa" and d["ortanca"]["pd_dd"]["kapsam"] == "piyasa"
    assert d["degerleme"]["kapsam"] == "piyasa"
    assert d["degerleme"]["hukum"] in ("ucuz", "makul", "pahali", "karisik")
    assert d["eksenler"]["degerleme"]["puan"] is not None
    assert "piyasa ortancası" in d["eksenler"]["degerleme"]["cumle"]


def test_sigorta_sablonu_durust_not_bilanco_yok_4_sirketle_sinirli():
    a = _inp("ANSGR")
    assert a["sablon"] == "sigorta" and "sigorta_kalemleri_sinirli" in a["veri_sorunlari"]
    # Borsada 4 sigorta sirketi var: 5'ten az grup -> kalite/buyume siralanmaz, degerleme hukmu yok
    peers = _peers(a, n=3, roe=[26.7, 40.0, 51.0], fk=[3.7, 5.0, 6.1], pd_dd=[1.0, 2.0, 3.1])
    inputs, buckets = _universe(("ANSGR", a), "Sigorta", peers)
    r = ts.score_universe(inputs, buckets)["ANSGR"]
    d = r["detay"]
    assert d["limited_data"] and d["temel"] is None and d["sebep"] == "eksen_yetersiz"
    assert r["saglik"]["categories_na"] == ["bilanco"] and d["veri_notu"] == "B"
    assert "prim, hasar ve teknik karşılık" in d["sablon_notu"]
    assert d["eksenler"]["bilanco"]["puan"] is None and "hesaplanmıyor" in d["eksenler"]["bilanco"]["cumle"]
    assert "Prim ve hasar kalemleri okunmadığı" in d["eksenler"]["kalite"]["cumle"]
    assert "en az 5 şirket" in d["eksenler"]["degerleme"]["cumle"] and d["degerleme"]["hukum"] is None
    # 5 sigorta sirketi olsaydi skor verilirdi (kalite yalniz ozsermaye karliligiyla)
    peers5 = _peers(a, n=4, roe=[26.7, 40.0, 51.0, 30.0], fk=[3.7, 5.0, 6.1, 4.0], pd_dd=[1.0, 2.0, 3.1, 1.5])
    d5 = ts.score_universe(*_universe(("ANSGR", a), "Sigorta", peers5))["ANSGR"]["detay"]
    assert d5["temel"] is not None and list(d5["eksenler"]["kalite"]["girdiler"]) == ["roe"]


def test_gyo_sablonu_yalniz_pd_dd_ve_net_borc_ozkaynak():
    e = _inp("EKGYO")
    assert e["sablon"] == "gyo" and e["fk"] is None and e["pd_dd"] == 0.49     # son 12 ay zarar: F/K yok
    peers = _peers(e, pd_dd=[0.3, 0.4, 0.6, 0.8], nb_ozkaynak=[-5.0, 10.0, 40.0, 60.0])
    d = ts.score_universe(*_universe(("EKGYO", e), "Gayrimenkul", peers))["EKGYO"]["detay"]
    assert list(d["eksenler"]["degerleme"]["girdiler"]) == ["pd_dd"] and list(d["degerleme"]["oran"]) == ["pd_dd"]
    assert "(GYO'da F/K kullanılmıyor)" in d["eksenler"]["degerleme"]["cumle"]
    assert set(d["eksenler"]["bilanco"]["girdiler"]) == {"nb_ozkaynak", "cari_oran"}
    assert d["eksenler"]["bilanco"]["cumle"].startswith("Net borç özkaynağın %")


def test_thyao_duzeltmesiz_esas_ve_kucuk_sektorde_hukum_yok():
    t = _inp("THYAO")
    assert t["esas"] == "yabanci_para" and ts.BASIS_CLASS[t["esas"]] == "duzeltmesiz"
    d = ts.score_universe({"THYAO": t}, {"THYAO": "Ulaştırma"})["THYAO"]["detay"]
    assert d["degerleme"]["hukum"] is None and d["eksenler"]["degerleme"]["puan"] is None
    assert "(TL'ye çevrilmiş)" in d["eksenler"]["buyume"]["cumle"]
    assert d["eksenler"]["bilanco"]["cumle"] == "Net borç FAVÖK'ün 2,68 katı · cari oran 0,99."
    assert d["eksenler"]["temettu"]["cumle"] == "Son 12 ayda ödeme yok · önceki 12 ayda ödeme var."
    # esasa duyarli gosterge (ozsermaye karliligi) reel TL sirketleriyle ayni grupta siralanmaz
    tu = _inp("TUPRS")
    mixed = {"THYAO": t, "A": tu, "B": copy.deepcopy(tu), "C": copy.deepcopy(tu), "D": copy.deepcopy(tu)}
    dm = ts.score_universe(mixed, {k: "Ulaştırma" for k in mixed})["THYAO"]["detay"]
    assert dm["eksenler"]["kalite"]["girdiler"]["roe"]["puan"] is None       # 'duzeltmesiz' grupta 5 sirket yok
    assert dm["eksenler"]["kalite"]["girdiler"]["net_marj"]["puan"] is not None   # oran: sektor kovasinda


def test_ozkaynak_okunamadi_ile_negatif_ayrilir():
    t = _inp("TUPRS")
    neg = dict(t, roe=None, ozkaynak=-5.0e9)
    miss = dict(t, roe=None, ozkaynak=None)
    s_neg = ts.score_universe({"N": neg}, {"N": "K"})["N"]["detay"]["eksenler"]["kalite"]["cumle"]
    s_miss = ts.score_universe({"M": miss}, {"M": "K"})["M"]["detay"]["eksenler"]["kalite"]["cumle"]
    assert s_neg.startswith("Özkaynak negatif;") and s_miss.startswith("Özkaynak kalemi raporda okunamadı;")


def test_kap_kaydi_yok_ve_rapor_yok_limited_data():
    r = ts.score_universe({"X": None, "Y": ts.company_inputs({"reports": []})}, {"X": "Elektrik", "Y": "Elektrik"})
    assert r["X"]["detay"]["limited_data"] and r["X"]["detay"]["sebep"] == "kap_kaydi_yok"
    assert r["Y"]["detay"]["sebep"] == "rapor_yok" and r["X"]["saglik"]["temel_analiz_skoru"] is None
    assert r["X"]["saglik"]["categories"] == {} and r["X"]["detay"]["veri_notu"] is None
    assert ts.company_inputs(None) is None


def test_veri_notu_a_b_c_olculebilir_kontroller():
    assert _inp("TUPRS")["veri_sorunlari"] == []                                  # A
    rec = _rec("TUPRS")
    assert ts.company_inputs(rec, 410.75, TODAY, 1926795598.0 / 3)["veri_sorunlari"] == ["tutarsizlik"]  # B: pay adedi
    # son rapor 2026/06: 20.12.2026'da 173 gun (sure icinde), 15.01.2027'de 199 gun -> gecikmis (B);
    # 2025 yillik raporu Nisan sonuna kadar hala guncel sayilir
    assert ts.company_inputs(rec, 410.75, date(2026, 12, 20), 1926795598.0)["veri_sorunlari"] == []
    assert ts.company_inputs(rec, 410.75, date(2027, 1, 15), 1926795598.0)["veri_sorunlari"] == ["son_rapor_gecikmis"]
    assert "yillik_rapor_eski" in ts.company_inputs(rec, 410.75, date(2027, 5, 2), 1926795598.0)["veri_sorunlari"]
    gap = copy.deepcopy(rec)
    gap["reports"] = [r for r in gap["reports"] if (r["fy"], r["period"]) != (2025, 3)]
    for r in gap["reports"]:
        if r["period"] == 4 and r["fy"] == 2025:
            r["items"]["cfo"] = None
    probs = ts.company_inputs(gap, 410.75, TODAY, 1926795598.0)["veri_sorunlari"]
    assert probs == ["ceyrek_eksik", "kalem_eksik"]                            # C
    d = ts.score_universe({"T": ts.company_inputs(gap, 410.75, TODAY, 1926795598.0)}, {"T": "K"})["T"]["detay"]
    assert d["veri_notu"] == "C"


def test_temettu_sureklilik_ve_verim():
    t = _inp("TUPRS")
    assert t["temettu_son12"] and t["temettu_onceki12"] and t["sureklilik"] == 100.0 and t["verim"] > 0
    th = _inp("THYAO")
    assert (th["temettu_son12"], th["temettu_onceki12"], th["sureklilik"], th["verim"]) == (False, True, 50.0, 0.0)
    rec = _rec("THYAO")
    rec["derived"]["temettu_odemeleri"] = []
    none = ts.company_inputs(rec, 288.5, TODAY, 1372283353.0)
    assert none["sureklilik"] == 0.0 and none["verim"] == 0.0
    d = ts.score_universe({"N": none}, {"N": "K"})["N"]["detay"]
    assert d["eksenler"]["temettu"]["puan"] == 0.0
    assert d["eksenler"]["temettu"]["cumle"] == "Son iki yılda nakit temettü ödemesi yok."


# ----------------------------------------------------------------------------- baglanti ve ciktilar

def test_financial_health_score_v2_dali_ve_bayrak_kapaliyken_ayni():
    pool = [{"ticker": "A%d" % i, "sector": "S", "roe": 10 + i, "profit_margin": 5 + i, "current_ratio": 1 + i / 10,
             "pe_ratio": 8 + i, "pb_ratio": 1 + i / 5} for i in range(6)]
    old = fhs.compute_health_score(dict(pool[0]), "S", pool)
    same = fhs.compute_health_score(dict(pool[0]), "S", pool)
    assert old == same and set(old["categories"]) <= set(fhs.CATEGORIES)
    assert "kategorisinde" in fhs.build_rationale(old["categories"], old["data_completeness"])
    t = _inp("TUPRS")
    peers = _peers(t, roe=[5.0, 10.0, 20.0, 25.0], fk=[8.0, 10.0, 14.0, 16.0], pd_dd=[0.6, 0.9, 1.1, 1.3])
    res = ts.score_universe(*_universe(("TUPRS", t), "Kimya", peers))["TUPRS"]
    h = fhs.compute_health_score(dict(pool[0], _temel_v2=res), "S", pool)
    assert list(h) == list(old) and h["temel_analiz_skoru"] == res["detay"]["temel"]
    assert set(h["categories"]) <= set(ts.AXES) and h["band"] == fhs._band(h["temel_analiz_skoru"])
    txt = fhs.build_rationale(h["categories"], h["data_completeness"], h["categories_na"])
    assert txt == ts.answer(h["categories"]) + "." and "kategorisinde" not in txt
    # BP formulu ayni yerden: v2 Temel %60 + teknik %40
    bp = fhs.compute_borsapusula_score(50, h["temel_analiz_skoru"])
    assert bp["borsapusula_skoru"] == round(h["temel_analiz_skoru"] * 0.6 + 50 * 0.4)


def test_cevap_betimleyici_ve_yasak_dil_yok():
    assert ts.answer({"kalite": 80, "buyume": 40, "bilanco": 60, "temettu": 55}) == "Kalite güçlü, büyüme zayıf"
    assert ts.answer({"kalite": 75, "bilanco": 72, "buyume": 60, "temettu": 60}) == "Kalite ve bilanço güçlü"
    assert ts.answer({"kalite": 60, "bilanco": 55, "buyume": 45, "temettu": 60}) == "Büyüme zayıf, diğerleri dengeli"
    assert ts.answer({"kalite": 60, "bilanco": 55, "buyume": 65, "temettu": 60}) == "Dengeli; belirgin zayıf alan yok"
    assert ts.answer({"degerleme": 10, "kalite": 60, "buyume": 60, "bilanco": 60}) == "Dengeli; belirgin zayıf alan yok"
    texts = []
    for t, b in (("TUPRS", "K1"), ("GARAN", "K2"), ("EKGYO", "K3"), ("ANSGR", "K4"), ("THYAO", "K5"), ("BIMAS", "K6")):
        d = ts.score_universe({t: _inp(t)}, {t: b})[t]["detay"]
        texts += [e["cumle"] or "" for e in d["eksenler"].values()] + [d["cevap"] or "", d["sablon_notu"] or ""]
    blob = " ".join(texts)
    assert blob and not any(w in blob for w in BANNED)
    assert "−%" in blob and "-%" not in blob                                   # eksi U+2212 (kanon §2.10)


def test_listeler_kurallari_ve_json():
    t = _inp("TUPRS")
    peers = _peers(t, roe=[1.0, 2.0, 3.0, 4.0], net_marj=[0.5, 1.0, 1.5, 2.0], fk=[20.0, 22.0, 24.0, 26.0],
                   pd_dd=[2.2, 2.4, 2.6, 2.8], gelir_deg=[-40.0, -35.0, -30.0, -25.0])
    d = ts.score_universe(*_universe(("TUPRS", t), "Kimya", peers))["TUPRS"]["detay"]
    assert d["degerleme"]["hukum"] == "ucuz"                        # F/K 11,7 / 22 ; PD/DD 1,74 / 2,4
    assert d["eksenler"]["kalite"]["puan"] >= 70
    # Kaliteli ve makul fiyatli + sektorune gore ucuz + istikrarli temettu; 2025 hasilat dustugu icin borcsuz buyuyen degil
    assert d["listeler"] == ["kaliteli_makul", "istikrarli_temettu", "sektorune_gore_ucuz"]
    low = dict(d, veri_tamligi=0.75)
    assert ts.list_membership(t, low, "Kimya") == []                 # tamlik <0,8: listeye girmez
    assert ts.list_membership(t, d, "Holding ve Yatırım")[0] != "kaliteli_makul"
    json.dumps(d, allow_nan=False)                                    # sonsuz/NaN yok (disk + API)
    peers_inf = _peers(t, nb_favok=[float("inf"), 0.5, 1.0, 2.0])
    dd = ts.score_universe(*_universe(("TUPRS", t), "Kimya", peers_inf))["P0"]["detay"]
    assert dd["eksenler"]["bilanco"]["girdiler"]["nb_favok"]["deger"] is None
    json.dumps(dd, allow_nan=False)


def test_web_yardimcilari_api_ortancasi_ve_tarama():
    t = _inp("TUPRS")
    peers = _peers(t, fk=[8.0, 10.0, 14.0, 16.0], pd_dd=[0.6, 0.9, 1.1, 1.3], roe=[5.0, 10.0, 20.0, 25.0])
    d = ts.score_universe(*_universe(("TUPRS", t), "Kimya", peers))["TUPRS"]["detay"]
    m = ts.api_medians(d)
    assert m["fk"] == {"deger": 11.73, "n": 5, "kapsam": "sektor"} and set(m) == {"fk", "pd_dd", "ozsermaye_karliligi"}
    v = ts.tarama_view(d)
    assert v == {"va": "p", "pe": 11.73, "pb": d["degerleme"]["pd_dd"], "roe": 14.8}
    assert ts.tarama_view(None) is None and ts.api_medians(None) is None
    lim = ts.score_universe({"X": None}, {"X": "K"})["X"]["detay"]
    assert ts.tarama_view(lim) is None and ts.api_medians(lim) is None     # kayitsiz hisse: eski (Yahoo) alanlar


def test_sayi_bicimi_kanon():
    assert ts._pc(14.8) == "%14,8" and ts._pc(-21.72, True) == "−%21,7" and ts._pc(2.1, True) == "+%2,1"
    assert ts._num(1234.5) == "1.234,50" and ts._num(-0.001) == "0,00"
    assert ts._money(57.0e9) == "57,0 Mrd ₺" and ts._money(409e9) == "409 Mrd ₺" and ts._money(1.06e12) == "1,06 T ₺"
    assert ts._money(912e6) == "912 Mn ₺"
    assert math.isclose(ts.valuation_points(0.8), 66.1)
