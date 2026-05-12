# UptimeRobot Monitor Kurulumu

Mevcut monitor'a ek olarak **3 yeni monitor** ekle.

## Monitor 1: API Health (KEYWORD CHECK)

Bu en önemli — sistem degraded olduğunda yakalar.

| Alan | Değer |
|---|---|
| **Monitor Type** | `Keyword (HTTP)` |
| **URL** | `https://borsapusula.com/api/health` |
| **Keyword** | `"status": "OK"` |
| **Alert when keyword** | `Not Exists` |
| **Interval** | 1 minute (free: 5 min, paid: 1 min) |
| **Timeout** | 30 seconds |
| **HTTP Method** | GET |
| **Custom HTTP Headers** | (yok) |

**Bu monitor şu senaryoları yakalar:**
- `status: DEGRADED` (stocks=0 veya macro stale)
- HTTP 500/502/504
- Connection timeout
- DNS sorunu

## Monitor 2: Macro Endpoint (KEYWORD CHECK — stale data)

| Alan | Değer |
|---|---|
| **Monitor Type** | `Keyword (HTTP)` |
| **URL** | `https://borsapusula.com/api/health` |
| **Keyword** | `"last_macro_refresh_age_s": null` |
| **Alert when keyword** | `Exists` (= bg loop hiç refresh yapmadı, ALARM) |
| **Interval** | 5 minutes |
| **Timeout** | 30 seconds |

VEYA daha akıllı versiyon (paid plan'da regex destekli):
- Keyword: `"last_macro_refresh_age_s": (null|[2-9][0-9]{3,})`  
  → Alert: macro 1 saatten eski (3600s+) veya null

## Monitor 3: News Endpoint (sample ticker)

| Alan | Değer |
|---|---|
| **Monitor Type** | `HTTP(s)` |
| **URL** | `https://borsapusula.com/api/hisse/THYAO/news` |
| **Expected Status** | 200 |
| **Interval** | 5 minutes |
| **Timeout** | 15 seconds |
| **Alert when status not 200** | Yes |

THYAO seçildi çünkü:
- BIST100'de ✓
- KAP bildirimi sıkça gelir (uçuş trafiği, vs.)
- Aktif ticker

---

## Alert Contacts

Mevcut Polymarket alarm mail adresine ekle:
- E-mail: ozan-turk19@hotmail.com
- Yeniden gönderme: 2 saatte bir (boğmasın)

---

## Status Page (opsiyonel)

UptimeRobot free plan **public status page** desteği var:

1. Dashboard → Status Pages → Add New
2. Monitors: tüm 4 monitor (mevcut + 3 yeni)
3. URL: `https://stats.uptimerobot.com/<your-id>`

Kullanıcılara "Sistem Sağlığı" link'i verebiliriz footer'da.

---

## Test Sonrası Doğrulama

3 monitor eklendiğinde:

```
✓ Monitor 1: api/health keyword "OK" → up
✓ Monitor 2: last_macro_refresh_age_s null değil → up
✓ Monitor 3: THYAO/news → 200
```

Birinde down olursa mail gelmeli. Test için:
```bash
# Service stop → 1-5 dakika sonra alarm gelir
ssh root@135.181.206.109 systemctl stop bist30
sleep 60
# Mail gelmeli
ssh root@135.181.206.109 systemctl start bist30
# 5 dakika sonra resolved mail gelir
```
