"""CPO-1157 §3.1+§3.3+§3.4 — Haber P0: yanlış zaman ekseni + flapping + monitor yakıtı.

Kök neden (canlı doğrulandı, DEV-1503/CPO-1157): kota circuit breaker 600s (10dk)
cooldown kullanıyordu ama Gemini free-tier kotası GÜNLÜK resetleniyor — devre her
10dk'da kapanıp ilk çağrı anında 429 yiyip yeniden açılıyordu (ratchet). Bunun
üstüne, negatif haber cache'i (5dk TTL) süresi dolduğunda endpoint "cache miss"
sayıp loading:true'ya dönüyordu — kota hâlâ tükenmişken bile. Kullanıcı spinner
("loading:true") ile dürüst mesaj ("unavailable:true") arasında salınıyordu.
Yakıt: UptimeRobot'un ~5dk'da bir attığı HEAD istekleri, Werkzeug'un varsayılan
HEAD davranışı yüzünden GET view'ın TÜM yan etkilerini (queue.add dahil) çalıştırıyordu.

Bu testler fix'in varlığını doğrular:
  - §3.1: kota cooldown 600s'den çok daha uzun bir "prob aralığı"na çıkarılmış
  - §3.3: negatif cache TTL'i dolmuş olsa bile kota devresi açıkken endpoint
    deterministik "unavailable" dönüyor, yeni bir bg-fetch kuyruklamıyor
  - §3.4: HEAD istekleri ve UptimeRobot UA'sı cache/queue mantığına hiç girmiyor
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


def test_quota_cooldown_extended_past_ten_minutes():
    src = _read_app()
    m = re.search(r"_GEMINI_QUOTA_CB_COOLDOWN\s*=\s*(\d+)", src)
    assert m, "_GEMINI_QUOTA_CB_COOLDOWN tanımlı değil"
    cooldown = int(m.group(1))
    assert cooldown > 600, (
        f"kota cooldown hâlâ 600s (10dk) ölçeğinde ({cooldown}s) — "
        "günlük kotaya göre yanlış zaman ekseni ratchet'i sürüyor"
    )


def test_news_endpoint_short_circuits_head_and_monitor_ua():
    src = _read_app()
    body = _extract_function_body(src, "api_stock_news")
    assert body, "api_stock_news() bulunamadı"
    assert 'request.method == "HEAD"' in body, (
        "HEAD isteği için erken dönüş yok — Werkzeug varsayılanı queue.add() dahil "
        "tüm yan etkileri çalıştırır"
    )
    assert "uptimerobot" in body.lower(), (
        "UptimeRobot User-Agent kısa devresi yok — monitör kendi kota devresini besliyor"
    )
    # Kısa devre, cache/queue mantığından ÖNCE olmalı (queue'ya add edilmeden dönmeli)
    head_idx = body.index('request.method == "HEAD"')
    queue_idx = body.index('_news_fetch_queue[ticker] = ("stock_news"')
    assert head_idx < queue_idx, "HEAD/monitor kısa devresi queue.add()'den SONRA geliyor"


def test_news_endpoint_deterministic_when_quota_degraded_even_after_cache_expiry():
    src = _read_app()
    body = _extract_function_body(src, "api_stock_news")
    assert body, "api_stock_news() bulunamadı"
    assert "if _gemini_news_degraded():" in body, (
        "kota-tükendi kısa devresi yok — negatif cache TTL'i dolunca hâlâ "
        "loading:true'ya (flapping) dönebilir"
    )
    degraded_idx = body.index("if _gemini_news_degraded():")
    queue_idx = body.index('_news_fetch_queue[ticker] = ("stock_news"')
    assert degraded_idx < queue_idx, (
        "kota-tükendi kontrolü queue'ya eklemeden ÖNCE olmalı — "
        "aksi halde doomed bir bg-fetch israf ediliyor"
    )


def test_quota_degraded_short_circuit_returns_unavailable_not_loading():
    src = _read_app()
    body = _extract_function_body(src, "api_stock_news")
    assert body, "api_stock_news() bulunamadı"
    degraded_idx = body.index("if _gemini_news_degraded():")
    # Bir sonraki return bloğu unavailable:True + loading:False dönmeli, loading:True DEĞİL
    snippet = body[degraded_idx:degraded_idx + 400]
    assert '"loading": False, "unavailable": True' in snippet
