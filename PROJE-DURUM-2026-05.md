# BorsaPusula — Proje Durum Raporu

> **Tarih:** 10 Mayıs 2026
> **Versiyon:** Production v=42 (Mayıs 2026 release)
> **VPS:** root@135.181.206.109 (Hetzner Helsinki)
> **Git:** github.com/ozanturk19/bist30 (main branch)
> **Stack:** Flask + Jinja2 + Vanilla JS + lightweight-charts + Cloudflare CDN
> **Veritabanı:** Yok (yfinance API + in-memory + localStorage + JSON dosyaları)

---

## 🎯 Misyon

Borsa İstanbul'da işlem gören 215 hisse için algoritmik teknik analiz sinyalleri üreten Türkçe fintech platformu. Hedef kitle: Türk bireysel yatırımcılar (aktif trader + araştırmacı yatırımcı + meraklı yatırımcı segmentleri).

**Sloganı:** "Piyasanın Yönü"

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────┐
│ Cloudflare CDN + DNS                    │
│   ↓ HTTPS                               │
│ Hetzner VPS (Helsinki, 4GB RAM)         │
│   ├── nginx (80/443)                    │
│   └── gunicorn -w 2 -k gevent           │
│       └── Flask app.py (5400 satır)     │
│           ├── /api/data → in-memory     │
│           ├── /api/macro → 60s cache    │
│           ├── /api/hisse/* → various    │
│           └── SSE stream (canlı fiyat)  │
└─────────────────────────────────────────┘
   ↓ Worker pool                              ↓ Background threads
   ├── yfinance fetcher (her 30s)             ├── Gemini AI haber prefetch
   ├── KAP scraper (4h)                       ├── _digest_cron_loop (19:00 daily)
   └── _refresh_data() (her 30s)              └── _macro_news_bg_loop
```

---

## 📊 Sinyal Motoru

### Algoritma (Mayıs 2026 sonu validate edilmiş)
```
Güçlü Trend (AL):
  Supertrend yukarı (LONG) +
  ADX ≥ 25 (trend gücü) +
  EMA12 > EMA99 (uzun vade uyumu)

Zayıf Trend (SAT):
  Supertrend aşağı (SHORT) +
  ADX ≥ 25 +
  EMA12 < EMA99

Yatay (eski "Belirsiz"):
  Yukarıdaki koşullar oluşmamış
```

### Premium Sinyal (★)
Backtest sonucu: **AL + RVOL ≥ 1.20** kombinasyonu en yüksek Sharpe (2.97) veriyor.
- RVOL = son 5 günlük hacim ortalaması / son 20 günlük hacim ortalaması
- Premium hisseler her sayfada altın ★ ikonu ile gösterilir

### Backtest Performansı (BIST30, 2 yıl)
| Metrik | Değer |
|---|---|
| Toplam sinyal | 451 (28 hisse · 2 yıl) |
| Güçlü Trend başarı oranı | %36.8 |
| Güçlü Trend ortalama getiri | +1.34% |
| Sharpe Ratio | 1.99 |
| Max Drawdown | -56.44% |
| Profit Factor | 1.47 |
| Premium subset Sharpe | 2.97 |

---

## 🌐 Sayfa Envanteri (28 sayfa)

### Ana sayfalar
| Route | Açıklama | Status |
|---|---|---|
| `/` | Ana sinyal panosu (215 hisse, real-time) | ✅ |
| `/ozet` | Günlük özet — kaç güçlü/zayıf | ✅ |
| `/tarama` | Hisse tarayıcı (sinyal/sektör/RVOL filter, sortable) | ✅ |
| `/gucu-yuksek` | En güçlü Premium sinyaller | ✅ |
| `/sektor-harita` | Sektör ısı haritası + tarama deeplink | ✅ |
| `/karsilastir` | 2-4 hisse yan yana karşılaştırma | ✅ |
| `/portfolio` | Kişisel portföy takibi (localStorage) | ✅ |
| `/sinyal-performans` | Backtest geçmişi + aktif sinyal sortable | ✅ |
| `/bilanco-takvimi` | Q1-Q4 bilanço açıklama tahminleri + KAP linkleri | ✅ |
| `/hisseler` | **YENİ** — Tüm 215 hisse SSR hub (SEO) | ✅ |
| `/hisse/<TICKER>` | Hisse detay (chart + indicators + AI commentary) | ✅ |

### Varlık sayfaları (kripto + emtia + ABD)
| Route | Açıklama |
|---|---|
| `/btc`, `/eth`, `/sol`, `/bnb`, `/kripto` | Kripto sayfaları |
| `/altin`, `/gumus`, `/petrol`, `/dogalgaz`, `/emtialar` | Emtia |
| `/abd`, `/abd/nasdaq`, `/abd/sp500`, `/abd/<TICKER>`, `/abd/tarama` | ABD piyasaları |

### İçerik + statik
| Route | Açıklama |
|---|---|
| `/blog` | 27+ makale liste |
| `/blog/<slug>` | Tek makale (yeni navbar eklenmiş) |
| `/gundem` | Haber ve KAP gündemi |
| `/metodoloji`, `/hakkinda`, `/iletisim`, `/yasal`, `/gizlilik` | Statik |
| `/profil` | Subscribe profile completion form |
| `/sitemap.xml`, `/robots.txt` | SEO |

### Legacy redirects (Search Console fix)
| Eski path | Yeni path | Kod |
|---|---|---|
| `/nasdaq` | `/abd/nasdaq` | 301 |
| `/sp500` | `/abd/sp500` | 301 |
| `/dow`, `/djia` | `/abd` | 301 |
| `/hisse/ANACM` (delisted) | — | 410 Gone |

---

## ✨ Önemli özellikler (Mayıs 2026 release)

### 1. Subscribe + kullanıcı tanıma sistemi
- **Cloudflare Email Routing** (free) → Brevo SMTP
- 2-step subscribe: ad/soyad + email
- Cookie + localStorage persistence (`bp_sub`, `bp_sub_user`)
- `/api/me` endpoint kullanıcıyı tanır
- Daily digest cron 19:00 (mail_pref-aware: instant/premium/daily/weekly)
- Profile completion CTA "Profili Tamamla →"

### 2. Hisse detay ⭐+🔔 butonları
- ➕ "Portföye ekle" pill button (mavi, active state)
- 🔔 "Bildirim al" pill button (yeşil, active state)
- Mobilde full-width row alt satıra düşer
- localStorage: `bp_portfolio` (qty, buy_price, added_at) + `bp_watchlist`

### 3. Mobil card zil butonu
- Her sinyal kartında sağ üst `mc-bell` button
- `mcb-{ticker}` ID + `toggleWatch()` global state senkronu
- Gold-on-active, transparent-on-inactive

### 4. Kategori başvuruları (kurumsal güvenlik)
| Vendor | Status |
|---|---|
| Symantec WebPulse | ✅ Submitted |
| Forcepoint | ✅ Submitted |
| Trend Micro | ✅ Submitted |
| Trellix/McAfee | ✅ Submitted |
| Palo Alto Networks | ✅ Submitted |
| Zscaler (email) | ✅ Submitted |
| Cisco Talos (email) | ✅ Submitted |
| **Fortinet** (Pornography → Finance dispute) | ⏳ Yanıt bekleniyor |

### 5. Search Console SEO
- Sitemap 358+ URL
- `/hisseler` SSR hub (214 internal hisse linki Googlebot'a)
- 5xx error fix doğrulaması başlatıldı
- 404 düzeltmeleri (delisted ticker → 410 Gone)
- robots.txt: tüm reputation crawler'lar allow

### 6. Performans + güvenlik altyapı
- **Gunicorn** `-w 2 -k gevent --max-requests 1500 --worker-tmp-dir /dev/shm`
- **systemd ExecStartPost** smoke test (deploy sonrası otomatik validation)
- **Health cron** her 5dk → 3 ardışık fail → admin alarm mail
- **Pre-deploy lint** (`predeploy_lint.sh`): Türkçe apostrof + cache buster + AST check
- **Frontend error tracker** `/api/log-error` (window.error + unhandledrejection)
- **Security headers**: CSP, HSTS, COOP, CORP, X-Permitted

---

## 🎨 UI/UX Geliştirmeleri (Mayıs 2026)

### Dark fintech tasarım dili
```css
--bp-bg: #0e0e12        /* sayfa arkaplan */
--bp-surface: #161b22   /* kart */
--bp-border: #30363d    /* border */
--bp-text: #e6edf3      /* metin */
--bp-text2: #8b949e     /* ikincil */
--bp-text3: #484f58     /* soluk */
--bp-al: #3fb950        /* AL/Güçlü Trend */
--bp-sat: #f85149       /* SAT/Zayıf Trend */
--bp-bkl: #8b949e       /* Yatay */
--bp-prem: #ffc850      /* Premium ★ */
```

### Son release değişiklikleri (12 madde batch)
1. ✅ Tarama sayfası: search icon position + premium filter + bidirectional sortable
2. ✅ "Belirsiz" → **"Yatay"** rename (12 template)
3. ✅ Bilanço refactor: nested `<a>` HTML bug fix + Premium ★ markers
4. ✅ Sektör cards: clickable `<div onclick>` (nested-a fix) + premium count pill
5. ✅ Performans: sortable kolonlar + filtre bar (search/signal/return)
6. ✅ Portfolio: ticker autocomplete (`<datalist>` 215 hisse)
7. ✅ Karşılaştır: Premium ★ row + Help icon (ⓘ) tooltips
8. ✅ Hisse detay algoritma onayları: hover tooltip (eskiden blog linkti)
9. ✅ Blog article: tam navbar eklendi (eskiden sadece logo+title)
10. ✅ Mobil hareketliler: tek kolona çöküyor (centering)
11. ✅ Page transitions: View Transitions API + prefetch on hover
12. ✅ /sinyal-performans header standardize (bp-main-nav + critical-css)

### Kalıcı iyileştirmeler
- **Macro ticker JS RAF** (sabit 55 px/sn) — 17 template, CSS animation tabanlı eski yaklaşım kaldırıldı
- **Critical CSS** anti-CLS tüm sayfalarda (nav layout lock + page-title gizle)
- **bp-search.js**: Cmd+K overlay search, Smart refresh, recognizeUser, applyKnownUserUI

---

## 🧪 Tarama + Filtre Sistemi

### Tarama (`/tarama`) parametreleri
```
GET /api/tarama
  signal:    AL | SAT | BEKLE
  only_premium: 1
  min_adx:   sayı
  sector:    sektör adı (URL encoded)
  eq:        IDEAL | IYI | DIKKATLI | UZAK
  min_price, max_price: ₺
  sort:      adx | price | change_pct | vol_ratio | signal_bars | bull_score
  sort_dir:  asc | desc
```

### Sektör → Tarama deeplink
Sektör kartına tıklayınca → `/tarama?sector={Bankacılık}` → o sektörün filtreli listesi.

---

## 📱 Responsive Breakpoints

| Genişlik | Davranış |
|---|---|
| ≥ 900px | Full nav (8+ item) + sidebar |
| 720-900px | Hamburger nav + responsive grid |
| ≤ 720px | Bottom navigation + cards stack |
| ≤ 480px | Tek kolon her şey, bottom-sheet modal |

---

## 🔐 Güvenlik

### Headers (her response)
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' ...
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Frame-Options: SAMEORIGIN
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
Referrer-Policy: strict-origin-when-cross-origin
```

### Rate limiting
- `/api/contact` 3/min
- `/api/subscribe` 5/min
- `/api/tarama` 60/min
- `/api/hisse/*/news` 20/min

### Admin endpoints
`/admin/*` — token-based, 1.1.1.1 + admin email IP whitelist

---

## 📈 Görselleştirme

- **Chart.js** (radar, donut, bar — performans sayfası)
- **lightweight-charts** (TradingView lib — OHLC + EMA overlay)
- **SVG inline** (logo, ikonlar, sektör heatmap)
- **CSS keyframes** (skeleton shimmer, tick animation, view transition)

---

## 🚀 Deploy + Operasyon

### Deploy süreci
```bash
# 1. Local'de test
python app.py

# 2. SSH'a kopyala (rsync veya scp)
rsync -avz --exclude=.git ./ root@135.181.206.109:/root/bist30/

# 3. VPS'te:
bash /root/bist30/predeploy_lint.sh    # apostrof + cache buster + AST check
systemctl restart bist30                # ExecStartPost otomatik smoke test
bash /root/bist30/smoke_test.sh         # manual verify
```

### Cache buster
`bp-search.js?v=42` — her release'te `v` artırılır, tüm template'lerde tek seferde:
```bash
sed -i 's|bp-search.js?v=42|bp-search.js?v=43|g' templates/*.html
```

### Health monitoring
- Her 5dk: `health_cron.sh` smoke test
- 3 ardışık fail → `notify_health.py` admin'e mail
- systemd ExecStartPost: deploy sonrası 60s warmup + smoke test

### Backup stratejisi
- Git commit + push (kod)
- localStorage (kullanıcı portföy/watchlist) — client-side
- subscribers.json (gitignored, sadece VPS) — abonelik veritabanı
- last_cache.json (gitignored) — startup gecikmesi azaltma

---

## 🐛 Bilinen Issue'lar

### 🟡 Aktif takip
- **Gemini API rate limit (429)** — ücretsiz tier sınırı; AI haber özeti zaman zaman boş döner. Çözüm: prefetch'i sadece AL hisselerine indirmek veya ücretli tier.
- **Fortinet "Pornography" kategorisi** — domain'in eski sahibinden kaldı, dispute gönderildi 10 May, yanıt bekleniyor.

### ✅ Çözüldü
- ~~ADX=0 fallback~~ → fix line 2726
- ~~/karsilastir 404~~ → sayfa eklendi
- ~~Subscribe duplicate empty msg~~ → "Bu e-posta zaten kayıtlı."
- ~~Belirsiz naming~~ → "Yatay"
- ~~Bilanço nested-a HTML bug~~ → div onclick + inner a
- ~~Sektör nested-a~~ → div onclick + click delegation
- ~~Blog article navbar yok~~ → eklendi
- ~~Sinyal performans eski header~~ → standartlaştırıldı

---

## 📁 Dizin Yapısı

```
bist30/
├── app.py                       # 5400 satır, tek dosya Flask app
├── backtest.py                  # backtest framework
├── blog_content.py              # 27+ makale data
├── baslat.sh                    # local dev başlatıcı
├── smoke_test.sh                # API sağlık testi
├── predeploy_lint.sh            # apostrof + cache buster + AST
├── health_cron.sh               # her 5dk health
├── notify_health.py             # admin alarm mail
├── safe_restart.sh              # graceful restart wrapper
├── subscribers.json             # ⚠️ gitignored, abonelik DB
├── last_cache.json              # ⚠️ gitignored, startup hızlandırma
├── .env                         # ⚠️ gitignored, SMTP + API keys
├── templates/
│   ├── index.html               # ana sinyal panosu
│   ├── hisse.html               # hisse detay
│   ├── hisseler.html            # SEO hub (YENİ)
│   ├── ozet.html, tarama.html, sektor_harita.html
│   ├── karsilastir.html, portfolio.html
│   ├── sinyal_performans.html, bilanco_takvimi.html
│   ├── varlik.html              # kripto/emtia/ABD generic
│   ├── abd_tarama.html, gucu_yuksek.html
│   ├── blog.html, blog_article.html
│   ├── kategori.html, gundem.html
│   ├── hakkinda.html, iletisim.html, metodoloji.html
│   ├── yasal.html, gizlilik.html
│   └── profil.html              # subscribe profile form
├── static/
│   ├── bp-search.js             # global search + nav + ticker
│   ├── lightweight-charts.min.js
│   ├── manifest.json, sw.js     # PWA
│   ├── favicon.ico, og-image.svg
│   └── bp-search.js?v=42        # cache busted
└── docs/
    ├── README.md
    ├── ROADMAP.md
    ├── master-plan.md
    ├── borsapusula-proje.md
    ├── borsapusula-guvenlik.md
    ├── ajan2_bist_sinyal.md
    ├── gelistirme-plani.md
    ├── test-raporu.md           # eski QA raporu
    └── PROJE-DURUM-2026-05.md   # bu dosya
```

---

## 🔮 Yol Haritası (kısa vade)

### Yapılacak (öncelikli)
- [ ] **Daily digest mail görsel test** — gerçek mail client'ta render kontrolü
- [ ] **/about + /iletisim trust signal güçlendirme** — başvurular için
- [ ] **yfinance cache** — hisse detay performans + Googlebot crawl budget
- [ ] **Profil tamamlama analytics** — kim dolduruyor takibi

### Beklemede (ileri vade)
- [ ] EODHD veya Foreks ticari veri lisansı (yfinance limitlerini aşmak için)
- [ ] Ücretli tier sinyal abonelik
- [ ] Mobile app (PWA → React Native)
- [ ] Telegram bot entegrasyonu
- [ ] WebSocket gerçek-zaman fiyat (polling yerine)

---

## 📞 Operasyonel İletişim

- **Domain:** borsapusula.com
- **Cloudflare:** Email Routing aktif
- **SMTP:** Brevo (smtp-relay.brevo.com:587, free 300/gün)
- **Admin email:** ozan-turk19@hotmail.com (alarm + admin)
- **Public email:** noreply@borsapusula.com (kullanıcı maili)
- **Telegram:** t.me/borsapusula

---

## 🏆 Kalite Metrikleri

| Metrik | Değer | Hedef |
|---|---|---|
| Yanıt süresi (anasayfa) | <20ms | <100ms |
| Yanıt süresi (hisse detay) | <15ms | <100ms |
| Lighthouse Performance | ~85 | >90 |
| RAM kullanımı (worker) | 142MB | <200MB |
| CPU (idle) | %5-10 | <%30 |
| Smoke test | 215 hisse pass | pass |

---

*Son güncelleme: 10 Mayıs 2026 — claude code session w/ ozan*
