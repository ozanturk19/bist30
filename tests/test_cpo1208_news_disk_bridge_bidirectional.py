"""CPO-1208 §1e-1 — haber cache disk köprüsü çift yönlü hale getirildi.

CPO'nun bulgusu: `_gemini_cache_sync_loop` yalnız LEADER dalında 90s'de bir diske
yazıyordu. `get_ai_news()` her worker'da (leader olsun olmasın) çağrılabiliyor
(`_on_demand_news_worker` + `_prefetch_news_worker`), ama non-leader'ın kendi
fetch'lediği ticker hiç diske düşmüyordu. `--max-requests` recycle'ı o worker'ın
in-memory `_news_cache`'ini sıfırlıyor, kaybolan girdi bir daha asla yazılmamış
oluyordu → sıradaki poll garantili cache-miss → gereksiz Gemini çağrısı.

Fix: fetch'i yapan worker kendi sonucunu (başarılı veya negatif-cache) hemen
`_save_news_cache_to_disk()` ile yazar — leader durumundan bağımsız.

Ayrıca CPO-1208 §1(d): "her recycle-sonrası poll gerçekten Gemini çağrısına mı
dönüşüyor" sorusunu 24s ölçmek için NEWS_MEASURE log satırları eklendi
([ua_class]×[cache hit/miss]×[gemini_call] tablosu için).

Bu testler kaynak-seviyesinde (statik) doğrular; canlı Gemini çağrısı yapmaz.
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


def test_get_ai_news_persists_to_disk_unconditionally_not_leader_gated():
    """Fetch'i yapan HER worker kendi sonucunu diske yazar — is_leader kontrolü YOK."""
    src = _read_app()
    body = _extract_function_body(src, "get_ai_news")
    assert body, "get_ai_news() bulunamadı"
    assert "_save_news_cache_to_disk()" in body, (
        "get_ai_news() artık fetch sonucunu hemen diske yazmıyor — non-leader worker'ın "
        "kendi fetch'lediği ticker recycle'da yine kaybolur (CPO-1208 §1e-1)"
    )
    save_idx = body.index("_save_news_cache_to_disk()")
    # Kaydetme çağrısı, cache set edildikten SONRA ve is_leader kontrolüne BAĞLI OLMAMALI.
    cache_set_idx = body.index('_news_cache[ticker] = {"text": text, "ts": now, "failed": False}')
    assert cache_set_idx < save_idx, "diske yazma, cache set edilmeden ÖNCE çağrılıyor"
    call_window = body[cache_set_idx:save_idx]
    assert "_is_gemini_leader" not in call_window, (
        "diske yazma hâlâ is_leader kontrolüne bağlı — bu tam olarak fix'in giderdiği "
        "tek-yönlü köprü asimetrisi"
    )


def test_news_measure_logs_cover_both_hit_and_miss_paths():
    """CPO-1208 §1(d) — [ua_class]×[hit/miss]×[gemini_call] tablosu için ölçüm satırları."""
    src = _read_app()
    body = _extract_function_body(src, "get_ai_news")
    assert body, "get_ai_news() bulunamadı"
    assert "NEWS_MEASURE" in body, "get_ai_news() NEWS_MEASURE ölçüm log satırı basmıyor"
    assert "cache=hit gemini_call=no" in body, "cache-hit dalı için ölçüm log satırı yok"
    assert "cache=miss gemini_call=yes" in body, "cache-miss (gerçek fetch) dalı için ölçüm log satırı yok"


def test_queue_carries_ua_class_alongside_origin():
    """Kuyruk artık {ticker: (origin, ua_class)} — ua_class NEWS_MEASURE'a taşınıyor."""
    src = _read_app()
    idx = src.index("_news_fetch_queue     = ")
    line = src[idx: idx + 80]
    assert "{}" in line, "_news_fetch_queue hâlâ dict olmalı"

    stock_body = _extract_function_body(src, "api_stock_news")
    assert '_news_fetch_queue[ticker] = ("stock_news", _news_ua_class(request))' in stock_body, (
        "api_stock_news kuyruğa eklerken UA sınıfını taşımıyor"
    )

    market_body = _extract_function_body(src, "api_market_news")
    assert '_news_fetch_queue[t] = ("market_news", _news_ua_class(request))' in market_body, (
        "api_market_news kuyruğa eklerken UA sınıfını taşımıyor"
    )

    on_demand_body = _extract_function_body(src, "_on_demand_news_worker")
    assert "ticker, (origin, ua_class) = _news_fetch_queue.popitem()" in on_demand_body, (
        "_on_demand_news_worker kuyruktan (origin, ua_class) tuple'ını açmıyor"
    )
    assert "get_ai_news(ticker, source=origin, ua_class=ua_class)" in on_demand_body, (
        "_on_demand_news_worker ua_class'ı get_ai_news()'e iletmiyor"
    )


def test_news_ua_class_classifies_known_monitor_and_bot_uas():
    """UptimeRobot/HeadlessChrome/BorsaPusulaQA ayrı sınıflara düşmeli — CPO'nun nginx
    analizinde (CPO-1208) kotayı tüketen üç gerçek UA sınıfı bunlardı."""
    src = _read_app()
    body = _extract_function_body(src, "_news_ua_class")
    assert body, "_news_ua_class() bulunamadı"
    assert '"uptimerobot"' in body
    assert '"headless_chrome"' in body
    assert '"qa_bot"' in body
    assert "_NON_HUMAN_UA_RE" in body, (
        "diğer bot sınıfları için mevcut _NON_HUMAN_UA_RE'yi yeniden kullanmıyor "
        "(gereksiz ikinci bir regex tanımlamak yerine)"
    )


def test_prefetch_worker_tags_ua_class_prefetch():
    src = _read_app()
    body = _extract_function_body(src, "_prefetch_news_worker")
    assert body, "_prefetch_news_worker() bulunamadı"
    assert 'get_ai_news(ticker, source="prefetch", ua_class="prefetch")' in body
