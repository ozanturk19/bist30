# BorsaPusula — Geliştirme Planı

> **Son güncelleme:** 26 Nisan 2026  
> **Durum:** Kaynak kod okunarak doğrulandı — "eksik" olduğu düşünülen ama aslında var olan her şey listeden çıkarıldı.

---

## ✅ Zaten Var Olanlar (Yanlış Raporlananlar)

Aşağıdakiler test raporlarında "eksik" görünüyordu — kaynak kodda **mevcut** olduğu teyit edildi:

| Özellik | Durum | Konum |
|---|---|---|
| Makro ticker bandı (BIST100, BTC, Altın…) | ✅ Var | `templates/index.html` satır 872+ |
| `/api/macro` endpoint | ✅ Var | `app.py` satır 1151 |
| Flask-Limiter rate limiting | ✅ Var | `app.py` satır 26 |
| `/api/refresh` admin koruması | ✅ Var | `app.py` satır 1113 |
| Temel veri sanitizasyonu (`_clean_fundamentals`) | ✅ Var | `app.py` satır 1919 |
| Haber AI prompt'una tarih ekleme | ✅ Var | `app.py` satır 1438 |
| `ssr_signal` SSR (hisse.html pre-JS) | ✅ Var | `templates/hisse.html` satır 864 |
| Blog Article + BreadcrumbList schema | ✅ Var | `templates/blog_article.html` satır 19 |
| Blog kısa slug → tam slug 301 yönlendirme | ✅ Var | `app.py` satır 2806 |
| `/hakkinda`, `/iletisim`, `/gucu-yuksek` sayfaları | ✅ Var | `app.py` satır 2312–2370 |
| MTF (haftalık/aylık) analiz endpoint + UI | ✅ Var | `app.py` satır 2136, `hisse.html` satır 771 |
| localStorage portföy takibi | ✅ Var | `templates/portfolio.html` |
| Backtest endpoint + sinyal performans sayfası | ✅ Var | `app.py` satır 2560, `sinyal_performans.html` |
| E-posta abonelik sistemi (Brevo SMTP) | ✅ Var | `app.py` satır 808+ |

---

## 🔴 TIER 1 — Hızlı Kazanımlar (Her biri < 2 saat)

### 1. GA4 Analytics Entegrasyonu

**Problem:** Hiçbir template'te `gtag` veya `dataLayer` yok. Kullanıcı davranışı, sayfa geçişleri, hangi hisselerin bakıldığı hakkında sıfır veri var.  
**Etki:** Yüksek — hangi içeriklerin trafik çektiğini bilmeden büyüme stratejisi kör.

**Yapılacak:** `templates/index.html` `<head>` bölümüne ekle — diğer tüm template'lerde de aynı snippet.

```html
<!-- GA4 — her template'in <head> içine, charset meta'sından sonra -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX', {
    page_title: document.title,
    anonymize_ip: true
  });
</script>
```

**Etkilenen dosyalar:** `templates/index.html`, `templates/hisse.html`, `templates/ozet.html`, `templates/blog.html`, `templates/blog_article.html`, `templates/gucu_yuksek.html`, `templates/sinyal_performans.html`, `templates/sektor_harita.html`, `templates/bilanco_takvimi.html`, `templates/portfolio.html`, `templates/hakkinda.html`

**Ek GA4 olayları — hisse.html'e ekle:**
```javascript
// Sinyal açıklaması yüklendikten sonra (mevcut fetchExplanation() içine)
gtag('event', 'signal_view', {
  ticker: TICKER,
  signal: '{{ ssr_signal.signal if ssr_signal else "unknown" }}'
});

// KAP linki tıklandığında
document.querySelectorAll('a[href*="kap.org.tr"]').forEach(a => {
  a.addEventListener('click', () => gtag('event', 'kap_click', { ticker: TICKER }));
});
```

**Kabul Kriteri:** Google Analytics Realtime raporunda sayfa görüntüleme olayları görünüyor.

---

### 2. Makro Ticker Bandını Alt Sayfalara Taşı

**Problem:** Makro ticker (BIST100, BTC, Altın, EUR/TRY…) yalnızca ana sayfada var. Hisse detay, özet, blog sayfalarında yok.  
**Etki:** Orta — kullanıcı hisse sayfasındayken piyasa bağlamını kaybediyor.

**Yapılacak:** `templates/hisse.html` dosyasında `<header>` bloğundan hemen sonra macro bar HTML + CSS + JS ekle.

**CSS** (hisse.html `<style>` bloğuna ekle):
```css
.macro-bar {
  background: #0d1520; border-bottom: 1px solid #1e2d45;
  height: 34px; overflow: hidden; position: relative;
  white-space: nowrap;
}
.macro-bar::before, .macro-bar::after {
  content: ''; position: absolute; top: 0; bottom: 0; width: 60px;
  pointer-events: none; z-index: 2;
}
.macro-bar::before { left: 0; background: linear-gradient(to right, #0d1520, transparent); }
.macro-bar::after  { right: 0; background: linear-gradient(to left, #0d1520, transparent); }
.macro-track {
  display: inline-flex; align-items: center; gap: 0;
  animation: macroScroll 40s linear infinite; height: 34px;
}
.macro-bar:hover .macro-track { animation-play-state: paused; }
@keyframes macroScroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }
.macro-item {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 0 20px; border-right: 1px solid #1e2d45;
  font-size: 12px; height: 34px; cursor: default;
}
.macro-label { font-weight: 600; color: #cbd5e1; }
.macro-pos { color: #3fb950; }
.macro-neg { color: #f85149; }
.macro-neu { color: #8b949e; }
```

**HTML** (hisse.html `<header>` bloğundan hemen sonra):
```html
<div class="macro-bar" id="macroBar">
  <div class="macro-track" id="macroTrack">
    <span class="macro-item"><span class="macro-label">Yükleniyor…</span></span>
  </div>
</div>
```

**JS** (hisse.html script bölümüne ekle):
```javascript
async function loadMacro() {
  try {
    const r = await fetch('/api/macro');
    const d = await r.json();
    const items = d.items || [];
    if (!items.length) return;
    const html = items.map(it => {
      const chgCls = it.change > 0 ? 'macro-pos' : it.change < 0 ? 'macro-neg' : 'macro-neu';
      const sign   = it.change > 0 ? '+' : '';
      return `<span class="macro-item">
        <span class="macro-label">${it.label}</span>
        <span>${it.price_fmt}</span>
        <span class="${chgCls}">${sign}${it.change_pct_fmt}</span>
      </span>`;
    }).join('');
    // Sonsuz scroll için içeriği iki kez tekrarla
    document.getElementById('macroTrack').innerHTML = html + html;
  } catch(e) { /* sessizce yoksay */ }
}
loadMacro();
setInterval(loadMacro, 60000);
```

**Etkilenen dosyalar:** `templates/hisse.html`, `templates/ozet.html`, `templates/gucu_yuksek.html`  
**Kabul Kriteri:** Hisse sayfası açıldığında header altında BIST100, BTC, Altın fiyatları kayan şeritte görünüyor.

---

### 3. İletişim Formu Backend Endpoint'i

**Problem:** `/iletisim` sayfasındaki form şu anda `window.location.href = 'mailto:...'` ile çalışıyor — kullanıcının e-posta istemcisi açılıyor, web'den mesaj gönderilemiyor. Mobilde çalışmıyor.  
**Etki:** Orta — gelen mesaj sıfır.

**Yapılacak:** `app.py`'e yeni route ekle.

**app.py'e eklenecek (satır 2370 civarı, `/iletisim` route'undan sonra):**
```python
@app.route("/api/contact", methods=["POST"])
@limiter.limit("3 per hour")
def api_contact():
    data = request.get_json(silent=True) or {}
    name    = str(data.get("name", "")).strip()[:100]
    email   = str(data.get("email", "")).strip()[:200]
    subject = str(data.get("subject", "")).strip()[:200]
    message = str(data.get("message", "")).strip()[:2000]

    if not all([name, email, message]):
        return jsonify({"ok": False, "error": "Eksik alan"}), 400
    if "@" not in email or "." not in email:
        return jsonify({"ok": False, "error": "Geçersiz e-posta"}), 400

    SMTP_HOST  = os.environ.get("SMTP_HOST", "")
    SMTP_USER  = os.environ.get("SMTP_USER", "")
    SMTP_PASS  = os.environ.get("SMTP_PASS", "")
    ADMIN_MAIL = os.environ.get("ADMIN_MAIL", "iletisim@borsapusula.com")

    if SMTP_HOST and SMTP_USER:
        try:
            msg = MIMEMultipart()
            msg["From"]    = SMTP_USER
            msg["To"]      = ADMIN_MAIL
            msg["Subject"] = f"[BorsaPusula İletişim] {subject}"
            body = f"Gönderen: {name} <{email}>\n\n{message}"
            msg.attach(MIMEText(body, "plain", "utf-8"))
            with smtplib.SMTP_SSL(SMTP_HOST, 465) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_USER, ADMIN_MAIL, msg.as_string())
        except Exception as ex:
            logger.error("Contact mail hatası: %s", ex)
            return jsonify({"ok": False, "error": "Mail gönderilemedi"}), 500

    return jsonify({"ok": True})
```

**templates/iletisim.html `submitForm` fonksiyonunu güncelle:**
```javascript
async function submitForm(e) {
  e.preventDefault();
  const btn = document.getElementById('cfBtn');
  btn.disabled = true; btn.textContent = 'Gönderiliyor…';
  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name:    document.getElementById('cfName').value,
        email:   document.getElementById('cfEmail').value,
        subject: document.getElementById('cfSubject').value,
        message: document.getElementById('cfMsg').value
      })
    });
    const d = await res.json();
    if (d.ok) {
      document.getElementById('contactForm').innerHTML =
        '<div style="color:#3fb950;padding:20px;text-align:center;font-size:15px">✅ Mesajınız iletildi. Teşekkürler!</div>';
    } else {
      btn.disabled = false; btn.textContent = 'Gönder';
      alert('Hata: ' + (d.error || 'Bilinmeyen hata'));
    }
  } catch(err) {
    btn.disabled = false; btn.textContent = 'Gönder';
    alert('Bağlantı hatası. Lütfen tekrar deneyin.');
  }
}
```

**Gerekli env var'lar:** `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `ADMIN_MAIL` (Brevo SMTP zaten ayarlıysa aynı değerleri kullan)  
**Kabul Kriteri:** Form doldurulup gönderildiğinde `iletisim@borsapusula.com` adresine e-posta geliyor.

---

### 4. Blog Makalelerine FAQPage Schema Ekleme

**Problem:** `blog_article.html` Article + BreadcrumbList schema var ama FAQPage yok. Google, FAQ şeması olan makalelere arama sonuçlarında genişletilmiş sonuç gösteriyor (snippet alanı artıyor).  
**Etki:** Orta-Yüksek — organik CTR'ı %20-40 artırabilir.

**Yapılacak:** `blog_content.py`'deki her makaleye `faqs` listesi ekle, `blog_article.html`'e şema entegre et.

**blog_content.py — makale objesine alan ekle (örnek):**
```python
{
    "slug": "supertrend-indikatoru-nedir",
    "title": "Supertrend İndikatörü Nedir?",
    # ... mevcut alanlar ...
    "faqs": [
        {
            "q": "Supertrend indikatörü ne işe yarar?",
            "a": "Supertrend, fiyatın trend yönünü ve olası dönüş noktalarını ATR tabanlı bantlarla gösterir. Yeşil bant fiyatın altında ise yükseliş trendi, kırmızı bant üstündeyse düşüş trendi sinyali verir."
        },
        {
            "q": "Supertrend hangi parametrelerle kullanılır?",
            "a": "BorsaPusula'da Supertrend(10,3) parametreleri kullanılır: 10 günlük ATR periyodu, 3 çarpan. Bu ayarlar BIST30 hisseleri için optimize edilmiştir."
        },
        {
            "q": "Supertrend tek başına yeterli mi?",
            "a": "Hayır. BorsaPusula sinyali için Supertrend'e ek olarak ADX≥25 (güçlü trend onayı) ve EMA12/EMA99 (yön filtresi) koşullarının üçü birden sağlanmalıdır."
        }
    ]
}
```

**blog_article.html — mevcut schema bloklarından sonra:**
```html
{% if article.faqs %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {% for faq in article.faqs %}
    {
      "@type": "Question",
      "name": {{ faq.q | tojson }},
      "acceptedAnswer": {
        "@type": "Answer",
        "text": {{ faq.a | tojson }}
      }
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
}
</script>
{% endif %}
```

**Kabul Kriteri:** Google Rich Results Test ile `blog/supertrend-indikatoru-nedir` adresi test edildiğinde FAQPage schema doğrulanıyor.

---

## 🟡 TIER 2 — Orta Vadeli Özellikler (Her biri 1-3 gün)

### 5. `/tarama` — Strateji Tarayıcısı

**Problem:** Rakip BistScan'in en güçlü silahı: 530 hisse × 24 strateji filtresi. Kullanıcılar "AL sinyali + ADX > 30 + hacim artışı" gibi kombinasyonlarla hisse listesi oluşturabiliyor. BorsaPusula'da bu yok.  
**Etki:** Yüksek — aktif trader segmentini çekmenin ana yolu.

**Backend — app.py'e eklenecek:**
```python
@app.route("/tarama")
def tarama():
    return render_template("tarama.html")

@app.route("/api/tarama")
@limiter.limit("30 per minute")
def api_tarama():
    """Hisse tarayıcısı: sinyal, ADX, fiyat aralığı, sektör filtresi."""
    sig     = request.args.get("signal", "")        # AL | SAT | BEKLE | ""
    min_adx = float(request.args.get("min_adx", 0))
    min_p   = float(request.args.get("min_price", 0))
    max_p   = float(request.args.get("max_price", 99999))
    sector  = request.args.get("sector", "")
    sort_by = request.args.get("sort", "ticker")    # ticker | adx | price | signal_bars

    with _lock:
        stocks = list(_cache["data"])

    results = []
    for s in stocks:
        if s.get("ticker") == "XU030": continue
        if sig    and s.get("signal") != sig: continue
        if sector and s.get("sector") != sector: continue
        price = s.get("price") or 0
        adx   = s.get("adx")  or 0
        if price < min_p or price > max_p: continue
        if adx < min_adx: continue
        results.append({
            "ticker":       s.get("ticker"),
            "name":         s.get("name"),
            "sector":       s.get("sector"),
            "signal":       s.get("signal"),
            "price":        price,
            "change_pct":   s.get("change_pct"),
            "adx":          adx,
            "signal_bars":  s.get("signal_bars"),
            "entry_quality":s.get("entry_quality"),
        })

    # Sırala
    rev = sort_by in ("adx", "price", "signal_bars")
    results.sort(key=lambda x: (x.get(sort_by) or 0), reverse=rev)

    # Mevcut sektör listesi
    with _lock:
        sectors = sorted(set(s.get("sector","") for s in _cache["data"] if s.get("sector")))

    return jsonify({"results": results, "sectors": sectors,
                    "count": len(results), "updated_at": _cache.get("updated_at","")})
```

**Yeni template:** `templates/tarama.html`  
Temel UI bileşenleri:
- Filtre çubuğu: Sinyal (AL/SAT/BEKLE/Tümü), Min ADX slider, Fiyat aralığı, Sektör dropdown
- Tablo: Ticker, Şirket, Sektör, Sinyal, Fiyat, Değişim%, ADX, Kaç gündür aktif, Giriş kalitesi
- Her satır `/hisse/<ticker>` linkine yönlendiriyor
- Kolon başlıklarına tıklayınca sıralama

**Sitemap'e eklenecek (app.py satır 2183):**
```python
{"loc": "/tarama", "priority": "0.8", "changefreq": "daily"},
```

**Kabul Kriteri:** `/tarama?signal=AL&min_adx=25` açıldığında yalnızca AL sinyalli + ADX≥25 hisseler listeleniyor.

---

### 6. `/karsilastir` — Hisse Karşılaştırma Aracı

**Problem:** Kullanıcı iki hisseyi yan yana görmek istiyor (örn. AKBNK vs GARAN). Yok.  
**Etki:** Orta — SEO için de güçlü: "AKBNK GARAN karşılaştırma" arama niyeti.

**Backend — app.py'e eklenecek:**
```python
@app.route("/karsilastir")
def karsilastir():
    return render_template("karsilastir.html")

@app.route("/api/karsilastir")
@limiter.limit("20 per minute")
def api_karsilastir():
    tickers = request.args.get("tickers", "").upper().split(",")[:4]  # max 4 hisse
    tickers = [t.strip() for t in tickers if t.strip() in STOCK_NAMES]
    if len(tickers) < 2:
        return jsonify({"error": "En az 2 hisse gerekli"}), 400

    with _lock:
        data_map = {s["ticker"]: s for s in _cache["data"]}

    result = []
    for ticker in tickers:
        s = data_map.get(ticker, {})
        # Temel veriler için yfinance çek (cache'lenmiş fundamentals endpoint'inden)
        result.append({
            "ticker":        ticker,
            "name":          STOCK_NAMES.get(ticker, ticker),
            "sector":        next((x for x in [s.get("sector")] if x), "—"),
            "signal":        s.get("signal"),
            "price":         s.get("price"),
            "change_pct":    s.get("change_pct"),
            "adx":           s.get("adx"),
            "signal_bars":   s.get("signal_bars"),
            "entry_quality": s.get("entry_quality"),
            "sl_level":      s.get("sl_level"),
            "tp1":           s.get("tp1"),
            "tp2":           s.get("tp2"),
        })
    return jsonify({"stocks": result})
```

**Yeni template:** `templates/karsilastir.html`  
UI: Üstte her hisse için arama kutusu (autocomplete), altta yan yana karşılaştırma kartları.

**URL yapısı:** `/karsilastir?tickers=AKBNK,GARAN` (paylaşılabilir link)

**SEO:** Her ticker kombinasyonu için title/description dinamik oluşturulmalı.  
**Kabul Kriteri:** `/karsilastir?tickers=AKBNK,GARAN` açıldığında iki hissenin sinyali, fiyatı, ADX'i yan yana görünüyor.

---

### 7. `/ozet/<tarih>` — Geçmiş Günlük Özet

**Problem:** `/ozet` yalnızca güncel sinyalleri gösteriyor. "Dünkü sinyaller neydi?" sorusunun cevabı yok. Düşük teknik efor, yüksek geri dönüş oranı değeri.  
**Etki:** Orta — güven artırır, sinyal şeffaflığı sağlar.

**Backend — app.py değişiklikleri:**

*1. Günlük snapshot kaydetme (mevcut `_refresh_data` fonksiyonuna ekle):*
```python
SNAPSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

def _save_daily_snapshot(data: list):
    """Her gün saat 18:00'den sonra çalıştığında bugünün snapshot'ını kaydet."""
    now = datetime.now()
    if now.hour < 17:  # Seans kapanmadan kaydetme
        return
    fname = os.path.join(SNAPSHOTS_DIR, f"{now.strftime('%Y-%m-%d')}.json")
    if os.path.exists(fname):
        return  # Bugün zaten kaydedildi
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({"date": now.strftime("%Y-%m-%d"), "data": data,
                       "saved_at": now.isoformat()}, f, ensure_ascii=False)
        logger.info("Günlük snapshot kaydedildi: %s", fname)
    except Exception as e:
        logger.error("Snapshot kaydetme hatası: %s", e)
```

*2. Geçmiş route'u:*
```python
@app.route("/ozet/<tarih>")
def ozet_tarih(tarih):
    """Geçmiş günlük özet. tarih formatı: YYYY-AA-GG"""
    import re as _re
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", tarih):
        abort(404)
    fname = os.path.join(SNAPSHOTS_DIR, f"{tarih}.json")
    if not os.path.exists(fname):
        abort(404)
    try:
        with open(fname, encoding="utf-8") as f:
            snap = json.load(f)
    except Exception:
        abort(404)
    return render_template("ozet.html", historical=snap, historical_date=tarih)
```

**templates/ozet.html değişikliği:** `{% if historical %}` bloğu ile geçmiş veri render'lanır, canlı SSE bağlantısı kurulmaz.

**Kabul Kriteri:** `/ozet/2026-04-25` açıldığında o günün sinyal durumu görünüyor; `/ozet/1990-01-01` 404 döndürüyor.

---

## 🟢 TIER 3 — Uzun Vadeli / Büyük Özellikler (1+ hafta)

### 8. Web Push Bildirimleri (VAPID)

**Durum:** Service worker var (`/static/sw.js`) ama `push` event listener yok. E-posta aboneliği var ama browser push yok.

**Gereksinimler:**
- `pywebpush` Python kütüphanesi (`pip install pywebpush`)
- VAPID key çifti oluştur: `vapid --gen` veya `webpush.generate_vapid_keys()`
- Env var: `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_SUB=mailto:iletisim@borsapusula.com`
- Yeni tablo/JSON: push_subscribers.json (endpoint + keys depolanır)

**sw.js'e eklenecek:**
```javascript
self.addEventListener('push', e => {
  const d = e.data?.json() || {};
  e.waitUntil(
    self.registration.showNotification(d.title || 'BorsaPusula', {
      body: d.body || '',
      icon: '/static/favicon.svg',
      badge: '/static/favicon.svg',
      data: { url: d.url || '/' }
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data.url));
});
```

**Öneri:** Sinyal değişimi push'u ile başla (günde max 1-2 bildirim). Kullanıcı, ilgilendiği hisseler için abone olabilsin.

---

### 9. Sunucu Taraflı Portföy (Opsiyonel Login)

**Durum:** Portföy şu an localStorage'da. Tarayıcı değişince kayboluyor.

**Yaklaşım:** Basit anonim token sistemi (hesap açmadan, token ile):
- Kayıt olmadan UUID token üret → kullanıcıya ver
- Token + portföy JSON → sunucuda sakla
- `/api/portfolio/<token>` GET/POST endpoints
- Token'ı kullanıcıya QR kod veya kopyalama ile ver

Bu yaklaşım KVKK açısından temiz (ad/e-posta yok), teknik yükü hafif.

---

### 10. Blog Makale Trafiği Artışı

**Mevcut durum:** 27 makale var ama FAQPage schema yok (Tier 1'de ele alındı).

**Ek yapılacaklar:**
- Her makaleye "İlgili Hisseler" bloğu: `blog_content.py`'de `related_tickers: ["AKBNK", "GARAN"]` alanı ekle → `blog_article.html`'de bu hisselerin güncel sinyalleri göster (API'den çek)
- İç bağlantı: Her makalenin sonunda ilgili 2-3 makaleye link
- Makale paylaşım butonları (Twitter/X, WhatsApp) — özellikle mobilde önemli
- Okuma süresi hesabı: `blog_content.py`'de `read_time` alanı (kelime sayısı / 200)

---

## 📊 Öncelik Özeti

| # | Özellik | Efor | Etki | Öncelik |
|---|---|---|---|---|
| 1 | GA4 analytics | 1 saat | Yüksek | 🔴 Hemen |
| 2 | Makro ticker alt sayfalarda | 1 saat | Orta | 🔴 Hemen |
| 3 | İletişim formu backend | 2 saat | Orta | 🔴 Hemen |
| 4 | Blog FAQPage schema | 3 saat | Yüksek (SEO) | 🔴 Hemen |
| 5 | `/tarama` tarayıcı | 2-3 gün | Çok Yüksek | 🟡 Bu hafta |
| 6 | `/karsilastir` karşılaştırma | 1-2 gün | Orta-Yüksek | 🟡 Bu hafta |
| 7 | `/ozet/<tarih>` geçmiş | 1 gün | Orta | 🟡 Bu hafta |
| 8 | Web Push (VAPID) | 1 hafta | Orta | 🟢 Sonraki sprint |
| 9 | Sunucu taraflı portföy | 2 hafta | Orta | 🟢 Sonraki sprint |
| 10 | Blog ilgili hisseler | 3-4 saat | Orta-Yüksek | 🟢 Sonraki sprint |

---

## 🧪 Her Özellik İçin Hızlı Test Prosedürü

### GA4
```bash
# Tarayıcı DevTools Network tab'ında filtrele:
# Filter: google-analytics.com
# Sayfa açıldığında hit görünmeli
```

### Makro Ticker
```bash
curl -s http://localhost:5001/api/macro | python3 -m json.tool | head -20
# items[] dizi boş değilse frontend çalışır
```

### İletişim Formu
```bash
curl -X POST http://localhost:5001/api/contact \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","subject":"Test","message":"Test mesajı"}'
# {"ok": true} dönmeli
```

### Tarayıcı
```bash
curl -s "http://localhost:5001/api/tarama?signal=AL&min_adx=25" | python3 -m json.tool | grep ticker
# AL sinyalli hisseler listelenmeli
```

---

*Bu belge, canlı koddan okunarak oluşturulmuştur. Her "eksik" madde gerçekten app.py ve templates/ altında aranarak doğrulanmıştır.*
