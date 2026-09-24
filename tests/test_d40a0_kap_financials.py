"""D-40a0: temel veri KAP finansal raporlarindan ("aciklanan veri" ilkesi).

Fixture'lar gercek KAP sayfalarindan (24.09.2026 cekildi), yalniz eslenen satirlar
birakilarak kucultuldu (tests/fixtures/kap_fin). app.py'yi import etmez (py3.9 yerel kapida kosar).
"""
import gzip
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_financials as kf  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_fin")
TODAY = date(2026, 9, 24)


def _rep(idx, tk, fy, period=4, sector=None):
    with gzip.open(os.path.join(FIX, "fr_%d.html.gz" % idx), "rt", encoding="utf-8") as f:
        return kf.build_report(f.read(), {"idx": idx, "fy": fy, "period": period, "publish": None}, tk, sector)


def _div(idx, tk):
    with gzip.open(os.path.join(FIX, "kpd_%d.txt.gz" % idx), "rt", encoding="utf-8") as f:
        return kf.parse_dividend(f.read(), tk, {"idx": idx, "publish": None})


def _closes(tk):
    with open(os.path.join(FIX, "yil_sonu_kapanis.json"), encoding="utf-8") as f:
        raw = json.load(f)
    return {y: {"date": v["date"], "close": v["closes"][tk]} for y, v in raw.items()}


def test_tborg_2024_ciro_degisimi_sirketin_kendi_raporundan():
    r = _rep(1401749, "TBORG", 2024)
    ch = kf.yearly_change(r)["revenue"]
    # Yahoo'nun naif farki +%59,4 (farkli raporlarin tutarlari); raporun kendi karsilastirmasi +%21,8
    assert (ch["cur"], ch["prev"]) == (30148500.0, 24751075.0)
    assert ch["pct"] == 21.81
    assert ch["kaynak"] == {"rapor": 1401749, "donem": "2024/12", "birim": "1.000 TL"}
    assert r["basis"] == "tms29" and r["mult"] == 1000 and r["currency"] == "TL"


def test_tuprs_bimas_froto_yillik_degisim_rapor_karsilastirmasiyla_birebir():
    t24, t25 = _rep(1393446, "TUPRS", 2024), _rep(1554106, "TUPRS", 2025)
    assert kf.yearly_change(t24)["revenue"]["pct"] == -18.24          # 810.385.588 / 991.202.993
    assert kf.yearly_change(t25)["revenue"]["pct"] == -21.72          # 830.356.131 / 1.060.729.904
    # TMS 29: ayni yil iki raporda iki farkli tutarla yer alir -> seri birlestirilmez
    assert t24["items"]["revenue"]["cur"] == 810385588.0
    assert t25["items"]["revenue"]["prev"] == 1060729904.0
    b, f = _rep(1570150, "BIMAS", 2025), _rep(1555145, "FROTO", 2025)
    assert (b["items"]["revenue"]["cur"], b["items"]["revenue"]["prev"]) == (721062506.0, 680072863.0)
    assert kf.yearly_change(b)["revenue"]["pct"] == 6.03
    assert (f["items"]["revenue"]["cur"], f["items"]["revenue"]["prev"]) == (830827933.0, 778801036.0)
    assert kf.yearly_change(f)["revenue"]["pct"] == 6.68
    assert {t24["basis"], t25["basis"], b["basis"], f["basis"]} == {"tms29"}


def test_garan_banka_toplam_sutunu_ve_bayrak():
    g = _rep(1552588, "GARAN", 2025, sector="BANKALAR")
    assert g["format"] == "banka" and g["basis"] == "banka"
    yc = kf.yearly_change(g)
    assert yc["net_interest_income"]["pct"] == 62.45
    assert yc["net_income_parent"]["pct"] == 20.36
    # 6 sutunlu bilancoda TP/YP degil "Toplam": kredi/mevduat %86,21
    assert round(g["items"]["loans"]["cur"] / g["items"]["deposits"]["cur"] * 100, 2) == 86.21
    rec = kf.build_record("GARAN", [g], sector="BANKALAR")
    assert rec["flags"] == {"banka": True, "sigorta": False, "yabanci_para": None}
    assert rec["derived"]["net_borc"] is None       # bankada net borc/FAVOK anlamsiz


def test_thyao_net_borc_kiralamalar_dahil_ve_usd_bayragi():
    t = _rep(1565996, "THYAO", 2025, sector="ULAŞTIRMA VE DEPOLAMA")
    nd = kf.net_debt(t)
    # Kiralama borclari (86.152 + 552.824) borclanma toplamlarinin alt kiriliminda
    assert nd["borclanma"] == 70069.0 + 92367.0 + 601817.0
    assert nd["favok"] == 90129.0 + 94682.0
    assert nd["net_borc"] == 764253.0 - 86035.0 - 182732.0
    # Aciklanan veriyle 2,68. Kalemin "~1,78" degeri Yahoo FAVOK'undan (rapordaki esas
    # faaliyet kari + amortisman degil); Yahoo'nun kiralamasiz 0,14'u de degil.
    assert nd["net_borc_favok"] == 2.68
    assert t["basis"] == "yabanci_para"
    rec = kf.build_record("THYAO", [t])
    assert rec["flags"]["yabanci_para"] == "USD" and rec["flags"]["banka"] is False


def test_thyao_son_12_ayda_temettu_odemesi_yok():
    divs = [_div(1440796, "THYAO"), _div(1590365, "THYAO")]
    assert divs[1]["odeme_sekli"] == "Ödenmeyecek" and divs[1]["taksitler"] == []
    pays = kf.dividend_payments(divs)
    assert [p["odeme"] for p in pays] == ["2025-06-18", "2025-09-04"]
    ttm = kf.dividend_ttm(pays, TODAY)
    assert ttm["odeme_var"] is False and ttm["brut_toplam"] == 0
    assert ttm["son_odeme"] == {"odeme": "2025-09-04", "brut": 3.4420289}


def test_tuprs_temettu_odenen_girer_duyurulan_girmez():
    pays = kf.dividend_payments([_div(1570793, "TUPRS")])
    ttm = kf.dividend_ttm(pays, TODAY)
    assert ttm["odemeler"] == [{"odeme": "2026-03-18", "brut": 10.3799282}]
    assert ttm["brut_toplam"] == 10.3799282
    assert ttm["duyurulan"] == [{"odeme": "2026-10-02", "brut": 6.7469533}]


def test_ceyreklik_degisim_3_aylik_sutundan():
    r = _rep(1643238, "THYAO", 2026, period=2)
    q = kf.quarter_change(r)
    assert (q["revenue"]["cur"], q["revenue"]["prev"]) == (327108.0, 231324.0)
    assert q["revenue"]["pct"] == 41.41
    assert kf.quarter_change(_rep(1565996, "THYAO", 2025)) is None   # Q4 yillik - 9A ile turetilmez


def test_degerleme_bandi_yil_sonu_resmi_kapanis_ve_o_yilin_raporu():
    band = kf.valuation_band([_rep(1393446, "TUPRS", 2024), _rep(1554106, "TUPRS", 2025)], _closes("TUPRS"))
    assert [(b["yil"], b["kapanis"], b["fk"], b["pd_dd"]) for b in band] == [
        (2024, 141.9, 14.93, 0.97), (2025, 184.4, 12.03, 0.98)]
    assert band[0]["pay_adedi"] == 1926796000.0      # Odenmis Sermaye 1.926.796 bin TL
    g = kf.valuation_band([_rep(1552588, "GARAN", 2025)], _closes("GARAN"))
    assert (g[0]["fk"], g[0]["pd_dd"]) == (5.49, 1.36)


def test_liste_secimi_ve_ikili_yayinda_konsolide():
    with open(os.path.join(FIX, "kap_listeleri.json"), encoding="utf-8") as f:
        lists = json.load(f)
    sel = kf.select_disclosures(lists["GARAN"])
    assert [m["idx"] for m in sel[(2025, 4)]] == [1552588, 1552589]
    assert sel[(2025, 4)][0]["publish"] == "2026-02-04T18:10"
    assert [m["idx"] for m in kf.select_disclosures(lists["TBORG"])[(2024, 4)]] == [1401749]
    assert kf.choose_report([{"idx": 1552589, "nature": "Konsolide Olmayan"},
                             {"idx": 1552588, "nature": "Konsolide"}])["idx"] == 1552588
    assert kf.choose_report([{"idx": 10, "nature": "Konsolide"}, {"idx": 12, "nature": "Konsolide"}])["idx"] == 12
    assert kf.parse_unit("1.000.000 TL") == (1000000, "TL") and kf.parse_unit("USD") == (1, "USD")


def test_trim_page_ayni_kalemleri_verir():
    with gzip.open(os.path.join(FIX, "fr_1401749.html.gz"), "rt", encoding="utf-8") as f:
        h = f.read()
    meta = {"idx": 1401749, "fy": 2024, "period": 4, "publish": None}
    assert kf.build_report(kf.trim_page(h), meta, "TBORG") == kf.build_report(h, meta, "TBORG")


def test_apply_to_fundamentals_kap_varsa_aciklanan_veri_yoksa_yahoo_buyumesi_yok():
    t = _rep(1565996, "THYAO", 2025)
    rec = kf.build_record("THYAO", [t], [_div(1440796, "THYAO"), _div(1590365, "THYAO")])
    yahoo = {"revenue_growth": 20.5, "earnings_growth": 11.0, "net_debt_to_ebitda": 0.14, "ev_to_ebitda": 1.45,
             "dividend_yield": 2.28, "pe_ratio": 3.4, "market_cap": {"value": 404137443328.0, "currency": "TRY"}}
    out = kf.apply_to_fundamentals(yahoo, rec, price=292.5, today=TODAY)
    assert out["revenue_growth"] == 28.18 and out["earnings_growth"] == 4.26
    assert out["net_debt_to_ebitda"] == 2.68
    assert out["ev_to_ebitda"] == round((404137443328.0 + 495486e6) / 184811e6, 2)
    assert out["dividend_yield"] == 0.0 and out["kap"]["temettu"]["odeme_var"] is False
    assert out["pe_ratio"] == 3.4                      # KAP'ta olmayan alan Yahoo'dan kalir
    assert out["kap"]["flags"]["yabanci_para"] == "USD" and out["kap"]["basis"] == "yabanci_para"
    assert "kaynak" not in json.dumps(out)             # ic dogrulama izi API'ye cikmaz
    assert yahoo["revenue_growth"] == 20.5             # girdi degismez
    bare = kf.apply_to_fundamentals(yahoo, None)
    assert bare["revenue_growth"] is None and bare["earnings_growth"] is None
    assert bare["net_debt_to_ebitda"] == 0.14 and "kap" not in bare
    assert kf.apply_to_fundamentals({}, rec) == {}


def test_load_record_mtime_onbellek_ve_sema(tmp_path):
    rec = kf.build_record("TBORG", [_rep(1401749, "TBORG", 2024)])
    (tmp_path / "TBORG.json").write_text(json.dumps(rec), encoding="utf-8")
    assert kf.load_record("TBORG", str(tmp_path))["derived"]["yillik_degisim"]["2024"]["revenue"]["pct"] == 21.81
    assert kf.load_record("YOK", str(tmp_path)) is None
    (tmp_path / "ESKI.json").write_text(json.dumps({"schema_version": 0}), encoding="utf-8")
    assert kf.load_record("ESKI", str(tmp_path)) is None
