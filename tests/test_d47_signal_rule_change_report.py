"""D-47 kalan kalem — "kural değişirse kaç hissenin durumu değişir" raporu
(tools/signal_rule_change_report.py, bp_yonlu_sim.py'nin genelleşmiş hali).
Sentetik snapshot ile, py3.9 yerel."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)

import business_rules as br  # noqa: E402
import signal_rule_change_report as R  # noqa: E402

# 4 sentetik hisse: biri ADX eşiğinin TAM üstünde (26, mevcut eşik 25'i geçer
# ama 30'u geçmez) — eşik 25→30 olursa SADECE bu hissenin adx_bull oyu düşer.
STOCKS = [
    {"ticker": "AAAA", "adx": 26.0, "di_plus": 20.0, "di_minus": 10.0,
     "e12": 12.0, "e99": 10.0, "weekly_trend": 1,
     "indicators": {"supertrend": {"bull": True, "bear": False}}},   # 5/5 → AL (eşik 25'te)
    {"ticker": "BBBB", "adx": 40.0, "di_plus": 20.0, "di_minus": 10.0,
     "e12": 12.0, "e99": 10.0, "weekly_trend": 1,
     "indicators": {"supertrend": {"bull": True, "bear": False}}},   # 5/5, ADX 40 → eşik 30'da da AL
    {"ticker": "CCCC", "adx": 10.0, "di_plus": 5.0, "di_minus": 20.0,
     "e12": 9.0, "e99": 10.0, "weekly_trend": -1,
     "indicators": {"supertrend": {"bull": False, "bear": True}}},   # 0/5 → SAT, eşikten etkilenmez
    {"ticker": "DDDD", "di_plus": 20.0, "di_minus": 10.0,
     "e12": 9.0, "e99": 10.0, "weekly_trend": 0,
     "indicators": {"supertrend": {"bull": False, "bear": False}}},  # adx eksik → atlanır
]


def test_st_dir_bull_bear_duz():
    assert R._st_dir(STOCKS[0]) == 1
    assert R._st_dir(STOCKS[2]) == -1
    assert R._st_dir({"indicators": {}}) == 0


def test_eksik_gosterge_atlanir():
    rows = R.simulate(STOCKS, adx_min=None)
    tickers = {r["ticker"] for r in rows}
    assert "DDDD" not in tickers  # adx alanı yok
    assert tickers == {"AAAA", "BBBB", "CCCC"}


def test_degisiklik_yoksa_sifir_fark():
    """araç kendi kendini sınar: eşik verilmezse (bugünkü kuralla kıyas) fark 0."""
    rows = R.simulate(STOCKS, adx_min=None)
    assert all(not r["degisti"] for r in rows)


def test_adx_esigi_yukseltilince_sinirdaki_hisse_degisir():
    rows = R.simulate(STOCKS, adx_min=30.0)
    by_t = {r["ticker"]: r for r in rows}
    assert by_t["AAAA"]["before"] == "AL"
    assert by_t["AAAA"]["after"] == "BEKLE"   # ADX 26 artık 30 eşiğini geçmiyor
    assert by_t["AAAA"]["degisti"] is True
    assert by_t["BBBB"]["degisti"] is False  # ADX 40, yeni eşikte de 5/5
    assert by_t["CCCC"]["degisti"] is False  # zaten 0/5, eşikten etkilenmez


def test_global_esik_cagri_sonrasi_geri_yuklenir():
    """simulate() br.TREND_ADX_MIN'i geçici değiştirir ama üretim koduna sızdırmaz."""
    orig = br.TREND_ADX_MIN
    R.simulate(STOCKS, adx_min=99.0)
    assert br.TREND_ADX_MIN == orig


def test_print_report_ozet(capsys):
    rows = R.simulate(STOCKS, adx_min=30.0)
    degisen = R.print_report(rows)
    out = capsys.readouterr().out
    assert len(degisen) == 1
    assert "AAAA" in out
    assert "Durum değişen: 1" in out
