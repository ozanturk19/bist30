# Master Plan v2 — 1 HAFTA SIKIŞTIRMA (DEV Hız Bazlı)

**Onay:** Ozan (28 Haz 20:25 TR): "uzak tarihler koyma, 14 Temmuz'a kadar 10 kere biter, atıl zaman yasak, 1 haftada"  
**Revize:** v1 6 hafta → **v2 1 hafta (Pzt 30 Haz - Paz 6 Tem)**  
**Hız Bazı:** DEV son 24h'de 14 task tamamladı (~50dk/task). Sprint 3.5 (10) + Sprint 4 (9) = 19 task → ~16 saat aktif iş. Paralelize + 24/7 = **1 hafta gerçekçi.**

---

## ANA PRENSIP: PARALELIZE + ATIL ZAMAN YASAK

| Eski (v1) | Yeni (v2) |
|---|---|
| Sequential madde-madde | Paralel branch'ler |
| Sprint 3.5 4 alt-sprint (Sal-Çar-Per-Cum) | Sprint 3.5 TEK Sal sığar |
| Sprint 4 W1 → W7 (6 hafta) | Sprint 4 W1+W2+W3 paralel (Per-Cum-Paz) |
| Her madde tek deploy window | Birleşik daily deploy |
| 24h sustained wait | 4h sustained yeterli |

---

## YENİ TAKVIM (HAFTA 1)

### Pzt 30 Haziran — Cutover + Hot-Fix

| Saat | Aksiyon |
|---|---|
| 09:00 | Hetzner snapshot (Ozan) |
| 09:30 | Cutover deploy (idempotent) |
| 10:00 | Ozan vize + sustain |
| 18:00 | DEV pre-deploy MSG (Fix 1 + Nav + smoke) |
| 18:30 | Hot-fix deploy + 5 katmanlı test |
| 19:30 | Ozan vize |
| **19:30-23:59** | **Sprint 3.5 TAM SPRINT BAŞLA — Codex M1-M8 + Fix 2 PARALEL branch** |

### Sal 1 Temmuz — Sprint 3.5 TAM GÜN

**Paralel 3 branch:**
- `fix/codex-m1-m2-m3` — Corruption RCA + yfinance + sanity guard
- `fix/codex-m4-m5-fix2` — Chart guard + health quality + Gemini rate limiter
- `fix/codex-m6-drift` — Health regression (KRİTİK)

| Saat | Aksiyon |
|---|---|
| 09:00-12:00 | DEV 3 branch paralel kod yazımı |
| 12:00-13:00 | 5 katmanlı test (branch by branch) |
| 13:00-13:30 | CPO vize + merge |
| 13:30 | Tek deploy (3 branch birleşik) |
| 14:00-18:00 | Codex M7+M8 + sustain gözlem |
| 18:30 | M7+M8 deploy |
| 19:00 | Sprint 3.5 wrap + kabul kriterleri test |

**Sprint 3.5 BİTTİ:** Sal 1 Tem 19:00 (~24h Pzt cutover sonrası)

### Çar 2 Temmuz — Sprint 4 W1 + W2 BAŞLA

**Paralel 3 branch:**
- `feature/f15-dark-theme` (S effort, 3h kod)
- `feature/f11-push-notification` (M effort, 6-8h kod)
- `feature/spec-018-heatmap-v2` (L effort, 12-16h kod, flagship)

| Saat | Aksiyon |
|---|---|
| 09:00-18:00 | DEV 3 branch paralel |
| 18:30 | F15 deploy (ilk biten) + test |
| 22:00 | F11 deploy (ikinci biten) + test |

### Per 3 Temmuz — Sprint 4 W2 (SPEC-018 + SPEC-017 başla)

| Saat | Aksiyon |
|---|---|
| 09:00-18:00 | DEV SPEC-018 finalize + SPEC-017 başla paralel |
| 18:30 | SPEC-018 Heatmap v2 DEPLOY (FLAGSHIP) + 5 katmanlı test |
| 19:30 | Ozan vize + browser walkthrough |
| 22:00 | SPEC-017 W2 ilerleme |

### Cum 4 Temmuz — Sprint 4 W3 + W4

**Paralel 2 branch:**
- `feature/spec-017-hisse-detay-v2` (L effort, finalize)
- `feature/spec-019-tarama-premium` (M effort)

| Saat | Aksiyon |
|---|---|
| 09:00-18:00 | DEV 2 branch finalize |
| 18:30 | SPEC-017 deploy + test |
| 21:00 | SPEC-019 deploy + test |

### Cmt 5 Temmuz — Sprint 4 W5 + W6

**Paralel 2 branch:**
- `feature/f14-backtest-history` (M effort)
- `feature/f12-ai-portfoy` (L effort başla)

| Saat | Aksiyon |
|---|---|
| 10:00-18:00 | DEV 2 branch |
| 18:30 | F14 deploy + test |
| 22:00 | F12 finalize |

### Paz 6 Temmuz — Sprint 4 W7 + Sprint 5 başla

| Saat | Aksiyon |
|---|---|
| 10:00-15:00 | DEV F12 deploy + test |
| 15:00-22:00 | F13 Sosyal Sinyal başla + SPEC-021 trailer kayıt (SPEC-018 sonrası materyal hazır) |
| 22:30 | F13 deploy (eğer biterse) + test |

**SPRINT 4 + SPRINT 5 (BÜYÜK ÖLÇÜDE) BİTTİ:** Paz 6 Tem 23:00 (~1 hafta)

---

## PARALEL ÇALIŞMA KURALLARI

### DEV
- 24/7 continuous mode
- Multiple branch parallel (3-4 branch aynı anda)
- Saatlik heartbeat (eskiden 60dk → şimdi 45dk)
- Test ile birlikte git (test PASS olmadan merge yok)

### CPO
- 30dk poll cycle (eskiden 5/20dk → daha sık)
- Pre-deploy MSG için 5dk vize (eskiden 10dk)
- Browser walkthrough deploy sonrası HEMEN
- Ozan ile günlük 1-2 vize toplantısı (sabah + akşam)

### Test
- 5 katmanlı test PARALELiz: smoke + lighthouse + visual aynı anda
- Sustained gözlem 4h yeterli (24h değil)
- Visual regression baseline her hafta yenilenir

---

## RİSK MİTİGASYON

| Risk | v1 plan | v2 plan |
|---|---|---|
| Paralel branch conflict | Sequential korur | Branch isolation + daily merge tag |
| Test atıl zaman | Sustained 24h gözlem | 4h yeterli + rollback hazır |
| DEV burnout | 24/7 OK | 24/7 OK (DEV agent) |
| CPO overload | 5dk poll | 30dk poll yeterli (otomatik DEV-CPO döngü olgun) |
| Rollback frekansı | Düşük | Orta (paralel deploy → bug ihtimali artar) |
| Sprint 3.5 stabilite | Slow + güvenli | Fast + 5-katmanlı test PASS şart |

---

## BAŞARI METRIKLERI (DEGISMEDI)

- CLS < 0.1 (Pzt hot-fix sonrası)
- 502/504 / 24h = 0
- public_smoke 5/5 (Sal 3.5c sonrası)
- /api/data drift = 0 (Sprint 3.5 sonrası)
- SPEC-018 SVG render < 500ms (Per 3 Tem)
- Sprint 4 W1-W7 + Sprint 5 → **Pzt 6 Tem 23:00 hazır**

---

## ATIL ZAMAN AVCILIĞI

| Atıl Zaman Kaynağı | Çözüm |
|---|---|
| Sequential madde sıralaması | Paralel branch (3-4 aynı anda) |
| Cron polling cycle bekleme | Event-driven (mailbox/git push trigger) |
| Sustained test 24h | 4h yeterli (memory önceki ALERT history baz) |
| Daily deploy window 1x | Saatlik mini-deploy window (her 4-6h bir) |
| Ozan vize bekleme | Saat dilimi ile uyum + verbose pre-deploy MSG |
| CPO 5dk poll fixed | 30dk poll + event-driven dispatch yeterli |

---

## DEV'E NET MESAJ (CPO-900)

DEV: 6 haftalık planı **1 haftaya** sıkıştırıyoruz. Paralel branch + 24/7 + daily deploy. Pzt 30 Haz başlangıç, Paz 6 Tem **Sprint 3.5 + Sprint 4 + Sprint 5 büyük ölçüde bitiyor.** Atıl zaman = boşa zaman. 1 task / saat ortalama hız sürdür.

---

## NOTLAR

- Bu plan v2 Ozan onayı sonrası aktif (28 Haz 20:25 TR)
- v1 docs/ altındaki dosyalar tarihsel referans olarak kalır
- Memory ders: deadline'ı DEV gerçek hızı bazlı koy, "rahatlık payı" = atıl zaman
- Sustain mode = backlog dolu (bu plan boyunca asla boş kalmaz)
