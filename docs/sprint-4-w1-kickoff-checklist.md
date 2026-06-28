# Sprint 4 W1 Kickoff Checklist

**Tarih:** 30 Haziran – 6 Temmuz 2026  
**Önkoşul:** Bundle 17 cutover tamamlanmış (TARGET_SHA `b1b7e3d`)

---

## Gün 0 — Pazartesi 30 Haziran

### 09:30 TR — Cutover

```bash
# VPS üzerinde (root@135.181.206.109)
cd /root/bist30
git fetch origin
git log --oneline -3   # b1b7e3d görülüyor mu?
./tools/deploy-bundle.sh   # prod deploy (bundle 17)
```

**Definition of Done:**
- [ ] `git log HEAD -1` → SHA `b1b7e3d`
- [ ] `systemctl status bist30` → active (running)
- [ ] `curl -s http://localhost:8003/health` → 200 OK

**Rollback:**
```bash
git checkout b1b7e3d~1   # bir önceki stabil
systemctl restart bist30
```

---

### 10:00 TR — Smoke Testi + Ozan Vize

**Kontrol listesi (Ozan tarayıcıdan):**

| Sayfa | Test | Beklenen |
|---|---|---|
| Ana sayfa | AKBNK, THYAO, BIMAS sinyalleri | AL/SAT/BEKLE görünüyor |
| /sektor | Sektör tablosu | Yükleniyor |
| /virtual-portfolio | Portföy sayfası | Render ediyor |
| /backtest | Backtest sayfası | Form görünüyor |
| F5 Makro AI özet | 0/215 mu? | Bekleniyor (Fix 1 akşam) |
| Mobil 375px | Ana sayfa | Responsive kırılma yok |

**Vize:** Ozan smoke listesini onaylarsa Sprint 4 W1 açık. Hayır = rollback önce.

---

### 18:00 TR — Pre-Deploy MSG

DEV → CPO mesajı:
- Patch: sentiment disk persistence fix
- Dosya:Satır: `app.py:4641`
- Diff özeti: `if computed:` guard kaldırılıyor (2 satır → 1 satır)  
- Restart planı: `systemctl restart bist30` (cold cache → 5-10dk dolum)
- CPO 10dk onay penceresi

---

### 18:30 TR — Fix 1 Deploy (Sentiment Disk Persistence)

**Ön koşul:** CPO onayı + seans 18:00 kapandı.

```bash
# Lokal (Mac)
cd "/Users/mac/Bist ve BTC/Bist30"
git add app.py     # veya sentiment.py
git commit -m "fix(sentiment): startup cache load, remove computed guard (app.py:4641)"
git push origin main

# VPS
cd /root/bist30
git pull origin main
systemctl restart bist30
```

**5-10 dk bekle (cold cache window)** — bkz. memory `cold_cache_restart`.

**Smoke (18:40+ TR):**
- [ ] `/health` → 200
- [ ] F5 makro özet skorun sıfırdan yükselmeye başladığı görülüyor (10-15dk içinde)
- [ ] Hata loglarında exception yok: `journalctl -u bist30 -n 50`

**Definition of Done:**
- [ ] `last_sentiment_cache.json` disk'e yazıldı: `ls -la /root/bist30/last_sentiment_cache.json`
- [ ] Restart sonrası F5 skoru 0/215'ten yukarı çıkıyor

**Rollback:**
```bash
git revert HEAD
systemctl restart bist30
```

---

## Gün 1 — Salı 1 Temmuz

### 09:00 TR — Fix 1 Post-Mortem + Fix 2 Deploy Kararı

- [ ] F5 skoru dün gece kontrol: 0 değil mi?
- [ ] `journalctl -u bist30 --since "2026-06-30 18:30"` — exception var mı?
- [ ] Fix 1 stabil → Fix 2 deploy devam

### 09:00 TR — Fix 2 Deploy (Gemini Global Rate Limiter)

**Spec dosyası:** `docs/sprint-3.5-fix2-rate-limiter.md`

```bash
# Lokal
# app.py veya gemini_client.py — flock-based slot reservation
git add .
git commit -m "fix(gemini-rate): flock global rate limiter, replace worker-local lock"
git push origin main

# VPS
git pull origin main
systemctl restart bist30
```

**Smoke (09:10+ TR):**
- [ ] `/health` → 200
- [ ] Lock dosyası oluştu: `ls /tmp/borsapusula_gemini_rate.lock`
- [ ] Gemini 429 hatası yok: `grep -i "429\|rate" /root/bist30/logs/app.log | tail -20`

**Definition of Done:**
- [ ] 4 worker aynı anda 10 RPM'i AŞMIYOR (Gemini log'larında 429 yok)
- [ ] Makro AI özetler normal hızda geliyor

---

### 14:00 TR — F15 Dark/Light Tema Branch Açılış

**Spec dosyası:** `docs/sprint-4-f15-dark-theme.md`

```bash
git checkout -b feature/f15-dark-light-theme
```

**W1 scope:**
- CSS variable seti tamamla (16 token)
- `data-theme="light"` toggle mekanizması
- `localStorage` persist
- `prefers-color-scheme` auto-detect
- Chart adapter katmanı (lightweight-charts renk güncelleme)

**Definition of Done (F15):**
- [ ] Dark mode: mevcut görünüm korunuyor
- [ ] Light mode: WCAG AA kontrast (4.5:1 text, 3:1 UI)
- [ ] Tema değiştirince sayfa reload yok
- [ ] localStorage'a kayıt → refresh sonra korunsun
- [ ] Chart renkleri tema ile değişiyor

---

## Gün 2 — Çarşamba 2 Temmuz

### 09:00 TR — F11 Push Notification Branch Açılış

**Spec dosyası:** `docs/sprint-4-f11-push-notification.md`

```bash
git checkout -b feature/f11-push-notification
```

**W1 scope (4 frontend adım):**
1. Permission request flow — "Bildirim Al" butonu + browser permission
2. Subscribe → `POST /api/push/subscribe` bağlantısı
3. Hisse bağlama UI — hangi tickerlar için bildirim
4. Silent fallback — izin reddedilirse graceful degrade

**Mevcut altyapı (değişmeden kullan):**
- `static/sw.js:87-119` — push handler
- `app.py:126-139` — VAPID key
- `app.py:9231-9253` — subscribe endpoint
- `app.py:9256-9268` — unsubscribe endpoint

**Definition of Done (F11):**
- [ ] AKBNK AL sinyali → push bildirim 30s içinde teslim
- [ ] Kullanıcı bildirimi kapatabilir
- [ ] Seans dışı push gönderilmiyor (10:00-18:00 TR penceresi)
- [ ] iOS fallback: "Web push iOS 16.4+ gerektirir" uyarısı

---

## Hız Göstergesi

| Gün | Hedef | Durum |
|---|---|---|
| Pzt | Cutover + Smoke + Fix 1 | — |
| Sal | Fix 2 + F15 branch açılış | — |
| Çar | F11 branch açılış + F15 ilerleme | — |
| Per | F15 PR hazır + F11 %50 | — |
| Cum | F15 deploy + F11 PR hazır | — |
| Cmt | F11 deploy + W2 hazırlık | — |

---

## Bağımlılıklar & Kilitleyiciler

| Adım | Bağımlı | Risk |
|---|---|---|
| Fix 2 | Fix 1 stabil (en az 12h) | Düşük |
| F15 deploy | Fix 2 stabil | Orta — tema restart gerektiriyor |
| F11 deploy | F15 sonrası (seans dışı) | Orta — SW kaydı restart |

---

## Port / Servis Kısıtları (DEV Hatırlatma)

- **Port 8004 YASAK** — paper-bot portu
- **paper-bot.service DOKUNMA**
- **/opt/polymarket/bot/* DOKUNMA**
- **10:00-18:00 TR arası prod restart YASAK** (BIST seans)
- Deploy saat penceresi: 09:00 (seans öncesi) veya 18:30+ (seans sonrası)
