"""CPO-1205 §4 madde 2/3 — Gemini prefetch amplifikatörü fix.

CPO'nun bulgusu: leader worker `--max-requests 500` recycle'ıyla 6 saatten çok
daha sık ölüyor. İki asimetri bunu pahalı hale getiriyordu:

  - madde 2: `_gemini_cache_sync_loop` leader dalında ASLA disk okumuyordu —
    yeni doğan boş leader diski hiç görmeden 8 hissenin tamamını Gemini'den
    yeniden istiyordu, sonra bu (kısmi) durumu diskin üstüne yazıyordu.
  - madde 3: prefetch turu `time.sleep(_NEWS_CACHE_TTL)` ile PROSES ömrüne
    bağlıydı — worker öldüğünde sayaç sıfırlanıyor, 6 saatlik aralık hiç
    dolmadan yeni PID sıfırdan bir tur daha çalıştırıyordu.

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


def test_leader_reads_disk_before_sync_loop_starts():
    """madde 2: leader artık döngüye girmeden önce bir kez diski okuyor."""
    src = _read_app()
    body = _extract_function_body(src, "_gemini_cache_sync_loop")
    assert body, "_gemini_cache_sync_loop() bulunamadı"
    before_loop = body.split("while True:")[0]
    assert "_load_news_cache_from_disk()" in before_loop, (
        "leader boot'ta _load_news_cache_from_disk() çağırmıyor — recycle sonrası "
        "boş leader diski görmeden Gemini'ye tam tur yeniden soruyor (CPO-1205 §4-2)"
    )


def test_save_news_cache_merges_with_existing_disk_copy():
    """madde 2: küçük bir in-memory snapshot, disk'teki daha zengin kopyayı silmemeli."""
    src = _read_app()
    body = _extract_function_body(src, "_save_news_cache_to_disk")
    assert body, "_save_news_cache_to_disk() bulunamadı"
    assert "json.load(f)" in body, (
        "_save_news_cache_to_disk artık yazmadan önce disk'teki mevcut kaydı okumuyor — "
        "kısmi/az veri disk'teki zengin kopyayı ezme riski sürüyor"
    )
    assert "_atomic_write_json(_NEWS_CACHE_DISK_PATH, merged)" in body, (
        "diske yazılan artık ham snapshot değil, disk+memory birleşimi (merged) olmalı"
    )


def test_prefetch_round_gated_by_disk_timestamp_not_process_sleep():
    """madde 3: tur artık disk'teki son-tur damgasına bağlı, process sleep'ine değil."""
    src = _read_app()
    body = _extract_function_body(src, "_prefetch_news_worker")
    assert body, "_prefetch_news_worker() bulunamadı"
    assert "_prefetch_last_run_ts()" in body, (
        "prefetch turu disk'teki son-tur zaman damgasını kontrol etmiyor — "
        "--max-requests recycle'ında process sleep'i sıfırlanır, tur zamanı korunmaz"
    )
    assert "_prefetch_mark_run(now)" in body, (
        "tamamlanan tur sonunda zaman damgası diske yazılmıyor — yeni PID'de "
        "6 saatlik gate hiç uygulanmaz"
    )
    assert "time.sleep(_NEWS_CACHE_TTL)" not in body, (
        "tur hâlâ process ömrüne bağlı 6 saatlik sleep kullanıyor — disk-gate "
        "eklendiyse bu tam çözüm değil, eski davranış hâlâ etkin"
    )


def test_prefetch_last_run_helpers_are_disk_backed():
    src = _read_app()
    ts_body = _extract_function_body(src, "_prefetch_last_run_ts")
    mark_body = _extract_function_body(src, "_prefetch_mark_run")
    assert ts_body and mark_body, "_prefetch_last_run_ts/_prefetch_mark_run bulunamadı"
    assert "_PREFETCH_LAST_RUN_PATH" in ts_body and "_PREFETCH_LAST_RUN_PATH" in mark_body, (
        "helper'lar aynı disk yoluna okuyup yazmıyor"
    )
    assert "_atomic_write_json" in mark_body, "_prefetch_mark_run atomic yazmıyor (yarı yazılmış dosya riski)"
