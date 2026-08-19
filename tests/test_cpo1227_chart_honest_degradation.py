"""CPO-1227 §2 — makro/varlık chart uçları için dürüst-degradasyon kontratı.

Kök neden: `_serial_chart_refresh` (10 varlık grafiği: BTC/ETH/SOL/BNB/ALTIN/
GUMUS/SP500/NASDAQ/PETROL/DOGALGAZ) REFRESH_WORKER=web olan worker'larda
tamamen atlanıyor (disk köprüsü henüz yok, bkz
[[project_varlik_chart_disk_bridge_missing]]) — yani bu worker'larda
`loading:true` hiçbir zaman gerçekleşmeyecek bir "az sonra dolacak" vaadi
veriyordu. Frontend (`varlik.html loadChart()`) bunu 8s'de bir sonsuz
retry'e çeviriyordu (SENECA 67s'lik süresiz spinner ölçtü).

Fix: `/news` ucundaki kontratla birebir aynı şekil — makul bir süre
(_CHART_LOADING_GRACE_S) sonunda hâlâ veri yoksa `loading:false,
unavailable:true, reason` dön; frontend süresiz retry yerine dürüst mesaj +
manuel "Tekrar dene" göstersin.

Bu testler kaynak-seviyesinde (statik) doğrular — 3.10+ import gerektirmez
(feedback_local_mac_no_python310).

Not (20.08): templates/varlik.html DEV2-036 (fee05c1) ile kaldırıldı —
BTC/ETH/ALTIN/GUMUS/SP500/NASDAQ/SOL/BNB/PETROL/DOGALGAZ tekil sayfaları
silindi (Ozan kararı, BIST odaklı sadeleşme). Üst kayan makro bar
(/api/macro, /api/chart/*) dokunulmadı, bu yüzden grace-period kontratını
doğrulayan ilk iki test hâlâ geçerli. varlik.html'in loadChart() JS'ini
doğrulayan üçüncü test dosyayla birlikte kaldırıldı.
"""
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {re.escape(func_name)}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


def test_chart_loading_grace_period_constant_defined_and_reasonable():
    src = _read(_APP_PY)
    m = re.search(r"_CHART_LOADING_GRACE_S\s*=\s*(\d+)", src)
    assert m, "_CHART_LOADING_GRACE_S sabiti tanımlı değil"
    grace = int(m.group(1))
    assert 30 <= grace <= 1800, (
        f"_CHART_LOADING_GRACE_S={grace}s makul aralık dışında — çok kısa gerçek "
        "'loading' durumlarını erken 'unavailable'a çevirir, çok uzun spinner'ı "
        "olduğu gibi bırakır (CPO-1227'nin şikayeti)"
    )


def test_chart_response_returns_honest_unavailable_after_grace_period():
    src = _read(_APP_PY)
    body = _extract_function_body(src, "_chart_response_with_macro_summary")
    assert body, "_chart_response_with_macro_summary() bulunamadı"
    assert "_CHART_LOADING_GRACE_S" in body, (
        "grace-period kontrolü fonksiyondan kaldırılmış — loading:true "
        "artık süresiz döner (CPO-1227 rekürans riski)"
    )
    assert '"unavailable": True' in body, (
        "grace period sonrası dürüst-degradasyon kontratı (unavailable:True) yok"
    )
    # unavailable kontrolü, loading:True dönüşünden ÖNCE olmalı — aksi halde
    # her zaman loading:True'ya düşer, unavailable'a asla ulaşılmaz.
    unavailable_idx = body.index('"unavailable": True')
    loading_true_idx = body.index('"loading": True')
    assert unavailable_idx < loading_true_idx, (
        "unavailable dalı loading:True dönüşünden SONRA — asla çalışmaz "
        "(erken return loading:True'da gerçekleşir)"
    )
