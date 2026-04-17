# BIST30 Sinyal Paneli — Proje Yol Haritası

> Hedef: Türkiye'nin en sade, algoritmik, ücretsiz borsa teknik analiz platformu.
> Boş niş: **Türkçe · Algoritmik · Modern UI · Ücretsiz**

---

## Mevcut Durum (Nisan 2026)

| Özellik | Durum |
|---------|-------|
| BIST30 sinyal motoru (ST + ADX + EMA) | ✅ Canlı |
| XU030 endeks grafiği | ✅ Canlı |
| Bireysel hisse sayfaları `/hisse/<ticker>` | ✅ Canlı |
| Canlı fiyat akışı (SSE) | ✅ Canlı |
| Haftalık trend gate | ✅ Aktif |
| SL / Giriş fiyatı gösterimi | ✅ Aktif |
| Sinyal geçmişi (hisse sayfaları) | ✅ Aktif |
| Domain + SSL | ❌ Eksik |
| Google indeksi | ❌ Eksik |

---

## FAZ 1 — Zemin ve SEO Temeli (1-2 Hafta)

**Hedef:** Google'ın siteyi bulması ve indekslemesi.

### 1.1 Domain ve Altyapı
- [ ] Domain al: `borsasinyali.com` / `bistanaliz.com` / `sinyalpanel.com`
- [ ] Nginx reverse proxy kur (port 8003 → 80/443)
- [ ] Let's Encrypt SSL sertifikası (Certbot)
- [ ] www redirect → non-www (ya da tersi), canonical URL
- [ ] Gzip sıkıştırma, HTTP/2

### 1.2 SEO Temelleri
- [ ] Her sayfa için `<title>` ve `<meta description>` (hisse sayfaları zaten var)
- [ ] `sitemap.xml` oluştur ve otomatik güncelle
  ```
  https://borsasinyali.com/
  https://borsasinyali.com/hisse/THYAO
  https://borsasinyali.com/hisse/GARAN
  ... (28 hisse × 2 URL = 56+ sayfa)
  ```
- [ ] `robots.txt` ekle
- [ ] Open Graph / Twitter Card meta tag'ları (sosyal paylaşım önizlemesi)
- [ ] Schema.org `FinancialProduct` markup
- [ ] Google Search Console bağla
- [ ] Google Analytics 4 entegre et
- [ ] Favicon ekle (şu an 404)

### 1.3 Performans
- [ ] Static dosyalar için cache-control header'ları
- [ ] CDN (Cloudflare ücretsiz katman) — DDoS koruması + hız

---

## FAZ 2 — İçerik ve SEO Derinliği (2-4 Hafta)

**Hedef:** Her hisse için Google'da sıraya girmek.

### 2.1 Hisse Sayfaları Geliştirme ✅ (temeli hazır)
Şu an `/hisse/THYAO` sayfası var. Eklenecekler:

- [ ] **Otomatik oluşturulan teknik yorum metni:**
  ```
  THYAO, son 27 gündür AL sinyali veriyor. Supertrend göstergesi yükseliş
  yönünde, ADX 31 ile güçlü trend gücü gösteriyor. EMA12 (14.876) EMA99'un
  (14.054) üzerinde seyrediyor. Haftalık trend yükselen.
  ```
  Bu metin tamamen otomatik, Python'dan template'e geçiyor.
  
- [ ] **52 haftalık yüksek/düşük** (fiyat aralığı barı)
- [ ] **Hacim göstergesi** (grafik altında ayrı pane)
- [ ] **Şirket bilgi kutusu**: Sektör, endeks, açıklama (statik JSON'dan)
- [ ] **KAP son haberleri** (bkz. Faz 3)

### 2.2 Günlük Özet Sayfaları
- [ ] `/ozet/2026-04-08` — Bugünün BIST30 sinyal özeti
  - Kaç AL, kaç SAT, kaç BEKLE
  - Bugün sinyal değişen hisseler
  - Piyasa genel görünümü
  - Google'da "BIST30 sinyalleri bugün" için sıralanır
  
- [ ] `/ozet/haftalik` — Haftalık performans tablosu
  - Sinyal başarı oranları
  
- [ ] Bu sayfalar cron job ile her gün kapanışta otomatik oluşturulur.

### 2.3 Eğitim İçeriği (Statik)
- [ ] `/metodoloji` — Supertrend, ADX, EMA nasıl kullanılır
- [ ] `/hakkinda` — Proje amacı, veri kaynakları
- [ ] Bu sayfalar uzun kuyruk aramalardan trafik çeker:
  - "supertrend nasıl kullanılır"
  - "ADX indikatörü nedir"
  - "bist hisse teknik analiz nasıl yapılır"

---

## FAZ 3 — Veri Zenginleştirme (4-8 Hafta)

**Hedef:** Rakiplerden ayıran içerik katmanı.

### 3.1 KAP Entegrasyonu
- [ ] KAP (Kamuyu Aydınlatma Platformu) API veya scraping
- [ ] Her hisse sayfasında son 5 şirket açıklaması
- [ ] Önemli açıklamalar için bildirim (ör. temettü, SPK kararı)
- [ ] Teknik sinyal + temel haber kombinasyonu → güçlü içerik

### 3.2 BIST100 Kapsamı
- [ ] 28 hisse → 100 hisse
  - Sadece `BIST30 = [...]` listesini genişlet
  - Her şey otomatik çalışır
- [ ] 100 ayrı hisse sayfası = 100 Google sayfası
- [ ] Sektör filtreleme (Bankacılık, Perakende, Enerji vb.)

### 3.3 Döviz ve Kripto (Opsiyonel)
- [ ] USD/TRY, EUR/TRY, XAU/TRY — aynı sinyal motoru, çok yüksek arama hacmi
- [ ] BTC/TRY, ETH/TRY — kripto arama hacmi çok yüksek

---

## FAZ 4 — Etkileşim ve Topluluk (3-6 Ay)

**Hedef:** Kullanıcıları geri getiren katmanlar.

### 4.1 Telegram Kanalı / Botu
```
🟢 THYAO — AL Sinyali
📅 08.04.2026  |  💰 Giriş: 340,50 ₺
🛑 SL: 294,02 ₺ (-14,4%)
📊 Skor: 3/3 (ST + ADX27 + EMA12/99)
🔗 borsasinyali.com/hisse/THYAO
```
- [ ] Python Telegram Bot API → otomatik sinyal gönderimi
- [ ] Kanal büyüyünce organik trafik kaynağına dönüşür

### 4.2 E-posta Bildirimleri
- [ ] Basit e-posta listesi (Mailchimp ücretsiz)
- [ ] Her gün kapanışta: "Bugünün sinyal değişimleri"
- [ ] Hisse bazlı alert: "Takip ettiğin THYAO'da sinyal değişti"

### 4.3 Portföy Takibi
- [ ] Kullanıcı tarayıcı localStorage'da hisseleri kaydeder (backend gerektirmez)
- [ ] "Portföyüm" sayfası → sadece takip edilen hisseler
- [ ] İleride hesap sistemi (kayıt/giriş)

### 4.4 Backtest Sonuçları
- [ ] Mevcut backtest.py'den üretilen performans tablosu
- [ ] Hisse sayfasında: "Bu strateji bu hissede 3 yılda +%47 getirdi"
- [ ] Şeffaflık + güven inşa eder

---

## FAZ 5 — Gelir Modeli (6+ Ay)

| Model | Açıklama | Potansiyel |
|-------|----------|------------|
| **Google AdSense** | İçerik sayfaları yeterince büyüyünce | Düşük-Orta |
| **Premium Abonelik** | Daha fazla hisse, anlık alert, mobil uygulama | Yüksek |
| **Affiliate** | Aracı kurum ortaklıkları (İş Yatırım, Midas, Piapiri) | Orta |
| **API Erişimi** | Diğer geliştiricilere sinyal API'si | Orta |
| **Sponsor İçerik** | Fintech şirketleri için içerik | Proje büyüyünce |

---

## Teknik Borç ve İyileştirmeler

### Kısa Vadeli (Yapılabilir)
- [ ] `_fill_intraday_gaps` her refresh'te çağrılıyor — önbelleğe al, sadece eksik günlerde çalıştır
- [ ] Her hisse için 3 ayrı yfinance çağrısı → batch download ile optimize et
- [ ] Hata durumlarında kullanıcıya bilgi ver (şu an spinner kalıyor)
- [ ] Sayfa yükleme süresi ölçümü ve optimizasyonu
- [ ] Unit test ekle (sinyal motoru doğruluk testleri)

### Orta Vadeli
- [ ] PostgreSQL/SQLite ile sinyal geçmişini kalıcı sakla
- [ ] Statik sayfa üretimi (Flask-Frozen veya HTML export) — daha hızlı yükleme
- [ ] Nginx ile cache — her hisse sayfası 15 dakikada bir cache'lenir
- [ ] Redis ile backend cache (gevent ile uyumlu)

### Uzun Vadeli
- [ ] Mobil uygulama (React Native veya Flutter)
- [ ] Kullanıcı hesapları (Flask-Login + SQLite)
- [ ] Çoklu dil desteği (EN/TR)
- [ ] Makine öğrenmesi tabanlı sinyal skoru

---

## Rakip Analizi

| Platform | Güçlü Yan | Zayıf Yan | Bizim Avantajımız |
|----------|-----------|-----------|-------------------|
| Investing.com | Geniş kapsam | Ağır, reklam yüklü | Hızlı, sade |
| İş Yatırım | Güvenilir | Ücretli, kurumsal | Ücretsiz, algoritmik |
| Finnet/Matriks | Profesyonel | Çok pahalı, karmaşık | Basit, anlaşılır |
| TradingView | Harika grafik | Türkçe BIST sinyali yok | Otomatik sinyal |
| Midas/Piapiri | Modern UI | Sadece aracı kurum | Bağımsız analiz |

---

## Hedef Anahtar Kelimeler (SEO)

### Yüksek Öncelik
- `[HISSE] teknik analiz` (ör. "THYAO teknik analiz")
- `[HISSE] al sinyali` 
- `[HISSE] supertrend`
- `BIST30 sinyalleri`
- `bist teknik analiz`

### Orta Öncelik  
- `supertrend indikatörü nedir`
- `ADX indikatörü borsa`
- `EMA crossover stratejisi`
- `BIST30 günlük analiz`

### Uzun Kuyruk
- `THYAO ne zaman alınır`
- `Garanti hissesi teknik görünüm`
- `BIST30 al sat sinyali`

---

## Başarı Metrikleri

| Metrik | 3 Ay Hedef | 6 Ay Hedef | 1 Yıl Hedef |
|--------|-----------|-----------|------------|
| Aylık ziyaretçi | 1.000 | 10.000 | 50.000 |
| Google'da sıralanan sayfa | 30+ | 100+ | 300+ |
| Telegram abone | 500 | 2.000 | 10.000 |
| E-posta listesi | 200 | 1.000 | 5.000 |
| Aylık gelir | 0 | 500₺ | 5.000₺+ |

---

*Güncelleme: Nisan 2026 — Faz 1 ve Faz 2 temeli tamamlandı (hisse sayfaları aktif)*
