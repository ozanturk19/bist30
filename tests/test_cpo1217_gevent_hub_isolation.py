"""CPO-1217 §2 — backtest_ticker() / _compute_mtf() gevent hub-bloke regresyon testi.

02 Ağu 2026: yfinance 1.2.0 curl_cffi kullanıyor — ham libcurl syscall'ı gevent
monkey.patch_all()'ın kapsamı dışında, senkron yf.download() çağrısı worker'ın
TÜM gevent hub'ını (aynı worker'daki her istek dahil, /api/data + /api/macro
dahil) ağın gerçek süresi kadar bloke ediyordu (CPO ölçümü: /api/backtest ve
/api/macro aynı worker'da aynı gün 60.000s+ 504 verdi, hiçbiri HUP/restart
penceresinde değildi). G24 subprocess-izolasyon dalgası (chart/fundamentals/
live-prices) bu iki çağrı noktasını (backtest_ticker, _compute_mtf) hiç
kapsamamıştı — backtest_ticker G24'ten ÖNCE eklenmişti, _compute_mtf'in
"REFRESH_WORKER=web" guard'ı ise prod .env'de bu değer hiç tanımlı olmadığı
için zaten devreye girmiyordu (web worker'lar cache-miss'te senkron çalıştırıyordu).

Fix: ikisi de artık _fetch_daily_subprocess() üzerinden (subprocess.run —
gevent monkey.patch_all() tarafından cooperatif hale getirilmiş) veri çekiyor.
Bu test ileride biri "hızlı olsun" diye tekrar doğrudan yf.download() eklerse
yakalar. Python 3.9 (yerel Mac) app.py'yi (3.10+ sözdizimi) import edemediği
için fonksiyon kaynaktan izole exec edilir (bkz. test_cpo1137_canonical_freshness.py).
"""
import logging
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

with open(_APP_PY, encoding="utf-8") as _f:
    _SRC = _f.read()


def _extract(name):
    m = re.search(rf"def {name}\(.*?\n\n\n", _SRC, re.DOTALL)
    assert m, f"{name}() app.py'de bulunamadı — fonksiyon adı/imzası değişmiş olabilir"
    return m.group(0)


def test_backtest_ticker_no_direct_yf_download():
    src = _extract("backtest_ticker")
    assert "yf.download(" not in src, (
        "backtest_ticker() tekrar doğrudan yf.download() çağırıyor — "
        "gevent hub bloke regresyonu (CPO-1217 §2)"
    )
    assert "_fetch_daily_subprocess(" in src, (
        "backtest_ticker() artık subprocess-izole fetch kullanmalı"
    )


def test_compute_mtf_no_direct_yf_download():
    src = _extract("_compute_mtf")
    assert "yf.download(" not in src, (
        "_compute_mtf() tekrar doğrudan yf.download() çağırıyor — "
        "gevent hub bloke regresyonu (CPO-1217 §2 ek bulgu)"
    )
    assert src.count("_fetch_daily_subprocess(") == 2, (
        "_compute_mtf() içindeki _tf_signal + _tf_signal_4h çağrılarının ikisi de "
        "subprocess-izole fetch kullanmalı"
    )


def test_backtest_ticker_returns_none_on_fetch_failure():
    """Fonksiyonel regresyon: _fetch_daily_subprocess None dönerse (CB-blocked,
    timeout, boş veri) backtest_ticker crash etmemeli, None dönmeli."""
    src = _extract("backtest_ticker")
    calls = []

    def _fake_fetch(ticker_base, period="2y", interval="1d", timeout=25):
        calls.append((ticker_base, period, interval, timeout))
        return None

    ns = {
        "_fetch_daily_subprocess": _fake_fetch,
        "logger": logging.getLogger("test_cpo1217"),
    }
    exec(src, ns)
    result = ns["backtest_ticker"]("THYAO")

    assert result is None
    assert calls == [("THYAO", "2y", "1d", 30)], f"beklenmeyen fetch çağrısı: {calls}"


def test_compute_mtf_returns_structure_on_fetch_failure():
    """Fonksiyonel regresyon: tüm zaman dilimlerinde fetch None dönerse
    _compute_mtf crash etmemeli, tüm alanları None olan bir dict dönmeli."""
    src = _extract("_compute_mtf")
    calls = []

    def _fake_fetch(ticker_base, period="2y", interval="1d", timeout=25):
        calls.append((ticker_base, period, interval, timeout))
        return None

    ns = {
        "_fetch_daily_subprocess": _fake_fetch,
        "logger": logging.getLogger("test_cpo1217"),
    }
    exec(src, ns)
    result = ns["_compute_mtf"]("THYAO")

    assert result == {
        "ticker": "THYAO", "h4": None, "daily": None, "weekly": None, "monthly": None,
    }
    # h4 60d/1h + daily 2y/1d + weekly 5y/1wk + monthly 10y/1mo — hepsi ticker_base ile (sym değil)
    assert ("THYAO", "60d", "1h", 25) in calls
    assert ("THYAO", "2y", "1d", 25) in calls
    assert ("THYAO", "5y", "1wk", 25) in calls
    assert ("THYAO", "10y", "1mo", 25) in calls
