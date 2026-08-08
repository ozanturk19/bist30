"""CPO-1340 S1 — prefetch, kota devresi açıkken (retry_after_s > 0) atlamalı.

Canlı kanıt (08.08 07:05 TR): fail_prefetch_today=8, ok_prefetch_today=0, ve gece
boyu ALERT satırlarında retry_after_s 24901 -> 21305 -> ... -> 10643 şeklinde
monoton azalıyordu — yani prefetch, kota penceresinin KAPALI olduğu bilindiği
halde 8 kez ateşledi ve 8'inde de garantili başarısız oldu. Bu hem israf hem
DQV_NEWS alarmını sahte-yeni satırla besliyordu.

Bu testler _prefetch_news_worker()'ın artık ateşlemeden önce _gemini_news_degraded()
kontrolü yaptığını ve atlanan denemeleri get_ai_news() DEĞİL, ayrı bir
prefetch_skipped_quota sayacıyla kaydettiğini doğrular.
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


def test_prefetch_worker_checks_degraded_before_calling_get_ai_news():
    src = _read_app()
    body = _extract_function_body(src, "_prefetch_news_worker")
    assert body, "_prefetch_news_worker() bulunamadı"

    degraded_idx = body.find("_gemini_news_degraded()")
    call_idx = body.find('get_ai_news(ticker, source="prefetch"')
    assert degraded_idx != -1, (
        "_prefetch_news_worker per-ticker döngüsünde _gemini_news_degraded() "
        "kontrolü yok — kota kapalıyken de ateşlemeye devam eder (CPO-1340 S1)"
    )
    assert call_idx != -1, "prefetch worker get_ai_news() çağrısı bulunamadı"
    assert degraded_idx < call_idx, (
        "kota kontrolü get_ai_news() çağrısından SONRA yapılıyor — sıra yanlış, "
        "kapı işe yaramaz"
    )


def test_prefetch_skip_increments_dedicated_counter_not_fail():
    src = _read_app()
    body = _extract_function_body(src, "_prefetch_news_worker")
    assert body, "_prefetch_news_worker() bulunamadı"

    degraded_idx = body.find("if _gemini_news_degraded():")
    assert degraded_idx != -1, "kota-kapısı if bloğu bulunamadı"
    # Kontrol bloğundan sonraki ~300 karakterlik pencerede continue'ya kadar bak.
    window = body[degraded_idx: degraded_idx + 400]
    assert '_news_daily_stats_incr("prefetch_skipped_quota")' in window, (
        "atlanan prefetch denemesi ayrı bir sayaçla kaydedilmiyor — "
        "fail_prefetch_today ile karışırsa gerçek başarısızlıklardan ayrılamaz"
    )
    assert "continue" in window, (
        "kota kapalıyken get_ai_news() çağrısı atlanmıyor (continue yok) — "
        "kapı fiilen çalışmıyor"
    )
    assert '_news_daily_stats_incr("fail")' not in window, (
        "atlanan deneme yanlışlıkla fail sayacını artırıyor — CPO-1340 S1 kabul "
        "ölçütü ihlali (fail_prefetch_today ARTMAMALI)"
    )


def test_prefetch_skipped_quota_counter_in_defaults():
    src = _read_app()
    defaults_idx = src.index("_NEWS_DAILY_STATS_DEFAULTS = {")
    defaults_window = src[defaults_idx: defaults_idx + 600]
    assert '"prefetch_skipped_quota"' in defaults_window, (
        "prefetch_skipped_quota varsayılan sayaç tanımında yok — /api/health "
        "ilk gün 0 yerine KeyError/eksik alan dönebilir"
    )


def test_leader_check_still_precedes_quota_check():
    """Leader olmayan worker zaten prefetch yapmamalı — kota kontrolü bunun
    yerini almamalı, sırası leader kontrolünden SONRA gelmeli."""
    src = _read_app()
    body = _extract_function_body(src, "_prefetch_news_worker")
    leader_idx = body.find("_is_gemini_leader()")
    degraded_idx = body.find("_gemini_news_degraded()")
    assert leader_idx != -1 and degraded_idx != -1
    assert leader_idx < degraded_idx, (
        "kota kontrolü leader kontrolünden önce yapılıyor — non-leader worker "
        "leader kontrolüne hiç ulaşmadan kota kontrolüne girebilir, sıra karışık"
    )
