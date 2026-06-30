"""Görev 25 — _cache["loading"] flag düzgün sıfırlama testleri (G25).

Root cause (24 Haz 2026): _cache.get("loading", True) default=True,
ama refresh_data() ve _load_cache_from_disk() loading=False SET ETMİYORDU.
Sonuç: /api/health her zaman loading=True döndürüyordu.

Bu testler fix'in (fb1ea4c) varlığını ve doğruluğunu doğrular:
  - refresh_data()  → with _lock: blokunda _cache["loading"] = False
  - _load_cache_from_disk() → with _lock: blokunda _cache["loading"] = False
  - _compute_health() → cache_loading okunuyor (okuma var = fix etkili)
  - Health varsayılan: loading=True default korunuyor (yeni data olmadan True kalmalı)
"""
import re
import os

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


# ── refresh_data() / _refresh_data_impl() kontrolleri ────────────────────────
# M2 (CPO-905): refresh_data() lock wrapper'a dönüştürüldü; gerçek implementasyon
# _refresh_data_impl() içinde. Testler her iki fonksiyonu birleşik kontrol eder.

def _get_refresh_impl_body(src):
    """M2 sonrası: _refresh_data_impl() varsa onu, yoksa refresh_data() kullan."""
    body = _extract_function_body(src, "_refresh_data_impl")
    if body:
        return body
    return _extract_function_body(src, "refresh_data")


def test_refresh_data_sets_loading_false():
    """refresh_data() veya _refresh_data_impl() içinde _cache["loading"] = False olmalı."""
    src = _read_app()
    body = _get_refresh_impl_body(src)
    assert body, "refresh_data() / _refresh_data_impl() bulunamadı"
    has_loading_false = (
        '_cache["loading"] = False' in body or
        "_cache['loading'] = False" in body
    )
    assert has_loading_false, (
        '_cache["loading"] = False bulunamadı — '
        "partial success (ANALYZE_TIMEOUT) dahil loading sıfırlanmıyor"
    )


def test_refresh_data_loading_false_in_lock_block():
    """loading=False cache data yazımıyla aynı with _lock: blokunda olmalı."""
    src = _read_app()
    body = _get_refresh_impl_body(src)
    assert body, "refresh_data() / _refresh_data_impl() bulunamadı"

    lock_blocks = re.findall(
        r"with _lock:(.*?)(?=\n {4}(?![ \t])|\Z)",
        body,
        re.DOTALL,
    )
    assert lock_blocks, "refresh_data() / _refresh_data_impl() içinde hiç with _lock: bloğu bulunamadı"

    write_block = None
    for block in lock_blocks:
        if '_cache["data"] = results' in block or "_cache['data'] = results" in block:
            write_block = block
            break

    assert write_block is not None, (
        "_cache['data'] = results içeren with _lock: bloğu bulunamadı"
    )

    has_loading_false = (
        '_cache["loading"] = False' in write_block or
        "_cache['loading'] = False" in write_block
    )
    assert has_loading_false, (
        "data-write lock bloğunda _cache['loading'] = False bulunamadı — "
        "data yazımı ve loading reset AYNI lock bloğunda olmalı (atomik)"
    )


def test_refresh_data_loading_false_after_data_write():
    """loading=False, _cache["data"] yazımından SONRA (veya aynı blokta) olmalı."""
    src = _read_app()
    body = _get_refresh_impl_body(src)
    assert body, "refresh_data() / _refresh_data_impl() bulunamadı"

    data_pos = body.find('_cache["data"] = results')
    if data_pos == -1:
        data_pos = body.find("_cache['data'] = results")

    loading_pos = body.find('_cache["loading"] = False')
    if loading_pos == -1:
        loading_pos = body.find("_cache['loading'] = False")

    assert data_pos != -1, "_cache['data'] = results bulunamadı"
    assert loading_pos != -1, "_cache['loading'] = False bulunamadı"
    assert loading_pos > data_pos, (
        "loading=False, data yazımından ÖNCE geliyor — sıra yanlış"
    )


# ── _load_cache_from_disk() kontrolleri ──────────────────────────────────────

def test_load_cache_from_disk_sets_loading_false():
    """_load_cache_from_disk() içinde _cache["loading"] = False satırı olmalı."""
    src = _read_app()
    body = _extract_function_body(src, "_load_cache_from_disk")
    assert body, "_load_cache_from_disk() bulunamadı"
    has_loading_false = (
        '_cache["loading"] = False' in body or
        "_cache['loading'] = False" in body
    )
    assert has_loading_false, (
        '_load_cache_from_disk() içinde _cache["loading"] = False bulunamadı — '
        "disk-reload sonrası web worker loading flag sıfırlanmıyor"
    )


def test_load_cache_from_disk_loading_false_in_lock_block():
    """_load_cache_from_disk() loading=False, with _lock: bloğunda olmalı."""
    src = _read_app()
    body = _extract_function_body(src, "_load_cache_from_disk")
    assert body, "_load_cache_from_disk() bulunamadı"

    lock_pattern = re.search(
        r"with _lock:(.*?)(?=\n            [^ ]|\Z)",
        body,
        re.DOTALL,
    )
    assert lock_pattern, "_load_cache_from_disk() içinde with _lock: bloğu bulunamadı"

    lock_body = lock_pattern.group(1)
    has_data_write = '_cache["data"] = data' in lock_body or "_cache['data'] = data" in lock_body
    has_loading_false = (
        '_cache["loading"] = False' in lock_body or
        "_cache['loading'] = False" in lock_body
    )
    assert has_data_write, "_load_cache_from_disk() lock bloğunda _cache['data'] = data bulunamadı"
    assert has_loading_false, (
        "_load_cache_from_disk() lock bloğunda _cache['loading'] = False bulunamadı"
    )


# ── _compute_health() kontrolleri ────────────────────────────────────────────

def test_compute_health_reads_loading_from_cache():
    """_compute_health() _cache'ten loading okuyor olmalı."""
    src = _read_app()
    body = _extract_function_body(src, "_compute_health")
    assert body, "_compute_health() bulunamadı"
    reads_loading = (
        '_cache.get("loading"' in body or
        "_cache.get('loading'" in body
    )
    assert reads_loading, "_compute_health() _cache.get('loading', ...) okumuyordu"


def test_compute_health_loading_default_is_true():
    """_compute_health() loading flag için True default korunmalı (veri yokken safe state)."""
    src = _read_app()
    body = _extract_function_body(src, "_compute_health")
    assert body, "_compute_health() bulunamadı"

    # True default: ilk yüklemede (cache boş) loading=True → frontend skeleton gösterir
    has_true_default = (
        '_cache.get("loading", True)' in body or
        "_cache.get('loading', True)" in body
    )
    assert has_true_default, (
        "_compute_health() loading default=True olmalı — "
        "cold start'ta cache boşken skeleton göstermek için"
    )


def test_health_endpoint_includes_loading_in_stocks():
    """Health endpoint yanıtında stocks.loading alanı olmalı."""
    src = _read_app()
    body = _extract_function_body(src, "_compute_health")
    assert body, "_compute_health() bulunamadı"

    # "loading": cache_loading şeklinde stocks dict'ine dahil edilmeli
    has_loading_in_response = '"loading": cache_loading' in body or "'loading': cache_loading" in body
    assert has_loading_in_response, (
        "_compute_health() stocks yanıtında 'loading': cache_loading yok"
    )


# ── Regresyon: loading flag hem yerde var mı kontrol ─────────────────────────

def test_loading_false_present_in_exactly_two_functions():
    """_cache["loading"] = False tam olarak 2 fonksiyonda olmalı (refresh_data + _load_cache_from_disk)."""
    src = _read_app()
    # Direkt sayım — G25 fix 2 yerde
    count = src.count('_cache["loading"] = False') + src.count("_cache['loading'] = False")
    assert count >= 2, (
        f"_cache['loading'] = False yalnızca {count} yerde — "
        "refresh_data() ve _load_cache_from_disk() her ikisi de set etmeli"
    )


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_refresh_data_sets_loading_false,
        test_refresh_data_loading_false_in_lock_block,
        test_refresh_data_loading_false_after_data_write,
        test_load_cache_from_disk_sets_loading_false,
        test_load_cache_from_disk_loading_false_in_lock_block,
        test_compute_health_reads_loading_from_cache,
        test_compute_health_loading_default_is_true,
        test_health_endpoint_includes_loading_in_stocks,
        test_loading_false_present_in_exactly_two_functions,
    ]
    passed = 0
    fail_names = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✓ {t.__name__}")
        except Exception as e:
            fail_names.append(t.__name__)
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{'='*65}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED ✅")
