# Sprint 4 Feature Katalog — F11-F15 (Post-Cutover Backlog)

**Tarih:** 28 Haziran 2026  
**Durum:** Brainstorm Draft (CPO onayı bekleniyor)  
**Önkoşul:** Bundle 17 cutover tamamlanmış (30 Haz 09:30 TR)

---

## Özet Tablo

| ID | Feature | Mantık | Impact | Effort | Öncelik |
|----|---------|--------|--------|--------|---------|
| F11 | Push Notification (Web) | Kullanıcı seçtiği hisselere sinyal gelince tarayıcı push bildirim alır | ★★★★ Yüksek — retention driver; kullanıcı siteye gelmeden haberdar olur | M — Service Worker + VAPID key + backend queue + UI izin akışı | P1 |
| F12 | AI Portföy Önerisi | Kullanıcının portföyünü analiz ederek "sat / tut / ekle" önerileri sunar (Gemini + sinyal verisi) | ★★★★★ En yüksek — monetization anchor; premium feature kapısı | L — portföy okuma + Gemini prompt mühendisliği + rate limit | P2 |
| F13 | Sosyal Sinyal Feed | Birden fazla kullanıcının "izledim / aldım / sattım" hareketlerini anonim feed'de göster | ★★★ Orta — community building; viral sharing potansiyeli | L — user action logging + feed aggregation + privacy layer | P3 |
| F14 | Backtest History & Karşılaştırma | Farklı tarih aralıkları + parametre kombinasyonları için backtest sonuçlarını kaydet ve karşılaştır | ★★★ Orta — power user retention; şu anda backtest tek parametreli ve geçici | M — backtest endpoint genişletme + history storage + comparison UI | P2 |
| F15 | Dark/Light Tema Toggle | Kalıcı tema seçimi (localStorage persist) + sistem tercihi auto-detect | ★★★ Orta — UX polish; düşük teknik risk | S — CSS variable toggle + system preference media query + preference save | P1 |

---

## Detay

### F11 — Push Notification (Web)
**Mantık:**  
Kullanıcı bir hisseyi izlemeye alır (virtual portfolio veya watchlist). O hisseye AL/SAT sinyali üretildiğinde Service Worker + VAPID push ile tarayıcıya bildirim gider. Seans saatleri dışında sessizlik modu.

**Impact:**  
- Kullanıcı siteye gelmeden sinyali alır → CTR artışı
- Retention driver #1 (push subscriber list = captive audience)
- Rakip ayrışım: çoğu Türk fintech uygulaması SMS odaklı, web push nadir

**Effort:**  
- Backend: `/api/push/subscribe` endpoint, VAPID key yönetimi, bildirim gönderim kuyruğu
- Frontend: Service Worker PermissionRequest flow, bildirim tercihi UI
- Infra: Push queue (Redis veya in-memory + disk persist yeterli ilk MVP'de)
- Risk: iOS Safari Web Push desteği iOS 16.4+ (kapsam sınırlı, mobil önce Android)

**Kabul kriterleri:**  
- AKBNK AL sinyali → push bildirim 30s içinde teslim
- Kullanıcı bildirimi kapatabiliyor
- Seans dışı push gönderilmiyor

---

### F12 — AI Portföy Önerisi
**Mantık:**  
Kullanıcı virtual portfolio'suna hisse ekler. Gemini + mevcut sinyal verisi + makro context ile "portföy yorumu" üretir: "THYAO pozisyonunuz aşırı ağırlıklı, sektör riskine dikkat" tarzında.

**Impact:**  
- Premium özellik kapısı — freemium model için doğal paywall
- Ortalama oturum süresi artışı (kişiselleştirilmiş içerik = daha fazla engagement)
- Farklılaşma: ChatGPT prompt arka planda ama BorsaPusula UI'ında seamless

**Effort:**  
- Gemini prompt: portföy kompozisyonu + sinyal durumu + makro özet → yorum
- Rate limit: leader-only, günlük veya isteğe bağlı refresh
- UI: "Portföyünü Analiz Et" butonu + overlay sonuç
- Risk: Gemini maliyet yönetimi (max_tokens kap + explicit disclaimer)

**Kabul kriterleri:**  
- 3 hisseli portföy için 5s içinde yorum
- Yasal disclaimer her yanıtta mevcut
- Gemini başarısız → "analiz şu an mevcut değil" graceful fallback

---

### F13 — Sosyal Sinyal Feed
**Mantık:**  
Kullanıcılar "Bu sinyali takip ediyorum" / "Aldım" / "Sattım" şeklinde anonim aksiyon bırakabilir. Ana sayfada veya /gundem'de "en çok takip edilen sinyaller" agregat olarak görünür.

**Impact:**  
- Community building — yatırımcı topluluğu hissi
- Social proof signal — "23 kişi bu sinyali izliyor" → güven artışı
- Viral: paylaşılabilir "Bu hafta en çok takip edilen" özeti

**Effort:**  
- Backend: user action log (anonim/token-based), aggregation endpoint
- Frontend: bir hisse sayfasında oy/takip butonu + counter
- Privacy: IP hash, rate limit (spam koruması), no PII
- Risk: manipülasyon riski (pump sinyali viral yapma) → threshold filtering gerekli

**Kabul kriterleri:**  
- Aksiyon → 60s içinde aggregate'e yansır
- Minimum 5 kullanıcı eşiği (gizlilik)
- Manipülasyon limiti: aynı IP 24h içinde max 10 aksiyon

---

### F14 — Backtest History & Karşılaştırma
**Mantık:**  
Mevcut backtest tek bir ticker + fixed 20-gün forward dönem için çalışır. F14 ile: farklı forward period (10/20/40 gün), farklı tarih baseline ve iki ticker yan yana karşılaştırma gelir.

**Impact:**  
- Power user retention: analistler strateji testleri yapabilir
- "Hangi parametre daha iyi çalışmış?" sorusu yanıtlanabilir hale gelir
- Veri güveni artar — kullanıcı metodolojiye erişir

**Effort:**  
- Backend: backtest endpoint'e `fwd_days` ve `base_date` param ekle, result storage (JSON per ticker)
- Frontend: parametre seçici + çoklu sonuç overlay grafiği
- Disk: backtest history JSON (hafif, 215 ticker × 3 param = ~650 dosya)
- Risk: hesaplama yükü (yineleme optimizasyonu gerekebilir)

**Kabul kriterleri:**  
- AKBNK 10 gün vs 20 gün backtest yan yana görünür
- Hesaplama 3s altı
- Geçmiş sonuçlar service restart sonrası korunuyor

---

### F15 — Dark/Light Tema Toggle
**Mantık:**  
Site şu an dark-mode-first. Bazı kullanıcılar light mode tercih ediyor. `prefers-color-scheme` media query + manuel toggle + localStorage persist. Sistem tercihi auto-detect, override mümkün.

**Impact:**  
- UX polish — küçük ama gelen talep var
- Accessibility: bazı kullanıcılar yüksek kontrast light tercih eder
- Professional impression artışı

**Effort:**  
- CSS: tüm hardcoded renkleri CSS variables'a çek (kısmen yapılmış, tamamlama gerekiyor)
- JS: 10 satır toggle + localStorage
- Risk: mevcut renk sistemi CSS var kullanıyor mu kontrol (görünüşe göre kısmen)

**Kabul kriterleri:**  
- Toggle tıklanınca tüm sayfada anlık tema değişimi
- Sayfa yenileme sonrası tercih korunuyor
- Sistem auto-detect ilk ziyarette çalışıyor

---

## Öneri Sıralaması

1. **F15** (tema) + **F11** (push): Paralel, low-risk UX sprint — 1 hafta
2. **F14** (backtest): Güçlü veri feature, medium effort — 1 hafta
3. **F12** (AI portföy): Premium anchor, yüksek impact — 2 hafta
4. **F13** (sosyal feed): Community bet, infra cost var — Sprint 5'e bırak

---

*Bu katalog DEV brainstorm draft. CPO onayı sonrası resmi backlog'a girer.*
