# FAZ8 "Tipografi/performans" — `/api/macro` client-poll / server-TTL "uyumsuzluğu" iddiası: sınıflandırma + doğrulama (KOD DEĞİŞMEDİ)

**Tarih:** 16.08.2026 (Paz) — DEV2-137
**Kapsam:** Master Donüşüm Programı FAZ8 backlog satırı: "`/api/macro` client-poll/sunucu-TTL uyumsuzluğu (17 sayfa × 60sn)". DEV2-136'nın "bir sonraki turda değerlendirilecek aday" olarak bıraktığı iki kalemden biri.
**Yöntem:** S1/S7/T3.4/T5.2/T5.4/T8-tipografi/T8-başlık/T1.5/ana-sayfa-yük ile aynı disiplin — Workflow ile 1 sınıflandırma ajanı + 1 tamamen bağımsız (öncekini görmeyen, sıfırdan grep/sed çalıştıran) doğrulama ajanı, ikisi de SSH salt-okur (`/root/bist30`, hiçbir dosya değiştirilmedi, hiçbir git/restart komutu çalıştırılmadı). Ayrıca ben (DEV2) kendi bağımsız üçüncü bir kontrolümü de yaptım (app.py:4617-4632 route body + 4500-4579 `_macro_bg_loop` gövdesi elle okundu).

## Sonuç — backlog iddiasının 3 parçası da YANLIŞ, gerçek bir uyumsuzluk yok

| Backlog iddiası | Kanıtlanmış gerçek | Doğru mu |
|---|---|---|
| "17 sayfa" | **15 şablon** (`grep -rln "fetch('/api/macro')" templates/ \| wc -l` = 15, çift-tırnak varyantı da tarandı, 0 ek eşleşme) | ❌ 2 fazla sayılmış |
| "client 60 saniyede bir poll ediyor" | **180 saniye** (`setInterval(fn,180000)`), 15/15 şablonda **tek istisnasız aynı** | ❌ gerçek değerin 1/3'ü |
| "sunucu farklı TTL/periyotta yeniliyor → uyumsuzluk" | Server leader-worker'ın gerçek yfinance-fetch periyodu da `time.sleep(180)` = **180s** — client ile birebir örtüşüyor. `_MACRO_TTL=21600` (6h) bu periyot değil, ayrı bir "stale" **bayrak eşiği** (cache-invalidation değil) | ❌ TTL ile refresh periyodu karıştırılmış, kategori hatası |

**İki bağımsız ajan (birbirini görmeden) ve DEV2'nin kendi üçüncü doğrulaması birebir aynı sonuca vardı: sıfır hata, sıfır anlaşmazlık.**

## Kanıt detayı

### 15 şablon, hepsi `setInterval(fn, 180000)`

| # | Şablon | fetch satırı | setInterval satırı | Değer |
|---|---|---|---|---|
| 1 | bilanco_takvimi.html | 340 | 341 | 180000ms |
| 2 | blog.html | — | 156 | 180000ms |
| 3 | blog_article.html | 416 | 417 | 180000ms |
| 4 | gundem.html | 591 | 610 | 180000ms |
| 5 | hisse.html | 4026 | 4053 | 180000ms |
| 6 | index.html | 2697 | 2704 | 180000ms |
| 7 | karsilastir.html | 873 | 892 | 180000ms |
| 8 | kategori.html | 238 | 252 | 180000ms |
| 9 | metodoloji.html | 379 | 380 | 180000ms |
| 10 | ozet.html | 645 | 646 | 180000ms |
| 11 | portfolio.html | 811 | 812 | 180000ms |
| 12 | sektor_harita.html | 572 | 573 | 180000ms |
| 13 | sinyal_performans.html | 538 | 539 | 180000ms |
| 14 | tarama.html | 586 | 601 | 180000ms |
| 15 | varlik.html | 496 | 550 | 180000ms |

**Elenmiş yanıltıcı komşu interval'lar** (macro'ya ait değil, karıştırılmamalı): `bilanco_takvimi.html:335` (`setInterval(load,1800000)` — bilanço verisi, 30dk), `gundem.html:583-584` (`loadGundem` 5dk, `loadMacroNewsSection` 30dk — ikisi de macro değil), `sinyal_performans.html:364,402` (macro'yla ilgisiz iki ayrı poll), `portfolio.html:677-678` (`fetchLive`/`fetchCharts` — macro değil), `sektor_harita.html:567` (`load`, 2dk — sektör verisi, macro değil). `kategori.html:264`'teki ikinci `fetch('/api/macro')` on-demand/promise-cache (`getMacroItems()`), periyodik değil — sayıma dahil edilmedi.

### Server: `app.py`

```python
# app.py:4500 _macro_bg_loop()
logger.info("_macro_bg_loop: LEADER worker — yfinance fetch modu (180s)")
...
time.sleep(180)   # 3 dakika   (satır 4573)

# app.py:4579
_MACRO_TTL   = 21600  # CPO-690: 6h — off-hours false-stale bastırılır

# app.py:4617-4632  @app.route("/api/macro")
with _lock:
    cached_items = _macro_cache.get("data") or []
    cached_ts    = _macro_cache.get("ts", 0)
stale = (time.time() - cached_ts) > _MACRO_TTL   # yalnızca "stale" bayrağı, cache invalidation DEĞİL
```

Non-leader/`REFRESH_WORKER=web` worker'lar yfinance çağırmaz, sadece diskten `time.sleep(90)` ile cache'i tazeler — ama alttaki veri kaynağı her zaman leader'ın 180s'lik döngüsü, tutarsızlık yaratmıyor (tasarım gereği: CPO-520/558/591 fcntl-leader-lock + stagger).

## Değerlendirme

Client (180000ms) ve server'ın gerçek veri-yenileme periyodu (`time.sleep(180)`) **tam olarak eşleşiyor** — kasıtlı bir tasarım (muhtemelen client interval'i server refresh cadence'ine göre ayarlanmış). `_MACRO_TTL` (6 saat) ayrı bir mekanizma: "bu veri kaç saattir gelmedi, artık şüpheli say" monitoring eşiği, poll sıklığıyla karşılaştırılabilir bir "TTL" değil — bu ikisini aynı eksende karşılaştırmak backlog cümlesinin temel kategori hatası.

**Bu madde aksiyon gerektirmiyor.** Gerçek bir performans/tazelik sorunu yok. Backlog satırı kapatılmalı ya da (varsa) gerçek bir optimizasyon fırsatı — örn. 15 şablonun her biri bağımsız `setInterval` kurmak yerine merkezi paylaşılan bir poller, ya da SSE/WS'e geçiş — ayrı ve doğru rakamlarla yeniden formüle edilmeli. Bu ikinci öneri düşük öncelikli bir mimari fikir, ayrı T-kodu önerilmiyor.

**Kalan bulgu — 15 vs 17 sayısı:** T5.2'nin "gerilemiş" bulgusu (DEV2-136) ve S7'nin 104-vs-98 rakamı (DEV2-135) ile aynı desen: backlog dokümanındaki bir sayı, kod driftı değil, orijinal yazımdaki bir hatanın ileri taşınmasıymış. Bu üçüncü örnek — Master Program dokümanının rakamsal iddialarına körlemesine güvenmemek gerektiğini bir kez daha doğruluyor.
