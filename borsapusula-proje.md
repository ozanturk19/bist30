# BorsaPusula — Kapsamlı Proje Dokümantasyonu

> Son güncelleme: Nisan 2026  
> Canlı URL: https://borsapusula.com  
> VPS: Hetzner — 135.181.206.109

---

## 1. Proje Özeti

BorsaPusula, BIST100 hisselerini **Supertrend + ADX + EMA12/99** algoritmasıyla analiz eden, günlük güncellenen, ücretsiz bir teknik analiz sinyal panelidir. Rakip olmayan niş: Türkçe · Algoritmik · Modern UI · Ücretsiz.

---

## 2. Altyapı ve Stack

### Sunucu
| Bileşen | Detay |
|---------|-------|
| VPS | Hetzner Cloud — 135.181.206.109 |
| OS | Ubuntu (root erişim) |
| Web sunucu | Nginx (reverse proxy, port 80 → 8003) |
| SSL | Cloudflare proxy (CF tarafında HTTPS) |
| Uygulama | Gunicorn + Gevent (1 worker, port 8003) |
| Process yöneticisi | systemd — `bist30.service` |
| Python | Python 3.12, virtualenv `/root/bist30/venv/` |

### Teknoloji Stack
| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.12 · Flask 2.3+ · Gunicorn + Gevent |
| Veri kaynağı | yfinance (Yahoo Finance) |
| Teknik analiz | pandas + numpy (custom Supertrend, ADX, EMA) |
| Frontend | Vanilla JS · HTML5 · CSS3 (framework YOK) |
| Grafikler | LightweightCharts v4 (TradingView OSS) |
| Canlı fiyat | SSE (Server-Sent Events) |
| AI açıklama | Google Gemini 2.5 Flash API |
| Bildirimler | SMTP email (Brevo/custom) · Telegram Bot API |
| Yedekleme | GitHub (ozanturk19/bist30) |

### Ortam Değişkenleri (systemd service)
```ini
GEMINI_API_KEY=...         # Google AI Studio
TELEGRAM_BOT_TOKEN=...     # Telegram Bot
TELEGRAM_CHANNEL_ID=...    # Kanal ID
SMTP_HOST=...              # Brevo: smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=...              # Brevo kayıt emaili
SMTP_PASS=...              # Brevo SMTP key
SMTP_FROM=BorsaPusula <noreply@borsapusula.com>
```

---

## 3. Dosya Yapısı

```
/root/bist30/              (VPS)
/Users/mac/Bist ve BTC/Bist30/  (Local Mac)
│
├── app.py                 # Ana Flask uygulaması (~2400 satır)
├── backtest.py            # Backtest motor modülü
├── blog_content.py        # Blog makaleleri (15 makale)
├── requirements.txt       # Python bağımlılıkları
├── subscribers.json       # Email aboneleri (local disk, gitignore'da DEĞİL)
├── baslat.sh              # Manuel başlatma scripti
│
├── templates/             # Jinja2 HTML şablonları (14 dosya)
│   ├── index.html         # Ana sayfa — sinyal tablosu + hero panel
│   ├── hisse.html         # Hisse detay — grafik + indikatörler + geçmiş
│   ├── ozet.html          # Günlük özet — AL/SAT/BEKLE grupları
│   ├── sinyal_performans.html  # Backtest sonuçları
│   ├── portfolio.html     # Portföy takibi (localStorage)
│   ├── metodoloji.html    # Algoritma açıklaması
│   ├── sektor_harita.html # Sektör ısı haritası
│   ├── bilanco_takvimi.html # Bilanço açıklama tarihleri
│   ├── blog.html          # Blog listesi
│   ├── blog_article.html  # Blog makale şablonu
│   ├── hakkinda.html      # Hakkında
│   ├── gizlilik.html      # Gizlilik + KVKK
│   ├── iletisim.html      # İletişim
│   └── yasal.html         # SPK yasal uyarı
│
├── static/
│   ├── favicon.svg
│   ├── logo.svg
│   ├── lightweight-charts.min.js
│   ├── manifest.json      # PWA manifest
│   ├── sw.js              # Service Worker (PWA)
│   ├── icon-192.png
│   └── icon-512.png
│
└── .claude/
    └── launch.json        # Claude Code local dev config (port 5557)
```

---

## 4. Sinyal Motoru — Algoritma

### Çekirdek Metodoloji
Üç kriterin **tamamı** aynı yönde olduğunda sinyal üretilir:

```
GÜÇLÜ TREND (AL)  = Supertrend ▲  AND  ADX ≥ 25  AND  EMA12 > EMA99
ZAYIF TREND (SAT) = Supertrend ▼  AND  ADX ≥ 25  AND  EMA12 < EMA99
BELİRSİZ (BEKLE)  = Yukarıdaki koşullar sağlanmıyor
```

### Parametreler
| İndikatör | Parametre | Açıklama |
|-----------|-----------|----------|
| Supertrend | period=10, multiplier=3 | Yön belirleme |
| ADX | period=14, threshold=25 | Trend gücü filtresi |
| EMA Kısa | 12 bar | Hız göstergesi |
| EMA Uzun | 99 bar | Uzun dönem trend |
| Haftalık EMA | 20 bar (haftalık) | Gate filtresi |
| Stop Loss | ATR tabanlı | Supertrend alt/üst bandı |

### Ek Göstergeler (bilgilendirici)
- RSI 14 (aşırı alım/satım göstergesi)
- Hacim oranı (vol_ratio × ortalama)
- Haftalık trend yönü (weeky_trend gate)
- 3-bar onay (confirmed flag)

### Veri Akışı
```
Yahoo Finance (yfinance)
    ↓ ~145 hisse, günlük OHLCV
_calc_signals() — her hisse için
    ↓ signal / signal_price / sl_level / bull_score / indicators
_cache["data"] — thread-safe lock
    ↓ SSE stream → browser live prices
    ↓ _notify_signal_changes() → email + Telegram
```

---

## 5. API Endpoints

| Method | URL | Açıklama |
|--------|-----|----------|
| GET | `/` | Ana sayfa |
| GET | `/api/data` | Tüm hisse sinyalleri (JSON) |
| GET | `/api/stream` | SSE canlı fiyat akışı |
| POST | `/api/refresh` | Veriyi yeniden çek ⚠️ korumasız |
| GET | `/api/chart` | XU030 grafik verisi |
| GET | `/hisse/<ticker>` | Hisse detay sayfası |
| GET | `/api/hisse/<t>/chart` | Hisse grafik + sinyal geçmişi |
| GET | `/api/hisse/<t>/mtf` | Çoklu zaman dilimi sinyalleri |
| GET | `/api/hisse/<t>/fundamentals` | Temel analiz verisi |
| GET | `/api/hisse/<t>/news` | AI haber özeti (Gemini) |
| GET | `/api/hisse/<t>/signal-explanation` | AI sinyal açıklaması |
| GET | `/api/backtest` | Backtest sonuçları |
| POST | `/api/backtest/run` | Backtest başlat ⚠️ korumasız |
| POST | `/api/subscribe` | Email abone ol |
| GET | `/unsubscribe/<token>` | Abonelik iptali |
| POST | `/api/telegram/test` | Telegram test mesajı |
| GET | `/sinyal-performans` | Backtest sonuç sayfası |
| GET | `/ozet` | Günlük özet |
| GET | `/portfolio` | Portföy takip |
| GET | `/sektor-harita` | Sektör ısı haritası |
| GET | `/bilanco-takvimi` | Bilanço takvimi |
| GET | `/blog` | Blog listesi |
| GET | `/blog/<slug>` | Blog makale (15 makale) |
| GET | `/metodoloji` | Algoritma metodoloji |
| GET | `/yasal` | SPK yasal uyarı |
| GET | `/gizlilik` | KVKK gizlilik politikası |
| GET | `/sitemap.xml` | SEO sitemap |
| GET | `/robots.txt` | Crawler kuralları |

---

## 6. Email + Bildirim Sistemi

### Email (SMTP)
- **Altyapı**: Python `smtplib` + SMTP relay (Brevo önerilir)
- **Aboneler**: `subscribers.json` — token, tarih, active flag, tickers
- **Tetikleyici**: Sinyal değişimi → `_notify_email_signal_changes()`
- **Şablonlar**: Welcome email + sinyal değişim email (HTML)
- **Unsubscribe**: Token tabanlı tek tıkla iptal

### Telegram
- **Bot**: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHANNEL_ID` env var
- **Tetikleyici**: Her sinyal değişiminde otomatik mesaj
- **Test**: `/api/telegram/test` endpoint

---

## 7. Frontend Özellikleri

### Ana Sayfa (index.html)
- Dashboard Split layout: %60 XU030 grafiği + %40 hero panel
- Hero panel: Güçlü Trendler / Günün Hareketlileri / Yeni Sinyaller
- Stats bar: animateCounter() cubic ease-out animasyon
- Skeleton loading: shimmer animasyonu (veri gelmeden önce)
- Tick animasyon: fiyat değişiminde yeşil/kırmızı flash
- Filtreler: Tümü / Güçlü Trend / Zayıf Trend / Belirsiz / Bugün
- Gelişmiş screener: ADX gücü / sinyal süresi / hacim / RSI
- Sektör filtreleri (dinamik, 12 sektör)
- Mobil: 768px'de tablo → kart stack dönüşümü
- Sıralama: tüm sütunlarda tıkla sırala
- Alarm sistemi: watchlist + browser notification + fiyat alarmı
- Email abonelik banner

### Hisse Sayfası (hisse.html)
- LightweightCharts 2 yıllık candlestick + EMA overlay + hacim
- Çoklu zaman dilimi (günlük / haftalık / aylık)
- Sinyal mini istatistik satırı (4 kart): toplam / AL / SAT / ort. aralık
- İndikatör durumu + blog help linkleri (Supertrend/ADX/EMA/RSI)
- Sinyal geçmişi tablosu
- AI sinyal açıklaması (Gemini)
- AI haber özeti
- Temel analiz (F/K, PD/DD, etc.)
- KAP / Yahoo Finance / İş Yatırım linkleri

### Diğer Sayfalar
- **Özet**: AL/SAT/BEKLE grupları + giriş fiyatından getiri %
- **Sinyal Performans**: Backtest özet bar + hisse bazlı tablo + aktif sinyaller
- **Portfolio**: localStorage tabanlı takip, NaN-safe summary, uyarı banner
- **Sektör Haritası**: D3.js treemap, renk = sinyal yönü
- **Blog**: 15 eğitim makalesi (Supertrend, ADX, EMA, RSI, vb.)
- **Metodoloji**: TL;DR kart + detaylı algoritma açıklaması

---

## 8. Senkronizasyon Durumu

### ⚠️ KRİTİK: Şu an 3 kopya uyumsuz

```
GitHub (origin/main)     ← 14 commit geride, sprint değişiklikleri YOK
        ↕ uyumsuz
Local Mac (çalışma kopyası) ← EN GÜNCEL ✅ (14 dosya değiştirildi, commit edilmedi)
        ↕ scp ile deploy (git yok)
VPS (/root/bist30/)      ← Local ile yakın ama git yok
```

### Güncel olmayan (git'te commit edilmemiş) dosyalar:
```
app.py
templates/bilanco_takvimi.html
templates/blog.html
templates/blog_article.html
templates/gizlilik.html          ← KVKK email bölümü eklendi
templates/hakkinda.html
templates/hisse.html             ← Sinyal mini stats + blog linkleri
templates/iletisim.html
templates/index.html             ← Skeleton + tick + mobil kart + hero panel
templates/metodoloji.html        ← TL;DR kart
templates/ozet.html              ← Getiri % badge'leri
templates/portfolio.html         ← localStorage uyarı + NaN fix
templates/sektor_harita.html
templates/sinyal_performans.html ← Özet bar + auto-backtest
templates/yasal.html             ← YENİ DOSYA (git'te yok)
```

### Hemen Yapılması Gereken Git Sync:
```bash
cd "/Users/mac/Bist ve BTC/Bist30"

# 1. Hassas bilgi sızdırma riskini kontrol et
git diff app.py | grep -i "key\|pass\|token\|secret"

# 2. Commit
git add templates/ app.py
git add templates/yasal.html   # untracked
git commit -m "feat: Sprint 1+2 — skeleton, mobile cards, sinyal stats, backtest özet, blog links, KVKK, yasal"

# 3. Push
git push origin main

# 4. VPS'de git pull (opsiyonel — şu an scp ile deploy ediliyor)
```

---

## 9. Deploy Süreci

### Mevcut Deploy Yöntemi (scp)
```bash
# Tek dosya deploy
scp templates/index.html root@135.181.206.109:/root/bist30/templates/

# Çoklu dosya deploy
scp templates/*.html root@135.181.206.109:/root/bist30/templates/
scp app.py root@135.181.206.109:/root/bist30/

# Python değişikliği varsa restart şart
ssh root@135.181.206.109 "systemctl restart bist30"

# Template değişikliği için restart (Flask debug=False, şablon cache'i var)
ssh root@135.181.206.109 "systemctl restart bist30"
```

### Önerilen İyileştirme — Git Tabanlı Deploy
```bash
# VPS'de git repo init (bir kez)
ssh root@135.181.206.109
cd /root/bist30
git init
git remote add origin https://github.com/ozanturk19/bist30.git
git pull origin main

# Gelecekte deploy
git push origin main
ssh root@135.181.206.109 "cd /root/bist30 && git pull && systemctl restart bist30"
```

---

## 10. Yedekleme Durumu

| Kopya | Konum | Durum | Risk |
|-------|-------|-------|------|
| Local Mac | `/Users/mac/Bist ve BTC/Bist30/` | ✅ En güncel | Mac çökmesi |
| GitHub | `ozanturk19/bist30` | ⚠️ 14 dosya eksik | Veri kaybı |
| VPS | `/root/bist30/` | ✅ Canlı, scp ile güncel | Sunucu arızası |

### Kritik Kaybolursa Ne Olur?
| Veri | Nerede? | Yedek Var mı? |
|------|---------|---------------|
| app.py (tüm logic) | Local + VPS + GitHub | ✅ (ama GitHub eksik) |
| subscribers.json | Sadece VPS disk | ❌ **TEK KOPYA** |
| Sinyal geçmişi | Sadece RAM cache | ❌ Kaybolabilir |
| Backtest sonuçları | Sadece RAM cache | ❌ Kaybolabilir |
| Blog içerikleri | blog_content.py içinde | ✅ |

### subscribers.json Yedeği İçin:
```bash
# VPS cron ile günlük yedek (önerilir)
ssh root@135.181.206.109
crontab -e
# Şunu ekle:
0 3 * * * cp /root/bist30/subscribers.json /root/backups/subscribers_$(date +\%Y\%m\%d).json
```

---

## 11. Güvenlik Analizi

Detaylar aşağıdaki "Güvenlik" bölümünde. Özet risk tablosu:

| Risk | Seviye | Durum |
|------|--------|-------|
| GitHub'da plaintext token | 🔴 KRİTİK | Hemen değiştir |
| `/api/refresh` korumasız | 🟠 YÜKSEK | Rate limit ekle |
| `/api/backtest/run` korumasız | 🟠 YÜKSEK | Rate limit ekle |
| subscribers.json tek kopya | 🟠 YÜKSEK | Cron yedek kur |
| Rate limiting yok | 🟠 YÜKSEK | Flask-Limiter ekle |
| SSE sınırsız bağlantı | 🟡 ORTA | Max client sınırı |
| subscribers.json gitignore'da yok | 🟡 ORTA | Gitignore'a ekle |
| debug=False ✅ | 🟢 OK | — |
| Nginx security headers ✅ | 🟢 OK | — |
| Token tabanlı unsubscribe ✅ | 🟢 OK | — |
| secrets.token_hex() kullanımı ✅ | 🟢 OK | — |

---

## 12. Ölçeklenme Notları

- **Şu an**: 1 Gunicorn worker, 145 hisse, ~100-500 günlük kullanıcı kapasitesi
- **Darboğaz**: yfinance HTTP çağrıları (145 hisse × ~2 dk)
- **SSE**: Her client 1 bağlantı tutar, >1000 kullanıcıda sorun olabilir
- **Backtest**: RAM-only cache, restart'ta sıfırlanır — Redis ile kalıcı yapılabilir
- **Ölçekleme yolu**: worker sayısını artır → Redis cache → CDN static files

---

## 13. Bakım Komutları

```bash
# Servis durumu
ssh root@135.181.206.109 "systemctl status bist30"

# Log takibi
ssh root@135.181.206.109 "journalctl -u bist30 -f"

# Servis restart (deploy sonrası)
ssh root@135.181.206.109 "systemctl restart bist30"

# Nginx yeniden yükle
ssh root@135.181.206.109 "nginx -t && systemctl reload nginx"

# Abone sayısı
ssh root@135.181.206.109 "python3 -c \"import json; s=json.load(open('/root/bist30/subscribers.json')); print(f'{len(s)} abone, {sum(1 for v in s.values() if v.get(\\\"active\\\")))} aktif')\""

# Backtest tetikle
curl -X POST https://borsapusula.com/api/backtest/run

# Veri yenile
curl -X POST https://borsapusula.com/api/refresh
```

---

## 14. Gelecek Roadmap

### Kısa Vade (1 ay)
- [ ] Email SMTP aktifleştir (Brevo)
- [ ] Git commit + push (14 eksik değişiklik)
- [ ] `/api/refresh` ve `/api/backtest/run` için IP-based rate limiting
- [ ] subscribers.json cron yedek
- [ ] GitHub token'ı değiştir (şu an URL'de plaintext!)

### Orta Vade (2-3 ay)
- [ ] Redis cache (backtest + session kalıcılığı)
- [ ] Kullanıcı kaydı + kişisel watchlist
- [ ] Push notification (PWA)
- [ ] Portföy server-side sync (şu an localStorage only)
- [ ] A/B test altyapısı

### Uzun Vade
- [ ] Premium plan (gelişmiş filtreler, öncelikli bildirim)
- [ ] BIST tüm hisseler (şu an ~145)
- [ ] Opsiyon/vadeli izleme
- [ ] Mobil uygulama (PWA yeterli olabilir)
