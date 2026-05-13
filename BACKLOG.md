# BorsaPusula — Backlog

## Soak test başarıyla bittiğinde yapılacaklar

### Test infra
- `tests/regression_macro_concurrency.py` urllib → `httpx.AsyncClient`
  - Mevcut: ThreadPoolExecutor + urllib blocking → gevent-uyumsuz
  - Hedef: `asyncio` + `httpx` → gerçek concurrent test, false-positive yok

### Observability
- Per-worker state → shared cache
  - Mevcut: `_news_queue_stats`, `_macro_bg_stats` per-worker memory
  - Hedef: Redis veya `last_state.json` disk-shared (yeterli, 4 worker × 4 dosya)
  - /api/health aggregate sayıları gösterir

### Architectural (eğer soak'ta sorun çıkarsa)
- signal-explanation → news ile aynı queue pattern (HIGH)
- fundamentals + chart + mtf → stale-while-revalidate (MEDIUM)

### Local Dev Environment (13 May 2026 — CPO MSG-012 önerisi)
- Mevcut: /Users/mac/Bist ve BTC/Bist30/ var ama venv yok, test prod-only
- Hedef: `python -m venv venv && pip install -r requirements.txt`
  + `.env.local` (yfinance/Gemini key opsiyonel, mock data fallback)
  + `flask run --port 8003` offline test
- Etkisi: Feature 1 gibi büyük UI değişikliklerinde test ortamı olur
- Tahmini: 1-2h
- Öncelik: Feature 1 ticket öncesi olursa iyi olur

### Flaky AUTO-RESTART (13 May 2026 — Brevo 24h Gözlem Sonrası Karar)
- 30dk MSG-007 Task C gözleminde 2 AUTO-RESTART tetiklendi (HTTP=000 timeout)
- Şüpheli kök neden: gunicorn `--max-requests 500` worker recycle anları
- Plan: 24h Brevo mail count gözle. >20 mail kalıyorsa yeni ticket aç:
  - `--max-requests` artır (500 → 2000)
  - `--worker-connections` tune et
  - Recycle sırasında "in-flight requests drain" guard
- Şu an MSG-007 Task C ile **mail spam'i durdurdu** ama site flaky'liği duruyor
- CPO MSG-011 talimatı: 24h sonra karar
