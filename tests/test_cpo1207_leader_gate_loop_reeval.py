"""CPO-1207 §1/§2 — leader kapılarının modül-yükleme anındaki tek seferlik
kontrolden döngü-içi her-turda kontrole taşınması.

Kök neden (CPO-1207 canlı bulgusu): `gemini-prefetch` thread'i yalnız
modül-yükleme anında `if _is_gemini_leader(): start()` ile başlatılıyordu.
O anda flock alınamazsa thread o worker'ın ömrü boyunca HİÇ başlamıyordu —
sonradan eski leader ölüp kilit boşalsa bile. Kanıt: `lsof` ile kilit sahibi
871107 iken, o worker'ın prefetch thread'i hiç yoktu (4 nesilden 05:24
neslinde prefetch tamamen ölüydü). Aynı sınıf bug modül-yükleme anında tek
seferlik başlayan her thread'de mevcut: Freshness monitor, chart-integrity
alarm (adı geçmeyen ama bitişik/aynı desendeki ikiz), gemini-company-summary,
ve gemini-cache-sync (bu farklı — thread koşulsuz başlıyordu ama `is_leader`
döngü ÖNCESİNDE bir kez okunup sabit kalıyordu).

Referans doğru desen — codebase'de zaten mevcut: `_digest_cron_loop`, thread'i
koşulsuz başlatıp `_is_digest_leader()`'ı HER TURDA döngü içinde kontrol
ediyor. Bu testler statik kaynak-doğrulamadır (mevcut CPO-1165/1206 testleriyle
aynı desen); app.py'yi import etmez (ağır bağımlılıklar + Python 3.10+ gerekir).
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


def _window_after(src, marker, size=400):
    idx = src.index(marker)
    return src[idx: idx + size]


# ── gemini-prefetch ──────────────────────────────────────────────────────

def test_prefetch_worker_checks_leader_inside_loop():
    src = _read_app()
    body = _extract_function_body(src, "_prefetch_news_worker")
    assert body, "_prefetch_news_worker() bulunamadı"
    while_idx = body.index("while True:")
    guard_window = body[while_idx: while_idx + 700]
    assert "_is_gemini_leader()" in guard_window, (
        "_prefetch_news_worker döngüsü leader durumunu her turda kontrol etmiyor — "
        "CPO-1207 §1'in tam konusu bu"
    )


def test_prefetch_thread_starts_unconditionally():
    src = _read_app()
    idx = src.index("_prefetch_thread = threading.Thread(")
    window = src[idx: idx + 600]
    assert "_prefetch_thread.start()" in window
    # Eski desende .start() bir `if _is_gemini_leader():` bloğunun İÇİNDE idi.
    start_idx = window.index("_prefetch_thread.start()")
    before_start = window[:start_idx]
    assert "if _is_gemini_leader():" not in before_start, (
        "gemini-prefetch thread'i hâlâ module-load-time leader kapısının "
        "arkasında başlıyor — non-leader worker thread'i hiç doğuramaz"
    )


# ── gemini-company-summary ───────────────────────────────────────────────

def test_company_summary_worker_checks_leader_inside_loop():
    src = _read_app()
    body = _extract_function_body(src, "_company_summary_prefetch_worker")
    assert body, "_company_summary_prefetch_worker() bulunamadı"
    while_idx = body.index("while True:")
    guard_window = body[while_idx: while_idx + 300]
    assert "_is_gemini_leader()" in guard_window, (
        "_company_summary_prefetch_worker döngüsü leader durumunu her turda "
        "kontrol etmiyor"
    )


def test_company_summary_thread_starts_unconditionally():
    src = _read_app()
    idx = src.index("_company_summary_thread = threading.Thread(")
    window = src[idx: idx + 400]
    assert "_company_summary_thread.start()" in window
    start_idx = window.index("_company_summary_thread.start()")
    before_start = window[:start_idx]
    assert "if _is_gemini_leader():" not in before_start, (
        "gemini-company-summary thread'i hâlâ module-load-time leader "
        "kapısının arkasında başlıyor"
    )


# ── Freshness monitor ────────────────────────────────────────────────────

def test_freshness_monitor_checks_leader_inside_loop():
    src = _read_app()
    body = _extract_function_body(src, "_freshness_monitor_loop")
    assert body, "_freshness_monitor_loop() bulunamadı"
    while_idx = body.index("while True:")
    guard_window = body[while_idx: while_idx + 200]
    assert "_is_notify_leader()" in guard_window, (
        "Freshness monitor döngüsü leader durumunu her turda kontrol etmiyor"
    )


def test_freshness_monitor_thread_starts_unconditionally():
    src = _read_app()
    idx = src.index('threading.Thread(target=_freshness_monitor_loop')
    window = src[max(0, idx - 300): idx + 100]
    assert "if _is_notify_leader():" not in window, (
        "Freshness monitor thread'i hâlâ module-load-time leader kapısının "
        "arkasında başlıyor"
    )


# ── Chart-integrity alarm (aynı sınıf ikiz, CPO'nun adını vermediği ama ──
# ── bitişik/aynı desende bulunan bug) ────────────────────────────────────

def test_chart_integrity_alarm_checks_leader_inside_loop():
    src = _read_app()
    body = _extract_function_body(src, "_chart_integrity_alarm_loop")
    assert body, "_chart_integrity_alarm_loop() bulunamadı"
    while_idx = body.index("while True:")
    guard_window = body[while_idx: while_idx + 200]
    assert "_is_notify_leader()" in guard_window, (
        "Chart-integrity alarm döngüsü leader durumunu her turda kontrol "
        "etmiyor — Freshness monitor ile aynı sınıf/aynı dosya, atlanmamalı"
    )


def test_chart_integrity_alarm_thread_starts_unconditionally():
    src = _read_app()
    idx = src.index('threading.Thread(target=_chart_integrity_alarm_loop')
    window = src[max(0, idx - 300): idx + 150]
    assert "if _is_notify_leader():" not in window, (
        "Chart-integrity alarm thread'i hâlâ module-load-time leader "
        "kapısının arkasında başlıyor"
    )


# ── gemini-cache-sync — farklı alt-sınıf: thread koşulsuz başlıyor ama ──
# ── is_leader döngü ÖNCESİNDE sabitleniyordu ─────────────────────────────

def test_gemini_cache_sync_reevaluates_leader_inside_loop_not_before():
    src = _read_app()
    body = _extract_function_body(src, "_gemini_cache_sync_loop")
    assert body, "_gemini_cache_sync_loop() bulunamadı"
    while_idx = body.index("while True:")
    before_loop = body[:while_idx]
    inside_loop = body[while_idx:]
    assert "is_leader = _is_gemini_leader()" not in before_loop, (
        "is_leader hâlâ döngüden ÖNCE bir kez okunuyor — kilit sonradan "
        "boşalsa/el değiştirse bile bu thread'in modu hiç güncellenmez"
    )
    assert "is_leader = _is_gemini_leader()" in inside_loop, (
        "is_leader döngü içinde her turda yeniden değerlendirilmiyor"
    )


# ── /api/health — leaders alanı (CPO-1207 §2) ────────────────────────────

def test_health_payload_exposes_leaders_block():
    src = _read_app()
    body = _extract_function_body(src, "_compute_health")
    assert body, "_compute_health() bulunamadı"
    idx = body.index('"leaders":')
    window = body[idx: idx + 250]
    assert '"gemini":' in window and "_is_gemini_leader()" in window, (
        "health.leaders.gemini alanı yok/yanlış"
    )
    assert '"notify":' in window and "_is_notify_leader()" in window, (
        "health.leaders.notify alanı yok/yanlış"
    )
    assert '"prefetch_thread_alive":' in window and "_prefetch_thread.is_alive()" in window, (
        "health.leaders.prefetch_thread_alive alanı yok/yanlış — reload sonrası "
        "'prefetch canlı mı' sorusu yine journalctl/lsof gerektirir"
    )
