"""CPO-1206 §3/§4/§5 — news-fetch kuyruğunun gerçek kökeni + worker-local
health dürüstlüğü + kota-devresi israf koruması.

CPO'nun canlı bulgusu: `src="user"` etiketi gerçek kullanıcı talebini değil,
hangi worker thread'inin (_on_demand_news_worker) çağırdığını gösteriyordu.
Kod okumasıyla ikinci bir üretici bulundu — `api_market_news` (piyasa haber
şeridi) de aynı kuyruğu (`_news_fetch_queue`) besliyor ama önceden hem
`_news_queue_stats`'e dokunmuyordu hem de aynı sabit "user" etiketiyle
işleniyordu. Nginx access log'da bu üretici bir freshness-check botu
(`BorsaPusulaQA/1.0`) tarafından tetiklenmiş bulundu — CPO'nun aradığı
"üçüncü üretici" buydu.

Bu testler statik kaynak-doğrulamadır (mevcut CPO-1165/1205 testleriyle aynı
desen); canlı Gemini çağrısı yapmaz.
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


def test_queue_is_ticker_to_origin_mapping_not_bare_set():
    src = _read_app()
    idx = src.index("_news_fetch_queue     = ")
    line = src[idx: idx + 80]
    assert "{}" in line, (
        "_news_fetch_queue artık {ticker: origin} dict olmalı — bare set() ile "
        "kim tarafından eklendiği bilgisi tutulamaz"
    )


def test_stock_news_endpoint_tags_origin_stock_news():
    src = _read_app()
    body = _extract_function_body(src, "api_stock_news")
    assert body, "api_stock_news() bulunamadı"
    assert '_news_fetch_queue[ticker] = ("stock_news"' in body, (
        "api_stock_news kuyruğa eklerken gerçek kökenini (stock_news) etiketlemiyor"
    )


def test_market_news_endpoint_tags_origin_and_updates_stats():
    src = _read_app()
    body = _extract_function_body(src, "api_market_news")
    assert body, "api_market_news() bulunamadı"
    assert '_news_fetch_queue[t] = ("market_news"' in body, (
        "api_market_news kuyruğa eklerken gerçek kökenini (market_news) etiketlemiyor — "
        "CPO-1206'nın bulduğu 'üçüncü üretici' burasıydı"
    )
    assert '_news_queue_stats["total_added"] += 1' in body, (
        "api_market_news hâlâ _news_queue_stats'e dokunmuyor — health.total_added "
        "bu üreticiyi saymaya devam eder (CPO-1206 §4 kısmi kapanmamış olur)"
    )


def test_on_demand_worker_uses_real_origin_not_hardcoded_user():
    src = _read_app()
    body = _extract_function_body(src, "_on_demand_news_worker")
    assert body, "_on_demand_news_worker() bulunamadı"
    assert 'get_ai_news(ticker, source=origin, ua_class=ua_class)' in body, (
        "_on_demand_news_worker hâlâ sabit source=\"user\" ile çağırıyor olabilir — "
        "kuyruktan gelen gerçek origin'i kullanmalı (CPO-1206 §3)"
    )
    assert 'get_ai_news(ticker, source="user")' not in body, (
        "_on_demand_news_worker içinde hâlâ get_ai_news'i hardcoded source=\"user\" ile çağıran kod var"
    )


def test_on_demand_worker_has_degraded_guard_before_draining_queue():
    """CPO-1206 §5 — kota devresi açıkken kuyruk tüketimi getirisi sıfır bir israf."""
    src = _read_app()
    body = _extract_function_body(src, "_on_demand_news_worker")
    assert body, "_on_demand_news_worker() bulunamadı"
    while_idx = body.index("while True:")
    guard_window = body[while_idx: while_idx + 200]
    assert "_gemini_news_degraded()" in guard_window, (
        "worker döngüsünün başında degraded guard yok — devre açıkken kuyruk "
        "boşuna tüketilmeye devam eder"
    )


def test_daily_stats_defaults_include_origin_specific_buckets():
    src = _read_app()
    defaults_idx = src.index("_NEWS_DAILY_STATS_DEFAULTS = {")
    defaults_window = src[defaults_idx: defaults_idx + 400]
    for key in ("ok_stock_news", "ok_market_news", "fail_stock_news", "fail_market_news"):
        assert f'"{key}"' in defaults_window, f"{key} varsayılan sayaç tanımında yok"


def test_health_news_queue_key_is_honestly_labeled_worker_local():
    """CPO-1206 §4 — 'sessiz sıfır' health.news_queue artık worker-local olarak
    açıkça etiketli; global bir toplammış gibi okunmasın."""
    src = _read_app()
    idx = src.index('"news_queue_worker_local"')
    window = src[idx: idx + 300]
    assert "news_queue_note" in window, (
        "news_queue_worker_local yanında 'temsili değil' notu yok"
    )
    assert '"news_queue":' not in src, (
        "eski yanıltıcı 'news_queue' anahtarı hâlâ health payload'ında — "
        "global toplammış gibi okunmaya devam eder"
    )
