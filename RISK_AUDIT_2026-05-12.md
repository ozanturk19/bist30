# Risk Audit Raporu — Diğer 4 Endpoint

> **Tarih:** 12 Mayıs 2026
> **Kapsam:** Read-only audit, kod değişikliği YOK
> **Bağlam:** /api/macro + /api/hisse/X/news kalıcı fix sonrası, kalan endpoint'lerin spike riski.

---

## Risk Skor Tablosu

| Endpoint | Sync external call | Süre (normal) | Worst case | Cache hit oran tahmini | Risk Skoru |
|---|---|---|---|---|---|
| **`/api/hisse/<t>/signal-explanation`** | **Gemini** | 1-5s | 25s timeout | %70-80 | 🔴 **HIGH** |
| `/api/hisse/<t>/fundamentals` | yfinance | 0.5-3s | 20s socket | %95 (4h TTL) | 🟡 MEDIUM |
| `/api/hisse/<t>/chart` | yfinance | 0.5-3s | 20s socket | %95 (15dk TTL) | 🟡 MEDIUM |
| `/api/hisse/<t>/mtf` | yfinance (×3) | 1-5s | 20s socket | %95 (30dk TTL) | 🟡 MEDIUM |
| `/api/hisse/<t>/kap` | HTTP scrape | 0.5-2s | 20s socket | %95 (4h TTL) | 🟢 LOW |

---

## ❶ `/api/hisse/<t>/signal-explanation` — 🔴 HIGH PRIORITY

### Kod analizi (app.py:4386)
```python
@app.route("/api/hisse/<ticker>/signal-explanation")
def api_signal_explanation(ticker):
    # 1. Cache hit'i yok — DOĞRUDAN get_ai_signal_explanation çağırıyor
    text = get_ai_signal_explanation(ticker, stock)
    return safe_json({"explanation": text, ...})
```

`get_ai_signal_explanation` içinde:
- 1 saatlik cache var (`_signal_explain_cache`)
- Cache miss → `_gemini_call` (5-25s)

### Risk profili
- **En sık çağrılan Gemini endpoint** — her hisse detay sayfası açılışında
- Cache hit normal şartlarda hızlı (~3-5ms)
- Cache miss = SYNC Gemini call **request handler içinde** ← MACRO İLE AYNI ANTI-PATTERN
- US stocks için ek: cache miss → `_compute_chart_data()` (yfinance) sonra Gemini

### Spike Senaryoları
1. **Gemini API throttling** (cache cold): 25s timeout × N concurrent → worker saturation
2. **Cache invalidation cascade**: signal değişince cache invalid → tüm aktif kullanıcılar concurrent miss
3. **US ticker cold start**: chart cache + Gemini cascade → 30s+ total

### Düzeltme Önerisi
**Macro pattern'ini uygula:**
- Cache miss → return `{"explanation": null, "loading": true}`
- Frontend retry loop (zaten `loadSignalStory` retry pattern var olabilir, kontrol et)
- BG queue: `_signal_explain_queue` + dedicated worker (15s rate limit)

### Kıyaslama (news fix'i ile)
- Aynı thread pattern (queue + single worker)
- Aynı semantik (placeholder + frontend polling)
- **Beklenen iş:** ~2-3 saat (test dahil)

---

## ❷ `/api/hisse/<t>/fundamentals` — 🟡 MEDIUM

### Kod analizi (app.py:4208)
```python
@app.route("/api/hisse/<ticker>/fundamentals")
def api_stock_fundamentals(ticker):
    data = _get_fundamentals(ticker)
    return safe_json({"fundamentals": data})
```

`_get_fundamentals` içinde:
- **4 saatlik cache** (`_FUND_TTL`)
- Cache miss → `yf.Ticker(sym).info` (yfinance, 1-3s normal)

### Risk profili
- **Cache TTL uzun (4h)** → %95+ hit oran
- yfinance 401/timeout durumunda 20s socket timeout
- Tek call per page open (chart ile aynı zamanda)

### Spike Senaryoları
1. **Yahoo 401 dönerse 215 hisse hepsi cache miss** → cumulative 215×20s = teorik 4300s worker time
2. **Worker recycle (max-requests=500)** sonrası cold cache → 4 worker'da peak load

### Düzeltme Önerisi (eğer gerekirse)
- Stale-while-revalidate pattern (macro'daki gibi)
- Disk persistence (`last_fundamentals.json`)
- Background warm cycle (her 4h × her hisse → 4 saatte 215 call, dakikada ~1 call OK)

### Beklenen iş
~3-4 saat (215 ticker, periodic warm thread complexity)

---

## ❸ `/api/hisse/<t>/chart` — 🟡 MEDIUM

### Kod analizi
```python
data = _compute_chart_data(ticker, "2y")
```

`_compute_chart_data` içinde:
- **15 dakika cache** (`_STOCK_CACHE_TTL`)
- Cache miss → `yf.download(sym, period="2y")` (yfinance, 2-5s normal)
- 500 günlük OHLC indir

### Risk profili
- **TTL kısa (15dk)** → daha sık cache miss
- yfinance download büyük (5-50 KB)
- Multi-index DataFrame parsing CPU-bound

### Spike Senaryoları
1. **Yahoo throttle**: 15dk'da bir 215 hisse cache miss → 215 × 3s = ~10dk worker time
2. **`_serial_chart_refresh` mevcut** (background_global_prices döngüsü) → bunu trust et?

### Düzeltme Önerisi
- TTL 15dk → 30dk (acceptable for daily chart)
- Eğer `_serial_chart_refresh` zaten background cycle yapıyorsa, endpoint pure cache lookup'a çevir
- En riskli senaryo: BIST açılış (10:00 TR) anında concurrent çoklu hisse

### Beklenen iş
~2 saat (audit + TTL bump + endpoint simplification)

---

## ❹ `/api/hisse/<t>/kap` — 🟢 LOW

### Kod analizi
- Public endpoint olarak görünmüyor (grep'te `/api/hisse/<ticker>/kap` route'u tek). Kullanılıyorsa:
- `fetch_kap_disclosures(ticker, days=90)` çağırır
- KAP scraping, 1-2s normal

### Risk profili
- **DÜŞÜK** — KAP servisi stable, rate limit yok
- `_kap_cache` 4h TTL

### Düzeltme gereksiz (low priority)

---

## 📊 Aksiyon Önceliği (Tetik geldiğinde uygulanacak sıra)

```
1. signal-explanation  ← HIGH, Gemini, en sık
2. fundamentals        ← MEDIUM, yfinance
3. chart               ← MEDIUM, yfinance + büyük data
4. mtf                 ← MEDIUM, 3x yfinance (en yavaş)
5. kap                 ← LOW, sadece kontrol
```

## 🎯 Önerilen Tetik

Bu endpoint'lere dokunmadan ÖNCE şunlardan en az biri olmalı:
1. UptimeRobot'tan **gerçek down event** (24-72 saat içinde)
2. Nginx error.log'da **>50 timeout/saat** sustained
3. /api/health `last_macro_refresh_age_s > 600s` (10dk+) — yfinance broken
4. /api/health `last_news_queue_age_s > 1800s` (30dk+) — queue worker stuck

## ⚙️ Mevcut Koruma Katmanları (audit sonucu güvende)

Yukarıdaki endpoint'ler kıracaksa bile şu katmanlar var:

1. **`socket.setdefaulttimeout(20)`** — infinite hang yasak
2. **Gunicorn `--timeout 45`** — worker hard-kill 45s sonra
3. **`--max-requests 500`** — worker periyodik reborn (memory/state temizlik)
4. **4 worker** — paralel kapasite
5. **gevent monkey-patch** — async I/O
6. **Health watchdog cron (1dk)** — 2 fail auto-restart
7. **UptimeRobot keyword check (1dk)** — degraded state catch
8. **Disk cache** (`last_cache.json`, `last_macro.json`) — restart cold start hızlı

Bu 8 katman olduğu sürece, bir endpoint patlasa bile **kullanıcı boş ekran görmez** (worst case: o endpoint için "Loading…" 8-15s).

---

## 📋 24 Saat Sonra Karar Matrisi

| Senaryo | Aksiyon |
|---|---|
| **0 timeout, /api/health ok** her zaman | ✅ Stable — diğer endpoint'lere DOKUNMA |
| 1-5 timeout/saat | 🟡 Monitor — başka aksiyon yok |
| `last_macro_refresh_age_s > 600` event | 🟠 Macro patternı ek koruma incele |
| `last_news_queue_age_s > 1800` event | 🟠 News worker stuck — debug |
| **Sustained 504 timeout (>30/saat)** | 🔴 signal-explanation fix derhal |
| Worker hang silent (log boşluğu) | 🔴 mt → gunicorn config ek tweak |

---

## 🚫 Yapılmayacaklar (24h Beklemede)

- ❌ Diğer endpoint'lere preventive değişiklik (mevcut güvende)
- ❌ Mimari refactor (mevcut pattern doğru, news+macro'da kanıtlandı)
- ❌ Yeni feature (önce stabiliteyi kanıtla)

---

*Son güncelleme: 12 Mayıs 2026 — claude code session*
