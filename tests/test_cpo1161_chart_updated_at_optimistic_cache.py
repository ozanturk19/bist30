"""CPO-1161 §5 D1 — chart summary'de gerçek updated_at eksikti, mtime fallback yalan söylüyordu.

Root cause (DEV-1508/CPO-1161 canlı doğrulandı): `_compute_chart_data()`'nın ürettiği
`summary` dict'inde `updated_at` alanı hiç yoktu. `_load_chart_from_disk_per_ticker()`
(app.py:4910) zaten `summary.updated_at`'i tercih ediyordu (`or` ile mtime'a düşüyordu)
ama alan hiç yazılmadığı için HER ZAMAN dosya mtime'ına (yazım zamanı, seri son mum
tarihi DEĞİL) düşüyordu — CPO-1147/CPO-1151 ile aynı optimistic-cache-time ailesinin
3. vakası. Canlı kanıt: 5 tickerin hepsinde updated_at == dosya mtime, ohlc son mumu
ise 3-21 gün önceydi (215'in %65'i ≥11 gün, pozisyonel açlık — Yahoo CB + sabit liste
sırası, ayrı D2 kök nedeni).

Bu testler fix'in varlığını doğrular: summary artık ohlc'nin SON barının tarihinden
türetilmiş dürüst bir updated_at içeriyor, mtime'a hiç referans vermiyor.
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


def test_summary_has_updated_at_field():
    body = _extract_function_body(_read_app(), "_compute_chart_data")
    assert body, "_compute_chart_data() bulunamadı"
    assert '"updated_at":' in body, (
        "summary dict'inde updated_at alanı yok — mtime fallback'e düşmeye devam eder"
    )


def test_updated_at_derived_from_last_ohlc_bar_not_mtime():
    body = _extract_function_body(_read_app(), "_compute_chart_data")
    assert body, "_compute_chart_data() bulunamadı"
    updated_at_idx = body.index('"updated_at":')
    snippet = body[updated_at_idx:updated_at_idx + 200]
    assert 'ohlc[-1]["time"]' in snippet, (
        "updated_at, ohlc'nin son barının tarihinden türetilmiyor"
    )
    assert "getmtime" not in snippet and "os.path.getmtime" not in snippet, (
        "updated_at hesaplamasında hâlâ dosya mtime'ı kullanılıyor"
    )


def test_reader_already_prefers_summary_updated_at_over_mtime():
    """_load_chart_from_disk_per_ticker zaten summary.updated_at'i mtime'dan ÖNCE
    kontrol ediyordu (`or` fallback) — bu test o kontratın bozulmadığını doğrular,
    okuyucu tarafında değişiklik gerekmedi."""
    body = _extract_function_body(_read_app(), "_load_chart_from_disk_per_ticker")
    assert body, "_load_chart_from_disk_per_ticker() bulunamadı"
    assert '(data.get("summary") or {}).get("updated_at")' in body
    assert "or datetime.fromtimestamp(mt" in body, (
        "mtime fallback tamamen kaldırılmış — artık gerçekten hiç summary yoksa "
        "(eski/bozuk dosya) yine de bir değer dönmeli, tamamen None olmamalı"
    )
