# T8-tipografi (font-size) Sınıflandırması

**Tarih:** 16.08.2026 · **Kapsam:** BorsaPusula kod tabanındaki tüm `font-size` kullanımları — 32 `templates/*.html` dosyası (`_partial`ler dahil), `static/css/tokens.css`, `static/css/page-info-panel.css`, ve tüm `static/**/*.js` (üst dizin + `static/js/` alt dizini). Yalnız sınıflandırma + envanter. **Bu turda hiçbir CSS/HTML/JS değişmedi.** Format ve disiplin S1/S7/T5.2/T5.4 emsaliyle birebir aynı: 3 paralel ajan (templates dosyaları A/B olarak ikiye bölünmüş + static/css+js+tokens.css üçüncü ajan) → 1 sentez ajanı (bu doküman). **Bağımsız doğrulama turu bu belgede yapıldı** (SSH grep/read, ajanların akıl yürütmesi görülmeden) — kritik ≤11px kümesi teyit edildi, ayrıca ajan raporlarının kaçırdığı bir dizin ve bir dosya-içi kör nokta bu turda ortaya çıktı (aşağıda Bölüm 1 ve Bölüm 5).

---

## 1. Toplam sayı ve doğrulama notu

| Kaynak | Ajan-bildirimli toplam | Not |
|---|---|---|
| Rapor A (16 şablon) | 718 | 613 token + 105 ham |
| Rapor B (16 şablon) | 440 | 400 token + 40 ham |
| Static (tokens.css tanım aralığı + page-info-panel.css + üst-dizin JS) | 37 | 0 token + 37 ham (page-info-panel.css 9 + bp-search.js 24 + learning-mode.js 4) |
| **Ajan-bildirimli genel toplam** | **≈1195** | |

**Bağımsız doğrulama bulguları (sentez turunda tespit edildi):**

1. **`static/js/` alt dizini hiç taranmamış.** Static ajanının `ls static/*.js` komutu kabuk joker karakteri olduğu için alt dizinlere inmiyor — `static/js/focus-trap.js`, `static/js/page-info-panel.js`, `static/js/toast.js` envanter dışı kalmış. Bu 3 dosyada 4 ek `font-size` kullanımı var: `page-info-panel.js` (2, `0.875rem`/`0.75rem`, ikisi de >11px), `toast.js` (2, `13px` ve **`11px`** — ikincisi kritik kümeye giriyor, bkz. Bölüm 3).
2. **`tokens.css`'in kendisi yalnız 190-255. satır aralığında (tipografi ölçeği tanımları) tarandı, dosyanın geri kalanı taranmadı.** Satır 485'te bağımsız bir ham `font-size: 9px` kuralı var (`nav/footer "kısmi" rozeti` — `/kripto`, `/emtialar`, `/abd` linkleri için `::after` içerik rozeti). `tokens.css` dosyanın kendi yorumuna göre ("tokens.css tüm sayfalarda yükleniyor") **her sayfada** yüklendiği için bu tek satır aslında en geniş kapsamlı ham kullanımlardan biri — ama static ajan raporunda hiç görünmüyor.
3. **Rapor A'nın 3 dosya bazında (blog_article.html, hisse.html, index.html) bildirdiği token+ham toplamları bağımsız `font-size\s*:\s*[^;]+;` taramasıyla tam örtüşmüyor** (blog_article 44→43, hisse.html 217→207, index.html 252→241; toplam fark −22). Rapor B'nin 16 dosyalık tüm tablosu ise satır satır **birebir doğrulandı** (sıfır sapma). Fark, muhtemelen alt-regex'lerin (token deseni + ham-px deseni) örtüşmeyen bir kenar durumundan kaynaklanıyor (ör. `var(--bp-text-md, 14px)` gibi fallback'li var() kullanımları ya da JS template-literal içinde noktalı virgülsüz biten değerler); kesin kök neden bu turda belirlenemedi ve **doğrulanmamış** olarak işaretleniyor — karar gerekçesi olarak kullanılmamalı. Kritik olan ≤11px alt kümesi bu belirsizlikten etkilenmiyor (Bölüm 3'te iki farklı yöntemle çapraz doğrulandı).
4. **tokens.css tipografi ölçeği "18 token" değil, "20 token"** — static rapor bunu 18 olarak bildirmiş ama `--bp-text-*: Npx` deseniyle doğrudan grep edildiğinde 20 farklı token satırı var (bkz. Bölüm 4). T5.2'nin "17 vs 20 aritmetik hata" emsaliyle aynı sınıf bir sayım hatası.

**Düzeltilmiş genel toplam (yaklaşık, çünkü madde 3'teki fark çözülmedi):** 1195 + 4 (madde 1) + 1 (madde 2) ≈ **1200**. Bu sayı "yaklaşık" olarak işaretli — kesin karar gerektiren tek sayı **Bölüm 3'teki ≤11px kümesi (98)**, o iki bağımsız yöntemle (`;`-sınırlı ve birim-çapa'lı regex) çapraz doğrulandı.

---

## 2. Dosya bazında token/ham dağılımı (ajan raporlarından, doğrulama notlarıyla)

### 2a. Templates grup A (16 dosya)

| Dosya | Token | Ham | Toplam (ajan) | Bağımsız doğrulama |
|---|---|---|---|---|
| 404.html | 9 | 0 | 9 | ✓ |
| bilanco_takvimi.html | 25 | 3 | 28 | ✓ |
| blog_article.html | 40 | 4 | 44 | ⚠ 43 çıktı (Bölüm 1, madde 3) |
| blog.html | 18 | 0 | 18 | ✓ |
| gizlilik.html | 8 | 0 | 8 | ✓ |
| gundem.html | 31 | 15 | 46 | ✓ |
| hakkinda.html | 29 | 0 | 29 | ✓ |
| _header.html | 0 | 3 | 3 | ✓ (2 SVG `font-size="…"` özniteliği bilinçli hariç tutulmuş, doğru) |
| _head.html | 1 | 0 | 1 | ✓ |
| hisse.html | 175 | 42 | 217 | ⚠ 207 çıktı |
| hisseler.html | 40 | 0 | 40 | ✓ |
| iletisim.html | 22 | 1 | 23 | ✓ |
| index.html | 215 | 37 | 252 | ⚠ 241 çıktı |
| _analytics.html / _base.html / _header_asset_price.html | 0 | 0 | 0 | ✓ (3 dosyada hiç font-size yok) |

### 2b. Templates grup B (16 dosya) — tamamı satır satır doğrulandı, sıfır sapma

| Dosya | Toplam | Token | Ham |
|---|---|---|---|
| karsilastir.html | 44 | 34 | 10 |
| kategori.html | 29 | 29 | 0 |
| metodoloji.html | 23 | 23 | 0 |
| _mobile_nav_partial.html | 7 | 7 | 0 |
| offline.html | 5 | 0 | 5 |
| ozet.html | 58 | 52 | 6 |
| portfolio.html | 44 | 43 | 1 |
| _premium_modal.html | 10 | 10 | 0 |
| profil.html | 14 | 12 | 2 |
| sektor_harita.html | 53 | 46 | 7 |
| sinyal_performans.html | 30 | 30 | 0 |
| _stale_banner.html | 1 | 1 | 0 |
| tarama.html | 58 | 51 | 7 |
| unsubscribe.html | 4 | 4 | 0 |
| varlik.html | 47 | 45 | 2 |
| yasal.html | 13 | 13 | 0 |

### 2c. Static (genişletilmiş — `static/js/` dahil)

| Dosya | Toplam | Token | Ham | Not |
|---|---|---|---|---|
| tokens.css | 20 tanım + 1 kullanım | 20 (tanım) | 1 (satır 485, kullanım) | Sentezde bulundu, ajan raporunda yok |
| page-info-panel.css | 9 | 0 | 9 (8 rem + 1 `inherit`) | Hiçbir template'te `<link>` ile bulunamadı — bkz. Açık Riskler |
| bp-search.js | 24 | 0 | 24 | |
| learning-mode.js | 4 | 0 | 4 | |
| page-info-panel.js | 2 | 0 | 2 | `static/js/`, sentezde bulundu |
| toast.js | 2 | 0 | 2 | `static/js/`, sentezde bulundu |

---

## 3. ≤11px ham (token'sız) kullanımlar — TAM liste, bağımsız doğrulanmış: 98 kullanım

**Yöntem:** iki bağımsız regex ile çapraz doğrulandı — (a) `;`-sınırlı `font-size\s*:\s*[^;]+;` ve (b) birim-çapalı `font-size\s*:\s*[0-9.]+px` (noktalı virgül şartı yok, JS'teki virgülle biten değerleri de yakalıyor). Templates alt kümesinde ikisi de **83** verdi (Rapor A'nın 62'si + Rapor B'nin 21'i = 83 ile birebir örtüşüyor). Static tarafında (b) yöntemi zorunlu, çünkü JS içindeki değerlerin çoğu `;` ile bitmiyor.

### Değer dağılımı (98 toplam)

| px değeri | adet | kaynak dağılımı |
|---|---|---|
| 8px | 1 | tarama.html:364 |
| 9px | 5 | gundem.html:541, index.html:2060, bp-search.js:54, bp-search.js:59, **tokens.css:485** |
| 10px | 24 | templates 21 + bp-search.js (32,116) + learning-mode.js:41 |
| 10.5px | 2 | bp-search.js:60, bp-search.js:104 |
| 11px | 66 | templates 59 + bp-search.js (58,82,108,111) + learning-mode.js (47,49) + **toast.js:48** |

**Düzeltme notu (bağımsız doğrulama turunda bulundu, `verification` sonucu):** İlk sentez taslağında `index.html:4026` (10px) Bölüm 3a listesinden atlanmıştı ve "11px (60)" başlığı kendi itemize listesiyle (59) tutarsızdı. Aşağıdaki liste ve tablo bu düzeltmeyi yansıtıyor; genel toplam (98) ve templates-only alt-toplam (83) bu düzeltmeden etkilenmiyor.

### 3a. Templates (83)

- **9px (2):** `gundem.html:541` (JS template-literal, kaynak rozeti) · `index.html:2060` (stat-label yanı ok ikonu)
- **10px (21):** `gundem.html:441,543` · `hisse.html:3161,3370,3739,3798,3836,3838` · `index.html:3603,3945,3946,4026,4090,4091,4097,4110,4124` · `karsilastir.html:435,443` · `sektor_harita.html:487` · `varlik.html:810`
- **11px (59):** `bilanco_takvimi.html:299` · `blog_article.html:401` · `gundem.html:443,444,466,471,472,514` · `_header.html:102,107,113` · `hisse.html:1253,1258,1264,2840,2852,2989,3020,3032,3137,3162,3360,3386,3614,3742,3744,4003` · `index.html:1975,1980,1986,2865,3943,3944,4083,4085,4086,4103,4136,4769,4770,4828,5011,5323` · `karsilastir.html:406,484` · `ozet.html:318,323,329` · `portfolio.html:399` · `sektor_harita.html:328,333,339,499,508` · `tarama.html:866,933,933,960,960` (933 ve 960 her biri aynı satırda 2 ayrı `font-size:11px` — masaüstü/mobil Premium+Plus rozet çifti)
- **8px (1):** `tarama.html:364` (`.fresh-dot` CSS kuralı — tüm envanterin en küçük mutlak değeri)

### 3b. Static (15, önceki ajan raporlarının kaçırdığı 2'si dahil)

- **9px (2):** `bp-search.js:54`, `bp-search.js:59`
- **10px (3):** `bp-search.js:32`, `bp-search.js:116`, `learning-mode.js:41`
- **10.5px (2):** `bp-search.js:60`, `bp-search.js:104`
- **11px (7):** `bp-search.js:58,82,108,111` · `learning-mode.js:47,49` · **`toast.js:48`** ← sentezde bulundu, ajan raporunda yok (bkz. Bölüm 1)
- **9px, sentezde bulundu (1):** **`tokens.css:485`** ← ajan raporunda yok, global kapsamlı (bkz. Bölüm 1 ve Açık Riskler)

### 84 ön-bulgusuyla karşılaştırma

DEV2'nin Pazar (16.08) ön-bulgusu **"84"** idi. Bu sentezde templates-only (static hariç) doğrulanan sayı **83** — fark yalnız **1**, pratikte örtüşüyor. En olası açıklama: ön-bulgu muhtemelen `static/` kapsamını içermiyordu (yalnız templates), ve 83 vs 84 farkı satır düzeyinde önemsiz bir metodoloji kayması (ör. tarama.html:933/960'daki iki-eşleşmeli satırların sayılma biçimi, ya da ön-bulgu ile bu tur arasında kod tabanında 1 satırlık bir değişiklik). **Static kapsamı dahil edildiğinde gerçek toplam 98'e çıkıyor** — 84 ön-bulgusunun static/JS'i (özellikle `bp-search.js`'in 12 satırını ve şimdi bulunan `toast.js`/`tokens.css` satırlarını) kapsamadığı sonucuna varılıyor. Bu bir tahmin, DEV2'nin orijinal ön-bulgusunun metodolojisi görülmeden kesinleştirilemez.

---

## 4. tokens.css tipografi ölçeği — 20 basamak (18 değil)

`--bp-text-*: Npx` deseniyle doğrudan grep edilen **20 token** (static raporun "18" iddiası hatalı, T5.2 emsaliyle aynı sınıf bir sayım hatası):

`2xs`(10) · `xs`(11) · `sm`(12) · `base`(13) · `md`(14) · `15`(15) · `lg`(16) · `17`(17) · `xl`(18) · `2xl`(20) · `22`(22) · `3xl`(24) · `26`(26) · `28`(28) · `32`(32) · `34`(34) · `36`(36) · `38`(38) · `40`(40) · `42`(42)

### Orijinal T8 hedefiyle karşılaştırma

Master Program'daki orijinal T8 hedefi: **"38 font-size değeri → 9 basamaklı ölçek; ≤11px olan → 12px tabanına çekilir."** Bu hedef, DEV2-078/079/080 (13-14.08.2026) turlarında fiilen **aşılmış ve genişletilmiş** durumda:

- Orijinal ölçüm 1249 kullanım / 28 ayrık değerden başlamış (38 değil — "38" muhtemelen ilk kaba tahmindi, gerçek dağılım çok daha büyük çıkmış).
- Üç turluk süreç, S1/S7'deki "aynı hiyerarşiyi bozma, değeri koru" ilkesini uygulamış: emsal (peer) kanıtı yeterli olan durumlarda yuvarlama yapılmış (ör. 17px close-ikon → xl/18), kanıt yetersiz kalan durumlarda **9 basamak yerine yeni ara-basamak token'ları açılmış** (15, 17, 22, 26, 28, 32, 34, 36, 38, 40, 42 — 11 ek basamak).
- DEV2-079'da bir **adversarial-review** turu, ilk yuvarlama kararını (page-title/h2 için 17→18) çürütüp gerçek şablon dağılımına göre düzeltmiş (page-title çoğunluk emsaline göre 2xl/20'ye, h2 gerçek emsallere göre xl/18'e çekilmiş) — kanıtsız yuvarlama yapılmamış.

**Değerlendirme:** 20 basamaklı ölçek, orijinal "9 basamak" hedefinin *ihlali* değil, o hedefin **daha sonraki, daha temkinli bir mühendislik kararıyla geride bırakılmış (superseded) hali**. "Kanıtsız yuvarlama yapma" ilkesi doğru bir disiplin, ama sonucu — orijinal 9-basamak hedefinin artık geçerli bir kabul ölçütü olmaktan çıkması — bu belgede açıkça not edilmeli: **orijinal T8 hedefi (9 basamak) bu tarihten sonra referans alınmamalı; güncel referans DEV2-078/079/080'in 20-basamaklı ölçeğidir.**

---

## 5. `--bp-text-xs` doğrulaması — hâlâ 11px, orijinal T8 kabul ölçütüyle doğrudan çelişiyor

```
static/css/tokens.css:226:  --bp-text-xs:   11px;
```

Doğrulandı: `--bp-text-xs` bugün de **11px**, 12px'e çekilmemiş. Ayrıca `--bp-text-2xs` **10px** olarak ayrı bir basamak — yani kanonik ölçeğin kendisi, orijinal ihlal eşiğinin (≤11px) **altında iki basamağı resmi/token'lı kullanım olarak barındırıyor**.

Bu, orijinal T8 kabul ölçütüyle ("≤11px olan → 12px tabanına çekilir") **doğrudan çelişiyor** — hedef "12px altına inme" iken, güncel kanonik ölçek bilinçli olarak 10px ve 11px basamaklarını korumuş (Bölüm 4'teki "kanıtsız yuvarlama yapma" ilkesinin bir sonucu: `xs`/`2xs`'i kullanan yerlerde 12px'e yuvarlamak için yeterli emsal kanıtı aranmamış/bulunamamış olabilir — bu doküman bunu doğrulamadı, yalnız çelişkinin varlığını tespit ediyor). Sonuç: **`--bp-text-xs`/`--bp-text-2xs` token'larının kendisi, 98 ham ≤11px kullanımından ayrı olarak, orijinal T8 hedefine göre "çözülmemiş" sayılmalı** — bunlar token'lı oldukları için Rapor A/B'nin "ham" sayımlarına hiç girmiyorlar, ama nihai görsel sonuç (11px/10px metin) hedefin istediği "12px taban" değil.

`--bp-text-xs`/`--bp-text-2xs` kullanan template satırı sayısı bu sentezin kapsamında ayrıca sayılmadı (yalnız token tanımı doğrulandı) — gerekirse ayrı bir tarama gerekir.

---

## 6. Envanter sonucu (özet, EYLEM İÇERMEZ)

- Kod tabanında toplam **≈1200** `font-size:` kullanımı var (templates + static/css + static/js, `static/js/` alt dizini dahil); bunun **≈1100'ü** (~%92) `var(--bp-text-*)` token'lı, **≈100'ü** ham değer.
- Ham değerlerin **98 tanesi** ≤11px — bunların 83'ü templates'te, 15'i static/css+js'te (bu 15'in 2'si — `toast.js:48` ve `tokens.css:485` — önceki 3 ajan raporunda da yoktu, sentez turunda bulundu).
- Kanonik tipografi ölçeği (`tokens.css`) **20 basamaklı** (`--bp-text-2xs` 10px'ten `--bp-text-42` 42px'e); orijinal Master Program T8 hedefindeki "9 basamak" artık güncel değil, DEV2-078/079/080 tarafından kanıt-temelli biçimde genişletilmiş.
- `--bp-text-xs` (11px) ve `--bp-text-2xs` (10px) hâlâ canlı token'lar — orijinal T8'in "≤11px'i 12px'e çek" hedefiyle çelişiyor, bu çelişki bu dokümanla ilk kez açıkça kayda geçiyor.
- En küçük mutlak değer **8px** (`tarama.html:364`, `.fresh-dot` CSS kuralı).
- Tekrarlayan/tek-kaynaklı desen: `.bp-nav-cat-label` (`font-size:11px`) 5 dosyada (`_header.html`, `hisse.html`, `index.html`, `ozet.html`, `sektor_harita.html`) birebir aynı 3 satırlık blok olarak kopyalanmış — 98'lik listenin **15 kalemi** (yaklaşık %15'i) tek bir bileşenin kopya-yapıştır tekrarından geliyor.

### UYGULAMA DEĞİL — yalnız migrasyon fizibilite notu

- 98 ham ≤11px kullanımının büyük bölümü (67'si) zaten mevcut `--bp-text-xs` (11px) veya `--bp-text-2xs` (10px) token'larına **mekanik olarak eşlenebilir** — yalnız `.bp-nav-cat-label` gibi 5-dosyalık kopya bloklar için tek kaynağa indirgeme (muhtemelen `_header.html`'e taşıma) ayrı bir yapısal karar gerektirir.
- `tokens.css:485` (9px, global "kısmi" rozeti) ve `tarama.html:364` (8px, `.fresh-dot`) WCAG asgari 12px önerisinin belirgin şekilde altında — bunlar semantik olarak "mikro-etiket/durum noktası" oldukları için mevcut token ölçeğinde (`2xs`=10px bile) karşılığı yok, yeni bir `--bp-text-3xs` basamağı ya da bilinçli "token'lanmayacak dekoratif eleman" istisnası gerektirir.
- Bu migrasyon kararı CPO onayı bekliyor; hiçbir satır bu sentez turunda değiştirilmedi.

---

## Açık Riskler

1. **8px/9px erişilebilirlik riski.** WCAG asgari gövde-metni önerisi genelde ≥12-14px'tir; envanterdeki 1×8px + 5×9px kullanım (özellikle `tokens.css:485`'in her sayfada yüklenen nav/footer rozeti) bu eşiğin belirgin altında. Bunlar dekoratif/durum rozetleri olduğu için WCAG 1.4.4 (yeniden boyutlandırılabilir metin) kapsamına girip girmediği ayrıca değerlendirilmeli.
2. **`page-info-panel.css` muhtemelen ölü/bağlantısız.** 32 template dosyasının hiçbirinde `page-info-panel.css`'e `<link>` ile referans bulunamadı (`grep -rln 'page-info-panel' templates/` boş döndü). Aynı isimli `static/js/page-info-panel.js` kendi `<style>` etiketini dinamik olarak enjekte ediyor — bu, `.css` dosyasının güncel akışta hiç kullanılmadığı, `.js`'in kendi stilini taşıdığı anlamına gelebilir. **Teyit edilmedi** (Flask şablon include zincirleri veya CDN/manifest üzerinden dolaylı bağlanma ihtimali dışlanmadı) — ayrı bir doğrulama gerekir.
3. **Rapor A'nın 3 dosyalık sayım farkı çözülmedi** (blog_article/hisse/index.html, Bölüm 1 madde 3) — bu sentez toplam sayıyı "yaklaşık 1200" olarak veriyor, tam kesinlik için tek bir regex yöntemiyle tüm kod tabanının yeniden taranması gerekir.
4. **`page-info-panel.css`'teki `rem` değerlerinin px karşılığı** kök `font-size` varsayımına (16px) dayanıyor; templates/static'te bunu geçersiz kılan bir `html{font-size}` kuralı bulunamadı, ama app.py veya tarayıcı-varsayılanı dışı bir kaynak olasılığı tam dışlanmadı.
5. **`app.py`'deki e-posta üretim fonksiyonları** (`_build_welcome_email` vb.) bu envanterin kapsamı dışında — DEV2-078 bunları e-posta istemcisi uyumluluğu gerekçesiyle bilinçli olarak hariç tutmuştu, bu sentez de aynı kapsam dışı bırakmayı sürdürüyor, teyit değil varsayım.
6. **`--bp-text-xs`/`--bp-text-2xs` kullanan satır sayısı sayılmadı** (Bölüm 5) — bu iki token'ın gerçek yayılımı bilinmeden "12px'e çekme" migrasyonunun gerçek etki alanı ölçülemez.

---

## Yöntem

3 paralel ajan (templates dosyaları A/B olarak bölünmüş iki ajan + static/css+js+tokens.css'e bakan üçüncü ajan, her biri yalnız kendi kapsamına baktı, birbirini görmedi) → 1 sentez ajanı (bu doküman, üç raporu birleştirdi; kendi SSH taramasıyla `static/js/` alt dizini ve `tokens.css`'in tanım-aralığı dışındaki satırları gibi iki kapsam boşluğunu ayrıca buldu) → 1 tamamen bağımsız 4. doğrulama ajanı (sentezi hiç görmeden kendi grep'lerini çalıştırıp aynı soruları cevapladı, sonra karşılaştırdı — S1/S7/T5.2/T5.4 emsaliyle aynı desen). Bu son doğrulama turu kritik ≤11px toplamını (98) ve tokens.css basamak sayısını (20) DOĞRULADI, ayrıca Bölüm 3'teki dağılım tablosunda küçük bir hata buldu (`index.html:4026` listeden eksikti, "11px (60)" başlığı kendi listesiyle tutarsızdı) — bu belge o düzeltmeyi (10px=24, 11px=66; templates 10px=21, 11px=59) içeriyor. Templates tarafındaki 3 dosyalık sayım farkı (Bölüm 1, madde 3) ise çözülemeden "doğrulanmamış" olarak işaretlendi (S1/S7/T5.4 emsalindeki disiplinle: doğrulanmamış sayı karar gerekçesi olamaz).
