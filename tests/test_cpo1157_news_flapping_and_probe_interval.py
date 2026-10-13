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


# D-22c adım 3 (13.10): api_stock_news() canlıda sıfır tüketiciyle silindi
# (/api/hisse/<T>/news) — HEAD/monitor kısa devresi, kota-tükendi-kısa-devresi
# ve unavailable/loading ayrımını doğrulayan 3 test konusuz kaldı, kaldırıldı.
# §3.1 (cooldown ölçeği) üstteki testte, _gemini_news_degraded()/kota devresi
# kendisi _gemini_call'ın paylaşımlı altyapısında (kalıcı, D-57/ai_notes.py
# tüketiyor) doğrulanmaya devam ediyor.
