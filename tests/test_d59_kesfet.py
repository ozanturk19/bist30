"""D-59: Keşfet orta-uzun vade listeleri (kesfet.py) -- gercek KAP kayitlariyla.

Fixture'lar tests/fixtures/kap_temel_v2 (VPS data/kap_fin 25.09.2026 kopyasi, D-40a2 ile ayni).
Evren testleri ayni kaydi farkli fiyatlarla cogaltir (sektor ortancasi en az 5 sirket ister).
app.py'yi import etmez (py3.9 yerel kapida kosar).
"""
import copy
import gzip
import json
import os
import re
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import home_fields  # noqa: E402
import kap_temel_v2 as kt  # noqa: E402
import kesfet  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_temel_v2")
TODAY = date(2026, 9, 25)
KIMYA = "Kimya, Petrol ve Plastik"
BANKA = "Bankacılık"


def _rec(t):
    with gzip.open(os.path.join(FIX, t + ".json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


def _scaled_income(rec, k):
    """Net kari k katina cikarilmis kopya (ozsermaye karliligi ve marj yukselir, F/K duser)."""
    r = copy.deepcopy(rec)
    for rep in r["reports"]:
        it = (rep.get("items") or {}).get("net_income_parent")
        if it:
            for col in ("cur", "prev", "q_cur", "q_prev"):
                if it.get(col) is not None:
                    it[col] = it[col] * k
    return r


# ----------------------------------------------------------------------------- sabitler ve dil

def test_slug_cozumleme_ve_ic_anahtar():
    assert kesfet.resolve("kaliteli-makul") == "kaliteli_makul"
    assert kesfet.resolve("Borcsuz-Buyuyenler") == "borcsuz_buyuyen"
    assert kesfet.resolve("sektorune_gore_ucuz") == "sektorune_gore_ucuz"
    assert kesfet.resolve("bilinmeyen") is None and kesfet.resolve(None) is None
    assert [kesfet.SLUG[k] for k in kesfet.LISTS] == [
        "kaliteli-makul", "istikrarli-temettu", "borcsuz-buyuyenler", "sektorune-gore-ucuz"]


_YASAK = re.compile(r"\b(AL|SAT|LONG|SHORT)\b|hedef|stop|giriş fiyat|kâr al|Ücretsiz|Kısmi|veri tamlığı|"
                    r"Sınırlı veri|hazırlanıyor|bugün|dün\b|yarın|tavsiye|ortanca|ROE", re.I)


def test_kurallar_tek_cumle_soru_basliklari_ve_yasak_dil():
    for k in kesfet.LISTS:
        rule = kesfet.KURAL[k]
        assert rule.endswith(".") and rule.count(". ") == 0, k        # tek cumle
        assert not _YASAK.search(rule) and not _YASAK.search(kesfet.SORU[k]), k
        assert kesfet.SORU[k].startswith("Hangi şirketler") and kesfet.SORU[k].endswith("?")
    assert [r["kural"] for r in kesfet.rules()] == [kesfet.KURAL[k] for k in kesfet.LISTS]


# ----------------------------------------------------------------------------- tek sirket

def test_tuprs_gercek_kayittan_girdiler_taslakla_ayni():
    f = kesfet.company_facts(_rec("TUPRS"), 397.0, TODAY, 1926795598.0)
    # Taslak v3 (22.09 kapanisi 397,00): F/K 11,33 · PD/DD 1,68 · ozsermaye karliligi %14,8 · temettu %4,48
    assert (f["fk"], f["pd_dd"], f["roe"], f["verim"]) == (11.33, 1.68, 14.8, 4.48)
    assert f["sablon"] == "sanayi" and f["yil"] == 2025 and f["net_marj"] == 3.56
    assert f["gelir_deg"] == -21.72               # 2025 raporunun kendi karsilastirmasi
    assert round(f["net_borc"] / 1e9, 1) == -57.0  # net nakit 57,0 Mrd TL (Temel sekmesi bilanco paneli)
    assert f["temettu_son12"] and f["temettu_onceki12"] and not f["pay_uyumsuz"]


def test_kayit_yoksa_ya_da_raporsuzsa_girdi_yok():
    assert kesfet.company_facts(None, 10.0) is None
    assert kesfet.company_facts({"reports": [], "derived": {}}, 10.0) is None


def test_veri_tamligi_sablona_gore_banka_ve_sigorta_eksik_sayilmaz():
    """D-58: bankada net borc / cari oran / kar marji, sigortada bilanco ve marj sablonda yok."""
    prices = {"TUPRS": 397.0, "GARAN": 133.9, "ANSGR": 100.0, "EKGYO": 20.0, "BIMAS": 500.0}
    for t, p in prices.items():
        f = kesfet.company_facts(_rec(t), p, TODAY)
        assert kesfet.completeness(f, 20.0) == 1.0, t
    g = kesfet.company_facts(_rec("GARAN"), 133.9, TODAY)
    assert "net_borc" not in g and "cari_oran" not in g and g["gider_gelir"] == 43.51
    # Fiyat yok: F/K, PD/DD ve verim hesaplanamaz -> sanayide 10/13
    assert kesfet.completeness(kesfet.company_facts(_rec("TUPRS"), None, TODAY)) == 0.77
    # Pay adedi Yahoo'yla %20+ ayrisiyor: oran verilmez, F/K ve PD/DD eksik sayilir
    bad = kesfet.company_facts(_rec("TUPRS"), 397.0, TODAY, yahoo_shares=1e9)
    assert bad["pay_uyumsuz"] and bad["fk"] is None and kesfet.completeness(bad) == 0.85


# ----------------------------------------------------------------------------- kurallar (tek tek)

def _med(**kw):
    return {k: ({"deger": v, "n": 6, "kapsam": "sektor"} if v is not None else None) for k, v in kw.items()}


def test_kalite_kosulu_karli_ve_sektorun_ust_ucte_birinde():
    """Onayli taslak (temel-v2: "banka, sigorta, GYO ve holdingler haric") + D-40c (kalite >= 70)."""
    med = _med(ozsermaye_karliligi=-1.5, net_marj=-0.5, roe_ust=6.0, net_marj_ust=3.0)
    base = {"sablon": "sanayi", "roe": 8.0, "net_marj": 4.0}
    assert kesfet._quality(base, med, "Taş ve Toprak")
    assert not kesfet._quality(dict(base, roe=5.0), med)             # ortancanin ustunde, ust ucte birde degil
    assert not kesfet._quality(dict(base, net_marj=2.9), med)
    assert not kesfet._quality(dict(base, roe=6.0), med)             # esik esitligi ust ucte bire sayilmaz
    assert not kesfet._quality(dict(base, roe=-1.0), _med(roe_ust=-2.0, net_marj_ust=3.0))   # zararda
    assert not kesfet._quality(base, _med(roe_ust=6.0, net_marj_ust=None))                    # esik yok
    # Holding ve gayrimenkul kovasi, GYO / banka / sigorta sablonu girmez (marj degerleme kazanciyla sisiyor)
    assert not kesfet._quality(base, med, "Holding ve Yatırım")
    assert not kesfet._quality(dict(base, net_marj=941.0), med, "Gayrimenkul")
    for tpl in ("gyo", "banka", "sigorta"):
        assert not kesfet._quality(dict(base, sablon=tpl, gider_gelir=20.0), med), tpl


def test_sektor_esigi_ucte_bir_ve_havuz():
    """roe_ust / net_marj_ust: sektor dagiliminin 2/3 noktasi (en az 5 sirket; 'Diger' kovasinda yok)."""
    facts = {"A%d" % i: {"sablon": "sanayi", "fiyat_var": True, "fk": 5.0, "pd_dd": 1.0,
                         "roe": float(i), "net_marj": float(10 * i)} for i in range(1, 7)}
    facts["Z"] = dict(facts["A1"], fiyat_var=False, roe=99.0)   # fiyatsiz: ozsermaye havuzunda yok
    med = kesfet.sector_medians(facts, lambda t: "X")["X"]
    assert med["roe_ust"] == {"deger": 4.33, "n": 6, "kapsam": "sektor"}
    assert med["net_marj_ust"]["deger"] == 40.0 and med["net_marj_ust"]["n"] == 7     # marj: tum sirketler
    assert med["ozsermaye_karliligi"]["deger"] == 3.5 and "gider_gelir" not in med
    few = kesfet.sector_medians({t: facts[t] for t in ("A1", "A2", "A3", "A4")}, lambda t: "X")["X"]
    assert few["roe_ust"] is None and few["net_marj_ust"] is None
    assert kesfet.sector_medians(facts, lambda t: "Diğer")["Diğer"]["roe_ust"] is None


def test_onbellege_yazma_kapisi_girdiler_tam():
    """app._kesfet_lists: web worker acilisinda _cache dolu, skor/pay onbellegi bos -> yazilmaz."""
    st = [{"ticker": "AKSA"}]
    assert kesfet.ready(st, {"AKSA": {"borsapusula_skoru": 52}}, {"AKSA": 3.9e9})
    assert not kesfet.ready(st, {}, {"AKSA": 3.9e9})                 # skor kayitlari yuklenmedi
    assert not kesfet.ready(st, {"AKSA": {}}, {"AKSA": 3.9e9})
    assert not kesfet.ready(st, {"AKSA": {"borsapusula_skoru": 52}}, {})          # pay adetleri yok
    assert not kesfet.ready(st, {"AKSA": {"borsapusula_skoru": 52}}, {"AKSA": None})
    assert not kesfet.ready([], {"AKSA": {"borsapusula_skoru": 52}}, {"AKSA": 3.9e9})


def test_uyelikler_dort_liste_kurali():
    med = _med(ozsermaye_karliligi=5.0, net_marj=2.0, fk=10.0, pd_dd=1.0, roe_ust=8.0, net_marj_ust=5.0)
    f = {"sablon": "sanayi", "roe": 9.0, "net_marj": 6.0, "fk": 7.0, "pd_dd": 0.7,
         "temettu_son12": True, "temettu_onceki12": True, "verim": 3.2,
         "net_borc": -1e9, "gelir_deg": 12.0, "yillik_kar": 5.0}
    assert kesfet.memberships(f, med, "ucuz") == list(kesfet.LISTS)
    assert kesfet.memberships(f, med, "pahali") == ["istikrarli_temettu", "borcsuz_buyuyen"]
    assert "kaliteli_makul" not in kesfet.memberships(f, med, "ucuz", "Holding ve Yatırım")
    # ucuz hukmu ama PD/DD ortancanin ustunde: "ikisi de altinda" kurali tutmaz
    assert "sektorune_gore_ucuz" not in kesfet.memberships(dict(f, pd_dd=1.1), med, "ucuz")
    # temettu: iki donemin ikisi de, verim > 0
    assert "istikrarli_temettu" not in kesfet.memberships(dict(f, temettu_onceki12=False), med, "makul")
    assert "istikrarli_temettu" not in kesfet.memberships(dict(f, verim=0.0), med, "makul")
    # borcsuz buyuyen: net nakit + satis artisi + yillik kar; banka sablonunda tanimsiz
    for bad in (dict(f, net_borc=1.0), dict(f, gelir_deg=-0.1), dict(f, yillik_kar=-3.0),
                dict(f, sablon="banka")):
        assert "borcsuz_buyuyen" not in kesfet.memberships(bad, med, "makul")


def test_neden_cumleleri_kanon_sayi_bicimi_betim():
    med = _med(ozsermaye_karliligi=-1.5, net_marj=-0.5, gider_gelir=50.71, fk=14.87, pd_dd=2.07)
    f = {"sablon": "sanayi", "roe": 18.21, "net_marj": 23.2, "verim": 13.704, "yil": 2025, "gelir_deg": 7.3,
         "net_borc": -2.31e9, "fk": 2.11, "pd_dd": 0.74}
    assert kesfet.reason("kaliteli_makul", f, med) == \
        "Özsermaye kârlılığı %18,2 (sektör −%1,5), net kâr marjı %23,2 (sektör −%0,5)"
    assert kesfet.reason("istikrarli_temettu", f, med) == \
        "Son 12 ayda temettü verimi %13,7; önceki 12 ayda da ödeme yaptı"
    assert kesfet.reason("borcsuz_buyuyen", f, med) == "2025 yılında satışlar +%7,3, net nakit 2,3 Mrd ₺"
    assert kesfet.reason("borcsuz_buyuyen", dict(f, net_borc=-213.4e9), med).endswith("net nakit 213 Mrd ₺")
    assert kesfet.reason("borcsuz_buyuyen", dict(f, net_borc=-47.2e6), med).endswith("net nakit 47 Mn ₺")
    assert kesfet.reason("sektorune_gore_ucuz", f, med) == "F/K 2,11 (sektör 14,87), PD/DD 0,74 (sektör 2,07)"


# ----------------------------------------------------------------------------- evren

def _universe():
    """7 rafineri (ayni kayit, farkli fiyat; KIMYA kovasi) + 1 donuk satir (K0) + GARAN + ANSGR.
    K3'un kari 1,5 kat: ozsermaye karliligi ve marj sektor ortancasinin ustunde."""
    tup = _rec("TUPRS")
    prices = {"K0": 100.0, "K1": 200.0, "K2": 240.0, "K3": 330.0, "K4": 397.0, "K5": 450.0, "K6": 600.0,
              "K7": 700.0}
    recs = {t: tup for t in prices}
    recs["K3"] = _scaled_income(tup, 1.5)
    recs["GARAN"], recs["ANSGR"] = _rec("GARAN"), _rec("ANSGR")
    prices.update({"GARAN": 133.9, "ANSGR": 100.0})
    sig = {"K1": "AL", "K2": "SAT", "K3": "BEKLE"}
    stocks = [{"ticker": t, "price": p, "signal": sig.get(t, "BEKLE"), "bar_date": "25.09.2026",
               "name": t + " AŞ"} for t, p in prices.items()]
    stocks[0].update(stale_reason="kapanis_gelmedi", bar_date="24.09.2026")      # K0 donuk
    bucket = {t: KIMYA for t in prices if t.startswith("K")}
    bucket.update({"GARAN": BANKA, "ANSGR": "Sigorta"})
    entries = {t: {"borsapusula_skoru": 40 + i} for i, t in enumerate(prices)}
    return stocks, entries, recs, bucket


def test_evren_listeleri_ucuzluk_temettu_kalite_sira_ve_donuk_satir():
    stocks, entries, recs, bucket = _universe()
    res = kesfet.build(stocks, entries, recs, {}, bucket, {"K1": "Birinci Rafineri"}, TODAY)
    ls = res["listeler"]
    assert res["tarih"] == "2026-09-25"
    # Sektorune gore ucuz: F/K ve PD/DD ikisi de ortancanin altinda ve hukum ucuz; en ucuzdan
    ucuz = [r["ticker"] for r in ls["sektorune_gore_ucuz"]]
    assert ucuz == ["K1", "K2", "K3"]
    assert all(r["degerleme"] == "ucuz" for r in ls["sektorune_gore_ucuz"])
    # Donuk K0 listede yok ama ortancaya girdi (hisse sayfasindaki havuzla ayni): 8 sirketin ortancasi
    assert all("K0" not in [r["ticker"] for r in rows] for rows in ls.values())
    k1 = ls["sektorune_gore_ucuz"][0]
    med_fk = kt.sector_medians({t: kt.kap_metrics(recs[t], s["price"]) for t, s in
                                ((x["ticker"], x) for x in stocks) if t.startswith("K")},
                               lambda t: bucket.get(t), KIMYA)["fk"]
    assert med_fk["n"] == 8 and ("(sektör %s)" % kesfet._fmt(med_fk["deger"], 2)) in k1["neden"]
    # Satir bicimi: ad, kova, BP, trend, degerleme, neden
    assert {k: k1[k] for k in ("ticker", "name", "sector", "bp", "trend", "trend_kod", "degerleme", "sablon")} == {
        "ticker": "K1", "name": "Birinci Rafineri", "sector": KIMYA, "bp": 41, "trend": "Güçlü Trend",
        "trend_kod": "g", "degerleme": "ucuz", "sablon": "sanayi"}
    # Istikrarli temettu: hepsi (sigorta ve banka dahil) son 12 ay verimine gore (dusuk fiyat yuksek verim)
    tem = [r["ticker"] for r in ls["istikrarli_temettu"]]
    assert tem[:3] == ["K1", "K2", "K3"] and "GARAN" in tem and "ANSGR" in tem and "K0" not in tem
    verims = [float(re.search(r"%([\d,]+)", r["neden"]).group(1).replace(",", ".")) for r in ls["istikrarli_temettu"]]
    assert verims == sorted(verims, reverse=True)
    # Kaliteli ve makul: yalniz K3 (kar 1,5 kat -> ozsermaye karliligi ve marj sektorun ust ucte birinde;
    # digerleri esikte -- esitlik sayilmaz). GARAN banka: kalite listesine girmez.
    assert [r["ticker"] for r in ls["kaliteli_makul"]] == ["K3"]
    assert ls["kaliteli_makul"][0]["neden"].startswith("Özsermaye kârlılığı %22,2 (sektör %14,8)")
    # Borcsuz buyuyen: rafinerinin 2025 satislari geriledi -> yok
    assert ls["borcsuz_buyuyen"] == []


def test_v2_kaydi_varsa_degerleme_hukmu_ondan_tek_kaynak():
    stocks, entries, recs, bucket = _universe()
    entries["K1"] = {"borsapusula_skoru": 77, "temel_v2": {"degerleme": {"hukum": "pahali"}, "veri_tamligi": 1.0}}
    res = kesfet.build(stocks, entries, recs, {}, bucket, {}, TODAY)
    assert "K1" not in [r["ticker"] for r in res["listeler"]["sektorune_gore_ucuz"]]
    k1 = next(r for r in res["listeler"]["istikrarli_temettu"] if r["ticker"] == "K1")
    assert k1["degerleme"] == "pahali" and k1["bp"] == 77


def test_degerleme_hukmu_hisse_sayfasiyla_ayni():
    """Liste rozeti = /fundamentals zinciri (kap_temel_v2.extend + home_fields.valuation)."""
    stocks, entries, recs, bucket = _universe()
    prices = {s["ticker"]: s["price"] for s in stocks}
    km = {t: kt.kap_metrics(recs[t], prices[t]) for t in prices}
    facts = {t: kesfet.company_facts(recs[t], prices[t], TODAY) for t in prices}
    meds = kesfet.sector_medians(facts, bucket)
    for t in prices:
        hisse = home_fields.valuation(
            entries[t], kt.extend({"kap": {"x": 1}}, recs[t], prices[t], TODAY,
                                  kt.sector_medians(km, lambda x: bucket.get(x), bucket[t])))
        assert kesfet.verdict(entries[t], facts[t], meds.get(bucket[t])) == hisse, t


def test_bozuk_kayit_listeyi_dusurmez_ve_dusuk_tamlik_girmez():
    stocks, entries, recs, bucket = _universe()
    recs["K1"] = {"reports": [{"bozuk": True}], "derived": {}}
    res = kesfet.build(stocks, entries, recs, {}, bucket, {}, TODAY)
    assert "K1" not in [r["ticker"] for rows in res["listeler"].values() for r in rows]
    assert res["listeler"]["istikrarli_temettu"]
    # pay adedi uyumsuz: F/K ve PD/DD yok -> tamlik 0,85 (giriyor) ama ucuzluk listesinde yok
    res2 = kesfet.build(stocks, entries, _universe()[2], {"K2": 1e9}, bucket, {}, TODAY)
    assert "K2" not in [r["ticker"] for r in res2["listeler"]["sektorune_gore_ucuz"]]
    assert "K2" in [r["ticker"] for r in res2["listeler"]["istikrarli_temettu"]]


def test_view_ozet_ve_varsayilan():
    stocks, entries, recs, bucket = _universe()
    res = kesfet.build(stocks, entries, recs, {}, bucket, {}, TODAY)
    v = kesfet.view(res, "sektorune_gore_ucuz")
    assert v["slug"] == "sektorune-gore-ucuz" and v["soru"] == "Hangi şirketler sektörüne göre ucuz?"
    assert v["sayi"] == len(v["satirlar"]) == 3 and v["tarih"] == "2026-09-25"
    assert [x["aktif"] for x in v["listeler"]] == [False, False, False, True]
    assert [x["sayi"] for x in v["listeler"]] == [len(res["listeler"][k]) for k in kesfet.LISTS]
    assert kesfet.view(res, "yok")["anahtar"] == kesfet.VARSAYILAN
    empty = kesfet.view(kesfet.build([], {}, {}, today=TODAY), "kaliteli_makul")
    assert empty["satirlar"] == [] and empty["tarih"] is None and empty["sayi"] == 0


# ----------------------------------------------------------------------------- D-40c paritesi

def test_veri_tamligi_d40c_ile_ayni():
    """D-40c (temel_skor_v2) birlestirilince kosar: liste kapisi = Temel v2 veri_tamligi."""
    v2 = pytest.importorskip("temel_skor_v2")
    stocks, entries, recs, bucket = _universe()
    recs.update({"BIMAS": _rec("BIMAS"), "EKGYO": _rec("EKGYO"), "THYAO": _rec("THYAO")})
    prices = {s["ticker"]: s["price"] for s in stocks}
    prices.update({"BIMAS": 500.0, "EKGYO": 20.0, "THYAO": 300.0})
    bucket.update({"BIMAS": "Ticaret", "EKGYO": "Gayrimenkul", "THYAO": "Ulaştırma"})
    inputs = {t: v2.company_inputs(recs[t], prices[t], TODAY) for t in prices}
    scored = v2.score_universe(inputs, bucket)
    facts = {t: kesfet.company_facts(recs[t], prices[t], TODAY) for t in prices}
    meds = kesfet.sector_medians(facts, bucket)
    for t in prices:
        assert kesfet.completeness(facts[t], kesfet._mv(meds.get(bucket[t]), "ozsermaye_karliligi")) == \
            scored[t]["detay"]["veri_tamligi"], t
