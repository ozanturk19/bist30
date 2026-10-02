"""CPO-1811 (C-70 K21 backend): /api/karsilastir değerleme hükmü (/hisse ile aynı
kaynak) + ?tickers= kullanıcı sırasının korunması (alfabetik sıralama kalktı)."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_normalize_tickers_kullanici_sirasi_korunur(app_module):
    app = app_module
    # Önceden alfabetik sıralıyordu (AKBNK,THYAO); artık giriş sırası korunur.
    assert app._normalize_tickers("THYAO,AKBNK") == ["THYAO", "AKBNK"]
    assert app._normalize_tickers("garan,ahgaz") == ["GARAN", "AHGAZ"]
    # Tekilleştirme hâlâ çalışır (ilk geçtiği sıra kalır).
    assert app._normalize_tickers("AKBNK,THYAO,AKBNK") == ["AKBNK", "THYAO"]
    # Endeks ticker'ları hâlâ elenir (CPO-1783 regresyonu yok).
    assert "XU030" not in app._normalize_tickers("THYAO,XU030,AKBNK")


def test_karsilastir_301_kullanici_sirasini_korur(app_module):
    client = app_module.app.test_client()
    # Küçük harf girişi 301'i zorunlu kılar (upper'a normalize); önceden hedef
    # alfabetik oluyordu (AKBNK,THYAO) — artık kullanıcı sırası korunur.
    r = client.get("/karsilastir?tickers=thyao,akbnk")
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/karsilastir?tickers=THYAO,AKBNK")


@pytest.mark.parametrize("tickers", [("AHGAZ", "THYAO", "GARAN")])
def test_karsilastir_degerleme_hukmu_hisse_ile_ayni_kaynak(app_module, tickers):
    """/api/karsilastir degerleme.h, /hisse sayfasının HX_TV2.h'sinin KÖKENİ olan
    home_fields.valuation(hs, fund) çağrısıyla birebir aynı sonucu vermeli — CPO-1811
    'yeni hesap icat edilmez' şartı: aynı fonksiyon, aynı girdi zinciri (_financial_health_cache
    + _fundamentals_temel_v2), api_karsilastir içindekiyle AYNI şekilde bağımsız hesaplanır."""
    import home_fields
    app_module._load_health_scores_from_disk()  # CPO-1811 near-miss: arka plan thread'i henüz yüklemediyse disk-reload tetikle
    client = app_module.app.test_client()

    expected = {}
    for t in tickers:
        with app_module._lock:
            hs_cached = app_module._financial_health_cache.get(t)
        hs_data = hs_cached["data"] if hs_cached else None
        fund = app_module._fundamentals_temel_v2(
            t, app_module._fundamentals_kap(t, app_module._get_fundamentals(t))
        ) if t in app_module.BIST100 else {}
        h = home_fields.valuation(hs_data, fund)
        assert h in ("ucuz", "makul", "pahali", "karisik", None)
        expected[t] = h

    r = client.get("/api/karsilastir?tickers=" + ",".join(tickers))
    assert r.status_code == 200
    data = r.get_json()
    got = {row["ticker"]: (row.get("degerleme") or {}).get("h") for row in data["stocks"]}

    for t in tickers:
        assert got[t] == expected[t], (t, got[t], expected[t])
