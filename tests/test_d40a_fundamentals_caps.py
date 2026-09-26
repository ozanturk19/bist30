"""D-40a (1)+(2): fundamentals şema-döngüsü günlük deneme sınırı, TTL 24 sa, bilanço günü tazelemesi."""
import os
import sys
import time
from datetime import datetime, timedelta

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A

EKSIK = {"statement_trend_quarterly": [], "financial_currency": None, "statement_currency": None}


@pytest.fixture(autouse=True)
def _temiz(monkeypatch):
    monkeypatch.delenv("REFRESH_WORKER", raising=False)
    A._fund_schema_tries.clear()
    yield
    A._fund_schema_tries.clear()
    A._fundamentals_cache.pop("ZZZT", None)


def test_ttl_24_saat():
    assert A._FUND_TTL == 24 * 3600


def test_deneme_hakki_gunde_iki_sonra_sifirlanir():
    now = time.time()
    assert A._fund_schema_try_allowed("ZZZT", now) is True
    assert A._fund_schema_try_allowed("ZZZT", now) is True
    assert A._fund_schema_try_allowed("ZZZT", now) is False
    assert A._fund_schema_try_allowed("ZZZT", now + 86400) is True  # ertesi gün


def test_eksik_kayit_gunde_en_cok_iki_kez_cekilir(monkeypatch):
    cagri = []
    monkeypatch.setattr(A, "_fetch_fundamentals_subprocess", lambda t, timeout=30: cagri.append(t) or None)
    A._fundamentals_cache["ZZZT"] = {"data": dict(EKSIK, marker=1), "ts": time.time() - 3600}
    sonuc = [A._get_fundamentals("ZZZT") for _ in range(6)]
    assert len(cagri) == 2
    assert sonuc[-1].get("marker") == 1  # hak dolunca eldeki kayıt servis edilir


def test_tam_kayit_ttl_icinde_hic_cekilmez(monkeypatch):
    cagri = []
    monkeypatch.setattr(A, "_fetch_fundamentals_subprocess", lambda t, timeout=30: cagri.append(t) or None)
    tam = {"statement_trend_quarterly": [1], "financial_currency": "TRY", "statement_currency": "TRY"}
    A._fundamentals_cache["ZZZT"] = {"data": tam, "ts": time.time() - 20 * 3600}  # eski 4 sa TTL'de bayat sayılırdı
    for _ in range(3):
        A._get_fundamentals("ZZZT")
    assert cagri == []


def test_bilanco_gunu_tazeleme(monkeypatch):
    bugun = datetime.now(A._TZ_TR).date()
    monkeypatch.setitem(A._earnings_cache, "data", {"estimates": {
        "ZZZT": (bugun - timedelta(days=1)).isoformat(),
        "ZZZU": (bugun - timedelta(days=9)).isoformat(),
        "ZZZV": (bugun + timedelta(days=2)).isoformat()}})
    now = time.time()
    eski = {"ts": now - 13 * 3600}
    assert A._fund_earnings_due("ZZZT", eski, now) is True
    assert A._fund_earnings_due("ZZZT", {"ts": now - 3600}, now) is False  # 12 saatten taze
    assert A._fund_earnings_due("ZZZU", eski, now) is False  # 3 günden eski
    assert A._fund_earnings_due("ZZZV", eski, now) is False  # henüz açıklanmadı
    assert A._fund_earnings_due("YOK", eski, now) is False


def test_warmup_daemon_acilista_diski_yukler():
    import inspect
    kaynak = inspect.getsource(A._fundamentals_warmup_daemon)
    assert kaynak.index("_load_fundamentals_cache_from_disk()") < kaynak.index("while True")
