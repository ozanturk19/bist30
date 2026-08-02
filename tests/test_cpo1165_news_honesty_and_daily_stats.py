"""CPO-1165 D-NEWS-1/D-NEWS-2 — haber degrade payload'ına retry_after_s + günlük
ok/fail/cb_opens sayaçları.

CPO'nun canlı ölçümü (THYAO/GARAN/EREGL, 19:01-19:02 TR): kota devresi açıkken
kullanıcıya "loading:true" dönen istekler yakalandı. Kök neden DEV-1519'da
bağımsız doğrulandı: _gemini_quota_cb worker-local'di (1555bb8/d8c50c4 ile
paylaşımlı dosyaya taşındı) — endpoint'in "unavailable" dalları zaten dürüsttü,
yalnız yanlış worker'a düşünce hiç tetiklenmiyordu.

Bu testler CPO-1165'in kalan iki somut isteğini doğrular:
  - D-NEWS-1: degrade payload'ı artık CB'nin ne zaman kapanacağını da söylüyor
    (retry_after_s) — frontend "biraz sonra tekrar dene" mesajı kurabilsin.
  - D-NEWS-2: /api/health artık günlük news_ok/news_fail/cb_opens sayacı taşıyor
    — önceden bu sayı yalnız journald grep'iyle (elle) çıkarılabiliyordu.
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


def test_retry_after_helper_exists_and_clamped_nonnegative():
    src = _read_app()
    body = _extract_function_body(src, "_gemini_cb_retry_after_s")
    assert body, "_gemini_cb_retry_after_s() bulunamadı"
    assert "max(0" in body, "retry_after_s negatif olabilir (CB kapalıyken) — max(0, ...) ile clamp edilmeli"


def test_news_endpoint_degraded_branches_include_retry_after_s():
    src = _read_app()
    body = _extract_function_body(src, "api_stock_news")
    assert body, "api_stock_news() bulunamadı"
    unavailable_blocks = [m.start() for m in re.finditer(r'"unavailable":\s*True', body)]
    assert len(unavailable_blocks) == 2, (
        f"beklenen 2 degrade dönüş bloğu bulunamadı (bulundu: {len(unavailable_blocks)}) — "
        "negatif-cache ve kota-devresi-açık dalları"
    )
    for idx in unavailable_blocks:
        window = body[idx: idx + 400]
        assert "retry_after_s" in window, (
            "degrade dönüşünde retry_after_s yok — kullanıcı ne kadar bekleyeceğini bilmiyor (D-NEWS-1)"
        )


def test_daily_stats_incremented_on_cb_open():
    src = _read_app()
    body = _extract_function_body(src, "_gemini_call")
    assert body, "_gemini_call() bulunamadı"
    assert '_news_daily_stats_incr("cb_opens")' in body, (
        "kota devresi açıldığında cb_opens sayacı artmıyor — D-NEWS-2 kapsamı eksik"
    )


def test_daily_stats_incremented_on_demand_worker_ok_and_fail():
    """CPO-1205 §4(1): sayaç artık get_ai_news() içinde tekil kaynaktan artıyor
    (önceden yalnız _on_demand_news_worker artırıyordu, _prefetch_news_worker hiç
    dokunmuyordu — ok/fail toplamı prefetch'i asla yansıtmıyordu). Bu test artık
    on-demand worker'ın get_ai_news()'i kuyruktan gelen gerçek origin ile çağırdığını
    (CPO-1206 §3 — sabit source="user" DEĞİL) VE get_ai_news()'in kendi içinde
    ok/fail'i artırdığını doğruluyor."""
    src = _read_app()
    on_demand_body = _extract_function_body(src, "_on_demand_news_worker")
    assert on_demand_body, "_on_demand_news_worker() bulunamadı"
    assert 'get_ai_news(ticker, source=origin, ua_class=ua_class)' in on_demand_body, (
        "on-demand worker get_ai_news()'i kuyruktaki gerçek origin ile çağırmıyor"
    )
    assert '_news_daily_stats_incr("fail")' in on_demand_body, (
        "on-demand worker exception dalı (get_ai_news'e hiç girilemedi) fail sayacına yansımıyor"
    )

    get_ai_news_body = _extract_function_body(src, "get_ai_news")
    assert get_ai_news_body, "get_ai_news() bulunamadı"
    assert '_news_daily_stats_incr("ok" if text else "fail")' in get_ai_news_body, (
        "get_ai_news() kendi başarı/başarısızlığını günlük sayaca yansıtmıyor — "
        "hem prefetch hem on-demand çağıranlar burada birleşiyor"
    )


def test_daily_stats_source_tagged_prefetch_vs_user():
    """CPO-1205 §4(1) — 28 Tem'den beri ok/fail toplamı yalnız on-demand'dan
    geliyordu, prefetch hiç sayılmadığı için kaynak ayrımı tahmindi. Artık
    get_ai_news(source=...) hem log satırında hem ok_<src>/fail_<src>
    sayaçlarında ayrışıyor."""
    src = _read_app()
    prefetch_body = _extract_function_body(src, "_prefetch_news_worker")
    assert prefetch_body, "_prefetch_news_worker() bulunamadı"
    assert 'get_ai_news(ticker, source="prefetch", ua_class="prefetch")' in prefetch_body, (
        "prefetch worker get_ai_news()'i source=prefetch ile çağırmıyor — "
        "kaynak ayrımı prefetch tarafında kayıp"
    )

    get_ai_news_body = _extract_function_body(src, "get_ai_news")
    assert 'src=%s' in get_ai_news_body, "get_ai_news() log satırlarında src= etiketi yok"
    assert '_news_daily_stats_incr(f"{\'ok\' if text else \'fail\'}_{source}")' in get_ai_news_body, (
        "get_ai_news() kaynak-bazlı sayaç (ok_<src>/fail_<src>) artırmıyor"
    )

    defaults_idx = src.index("_NEWS_DAILY_STATS_DEFAULTS = {")
    defaults_window = src[defaults_idx: defaults_idx + 300]
    for key in ("ok_prefetch", "ok_user", "fail_prefetch", "fail_user"):
        assert f'"{key}"' in defaults_window, f"{key} varsayılan sayaç tanımında yok"


def test_daily_stats_reset_on_calendar_day_change():
    src = _read_app()
    body = _extract_function_body(src, "_news_daily_stats_sync")
    assert body, "_news_daily_stats_sync() bulunamadı"
    assert "_TZ_TR" in body, "gün sınırı TR takvimine göre değil — UTC/naive kaymasına açık"
    assert '{"date": today, **_NEWS_DAILY_STATS_DEFAULTS}' in body, (
        "gün değişince sayaçlar sıfırlanmıyor"
    )
    defaults_idx = src.index("_NEWS_DAILY_STATS_DEFAULTS = {")
    defaults_window = src[defaults_idx: defaults_idx + 300]
    assert '"ok": 0' in defaults_window and '"fail": 0' in defaults_window and '"cb_opens": 0' in defaults_window, (
        "_NEWS_DAILY_STATS_DEFAULTS ok/fail/cb_opens'i sıfırlamıyor"
    )


def test_health_payload_exposes_daily_news_stats_and_retry_after():
    src = _read_app()
    idx = src.index('"news": {')
    window = src[idx: idx + 500]
    assert "_gemini_cb_retry_after_s" in window, "/api/health news bölümünde retry_after_s yok"
    assert "_news_daily_stats_sync" in window, "/api/health news bölümünde günlük sayaçlar yok"
