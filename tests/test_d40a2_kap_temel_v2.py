"""D-40a2: Temel v2 veri uclari (kap_temel_v2) -- gercek KAP kayitlariyla.

Fixture'lar VPS data/kap_fin/<T>.json (25.09.2026 uretimi) kayitlarinin kucultulmus kopyasi
(tests/fixtures/kap_temel_v2, yalniz rapor kalemleri + derived; kaynak izi yok).
Beklenen degerler onayli taslak v3 (plans/mockups/temel-v2.html, 22.09 kapanisi) ile ayni.
app.py'yi import etmez (py3.9 yerel kapida kosar).
"""
import gzip
import json
import os
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_financials as kf  # noqa: E402
import kap_temel_v2 as kt  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_temel_v2")
TODAY = date(2026, 9, 25)


def _rec(t):
    with gzip.open(os.path.join(FIX, t + ".json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


def _items(sc):
    return {i["k"]: i for i in sc["maddeler"]}


def test_sablonlar_bayrak_ve_sektorden():
    assert [kt.template_of(_rec(t)) for t in ("TUPRS", "THYAO", "GARAN", "BIMAS", "ANSGR", "EKGYO")] == \
        ["sanayi", "sanayi", "banka", "sanayi", "sigorta", "gyo"]


def test_tuprs_o22_son12ay_fk_pddd_ozsermaye_taslakla_ayni():
    rec = _rec("TUPRS")
    ttm = kt.ttm_net_income(rec)
    # 2025 yillik ana ortaklik kari 29.523.183 bin TL + 2026 ilk yari farki (ayni ara donem raporu)
    assert ttm["yontem"] == "son12ay" and (ttm["yillik"], ttm["ara"]) == ("2025/12", "2026/06")
    assert ttm["tutar"] == 29523183000.0 + ttm["fark"] and round(ttm["tutar"] / 1e9, 2) == 67.5
    now = kt.valuation_now(rec, "sanayi", 397.0, yahoo_shares=1926795598.0)
    # Taslak v3 (22.09 kapanisi 397,00): F/K 11,3 · PD/DD 1,68 · ozsermaye karliligi %14,8
    assert (now["fk"], now["pd_dd"], now["ozsermaye_karliligi"]) == (11.33, 1.68, 14.8)
    assert now["pay_adedi"] == 1926796000.0 and now["ozkaynak_donem"] == "2026/06"
    # Son yillik karla (O22=A) F/K 25,9 olurdu -- son 12 ay kari bundan farkli
    assert round(now["piyasa_degeri"] / 29523183000.0, 1) == 25.9


def test_tuprs_marjlar_yillar_boyu_ve_ara_donem_kesikli_nokta():
    rec = _rec("TUPRS")
    m = kt.ratios_by_year(rec, "sanayi")
    assert [m[y]["brut"] for y in ("2021", "2022", "2023", "2024", "2025")] == [10.23, 13.03, 15.98, 8.39, 9.78]
    assert [m[y]["net"] for y in ("2021", "2022", "2023", "2024", "2025")] == [2.2, 8.52, 7.8, 2.26, 3.56]
    assert m["2025"]["favok"] == 6.78 and m["2025"]["ozsermaye_karliligi"] == 8.05
    ara = kt.interim_ratios(rec, "sanayi")
    assert (ara["donem"], ara["etiket"], ara["kisa"], ara["brut"], ara["net"]) == \
        ("2026/06", "2026 ilk yarı", "26 İY", 12.69, 7.52)


def test_degisim_grafigi_yalniz_ayni_esas_tms29_2023_sonrasi():
    ys = kt.yearly_series(_rec("TUPRS"), "sanayi")
    assert [r["yil"] for r in ys["seri"]] == [2023, 2024, 2025] and ys["dusen_yillar"] == [2021, 2022]
    d = {r["yil"]: r["degisim"] for r in ys["seri"]}
    assert (d[2024]["revenue"], d[2025]["revenue"]) == (-18.24, -21.72)   # D-40a0 ile ayni
    assert (d[2023]["fcf"], d[2024]["fcf"], d[2025]["fcf"]) == (-5.59, -79.61, 8.03)
    # Banka nominal: tum yillar
    g = kt.yearly_series(_rec("GARAN"), "banka")
    assert [r["yil"] for r in g["seri"]] == [2021, 2022, 2023, 2024, 2025] and g["dusen_yillar"] == []


def test_ceyreklik_seri_3_aylik_sutundan_q4_yok():
    q = kt.quarterly_series(_rec("TUPRS"), "sanayi")
    assert [x["ceyrek"] for x in q] == ["25 Ç1", "25 Ç2", "25 Ç3", "26 Ç1", "26 Ç2"]
    by = {x["ceyrek"]: x["degisim"] for x in q}
    assert (by["25 Ç2"]["revenue"], by["25 Ç3"]["revenue"], by["26 Ç1"]["revenue"], by["26 Ç2"]["revenue"]) == \
        (-28.88, -15.63, 24.41, 59.69)
    gq = {x["ceyrek"]: x["degisim"] for x in kt.quarterly_series(_rec("GARAN"), "banka")}
    assert (gq["26 Ç2"]["net_interest_income"], gq["26 Ç2"]["net_fees"], gq["26 Ç2"]["net_income_parent"]) == \
        (62.45, 37.05, 8.77)


def test_garan_banka_oranlari_ve_5_madde():
    rec = _rec("GARAN")
    r = kt.ratios_by_year(rec, "banka")["2025"]
    assert (r["ozsermaye_karliligi"], r["gider_gelir"], r["kredi_mevduat"]) == (28.38, 43.51, 86.21)
    assert (r["ozkaynak_degisim"], r["varlik_degisim"]) == (34.65, 51.46)
    assert r["net_faiz_marji"] is not None and 4 < r["net_faiz_marji"] < 6
    now = kt.valuation_now(rec, "banka", 133.9, yahoo_shares=4200000000.0)
    # Taslak: F/K 4,67 · PD/DD 1,16 · ozsermaye karliligi son 12 ay %24,7 (2026/06 raporu 1.000.000 TL birimli)
    assert (now["fk"], now["pd_dd"], now["ozsermaye_karliligi"]) == (4.67, 1.16, 24.72)
    ck = kt.checks(rec, "banka", roe=28.1, roe_median=23.3)
    it = _items(ck)
    assert (ck["puan"], ck["toplam"]) == (3, 5)
    assert it["kredi_mevduat_100_alti"]["gecti"] and not it["gider_gelir_40_alti"]["gecti"]
    assert not it["ozkaynak_varliktan_hizli"]["gecti"]
    # Ortanca yoksa o madde puana girmez (uydurma esik yok)
    ck2 = kt.checks(rec, "banka")
    assert (ck2["puan"], ck2["toplam"], ck2["eksik"]) == (2, 4, ["ozsermaye_karliligi_ortanca_ustu"])


def test_piotroski_9_madde_tek_yillik_rapordan():
    ck = kt.checks(_rec("TUPRS"), "sanayi")
    it = _items(ck)
    assert (ck["yontem"], ck["yil"], ck["puan"], ck["toplam"]) == ("piotroski", 2025, 7, 9)
    assert (it["aktif_karliligi_artti"]["cur"], it["aktif_karliligi_artti"]["prev"]) == (5.05, 4.19)
    assert not it["uv_borc_orani_dustu"]["gecti"] and not it["aktif_devir_artti"]["gecti"]
    assert (it["cari_oran_artti"]["cur"], it["cari_oran_artti"]["prev"]) == (1.4, 1.25)
    assert kt.checks(_rec("ANSGR"), "sigorta") is None   # sigortada hasilat eslenmedi


def test_bilanco_net_nakit_ve_thyao_nb_favok():
    b = kt.balance(_rec("TUPRS"), "sanayi")
    assert round(b["cur"]["net_borc"] / 1e9, 1) == -57.0 and round(b["prev"]["net_borc"] / 1e9, 1) == -71.4
    assert (b["cur"]["cari_oran"], b["prev"]["cari_oran"]) == (1.4, 1.25)
    t = kt.balance(_rec("THYAO"), "sanayi")
    assert t["cur"]["net_borc_favok"] == 2.68       # D-40a0 kabul degeri (CPO 24.09 tanimi)
    g = kt.balance(_rec("GARAN"), "banka")
    assert (g["cur"]["kredi_mevduat"], g["prev"]["kredi_mevduat"]) == (86.21, 82.45)


def test_thyao_usd_raporlayan_tl_ile_fk_hesaplanir():
    rec = _rec("THYAO")
    assert rec["flags"]["yabanci_para"] == "USD" and rec["derived"]["basis"] == "yabanci_para"
    now = kt.valuation_now(rec, "sanayi", 288.5, yahoo_shares=1372283353.0)
    assert now["fk"] is not None and 3 < now["fk"] < 5 and not now["pay_uyumsuz"]
    ys = kt.yearly_series(rec, "sanayi")      # tum raporlar ayni esas (TL'ye cevrilmis)
    assert ys["dusen_yillar"] == [] and len(ys["seri"]) == 5


def test_pay_adedi_uyumsuzsa_oran_ve_bant_verilmez():
    rec = _rec("BIMAS")
    now = kt.valuation_now(rec, "sanayi", 422.75, yahoo_shares=1200000000.0 / 3)
    assert now["pay_uyumsuz"] and now["fk"] is None and now["pd_dd"] is None
    v2 = kt.build_v2(rec, price=422.75, today=TODAY, yahoo_shares=1200000000.0 / 3)
    assert v2["degerleme_bandi_v2"] == []
    ok = kt.build_v2(rec, price=422.75, today=TODAY, yahoo_shares=1185780000.0)
    assert ok["degerleme_simdi"]["fk"] and len(ok["degerleme_bandi_v2"]) == 5


def test_sigorta_sablonu_ozkaynak_toplamdan_pd_dd_bos_kalmaz():
    rec = _rec("ANSGR")
    band = kt.valuation_band(rec, "sigorta")
    assert all(b["pd_dd"] for b in band) and all(b["fk"] for b in band)
    r = kt.ratios_by_year(rec, "sigorta")["2025"]
    assert r["ozsermaye_karliligi"] == 45.31 and "brut" not in r
    now = kt.valuation_now(rec, "sigorta", 25.12, yahoo_shares=2000000000.0)
    assert now["pd_dd"] and now["fk"]


def test_gyo_zararda_fk_yok_pd_dd_var():
    now = kt.valuation_now(_rec("EKGYO"), "gyo", 19.58, yahoo_shares=3661120138.0)
    assert now["son12ay_kar"] < 0 and now["fk"] is None and now["pd_dd"] == 0.49


def test_extend_kayit_yoksa_hazirlaniyor_varsa_kaynaksiz_v2():
    yahoo = {"pe_ratio": 11.7, "roe": 17.6, "shares": 1926795598.0, "market_cap": {"value": 7.9e11, "currency": "TRY"}}
    med = {"fk": {"deger": 13.8, "n": 12, "kapsam": "sektor"}, "pd_dd": None, "ozsermaye_karliligi": None}
    none = kt.extend(kf.apply_to_fundamentals(dict(yahoo), None, 410.75, TODAY), None, 410.75, TODAY, med)
    assert none["kap_durum"] == "hazirlaniyor" and "kap" not in none and none["pe_ratio"] == 11.7
    assert none["sektor_ortanca"]["fk"]["deger"] == 13.8
    rec = _rec("TUPRS")
    out = kt.extend(kf.apply_to_fundamentals(dict(yahoo), rec, 410.75, TODAY), rec, 410.75, TODAY, med)
    k = out["kap"]
    assert out["kap_durum"] == "var" and k["sablon"] == "sanayi" and k["son_rapor_etiket"] == "2026 ilk yarı"
    assert k["degerleme_simdi"]["fk"] == round(410.75 * 1926796000.0 / k["son12ay"]["tutar"], 2)
    assert '"kaynak"' not in json.dumps(out)       # ic dogrulama izi API'ye cikmaz, JSON'a cevrilebilir
    assert [t["yil"] for t in k["temettu_yillar"]] == [2025, 2026]
    assert kt.extend({}, rec) == {}


def test_sektor_ortancasi_d51_kurali():
    fund = {"A": {"pe_ratio": 10, "pb_ratio": 1.0, "roe": 20}, "B": {"pe_ratio": 12, "pb_ratio": 2.0, "roe": 10},
            "C": {"pe_ratio": 14, "pb_ratio": -1, "roe": -5}, "D": {"pe_ratio": 40, "pb_ratio": 3.0, "roe": 30},
            "E": {"pe_ratio": None, "pb_ratio": 5.0, "roe": None}}
    sec = {"A": "Banka", "B": "Banka", "C": "Banka", "D": "Enerji", "E": "Diğer"}.get
    m = kt.sector_medians(fund, sec, "Banka")
    assert m["fk"] == {"deger": 12, "n": 3, "kapsam": "sektor"}
    assert m["pd_dd"] == {"deger": 2.5, "n": 4, "kapsam": "bist"}        # bankada pozitif PD/DD 2 (<3) -> BIST
    assert m["ozsermaye_karliligi"]["kapsam"] == "sektor" and m["ozsermaye_karliligi"]["deger"] == 10
    assert kt.sector_medians(fund, sec, "Diğer")["fk"]["kapsam"] == "bist"


@pytest.mark.parametrize("t", ["TUPRS", "THYAO", "GARAN", "BIMAS", "ANSGR", "EKGYO"])
def test_bos_panel_yok_her_sablonda_temel_alanlar_dolu(t):
    rec = _rec(t)
    v2 = kt.build_v2(rec, price=100.0, today=TODAY)
    assert v2["yillik_seri"] and v2["ceyrek_seri"] and v2["tutarlar"] and v2["bilanco"]
    assert v2["oranlar"] and v2["son12ay"] and v2["degerleme_simdi"]["ozkaynak"]
    assert v2["temettu_yillar"]
