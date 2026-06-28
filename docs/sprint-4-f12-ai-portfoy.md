# Sprint 4 F12 — AI Portföy Önerisi Spec

**Tarih:** 28 Haziran 2026  
**Sprint:** 4 W3–4 (14–27 Tem 2026)  
**Effort:** L  
**Ticket:** F12

---

## 1. Mevcut Durum

| Bileşen | Durum | Dosya:Satır |
|---|---|---|
| Gemini API istemcisi + leader gate | ✅ Hazır | `app.py:1738-1752` |
| `_gemini_call()` yardımcısı | ✅ Hazır | `app.py:4335+` |
| Virtual portfolio (kullanıcı pozisyonları) | ✅ Hazır | `app.py:9340`, `virtual_portfolio.json` |
| BIST30 sinyal verileri | ✅ Hazır | `_signals_cache` (app.py) |
| Makro AI özeti (Gemini) | ✅ Hazır | `app.py:3860-3935` |
| **Risk profili formu** | ❌ Eksik | — |
| **Portföy öneri prompt + endpoint** | ❌ Eksik | — |
| **Öneri UI** | ❌ Eksik | — |

---

## 2. Kullanıcı Akışı

```
Kullanıcı → Virtual Portfolio sayfası
  → "Portföyümü Analiz Et" butonu
  → Risk profili adımı (eğer hiç doldurulmadıysa)
  → Gemini analizi başlatıldı (spinner)
  → Sonuç overlay: sektör dağılımı + öneriler + uyarı
```

---

## 3. Risk Profili Formu

### 3a. Alanlar

| Alan | Tip | Değerler | Zorunlu |
|------|-----|---------|---------|
| Yatırım ufku | radio | `short` (0-3 ay), `medium` (3-12 ay), `long` (1+ yıl) | Evet |
| Risk toleransı | radio | `dusuk` (sermaye koruma), `orta` (dengeli), `yuksek` (agresif büyüme) | Evet |
| Mevcut portföy amacı | checkbox (multi) | `kar_al`, `uzun_tut`, `cesitle`, `test_ediyor` | Hayır |
| Hisse başına max ağırlık % | number | 5–50, varsayılan 20 | Hayır |

### 3b. Depolama

`virtual_portfolio.json` içine `risk_profile` anahtarı olarak eklenir (kullanıcı ID ile ayrılmış mevcut yapıya uygun):

```json
{
  "email_hash": "abc123...",
  "risk_profile": {
    "horizon": "medium",
    "tolerance": "orta",
    "goals": ["uzun_tut", "cesitle"],
    "max_weight_pct": 20,
    "filled_at": "2026-07-14T10:00:00"
  },
  "positions": [ ... ]
}
```

Risk profili doldurulduktan sonra bir daha sorulmaz; `/virtual-portfolio` sayfasında "Profili Güncelle" linki ile değiştirilebilir.

---

## 4. Portföy Analiz Verisi Derleme

`/api/portfoy-oneri` endpoint'i içeride şunları birleştirir:

```python
def _build_portfolio_context(email):
    vp = _load_vp(email)           # pozisyonlar: [{ticker, shares, entry_price, ...}]
    signals = _get_signals_cache() # {AKBNK: {signal: "AL", score: 1.43, ...}, ...}
    macro = _get_macro_summary()   # mevcut makro AI metni (önbellek)

    holdings = []
    total_value = sum(pos["current_value"] for pos in vp["positions"])
    for pos in vp["positions"]:
        ticker = pos["ticker"]
        weight_pct = round(pos["current_value"] / total_value * 100, 1) if total_value else 0
        sig = signals.get(ticker, {})
        holdings.append({
            "ticker":      ticker,
            "weight_pct":  weight_pct,
            "pnl_pct":     pos.get("pnl_pct", 0),
            "signal":      sig.get("signal", "—"),
            "signal_score": sig.get("score"),
        })

    return {
        "holdings": holdings,
        "risk_profile": vp.get("risk_profile", {}),
        "macro_summary": macro[:500],   # token tasarrufu için ilk 500 karakter
    }
```

---

## 5. Gemini Prompt Template

```
Sen BorsaPusula'nın kişisel yatırım asistanısın.
Kullanıcı BIST30 hisselerinden oluşan bir portföy tutuyor.
Aşağıdaki verilere bakarak 3-5 maddelik, somut ve kısa öneriler üret.

### Portföy
{holdings_table}

### Kullanıcı Profili
- Yatırım ufku: {horizon}
- Risk toleransı: {tolerance}
- Hisse başı max ağırlık: {max_weight_pct}%

### Piyasa Özeti (bugün)
{macro_summary}

### Yanıt Formatı (JSON, TR, teknik terimden kaçın)
{
  "ozet": "1-2 cümle genel değerlendirme",
  "oneriler": [
    { "hisse": "AKBNK", "eylem": "tut|azalt|artir|dikkat", "neden": "..." },
    ...  (max 5)
  ],
  "uyari": "Gerekirse risk uyarısı, yoksa null"
}
```

**Token bütçesi:** `max_tokens=400`, `temperature=0.3`  
**Prompt boyutu:** ~600-800 token (holdings tablosu + makro özet)

---

## 6. Endpoint: POST /api/portfoy-oneri

```
POST /api/portfoy-oneri
Auth: Cookie (login zorunlu)
Body: { "force_refresh": false }   # true → önbelleği yok say

Response 200:
{
  "ok": true,
  "ozet": "Portföyünüz dengeli görünüyor ancak...",
  "oneriler": [
    { "hisse": "THYAO", "eylem": "tut", "neden": "AL sinyali aktif, EMA kırılımı pozitif" },
    { "hisse": "GARAN", "eylem": "artir", "neden": "Düşük ağırlık, güçlü Sharpe geçmişi" },
    { "hisse": "EREGL", "eylem": "dikkat", "neden": "SAT sinyali + ağır pozisyon (%28)" }
  ],
  "uyari": "Bu öneriler bilgi amaçlıdır, yatırım tavsiyesi değildir.",
  "cached_at": "2026-07-14T10:05:00",
  "cache_fresh": true
}

Response 400: { "ok": false, "error": "portfoy_bos" }
Response 401: { "ok": false, "error": "login_required" }
Response 503: { "ok": false, "error": "ai_unavailable" }
```

### Önbellek (Cache)

Her kullanıcı için sonuç 4 saat önbelleğe alınır (`/root/bist30/portfoy_oneri/{hash}.json`).  
`force_refresh: true` veya portföy değişimi (position count/composition farkı) → yeni çağrı.

**Rate limit:** 3/saat/kullanıcı (`@limiter.limit("3 per hour")`).

### Leader Gate

Gemini çağrısı doğrudan endpoint'ten yapılır (background thread'e gerek yok — kullanıcı istediğinde tetikler). `_is_gemini_leader()` kontrolü gerekmiyor; per-user önbellek sayesinde her istek tek Gemini çağrısı yapar.

---

## 7. Frontend UI

### 7a. "Portföyümü Analiz Et" Butonu

**Konum:** Virtual Portfolio sayfası (`virtual_portfolio.html`) — tablo altı, "Backtest" butonu yanına.

```html
<button id="vp-analyze-btn" class="vp-action-btn">
  🤖 Portföyümü Analiz Et
</button>
```

Risk profili dolmamışsa → önce `#vp-risk-modal` gösterilir, form submit sonrası analiz tetiklenir.

### 7b. Risk Profili Modal (#vp-risk-modal)

3 adımlı minimal form (bir sayfada):

```html
<div class="modal" id="vp-risk-modal">
  <h3>Kısa Profil (1 dk)</h3>
  <p>Öneriler profilinize göre şekillenecek.</p>
  <!-- Yatırım ufku -->
  <fieldset>
    <legend>Ne kadar süre tutmayı planlıyorsunuz?</legend>
    <label><input type="radio" name="horizon" value="short"> 0-3 ay</label>
    <label><input type="radio" name="horizon" value="medium" checked> 3-12 ay</label>
    <label><input type="radio" name="horizon" value="long"> 1 yıldan fazla</label>
  </fieldset>
  <!-- Risk toleransı -->
  <fieldset>
    <legend>Risk toleransınız?</legend>
    <label><input type="radio" name="tolerance" value="dusuk"> Düşük</label>
    <label><input type="radio" name="tolerance" value="orta" checked> Orta</label>
    <label><input type="radio" name="tolerance" value="yuksek"> Yüksek</label>
  </fieldset>
  <button id="vp-risk-submit">Analizi Başlat</button>
</div>
```

### 7c. Sonuç Overlay (#vp-oneri-panel)

```html
<div id="vp-oneri-panel" class="vp-oneri-panel hidden">
  <div class="vp-oneri-header">
    <span>🤖 AI Portföy Değerlendirmesi</span>
    <small id="vp-oneri-time"></small>
    <button id="vp-oneri-close">✕</button>
  </div>
  <p id="vp-oneri-ozet" class="vp-ozet"></p>
  <table id="vp-oneri-table">
    <thead><tr><th>Hisse</th><th>Öneri</th><th>Neden</th></tr></thead>
    <tbody></tbody>
  </table>
  <p class="vp-oneri-disclaimer" id="vp-oneri-uyari"></p>
  <button id="vp-oneri-refresh">↻ Yenile</button>
</div>
```

**Eylem renkleri:**

| Eylem | Renk |
|-------|------|
| `artir` | Yeşil |
| `tut` | Gri/Nötr |
| `azalt` | Sarı |
| `dikkat` | Kırmızı |

---

## 8. Explainability Kuralları

1. Her öneri `neden` alanı **sinyal verisine referans vermelidir** — "AL sinyali aktif", "SAT sinyali geldikten bu yana 5 gün", "portföy ağırlığı %28 — max tolerans %20" gibi.
2. Genel piyasa kopyası yasak — Gemini prompt'u bunu açıkça kısıtlar.
3. Disclaimer her zaman gösterilir (yasal zorunluluk).

---

## 9. Maliyet Yönetimi

| Parametre | Değer |
|-----------|-------|
| max_tokens | 400 |
| Prompt boyutu | ~700 token |
| Toplam per-call | ~1100 token |
| Cache süresi | 4 saat |
| Aktif kullanıcı estimate | 50/gün |
| Günlük Gemini çağrısı tahmini | ~50 (her kullanıcı 4h'te 1) |

Gemini Flash fiyatı ile aylık maliyet: 50 × 30 × 1100 token ≈ 1.65M token/ay → Flash $0.075/1M = **~$0.12/ay** (ihmal edilebilir).

---

## 10. Test Planı

```
1. VP'ye 3+ hisse ekle → "Portföyümü Analiz Et" tıkla
2. Risk profili modal çıksın → doldur → submit
3. Spinner → /api/portfoy-oneri çağrısı → 200 OK
4. Öneri paneli açılsın — 3-5 satır, eylem + neden dolu
5. 4h önce: tekrar tıkla → Gemini çağrısı YOK (cache_fresh: true)
6. force_refresh: true → yeni çağrı
7. VP boşken /api/portfoy-oneri → {"ok": false, "error": "portfoy_bos"}
8. Login olmadan → 401
9. 4. istek aynı saatte → 429 (rate limit)
10. "Profili Güncelle" → risk modal tekrar açılsın, mevcut değerler dolu gelsin
```

---

## 11. Implementation Sırası (Sprint 4 W3–4)

1. **Gün 1:** Risk profili storage (`virtual_portfolio.json` güncelleme) + `/api/vp-risk-profile` PUT endpoint
2. **Gün 2:** `_build_portfolio_context()` + Gemini prompt
3. **Gün 3:** `/api/portfoy-oneri` endpoint + önbellek + rate limit
4. **Gün 4:** Risk profili modal UI + fetch entegrasyonu
5. **Gün 5:** Sonuç overlay UI + eylem renkleri
6. **Gün 6:** Test + disclaimer + deploy (seans sonrası)

---

*Spec: DEV-888 | Hedef: Sprint 4 W3–4*
