# M1 — Cache Corruption RCA

**Tarih:** 30 Haziran 2026  
**Branch:** fix/codex-m1-m2-m3  
**Etkilenen path:** `app.py` → disk cache okuma + yfinance concurrency

---

## 1. Sorun Tanımı

Ara sıra `/api/data` endpoint'i tutarsız veya eksik veri dönüyor:
- Bazı hisseler 0 fiyat gösteriyor (`"price": 0`)
- `stocks.count` 215 yerine 193 gibi değerlerde donuyor
- Restart sonrası `last_cache.json` yüklenmesine rağmen bazı alanlar eksik

---

## 2. Root Cause Analizi — 3 Katman

### Katman 1: Concurrent `refresh_data()` çağrıları

**Nerede:** `refresh_data()` (app.py:2797)  
**Durum öncesi:** Watchdog timer + gunicorn pre-fork modeli birlikte çalışınca aynı worker içinde ikinci bir `refresh_data()` çağrısı başlayabiliyordu.  
**Etki:** Yarım kalan sonuç seti `_cache["data"]`'ya yazılıyor → 193/215 görünümü.  
**Fix (M2):** `_refresh_data_lock` — non-blocking acquire; ikinci çağrı `return` ile atlanır.

### Katman 2: Disk cache okuma sırasında yazım yarışı

**Nerede:** `_load_disk_cache()` (app.py:2730)  
**Durum:** `_save_cache_to_disk()` ve `_load_disk_cache()` aynı anda çalışabilir.  
`_save_cache_to_disk()` → `open(path, "w")` → json.dump → flush — bu sürede reader bozuk JSON okuyabilir.  
**Mevcut guard:** `_is_valid_disk_cache()` bozuk JSON'u yakalıyor ve yüklemeyi atlıyor.  
**Etki:** Kısa süreli corruption sonrası cache 0 olabiliyor (bir sonraki yazıma kadar).  
**Öneri (gelecek):** Atomic write pattern: `tmp_path` → `json.dump` → `os.rename(tmp_path, dst)` (rename POSIX atomic).

### Katman 3: yfinance subprocess timeout → stale fallback kümülasyonu

**Nerede:** `_analyze_with_timeout()` → `refresh_data()` prev_cache fallback (app.py:2903)  
**Durum:** yfinance zaman zaman bazı ticker'lar için timeout → `analyze()` → `None` → stale fallback.  
Birden fazla seans sonrası stale ticket birikirse, `results` listesi ağırlıklı stale olur.  
**Fix (M3):** `_validate_price_snapshot()` + `_keep_known_good_cache()` — bozuk batch son-bilinen-iyi ile karşılaştırılabilir.

---

## 3. Fix Özeti

| Madde | Fix | Satır |
|---|---|---|
| M2 | `_refresh_data_lock` non-blocking — concurrent skip | app.py:2797 |
| M3 | `_validate_price_snapshot()` + `_keep_known_good_cache()` | app.py:2673+ |
| M3 hook | `_keep_known_good_cache(results)` refresh sonrası | app.py:2921 |

---

## 4. Gelecek Öneri (Kapsam Dışı Bu Branch)

- `_save_cache_to_disk()` → atomic rename pattern (tmp → rename)
- `_stale_count > N` eşiği → last_known_good geri al (agresif corrupted data koruma)
- Ticker bazında stale süre takibi (3+ döngü stale → alarm)

---

*RCA Yazar: DEV Sprint 3.5 M1 | Referans: CPO-903*
