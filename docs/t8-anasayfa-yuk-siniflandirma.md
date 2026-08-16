# T8-anasayfa-yük — Ana Sayfa 11 Paralel İstek Tetikleyici Sınıflandırması (KOD DEĞİŞMEDİ)

**Tarih:** 16.08.2026 · **Kapsam:** Master Program §8 FAZ8 "Tipografi/performans" backlog'undaki "Ana sayfa 11 paralel istek → grafik endpoint'leri tembel yükleme" kalemi — yalnız sınıflandırma, hangi fetch çağrısının hangi koşulda ateşlendiğinin kanıtlı tespiti. S1/S7/T3.4/T5.2/T5.4/T8-tipografi/T8-başlık/T1.5 deseniyle aynı: kod-değiştirmeyen envanter, CPO onayı öncesi migrasyon yok. Bu turda hiçbir CSS/HTML/JS değişmedi.

## Kaynak veri

```
templates/index.html — 5564 satır, tek <script> bloğu (satır 2639–5479), defer/async YOK,
DOMContentLoaded hiç geçmiyor (grep boş) → script HTML parse edilirken senkron çalışır.

grep -n "fetch('/api" templates/index.html → sayfa-yüklemede-adaylık taşıyan 11 endpoint:
  /api/macro, /api/chart, /api/chart/XU100, /api/data, /api/market-summary,
  /api/user-alerts, /api/market-news, /api/bilanco-mini, /api/backtest,
  /api/macro-summary, /api/macro-news
```

Workflow: 4 paralel izleme ajanı (her biri 2-3 endpoint'e odaklandı, salt-okur SSH grep+sed, birbirini görmedi) → 1 sentez ajanı (11 satırlık birleşik tabloyu kurdu + 3 soruyu yanıtladı) → 1 bağımsız doğrulama ajanı (sentezi görmeden kendi grep/sed turunu sıfırdan yaptı, kritik "YÜKLEMEDE-HEMEN" satırların çoğunu elle yeniden okudu). Doğrulama **ONAY** verdi — sınıflandırmaların hiçbiri yanlış çıkmadı, yalnız 2 kozmetik satır-numarası kayması (5464→5463, `loadGundem` üst-seviye çağrısı) ve sentezin kendi metninde bir iç tutarsızlık ("9 başlangıç noktası" dedikten sonra 8 öğe sayması — doğrusu 8 çağrı ifadesi → 9 endpoint) buldu; bu düzeltmeler aşağıdaki tabloya işlenmiştir.

## Sonuç tablosu

| # | Endpoint | Sarmalayan fonksiyon | Tetikleyici sınıfı | Grafik-ilişkili mi | Kanıt satırı |
|---|---|---|---|---|---|
| 1 | `/api/macro` | `loadMacro()` (IIFE gövdesinde) | **YÜKLEMEDE-HEMEN** + periyodik `setInterval` 180000ms | H | 2703 (çağrı), 2704 (`setInterval`) |
| 2 | `/api/chart` | `fetchChart()` | **YÜKLEMEDE-HEMEN** + retry `setTimeout` 4000/8000/5000ms | **E** | 3101 |
| 3 | `/api/chart/XU100` | `fetchChart100()` | **YÜKLEMEDE-HEMEN** + koşullu 2. çağrı (`sym==='XU100' && !_chartData.xu100`, tab-switch) + retry 5000/8000/6000ms | **E** | 3102 (çağrı), 3033 (koşullu 2. çağrı) |
| 4 | `/api/data` | `fetchData()` | **YÜKLEMEDE-HEMEN** + poll `setTimeout` 60000ms + retry 3000/5000ms + etkileşimde (manuel refresh, pull-to-refresh) | H | 4384 |
| 5 | `/api/market-summary` | `renderMarketSummary()` | **YÜKLEMEDE-HEMEN ama ZİNCİRLEME** (`/api/data`'nın `await` yanıtını bekliyor, paralel değil) + koşullu `stocks.length>0` | H | 3407 (çağrı) → 3440 (fetch), 3430 (koşul) |
| 6 | `/api/user-alerts` | `_loadUserAlerts()` | **KOŞULLU** — yalnız `_isLoggedIn()` (`bp_sub` cookie) true ise | H | 3877 (çağrı), 3747-3749 (koşul tanımı) |
| 7 | `/api/market-news` | `loadGundem(false)` | **YÜKLEMEDE-HEMEN** (asıl tetikleyici) + koşullu 2. çağrı (tab≠makro && `!_hisseLoaded`) + retry `setTimeout` 30000ms | H | 5463 (çağrı — doğrulamada düzeltildi), 5428-5429 (koşullu), 5032 (retry) |
| 8 | `/api/bilanco-mini` | `loadGundem(false)` (aynı çağrı, `Promise.all`) | **YÜKLEMEDE-HEMEN** yalnız ilk çağrıda (`newsOnly===false`); retry döngüsünde (`newsOnly=true`) atlanıyor | H | 5463→4984 (doğrulamada düzeltildi), 4982-4983 (koşul) |
| 9 | `/api/backtest` | `loadBtBadge` (named IIFE) | **YÜKLEMEDE-HEMEN**, koşulsuz | H | 5043-5045 |
| 10 | `/api/macro-summary` | anonim IIFE | **YÜKLEMEDE-HEMEN**, koşulsuz | H | 5374, 5377 |
| 11 | `/api/macro-news` | `loadMacroNews()` | **YÜKLEMEDE-HEMEN** (asıl tetikleyici) + koşullu 2. çağrı (`_macroLoaded` bayrağı, tab-click — ilk yüklemeden sonra pratikte no-op) | H | 5462 (çağrı), 5420-5421 (koşullu 2. çağrı) |

## Soru 1 — Kaçı gerçekten "yüklemede-hemen"?

**10/11** çağrı, kullanıcı hiçbir şey yapmadan sayfa parse edilir edilmez otomatik olarak ateşleniyor. **1/11** (`/api/user-alerts`) gerçekten koşullu — yalnız login (`bp_sub` cookie) kullanıcılarında oluşuyor, login olmayan ziyaretçide (organik trafiğin büyük kısmı) hiç fetch edilmiyor.

**Ama "11 paralel istek" ifadesi teknik olarak abartılı — paralellik değil, çoğunlukla eşzamanlı-ama-bağımsız başlatma:**
- `/api/market-summary` gerçekte paralel değil, **zincirleme** — `/api/data`'nın `await` yanıtı dönmeden tetiklenmiyor.
- Gerçek bağımsız üst-seviye çağrı ifadesi sayısı **8**'dir (`loadMacro`, `fetchChart`, `fetchChart100`, `fetchData`, `loadBtBadge` IIFE, macro-summary IIFE, `loadMacroNews`, `loadGundem(false)`); bunlardan biri (`loadGundem`) kendi içinde `Promise.all` ile 2 endpoint'i (market-news+bilanco-mini) birlikte tetiklediği için toplam **9 endpoint** anlık/bağımsız başlıyor, 10. (`market-summary`) zincirleme, 11. (`user-alerts`) koşullu.
- Çoğu ayrıca kendi poll/retry katmanını taşıyor (`/api/macro` 180sn periyodik, `/api/data` 60sn poll) — yani "11 istek bir kere" değil, sayfa açık kaldıkça tekrarlayan bir istek akışı.

**Sonuç:** Master Program'ın iddiası "kaç tanesi otomatik/koşulsuz ateşleniyor" sorusuna göre büyük ölçüde doğru (10/11 kullanıcı-eylemsiz tetikleniyor), ama "paralel" kelimesi teknik olarak yanlış (1 zincirleme, 1 koşullu).

## Soru 2 — Grafik-ilişkili adaylar viewport lazy-load için uygun mu?

Grafikle (lightweight-charts/OHLC) ilişkili yalnız **2 endpoint**: `/api/chart`, `/api/chart/XU100`. **İkisi de tembel-yükleme önerisine tam uygun aday** — sayfa yüklenir yüklenmez, accordion kapalı olsa/kullanıcı grafiği hiç görmese bile koşulsuz çekiliyor (satır 3101, 3102). Buna karşılık ağır render kütüphanesi (`lightweight-charts.min.js`, 160KB) zaten `_loadChartLib()` ile accordion açılana/masaüstünde ilk grafik çizilene kadar lazy-load ediliyor (satır 2711-2723 civarı) — yani **kütüphane zaten tembel, veri fetch'i değil**. Bu, önerinin hedeflemesi gereken tam boşluk: kod hazır, yalnız 2 `fetch()` çağrısının aynı `_accOpen`/viewport koşuluna bağlanması gerekiyor.

## Açık/belirsiz kalan nokta

`/api/chart/XU100`'ün satır 3033'teki ikinci (koşullu, tab-switch) çağrı noktasını saran dış fonksiyonun tam adı doğrulanmadı (yalnız if/else gövdesi görüldü, ~3015-3040 aralığının tam okunması gerekir) — sınıflandırma sonucunu etkilemiyor (çağrı zaten "koşullu/etkileşimde" olarak doğru sınıflandırıldı), yalnız migrasyon turu için tam fonksiyon imzası gerekecek.

## Migrasyon önerisi (kod değişmedi, karar kuyruğuna eklenmesi önerilir)

`fetchChart()`/`fetchChart100()`'ün ilk çağrısını (satır 3101-3102) `_accOpen` durumuna veya bir `IntersectionObserver`'a bağlamak — düşük riskli, tek dosya (index.html), görsel/marka kararı gerektirmiyor (davranış değişikliği: accordion kapalıyken sparkline/kart-fiyatı ilk render'da boş/skeleton kalır, açılınca dolar). Diğer 9 endpoint (macro, data, market-summary, user-alerts, market-news, bilanco-mini, backtest, macro-summary, macro-news) lazy-load hedefi DEĞİL — hepsi sayfanın ilk görünür içeriği (fiyat şeridi, tablo, özet, alert, haber, rozet) için gerekli, viewport'a girmeden önce zaten görünür alanda.

Migrasyon kararının kendisi (accordion-state'e bağlama davranış değişikliği içerdiği için) S1/S7/T3.4/T5.2/T5.4/T8-tipografi/T8-başlık/T1.5 ile aynı karar kuyruğuna eklenmesi öneriliyor — düşük risk sınıfında (görsel/marka etkisi yok, yalnız zamanlama), CPO uygun görürse hızlı-onay adayı olabilir.
