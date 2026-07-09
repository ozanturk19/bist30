"""CPO-1032 Sprint 6 SINIF fix — 4 leader-election flock + _get_kap_uuid offload.

Root cause sınıfı (DEV-1046/CPO-1017/DEV-1102 ile aynı): `open()`/`flock()` ve
senkron `requests.post()` OS-seviyeli syscall'lar — gevent monkey-patch bunları
cooperatize etmiyor (flock) ya da DNS/soket katmanında nadir kenar durumlarda
worker'ın TÜM OS thread'ini bloke edebilir. Fix: her kritik bölüm ayrı bir
`_blocking` fonksiyona taşındı; public wrapper bunu gevent hub threadpool'a
offload edip 10s sert tavan koyuyor (_tp_read_json/_gemini_rate_acquire ile
aynı desen, DEV-1102/5f4baf1).

Bu testler kod tabanını statik olarak inceler (regex) ve `_blocking`
fonksiyonlarını izole exec ile davranış olarak doğrular — sunucu/3.10+ import
gerektirmez (feedback_local_mac_no_python310).
"""
import os
import re

import pytest

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

# (public_fn, blocking_fn, safe_default_literal)
LEADER_FUNCS = [
    ("_is_notify_leader", "_is_notify_leader_blocking", "False"),
    ("_is_bg_leader", "_is_bg_leader_blocking", "False"),
    ("_is_digest_leader", "_is_digest_leader_blocking", "False"),
    ("_is_macro_leader", "_is_macro_leader_blocking", "False"),
]

ALL_FUNCS = LEADER_FUNCS + [("_get_kap_uuid", "_get_kap_uuid_blocking", "None")]


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    # Fonksiyon adı tam eşleşsin — örn. "_is_notify_leader" araması
    # "_is_notify_leader_blocking"'i yakalamasın (kelime sınırı + parantez).
    pattern = rf"def {re.escape(func_name)}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


@pytest.mark.parametrize("public_fn,blocking_fn,_default", ALL_FUNCS)
def test_public_wrapper_offloads_to_threadpool_with_10s_timeout(public_fn, blocking_fn, _default):
    src = _read_app()
    body = _extract_function_body(src, public_fn)
    assert body, f"{public_fn}() bulunamadı"
    assert f"threadpool.spawn({blocking_fn}" in body, (
        f"{public_fn}() kritik bölümü gevent hub threadpool'a offload etmeli "
        f"({blocking_fn} üzerinden) — aksi halde worker syscall'da süresiz bloke olabilir"
    )
    assert ".get(timeout=10)" in body, f"{public_fn}() 10s sert tavan koymalı (_tp_read_json deseni)"


@pytest.mark.parametrize("public_fn,blocking_fn,default", ALL_FUNCS)
def test_timeout_returns_safe_default(public_fn, blocking_fn, default):
    src = _read_app()
    body = _extract_function_body(src, public_fn)
    assert body, f"{public_fn}() bulunamadı"
    assert "except _gevent.Timeout:" in body, f"{public_fn}() _gevent.Timeout yakalamalı"
    timeout_idx = body.index("except _gevent.Timeout:")
    return_idx = body.index(f"return {default}", timeout_idx)
    assert timeout_idx < return_idx, (
        f"{public_fn}() timeout durumunda güvenli varsayılan ({default}) dönmeli — "
        "leader fonksiyonları için non-leader (False), kap_uuid için None"
    )


@pytest.mark.parametrize("public_fn,blocking_fn,_default", ALL_FUNCS)
def test_blocking_fallback_used_when_ws_unavailable(public_fn, blocking_fn, _default):
    src = _read_app()
    body = _extract_function_body(src, public_fn)
    assert body, f"{public_fn}() bulunamadı"
    assert f"return {blocking_fn}(" in body, (
        f"{public_fn}() _WS_AVAILABLE False iken (gevent yokken) senkron "
        f"{blocking_fn}() fallback'ine düşmeli"
    )


@pytest.mark.parametrize("public_fn,blocking_fn,_default", LEADER_FUNCS)
def test_no_direct_call_site_bypasses_wrapper(public_fn, blocking_fn, _default):
    src = _read_app()
    # Blocking fonksiyona doğrudan çağrı sadece: (1) kendi `def` satırı,
    # (2) public wrapper içindeki iki çağrı noktası (threadpool.spawn + sync fallback).
    direct_calls = re.findall(rf"(?<!def ){re.escape(blocking_fn)}\(\)", src)
    assert len(direct_calls) <= 2, (
        f"{blocking_fn}() doğrudan çağrılmamalı (offload atlanır) — "
        f"beklenenden fazla ({len(direct_calls)}) doğrudan çağrı bulundu"
    )


def _load_fn_isolated(func_name, extra_ns=None):
    """Verilen fonksiyonu izole exec ile yükler (gerçek fcntl ile davranış testi).

    `str | None` gibi PEP 604 union dönüş tipleri local py3.9'da def satırı exec
    edilirken TypeError verir (3.10+ syntax, feedback_local_mac_no_python310) —
    izole exec sadece davranışı doğruladığı için imza/annotation önemsiz, testte
    kaldırılır."""
    import fcntl as real_fcntl

    src = _read_app()
    body = _extract_function_body(src, func_name)
    assert body, f"{func_name}() bulunamadı"
    body = re.sub(rf"(def {re.escape(func_name)}\([^)]*\))\s*->\s*[^:]+:", r"\1:", body, count=1)
    ns = {"_fcntl": real_fcntl}
    ns.update(extra_ns or {})
    exec(body, ns)
    return ns[func_name], ns


@pytest.mark.parametrize("blocking_fn,fh_var,path_var", [
    ("_is_notify_leader_blocking", "_notify_lock_fh", "_NOTIFY_LOCK_PATH"),
    ("_is_bg_leader_blocking", "_bg_lock_fh", "_BG_LOCK_PATH"),
    ("_is_digest_leader_blocking", "_digest_lock_fh", "_DIGEST_LOCK_PATH"),
    ("_is_macro_leader_blocking", "_macro_leader_fh", "_MACRO_LOCK_PATH"),
])
def test_leader_blocking_helper_preserves_original_flock_behavior(tmp_path, blocking_fn, fh_var, path_var):
    """Fix öncesi/sonrası davranış birebir aynı olmalı: ilk çağıran True (leader)
    alır, aynı lock dosyasını tutan ikinci bir handle False (non-leader) alır."""
    fn, ns = _load_fn_isolated(blocking_fn, extra_ns={fh_var: None, path_var: str(tmp_path / "leader_test.lock")})
    assert fn() is True, f"{blocking_fn}: ilk çağrı lock'u tutmalı → True (leader)"

    # İkinci bağımsız dosya tanıtıcısı aynı yolu LOCK_NB ile kilitlemeye çalışır —
    # ilk handle hâlâ açık/kilitli olduğundan bloklanmalı (non-leader kanıtı).
    import fcntl
    with open(ns[path_var], "w") as rival_fh:
        with pytest.raises((BlockingIOError, OSError)):
            fcntl.flock(rival_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_kap_uuid_blocking_helper_uses_cache_before_network(monkeypatch):
    """Cache'de (KAP_UUID_OIDS/_kap_uuid_runtime) varsa network'e hiç gidilmemeli —
    davranış fix öncesiyle birebir aynı olmalı."""
    fn, ns = _load_fn_isolated(
        "_get_kap_uuid_blocking",
        extra_ns={"KAP_UUID_OIDS": {"TEST": "cached-uuid-123"}, "_kap_uuid_runtime": {}},
    )
    assert fn("TEST") == "cached-uuid-123"


def test_kap_uuid_blocking_helper_returns_none_on_network_exception():
    """Network hatası (timeout/ConnectionError) sessizce None dönmeli —
    fix öncesi davranışla birebir aynı (try/except Exception: pass)."""
    class _FailingRequests:
        @staticmethod
        def post(*a, **kw):
            raise ConnectionError("boom")

    fn, ns = _load_fn_isolated(
        "_get_kap_uuid_blocking",
        extra_ns={"KAP_UUID_OIDS": {}, "_kap_uuid_runtime": {}, "requests": _FailingRequests()},
    )
    assert fn("UNKNOWN") is None
