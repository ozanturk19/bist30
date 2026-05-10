# BorsaPusula — Kapsamlı Test Raporu

> **Test tarihi:** 29 Nisan 2026  
> **Test yöntemi:** VPS SSH + canlı API testleri + kaynak kod incelemesi  
> **VPS:** root@135.181.206.109 — Hetzner Helsinki  
> **Versiyon:** app.py 3520 satır (üretim), local backup 2384 satır  

---

## 🖥️ Sistem Durumu

| Metrik | Değer | Durum |
|--------|-------|-------|
| Uptime | 15 gün 23 saat | ✅ |
| RAM | 1.5G / 3.7G (%41) | ✅ |
| Disk | 9.1G / 38G (%26) | ✅ |
| Load Average | 0.17 / 0.32 / 0.35 | ✅ |
| Gunicorn worker CPU | 16.4% (anlık) | ⚠️ |
| Gunicorn worker RSS | 142MB | ✅ |
| Açık bağlantı (port 8003) | 1 | ✅ |

---

## 🛣️ Tüm Route'lar HTTP Durum Kodları

| URL | HTTP | Süre | Durum |
|-----|------|------|-------|
| / | 200 | 5.5ms | ✅ |
| /ozet | 200 | 3.8ms | ✅ |
| /gucu-yuksek | 200 | — | ✅ |
| /tarama | 200 | — | ✅ |
| /metodoloji | 200 | — | ✅ |
| /hakkinda | 200 | — | ✅ |
| /iletisim | 200 | — | ✅ |
| /yasal | 200 | — | ✅ |
| /gizlilik | 200 | — | ✅ |
| /portfolio | 200 | — | ✅ |
| /sinyal-performans | 200 | — | ✅ |
| /sektor-harita | 200 | — | ✅ |
| /bilanco-takvimi | 200 | — | ✅ |
| /blog | 200 | — | ✅ |
| /blog/supertrend-indikatoru-nedir | 200 | — | ✅ |
| /blog/supertrend-nedir | **301** | — | ✅ redirect |
| /hisse/AKBNK | 200 | 6.5ms | ✅ |
| /abd | 200 | — | ✅ |
| /abd/nasdaq | 200 | — | ✅ |
| /abd/sp500 | 200 | — | ✅ |
| /abd/AAPL | 200 | — | ✅ |
| /abd/tarama | 200 | — | ✅ |
| /btc | 200 | 3.8ms | ✅ |
| /eth | 200 | 2.8ms | ✅ |
| /altin | 200 | 6.0ms | ✅ |
| /kripto | 200 | 5.0ms | ✅ |
| /emtialar | 200 | 4.7ms | ✅ |
| /hisse/INVALID123 | **404** | — | ✅ |
| /blog/olmayan-makale | **404** | — | ✅ |
| /gecmissayfa | **404** | — | ✅ |
| **/karsilastir** | **404** | — | ❌ Yok |

---

## 🔌 API Endpoint Testleri

### `/api/data` — Ana Sinyal Verisi
```
stocks: 145 | AL: 36 | SAT: 3 | BEKLE: 106
loading: false | updated: 29.04.2026 18:10:23
```
✅ Çalışıyor  
⚠️ **Başlangıçtan sonra ~3 dakika loading:true kalıyor** (startup latency)  
⚠️ **ADX değeri hiçbir hissede doğrudan field olarak yok** (`adx: null` — nested `indicators.adx.label`'de var ama üst seviyede yok)

**Tam hisse kaydı (ENJSA):**
```json
{
  "ticker": "ENJSA", "price": 122.5, "change_pct": 1.58,
  "signal": "AL", "signal_date": "29.04.2026", "signal_bars": 1,
  "signal_price": 122.5, "sl_level": 113.31,
  "is_new_signal": true, "confirmed": false,
  "bull_score": 3, "bear_score": 0,
  "indicators": {
    "supertrend": {"label": "ST", "value": "LONG", "bull": true},
    "adx": {"label": "ADX 25", "value": "DI+27/DI-15", "bull": true},
    "ema1299": {"label": "EMA12/99", "value": "121/104", "bull": true}
  },
  "rsi": 57.1, "vol_ratio": 0.74, "vol_confirmed": false,
  "atr14": 4.49, "entry_quality": "IDEAL",
  "entry_note": "Sinyal taze (1 bar), fiyat SL'ye yakın — R/R en avantajlı bölge",
  "tp1": 140.88, "tp2": 150.07, "rr_ratio": 2.0,
  "sector": "Enerji", "_mscore": 39
}
```

---

### `/api/macro`
```
XU100: 14311.19 | XU030: 16478.35 | USDTRY: 45.07
EURTRY: 52.75 | BTC: 75022.26 | ALTIN: 4561.10
GUMUS: 71.93 | PETROL: 106.63 | SP500: 7112.14 | NASDAQ: 24551.78
```
✅ 10 sembol hazır, hızlı (2.9ms)  
⚠️ `change_pct_fmt` field'ı yok — frontend formatlamayı kendisi yapıyor olmalı

---

### `/api/tarama`
```
signal=AL&min_adx=25 → count: 35 | süre: <5ms
sector=Bankacılık → count: 11 (AKBNK, CRDFA, ALBRK, VAKBN, GARAN, ...)
```
✅ Çalışıyor, filtreler doğru çalışıyor  
✅ 144 US hisse de tarama kapsamında

---

### `/api/hisse/<ticker>/fundamentals`
```json
AKBNK: {"pe_ratio": 6.7, "pb_ratio": 1.24, "eps": 11.01,
        "market_cap": "383.24 Mrd₺", "revenue": "190.31 Mrd₺",
        "dividend_yield": null, "roe": 20.8, "beta": 0.86}
```
✅ Çalışıyor  
✅ Sanitizasyon aktif (dividend_yield: null, reasonable P/E)

---

### `/api/hisse/<ticker>/chart`
```
ohlc: 500 mum | ema12: 500 | markers: 6 adet (sinyal tarihleri)
Son mum (GARAN): 2026-04-29, high:136.4, close:132.7
```
✅ 500 günlük OHLC, EMA12/99, Supertrend marker'lar, signal_history hepsi var  
✅ Güncelleme zamanı doğru (18:11:31)

---

### `/api/hisse/<ticker>/mtf`
```json
AKBNK: {
  "h4":     {"signal": "BEKLE", "adx": 19.8, "price": 73.8},
  "daily":  {"signal": "BEKLE", "adx": 22.8, "price": 73.7},
  "weekly": {"signal": "BEKLE", "adx": 22.5, "price": 73.7},
  "monthly":{"signal": "AL",   "adx": 34.7, "price": 73.7}
}
```
✅ H4/Günlük/Haftalık/Aylık 4 zaman dilimi çalışıyor

---

### `/api/hisse/<ticker>/news`
```json
{"news": null}
```
❌ **NULL dönüyor — Gemini API 429 rate limit tüm haberleri engelliyor**

---

### `/api/hisse/<ticker>/signal-explanation`
```
BIST hissesi: source: gemini | ok: None | explanation: 208 char (fallback)
AAPL (ABD): source: None | explanation: "" (BOŞ)
```
⚠️ BIST: Fallback metin üretiliyor ama ADX değeri 0 gösteriyor (bug)  
❌ ABD hisseleri: Explanation tamamen boş

---

### `/api/bilanco-takvimi`
```
periods: 5 | updated: 29.04.2026 18:10
```
✅ Çalışıyor

---

### `/api/backtest`
```json
{"status": "computing", "message": "Backtest hesaplanıyor..."}
```
⚠️ Hesaplanıyor durumunda — zaman alıyor olabilir, normal mi kontrol edilmeli

---

### `/api/contact`
```
POST {name, email, subject, message} → {"ok": true}
```
✅ Çalışıyor

---

### `/api/subscribe`
```
İlk kayıt: {"ok": true, "message": "Abonelik başarılı! Onay e-postası gönderildi."}
Tekrar kayıt: {"ok": false, "message": ""}
```
✅ Kayıt çalışıyor  
⚠️ Duplicate abone için mesaj boş — kullanıcıya ne olduğu söylenmiyor

---

### Diğer Altyapı
| Endpoint | Durum |
|----------|-------|
| /robots.txt | ✅ Doğru (Allow: /, Disallow: /api/) |
| /sitemap.xml | ✅ 213 URL |
| /og-image.svg | ✅ 200 |
| /sw.js | ✅ 200 |
| /api/stream (SSE) | ⚠️ Bağlantı kurdu ama veri gelmiyor (seans dışı normal) |

---

## 🐛 Aktif Hatalar

### 🔴 KRİTİK — 1: Gemini API Rate Limit (429) — SÜREGELEN

**Ne oluyor:** Tüm Gemini çağrıları 429 hatası alıyor. Log:
```
[WARNING] get_ai_news(AKBNK): tüm modeller başarısız → negatif cache 5dk
[INFO] Prefetch tamamlandı: 0/18 başarılı
```

**Kullanıcıya etkisi:**
- Haber bölümü tamamen boş veya "Yükleniyor..." takılı
- Sinyal açıklaması fallback metin gösteriyor (AI değil, template)
- ABD hisse sinyal açıklaması tamamen boş

**Kök neden:**  
18 hisse için seri haber prefetch: her 5 saniyede bir, 2 model × 18 hisse = 36 request ~90 saniyede. Google Gemini ücretsiz tier bunu kaldırmıyor.

**Çözüm önerileri:**
```python
# Seçenek 1: Prefetch'i sadece AL sinyalli hisseler için yap (18 → ~5)
# Seçenek 2: Prefetch aralığını 5s → 30s yap (günde 1 kez yeter)
# Seçenek 3: Kullanıcı sayfayı açınca yükle, cache'i 6 saat tut
# Seçenek 4: Gemini API ücretli tiere geç (1K req/gün ücretsiz, daha fazlası ücretli)
```

---

### 🔴 KRİTİK — 2: Sinyal Açıklamasında ADX=0 Hatası

**Ne oluyor:** Fallback sinyal açıklaması "ADX 0 ile zayıf bir yükseliş trendi" yazıyor. Gerçek ADX değeri (ör. ENJSA için ADX 25, AKBNK için ADX 22.8) var ama okunmuyor.

**Kök neden:** `_cache["data"]`'da ADX şu yapıda saklanıyor:
```json
"indicators": {"adx": {"label": "ADX 25", "value": "DI+27/DI-15"}}
```
Ama sinyal açıklama fonksiyonu `signal_data.get("adx", 0)` yapıyor → `None → 0`.

**Fix:**
```python
# app.py — get_ai_signal_explanation() içinde, adx değeri okunan satırı bul:
# Eski:
adx = signal_data.get("adx", 0) or 0
# Yeni:
adx_raw = signal_data.get("adx") or signal_data.get("indicators", {}).get("adx", {}).get("label", "ADX 0")
adx = float(str(adx_raw).replace("ADX ", "")) if "ADX" in str(adx_raw) else float(adx_raw or 0)
```

---

### 🟡 ORTA — 3: Haber API null Dönüyor (JSON Kontrat İhlali)

**Mevcut:** `{"news": null}`  
**Olması gereken:** `{"news": []}` (boş array)  
Null, JavaScript'te `null.map()` → crash yaratır.

**Fix (app.py news endpoint'i):**
```python
return jsonify({"news": news or [], "source": source})
```

---

### 🟡 ORTA — 4: ABD Hisse Sinyal Açıklaması Çalışmıyor

**Durum:** `/api/hisse/AAPL/signal-explanation` → `source: None, explanation: ""`  
Kullanıcı AAPL sayfasında sinyal açıklaması görmüyor. Boş kart render'lanıyor.

---

### 🟡 ORTA — 5: Abonelik Duplicate Mesajı Boş

**Mevcut:** `{"ok": false, "message": ""}` — kullanıcıya boş mesaj  
**Olması gereken:** `{"ok": false, "message": "Bu e-posta zaten kayıtlı."}`

---

### 🟡 ORTA — 6: Log Boyutu 1.1GB

**Durum:** `journalctl --disk-usage: 1.1G`  
Neden: Gemini 429 hataları sürekli loga yazılıyor.

**Fix:**
```bash
journalctl --vacuum-size=200M
# /etc/systemd/journald.conf dosyasına ekle:
SystemMaxUse=200M
```

---

### 🟡 ORTA — 7: Startup Gecikmesi (~3 dakika boş sayfa)

**Durum:** Servis restart sonrası ~3 dakika `loading: true`, stocks: 0.

**Fix:** Restart öncesi son cache'i diske yaz:
```python
# app.py içinde _refresh_data() sonunda:
def _save_cache_to_disk():
    try:
        with open("last_cache.json", "w") as f:
            json.dump(_cache["data"], f)
    except: pass

# Startup'ta:
def _load_cache_from_disk():
    try:
        with open("last_cache.json") as f:
            _cache["data"] = json.load(f)
            _cache["loading"] = False
    except: pass
```

---

### 🟢 KÜÇÜK — 8: GA4 Analytics Yok

Hiçbir template'te `gtag` yok. Hangi sayfaların trafik çektiği görünmüyor.

---

### 🟢 KÜÇÜK — 9: `/karsilastir` Sayfası Yok (404)

Geliştirme planında var ama henüz deploy edilmemiş.

---

### 🟢 KÜÇÜK — 10: /tarama Navigasyonda Görünmüyor

Sayfa var, çalışıyor ama ana menüde link yok. Kullanıcı nasıl bulacak?

---

## ✅ Çalışan Özellikler

| Özellik | Durum |
|---------|-------|
| Ana sinyal tablosu (145 hisse) | ✅ |
| AL/SAT/BEKLE sinyal motoru | ✅ |
| TP1/TP2/RR hesaplama | ✅ |
| Giriş kalitesi (IDEAL/IYI/DIKKATLI/UZAK) | ✅ |
| Stop loss seviyesi | ✅ |
| 500 günlük OHLC grafik | ✅ |
| EMA12/EMA99 grafik üstü | ✅ |
| Supertrend signal markers | ✅ |
| MTF analizi (H4/D/W/M) | ✅ |
| Makro ticker (10 sembol) | ✅ |
| Sektör ısı haritası | ✅ |
| Bilanço takvimi | ✅ |
| Hisse tarayıcı (/tarama) | ✅ |
| ABD piyasası (/abd + /abd/nasdaq + /abd/sp500) | ✅ |
| ABD hisse detay (/abd/AAPL) | ✅ |
| ABD hisse tarama | ✅ (144 US hisse) |
| Kripto sayfaları (BTC/ETH/BNB/SOL) | ✅ |
| Emtia sayfaları (Altın/Gümüş/Petrol/Doğalgaz) | ✅ |
| Blog (27+ makale) | ✅ |
| Blog 301 yönlendirme | ✅ |
| Temel veri (P/E, P/D, ROE...) | ✅ |
| Temel veri sanitizasyonu | ✅ |
| E-posta aboneliği | ✅ |
| İletişim formu (API) | ✅ |
| Portföy (localStorage) | ✅ |
| SSR sinyal (pre-JS) | ✅ |
| sitemap.xml (213 URL) | ✅ |
| robots.txt | ✅ |
| OG image | ✅ |
| Service Worker / PWA | ✅ |
| Rate limiting | ✅ |
| Admin endpoint koruması | ✅ |
| Geçersiz hisse → 404 | ✅ |
| Yanıt süresi | ✅ (<20ms tüm sayfalar) |

---

## 👤 Kullanıcı Gözüyle Değerlendirme

### İlk İzlenim (Yeni Ziyaretçi)
**Güçlü yönler:**
- Sayfa çok hızlı açılıyor. İlk ekran anında geliyor, veri kısa sürede yükleniyor.
- Tasarım profesyonel, karanlık tema güzel. Rakiplerden görsel olarak daha temiz.
- Makro ticker bandı değerli — anlık bağlam veriyor.
- Hisse kartlarında "Güçlü Trend / Zayıf Trend" yeşil/kırmızı renk kodlaması net.
- Ana sayfada sinyal filtresi (AL/SAT/BEKLE) ve sektör filtresi kullanışlı.

**Sorunlu noktalar:**
- Haber bölümü boş geliyor. "Haberler yükleniyor..." durumunda kalıyor. Kullanıcı bunun neden olduğunu anlamıyor — net bir hata mesajı veya fallback içerik olmalı.
- Sinyal açıklamasında "ADX 0" yazması güven kırıcı. Teknik bilgisi olan biri "bu site yanlış veri gösteriyor" diye düşünür.
- ABD hisselerinde sinyal açıklaması tamamen boş kart — neden boş olduğu söylenmiyor.

### Aktif Trader (Günlük Kullanan)
**Güçlü yönler:**
- MTF (H4/Günlük/Haftalık/Aylık) analizi rakiplerde nadir. Çok değerli özellik.
- TP1/TP2/SL seviyeleri somut. R/R oranı (2.0:1) profesyonel.
- Giriş kalitesi (IDEAL vs UZAK) sinyalin ne zaman verildiğini anlamayı kolaylaştırıyor.
- /gucu-yuksek sayfası aktif trader için ideal başlangıç noktası.
- 145 hisse + ABD hisseleri geniş kapsam.

**Sorunlu noktalar:**
- Hisse chart'ındaki signal_history marker'ları (ok işaretleri) üzerine gelin tooltip yok. "Bu AL sinyalinde kaç gün sonra ne oldu?" sorusu cevaplanmıyor. Tıklanabilir/tooltip olmalı.
- /tarama navigasyonda yok. Aktif trader için en güçlü araç gizli.
- "Onaylanmış sinyal" ile "taze sinyal" farkı net değil. `confirmed: false` ne demek? UI'da açıklama yok.
- Portföy her tarayıcıda baştan başlıyor (localStorage sınırı). Farklı cihazlarda senkronizasyon yok.

### Pasif Takipçi (Ayda 1-2 Bakan)
**Güçlü yönler:**
- E-posta aboneliği var, sinyal değişiminde mail geliyor.
- Blog makaleleri eğitici.
- Bilanço takvimi kullanışlı — kimin ne zaman sonuç açıkladığı tek yerde.

**Sorunlu noktalar:**
- Toplam 4 abone endişe verici. Abonelik flow'u (butonu, formu, onay maili) A/B test edilmeli.
- Blog'da "bu makalenin ilgili olduğu hisseyi" görmek istiyorum — AKBNK üzerine makale varsa hisse sayfasında link olmalı.

### SEO / Google Bakış Açısı
- sitemap.xml 213 URL ✅
- robots.txt doğru ✅
- OG tags + schema.org Article + BreadcrumbList ✅
- **FAQPage schema yok** → Google genişletilmiş snippet fırsatı kaçıyor
- **GA4 yok** → hangi sayfaların trafik aldığı bilinmiyor, içerik stratejisi kör çalışıyor
- /abd, /kripto, /emtialar gibi yeni büyük sayfalar sitemap'te var mı kontrol edilmeli

---

## 🚀 Keşfedilen Yeni Özellikler (Bu Testte Görülen)

Önceki raporlarda eksik olduğu düşünülen birçok özellik VPS'te aktif. **Lokal kod üretimden 1136 satır geride:**

| Özellik | Lokal | VPS Üretim |
|---------|-------|------------|
| `/tarama` hisse tarayıcı | ❌ | ✅ |
| `/abd` ABD piyasası (NASDAQ/SP500/hisseler) | ❌ | ✅ |
| `/btc`, `/eth`, `/kripto` | ❌ | ✅ |
| `/altin`, `/emtialar` | ❌ | ✅ |
| `/api/contact` iletişim formu | ❌ | ✅ |
| `/api/chart/BTC` vb. varlık chart | ❌ | ✅ |
| ABD hisse grafikleri (/api/chart/us/<ticker>) | ❌ | ✅ |
| US hisse tarama | ❌ | ✅ |
| app.py satır sayısı | 2384 | 3520 |

**Aksiyon:** Lokal backup `/Users/mac/Bist ve BTC/Bist30/app.py` güncel değil. VPS'ten çekilmeli.

---

## 📋 Öncelik Listesi

### 🔴 Bu Hafta — Bug Fix

| # | Bug | Efor | Etki |
|---|-----|------|------|
| 1 | Gemini 429 — prefetch stratejisini değiştir | 2 saat | Çok Yüksek |
| 2 | ADX=0 bug'ı sinyal açıklamada fix et | 30 dk | Yüksek |
| 3 | `{"news": null}` → `{"news": []}` | 10 dk | Orta |
| 4 | ABD hisse sinyal açıklaması boş — düzelt | 2 saat | Orta |
| 5 | Duplicate abone mesajı boş — ekle | 10 dk | Düşük |
| 6 | Log rotation ekle (1.1GB → 200MB) | 15 dk | Orta |

### 🟡 Bu Ay — İyileştirme

| # | Özellik | Efor | Etki |
|---|---------|------|------|
| 7 | GA4 analytics ekle (tüm template'ler) | 1 saat | Yüksek |
| 8 | Startup cache (restart sonrası boş sayfa fix) | 3 saat | Orta |
| 9 | Blog FAQPage schema | 3 saat | Yüksek (SEO) |
| 10 | /tarama navigasyona ekle | 30 dk | Yüksek |
| 11 | Sinyal marker tooltip (grafik üstü) | 4 saat | Yüksek (UX) |
| 12 | "confirmed: false" açıklaması UI'da | 1 saat | Orta |
| 13 | Lokal kodu VPS ile senkronize et | — | Kritik |

### 🟢 Sonraki Sprint

| # | Özellik | Efor | Etki |
|---|---------|------|------|
| 14 | /karsilastir hisse karşılaştırma | 2 gün | Orta |
| 15 | /ozet/<tarih> geçmiş özet | 1 gün | Orta |
| 16 | Blog ↔ Hisse bağlantısı | 3 saat | Orta |
| 17 | Portföy sunucu taraflı (token bazlı) | 2 hafta | Orta |

---

## 📊 Genel Skor

| Kategori | Puan | Not |
|----------|------|-----|
| Altyapı Kararlılığı | 8/10 | 15 gün uptime, hızlı response |
| API Doğruluğu | 6/10 | ADX=0 bug, news null, ABD açıklama boş |
| UI/UX | 7/10 | Temiz tasarım, bazı eksik geri bildirimler |
| Özellik Zenginliği | 9/10 | BIST+ABD+kripto+emtia+tarama kapsamlı |
| SEO Altyapısı | 7/10 | Schema var, GA4 yok, FAQPage yok |
| Performans | 10/10 | <20ms tüm sayfalar, cache'ler hazır |
| **Genel** | **7.8/10** | Solid proje, Gemini 429 çözülmeli |

---

*Test: 29 Nisan 2026 — VPS SSH ile canlı test. Proje bir önceki rapora göre ciddi ölçüde büyüdü (ABD, kripto, emtia, tarama). Temel acil sorun Gemini rate limit; bu çözüldüğünde kullanıcı deneyimi önemli ölçüde iyileşecek.*
