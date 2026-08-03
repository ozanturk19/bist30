"""DEV-1570/CPO-1226 — gemini-cache-sync disk I/O threadpool offload.

Root cause (CPO-1218/1221/1223/1226, canlı ölçüldü): `_gemini_cache_sync_loop`
90s'de bir `threading.Thread` içinde çalışıyor, ama monkey.patch_all()
thread=True olduğu için bu "thread" aslında ana hub ile AYNI event loop'u
paylaşan bir greenlet. İçindeki `_save_*_to_disk`/`_load_*_from_disk`
fonksiyonları eskiden inline `open()`/`json.load()`/`_atomic_write_json`
(fsync+os.replace) kullanıyordu — CPO-992/DEV-983'ün izole repro'sunun
gösterdiği gibi (p50 0.6ms -> 1930ms, 6 concurrent fsync writer) bu tür
syscall'lar gevent tarafından cooperatize edilmez ve worker'ın TÜM hub'ını
bloke eder. Yalnız leader worker yazdığı (3 dosya, fsync+replace) için
sızıntı CLOSE_WAIT olarak yalnız o worker'da birikiyordu (95-97/100
worker-connections tavanına dayandı, --max-requests emniyet ağı da bu
yüzden devreye giremiyordu — worker yeni istek kabul edemediği için
istek sayacı ilerlemiyordu).

Fix: zaten prod'da 8+ yerde kanıtlanmış `_tp_read_json`/`_tp_write_json`
(CPO-992/DEV-983 deseni) — gevent hub threadpool'a offload edip 10s tavan
koyar. Bu testler kaynak-seviyesinde (statik) doğrular — 3.10+ import
gerektirmez (feedback_local_mac_no_python310).
"""
import os
import re

import pytest

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

# (fn_name, path_const) — hepsi gemini-cache-sync 90s loop'unun parçası
SAVE_FUNCS = [
    ("_save_macro_ai_to_disk", "_MACRO_AI_DISK_PATH"),
    ("_save_news_cache_to_disk", "_NEWS_CACHE_DISK_PATH"),
    ("_save_company_summary_to_disk", "_COMPANY_SUMMARY_PATH"),
]
LOAD_FUNCS = [
    ("_load_macro_ai_from_disk", "_MACRO_AI_DISK_PATH"),
    ("_load_news_cache_from_disk", "_NEWS_CACHE_DISK_PATH"),
    ("_load_company_summary_from_disk", "_COMPANY_SUMMARY_PATH"),
]


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {re.escape(func_name)}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


@pytest.mark.parametrize("fn_name,path_const", SAVE_FUNCS)
def test_save_fn_uses_threadpool_write_not_inline_atomic_write(fn_name, path_const):
    src = _read_app()
    body = _extract_function_body(src, fn_name)
    assert body, f"{fn_name}() bulunamadı"
    assert f"_tp_write_json({path_const}" in body, (
        f"{fn_name}() artık _tp_write_json (gevent hub threadpool offload) kullanmalı — "
        "inline _atomic_write_json (fsync+os.replace) leader worker'ın hub'ını "
        "bloke edip CLOSE_WAIT sızıntısına yol açıyordu (CPO-1218/1226)"
    )
    assert "_atomic_write_json(" not in body, (
        f"{fn_name}() hâlâ inline _atomic_write_json çağırıyor — threadpool offload'dan kaçıyor"
    )


@pytest.mark.parametrize("fn_name,path_const", LOAD_FUNCS)
def test_load_fn_uses_threadpool_read_not_inline_open(fn_name, path_const):
    src = _read_app()
    body = _extract_function_body(src, fn_name)
    assert body, f"{fn_name}() bulunamadı"
    assert f"_tp_read_json({path_const})" in body, (
        f"{fn_name}() artık _tp_read_json (gevent hub threadpool offload) kullanmalı — "
        "inline open()/json.load() non-leader worker'ın hub'ını da bloke edebilir"
    )
    assert "json.load(" not in body, (
        f"{fn_name}() hâlâ inline json.load() çağırıyor — threadpool offload'dan kaçıyor"
    )
