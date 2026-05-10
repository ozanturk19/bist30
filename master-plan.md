# BorsaPusula — Master Plan & Kapsamlı Test Raporu

> **Son güncelleme:** 2 Mayıs 2026  
> **Kapsam:** Canlı VPS testi (SSH) + kullanıcı analizi + rakip karşılaştırması + tam implementasyon planı + makro haber planı  
> **VPS:** root@135.181.206.109 — port 8003 — app.py 4882 satır (1 Mayıs'ta 3520'ydi, +1362 satır)  
> **Amaç:** Bu belge ajana doğrudan verilebilir. Her madde implementation-ready.

---

## 1. SİSTEM DURUMU (1 Mayıs 2026)

| Metrik | Değer | Durum |
|--------|-------|-------|
| Uptime | 15 gün 23 saat | ✅ |
| RAM | 1.5G / 3.7G (%41) | ✅ |
| Disk | 9.1G / 38G (%26) | ✅ |
| Load Average | 0.17 / 0.32 / 0.35 | ✅ |
| Gunicorn worker RSS | 142MB | ✅ |
| Journal log boyutu | **1.1GB** | ⚠️ Gemini 429 log'ları birikiyor |
| Toplam hisse | 145 (BIST + US genişletilmiş) | ✅ |
| AL / SAT / BEKLE | 38 / 3 / 104 | ✅ |
| Yanıt süresi (tüm sayfalar) | <20ms | ✅ |

---

## 2. TÜM ROUTE'LAR — HTTP DURUM

| URL | HTTP | Süre | Durum |
|-----|------|------|-------|
| / | 200 | 5.5ms | ✅ |
| /ozet | 200 | 3.8ms | ✅ |
| /gucu-yuksek | 200 | — | ✅ |
| /tarama | 200 | — | ✅ (navigasyonda görünmüyor) |
| /sektor-harita | 200 | — | ✅ |
| /bilanco-takvimi | 200 | — | ✅ |
| /sinyal-performans | 200 | — | ✅ |
| /portfolio | 200 | — | ✅ |
| /blog | 200 | — | ✅ |
| /blog/supertrend-indikatoru-nedir | 200 | — | ✅ |
| /blog/supertrend-nedir | 301 | — | ✅ redirect çalışıyor |
| /hisse/AKBNK | 200 | 6.5ms | ✅ |
| /abd | 200 | — | ✅ |
| /abd/nasdaq | 200 | — | ✅ |
| /abd/sp500 | 200 | — | ✅ |
| /abd/AAPL | 200 | — | ✅ |
| /abd/tarama | 200 | — | ✅ |
| /btc /eth /bnb /sol | 200 | 2–4ms | ✅ |
| /altin /gumus /petrol /dogalgaz | 200 | 4–6ms | ✅ |
| /kripto /emtialar | 200 | 4–5ms | ✅ |
| /metodoloji /hakkinda /iletisim /yasal /gizlilik | 200 | — | ✅ |
| /hisse/INVALID123 | 404 | — | ✅ |
| /blog/olmayan-makale | 404 | — | ✅ |
| **/karsilastir** | **404** | — | ❌ Eksik |
| **/gundem** | **404** | — | ❌ Eksik |

---

## 3. API TEST SONUÇLARI

### `/api/data`
```
stocks: 145 | AL: 38 | SAT: 3 | BEKLE: 104
loading: false | updated: 01.05.2026 16:17:36
```
✅ Çalışıyor | ⚠️ Restart sonrası ~3 dk loading:true

**Örnek tam kayıt (ASELS — AL, 14 gündür):**
```json
{
  "ticker": "ASELS", "price": 420.25, "change_pct": -1.23,
  "signal": "AL", "signal_date": "10.04.2026", "signal_bars": 14,
  "signal_price": 398.5, "sl_level": 376.26,
  "confirmed": true, "bull_score": 3, "bear_score": 0,
  "indicators": {
    "adx": {"label": "ADX 41", "value": "DI+33/DI-11", "bull": true}
  },
  "rsi": 66.9, "vol_ratio": 0.94, "entry_quality": "IYI",
  "tp1": 508.23, "tp2": 552.22, "rr_ratio": 2.0
}
```
⚠️ **ADX `indicators.adx.label` içinde saklı, üst seviyede `null`** → sinyal açıklama bug'ı kaynağı

---

### `/api/market-news` (Gündem Kutusu)
```
items: 5 | updated: 01.05.2026 16:33 | has_loading: false
```
Mevcut itemler: ASELS, EREGL, HEKTS, KRDMD, ODAS (hepsi AL sinyalli)

⚠️ **KAP URL yok** — kap_url: YOK (5 itemde de)  
⚠️ **Boş içerik gösteriliyor** — HEKTS ve KRDMD için "kayda değer gelişme yok" mesajı item olarak dönüyor  
⚠️ **Sadece 5 hisse** — 38 AL sinyalli hisse varken neden 5?

---

### `/api/hisse/<ticker>/news`
```
AKBNK: OK (gemini, 746 char)
GARAN: OK (174 char — "kayda değer gelişme yok" mesajı)
ASELS: OK (gemini, 502 char) — ⚠️ GELECEK TARİHLİ HABERLER (aşağıya bak)
ENJSA: OK (184 char — "kayda değer gelişme yok" mesajı)
```

---

### `/api/hisse/<ticker>/signal-explanation`
```
BIST: source: gemini | explanation: ~200 char (fallback metin)
AAPL (ABD): source: None | explanation: "" — BOŞTU
```
⚠️ ADX değeri açıklamada 0 görünüyor (bug)  
❌ ABD hisseleri için tamamen boş

---

### `/api/hisse/<ticker>/mtf`
```json
AKBNK: { h4: BEKLE/19.8, daily: BEKLE/22.8, weekly: BEKLE/22.5, monthly: AL/34.7 }
```
✅ 4 zaman dilimi çalışıyor, ADX değerleri doğru

---

### `/api/hisse/<ticker>/chart`
```
ohlc: 500 mum | ema12: 500 | markers: 6 sinyal işareti
Son mum: 2026-04-29, close: 132.7
```
✅ Tam veri

---

### `/api/tarama`
```
signal=AL&min_adx=25 → count: 35
sector=Bankacılık → count: 11
US hisse tarama: 144 hisse
```
✅ Çalışıyor | ⚠️ Navigasyonda link yok

---

### `/api/macro`
```
XU100: 14311 | BTC: 75022 | ALTIN: 4561 | USDTRY: 45.07
SP500: 7112 | NASDAQ: 24551 | ... (10 sembol)
```
✅ 2.9ms | ⚠️ change_pct_fmt field yok

---

### Diğer
| Endpoint | Durum |
|----------|-------|
| /api/bilanco-takvimi | ✅ 5 dönem |
| /api/contact POST | ✅ {"ok": true} |
| /api/subscribe | ✅ Kayıt + duplicate mesajı var |
| /robots.txt | ✅ |
| /sitemap.xml | ✅ 213 URL |
| /api/backtest | ⚠️ "computing" — tamamlanmadı |
| /api/stream (SSE) | ⚠️ Seans dışı veri yok (normal) |

---

## 4. AKTİF HATALAR — TAM LİSTE

---

### 🔴 BUG-1 — Gemini Hallucination (Gelecek Tarihli Haberler)

**Öncelik: ACİL — Güven Kırıcı**

**Kanıt:** Bugün 1 Mayıs 2026. ASELS için üretilen haberler:
```
* 2026-05-05: ASELSAN, Kuzey Kutbu uydu sözleşmesi 21M$  ← 4 gün sonrası
* 2026-05-03: ASELSAN 1Ç2026 finansal sonuçları           ← 2 gün sonrası
* 2026-05-02: Radar sistemi geliştirme                    ← 1 gün sonrası
```
Gemini bilmediği için uydurdu. KAP URL yok, doğrulama yolu yok.

**Kök neden:** `get_ai_news()` prompt'u tarih kontrolünü yeterince zorunlu kılmıyor.

**Fix — app.py `get_ai_news()` içindeki prompt:**
```python
today_str   = datetime.now().strftime("%d %B %Y")
cutoff_str  = datetime.now().strftime("%Y-%m-%d")

prompt = (
    f"Bugünün tarihi: {today_str} ({cutoff_str}).\n"
    f"KURAL 1: YALNIZCA {cutoff_str} TARİHİNDEN ÖNCE gerçekleşmiş olayları yaz.\n"
    f"KURAL 2: Eğer son 7 günde bu hisse için doğrulanmış bir bilgin yoksa, "
    f"SADECE şunu yaz: 'Son 7 günde kayda değer bir gelişme bulunmuyor.'\n"
    f"KURAL 3: Tarih uydurma. Gelecek tarihli haber yazma. Tahmin yapma.\n\n"
    f"Görev: {ticker} ({name}) hissesi için son 7 gün içindeki "
    f"gerçek KAP bildirimleri, finansal sonuçlar veya önemli açıklamaları "
    f"madde madde listele."
)
```

**Kabul kriteri:** ASELS için üretilen tüm tarihler ≤ bugün.

---

### 🔴 BUG-2 — ADX=0 Sinyal Açıklamada

**Öncelik: ACİL — Veri Yanlışlığı**

**Kanıt:** Sinyal açıklaması "ADX 0 ile zayıf yükseliş trendi" yazıyor.  
Gerçek ADX: ASELS=41, AKBNK=22.8, ENJSA=25 (MTF ve tarama doğruluyor).

**Kök neden:** `_cache["data"]`'da ADX şu yapıda:
```json
"indicators": {"adx": {"label": "ADX 41", "value": "DI+33/DI-11"}}
```
Sinyal açıklama fonksiyonu `signal_data.get("adx", 0) or 0` yapıyor → `None → 0`.

**Fix — app.py, sinyal açıklama fonksiyonu içinde:**
```python
# Eski (yanlış):
adx = signal_data.get("adx", 0) or 0

# Yeni (doğru):
_adx_raw = (signal_data.get("adx")
            or signal_data.get("indicators", {}).get("adx", {}).get("label", ""))
try:
    adx = float(str(_adx_raw).replace("ADX", "").strip()) if _adx_raw else 0.0
except (ValueError, TypeError):
    adx = 0.0
```

Aynı pattern EMA ve DI değerleri için de kontrol edilmeli (e12, e99, di_plus, di_minus).

**Kabul kriteri:** ASELS sinyal açıklaması "ADX 41 ile güçlü trend" yazıyor.

---

### 🔴 BUG-3 — Gündem Kartında Boş İçerik Gösteriliyor

**Öncelik: Yüksek — Kullanıcı Deneyimi**

**Kanıt:** `/api/market-news` 5 item döndürüyor ama 2-3 tanesi "kayda değer gelişme yok" içeriyor. Bu boş mesajlar kart olarak render ediliyor.

**Fix — app.py `api_market_news()` içinde:**
```python
# snippet üretildikten sonra, results.append'den önce:
EMPTY_PATTERNS = (
    "kayda değer bir gelişme",
    "kayda değer gelişme bulunmuyor",
    "kayda değer bir haber",
    "herhangi bir haber bulunamadı",
    "son 7 gün",  # sadece bu cümleden oluşan snippet
)
is_empty = any(pat in snippet.lower() for pat in EMPTY_PATTERNS) and len(snippet) < 120
if is_empty:
    # Boş haber için algoritmik fallback — sinyal bilgisini göster
    dur = "bugün" if bars <= 1 else f"son {bars} gündür"
    entry_q = s.get("entry_quality", "")
    snippet = (f"{dur.capitalize()} {sig} sinyali aktif"
               f"{', ' + entry_q + ' giriş bölgesi' if entry_q else ''}. "
               f"SL: {s.get('sl_level', 0):.2f}₺ | "
               f"Hedef: {s.get('tp1', 0):.2f}₺")
    source = "algorithmic"
```

**Kabul kriteri:** Gündem kutusunda "kayda değer gelişme yok" metni görünmüyor.

---

### 🔴 BUG-4 — Gündem Kartında KAP Linki Yok

**Öncelik: Yüksek — Güvenilirlik**

**Kanıt:** `kap_url: YOK` — tüm 5 market-news item'ında.

**Fix — app.py `api_market_news()` içinde, results.append'e ekle:**
```python
# KAP_MEMBER_OIDS tablosu app.py başına eklenmeli (aşağıya bak)
kap_oid = KAP_MEMBER_OIDS.get(t, "")
results.append({
    ...
    "kap_url": f"https://www.kap.org.tr/tr/sirket/{kap_oid}" if kap_oid else
               f"https://www.kap.org.tr/tr/arama?q={t}",
})
```

**Tablonun ekleneceği yer — app.py başı (importların hemen altı):**
```python
# KAP Kamuyu Aydınlatma Platformu — şirket ID eşleştirme
KAP_MEMBER_OIDS = {
    "AKBNK": "2770", "GARAN": "2760", "ISCTR": "2776", "YKBNK": "2780",
    "VAKBN": "2778", "HALKB": "2762", "ALBRK": "2750",
    "ASELS": "792",  "THYAO": "2874", "EREGL": "2362", "TUPRS": "2878",
    "SASA":  "2726", "FROTO": "2756", "TOASO": "2876", "ARCLK": "2748",
    "BIMAS": "2752", "MGROS": "2772", "KCHOL": "2764", "SAHOL": "2758",
    "AGHOL": "2744", "TKFEN": "2872", "ENJSA": "5496", "ODAS":  "6159",
    "HEKTS": "2766", "KRDMD": "2768", "SISE":  "2724", "PETKM": "2774",
    "EKGYO": "2754", "TTRAK": "2870", "LOGO":  "3494", "NETAS": "2773",
    # US hisseler için KAP yok, SEC EDGAR linki ver:
    # "AAPL": "" → https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=apple
}
```

**Kabul kriteri:** Her gündem kartında tıklanabilir "KAP'ta gör ↗" linki var.

---

### 🟡 BUG-5 — ABD Hisse Sinyal Açıklaması Boş

**Kanıt:** `/api/hisse/AAPL/signal-explanation` → `source: None, explanation: ""`

**Kök neden:** US hisseler için sinyal açıklama mantığı BIST listesini kontrol ediyor, US hisseler bulunamıyor.

**Fix — VPS app.py'de signal-explanation endpoint'ini bul, US ticker branch ekle:**
```python
# US ticker ise farklı prompt kullan
is_us = ticker not in STOCK_NAMES and ticker in US_STOCK_NAMES
if is_us:
    prompt = (
        f"Bugün {today_str}. {ticker} ({US_STOCK_NAMES.get(ticker, ticker)}) "
        f"hissesi için algoritmik analiz: Supertrend {sig_label}, "
        f"bull_score={bull_score}/3. "
        f"Bu teknik durumu bireysel yatırımcı için 2 cümleyle açıkla. "
        f"Yatırım tavsiyesi verme."
    )
```

---

### 🟡 BUG-6 — Startup Gecikmesi (3 dk boş sayfa)

**Kanıt:** Restart sonrası `loading: true`, stocks: 0 → ~3 dakika.

**Fix — app.py başlatma mantığına ekle:**
```python
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_cache.json")

def _save_cache_snapshot():
    """Her başarılı refresh sonrası diske yaz."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "data": _cache["data"],
                "updated_at": _cache.get("updated_at", ""),
                "saved_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning("Cache snapshot yazılamadı: %s", e)

def _load_cache_snapshot():
    """Startup'ta son cache'i yükle (stale olsa bile gösterilir)."""
    try:
        if not os.path.exists(CACHE_FILE):
            return
        with open(CACHE_FILE, encoding="utf-8") as f:
            snap = json.load(f)
        if snap.get("data"):
            _cache["data"]       = snap["data"]
            _cache["updated_at"] = snap.get("updated_at", "")
            _cache["loading"]    = False  # Stale data flag'ı eklenebilir
            logger.info("Startup cache yüklendi: %d hisse (son: %s)",
                        len(snap["data"]), snap.get("updated_at", "?"))
    except Exception as e:
        logger.warning("Cache snapshot okunamadı: %s", e)

# Uygulama başında çağır:
_load_cache_snapshot()
# _refresh_data() tamamlandığında çağır:
_save_cache_snapshot()
```

**Kabul kriteri:** Restart sonrası anında eski veriler gösteriliyor, arka planda yeni veri yüklenirken "stale" bandı görünüyor.

---

### 🟡 BUG-7 — Log Rotasyonu Yok (1.1GB)

**Fix — VPS'te çalıştır:**
```bash
# Anlık temizlik
journalctl --vacuum-size=200M

# Kalıcı limit — /etc/systemd/journald.conf
echo "SystemMaxUse=300M" >> /etc/systemd/journald.conf
echo "SystemKeepFree=500M" >> /etc/systemd/journald.conf
systemctl restart systemd-journald
```

Ayrıca Gemini 429 loglarını INFO → DEBUG seviyesine indir:
```python
# app.py — _gemini_call() içinde 429 loglamasını değiştir:
# Eski:
logger.warning("_gemini_call [%s]: HTTPError (HTTP 429)", model)
# Yeni:
logger.debug("_gemini_call [%s]: rate-limited (429)", model)  # sessiz
```

---

### 🟢 BUG-8 — GA4 Analytics Yok

**Fix:** Her template `<head>` içine (charset meta'sından sonra):
```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX', { anonymize_ip: true });
</script>
```

**Etkilenen template'ler (VPS /root/bist30/templates/):**
index.html, hisse.html, varlik.html, ozet.html, blog.html, blog_article.html,
gucu_yuksek.html, tarama.html, abd_tarama.html, sektor_harita.html,
bilanco_takvimi.html, sinyal_performans.html, portfolio.html, hakkinda.html

**Ek event'ler hisse.html'e:**
```javascript
// fetchExplanation() tamamlandıktan sonra:
if(typeof gtag !== 'undefined') {
  gtag('event', 'signal_view', { ticker: TICKER, signal: '{{ssr_signal.signal if ssr_signal}}' });
}
// KAP link tıklaması:
document.querySelectorAll('a[href*="kap.org.tr"]').forEach(a =>
  a.addEventListener('click', () => gtag('event', 'kap_click', { ticker: TICKER }))
);
```

---

### 🟢 BUG-9 — /tarama Navigasyonda Görünmüyor

Sayfa var, çalışıyor, ama ana menüde link yok. 38 AL sinyalli hisse ile en güçlü araç gizli.

**Fix — index.html ve diğer sayfalarda nav menüsüne ekle:**
```html
<a href="/tarama" class="nav-link">🔍 Tarayıcı</a>
```

---

### 🟢 BUG-10 — Markdown Formatı Haber Metninde

**Kanıt:** Haber snippet'leri `* **2026-05-05:**` formatında geliyor. UI'da ham markdown görünme riski.

**Fix — index.html `_renderGnmCard()` ve hisse.html `fetchNews()` içinde:**
```javascript
function parseNewsMarkdown(text) {
    return text
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/^\*\s+/gm, '• ')
        .replace(/^-\s+/gm, '• ')
        .replace(/\n/g, '<br>');
}
// snippet render edilirken:
el.innerHTML = parseNewsMarkdown(item.snippet);
```

---

## 5. ÇALIŞAN ÖZELLİKLER — TAM LİSTE

| Özellik | Durum | Not |
|---------|-------|-----|
| Ana sinyal tablosu (145 hisse) | ✅ | BIST + US genişletilmiş |
| AL/SAT/BEKLE sinyal motoru (3 kriter) | ✅ | Supertrend + ADX≥25 + EMA12/99 |
| TP1/TP2/RR hesaplama | ✅ | |
| Giriş kalitesi (IDEAL/IYI/DIKKATLI/UZAK) | ✅ | |
| Stop loss seviyesi | ✅ | ATR bazlı |
| 500 günlük OHLC grafik | ✅ | LightweightCharts |
| EMA12/EMA99 grafik üstü | ✅ | |
| Supertrend signal markers (ok işaretleri) | ✅ | Tooltip yok |
| MTF analizi (H4/D/W/M) | ✅ | 4 zaman dilimi |
| Makro ticker (10 sembol, kayan) | ✅ | Sadece ana sayfada |
| Sektör ısı haritası | ✅ | |
| Bilanço takvimi | ✅ | |
| Hisse tarayıcı (/tarama) | ✅ | Navigasyonda gizli |
| ABD piyasası (NASDAQ/SP500/hisseler) | ✅ | 144 US hisse |
| US hisse teknik analiz grafikleri | ✅ | Ayrı varlik.html template |
| Kripto sayfaları (BTC/ETH/BNB/SOL) | ✅ | |
| Emtia sayfaları (Altın/Gümüş/Petrol/Doğalgaz) | ✅ | |
| Gündem kutusu (market-news) | ✅ | 5 hisse, KAP linksiz |
| Haber AI (hisse bazlı) | ✅ | Hallucination riski var |
| Sinyal açıklaması AI | ✅ | ADX=0 bug'ı |
| Blog (27+ makale) | ✅ | |
| Blog 301 yönlendirme | ✅ | |
| Temel veri (P/E, P/D, ROE...) | ✅ | Sanitizasyon aktif |
| E-posta aboneliği | ✅ | Brevo SMTP, 4 abone |
| İletişim formu API | ✅ | |
| Portföy (localStorage) | ✅ | Cihazlar arası sync yok |
| SSR sinyal (pre-JS) | ✅ | hisse.html satır 864 |
| sitemap.xml (213 URL) | ✅ | |
| robots.txt | ✅ | |
| OG image + meta | ✅ | |
| Service Worker / PWA | ✅ | Push listener yok |
| Rate limiting | ✅ | Flask-Limiter |
| Admin endpoint koruması | ✅ | X-Admin-Secret header |
| 404 hata sayfaları | ✅ | |

---

## 6. KULLANICI GÖZÜNDEKİ DEĞERLENDİRME

### Yeni Ziyaretçi
**İyi:** Hız mükemmel. Tasarım rakiplerden temiz. Makro ticker bağlam veriyor. Renk kodlaması net.  
**Kötü:** Gündem kutusunda "kayda değer gelişme yok" metni — boş içerik. Sinyal açıklamasında "ADX 0" güven kırıcı. ABD hisselerinde açıklama yok.

### Aktif Trader
**İyi:** MTF analizi rakiplerde nadir. TP/SL/RR somut. Giriş kalitesi sinyali konumlandırıyor. /gucu-yuksek idealanchor sayfa.  
**Kötü:** Grafik marker'larında tooltip yok — "bu AL sinyalinde sonra ne oldu?". /tarama gizli. "Confirmed" vs "taze sinyal" farkı UI'da açıklanmıyor. Portföy cihazlar arası kaybolıyor.

### Pasif Takipçi
**İyi:** E-posta aboneliği var. Blog eğitici. Bilanço takvimi tek yerde.  
**Kötü:** 4 abone çok az — abonelik flow'u test edilmeli. Blog'da ilgili hisse bağlantısı yok.

### SEO Perspektifi
**İyi:** sitemap 213 URL, Article+BreadcrumbList schema, 301 redirect'ler.  
**Kötü:** GA4 yok (büyüme kör). FAQPage schema yok (zengin snippet fırsatı kaçıyor). Yeni büyük sayfalar (/abd, /kripto, /emtialar) sitemap'te doğrulanmalı.

---

## 7. HABER/GÜNDEM — RAKİP KARŞILAŞTIRMASI

| Platform | Haber Kaynağı | Sinyal Bağlantısı | KAP Entegrasyon | AI Kullanımı | Gerçek mi? |
|----------|--------------|-------------------|-----------------|--------------|------------|
| **Bigpara** | Editöryal + AA/Reuters | ❌ Yok | ✅ Anlık | ❌ Yok | ✅ Gerçek |
| **ForInvest** | KAP Real-time + Ajans | ❌ Yok | ✅ WebSocket | ❌ Yok | ✅ Gerçek |
| **Mynet Finans** | Haber agregasyonu | ❌ Yok | ⚠️ Gecikmeli | ❌ Yok | ✅ Gerçek |
| **BistScan** | ❌ Haber yok | — | ❌ Yok | ❌ Yok | — |
| **Midas** | Temel haberler | ❌ Yok | ⚠️ Bazı | ❌ Yok | ✅ Gerçek |
| **TradingView** | Küresel haber akışı | ✅ Var | ❌ Yok | ⚠️ Az | ✅ Gerçek |
| **BorsaPusula** | AI Üretim | ✅ Var | ❌ Yok | ✅ Var | ⚠️ Hallucination |

**Sonuç:** BorsaPusula tek olarak sinyalle haberi birleştiriyor — ama kaynak gerçek değil.  
**Hedef:** KAP (gerçek kaynak) + AI özetleme + sinyal bağlantısı = Türkiye'de benzersiz.

---

## 8. STRATEJİK FARKLILAŞMA — HABER/GÜNDEM

### Neden Büyük Boşluk Var?

ForInvest KAP bildirimi veriyor ama sinyalle bağlamıyor.  
Bigpara haber veriyor ama "bu haber beni etkiler mi?" sorusu yanıtsız.  
BistScan sinyal veriyor ama haber yok.  

**BorsaPusula'nın hedefi:**
> "Bu hisse neden bu sinyalde?" — teknik (ADX/Supertrend) + gerçek olay (KAP) + AI yorumu — hepsini tek ekranda.

Bireysel yatırımcı ASELS'e bakarken görmek istediği:
1. ✅ "AL sinyalinde, 14 gündür aktif" — var
2. ❌ "ASELSAN bu ay savunma bakanlığıyla gerçek sözleşme imzaladı" — KAP'tan gelmeli
3. ❌ "AI: Bu sözleşme gelirin ~%12'si, teknik göstergeler onaylıyor" — AI+KAP
4. ✅ "Stop loss: 376₺, Hedef: 508₺" — var

---

## 9. İMPLEMENTASYON PLANI

---

### TIER 0 — BUGÜN (< 2 saat, kritik bug fix)

#### T0-1: Hallucination Fix (30 dk)
**Dosya:** `/root/bist30/app.py`  
**Bul:** `get_ai_news()` fonksiyonu içindeki prompt string  
**Değiştir:** Yukarıdaki BUG-1 fix'ini uygula (tarihe katı kısıt + uydurma yasağı)

#### T0-2: ADX=0 Fix (20 dk)
**Dosya:** `/root/bist30/app.py`  
**Bul:** `get_ai_signal_explanation()` içinde `adx = signal_data.get("adx", 0) or 0` satırı  
**Değiştir:** Yukarıdaki BUG-2 fix'ini uygula

#### T0-3: Log Rotasyonu (10 dk)
**VPS'te çalıştır:** Yukarıdaki BUG-7 komutları  
Gemini 429'ları DEBUG seviyesine indir

#### T0-4: Boş Haber Kartı Gizle (20 dk)
**Dosya:** `/root/bist30/app.py`  
**Bul:** `api_market_news()` fonksiyonu, snippet üretimi  
**Ekle:** BUG-3 fix'ini uygula

---

### TIER 1 — BU HAFTA (< 2 saat her biri)

#### T1-1: KAP Linkleri (1 saat)
**Dosya:** `/root/bist30/app.py`  
**Ekle:** `KAP_MEMBER_OIDS` sözlüğünü (BUG-4'teki tablo)  
**Güncelle:** `api_market_news()` ve `api_hisse_news()` endpoint'lerinde kap_url döndür  
**Frontend:** index.html `_renderGnmCard()` içinde KAP linki render et  
**Kabul:** Her gündem kartında "KAP'ta gör ↗" linki var

#### T1-2: Markdown Parser (30 dk)
**Dosya:** `/root/bist30/templates/index.html` ve `hisse.html`  
**Ekle:** BUG-10 `parseNewsMarkdown()` fonksiyonu  
**Kabul:** `* **2026-05-05:**` görünmüyor, düzgün bullet point var

#### T1-3: GA4 Analytics (1 saat)
**Dosya:** Tüm template'ler  
**Ekle:** BUG-8'deki GA4 snippet'ini 14 template'e ekle  
**Ekle:** hisse.html'e signal_view ve kap_click event'leri  
**Kabul:** GA4 Realtime'da sayfa görüntüleme görünüyor

#### T1-4: /tarama Navigasyona Ekle (30 dk)
**Dosya:** index.html, ozet.html, gucu_yuksek.html nav/header bölümü  
**Ekle:** "🔍 Tarayıcı" linki  
**Kabul:** Her sayfadan /tarama'ya erişilebiliyor

#### T1-5: Startup Cache (2 saat)
**Dosya:** `/root/bist30/app.py`  
**Ekle:** BUG-6'daki `_save_cache_snapshot()` ve `_load_cache_snapshot()` fonksiyonları  
**Entegre:** `_refresh_data()` sonunda save çağır, uygulama başında load çağır  
**Kabul:** Restart sonrası anında eski veri gösteriyor

---

### TIER 2 — BU AY (Her biri 1-3 gün)

#### T2-1: KAP Entegrasyonu — Gerçek Haber Kaynağı (3 gün)

**Neden önemli:** Hallucination'ı tamamen ortadan kaldırır. AI artık "üretmez", "özetler".

**app.py'e eklenecek fonksiyonlar:**

```python
import requests
from datetime import timedelta

# Cache — her ticker için son KAP verileri
_kap_cache: dict = {}       # {ticker: {"data": [...], "ts": float}}
_kap_lock = threading.Lock()
_KAP_TTL  = 900             # 15 dakika

def fetch_kap_disclosures(ticker: str, days: int = 30) -> list:
    """KAP API'sinden gerçek bildirimler çek, cache'le."""
    with _kap_lock:
        cached = _kap_cache.get(ticker, {})
        if cached and (time.time() - cached.get("ts", 0)) < _KAP_TTL:
            return cached["data"]

    oid = KAP_MEMBER_OIDS.get(ticker)
    if not oid:
        return []

    try:
        r = requests.get(
            f"https://www.kap.org.tr/tr/api/disc/memberRelated/company/{oid}",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 BorsaPusula/2.0"},
        )
        items = r.json() or []
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        for it in items:
            try:
                pub = datetime.fromisoformat(it.get("publishDate", "")[:19])
                if pub >= cutoff:
                    recent.append({
                        "date":    pub.strftime("%d.%m.%Y"),
                        "subject": it.get("subject", ""),
                        "type":    it.get("disclosureClass", ""),
                        "url":     f"https://www.kap.org.tr/tr/Bildirim/{it.get('id', '')}",
                    })
            except Exception:
                continue
        result = recent[:10]
        with _kap_lock:
            _kap_cache[ticker] = {"data": result, "ts": time.time()}
        return result
    except Exception as e:
        logger.warning("KAP fetch [%s]: %s", ticker, e)
        return []


def summarize_kap_for_investor(ticker: str, name: str, disclosures: list) -> str | None:
    """KAP bildirimlerini AI ile yatırımcı dilinde özetle — Hallucination YOK."""
    if not disclosures:
        return None
    today_str = datetime.now().strftime("%d %B %Y")
    texts = "\n".join([
        f"- {d['date']}: {d['subject']} [{d['type']}]"
        for d in disclosures[:5]
    ])
    prompt = (
        f"Bugün {today_str}. Aşağıdakiler {ticker} ({name}) şirketinin "
        f"KAP (Kamuyu Aydınlatma Platformu) resmi bildirimleridir:\n\n"
        f"{texts}\n\n"
        f"Bu bildirimleri bireysel yatırımcı için 2 cümleyle Türkçe özetle. "
        f"Teknik jargonu sade dile çevir. "
        f"SADECE bu gerçek bildirimlerden hareket et — ek yorum veya tahmin yapma."
    )
    return _gemini_call_with_fallback(prompt)
```

**Yeni `/api/hisse/<ticker>/kap-disclosures` endpoint:**
```python
@app.route("/api/hisse/<ticker>/kap-disclosures")
@limiter.limit("20 per minute")
def api_kap_disclosures(ticker):
    ticker = ticker.upper()
    disclosures = fetch_kap_disclosures(ticker, days=30)
    kap_oid     = KAP_MEMBER_OIDS.get(ticker, "")
    return safe_json({
        "ticker":       ticker,
        "disclosures":  disclosures,
        "kap_url":      f"https://www.kap.org.tr/tr/sirket/{kap_oid}" if kap_oid else "",
        "count":        len(disclosures),
    })
```

**hisse.html'e yeni "KAP Bildirimleri" sekmesi:**
```html
<div class="tab-btn" onclick="switchTab('kap')">📋 KAP</div>

<div id="tabKap" class="tab-content" style="display:none">
  <div id="kapList"></div>
</div>

<script>
async function loadKapDisclosures() {
  const res  = await fetch(`/api/hisse/${TICKER}/kap-disclosures`);
  const data = await res.json();
  const list = document.getElementById('kapList');
  if (!data.disclosures || data.disclosures.length === 0) {
    list.innerHTML = '<p style="color:#8b949e;font-size:13px">Son 30 günde KAP bildirimi yok.</p>';
    return;
  }
  list.innerHTML = data.disclosures.map(d => `
    <div style="padding:10px 0;border-bottom:1px solid #21262d">
      <div style="font-size:12px;color:#8b949e">${d.date} · ${d.type}</div>
      <a href="${d.url}" target="_blank" rel="noopener"
         style="font-size:13px;color:#58a6ff;text-decoration:none">
        ${d.subject} ↗
      </a>
    </div>
  `).join('');
}
</script>
```

**Kabul kriteri:** AKBNK hisse sayfasında "KAP" sekmesi açıldığında son 30 günlük gerçek bildirimler listeleniyor.

---

#### T2-2: AI Rolünü Değiştir — Üretici → Özetleyici (1 gün)

**Mevcut akış:** `get_ai_news(ticker)` → Gemini'ye "haber yaz" → Hallucination  
**Yeni akış:** `fetch_kap_disclosures(ticker)` → `summarize_kap_for_investor()` → Gerçek

**api_hisse_news() fonksiyonunu güncelle:**
```python
@app.route("/api/hisse/<ticker>/news")
def api_hisse_news(ticker):
    ticker = ticker.upper()
    
    # 1. KAP'tan gerçek bildirimleri al
    disclosures = fetch_kap_disclosures(ticker, days=7)
    
    if disclosures:
        # 2. AI sadece Türkçe özetleme yapıyor — uydurmuyor
        summary = summarize_kap_for_investor(
            ticker,
            STOCK_NAMES.get(ticker, ticker),
            disclosures
        )
        if summary:
            return safe_json({"news": summary, "source": "kap_ai", 
                              "disclosure_count": len(disclosures)})
    
    # 3. KAP bildirimi yoksa genel AI haberi (mevcut davranış, ama düzeltilmiş prompt)
    news = get_ai_news(ticker)
    return safe_json({"news": news or [], "source": "gemini_general"})
```

**Kabul kriteri:** Haber kaynağı "kap_ai" olduğunda gerçek KAP bildirimleri özetleniyor, tarih tutarlı.

---

#### T2-3: /gundem — Yeni Tam Sayfa (2 gün)

**app.py'e route:**
```python
@app.route("/gundem")
def gundem():
    return render_template("gundem.html")

@app.route("/api/gundem")
@limiter.limit("30 per minute")
def api_gundem():
    """Piyasa Gündem Merkezi — sinyal değişimleri + KAP + makro."""
    with _lock:
        stocks = list(_cache["data"])
    
    # Bugün sinyal değişen hisseler
    today = datetime.now().strftime("%d.%m.%Y")
    new_signals = [s for s in stocks
                   if s.get("signal_date") == today and s.get("signal") != "BEKLE"]
    
    # En yüksek ADX'li AL hisseler (güçlü trend)
    strong_al = sorted(
        [s for s in stocks if s.get("signal") == "AL"],
        key=lambda x: float(str(x.get("indicators",{})
                               .get("adx",{}).get("label","ADX 0")
                               ).replace("ADX","").strip() or 0),
        reverse=True
    )[:8]
    
    return safe_json({
        "new_signals":   new_signals,
        "strong_al":     strong_al,
        "updated_at":    datetime.now().strftime("%d.%m.%Y %H:%M"),
        "signal_summary": {
            "al":    sum(1 for s in stocks if s.get("signal") == "AL"),
            "sat":   sum(1 for s in stocks if s.get("signal") == "SAT"),
            "bekle": sum(1 for s in stocks if s.get("signal") == "BEKLE"),
        }
    })
```

**gundem.html sayfa yapısı:**
```
Piyasa Gündem Merkezi — borsapusula.com/gundem

┌─ Bugün Değişen Sinyaller (SSE/polling) ──────┐
│  ENJSA → AL (bugün, IDEAL giriş)             │
│  TTRAK → SAT (bugün)                          │
└───────────────────────────────────────────────┘

┌─ En Güçlü Trendler (ADX sıralamalı) ─────────┐
│  ASELS ADX:41 | IYI | TP:508₺                │
│  IEYHO ADX:38 | ...                           │
└───────────────────────────────────────────────┘

┌─ KAP Bildirimleri (son 48 saat) ─────────────┐
│  [KAP'tan gerçek veriler]                     │
└───────────────────────────────────────────────┘

┌─ Makro Takvim ────────────────────────────────┐
│  22 Mayıs: TCMB Faiz Kararı                  │
│  31 Mayıs: Enflasyon açıklaması              │
│  15 Haz: Q1 Bilanço son gün                  │
└───────────────────────────────────────────────┘
```

---

#### T2-4: /karsilastir — Hisse Karşılaştırma (2 gün)

**app.py route:**
```python
@app.route("/karsilastir")
def karsilastir():
    tickers_param = request.args.get("tickers", "")
    return render_template("karsilastir.html", tickers_param=tickers_param)

@app.route("/api/karsilastir")
@limiter.limit("20 per minute")
def api_karsilastir():
    tickers = [t.strip().upper() for t in
               request.args.get("tickers", "").split(",")
               if t.strip()][:4]
    
    with _lock:
        data_map = {s["ticker"]: s for s in _cache["data"]}

    results = []
    for ticker in tickers:
        s = data_map.get(ticker, {})
        adx_label = s.get("indicators", {}).get("adx", {}).get("label", "")
        try:
            adx_val = float(adx_label.replace("ADX", "").strip())
        except (ValueError, TypeError):
            adx_val = None
        results.append({
            "ticker":        ticker,
            "name":          STOCK_NAMES.get(ticker, ticker),
            "signal":        s.get("signal"),
            "price":         s.get("price"),
            "change_pct":    s.get("change_pct"),
            "adx":           adx_val,
            "signal_bars":   s.get("signal_bars"),
            "entry_quality": s.get("entry_quality"),
            "sl_level":      s.get("sl_level"),
            "tp1":           s.get("tp1"),
            "tp2":           s.get("tp2"),
            "rr_ratio":      s.get("rr_ratio"),
            "rsi":           s.get("rsi"),
            "sector":        s.get("sector"),
            "bull_score":    s.get("bull_score"),
        })
    return safe_json({"stocks": results})
```

**SEO:** `<title>{{ tickers }} Karşılaştırma — BorsaPusula</title>`  
**URL yapısı:** `/karsilastir?tickers=AKBNK,GARAN` (paylaşılabilir)  
**Kabul kriteri:** 2 hisse yan yana tüm metriklerle görünüyor.

---

#### T2-5: Blog FAQPage Schema (3 saat)

**blog_content.py** — her makale dict'ine `faqs` listesi ekle:
```python
# Örnek — supertrend makalesi için:
"faqs": [
    {"q": "Supertrend indikatörü ne işe yarar?",
     "a": "Supertrend, ATR tabanlı bantlarla fiyat trend yönünü gösterir..."},
    {"q": "BorsaPusula hangi Supertrend parametrelerini kullanıyor?",
     "a": "Supertrend(10,3) — 10 günlük ATR, 3 çarpan. BIST30 optimize."},
    {"q": "Supertrend tek başına sinyal olarak yeterli mi?",
     "a": "Hayır. ADX≥25 ve EMA12/EMA99 üçü birden gerekli."},
]
```

**blog_article.html** — mevcut schema bloklarından sonra:
```html
{% if article.faqs %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {% for faq in article.faqs %}{
      "@type": "Question",
      "name": {{ faq.q | tojson }},
      "acceptedAnswer": {"@type": "Answer", "text": {{ faq.a | tojson }}}
    }{% if not loop.last %},{% endif %}{% endfor %}
  ]
}
</script>
{% endif %}
```

---

#### T2-6: /ozet/\<tarih\> — Geçmiş Günlük Özet (1 gün)

**app.py'e ekle:**
```python
SNAPSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

def _save_daily_snapshot(stocks: list):
    """Seans kapandıktan sonra (17:00 TR = 14:00 UTC) günlük snapshot yaz."""
    now = datetime.now()
    if now.hour < 14:  # UTC — Türkiye seans saati henüz bitmedi
        return
    fname = os.path.join(SNAPSHOTS_DIR, f"{now.strftime('%Y-%m-%d')}.json")
    if os.path.exists(fname):
        return
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({"date": now.strftime("%Y-%m-%d"), "stocks": stocks,
                       "saved_at": now.isoformat()}, f, ensure_ascii=False)
        logger.info("Günlük snapshot: %s", fname)
    except Exception as e:
        logger.error("Snapshot hatası: %s", e)

@app.route("/ozet/<tarih>")
def ozet_gecmis(tarih):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", tarih):
        abort(404)
    fname = os.path.join(SNAPSHOTS_DIR, f"{tarih}.json")
    if not os.path.exists(fname):
        abort(404)
    try:
        snap = json.load(open(fname, encoding="utf-8"))
    except Exception:
        abort(404)
    return render_template("ozet.html", historical=snap, historical_date=tarih)
```

---

### TIER 3 — SONRAKI SPRINT (1+ hafta)

#### T3-1: "Sinyalin Hikayesi" Feature
En güçlü farklılaştırıcı. Hisse AL sinyali aldığında sinyal tarihini al, o tarihe yakın KAP bildirimlerini eşleştir. Hem teknik hem fundamentali aynı ekranda sun.

```python
# hisse.html — yeni "Sinyal Hikayesi" bölümü
def get_signal_story(ticker, signal_date):
    """Sinyal tarihi etrafındaki KAP bildirimlerini getir (-15/+5 gün)."""
    from datetime import datetime, timedelta
    sig_dt   = datetime.strptime(signal_date, "%d.%m.%Y")
    window_s = sig_dt - timedelta(days=15)
    window_e = sig_dt + timedelta(days=5)
    disclosures = fetch_kap_disclosures(ticker, days=60)
    return [d for d in disclosures
            if window_s <= datetime.strptime(d["date"], "%d.%m.%Y") <= window_e]
```

#### T3-2: Web Push Bildirimleri (VAPID)
```bash
pip install pywebpush
```
sw.js'e push + notificationclick event listener ekle.  
`/api/push/subscribe` endpoint — endpoint + keys kaydet.  
Sinyal değişiminde push gönder (günde max 2).

#### T3-3: Portföy Sunucu Taraflı (Token Bazlı)
UUID token → `/api/portfolio/<token>` GET/POST.  
KVKK temiz (isim/email yok). QR veya link ile paylaşılabilir.

#### T3-4: Blog ↔ Hisse Bağlantısı
`blog_content.py`'e `related_tickers` alanı.  
Hisse sayfasında ilgili blog makaleleri göster.  
Blog makalesinde ilgili hissenin güncel sinyali göster.

#### T3-5: Sinyal Marker Tooltip
LightweightCharts'ta marker'a hover/click ile: "Bu AL sinyalinde giriş: X₺, şu an: Y₺, getiri: Z%"

---

## 10. TEST PROSEDÜRLERI (Her Özellik İçin)

```bash
VPS=root@135.181.206.109

# BUG-1: Hallucination fix
ssh $VPS "curl -s http://localhost:8003/api/hisse/ASELS/news" | python3 -c "
import json,sys,datetime
d=json.load(sys.stdin); news=d.get('news',''); today=datetime.date.today()
import re; dates=re.findall(r'202\d-\d{2}-\d{2}', news)
future=[d for d in dates if d > str(today)]
print('PASS' if not future else 'FAIL — Gelecek tarihler: '+str(future))
"

# BUG-2: ADX fix
ssh $VPS "curl -s http://localhost:8003/api/hisse/ASELS/signal-explanation" | python3 -c "
import json,sys; d=json.load(sys.stdin); exp=d.get('explanation','')
print('PASS' if 'ADX 0' not in exp else 'FAIL — ADX 0 hala var')
"

# BUG-4: KAP linki
ssh $VPS "curl -s http://localhost:8003/api/market-news" | python3 -c "
import json,sys; d=json.load(sys.stdin)
items=d.get('items',[]); missing=[i['ticker'] for i in items if not i.get('kap_url')]
print('PASS' if not missing else 'FAIL — KAP URL yok: '+str(missing))
"

# T1-3: GA4
ssh $VPS "grep -c 'gtag' /root/bist30/templates/index.html" | python3 -c "
import sys; n=int(sys.stdin.read().strip()); print('PASS' if n>0 else 'FAIL — gtag yok')
"

# T2-1: KAP entegrasyon
ssh $VPS "curl -s http://localhost:8003/api/hisse/AKBNK/kap-disclosures" | python3 -c "
import json,sys; d=json.load(sys.stdin)
count=d.get('count',0); print('PASS (%d bildirim)' % count if count>0 else 'FAIL — bildirim yok')
"

# T2-3: /gundem sayfası
ssh $VPS "curl -s -o /dev/null -w '%{http_code}' http://localhost:8003/gundem"
# 200 bekleniyor

# T2-4: /karsilastir
ssh $VPS "curl -s 'http://localhost:8003/api/karsilastir?tickers=AKBNK,GARAN'" | python3 -c "
import json,sys; d=json.load(sys.stdin)
stocks=d.get('stocks',[]); print('PASS' if len(stocks)==2 else 'FAIL')
"
```

---

## 11. LOKAL KOD SENKRONIZASYONU

**⚠️ Kritik:** VPS app.py 3520 satır, lokal backup 2384 satır — **1136 satır fark.**  
Lokal dosyalar (Mac) güncel değil. Geliştirme VPS üzerinde yapılmalı veya önce pull edilmeli.

```bash
# VPS'ten lokal'e çek:
scp root@135.181.206.109:/root/bist30/app.py \
    "/Users/mac/Bist ve BTC/Bist30/app.py"
scp -r root@135.181.206.109:/root/bist30/templates/ \
    "/Users/mac/Bist ve BTC/Bist30/templates/"
scp root@135.181.206.109:/root/bist30/blog_content.py \
    "/Users/mac/Bist ve BTC/Bist30/blog_content.py"
```

---

## 12. GENEL SKOR

| Kategori | Puan | Not |
|----------|------|-----|
| Altyapı Kararlılığı | 8/10 | 15+ gün uptime, <20ms response |
| API Doğruluğu | 6/10 | ADX=0 + hallucination aktif |
| Haber/Gündem Kalitesi | 4/10 | Hallucination, KAP linksiz, boş kartlar |
| UI/UX | 7/10 | Temiz tasarım, bazı eksik geri bildirimler |
| Özellik Zenginliği | 9/10 | BIST+ABD+kripto+emtia+tarama kapsamlı |
| SEO Altyapısı | 6/10 | Schema var, GA4 yok, FAQPage yok |
| Performans | 10/10 | Tüm sayfalar <20ms |
| **Genel** | **7.1/10** | Güçlü altyapı, AI güvenilirliği düzeltilmeli |

---

*Birleştirildi: test-raporu.md (29 Nisan) + gelistirme-plani.md (26 Nisan) + haber/gündem ultrathink analizi (1 Mayıs 2026).*  
*Bu belge ajana doğrudan verilebilir — her madde implementation-ready.*

---

# GÜNCELLEME — 2 MAYIS 2026

## §A. SİSTEM DURUMU (2 Mayıs 2026)

| Metrik | Değer | Durum |
|--------|-------|-------|
| Uptime | 18 gün 12 saat | ✅ |
| RAM | 1.5G / 3.7G (%41) | ✅ |
| Disk | 8.7G / 38G (%23) | ✅ |
| Load Average | 0.68 / 0.45 / 0.34 | ✅ |
| Gunicorn worker RSS | 166MB | ✅ (normal) |
| Journal log boyutu | **154MB** | ✅ ⬇️ (1 Mayıs'ta 1.1GB'tı — log rotation uygulandı) |
| app.py satır sayısı | **4882 satır** | 1 Mayıs'ta 3520'ydi, +1362 satır yeni özellik |
| Toplam hisse | 145 (BIST + US genişletilmiş) | ✅ |
| AL / SAT / BEKLE | 37 / 3 / 104 | ✅ |
| Prefetch | 8/8 başarılı (06:39–06:44) | ✅ Gemini 429 sorunu çözüldü |

---

## §B. 1 MAYIS'TAN BU YANA ÇÖZÜLEN BUGLAR ✅

| Bug | Durum | Notlar |
|-----|-------|--------|
| /gundem → 404 | ✅ **ÇÖZÜLDÜ** | Artık 200, sayfa tam çalışıyor |
| /karsilastir → 404 | ✅ **ÇÖZÜLDÜ** | Artık 200, sayfa tam çalışıyor |
| /tarama navigasyonda yok | ✅ **ÇÖZÜLDÜ** | Header'da görünüyor |
| /gundem ve /karsilastir navigasyonda yok | ✅ **ÇÖZÜLDÜ** | Araçlar menüsünde var |
| GA4 analytics | ✅ **ÇÖZÜLDÜ** | G-WXLPNFHYLP tüm sayfalarda aktif |
| Gemini hallucination | ✅ **BÜYÜK ÖLÇÜDE ÇÖZÜLDÜ** | KURAL 1–4 prompt sistemi uygulandı |
| Log boyutu 1.1GB | ✅ **ÇÖZÜLDÜ** | 154MB'a düştü |
| KAP entegrasyonu yok | ✅ **ÇÖZÜLDÜ** | `/api/hisse/TICKER/kap` real-time KAP bildirimleri döner |
| Haber kaynağı hallucination | ✅ **BÜYÜK ÖLÇÜDE ÇÖZÜLDÜ** | `/api/hisse/TICKER/news` artık `source=kap_ai` → KAP verisi AI özetliyor |
| Boş Gündem kartı (HEKTS) | ✅ **2 MAYIS ÇÖZÜLDÜ** | `_skip_prefixes` empty snippet guard eklendi |
| Gemini 429 rate limit | ✅ **ÇÖZÜLDÜ** | Prefetch frekansı düşürüldü |

---

## §C. AKTİF BUGLAR (2 Mayıs 2026)

### BUG-C1 (KRİTİK): ADX Değeri Null — Hisse Sayfasında "ADX null" Görünüyor

**Kanıt:**
```
ASELS: adx=None | indicators.adx.label=ADX 41
EREGL: adx=None | indicators.adx.label=ADX 28
HEKTS: adx=None | indicators.adx.label=ADX 31
```

**Sorun:** `/api/data` her hisse için `adx: null` döner. Hisse sayfası JS kodu `s.adx` okur → `'ADX ' + null` = `"ADX null"`. SSR kısmında `{% if ssr_signal.adx %}` falsy olduğu için ADX cümlesi hiç render edilmez.

**Kök neden:** Sinyal hesaplama kodunda ADX değeri `indicators.adx.label = "ADX 41"` şeklinde nested yapıda saklanıyor ama üst düzey `adx` alanı populate edilmiyor.

**Dosya:** `/root/bist30/app.py` — sinyal hesaplama fonksiyonu

**Fix:** Sinyal dict'i dönerken `adx` alanını `indicators.adx.label`'dan parse et:

```python
# Sinyal dict'e eklenecek (her hisse için hesaplama sonrasında):
_adx_label = indicators.get("adx", {}).get("label", "")   # "ADX 41"
try:
    adx_val = float(_adx_label.replace("ADX", "").strip()) if _adx_label else 0.0
except (ValueError, TypeError):
    adx_val = 0.0

# Dict'e ekle:
signal_dict["adx"] = adx_val
signal_dict["di_plus"] = ...   # indicators.adx.value'dan parse ("DI+33/DI-11")
signal_dict["di_minus"] = ...
```

**Alternatif fix (daha hızlı):** `/api/data` response'unu veren endpoint'te her stock için post-process:
```python
for s in stocks:
    if s.get("adx") is None:
        adx_label = s.get("indicators", {}).get("adx", {}).get("label", "")
        try:
            s["adx"] = float(adx_label.replace("ADX", "").strip()) if adx_label else 0.0
        except (ValueError, TypeError):
            s["adx"] = 0.0
        # di_plus / di_minus de parse et:
        adx_value = s.get("indicators", {}).get("adx", {}).get("value", "")  # "DI+33/DI-11"
        parts = re.findall(r'\d+', adx_value)
        if len(parts) >= 2:
            s["di_plus"] = float(parts[0])
            s["di_minus"] = float(parts[1])
```

**Etki:** Hisse sayfasında gösterge kutusu "ADX null" yerine "ADX 41" gösterir. SSR SEO metninde `"ADX değeri 41."` görünür.

---

### BUG-C2 (ORTA): Gündem Widget — İki Farklı Haber Sistemi Çakışması

**Sorun:** Uygulama iki ayrı haber pipeline'ı kullanıyor:

| Sistem | Nerede | Kaynak | Kalite |
|--------|--------|--------|--------|
| `_news_cache` (eski) | `api_market_news()` widget | Google Search grounding | ⚠️ Hallucination riski hâlâ var |
| `kap_ai` (yeni) | `/api/hisse/TICKER/news` | Gerçek KAP verisi → AI özeti | ✅ Güvenilir |

**Neden sorun:** Gündem widget'ı eski sistemi kullanıyor. Hisse sayfası yeni KAP-AI sistemini kullanıyor. Widget'ta HEKTS gibi hisseler için "kayda değer gelişme yok" dönerken hisse sayfasında gerçek KAP verileri var.

**Fix:** `api_market_news()` fonksiyonunu güncelle — `_news_cache` yerine `/api/hisse/TICKER/news` ile aynı kap_ai pipeline'ı kullan:

```python
# api_market_news() içinde, her ticker için:
# Önce kap_ai cache'e bak (_kap_news_cache veya _news_cache'deki kap_ai source'u)
# Yoksa get_ai_news() yerine _get_kap_based_news(ticker) kullan

def _get_kap_based_news_snippet(ticker: str, name: str) -> tuple[str, str]:
    """KAP bildirimleri üzerinden snippet üretir. source=kap_ai döner."""
    discs = fetch_kap_disclosures(ticker, days=14)
    if not discs:
        return "", "no_kap"
    # En son 3 bildirimi özetle (Gemini'siz, sadece tarih+konu)
    lines = []
    for d in discs[:3]:
        lines.append(f"{d['date']}: {d['subject']}")
    snippet = " | ".join(lines)
    return snippet[:220], "kap"
```

**Not:** Bu adım isteğe bağlı. BUG-C1 daha öncelikli.

---

### BUG-C3 (KÜÇÜK): KAP URL Gündem Widget'ta Generic

**Sorun:** `api_market_news()` kap_url değeri: `https://www.kap.org.tr/tr/bildirim-sorgu?q=ASELS` (arama sayfası). Hisse sayfasındaki KAP kutusu ise `https://www.kap.org.tr/tr/Bildirim/1599128` (direkt bildirim) dönüyor.

**Fix:** `kap_url_for(ticker)` fonksiyonunu şirket OID tablosuyla güncelle (master-plan §5.4'teki `KAP_MEMBER_OIDS` tablosunu kullan):
```python
def kap_url_for(ticker):
    oid = KAP_MEMBER_OIDS.get(ticker)
    if oid:
        return f"https://www.kap.org.tr/tr/sirket-bilgileri/bildirimleri/{oid}"
    return f"https://www.kap.org.tr/tr/bildirim-sorgu?q={ticker}"
```

---

## §D. GÜNDEM & HABERLER BÖLÜMÜ — DERİN ANALİZ

### D.1 Mevcut Durum (2 Mayıs 2026)

**Hisse Sayfası Haberleri (`/api/hisse/TICKER/news`):**
```json
{
  "source": "kap_ai",
  "kap_count": 4,
  "news": "ASELSAN'ın son 7 günlük KAP bildirimlerinin bireysel yatırımcılar için özeti:\n\n* 30 Nisan 2026: Şirket, yeni bir sözleşme imzaladığını duyurdu.\n* 28 Nisan 2026: Finansal raporlar yayınlandı...",
  "kap_url": "..."
}
```
✅ **Güvenilir.** Gerçek KAP verisi → AI özeti → tarih hallucination riski minimal.

**Gündem Widget (`/api/market-news`):**
```json
{
  "items": [
    {"ticker": "HEKTS", "snippet": "", "source": "news"},  // ← BUG-C1 ile DÜZELTİLDİ
    {"ticker": "ASELS", "snippet": "ASELSAN 2026 ilk çeyrekte...", "source": "news"}
  ]
}
```
⚠️ **Eski pipeline.** `source=news` = Google Search grounding, hallucination riski var.

### D.2 Görsel UX Sorunları

1. **Boş snippet kartı** — HEKTS gibi hisseler için snippet "" olunca `<div class="gnm-text"></div>` render edilir → görsel boşluk. (**2 Mayıs'ta fix edildi**)
2. **Snippet çok kısa kesildi** — 220 karakter limiti haberin ortasında kesiyor, "…" ile bitiyor. Kullanıcı devamını göremez.
3. **"Haber yükleniyor…" spinner durumu** — restart sonrası tüm kartlar bu durumda kalıyor, 30 saniye sonra yenileniyor. Kullanıcı için sinir bozucu.
4. **KAP linki generic** — "KAP ↗" tıklandığında arama sayfasına gidiyor, direkt bildirimlere değil.
5. **Scroll limiti** — Gündem kartları yatay scroll ile 5 kart. 5'ten fazlası görünmüyor, "/gundem" sayfasına yönlendirme var ama belirgin değil.
6. **Mobilde kart boyutu** — Gündem kartları mobilde çok geniş, scroll deneyimi zor.

### D.3 Rakiplerle Kıyaslama — Haber Bölümü

| Platform | Haber Kaynağı | Gerçek Zaman | Şirket Özelinde | Sinyalle Bağlantılı |
|----------|--------------|--------------|-----------------|---------------------|
| **BorsaPusula** | KAP-AI (hisse), Google-AI (widget) | 15dk+ gecikme | ✅ Her hisse | ✅ Sadece AL/SAT hisseleri |
| Bigpara | İnsan editörler + ajanslar | Gerçek zamanlı | ⚠️ Seçili | ❌ |
| ForInvest | KAP resmi + Bloomberg | Gerçek zamanlı | ✅ | ❌ |
| BistScan | Yok | — | ❌ | ✅ |
| Midas | Yatırım notları | Seçili | ⚠️ | ❌ |

**BorsaPusula'nın stratejik avantajı:** Tek platform olarak hem KAP bildirimi hem de teknik sinyal birlikte sunuluyor. Bu gap rakiplerinde yok.

---

## §E. MAKRO HABER & GÜNDEM İŞ PLANI

### E.1 Ne Eksik?

Şu an `/api/macro` endpoint'i **fiyat verisi** (XU100, USDTRY, BTC, ALTIN vb.) döndürüyor ve homepage'de kayan scrollbar olarak gösteriliyor. **Ama habere dönüşmüyor.**

Eksik olan:
1. **Makro haber başlıkları** — TCMB faiz kararı, TÜFE açıklandı, Merkez Bankası toplantısı
2. **Ekonomik takvim** — Önümüzdeki haftanın kritik tarihleri (TUIK, TCMB, Fed)
3. **Sektör bazlı güncelleme** — "Enerji sektörü bugün ortalama +3.2% yükseldi"
4. **Makro bağlam** — "Dolar/TL 45.17'de, BIST100 %0.96 artı, petrol %3.34 düşüşte — bunun ne anlama geldiği"

### E.2 Teknik İmplementasyon Planı

#### AŞAMA 1 — Ücretsiz Kaynaklar (Önce Bunu Yap)

**A) RSS Feed Aggregatör:**
```python
# /root/bist30/app.py'ye eklenecek

import feedparser

_MACRO_RSS_SOURCES = [
    # Türkiye odaklı, Türkçe
    ("Reuters TR", "https://tr.reuters.com/rssFeed/businessNews"),
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),
    ("Dünya Gazetesi", "https://www.dunya.com/rss/ekonomi.xml"),
    ("Haberler.com Ekonomi", "https://www.haberler.com/ekonomi/rss/"),
    # TCMB resmi duyurular
    ("TCMB", "https://www.tcmb.gov.tr/wps/wcm/connect/tcmb+tr/tcmb+tr/main+menu/duyurular/basin+duyurulari/"),
]

_macro_news_cache = []
_macro_news_ts = 0.0
_MACRO_NEWS_TTL = 1800  # 30 dakika

def _fetch_macro_rss() -> list:
    """Makro haber RSS'lerini çek, son 24 saatin başlıklarını döndür."""
    results = []
    cutoff = datetime.now() - timedelta(hours=24)
    for source_name, url in _MACRO_RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                try:
                    pub = datetime(*entry.published_parsed[:6])
                    if pub < cutoff:
                        continue
                    results.append({
                        "title": entry.title,
                        "url": entry.link,
                        "source": source_name,
                        "published": pub.strftime("%H:%M"),
                        "category": "makro"
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning("RSS fetch [%s]: %s", source_name, e)
    # Zamana göre sırala (yeni önce)
    results.sort(key=lambda x: x.get("published", ""), reverse=True)
    return results[:15]

def _update_macro_news_bg():
    """Arka planda RSS güncelleme döngüsü."""
    global _macro_news_cache, _macro_news_ts
    while True:
        try:
            news = _fetch_macro_rss()
            _macro_news_cache = news
            _macro_news_ts = time.time()
            logger.info("Makro RSS güncellendi: %d haber", len(news))
        except Exception as e:
            logger.warning("Makro RSS güncelleme hatası: %s", e)
        time.sleep(_MACRO_NEWS_TTL)

# Uygulama başlangıcında başlat:
threading.Thread(target=_update_macro_news_bg, daemon=True).start()
```

**B) Yeni API Endpoint:**
```python
@app.route("/api/macro-news")
@limiter.limit("60 per minute")
def api_macro_news():
    """Makro ekonomi haberleri — RSS tabanlı, gerçek zamanlı."""
    return safe_json({
        "items": _macro_news_cache,
        "updated_at": datetime.fromtimestamp(_macro_news_ts).strftime("%H:%M") if _macro_news_ts else "—",
        "count": len(_macro_news_cache)
    })
```

**C) Gereksinim:**
```bash
cd /root/bist30 && venv/bin/pip install feedparser
```

---

#### AŞAMA 2 — TCMB Resmi Veri (Yüksek Değerli)

**A) TCMB Elektronik Veri Dağıtım Sistemi (EVDS):**
```python
# TCMB EVDS ücretsiz API - kayıt gerekiyor (tcmb.gov.tr/evds)
TCMB_API_KEY = os.getenv("TCMB_API_KEY", "")

_TCMB_SERIES = {
    "faiz":    "TP.MB.C2",     # Merkez Bankası politika faizi
    "usdtry":  "TP.DK.USD.A.YTL",  # USD/TRY
    "tufe":    "TP.FG.J0",     # TÜFE (aylık)
}

def fetch_tcmb_policy_rate() -> dict:
    """TCMB politika faizini çek."""
    if not TCMB_API_KEY:
        return {}
    url = (f"https://evds2.tcmb.gov.tr/service/evds/"
           f"series=TP.MB.C2&startDate=01-01-2026"
           f"&endDate={datetime.now().strftime('%d-%m-%Y')}"
           f"&type=json&key={TCMB_API_KEY}")
    try:
        r = requests.get(url, timeout=8)
        data = r.json()
        # Parse son değeri
        items = data.get("items", [])
        if items:
            last = items[-1]
            return {"rate": last.get("TP_MB_C2"), "date": last.get("Tarih")}
    except Exception as e:
        logger.warning("TCMB EVDS: %s", e)
    return {}
```

---

#### AŞAMA 3 — Ekonomik Takvim (Statik + Dinamik)

**A) Statik Takvim (Hemen Yapılabilir):**
```python
# Bilinen ekonomik takvim verileri (yılın başında güncellenir)
ECONOMIC_CALENDAR_2026 = [
    # TCMB Para Politikası Kurulu Toplantıları
    {"date": "2026-05-22", "event": "TCMB PPK Toplantısı", "importance": "HIGH", "source": "TCMB"},
    {"date": "2026-06-26", "event": "TCMB PPK Toplantısı", "importance": "HIGH", "source": "TCMB"},
    {"date": "2026-07-23", "event": "TCMB PPK Toplantısı", "importance": "HIGH", "source": "TCMB"},
    # TUIK Enflasyon Verileri
    {"date": "2026-05-05", "event": "Nisan 2026 TÜFE Açıklaması", "importance": "HIGH", "source": "TUIK"},
    {"date": "2026-06-03", "event": "Mayıs 2026 TÜFE Açıklaması", "importance": "HIGH", "source": "TUIK"},
    # Fed Faiz Kararları
    {"date": "2026-05-07", "event": "Fed Faiz Kararı", "importance": "HIGH", "source": "FED"},
    {"date": "2026-06-18", "event": "Fed Faiz Kararı", "importance": "HIGH", "source": "FED"},
    {"date": "2026-07-30", "event": "Fed Faiz Kararı", "importance": "HIGH", "source": "FED"},
    # BDDK/BIST özel
    {"date": "2026-05-15", "event": "BIST Mart 2026 İşlem İstatistikleri", "importance": "MED", "source": "BIST"},
]

@app.route("/api/economic-calendar")
def api_economic_calendar():
    today = datetime.now().date()
    upcoming = [
        e for e in ECONOMIC_CALENDAR_2026
        if datetime.strptime(e["date"], "%Y-%m-%d").date() >= today
    ]
    # Geçen olayları da döndür (son 7 gün)
    past = [
        e for e in ECONOMIC_CALENDAR_2026
        if today - timedelta(days=7) <= datetime.strptime(e["date"], "%Y-%m-%d").date() < today
    ]
    return safe_json({
        "upcoming": upcoming[:5],
        "past": past[:3],
        "today": [e for e in upcoming if e["date"] == today.strftime("%Y-%m-%d")]
    })
```

---

#### AŞAMA 4 — Makro AI Yorumu (Gelişmiş)

**A) Günlük Makro Özet (Gemini):**
```python
def get_macro_ai_summary() -> str:
    """Günlük makro ekonomi özeti — Gemini ile üret."""
    macro = _macro_cache.get("data", {})  # /api/macro'nun cache'i
    
    xu100  = next((m["price"] for m in macro.get("items", []) if m["label"]=="XU100"), None)
    usdtry = next((m["price"] for m in macro.get("items", []) if m["label"]=="USDTRY"), None)
    gold   = next((m["price"] for m in macro.get("items", []) if m["label"]=="ALTIN"), None)
    oil    = next((m["price"] for m in macro.get("items", []) if m["label"]=="PETROL"), None)

    today = datetime.now().strftime("%d %B %Y")
    prompt = (
        f"Bugün {today}. Türk piyasalarında anlık veriler:\n"
        f"• BIST100: {xu100} ₺\n"
        f"• USD/TRY: {usdtry}\n"  
        f"• Altın: {gold} ₺/gr\n"
        f"• Brent Petrol: {oil} USD\n\n"
        f"KURAL: Sadece bu verileri yorumla. Spekülasyon yapma. Tahmin yapma.\n"
        f"GÖREV: Bireysel yatırımcı için 2 cümlelik Türkçe piyasa özeti. "
        f"Giriş/kapanış cümlesi ekleme."
    )
    _, text = _gemini_call(prompt, _GEMINI_NEWS_ATTEMPTS, timeout=15)
    return text or ""
```

---

### E.3 /gundem Sayfasına Entegrasyon

Mevcut `/gundem` sayfası sinyal-odaklı (ADX sıralamalı hisseler, sinyal değişikliği vb.). Makro haberlerin ekleneceği bölümler:

```
/gundem sayfası yeni yapısı:
┌─────────────────────────────────────────┐
│  📊 MAKRO TABLASI                       │
│  XU100 | USDTRY | ALTIN | PETROL        │  ← Zaten var (macro scroll)
├─────────────────────────────────────────┤
│  📅 BUGÜNÜN AJANDİ                      │  ← YENİ (Ekonomik takvim)
│  14:30 TÜFE Nisan → açıklandı: %3.2    │
│  22:00 Fed Faiz Kararı → Bekleniyor    │
├─────────────────────────────────────────┤
│  📰 MAKRO HABERLER                      │  ← YENİ (RSS tabanlı)
│  Reuters TR | Bloomberg HT | Dünya      │
│  [başlık 1] [saat]                      │
│  [başlık 2] [saat]                      │
├─────────────────────────────────────────┤
│  🎯 BUGÜN SİNYAL DEĞIŞENLER            │  ← Zaten var
│  AL→BEKLE: 2 hisse | BEKLE→AL: 5 hisse │
├─────────────────────────────────────────┤
│  💪 GÜÇLÜ TREND (ADX sıralamalı)       │  ← Zaten var
└─────────────────────────────────────────┘
```

### E.4 RSS Kaynak Değerlendirmesi

| Kaynak | URL | Türkçe | Güncellik | Güvenilirlik | Lisans |
|--------|-----|--------|-----------|--------------|--------|
| Reuters TR | tr.reuters.com/rssFeed | ✅ | Dakika | ⭐⭐⭐⭐⭐ | Ücretsiz RSS |
| Bloomberg HT | bloomberght.com/rss | ✅ | Dakika | ⭐⭐⭐⭐⭐ | Ücretsiz RSS |
| Dünya Gazetesi | dunya.com/rss | ✅ | Saat | ⭐⭐⭐⭐ | Ücretsiz RSS |
| Haberler.com | haberler.com/rss | ✅ | Dakika | ⭐⭐⭐ | Ücretsiz RSS |
| TCMB | tcmb.gov.tr | ✅ | Resmi | ⭐⭐⭐⭐⭐ | Resmi, ücretsiz |

**Tavsiye:** Reuters TR + Bloomberg HT ile başla. `feedparser` kütüphanesi gerektiriyor (`pip install feedparser`).

### E.5 Öncelik Sıralaması

| Öncelik | Aşama | Süre | Etki |
|---------|-------|------|------|
| 🔴 1 | `/api/economic-calendar` — statik takvim | 1 saat | Yüksek değer, sıfır risk |
| 🔴 2 | `/api/macro-news` — RSS aggregatör | 2 saat | Gerçek zamanlı haberler |
| 🟡 3 | /gundem sayfasına entegrasyon | 3 saat | Tüm veri görünür hale gelir |
| 🟡 4 | TCMB EVDS API entegrasyonu | 4 saat | Resmi faiz/enflasyon verisi |
| 🟢 5 | Makro AI yorumu (Gemini) | 2 saat | Bağlam + katma değer |

---

## §F. KAPSAMLI ROTA VE API DURUMU (2 Mayıs 2026)

| URL | HTTP | Süre | Durum |
|-----|------|------|-------|
| / | 200 | 8ms | ✅ |
| /ozet | 200 | 5ms | ✅ |
| /tarama | 200 | 2ms | ✅ |
| /gundem | 200 | 4ms | ✅ (1 Mayıs'ta 404'tü) |
| /karsilastir | 200 | 3ms | ✅ (1 Mayıs'ta 404'tü) |
| /sektor-harita | 200 | 3ms | ✅ |
| /bilanco-takvimi | 200 | 4ms | ✅ |
| /sinyal-performans | 200 | 6ms | ✅ |
| /blog | 200 | 80ms | ⚠️ En yavaş |
| /hisse/AKBNK | 200 | 7ms | ✅ |
| /abd | 200 | 6ms | ✅ |
| /abd/AAPL | 200 | 3ms | ✅ |
| /kripto | 200 | 2ms | ✅ |
| /emtialar | 200 | 3ms | ✅ |
| /altin | 200 | 3ms | ✅ |
| /btc | 200 | 4ms | ✅ |
| /metodoloji | 200 | 3ms | ✅ |
| /hakkinda | 200 | 3ms | ✅ |
| /iletisim | 200 | 5ms | ✅ |
| /hisse/INVALID | 404 | — | ✅ doğru |

| API | HTTP | Boyut | Durum |
|-----|------|-------|-------|
| /api/data | 200 | 112KB | ✅ |
| /api/market-news | 200 | 2.8KB | ✅ (items key) |
| /api/bilanco-mini | 200 | 548B | ✅ |
| /api/tarama | 200 | 31KB | ✅ |
| /api/macro | 200 | ~500B | ✅ 10 makro varlık |
| /api/hisse/ASELS/kap | 200 | ~2KB | ✅ Gerçek KAP bildirimleri |
| /api/hisse/ASELS/news | 200 | ~800B | ✅ source=kap_ai |
| /api/hisse/AKBNK/chart | 200 | — | ✅ |
| /api/hisse/AKBNK/fundamentals | 200 | — | ✅ |
| /api/hisse/AKBNK/mtf | 200 | — | ✅ |

---

## §G. GELİŞTİRME ÖNCELİK SIRASI (GÜNCEL)

### 🔴 TIER 0 — Bu Hafta (Acil)

| # | Görev | Etki | Süre |
|---|-------|------|------|
| G-1 | **BUG-C1: ADX değeri null → parse et** | Hisse sayfası gösterge kutusu bozuk | 30dk |
| G-2 | **Ekonomik Takvim API** (`/api/economic-calendar`) | /gundem sayfasına gündem kazandırır | 1 saat |
| G-3 | **RSS Makro Haber** (`/api/macro-news` + feedparser) | Gerçek haber akışı | 2 saat |

### 🟡 TIER 1 — Bu Ay

| # | Görev | Etki | Süre |
|---|-------|------|------|
| G-4 | /gundem sayfasına ekonomik takvim + RSS haberleri ekle | /gundem'i gerçek haber merkezine dönüştür | 3 saat |
| G-5 | market-news widget'ını kap_ai pipeline'ına geçir | Widget güvenilirliği artar | 2 saat |
| G-6 | Blog sayfası performansı (80ms → <20ms) | /blog çok yavaş | 1 saat |
| G-7 | KAP URL'lerini OID tablosundan al | Direkt bildirim linkleri | 30dk |

### 🟢 TIER 2 — Sonraki Ay

| # | Görev | Etki | Süre |
|---|-------|------|------|
| G-8 | TCMB EVDS API entegrasyonu | Resmi faiz/enflasyon verisi | 4 saat |
| G-9 | Makro AI yorumu (Gemini) | Bağlam + anlam | 2 saat |
| G-10 | /ozet/<tarih> — tarihsel snapshot | SEO değeri yüksek | 6 saat |
| G-11 | Blog FAQPage schema | SEO | 2 saat |
| G-12 | E-posta bülteni — haftanın sinyalleri | Kullanıcı bağlılığı | 1 gün |

---

## §H. BUG-C1 ADX FIX — TAM UYGULAMA KODU

app.py'de `/api/data` endpoint'ini döndüren fonksiyonu bul (muhtemelen `api_data()` adında). Return öncesinde:

```python
@app.route("/api/data")
def api_data():
    with _lock:
        stocks = list(_cache.get("data", []))
        loading = _cache.get("loading", True)
        updated_at = _cache.get("updated_at", "")
    
    # ── ADX NULL FIX ────────────────────────────────────────────
    _ADX_RE = re.compile(r'ADX\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
    _DI_RE  = re.compile(r'DI\+\s*(\d+(?:\.\d+)?)\s*/\s*DI-\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
    for s in stocks:
        if s.get("adx") is None:
            adx_label = s.get("indicators", {}).get("adx", {}).get("label", "")
            adx_value = s.get("indicators", {}).get("adx", {}).get("value", "")
            m = _ADX_RE.search(adx_label)
            s["adx"] = float(m.group(1)) if m else 0.0
            m2 = _DI_RE.search(adx_value)
            if m2:
                s["di_plus"]  = float(m2.group(1))
                s["di_minus"] = float(m2.group(2))
    # ────────────────────────────────────────────────────────────
    
    return safe_json({
        "stocks": stocks,
        "loading": loading,
        "updated_at": updated_at
    })
```

**Test:**
```bash
curl -s http://localhost:8003/api/data | python3 -c "
import json,sys
d=json.load(sys.stdin)
for s in d['stocks'][:5]:
    print(f'{s[\"ticker\"]}: adx={s.get(\"adx\")} di+={s.get(\"di_plus\")} di-={s.get(\"di_minus\")}')
"
# Beklenen: ASELS: adx=41.0 di+=33.0 di-=11.0
```

---

*Güncellendi: 2 Mayıs 2026 — VPS SSH testi + Gündem derin analizi + Makro haber iş planı.*  
*Önceki: 1 Mayıs 2026 versiyon aşağıda korunmaktadır.*

---

# RAKİP ANALİZİ — 3 MAYIS 2026
## yatirimci.ai + borsadirekt.com + Mevcut Rakipler

---

## §R1. YATIRIMCİ.AI — Detaylı Analiz

**Genel:** Pulse şirketi (UK + TR) tarafından geliştirilen AI-öncelikli yatırım platformu.  
**Hedef kitle:** Tüm yatırımcılar, özellikle teknoloji-uyumlu bireysel yatırımcılar.  
**Model:** Freemium — Basic (ücretsiz) + **Plus: 399₺/ay**

### Özellik Listesi

| Kategori | Özellik | Plan |
|----------|---------|------|
| Varlıklar | BIST hisseleri, yatırım fonları, döviz, kripto, altın, emtia, ABD borsaları | Basic |
| AI | Yapay zeka tahmin algoritmaları | Plus |
| AI | Teknik görünüm analizi | Plus |
| AI | Piyasa hareketi keşif sistemi | Plus |
| Veri | Gerçek zamanlı canlı hisse verisi | Plus |
| Sinyal | Teknik analiz sinyalleri | Plus |
| Entegrasyon | SPK lisanslı aracı kurum hesap bağlantısı | Plus |
| Akış | Analiz → İşlem → Takip tek ekranda | Plus |
| Eğitim | Yatırımcı.AI Akademi | Basic (ücretsiz) |
| Mobil | iOS App Store + Google Play | Her iki plan |

### Güçlü Yönleri
- **Aracı kurum bağlantısı** → Tek ekranda gör-karar ver-işlem yap akışı (rakiplerde yok)
- **Mobil uygulama** → iOS + Android tam native app
- **Fiyatlandırma** → 399₺/ay ile niş premium segment oluşturmuş
- **Akademi** → Ücretsiz eğitim içeriği, kullanıcı kazanım aracı
- **Marka** → "AI" odaklı net konumlandırma, modern görünüm

### Zayıf Yönleri
- AI tahmin algoritması tamamen kara kutu — şeffaflık sıfır
- Teknik sinyal nasıl üretiliyor bilinmiyor (Supertrend mi? RSI mi? gizemli)
- KAP bildirimleri yok (şirket haberleri için ayrı kaynak gerekiyor)
- Gerçek zamanlı veri sadece ücretli planda
- Backtest performans verisi yok (algoritma kanıtlanabilir değil)

---

## §R2. BORSADIREKT.COM — Detaylı Analiz

**Genel:** Osmanlı Yatırım Menkul Değerler A.Ş.'nin kurumsal dijital platformu.  
**Hedef kitle:** Osmanlı Yatırım müşterileri + genel yatırımcılar.  
**Model:** Tamamen ücretsiz (hesap açmak yeterli). Veri: Matriks (gerçek zamanlı).  
**Veri kaynağı:** Matriks — BIST lisanslı gerçek zamanlı veri.

### Özellik Listesi

| Kategori | Özellik | Durum |
|----------|---------|-------|
| Piyasa | BIST100/30, BYF, endeksler, yükselenler/düşenler/hacimliler | ✅ Gerçek zamanlı |
| Teknik | Teknik analiz + grafik (günlük/haftalık/aylık/5 yıla kadar) | ✅ |
| Teknik | **Formasyon analizi** (otomatik pattern tespit) | ✅ AI destekli |
| Analitik | **Hisse korelasyon analizi** | ✅ |
| Analitik | **Hisse karşılaştırma grafikleri** | ✅ |
| Analitik | **F/K değişimi tarihi** | ✅ |
| Analitik | **PD/DD değişimi tarihi** | ✅ |
| Analitik | **USD bazında getiri karşılaştırması** | ✅ |
| Analitik | **Mali tablo sonrası getiri analizi** | ✅ |
| Simülatör | **"100.000 TL Ne Oldu?"** yatırım performans simülatörü | ✅ |
| Temettü | **Temettü takvimi** | ✅ |
| Temettü | **Temettü beklentisi** | ✅ |
| Temettü | **Temettü filtreleme** | ✅ |
| Hesaplama | **Sermaye ve temettü hesap makinesi** | ✅ |
| Türev | Vadeli piyasa (VIOP) — analiz, hesap makinesi | ✅ |
| Türev | Opsiyon piyasası — analiz, opsiyon ağacı | ✅ |
| Türev | Varant piyasası — varant seçer, analiz | ✅ |
| Döviz | 5 ana parite + döviz çevirici | ✅ |
| Altın | Gram/çeyrek/yarım/tam/Cumhuriyet altını + ONS | ✅ |
| Emtia | Brent + ham petrol | ✅ |
| Tahvil | Türkiye 2Y + 10Y + TLREF | ✅ |
| Haber | Haberler bölümü | ✅ |
| Takvim | **Ekonomik takvim** | ✅ |
| İçerik | Blog (BorsaBlog) | ✅ |
| Bülten | **Günlük bülten talep formu** | ✅ |
| Alarm | Fiyat ve haber alarmları | ✅ (üyelik gerekli) |
| Watchlist | Kişisel takip listesi | ✅ (üyelik gerekli) |
| Mobil | iOS + Android + Huawei AppGallery | ✅ |

### Güçlü Yönleri
- **Gerçek zamanlı veri** (Matriks lisanslı) — BorsaPusula'nın en büyük dezavantajı burası
- **Türev araçlar** — Vadeli, opsiyon, varant; rakipte bu kadar kapsamlı yok
- **Temettü ekosistemi** — Takvim + beklenti + filtreleme + hesaplayıcı
- **Finansal araç çeşitliliği** — Korelasyon, F/K değişimi, USD bazlı karşılaştırma
- **"100.000 TL Ne Oldu?"** — Kullanıcı dostu, viral potansiyeli olan araç
- **Ekonomik takvim** — Hazır, detaylı
- **Ücretsiz** — Tüm özellikler para ödemeden kullanılabiliyor

### Zayıf Yönleri
- Teknik sinyal yok (sadece grafik + indikatör gösterme)
- KAP bildirimi entegrasyonu yok
- AI haber özeti yok
- ABD hisseleri için kapsamlı analiz yok
- Tasarım kurumsal/kalabalık, modern değil
- Algoritmanın performansı/backtest'i yok

---

## §R3. TÜM RAKİP KARŞILAŞTIRMA TABLOSU (Güncel)

| Özellik | BorsaPusula | yatirimci.ai | borsadirekt.com | Bigpara | ForInvest | BistScan |
|---------|------------|-------------|----------------|---------|-----------|---------|
| **Teknik sinyal (AL/SAT)** | ✅ Supertrend+ADX+EMA | ✅ AI (kara kutu) | ❌ | ❌ | ❌ | ✅ |
| **Algoritma şeffaflığı** | ✅ Tam açık | ❌ Kara kutu | — | — | — | ⚠️ Kısmi |
| **Backtest / kanıt** | ✅ 2 yıl, Sharpe 1.34 | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Veri gecikme** | ⚠️ 15 dk | ✅ Gerçek zamanlı (Plus) | ✅ Gerçek zamanlı | ✅ | ✅ | ⚠️ |
| **KAP bildirimleri** | ✅ Her hisse | ❌ | ❌ | ⚠️ Seçili | ✅ | ❌ |
| **AI haber özeti** | ✅ kap_ai | ⚠️ Genel AI | ❌ | ❌ | ❌ | ❌ |
| **ABD hisseleri** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Kripto analiz** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Emtia/altın** | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| **Temettü bölümü** | ❌ | ❌ | ✅ Kapsamlı | ✅ | ⚠️ | ❌ |
| **Formasyon analizi** | ❌ | ❌ | ✅ | ⚠️ | ❌ | ❌ |
| **Korelasyon analizi** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Hisse karşılaştırma** | ✅ /karsilastir | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Ekonomik takvim** | ⚠️ Planlandı | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Vadeli/Opsiyon** | ❌ | ❌ | ✅ | ⚠️ | ⚠️ | ❌ |
| **Makro haberler** | ⚠️ Planlandı | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Üyelik/Alarm** | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Mobil uygulama** | ❌ | ✅ iOS+Android | ✅ iOS+Android+Huawei | ✅ | ❌ | ❌ |
| **Premium plan** | ❌ | ✅ 399₺/ay | ❌ Ücretsiz | ❌ | ✅ | ❌ |
| **Aracı kurum bağlantısı** | ❌ | ✅ | ✅ (Osmanlı) | ❌ | ❌ | ❌ |
| **MTF analiz** | ✅ (H4/D/W/M) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Senaryo simülatörü** | ❌ | ❌ | ✅ 100K TL | ❌ | ❌ | ❌ |
| **Ücretsiz mi?** | ✅ Tamamen | ⚠️ Kısmi | ✅ Tamamen | ✅ | ⚠️ | ✅ |

---

## §R4. BORSAPusula'YA KATABİLECEKLERİMİZ — ÖNCELİKLİ LİSTE

### 🔴 YÜKSEK ETKİ + KOLAY UYGULAMA (Bu ay)

#### R4-1: Yatırım Performans Simülatörü — "X TL'yi {Hissede} Tutsaydın?"
**Esin kaynağı:** borsadirekt.com "100.000 TL Ne Oldu?"  
**BorsaPusula versiyonu:** Sinyal bazlı simülatör — "Algoritmamızın sinyallerini takip etseydin X TL'n bugün ne olurdu?"  
**Neden güçlü:** Backtest sayfamız var (Sharpe 1.34), bu data zaten elimizde.  
**Uygulama:**
```python
# /api/backtest-sim?amount=10000&from=2024-01-01 
# Mevcut sinyal geçmişinden hesaplanır
# Input: başlangıç sermayesi, başlangıç tarihi
# Output: portföy değeri, pozisyon listesi, max drawdown, Sharpe
```
**Sayfa:** `/sinyal-performans`'a embed edilebilir veya ayrı `/simule` sayfası  
**Zaman:** 4-6 saat

---

#### R4-2: Temettü Takvimi & Beklenti
**Esin kaynağı:** borsadirekt.com  
**Veri kaynağı:** KAP temettü bildirimleri (zaten çekiyoruz) + KAP takvim API  
**Neden güçlü:** BIST yatırımcılarının büyük çoğunluğu temettüye bakıyor; şu an bu sayfa hiç yok.  
**Yeni endpoint:** `/temettü` sayfası  
**Veri:**
```python
# KAP temettü bildirimleri: /api/disc/memberRelated/company/{oid}?disclosureClass=TD
# TD = Temettü bildirimi class'ı
# Her AL sinyalli hisse için temettü verimi ve ödeme tarihi göster
```
**Tablo görünümü:** Hisse | Brüt Temettü | Verim % | Ödeme Tarihi | Sinyal  
**Zaman:** 6-8 saat

---

#### R4-3: Hisse Korelasyon Matrisi
**Esin kaynağı:** borsadirekt.com  
**Neden güçlü:** Portföy çeşitlendirme kararı için kritik. "AKBNK alırsam GARAN ile ne kadar korelasyon?" sorusuna cevap veriyor.  
**Uygulama:**
```python
# /api/korelasyon?tickers=AKBNK,GARAN,EREGL&period=90
# yfinance'tan günlük kapanış çek, pearson korelasyon hesapla
import pandas as pd
import numpy as np

def calc_correlation(tickers: list, days: int = 90) -> dict:
    closes = {}
    for t in tickers:
        data = yf.download(f"{t}.IS", period=f"{days}d", interval="1d")
        closes[t] = data["Close"]
    df = pd.DataFrame(closes).dropna()
    corr = df.corr().round(3)
    return corr.to_dict()
```
**Görsel:** Heatmap tablo (renk kodlu: yeşil = düşük korelasyon, kırmızı = yüksek)  
**Sayfa:** `/karsilastir` sayfasına ek sekme olarak ekle  
**Zaman:** 4 saat

---

#### R4-4: Akademi / Eğitim Bölümü
**Esin kaynağı:** yatirimci.ai Akademi  
**BorsaPusula versiyonu:** Blog'u genişlet → "Nasıl Kullanılır?" video/yazı serisi  
**İçerik fikirleri:**
- "BorsaPusula sinyali nasıl okunur?" (3 dakika video)
- "Supertrend nedir, nasıl çalışır?" (zaten blog'da var)
- "Stop-loss neden önemli?" 
- "ADX ile trend gücü nasıl ölçülür?"
- "AL sinyalinde nasıl işlem yapılır?" (aracı kurum görselleri ile)
**Neden değerli:** SEO + kullanıcı bağlılığı + yatirimci.ai'ye karşı ücretsiz rekabet  
**Zaman:** İçerik üretimi gerekiyor, sayfa altyapısı blog'dan geliyor

---

#### R4-5: USD Bazında Getiri Karşılaştırması
**Esin kaynağı:** borsadirekt.com  
**Neden güçlü:** TL enflasyonu bağlamında reel getiri görmek kritik. "AKBNK 1 yılda %45 arttı ama dolar bazında ne oldu?"  
**Uygulama:** `/hisse/AKBNK` sayfasına ek sekme — "Dolar Bazlı Getiri"  
**Hesap:** `getiri_usd = (fiyat_son / kur_son) / (fiyat_baş / kur_baş) - 1`  
**Zaman:** 2-3 saat

---

### 🟡 ORTA ETKİ + ORTA SÜRE (Gelecek ay)

#### R4-6: Alarm Sistemi (Fiyat + Sinyal)
**Esin kaynağı:** yatirimci.ai + borsadirekt.com  
**BorsaPusula versiyonu:** Sinyal değişikliği alarmı — "AKBNK AL'a geçerse bildir"  
**Kanal:** E-posta (zaten abonelik altyapımız var) + browser push notification  
**Backend:** Mevcut sinyal hesaplama döngüsüne delta tespiti ekle  
```python
def check_signal_changes():
    old_signals = load_prev_signals()
    new_signals = get_current_signals()
    changes = [(t, old, new) for t, old in old_signals.items() 
               if (new := new_signals.get(t)) and new != old]
    for ticker, old_sig, new_sig in changes:
        notify_subscribers(ticker, old_sig, new_sig)
```
**Zaman:** 8-12 saat (e-posta altyapısı zaten var)

---

#### R4-7: Yatırım Fonu Analizi
**Esin kaynağı:** yatirimci.ai  
**Veri kaynağı:** TEFAS API (kamuya açık) — `https://www.tefas.gov.tr`  
**BorsaPusula versiyonu:** BIST hisselerimizle aynı sinyal metodolojisini fonlara uygula  
**Yeni sayfa:** `/fonlar` — Supertrend + ADX sinyali olan fonları listele  
**Zaman:** 8-12 saat

---

#### R4-8: Premium Plan — BorsaPusula Plus
**Esin kaynağı:** yatirimci.ai (399₺/ay)  
**Öneri:** Şu an tamamen ücretsiz olan platform için premium katman oluştur  
**Ücretsiz kalacaklar:** Tüm sinyal verileri, hisse sayfaları, grafikler (SEO için)  
**Premium (99-149₺/ay) olacaklar:**
- Anlık sinyal değişikliği bildirimi (push/e-posta)
- Portföy takibi + SL takibi (fiyat SL'e yaklaşırsa uyar)
- Özel filtreli tarama (kendi ADX/RSI eşiklerini belirle)
- Haftalık AI portföy özeti e-posta
- API erişimi (bots için)
**Not:** Monetization için kritik ama kullanıcı tabanı oluşturulunca yapılmalı

---

#### R4-9: Opsiyon / Varant Farkındalık Sayfası
**Esin kaynağı:** borsadirekt.com (kapsamlı türev bölümü)  
**BorsaPusula versiyonu:** Tam türev analizi değil, sadece "Bu hissenin varantları" bilgisi  
**Uygulama:** `/hisse/ASELS` sayfasında alt bölüm — "ASELS'e bağlı varantlar"  
**Veri:** BIST Warrant veritabanı (kamuya açık XML feed)  
**Zaman:** 6-8 saat

---

### 🟢 UZUN VADE (3+ ay)

#### R4-10: Mobil Uygulama (PWA olarak başla)
**Esin kaynağı:** yatirimci.ai + borsadirekt.com (her ikisi de native app)  
**BorsaPusula yolu:** Native uygulama öncesinde PWA (Progressive Web App)  
**PWA özellikleri:** Offline çalışma, ana ekrana ekle, push notification  
**Uygulama:** `manifest.json` + `service-worker.js` + meta tag'lar  
**Zaman:** 8 saat (PWA) → 2-3 ay (native)

---

#### R4-11: Aracı Kurum Entegrasyonu (Uzun vade)
**Esin kaynağı:** yatirimci.ai (en büyük differentiator'ları)  
**BorsaPusula versiyonu:** Sinyal geldiğinde direkt işlem yapabilme  
**Teknik:** SPK lisanslı aracı kurumların FIX/REST API'leri (Gedik, Denizbank, İş Yatırım vb.)  
**Önce:** Broker API araştır, demo hesap aç, test et  
**Zaman:** 3-6 ay

---

## §R5. STRATEJİK KONUMLANDIRMA — BORSAPusula'nın Fırsatı

### Rakiplerin Kör Noktası
| Rakip | En Büyük Eksik |
|-------|---------------|
| yatirimci.ai | KAP bildirimleri yok, sinyal şeffaflığı sıfır, backtest yok |
| borsadirekt.com | Sinyal/algoritma yok, AI haber özeti yok, kurumsal/ağır tasarım |
| Bigpara | Teknik sinyal yok, KAP bağlantısı sınırlı |
| ForInvest | Sinyal yok, kullanıcı araçları sınırlı |
| BistScan | Haber/KAP yok, tek boyutlu |

### BorsaPusula'nın Eşsiz Konumu
```
Piyasadaki tek platform:
✅ Şeffaf algoritma (Supertrend+ADX+EMA açık kaynak mantığı)
✅ 2 yıllık backtest kanıtı (Sharpe 1.34)
✅ KAP bildirimi + AI özeti + teknik sinyal (üçü aynı anda)
✅ BIST + ABD + Kripto + Emtia tek platform
✅ Tamamen ücretsiz
✅ Hızlı (<20ms)
```

### Önerilen 3 Aylık Yol Haritası

```
MAYIS 2026 (Bu ay):
├── BUG: ADX null fix (30dk)
├── Ekonomik takvim API (1 saat)
├── RSS makro haberler (2 saat)
├── USD bazlı getiri (2 saat)
└── /gundem sayfası güncellemesi (3 saat)

HAZİRAN 2026:
├── Temettü takvimi sayfası
├── Yatırım simülatörü ("X TL alsaydın")
├── Sinyal alarm sistemi (e-posta)
└── Korelasyon analizi

TEMMUZ 2026:
├── PWA (Progressive Web App)
├── Yatırım fonu analizi (TEFAS)
├── Premium plan altyapısı
└── Akademi/eğitim içeriği
```

---

---

## §R6. BULLSYATIRIM.COM — Detaylı Analiz

**Genel:** Bulls Yatırım Menkul Değerler A.Ş. — SPK lisanslı gerçek bir **aracı kurum**.  
**Hedef kitle:** Bireysel ve kurumsal yatırımcılar, Bulls Yatırım müşterileri.  
**Model:** Araştırma içeriği ücretsiz; gelir brokerage komisyonundan geliyor.  
**Önemli fark:** Bu bir yazılım şirketi değil, **düzenlenmiş bir finans kurumu** → güvenilirlik otomatik.

### Özellik Listesi

| Kategori | Özellik | Durum |
|----------|---------|-------|
| Hisse | **611 hisse** listesi (A-Z, tüm BIST) | ✅ Gerçek zamanlı |
| Temel | F/K, PD/DD, net kar, halka açıklık, sermaye | ✅ Her hisse için |
| Temel | **Ortaklık yapısı** (kim ne kadar pay sahibi) | ✅ |
| Temel | **Sermaye artırımları + temettü geçmişi** | ✅ |
| Fiyat | Tarihsel fiyat tablosu (açılış/yüksek/düşük/kapanış/lot) | ✅ |
| Grafik | Düzeltilmiş fiyat grafiği (6A/1Y/3Y) | ✅ Basit |
| Filtreleme | Gelişmiş hisse tarama (sembol, F/K, PD/DD, değişim %) | ✅ |
| Araştırma | **Teknik bülten** (günlük BIST100 analizi, insan analist) | ✅ |
| Araştırma | **Şirket raporları** (bireysel hisse incelemeleri) | ✅ |
| Araştırma | **VİOP bülteni** (vadeli piyasa) | ✅ |
| Araştırma | **Makroekonomik analizler** | ✅ |
| Araştırma | **Pair trade içeriği** (ikili işlem stratejileri) | ✅ Nadir özellik |
| Araştırma | Kısa vadeli öneriler | ✅ |
| Bülten | Bülten aboneliği (e-posta) | ✅ |
| AI | Bulls Yatırım Asistan (chatbot) | ⚠️ Temel |
| Hizmet | Yatırım danışmanlığı (kişiye özel portföy) | ✅ Premium |
| Hizmet | Bireysel portföy yönetimi | ✅ Premium |
| Hizmet | Kurumsal finansman / halka arz aracılığı | ✅ |
| Hesap | Görüntülü görüşme ile kağıtsız hesap açma | ✅ |
| Platform | İdeal Data entegrasyonu | ✅ |
| Platform | E-Şube (sanal şube) | ✅ |
| Mobil | Anlık işlem bildirimleri (mobil) | ✅ |

### Güçlü Yönleri
- **SPK lisanslı aracı kurum** → düzenleyici otorite güvencesi, kurumsal itibar
- **611 hisse** → BorsaPusula'nın 145 hissesinin 4 katı kapsam
- **Temel analiz verileri** — F/K, PD/DD, ortaklık yapısı, sermaye artırımları (BorsaPusula'da yok)
- **Pair trade** — Türk platformlarda nadir görülen ikili strateji içeriği
- **İnsan analist** — Günlük teknik bülten + şirket raporları (AI değil, gerçek uzman)
- **Mevzuat uyumu** — Yasal çerçeve ve şeffaflık built-in

### Zayıf Yönleri
- Hisse sayfasında **sinyal yok** (AL/SAT/BEKLE), teknik indikatör yok
- **AI analiz yok** — chatbot var ama hisse bazlı analiz yok
- **KAP bildirimi entegrasyonu yok**
- Grafik çok basit — LightweightCharts gibi interaktif grafik yok
- Backtest / algoritma performans kanıtı yok
- **Kripto ve ABD hisseleri yok**
- UX/UI kurumsal ve ağır, modern değil

---

## §R7. GÜNCELLENMİŞ TAM RAKİP TABLOSU (3 Mayıs 2026)

| Özellik | BorsaPusula | yatirimci.ai | borsadirekt | bullsyatirim | Bigpara | ForInvest |
|---------|------------|-------------|-------------|-------------|---------|-----------|
| **AL/SAT sinyali** | ✅ Şeffaf algo | ✅ Kara kutu | ❌ | ❌ | ❌ | ❌ |
| **Backtest kanıtı** | ✅ Sharpe 1.34 | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Gerçek zamanlı veri** | ⚠️ 15dk gecikme | ✅ (Plus) | ✅ Matriks | ✅ | ✅ | ✅ |
| **Hisse sayısı** | 145 | ~100 | BIST tümü | **611** | BIST tümü | BIST tümü |
| **KAP bildirimleri** | ✅ | ❌ | ❌ | ❌ | ⚠️ | ✅ |
| **AI haber özeti** | ✅ Gemini | ⚠️ Genel | ❌ | ❌ chatbot | ❌ | ❌ |
| **Temel analiz (F/K, PD/DD)** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Ortaklık yapısı** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Temettü ekosistemi** | ❌ | ❌ | ✅ Kapsamlı | ⚠️ Geçmiş | ✅ | ⚠️ |
| **Formasyon analizi** | ❌ | ❌ | ✅ | ❌ | ⚠️ | ❌ |
| **Korelasyon analizi** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Pair trade** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **VİOP/Türev** | ❌ | ❌ | ✅ Kapsamlı | ✅ bülten | ⚠️ | ⚠️ |
| **ABD hisseleri** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Kripto analiz** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **MTF analiz (H4/D/W/M)** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Ekonomik takvim** | ⚠️ Planlandı | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Araştırma bülteni** | ❌ | ❌ | ⚠️ | ✅ İnsan analist | ✅ | ✅ |
| **Hisse karşılaştırma** | ✅ Planlandı | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Mobil uygulama** | ❌ | ✅ iOS+Android | ✅ +Huawei | ✅ | ✅ | ❌ |
| **Premium plan** | ❌ | ✅ 399₺/ay | ❌ Ücretsiz | ❌ | ❌ | ✅ |
| **Ücretsiz mi?** | ✅ | ⚠️ Kısmi | ✅ | ✅ | ✅ | ⚠️ |
| **SPK lisansı** | ❌ | ❌ | ⚠️ (Osmanlı) | ✅ Aracı kurum | ✅ | ✅ |

---

## §R8. BULLSYATIRIM'DAN KATABİLECEKLERİMİZ

### 🔴 Yüksek Öncelik

#### RB-1: Temel Analiz Verileri — Her Hisse Sayfasına Ekle
**Ne:** F/K oranı, PD/DD oranı, piyasa değeri, net kar, halka açıklık %, sermaye  
**Veri kaynağı:** Bu veriler KAP finansal tablolarından zaten geliyor; yfinance `info` dict'inde de var  
```python
# yfinance'tan temel veri çekimi
import yfinance as yf
ticker = yf.Ticker("AKBNK.IS")
info = ticker.info
fundamentals = {
    "pe_ratio": info.get("trailingPE"),
    "pb_ratio": info.get("priceToBook"),
    "market_cap": info.get("marketCap"),
    "net_income": info.get("netIncomeToCommon"),
    "float_shares_pct": info.get("floatShares", 0) / info.get("sharesOutstanding", 1) * 100
}
```
**Gösterim:** `/hisse/AKBNK` sayfasında sinyal kartının altına küçük metrik satırı  
**Zaman:** 3-4 saat

#### RB-2: Ortaklık Yapısı (Major Shareholders)
**Ne:** Kim, ne kadar pay sahibi — önemli ortakların listesi  
**Veri kaynağı:** `yf.Ticker("AKBNK.IS").major_holders` + `institutional_holders`  
**Neden değerli:** Büyük ortak çıkışı/girişi kritik sinyal; rakipler bunu gösteriyor  
**Zaman:** 2-3 saat

#### RB-3: Hisse Sayısını 611'e Yaklaştır
**Mevcut durum:** 145 hisse (BIST30 + genişletilmiş seçki + ABD)  
**Hedef:** Tüm BIST hisselerini ekle (~400+ hisse)  
**Teknik:** yfinance tüm BIST hisselerini çekebiliyor; sadece tarama genişletilmeli  
**Risk:** Sunucu yükü artar; rate limiting ve cache stratejisi önemli  
**Çözüm:** Ana sayfa sadece sinyal verilen hisseleri göster; `/tarama` da tümü listelensin  
**Zaman:** 4-6 saat

#### RB-4: Pair Trade Bölümü (Türk platformlarda yok!)
**Ne:** İki hisse arasındaki spread analizi + korelasyon bazlı trade önerisi  
**Neden güçlü:** bullsyatirim'de var ama basit; biz sinyal+AI açıklamasıyla üstün yapabiliriz  
**Örnek:** "AKBNK güçlü, YKBNK zayıf → pair trade fırsatı?"  
**Uygulama:** 
```python
# /api/pair-trade?long=AKBNK&short=YKBNK
# Korelasyon: 0.87, Spread z-score: 2.3 (aşırı uzaklaşma)
# Sinyal: AKBNK=AL, YKBNK=BEKLE → long AKBNK / short YKBNK
```
**Sayfa:** `/karsilastir` sayfasına "Pair Trade Analizi" sekmesi  
**Zaman:** 6-8 saat

### 🟡 Orta Öncelik

#### RB-5: Sermaye Artırımı ve Temettü Geçmişi
**Ne:** Hangi hisse ne zaman bedelsiz/bedelî artırım yaptı, temettü verdi  
**Veri:** KAP bildirimleri + yfinance corporate actions  
**Gösterim:** `/hisse/AKBNK` sayfasında "Kurumsal Eylemler" sekmesi  
**Zaman:** 4-5 saat

---

## §R9. GENEL STRATEJİK SONUÇ — TÜM RAKİPLER

### BorsaPusula'nın KORUNMASI GEREKEN Üstünlükleri
1. **Şeffaf algoritma + backtest kanıtı** — Rakiplerin hiçbirinde yok, en büyük differentiator
2. **KAP + AI özeti + teknik sinyal** üçlüsü — Kimde yok
3. **MTF analiz** (H4/D/W/M) — Kimde yok
4. **Ücretsiz + hızlı** — yatirimci.ai ücret alıyor, kurumsal siteler yavaş

### BorsaPusula'nın KAPATMASI GEREKEN Açıklar
| Açık | En iyi rakip | Öncelik |
|------|------------|---------|
| Temel veri (F/K, PD/DD, ortaklık) | bullsyatirim | 🔴 Yüksek |
| Temettü takvimi | borsadirekt | 🔴 Yüksek |
| Hisse sayısı (145 → 400+) | bullsyatirim (611) | 🔴 Yüksek |
| Korelasyon / pair trade | borsadirekt + bullsyatirim | 🟡 Orta |
| Ekonomik takvim + makro haberler | borsadirekt | 🟡 Orta |
| Yatırım simülatörü | borsadirekt | 🟡 Orta |
| Alarm sistemi | yatirimci.ai + borsadirekt | 🟡 Orta |
| Mobil uygulama | tüm rakipler | 🟢 Uzun vade |

### Kazanma Formülü
```
BorsaPusula'nın şu anki unique pozisyonu:
"Şeffaf AL/SAT + 2yr backtest + KAP + AI"

Rakiplerin kör noktası = bu kombinasyon hiçbirinde yok

Kısa vadede kapatılacak açıklar (1 ay):
Temel veri + temettü + hisse sayısı

Orta vadede (3 ay):
Alarm + simülatör + korelasyon/pair trade

Uzun vadede (6+ ay):
PWA/mobil + fon analizi + premium plan
```

---

*3 Mayıs 2026 — yatirimci.ai + borsadirekt.com + bullsyatirim.com rakip analizi eklendi.*
