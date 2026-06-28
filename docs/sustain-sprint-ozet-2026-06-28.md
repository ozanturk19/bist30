# Sustain Sprint Özet — 28 Haziran 2026 (Pazar)

**Hedef kitle:** Ozan — Pzt cutover öncesi 5 dakikada oku.  
**Kapsam:** T1–T11 (11 task, ~12 saat, sıfır kod deploy).  
**Durum:** Tüm tasklar DONE. Pzt 30 Haz cutover için zemin hazır.

---

## Özet Tablo

| # | Görev | Çıktı | Pzt Aksiyon |
|---|---|---|---|
| T1 | UX QA Pass — F1-F10 tam | 10/10 regression yok | Yok |
| T2 | F5 0/215 RCA | Root cause net, 2 fix planlandı | Fix 1 Pzt 18:30 |
| T3 | Sprint 4 katalog | `docs/sprint-4-katalog.md` | Okuma |
| T4 | Cutover dry-run #2 | PASS, idempotent | — |
| T5 | F15 dark theme spec | `docs/sprint-4-f15-dark-theme.md` | Sprint 4 W1 |
| T6 | Fix 1 preflight code review | app.py:4641 → 1 satır fix | Pzt 18:30 deploy |
| T7 | Fix 2 rate limiter spec | `docs/sprint-3.5-fix2-rate-limiter.md` | Sprint 4 W1 |
| T8 | F11 push notification spec | `docs/sprint-4-f11-push-notification.md` | Sprint 4 W1 |
| T9 | F14 backtest history spec | `docs/sprint-4-f14-backtest-history.md` | Sprint 4 W2 |
| T10 | F12 AI portföy önerisi spec | `docs/sprint-4-f12-ai-portfoy.md` | Sprint 4 W3-4 |
| T11 | F13 sosyal sinyal feed spec | `docs/sprint-5-f13-sosyal-sinyal.md` | Sprint 5 |

---

## Task Detayları

### T1 — UX QA Pass ✅
**Ne:** F1-F10 tüm feature'lar mobil 375px + desktop 1440px, 3 hisse (AKBNK, THYAO, BIMAS), 3 yeni sayfa (/sektor, /virtual-portfolio, /backtest).  
**Sonuç:** 10/10 feature regression yok. Tüm sayfalar render ediyor.  
**Takip:** Pzt cutover smoke testi aynı listeyi tekrar tarar (bkz. T13).

---

### T2 — F5 0/215 RCA ✅
**Ne:** Makro AI özet skoru sıfır gösteriyordu (cold start sonrası).  
**Root cause:** Üç katmanlı:
1. Cold start = `_sentiment_cache` boş başlıyor
2. Disk persist yok → restart = sıfırlama
3. Gemini rate: worker-local limit → 4 worker × 10 RPM = 40 RPM (Gemini 10 RPM'i aşıyor)

**Fix 1 (Pzt 18:30):** `app.py` veya `sentiment.py` — startup'ta `last_sentiment_cache.json` yükle. Preflight: `app.py:4641` `if computed:` guard kaldırılıyor (2 satır → 1 satır). Risk: minimal, ~30dk.  
**Fix 2 (Sprint 4 W1):** Gemini global rate limiter — flock-based slot reservation. Bkz. T7.

---

### T3 — Sprint 4 Katalog ✅
**Ne:** F11-F15 post-cutover feature backlog. CPO sıralaması onayladı.  
**Dosya:** `docs/sprint-4-katalog.md`  
**Sıralama:** F15+F11 paralel W1 → F14 W2 → F12 W3-4 → F13 Sprint 5.

---

### T4 — Cutover Dry-Run #2 ✅
**Ne:** `./tools/deploy-bundle.sh --dry-run` + pre-flight script yeniden test.  
**Sonuç:** PASS. Idempotent doğrulandı. TARGET_SHA = `b1b7e3d`. Pzt yeşil ışık.  
**Takip:** Yok — script hazır.

---

### T5 — F15 Dark/Light Tema Spec ✅
**Ne:** CSS variable map, WCAG AA kontrast onayı, chart adapter katmanı, 5 adım uygulama planı.  
**Dosya:** `docs/sprint-4-f15-dark-theme.md`  
**Bağımlılık:** Kod yok, Sprint 4 W1'de uygulama başlar başlamaz dosya:satır hazır.

---

### T6 — Fix 1 Preflight Code Review ✅
**Ne:** Sentiment disk persistence fix — mevcut kodu okuyup tam dosya:satır netleştirme.  
**Root cause satırı:** `app.py:4641` — `if computed:` guard sentiment'i blokluyordu.  
**Fix:** O guard'ı kaldır (2 satır → 1 satır). Gevent uyumlu, thread-safe.  
**Deploy zamanı:** Pzt 18:30 TR (seans kapatıldıktan sonra). Pre-deploy MSG 18:00 TR.

---

### T7 — Fix 2 Rate Limiter Spec ✅
**Ne:** Gemini global rate limiter — flock-based inter-process slot reservation.  
**Dosya:** `docs/sprint-3.5-fix2-rate-limiter.md`  
**Çözüm:** `/tmp/borsapusula_gemini_rate.lock` + flock → worker sayısından bağımsız gerçek 10 RPM limit.  
**Deploy zamanı:** Sprint 4 W1, Salı 1 Tem (Fix 1 sonrası 12h+ gözlem).  
**Risk:** Düşük — ~22 satır net diff, mevcut `_gemini_rate_lock` yerine geçiyor.

---

### T8 — F11 Push Notification Spec ✅
**Ne:** Web Push Bildirim entegrasyonu spec.  
**Dosya:** `docs/sprint-4-f11-push-notification.md`  
**Mevcut:** Backend + Service Worker altyapısı zaten var (`static/sw.js:87-119`, `app.py:126-139`, `push_subs.json`).  
**Eksik:** 4 frontend adımı (izin akışı, toggle UI, hisse bağlama, silent fallback).  
**Deploy zamanı:** Sprint 4 W1, Çarşamba 2 Tem.

---

### T9 — F14 Backtest History Spec ✅
**Ne:** Backtest sonuçlarını kaydet + karşılaştır.  
**Dosya:** `docs/sprint-4-f14-backtest-history.md`  
**Çözüm:** Kullanıcı başına JSONL (email hash'i, sunucuda) + 4 endpoint + delta UI. FIFO 50 kayıt cap.  
**Deploy zamanı:** Sprint 4 W2 (7-13 Tem).

---

### T10 — F12 AI Portföy Önerisi Spec ✅
**Ne:** Gemini tabanlı portföy analizi + öneri.  
**Dosya:** `docs/sprint-4-f12-ai-portfoy.md`  
**Çözüm:** Risk profili formu → Gemini prompt JSON → /api/portfoy-oneri. Per-user 24h cache. Maliyet ~$0.12/ay.  
**Deploy zamanı:** Sprint 4 W3-4 (14-27 Tem).

---

### T11 — F13 Sosyal Sinyal Feed Spec ✅
**Ne:** Anonim kullanıcı eylemi (izle/al/sat) → topluluk sinyali.  
**Dosya:** `docs/sprint-5-f13-sosyal-sinyal.md`  
**Tasarım:** session_hash + k-anonimlik (min 5 kullanıcı eşiği) + opt-in localStorage + KVKK 4 hafta retention.  
**Deploy zamanı:** Sprint 5 (Ağustos).

---

## Yol Haritası Tek Bakış

```
Pzt 30 Haz    Cutover (bundle 17, SHA b1b7e3d) → smoke → Ozan vize
Pzt 18:30     Fix 1 deploy (sentiment disk persistence)
Sal 1 Tem     Fix 2 deploy (Gemini global rate limiter)
Sal-Car       F15 dark theme + F11 push notification (paralel)
7-13 Tem      F14 backtest history
14-27 Tem     F12 AI portföy önerisi
Ağu           F13 sosyal sinyal feed (Sprint 5)
```

---

## Risk & Dikkat

| Risk | Durum |
|---|---|
| Cutover rollback | TARGET_SHA `b1b7e3d` explicit — rollback 2 komut |
| Fix 1 seans saati çakışması | Pzt 18:30 deploy, seans 18:00 kapanır → güvenli |
| Fix 2 gevent uyumu | threading.Lock içinde sleep YOK, flock pattern gevent-safe |
| F5 Pzt sabah sıfır görünüm | Bekleniyor — haber akışıyla doğal dolum, Fix 1 akşam |
| Port 8004 / paper-bot | DEV dokunmuyor — bu sprint kapsam dışı |
