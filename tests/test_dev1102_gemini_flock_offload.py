"""DEV-1102/CPO-1023 — _gemini_rate_acquire() blocking flock offload (PRE-EMPTIVE PREP).

Root cause hipotezi (DEV-1046, 06-07 Tem tekrarlayan TOTAL-OUTAGE): tüm worker'lar
py-spy'da idle görünürken Gemini'siz route'lar (`/`, `/api/data`, `/heatmap`) dahi
8-40s hang'e düştü — CPO-1017'nin `_tp_read_json` öncesi belgelediği sınıfla aynı
imza. `_gemini_rate_acquire()` içindeki `flock(LOCK_EX)` timeout'suz, cross-worker
paylaşımlı bir dosya üzerinde — gevent onu cooperatize etmiyor, bir worker flock'u
uzun tutarsa aynı flock'u bekleyen worker'ın TÜM OS thread'i (o worker'daki her
istek dahil) süresiz bloke olabilir.

Fix (henüz PROD'a deploy EDİLMEDİ — Ozan outage-öncelik kararı bekleniyor,
[[feedback_ozan_vize_async]] gereği kod hazırlığı yapılıyor, deploy değil):
flock-korumalı kritik bölüm `_gemini_rate_acquire_blocking()` adlı ayrı bir
fonksiyona taşındı; `_gemini_rate_acquire()` bunu `_tp_read_json` ile aynı desende
gevent hub threadpool'a offload edip 10s sert tavan koyuyor. Timeout'ta worker'ı
süresiz bloke etmek yerine `_GEMINI_RATE_INTERVAL` (standart bekleme) dönülür.

Bu testler kod tabanını statik olarak inceler (regex) ve `_gemini_rate_acquire_blocking`
fonksiyonunu izole exec ile davranış olarak doğrular — sunucu/3.10+ import gerektirmez
(feedback_local_mac_no_python310).
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


def test_gemini_rate_acquire_offloads_to_threadpool_with_timeout():
    src = _read_app()
    body = _extract_function_body(src, "_gemini_rate_acquire")
    assert body, "_gemini_rate_acquire() bulunamadı"
    assert "threadpool.spawn(_gemini_rate_acquire_blocking).get(timeout=10)" in body, (
        "_gemini_rate_acquire() blocking flock kritik bölümünü gevent hub "
        "threadpool'a offload etmeli — _tp_read_json (CPO-1017) ile aynı desen, "
        "aksi halde worker flock'ta süresiz bloke olabilir (DEV-1046 hipotezi)"
    )


def test_gemini_rate_acquire_timeout_returns_safe_default_not_zero():
    src = _read_app()
    body = _extract_function_body(src, "_gemini_rate_acquire")
    assert body, "_gemini_rate_acquire() bulunamadı"
    assert "except _gevent.Timeout:" in body
    timeout_idx = body.index("except _gevent.Timeout:")
    return_idx = body.index("return _GEMINI_RATE_INTERVAL", timeout_idx)
    assert timeout_idx < return_idx, (
        "Timeout durumunda 0 (beklemesiz devam) DEĞİL, standart "
        "_GEMINI_RATE_INTERVAL dönülmeli — rate-limit güvenliği korunmalı, "
        "hub threadpool tıkanmışken agresif hızlı-geçe izin verilmemeli"
    )


def test_blocking_helper_preserves_original_flock_and_math():
    src = _read_app()
    body = _extract_function_body(src, "_gemini_rate_acquire_blocking")
    assert body, "_gemini_rate_acquire_blocking() bulunamadı"
    # Orijinal flock + slot-reservation mantığı aynen korunmalı — sadece
    # ÇAĞRILDIĞI YER (worker OS thread → threadpool) değişti, davranış değil
    assert "_fcntl.flock(_gemini_rate_fh, _fcntl.LOCK_EX)" in body
    assert "_fcntl.flock(_gemini_rate_fh, _fcntl.LOCK_UN)" in body
    assert "my_slot = max(now, last_slot) + _GEMINI_RATE_INTERVAL" in body
    assert "return my_slot - _GEMINI_RATE_INTERVAL - now" in body


def test_only_call_site_uses_public_wrapper_not_blocking_directly():
    src = _read_app()
    # Tek gerçek çağrı noktası (analiz/sinyal-explanation akışı) hâlâ public
    # _gemini_rate_acquire() sarmalayıcısını kullanmalı — _blocking'i doğrudan
    # çağıran yeni bir call-site eklenmemiş olmalı (offload atlanmasın)
    direct_calls = re.findall(r"(?<!def )(?<!\.spawn\()_gemini_rate_acquire_blocking\(\)", src)
    # Beklenen tek "çağrı" _gemini_rate_acquire() içindeki fallback dönüş satırı
    # (threadpool yokken senkron fallback) — onun dışında doğrudan çağrı olmamalı
    assert len(direct_calls) <= 1, (
        "_gemini_rate_acquire_blocking() doğrudan çağrılmamalı (offload atlanır) — "
        f"beklenmeyen {len(direct_calls)} doğrudan çağrı bulundu"
    )


def _load_blocking_fn_isolated():
    """`_gemini_rate_acquire_blocking`'i izole exec ile yükler, gerçek dosya I/O
    ile davranışını doğrular (fcntl gerçek, /tmp'de geçici dosya kullanılır)."""
    import fcntl as real_fcntl
    import time as real_time

    src = _read_app()
    body = _extract_function_body(src, "_gemini_rate_acquire_blocking")
    assert body, "_gemini_rate_acquire_blocking() bulunamadı"
    ns = {"_fcntl": real_fcntl, "time": real_time}
    exec(body, ns)
    return ns["_gemini_rate_acquire_blocking"], ns


def test_blocking_helper_behaves_identically_to_pre_fix_version(tmp_path):
    """Fix öncesi/sonrası math birebir aynı olmalı — sadece nerede çalıştığı değişti."""
    fn, ns = _load_blocking_fn_isolated()
    lock_path = str(tmp_path / "gemini_rate_test.lock")
    ns["_gemini_rate_fh"] = None
    ns["_GEMINI_RATE_PATH"] = lock_path
    ns["_GEMINI_RATE_INTERVAL"] = 6.5

    wait1 = fn()
    assert wait1 <= 0, "ilk çağrı beklemesiz geçmeli (slot boş)"

    wait2 = fn()
    assert wait2 > 0, "ikinci ardışık çağrı rate-interval kadar beklemeli"
    assert 5.5 <= wait2 <= 6.5, f"beklenen ~6.5s bekleme, gerçek={wait2}"
