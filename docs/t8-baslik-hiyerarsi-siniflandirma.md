# T8-başlık genişletme — 10 şablon başlık hiyerarşisi sınıflandırması

**Durum: SINIFLANDIRMA TAMAM, KOD DEĞİŞMEDİ.** S1/S7/T3.4/T5.2/T5.4/T8-tipografi ile aynı desen: kod-değiştirmeyen envanter, migrasyon kararı CPO/Ozan karar kuyruğuna eklendi.

**Kapsam:** `index.html`'de daha önce doğrudan uygulanan T8-başlık düzeltmesinin (0→9 h2-h6, ayrı onay gerektirmeden yapılmış) aynı desenini, hâlâ 0 h2-h6 taşıyan 10 içerik şablonuna genişletme denemesi: `bilanco_takvimi`, `blog`, `blog_article`, `gundem`, `kategori`, `ozet`, `portfolio`, `profil`, `sektor_harita`, `sinyal_performans`.

**Yöntem:** Workflow ile 5 paralel bulucu ajan (2 şablon/ajan, salt-okur SSH grep+read+curl, birbirini görmedi) → 1 sentez ajanı → 1 bağımsız doğrulama ajanı (sentezi görmeden 6 dosyada 6 SAFE iddiasını + 3 h1-anomali vakasını sıfırdan yeniden türetti). Doğrulama **DÜZELTME_GEREKLİ** verdi — bulgular aşağıda düzeltilmiş haliyle.

## Önemli metodolojik not — index.html emsali kısmen yanıltıcı

index.html'deki "aynı class'ı koru, div→h2 yap, görsel fark sıfır" varsayımı **yalnızca sayfanın kendi `* { margin:0; padding:0; }` resetiyle margin'i tamamen kontrol ettiği durumlarda** geçerli — font-size/font-weight zaten hemen her adayda class üzerinden zaten kontrollüydü, asıl risk ekseni margin. Bu resete sahip olmayan/eksik olan dosyalarda class'ı koru varsayımı **görsel regresyon riski taşır** (UA varsayılan h2/h3 margin'i sızar).

## 1. Yönetici özeti (doğrulama sonrası düzeltilmiş)

| Metrik | Sayı |
|---|---|
| h1 anomalisi taşıyan dosya | 5/10 — bilanco_takvimi, gundem, profil, sektor_harita, sinyal_performans |
| Güvenli (CSS-doğrulanmış no-op) div→h* adayı | **21** kod noktası, 7 dosyada (bilanco_takvimi 1, blog 1, gundem 6, kategori 2, ozet 7, portfolio 1, sinyal_performans 3) |
| Riskli/belirsiz aday (önce CSS düzeltmesi veya semantik karar gerekli) | **12** CSS-risk noktası + birkaç semantik-dışlama notu |
| Sıfır güvenli adaya sahip dosya | blog_article, profil, sektor_harita |
| Sınıflandırma turunda bulunan, iddiadan bağımsız 2 gerçek bug | bilanco_takvimi.html + gundem.html'de canlı çift `<h1>`; sinyal_performans.html'de erişilebilir h1 SIFIR (0 h2-h6'dan daha kötü bir durum) |

## 2. Dosya bazlı özet tablosu (doğrulama sonrası)

| Dosya | h1 (render/erişilebilir) | h2-h6 | Güvenli aday | Riskli/belirsiz aday |
|---|---|---|---|---|
| bilanco_takvimi.html | **2** (bug — çift) | 0 | 1 (`.period-label`, JS-injected uyarısı var) | 0 |
| blog.html | 1 | 0 | 1 (`.bc-title`) | 0 |
| blog_article.html | 1 (meşru) | 0 | 0 | 4 nokta / 3 class |
| gundem.html | **1 render + 1 CSS-bastırılmış** (bug) | 0 | **6** (`.section-title`, doğrulama düzeltmesiyle riskiden güvenliye taşındı — bkz §3 doğrulama notu) | 0 |
| kategori.html | 1 | 0 | 2 | 1 (semantik karar) |
| ozet.html | 1 | 0 | 7 | 0 |
| portfolio.html | 1 | 0 | 1 | 1 |
| profil.html | **2** (meşru — birbirini dışlayan Jinja dalları) | 0 | 0 | 5 nokta (1 paylaşımlı class — `<label>` elementleri, ayrı risk sınıfı bkz §4) |
| sektor_harita.html | **2** (bir rapora göre meşru/kasıtlı — bkz §6 çözülmemiş çelişki) | 0 | 0 | 0 önerilen (2 class kapsam-dışı) |
| sinyal_performans.html | **0 erişilebilir** (bug/boşluk) | 0 | 3 (`.sec-head`) | 1 (düşük güven, önerilmedi) |
| **Toplam** | | | **21** | **12 CSS-risk + kapsam-dışı notlar** |

## 3. Güvenli adaylar — önerilen minimal düzenlemeler (CSS-doğrulanmış no-op, bağımsız doğrulamadan geçti)

### bilanco_takvimi.html
- Satır 284: `<div class="period-label">${period.label}</div>` → `<h2 class="period-label">${period.label}</h2>` (veya h3 — aradaki bölüm sarmalayıcı yok, ikisi de savunulabilir).
  - `.period-label` font-size/weight/color açık; dosyanın kendi `* {margin:0}` (satır 24) margin'i kapsıyor.
  - **Bu adaya özgü tek uyarı:** bu markup Jinja değil, `<script>` içindeki `.map(...)` → `innerHTML` ile client-side üretiliyor — başlık ilk HTML yanıtında YOK, yalnız JS çalıştıktan sonra DOM'a giriyor. JS öncesi HTML okuyan araçlar için farklı bir durum.

### blog.html
- Satır 107 (`{% for a in articles %}` döngüsü içinde, satır 102-111): `<div class="bc-title">{{ a.title }}</div>` → `<h2 class="bc-title">{{ a.title }}</h2>`.
  - font-size/weight/color/line-height açık; margin-bottom açık, margin-top dosyanın `* {margin:0}` resetinden (satır 21) geliyor. Sunucu-taraflı Jinja, JS-injection uyarısı yok.

### gundem.html — **doğrulama düzeltmesi: RİSKLİ'den GÜVENLİ'ye taşındı**
Sentez raporu bu 6 noktayı "margin hiç set edilmemiş, riskli" diye sınıflandırmıştı — bağımsız doğrulama, dosyanın KENDİ metodolojisini (page-wide `* {margin:0}` reset var mı) yanlış uyguladığını buldu: `gundem.html:24`'te tam olarak aynı `* { margin:0; padding:0; box-sizing:border-box; }` reseti var, sentez raporu bunu atlamış. font-size/weight de class üzerinden zaten açık. Doğru satır numaraları da düzeltildi (sentez ilk taslakta birer kaymıştı):
- Satır 245: "Bugün Sinyal Değişenler" → `<h2 class="section-title">...</h2>`
- Satır 260: "En Güçlü Trendler" → `<h2 class="section-title">...</h2>`
- Satır 276: "Bilanço Takvimi" → `<h2 class="section-title">...</h2>`
- Satır 288: "Ekonomik Takvim" → `<h2 class="section-title">...</h2>`
- Satır 303: "Makro Haberler" → `<h2 class="section-title">...</h2>`
- Satır 319: "Piyasa Haberleri" → `<h2 class="section-title">...</h2>`

Hepsi paralel kardeş (flat sibling), hepsi h2.

### kategori.html
- Satır 153: `.cat-hero-title` → h2
- Satır 184: `.section-title` ("ABD Hisseleri — Hızlı Erişim") → h2
  - İkisi de dosyanın `* {margin:0}` (satır 21) + class'ın kendi font-size/weight/margin-bottom'u ile tam kapsanıyor.

### ozet.html
7× `.section-title` (satır 444/461/482/509/529/554/579), tek paylaşımlı kural (satır 114-122: font-size/weight/font-family açık, margin-bottom açık + dosyanın `* {margin:0}` resetiyle tam kapsama) — hepsi h2.

### portfolio.html
- Satır 241: inline-style "☁ Cloud Sync" div → h2 (aynı inline style korunarak). Modal dialog başlığı (`role="dialog"` içinde).

### sinyal_performans.html
3× `.sec-head` (satır 179, 219, 279) — CSS'de `margin:28px 0 14px` açık, dosyanın `* {margin:0}` resetiyle çifte kapsanmış — hepsi h2.
- **Yapısal uyarı:** bu sayfanın şu an erişilebilir h1'i YOK (§5) — bu 3 h2'yi eklemek h1 atlanmış bir hiyerarşi (h2'den başlayan outline) üretir, ayrı bir düzeltme gerekiyor.
- Satır 219-223'teki başlık içinde tıklanabilir bir `<button>` var (HTML içerik modeli açısından geçerli ama ekran-okuyucu başlık-gezinme davranışı için alışılmadık) — ikinci bir bakış önerilir, engelleyici değil.

## 4. Riskli/belirsiz adaylar — mekanik düzeltme ÖNERİLMEDİ

### CSS kapsama boşluğu (margin ve/veya font-size tam override edilmemiş — gerçek görsel regresyon riski)

| Dosya | Class/Satır | Eksik kapsama | Gereken ön-düzeltme |
|---|---|---|---|
| blog_article.html | `.faq-section-title` (273) | margin-top set değil | Satır 162'deki kurala `margin-top:0` ekle |
| blog_article.html | `.related-title` (344, 360) | margin-top set değil | Satır 139'daki kurala `margin-top:0` ekle |
| blog_article.html | `.rel-title` (365, kart-içi döngü) | Margin hiç yok + semantik olarak sınırda (sayfa bölüm başlığı değil, kart-içi teaser başlığı) | Satır 144'e `margin:0` + kapsam kararı |
| portfolio.html | `.ls-warning-title` (191) | **font-size hiç set edilmemiş**, ambient boyut miras alıyor — h2/h3'e çevirmek gerçek boyut regresyonu | Satır 113'e açık font-size + "bu bir başlık mı" ürün kararı |
| profil.html | `.q-label` ×5 (205/216/227/239/273) | margin-top set değil, VE dosyada page-wide `* {margin:0}` reseti YOK (yalnız `box-sizing` reset var) — UA varsayılan margin tam sızar | **Ayrıca ve daha temel bir sorun (doğrulama turunda bulundu): bunlar `<div>`/`<span>` değil, gerçek `<label>` elementleri** — h2/h3'e çevirmek form kontrolleriyle native label ilişkisini/semantiğini kırar. Margin düzeltmesi yetmez, bu class'lar heading'e dönüştürülmemeli. |

### Semantik/kapsam dışlamaları (CSS-güvenlik sorunu değil, tasarım/IA kararı)

| Dosya | Eleman | Neden önerilmedi |
|---|---|---|
| kategori.html | `.ac-name` (165, `#assetGrid` içinde tekrarlı) | Küçük (~2-4 öğe) grid'de tekrarlı isim — CSS-güvenli ama doküman outline'ına girip girmeyeceği belirsiz, öğe sayısı şablondan doğrulanamıyor (route'tan geliyor) |
| sektor_harita.html | `.sec-name` (493), `.sec-col-name` (714) | JS-templated, sektör kartı/karşılaştır kolonu başına N kez tekrarlı — hepsini çevirmek outline'ı boğar, sayfa-yapısı kararı gerekir. **Bu dosya için hiç aday önerilmedi.** |
| ozet.html | `.bp-nav-cat-label` ×3, `.sc-ticker`/`.sc-name` (kart-başına), footer yakını inline CTA metni | Nav dropdown grup etiketleri (farklı a11y deseni), büyük tekrarlı kart etiketleri, class'sız promosyon metni |
| portfolio.html | `.sum-lbl`, `.add-lbl` | Kart/form etiketleri, bölüm başlığı değil |
| sinyal_performans.html | `#computingTitle` (263, `{% else %}` dalı) | Durum mesajı gibi okunuyor (JS `textContent` ile değişiyor), kapsama-dahil-etme kararı |

## 5. H1 anomali vakaları — öneri ve minimal düzeltme

| Dosya | Anomali | Mekanizma | Öneri | Önerilen minimal düzeltme |
|---|---|---|---|---|
| **bilanco_takvimi.html** | 2 render edilen h1 | `{% with hdr_title=... %}{% include '_header.html' %}{% endwith %}` (satır 176) `hdr_title_tag` geçmiyor, varsayılan `'h1'`; sayfanın kendi sr-only h1'i de var (satır 177). Header'ın h1'i critical CSS ile `display:none` — şu an AT'ye zararsız ama ham HTML'de 2 `<h1>` var. | Muhtemel gözden kaçmış düzeltme — **ama bkz §6 çözülmemiş çelişki**, emsal olarak gösterilen `abd_tarama.html` artık repo'da yok (bağımsız doğrulamayla teyit edildi) | Satır 176'daki `{% with %}` çağrısına `hdr_title_tag='div'` ekle |
| **gundem.html** | 1 gerçek sr-only h1 (satır 208) + `_header.html`'den 1 CSS-bastırılmış h1 (satır 207, `hdr_title_tag` geçilmiyor) | bilanco_takvimi ile birebir aynı mekanizma | Muhtemel gözden kaçmış düzeltme — **aynı §6 çelişkisi geçerli** | Satır 207'ye `hdr_title_tag='div'` ekle; §3'teki 6× `.section-title`→h2 işiyle aynı turda yapılması mantıklı (o zaman h1→h2 outline'ı gerçekten kullanılan bir şey olur) |
| **profil.html** | 2 h1 (193, 298) | Birbirini dışlayan Jinja dalları (`{% if email %}...{% else %}...{% endif %}`) — istekte yalnız biri render edilir | **Meşru — bug değil** | Gerekmiyor |
| **sektor_harita.html** | 2 h1 (298 `h1.page-title` CSS-gizli, 352 sr-only erişilebilir) | 298, `<header>` içinde ve critical CSS'te `display:none`; 352, `</header>` kapandıktan sonra, bastırılmıyor | Bir rapora göre meşru/kasıtlı site kuralı — **§6'da bilanco_takvimi/gundem çelişkisi görün** | Önerilmedi; satır 298'in a11y/SEO için "ölü ağırlık" olduğu not edildi ama kaldırma güvenli doğrulanmadı (anti-CLS layout-reservation rolü olabilir) |
| **sinyal_performans.html** | **0 erişilebilir h1** | `_header.html` (satır 115) `<h1 class="page-title">` üretiyor ama critical CSS koşulsuz `display:none` yapıyor; sektor_harita'nın aksine telafi edici sr-only h1 YOK (sıfır literal `<h1` doğrulandı) | **Gerçek boşluk**, meşru sıfır-h1 durumu değil — mevcut "0 h2-h6" temelinden daha kötü, şu an hiçbir seviyede erişilebilir başlık ekran okuyucuya/crawler'a ulaşmıyor | Temiz bir minimal düzeltme sayfa-özel metin icat etmeden mümkün değil (içerik kararı) — ayrı bilet önerilir: site kuralına uygun (clip-rect deseni) küçük bir sr-only `<h1>` eklensin, en doğal şekilde §3'teki 3× `.sec-head`→h2 işiyle aynı turda |

## 6. Çözülmemiş çelişki (CPO/Ozan'a taşınıyor, burada çözülmedi)

Bağımsız doğrulama turu `abd_tarama.html`'in **artık repo'da olmadığını** teyit etti (`ls` → No such file or directory) — bu, bilanco_takvimi/gundem için "bu bug zaten başka bir yerde düzeltilmişti" emsalinin dayandığı dosyanın kendisinin silinmiş olduğu anlamına geliyor; emsal yalnızca `_header.html`'deki bir yorum satırında yaşıyor, canlı bir örnek değil.

Buna bağlı ikinci, çözülmemiş bir tutarsızlık var: bilanco_takvimi.html ve gundem.html'deki **aynı yapısal desen** (CSS-gizli `h1.page-title` + sayfanın kendi ayrı sr-only h1'i) bir raporda "gözden kaçmış bug, `hdr_title_tag='div'` ile düzeltilmeli" diye sınıflandırılırken, sektor_harita.html'deki **yapısal olarak aynı** desen başka bir raporda "meşru, kasıtlı site kuralı" diye sınıflandırıldı. İkisi aynı anda doğru olamaz — ya bilanco_takvimi/gundem değerlendirmesi fazla agresif ya da sektor_harita değerlendirmesi fazla toleranslı. Tek bir gözden geçirenin üçünü birlikte incelemesi gerekiyor (§6'daki silinmiş-dosya emsal sorunuyla birlikte) — bu doküman bunu çözmüyor, olduğu gibi bırakıyor.

## 7. Kapanış risk notu

§3'teki her "güvenli" sınıflandırma statik CSS kuralı okumasına ve global reset karşılaştırmasına dayanıyor — render edilmiş görsel diff değil. Bu ekibin S1/S7/T3.4/T5.2/T5.4/T8-tipografi disiplini gereği: **şimdi sınıflandır, migrasyon yalnızca bağımsız doğrulama turu (render öncesi/sonrası ekran görüntüsü veya computed-style diff, yalnız kaynak-seviyesi akıl yürütme değil) VE CPO/Ozan karar-kuyruğu onayından sonra** — özellikle bu iş 7+ şablona dokunuyor ve §5'teki 2 h1-düzeltmesi (`hdr_title_tag='div'`) paylaşılan `_header.html` tüketen deseni değiştiriyor. §6'daki çelişki, `hdr_title_tag` düzeltmesinin gerçekten "düzeltme" mi yoksa mevcut kasıtlı bir deseni mi bozacağı sorusunu netleştirmeden çözülmemeli.

**Migrasyon kararı** (21 güvenli div→h* dönüşümü + 2 `hdr_title_tag='div'` düzeltmesi + sinyal_performans'a yeni sr-only h1 + profil.html `.q-label` semantiği ayrı ele alınmalı çünkü `<label>`, heading'e çevrilmemeli) S1/S7/T3.4/T5.2/T5.4/T8-tipografi ile aynı karar kuyruğuna eklenmesi önerilir, kod değişmedi.
