# FAZ8 "Tipografi/performans" — `/api/data` (285KB) Alan Projeksiyonu + ETag/Cache-Control — Sınıflandırma Raporu

**Tarih:** 16.08.2026 · **Kod değişmedi** (salt-okur envanter) · S1/S7/T3.4/T5.2/T5.4/T8-tipografi/T8-başlık/T1.5/anasayfa-yük/api-macro deseni.

## Backlog cümlesi (Master Program §"Tipografi/performans")

> `/api/data` (285KB) alan projeksiyonu + ETag/Cache-Control; blog_article.html'in bu endpoint'i çekmesi kaldırılır

## Yöntem

Workflow ile 3 paralel salt-okur SSH ajanı (endpoint/`app.py`, tüketiciler/`templates/`, blog_article.html iddiası — birbirini görmedi) → 1 sentez ajanı → 1 tamamen bağımsız kör doğrulama ajanı (sentezi görmeden kendi SSH turunu sıfırdan yaptı). Ayrıca DEV2 üçüncü elle-kontrol olarak `app.py:4111-4204` route gövdesinin tamamını okudu.

## Nihai hükümler

| Backlog bileşeni | Hüküm | Kanıt |
|---|---|---|
| **"285KB" rakamı** | **DOĞRU** | Canlı ölçüm 282–283KB (public CF + origin, 3+ örnek); `app.py:4210` docstring'i "~280KB" diyor; commit mesajı `c667f72` "282KB" diyor. |
| **"blog_article.html gereksiz `/api/data` çekiyor"** | **YANLIŞ — zaten çözülmüş** | `templates/blog_article.html:385` yalnızca `/api/data-lite?tickers=...` çağırıyor (335 byte, 5 alan/ticker). Tam `/api/data` (283KB) hiç çekilmiyor. |
| **"ETag/Cache-Control eklensin"** | **YANLIŞ — zaten kodda** | `app.py:4192-4198`: MD5 ETag + `Cache-Control: no-cache` + `If-None-Match`→304. Aynı commit ile eklenmiş. |
| **"Alan projeksiyonu yapılmalı"** | **KISMEN-DOĞRU / kısmen zaten yapılmış** | `/api/data-lite` (`app.py:4207-4231`) zaten var ve blog_article.html onu kullanıyor. Genel/tek-ortak bir küçültme fikri yanlış varsayıma dayanıyor (bkz. aşağı) — ama `hisse.html` için hâlâ açık bir fırsat var. |

**Kök neden:** Backlog satırı, **11.08.2026 tarihli commit `c667f72`** ("feat(faz8-perf): /api/data ETag+Cache-Control + /api/data-lite alan projeksiyonu (blog_article.html 282KB->birkaç alan)") ile zaten yapılmış bir işi tarif ediyor. Bu, `/api/macro` (DEV2-137) ve S7 (DEV2-135) turlarındaki gibi "doküman driftı, kod driftı değil" sınıfının dördüncü örneği — ama bu seferki farklı: önceki üçü rakam/sayım hatasıydı, bu seferki **backlog satırının kendisi geçmişte kalmış** (iş zaten bitmiş, doküman güncellenmemiş).

## Detay — route yapısı

`app.py:4111` — `@app.route("/api/data")`, fonksiyon `api_data()`, gövde 4111–4204.

- Üst seviye 9 alan: `stocks, updated_at, loading, sectors, data_quality, stocks_age_s, refreshing, data_freshness, xu100_spark` (`app.py:4159-4169`)
- 215 hisse objesi (canlı ölçüm), her biri temel alanlar + route içinde enjekte edilen `anomaly` (F2, `app.py:4116-4118`), `sentiment` (F5, `app.py:4119-4126`), koşullu `adx`/`di_plus`/`di_minus` (BUG-C1 fix, `app.py:4128-4140`)
- **Not — 3 ajan raporu hisse-başı alan sayısında 43/44/45 arasında küçük farklarla ayrıştı.** Kök neden muhtemelen alan varlığının hisseye göre koşullu olması: `di_plus`/`di_minus` yalnız regex eşleşirse eklenir (`app.py:4136-4140`), `adx` yalnız top-level null ise parse edilir — yani farklı ajanlar farklı örnek hisseleri incelediği için farklı alan kümeleri gördü. Bu, backlog'un hiçbir hükmünü etkilemiyor (285KB/blog_article/ETag hükümlerinin hiçbiri bu ±2 alan farkına duyarlı değil), sadece not düşülüyor.

## Kardeş endpoint — `/api/data-lite` (zaten var)

`app.py:4207-4231`, fonksiyon `api_data_lite()`. Docstring (`4209-4210`): *"FAZ8 perf: alan projeksiyonu — blog_article.html gibi tüketiciler için tam /api/data (~280KB, tüm alanlar) yerine yalnız istenen ticker'ların kart-gösterimi için gereken 5 alanı döner."*

- Zorunlu `?tickers=` param — verilmezse boş `stocks:[]` döner (tam liste asla dönmez)
- 5 alan/hisse: `ticker, name, price, change_pct, signal`
- Aynı ETag/Cache-Control deseni burada da var
- Canlı test: `?tickers=AKBNK,GARAN,THYAO` → 335 byte (tam `/api/data`'nın ~845'te biri)

## `/api/data`'yı çağıran 4 şablon — alan kullanım oranı

| Şablon | Satır | Kullanım | Not |
|---|---|---|---|
| `portfolio.html` | :562 | ~5/52 alan (%10) — `ticker,price,signal,signal_price` | `/api/data-lite`'a (+`signal_price`) taşınabilir |
| `sektor_harita.html` | :537 | ~9/52 alan (%17) — `ticker,sector,signal,is_premium,rvol` | tüm 215 hisseyi gerektirir, `?tickers=` filtre modeli uymuyor — ayrı bir `?fields=` varyantı gerekir |
| `hisse.html` | :3490 | ~30/52 alan (%58) | tek ticker için `/api/data`'nın tamamını çekiyor — `/api/data-lite` genişletilse (signal_bars/signal_date eklenir) buraya da uyabilir, **hâlâ açık fırsat** |
| `index.html` | :3383 | ~32/52 alan (%62) | dokunma — zaten çoğu alanı kullanıyor |

Birleşim (union) analizi: 4 şablonun kullandığı hisse-alanları 43 alanın 37'sini (%86) kapsıyor — **tek/ortak bir küçültülmüş varyant net kazanç sağlamaz** (orijinalin neredeyse tamamını taşımak zorunda kalır). Gerçek fırsat yalnız **tüketici-bazlı**: portfolio.html + sektor_harita.html (dar kullanım) ve hisse.html (tek-ticker, tam payload).

**Templates kapsamında hiç kullanılmayan 5 alan (ayrı, doğrulanmamış bulgu):** `signal_strength, volume_tl_avg20, vol_confirmed, atr14, rr_ratio` + yorum-kalıntısı `is_new_signal` (`index.html:3203`, kod değil). Bunların `templates/` dışı tüketicisi (backtest scriptleri, `/api/hisse/<ticker>` vb.) taranmadı — kaldırma kararı verilmeden önce ayrıca doğrulanmalı.

## Yeni, doğrulanmamış gözlem — Cloudflare ETag stripping

Origin nginx ve backend (localhost:8003) `/api/data` yanıtında ETag header'ı gönderiyor (kod doğru çalışıyor), ama **public `https://borsapusula.com/api/data` yanıtında ETag header'ı görünmüyor** — yalnız `Cache-Control: no-cache` geçiyor. nginx config'inde `proxy_hide_header`/etag ile ilgili bir satır yok, dolayısıyla muhtemelen Cloudflare dinamik içerik davranışıyla stripliyor. Bu doğruysa, 304 conditional-request/bant genişliği kazanımı public trafikte fiilen çalışmıyor demektir. **Bu görev kapsamında doğrulanmadı** — ayrı bir CF ayarları incelemesi (Transform Rules / Cache Rules) gerekir, alan ayrımı (nginx/CF altyapısı) net değil, CPO'ya iletiliyor.

## Öneri (kod değişikliği yok — yalnızca öneri)

1. Backlog satırını **"stale/zaten-çözülmüş"** olarak kapat — referans: `c667f72`.
2. Yeni, dar kapsamlı düşük-riskli 2 kalem karar kuyruğuna eklenebilir:
   - `portfolio.html:562` → `/api/data-lite` (+`signal_price`) — tek dosya, görsel etki yok.
   - `hisse.html:3490` → `/api/data-lite` genişletilip (`signal_bars`,`signal_date` eklenir) veya ayrı bir tek-ticker "detay-lite" endpoint'i.
   - `sektor_harita.html:537` → ayrı bir `?fields=` varyantı gerektirir (mevcut `?tickers=` modeli 215 hisseyi tek tek istemeyi gerektirir, uymuyor) — daha büyük bir iş, ayrı değerlendirilmeli.
3. Cloudflare ETag-strip gözlemini ayrı bir görev olarak doğrulat (alan ayrımı belirsiz, CPO yönlendirsin).
4. 5 hiç-kullanılmayan alanın (`signal_strength` vb.) `templates/` dışı tüketicilerini tara, sonra kaldırma kararı ver.
