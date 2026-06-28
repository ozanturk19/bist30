# Sprint 4 F14 — Backtest History & Karşılaştırma Spec

**Tarih:** 28 Haziran 2026  
**Sprint:** 4 W2 (7–13 Tem 2026)  
**Effort:** M  
**Ticket:** F14

---

## 1. Mevcut Durum

Mevcut `/api/backtest/custom` endpoint'i (app.py:9601) single-shot çalışır: parametre gönder, sonuç al, sayfa kapandığında kaybolur. Kullanıcı farklı parametre kombinasyonlarını karşılaştırmak istediğinde sıfırdan başlamak zorunda kalıyor.

| Bileşen | Durum | Dosya:Satır |
|---|---|---|
| `/api/backtest/custom` POST | ✅ Hazır | `app.py:9601-9672` |
| Backtest hesaplama motoru | ✅ Hazır | `backtest.py` |
| Backtest sayfası | ✅ Hazır | `backtest.html`, `app.py:9579` |
| **Sonuç kaydetme** | ❌ Eksik | — |
| **History listesi + yükleme** | ❌ Eksik | — |
| **Karşılaştırma UI** | ❌ Eksik | — |

---

## 2. Veri Modeli — Saved Backtest Entity

Her kayıtlı backtest bir JSON satırı olarak kullanıcı bazlı dosyada saklanır.

```python
# Yapı
{
  "id": "bt_20260628_143021_AKBNK",   # {bt}_{YYYYMMDD}_{HHMMSS}_{ticker}
  "saved_at": "2026-06-28T14:30:21",  # ISO 8601 UTC
  "label": "AKBNK 3Y Stop5%",        # Kullanıcının verdiği isim (opsiyonel, max 40 chr)
  "params": {
    "ticker": "AKBNK",
    "strategy": "current",
    "use_3bar": false,
    "period": "3y",
    "stop_pct": 5.0,
    "trail_pct": null
  },
  "stats": {
    "total_trades": 18,
    "win_rate": 0.56,
    "sharpe": 1.82,
    "max_dd": -0.127,
    "total_ret": 0.491,
    "avg_bars": 14.3
  }
}
```

**Equity curve kayıt edilmez** (ağır: ~300 punkt × 2 alan). Karşılaştırma istatistik tabanlı; overlay chart gerekirse ayrı re-run.

### Storage Yolu

```
/root/bist30/bt_history/{sha256(email)[:16]}.jsonl
```

JSONL (JSON Lines) — append-only, her satır bir kayıt. Kullanıcı başına max 50 kayıt (FIFO drop). `sha256(email)` ile dosya adı → email disk'te açık değil.

---

## 3. Backend — Yeni Endpoint'ler

### 3a. POST /api/backtest/save

Mevcut `/api/backtest/custom` çalışıp sonucu döndükten sonra ayrı kaydet isteği gelir (ya da `/api/backtest/custom` tek seferlik `?save=1` param ile).

```
POST /api/backtest/save
Auth: Cookie (login zorunlu — app.py pattern)
Body: {
  "id": "bt_20260628_143021_AKBNK",   # run anında üretilmiş ID
  "label": "AKBNK 3Y Stop5%",         # kullanıcı isteğe bağlı
  "params": { ... },
  "stats": { ... }
}
Response: { "ok": true, "id": "bt_..." }
```

**Rate limit:** 10/dakika (backtest run'dan bağımsız kayıt isteği).

### 3b. GET /api/backtest/history

```
GET /api/backtest/history
Auth: Cookie (login zorunlu)
Response: {
  "ok": true,
  "items": [
    { "id": "...", "saved_at": "...", "label": "...", "params": {...}, "stats": {...} },
    ...
  ]
}
```

Yeni → eski sıralama. Max 50 item.

### 3c. DELETE /api/backtest/history/{id}

```
DELETE /api/backtest/history/{id}
Auth: Cookie
Response: { "ok": true }
```

JSONL'den o satırı filtreler, dosyayı yeniden yazar (max 50 satır, IO kabul edilebilir).

### 3d. GET /api/backtest/compare?ids=id1,id2,id3

Birden fazla ID'yi tek seferde çekip karşılaştırma tablosuna hazır döndürür.

```
GET /api/backtest/compare?ids=bt_...,bt_...,bt_...
Auth: Cookie
Response: {
  "ok": true,
  "items": [ {id, label, params, stats}, ... ],  # max 4 item
  "delta": {                                       # ilk item baz alınarak fark
    "bt_...": { "sharpe": +0.31, "win_rate": +0.04, "total_ret": -0.02, ... }
  }
}
```

---

## 4. Frontend — Backtest Geçmişi UI

### 4a. Backtest Sayfası Değişiklikleri (`backtest.html`)

**"Kaydet" butonu** — run tamamlandıktan sonra sonuç panelinde gösterilir:

```html
<button id="bt-save-btn" class="bt-action-btn" hidden>
  💾 Kaydet
</button>
<input id="bt-save-label" type="text" maxlength="40" placeholder="İsim (opsiyonel)" hidden />
```

**"Geçmiş" toggle paneli** — sağ üst köşe:

```html
<button id="bt-history-toggle" class="bt-history-btn">📋 Geçmiş (N)</button>
<div id="bt-history-panel" class="bt-history-panel hidden">
  <table id="bt-history-table">
    <thead>
      <tr>
        <th><input type="checkbox" id="bt-select-all" /></th>
        <th>İsim / Hisse</th>
        <th>Süre</th>
        <th>Trades</th>
        <th>Win%</th>
        <th>Sharpe</th>
        <th>Max DD</th>
        <th>Return</th>
        <th></th>
      </tr>
    </thead>
    <tbody id="bt-history-rows"></tbody>
  </table>
  <div class="bt-compare-bar hidden" id="bt-compare-bar">
    <button id="bt-compare-btn">Karşılaştır (N seçili)</button>
  </div>
</div>
```

### 4b. Karşılaştırma Modal'ı

`/api/backtest/compare` sonuçlarını inline tablo olarak gösterir:

| Metrik | AKBNK 3Y | AKBNK 2Y | THYAO 3Y |
|--------|----------|----------|----------|
| Win Rate | **56%** | 52% | 49% |
| Sharpe | **1.82** | 1.51 | 1.23 |
| Max DD | -12.7% | -9.3% | **-8.1%** |
| Return | **+49.1%** | +31.2% | +22.4% |

Delta sütunu (baz = liste sıralaması 1. item): yeşil = iyileşme, kırmızı = kötüleşme.

Max 4 backtest karşılaştırılabilir (UI genişliği kısıtı).

---

## 5. Storage Limitleri ve Güvenlik

| Kural | Değer |
|-------|-------|
| Kullanıcı başına max kayıt | 50 (FIFO — en eski silinir) |
| Label max uzunluk | 40 karakter |
| IDs per compare request | max 4 |
| JSONL dosya max boyutu | ~25 KB / kullanıcı |
| Dosya yolu | `/root/bist30/bt_history/{hash}.jsonl` |
| Auth | Cookie session (login zorunlu) |
| ID format validation | `^bt_\d{8}_\d{6}_[A-Z]{3,6}$` |

---

## 6. Karşılaştırma Algoritması

Delta hesabı basit diff — karmaşık normalize gerekmez:

```python
def build_delta(items):
    base = items[0]["stats"]
    delta = {}
    for item in items[1:]:
        s = item["stats"]
        delta[item["id"]] = {
            "sharpe":     round(s["sharpe"]     - base["sharpe"],     3),
            "win_rate":   round(s["win_rate"]   - base["win_rate"],   3),
            "total_ret":  round(s["total_ret"]  - base["total_ret"],  3),
            "max_dd":     round(s["max_dd"]     - base["max_dd"],     3),
            "avg_bars":   round(s["avg_bars"]   - base["avg_bars"],   1),
        }
    return delta
```

---

## 7. Test Planı

```
1. Login → /backtest → run AKBNK 3Y → "Kaydet" butonuna tıkla
2. GET /api/backtest/history → item listede görünsün
3. Farklı param ile 2. run → kaydet
4. GET /api/backtest/compare?ids=id1,id2 → delta doğru hesaplansın
5. DELETE /api/backtest/history/{id} → listeden kalksın
6. 51. kayıt: FIFO → 1. kayıt silinsin, toplam 50 kalsın
7. Login olmadan GET /api/backtest/history → 401
8. Başka kullanıcının ID'si ile DELETE → 404 (hash farklı dosya)
```

---

## 8. Implementation Sırası (Sprint 4 W2)

1. **Gün 1:** `bt_history/` dizin oluştur + JSONL yardımcıları (`_bt_history_load`, `_bt_history_save`, `_bt_history_delete`)
2. **Gün 2:** `/api/backtest/save` + `/api/backtest/history` endpoint'leri
3. **Gün 3:** `/api/backtest/compare` endpoint + delta builder
4. **Gün 4:** Frontend — geçmiş paneli + kaydet butonu (`backtest.html` + `main.js`)
5. **Gün 5:** Karşılaştırma modal + test + deploy (seans sonrası)

---

*Spec: DEV-888 | Hedef: Sprint 4 W2*
