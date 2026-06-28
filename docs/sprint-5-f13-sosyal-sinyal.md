# Sprint 5 F13 — Sosyal Sinyal Feed Spec

**Tarih:** 28 Haziran 2026  
**Sprint:** 5 (Tem sonu – Ağu 2026)  
**Effort:** L  
**Ticket:** F13

---

## 1. Konsept

Kullanıcıların "bu hisseyi izliyorum / aldım / sattım" eylemlerini anonim olarak topla ve diğer kullanıcılara **topluluk sinyali** olarak göster. Amaç: bireysel teknik sinyale sosyal kanıt katmanı eklemek.

**Temel prensipler:**
- **Gizlilik önce:** Hiçbir eylem bireysel kullanıcıya bağlanmaz. İsim, email, IP log'lanmaz.
- **Opt-in:** Paylaşım varsayılan olarak kapalı; kullanıcı açıkça seçmeli.
- **Agregasyon:** Minimum 5 kullanıcı eşiği altında veri gösterilmez (k-anonimlik).

---

## 2. Veri Modeli — Sosyal Eylem

### 2a. Event Yapısı

```python
{
  "event_id":  "ev_20260714_143021_a7f3",  # UUID4-benzeri, UUID4 yerine hash(timestamp+random)
  "ticker":    "AKBNK",
  "action":    "izle",           # izle | al | sat | cikart
  "ts":        1752498621,       # Unix timestamp (integer, dakika hassasiyetine yuvarla → gizlilik)
  "session_hash": "b3c4d5..."    # sha256(session_id)[:12] — tekrar sayım önler, kim olduğunu belli etmez
}
```

**Kaydedilmeyen veriler:** IP adresi, email, kullanıcı adı, kesin saat (dakika yuvarlama), user-agent.

### 2b. Storage

```
/root/bist30/social_feed/events_{YYYY_WW}.jsonl
```

Haftalık JSONL dosyaları. Her 7 günde yeni dosya. Eski dosyalar 4 hafta sonra silinir (GDPR/KVKK data retention).

**Toplam disk tahmini:** ~5 olay/aktif kullanıcı/gün × 200 kullanıcı × 7 gün ≈ 7000 satır/hafta ≈ ~700 KB/hafta.

### 2c. Agregasyon Tablosu (Önbellek)

Ham event'lerden türetilen, 15 dakikada bir hesaplanan özet:

```json
{
  "AKBNK": {
    "izleyen_7d": 34,
    "alan_7d":    12,
    "satan_7d":    5,
    "trend_badge": "izleniyor",  # izleniyor | alim_dalgasi | satis_baskisi | sakin
    "updated_at": 1752498621
  }
}
```

`trend_badge` kuralı:

| Kural | Badge |
|-------|-------|
| `alan_7d` ≥ 10 VE `alan_7d` > `satan_7d` × 2 | `alim_dalgasi` |
| `satan_7d` ≥ 10 VE `satan_7d` > `alan_7d` × 2 | `satis_baskisi` |
| `izleyen_7d` ≥ 5 | `izleniyor` |
| Hiçbiri | `sakin` (gösterilmez) |

**K-anonimlik:** Herhangi bir metrik < 5 ise o metrik `null` döndürülür.

---

## 3. Opt-in / Opt-out Akışı

### 3a. İlk Kez Karşılaşma

Kullanıcı virtual portfolio'ya hisse eklediğinde veya watchlist'i kaydettiğinde — **bir kez** gösterilecek consent banner:

```html
<div id="social-consent-banner" class="social-banner" role="dialog">
  <p>
    <strong>Topluluk verisi paylaşımı</strong><br>
    Hareketleriniz (izleme, alım, satım) <em>anonim olarak</em> topluluk istatistiklerine katkı sağlayabilir.
    Kişisel veri paylaşılmaz.
  </p>
  <button id="social-opt-in">Katıl (anonim)</button>
  <button id="social-opt-out">Hayır, teşekkürler</button>
  <a href="/gizlilik" target="_blank">Gizlilik Politikası</a>
</div>
```

Seçim `localStorage["social_consent"]` = `"in"` / `"out"` olarak kaydedilir. Banner bir daha çıkmaz.

### 3b. Ayarlar Sayfası

`/ayarlar` veya `/hesap` sayfasında "Topluluk verisi paylaşımı" toggle'ı:

```html
<label class="toggle-row">
  <span>Anonim topluluk istatistiklerine katkı sağla</span>
  <input type="checkbox" id="social-toggle" />
</label>
```

Toggle değiştiğinde `localStorage["social_consent"]` güncellenir. **Sunucuya kaydedilmez** — tamamen istemci tarafı. Server event log'a girmesin diye frontend `social_consent !== "in"` kontrolü yapar, `false` ise `POST /api/social/event` çağrılmaz.

---

## 4. Backend Endpoint'leri

### 4a. POST /api/social/event

```
POST /api/social/event
Auth: Opsiyonel (login olmayan kullanıcı event gönderebilir — session_hash yeterli)
Body: {
  "ticker": "AKBNK",
  "action": "izle"   # izle | al | sat | cikart
}
Response: { "ok": true }
```

**Server-side:**
- IP log'lanmaz.
- `session_hash = sha256(request.cookies.get("session", uuid4()))[:12]`
- Timestamp dakikaya yuvarlanır: `ts = int(time.time() // 60) * 60`
- Rate limit: 20/saat/session (spam önleme).
- Ticker whitelist: BIST30 + izin verilen liste.

### 4b. GET /api/social/feed

```
GET /api/social/feed?ticker=AKBNK
GET /api/social/feed        # tüm BIST30 özeti

Response:
{
  "ok": true,
  "data": {
    "AKBNK": {
      "izleyen_7d": 34,
      "alan_7d":    12,
      "satan_7d":   null,  # < 5 → null (k-anonimlik)
      "trend_badge": "alim_dalgasi"
    }
  },
  "updated_at": 1752498621
}
```

**Cache:** 15 dakika (in-memory). Aggregate hesaplama arka plan thread'inde her 15 dakikada bir çalışır.

### 4c. DELETE /api/social/my-events (GDPR/KVKK Silme Hakkı)

```
DELETE /api/social/my-events
Auth: Cookie (login zorunlu)
Body: { "session_hash": "b3c4d5..." }

Response: { "ok": true, "deleted_count": 7 }
```

JSONL dosyalarından o `session_hash`'e ait tüm satırları filtreler. Statik agregasyon bir sonraki 15dk döngüsünde güncellenecek.

---

## 5. Frontend — Sosyal Kanıt Badge

### 5a. Hisse Kartında (Ana Sayfa / Sinyal Tablosu)

```html
<span class="social-badge social-badge--alim" title="Son 7 günde 12 kişi aldı">
  👥 12 alım
</span>
```

| Badge | CSS Sınıfı | Renk |
|-------|-----------|------|
| `alim_dalgasi` | `social-badge--alim` | Yeşil |
| `satis_baskisi` | `social-badge--satis` | Kırmızı |
| `izleniyor` | `social-badge--izle` | Mavi |
| `sakin` / null | — (gösterilmez) | — |

Badge yalnızca `alan_7d` veya `izleyen_7d` ≥ 5 ise gösterilir.

### 5b. Hisse Detay Modalı

Modal alt bölümünde:

```
Topluluk (son 7 gün)
👁 34 kişi izliyor   🟢 12 alım   🔴 — satış

Anonim ve agregat veriye dayanır.
```

### 5c. Trending Tickers Feed

Ana sayfada "Bugün Öne Çıkanlar" kutusu (mevcut haber feed'inin altına):

```
🔥 Topluluk Radari
┌─────────────────────────────────────────┐
│ AKBNK    👥 34 izleyen  🟢 Alım dalgası │
│ THYAO    👥 28 izleyen  📊 Stabil       │
│ GARAN    👥 19 izleyen  🟢 Alım dalgası │
└─────────────────────────────────────────┘
```

Top 5 — `izleyen_7d + alan_7d` toplam skoruna göre sıralanır. Günde bir kez güncellenir (15dk cache yeterli, ayrıca daily sort gerekmez).

---

## 6. Event Tetikleme Noktaları

| Kullanıcı Aksiyonu | Tetiklenen Event |
|-------------------|-----------------|
| Watchlist'e hisse ekleme | `action: "izle"` |
| Watchlist'ten hisse çıkarma | `action: "cikart"` |
| Virtual portfolio'ya hisse açma | `action: "al"` |
| Virtual portfolio'da pozisyon kapatma | `action: "sat"` |

Frontend her aksiyonda önce `social_consent === "in"` kontrolü yapar, evet ise `POST /api/social/event` gönderir (fire-and-forget, `fetch` + `.catch()` — UI bloklanmaz).

---

## 7. GDPR / KVKK Uyum

| Gereklilik | Uygulama |
|-----------|---------|
| Açık rıza (consent) | Opt-in banner + localStorage |
| Hangi veri toplandığı | Banner metni + Gizlilik Politikası sayfasında F13 maddesi |
| Silme hakkı | `DELETE /api/social/my-events` (session_hash ile) |
| Data retention | Haftalık JSONL dosyaları 4 hafta sonra silinir |
| Kişisel veri işlenmemesi | IP/email/kullanıcı adı event'e dahil edilmez |
| Kapsam | Türkiye — KVKK md. 5/2-f "meşru menfaat" uygulanabilir; opt-in ile her türlü risk bertaraf |

Gizlilik Politikası sayfasına eklenmesi gereken madde taslağı:

> **Anonim Kullanım İstatistikleri (F13)**  
> BorsaPusula, kullanıcıların gönüllü onayıyla hisse izleme/alım/satım eylemlerini anonim ve toplu olarak kaydedebilir. Kişisel veri (ad, e-posta, IP) bu süreçte işlenmez. Bireysel eyleme ulaşılması teknik olarak mümkün değildir; veriler yalnızca 5 kişi eşiği sağlandığında topluluk istatistiklerine dahil edilir. Onayınızı istediğiniz zaman [Hesap Ayarları] sayfasından geri çekebilirsiniz. Veriler en fazla 28 gün saklanır.

---

## 8. Agregasyon Thread

```python
_SOCIAL_AGG_CACHE = {"data": {}, "updated_at": 0}
_SOCIAL_AGG_LOCK = threading.Lock()

def _recompute_social_agg():
    """Son 7 günün JSONL dosyalarından ticker bazlı saydır."""
    from collections import defaultdict
    counts = defaultdict(lambda: {"izle": 0, "al": 0, "sat": 0, "cikart": 0})
    
    social_dir = os.path.join(_APP_DIR, "social_feed")
    now_week = int(time.time() // (7 * 86400))
    for wk in range(now_week - 1, now_week + 1):  # bu hafta + önceki hafta
        fname = os.path.join(social_dir, f"events_{wk}.jsonl")
        if not os.path.exists(fname):
            continue
        cutoff = time.time() - 7 * 86400
        with open(fname) as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    if ev["ts"] < cutoff:
                        continue
                    counts[ev["ticker"]][ev["action"]] += 1
                except Exception:
                    continue

    result = {}
    for ticker, c in counts.items():
        izl = c["izle"] + c["al"]   # izleyen = izle + al (pozisyon sahibi de izliyor)
        al  = c["al"]
        sat = c["sat"]
        badge = "sakin"
        if al >= 10 and al > sat * 2:
            badge = "alim_dalgasi"
        elif sat >= 10 and sat > al * 2:
            badge = "satis_baskisi"
        elif izl >= 5:
            badge = "izleniyor"
        result[ticker] = {
            "izleyen_7d": izl if izl >= 5 else None,
            "alan_7d":    al  if al  >= 5 else None,
            "satan_7d":   sat if sat >= 5 else None,
            "trend_badge": badge,
        }

    with _SOCIAL_AGG_LOCK:
        _SOCIAL_AGG_CACHE["data"] = result
        _SOCIAL_AGG_CACHE["updated_at"] = int(time.time())
```

Her 15 dakikada bir background thread olarak çalışır (`_schedule_social_agg_refresh()`). `_is_gemini_leader()` ile aynı pattern — leader-only değil, tüm worker'larda çalışabilir (idempotent sonuç).

---

## 9. Test Planı

```
1. Opt-in consent banner → "Katıl" tıkla → localStorage["social_consent"] = "in"
2. Watchlist'e AKBNK ekle → POST /api/social/event {ticker:"AKBNK", action:"izle"} çağrıldı mı?
3. 5 farklı session_hash ile "izle" gönder → GET /api/social/feed → izleyen_7d = 5
4. 4 session_hash ile "al" gönder → alan_7d null (< 5 eşiği)
5. 5. "al" → alan_7d = 5, trend_badge değişti mi?
6. 10 "al" + 4 "sat" → badge = "alim_dalgasi"
7. "Hayır, teşekkürler" → watchlist ekleme → event gönderilmedi
8. DELETE /api/social/my-events → o session'ın eventleri silindi
9. 28 gün önceki JSONL → otomatik silinmiş
10. k-anonimlik: 3 kişi "al" → api yanıtında alan_7d null
```

---

## 10. Implementation Sırası (Sprint 5)

1. **Gün 1:** `social_feed/` dizin yapısı + JSONL yardımcıları + `_recompute_social_agg()`
2. **Gün 2:** `POST /api/social/event` + `GET /api/social/feed` endpoint'leri
3. **Gün 3:** Opt-in banner + localStorage consent logic + `DELETE /api/social/my-events`
4. **Gün 4:** Frontend event tetikleme (watchlist + VP entegrasyonu) + badge bileşeni
5. **Gün 5:** Trending ticker kutusu (ana sayfa) + karanlık tema uyumu
6. **Gün 6:** KVKK metin ekle (gizlilik sayfası) + Ayarlar toggle
7. **Gün 7:** Test + deploy (seans sonrası)

---

*Spec: DEV-888 | Hedef: Sprint 5*
