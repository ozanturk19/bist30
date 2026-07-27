"""CPO-1151 §2 (P1-A) — /api/health'in KAÇAN 4. çağıranı: stocks.updated fallback.

Root cause: _stocks_eff_ts None iken (p90 sentinel bölgesi, gerçek tazelik
bilinmiyor) cache_updated ham cache yazım zamanına (raw_cache_updated)
düşüyordu. Sonuç: aynı payload'da age_s=null ("bilinmiyor") + updated=17:52
("17:52'den") çelişkisi — /api/data'nın (updated_at: null, else fallback yok)
davranışından ayrışıyordu.

Bu testler fix'in varlığını doğrular:
  - cache_updated, _stocks_eff_ts None iken None döner (raw_cache_updated'a düşmez)
  - ham cache zamanı ayrı ve dürüst isimli bir alanda (cache_written_at) korunur
"""
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


def test_cache_updated_does_not_fall_back_to_raw_cache_time():
    src = _read_app()
    body = _extract_function_body(src, "_compute_health")
    assert body, "_compute_health() bulunamadı"
    assert "if _stocks_eff_ts else None" in body, (
        "cache_updated artık _stocks_eff_ts None iken None dönmeli — "
        "raw_cache_updated fallback'i (iyimser, age_s:null ile çelişen) kaldırılmış olmalı"
    )
    assert "if _stocks_eff_ts else raw_cache_updated" not in body, (
        "eski iyimser fallback (raw_cache_updated) hâlâ mevcut"
    )


def test_raw_cache_time_preserved_in_honestly_named_field():
    src = _read_app()
    body = _extract_function_body(src, "_compute_health")
    assert body, "_compute_health() bulunamadı"
    assert '"cache_written_at": raw_cache_updated' in body, (
        "ham cache yazım zamanı kanonik 'updated' alanına gizlenmemeli — "
        "ayrı 'cache_written_at' alanında dönmeli"
    )
