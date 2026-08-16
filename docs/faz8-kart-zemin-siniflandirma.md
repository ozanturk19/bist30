# FAZ8 "Kart/Zemin Ayrımı" Sınıflandırması — Sentez Raporu (Doğrulanmış)

**Kapsam:** 3 bağımsız alt-ajan raporu — (1) Liste/Tablo sayfaları, (2) Tekli varlık/detay sayfaları, (3) Diğer yüzeyler (portfolio/blog/statik/partial) — 22 şablon dosyası. **Ek olarak** bağımsız bir doğrulama turu (32 şablonun tamamı) bu sentezle karşılaştırılmış ve tüm satır/sayı iddiaları canlı repoda (`7b750ac`) yeniden hesaplanarak doğrulanmıştır (bkz. §9).

**HEAD notu:** Rapor 1 ve Rapor 2, `7b750ac` üzerinden ölçülmüş; Rapor 3 `5fc2867` üzerinden ölçülmüş. Bağımsız doğrulama turu da `7b750ac` kullanmış. Üç alt-ajan aynı HEAD'i kullanmamış — bu sentez bu farkı düzeltmiyor, sadece işaretliyor. Hepsi tokens.css referans değerlerinde (`--bp-bg #0e0e12`, `--bp-surface #141416`, `--bp-surface2 #1c1b1f`, `--bp-surface3 #201f21`) hemfikir; HEAD farkının sonucu etkilediğine dair kanıt yok — `7b750ac`'te bu değerler değişmemiş (doğrulandı).

**Yöntem:** WCAG relative-luminance formülü (sRGB→linear→L→kontrast oranı). Kod hiçbir raporda değiştirilmedi — tamamı salt-okur envanter.

---

## 1) Birleşik Sayfa/Kart Çiftleri Tablosu

### 1.1 Liste/Tablo sayfaları (Rapor 1 kapsamı — 31 birincil çift)

| Sayfa | Selector | Satır | Ham/Token | Kart Hex | Zemin Hex | Kontrast | Kova |
|---|---|---|---|---|---|---|---|
| index.html | `.search-modal` | 288 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.premium-modal` | 556 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.ms-stat` | 785 | **HAM** rgba composite | #16191f | #0e0e12 | 1.094:1 | (a)+(d) |
| index.html | `.ms-stat:hover` | 791 | **HAM** rgba composite | #1b2027 | #0e0e12 | 1.176:1 | (a)+(d) |
| index.html | `.gnm-card` | 836 | Token (non-kanonik ad `--bg2`) | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.gnm-card:hover` | 844 | **HAM** | #1c2128 | #0e0e12 | 1.190:1 | (a)+(d) |
| index.html | `.bilanco-mini-box` | 960 | Token (`--bg2`) | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.stat-card` | 992 | Token (rgba) | #131315 (composite) | #0e0e12 | 1.038:1 | (a) |
| index.html | `.bp-filter-panel` | 1056 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.adv-panel` | 1220 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.sig-tip` | 1308 | **HAM** | #1c2128 | #0e0e12 | 1.190:1 | (a)+(d) |
| index.html | `.endeks-card` | 1441 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.alert-modal` | 1634 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| index.html | `.alarm-panel` | 1648 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| tarama.html | `.mr-card` | 416 | Token→ham (yerel `--surface`) | #161b22 | #0e0e12 | 1.114:1 | (a) — **T1.6 örtüşmesi, tekrar sınıflandırılmadı** |
| gundem.html | `.stat-card` | 56 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| gundem.html | `.stock-card` | 90 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| gundem.html | `.stock-card:hover` | 101 | Token | #1c1b1f | #0e0e12 | 1.124:1 | (a) |
| gundem.html | `.empty-box` | 148 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| ozet.html | `.counter-card` | 89 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| ozet.html | `.section-box` | 104 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| ozet.html | `.stock-card` | 127 | Token | #1c1b1f | #0e0e12 | 1.124:1 | (a) |
| ozet.html | `.stock-card:hover` | 137 | Token | #201f21 | #0e0e12 | **1.173:1** | (a) — bu turda ölçülen en yüksek kanonik-token değeri |
| ozet.html | `.search-modal` | 218 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| kategori.html | `.asset-card` | 67 | Token→ham (yerel `--surface`) | #161b22 | #0e0e12 | 1.114:1 | (a) — **T1.6 örtüşmesi, tekrar sınıflandırılmadı** |
| sinyal_performans.html | `header` | 26 | Token (ama zemin off-palette) | #141416 | **#0b111f** | **1.024:1** | (a) — kanonik token bile başarısız |
| sinyal_performans.html | `.stat-card` | 35 | **HAM** | #161b22 | #0b111f | 1.090:1 | (a)+(d) |
| sinyal_performans.html | `.tbl-wrap` | 46 | **HAM** | #161b22 | #0b111f | 1.090:1 | (a)+(d) |
| sinyal_performans.html | `.computing` | 71 | **HAM** | #161b22 | #0b111f | 1.090:1 | (a)+(d) |
| sinyal_performans.html | `.info-box` | 76 | **HAM** | #161b22 | #0b111f | 1.090:1 | (a)+(d) |
| sinyal_performans.html | `.perf-filter-bar` (inline) | 283 | **HAM** | #161b22 | #0b111f | 1.090:1 | (a)+(d) |

### 1.2 Detay sayfaları (Rapor 2 kapsamı — 19 birincil çift; `sektor_karsilastir.html` repoda bulunamadı, kapsam dışı bırakıldı)

| Sayfa | Selector / Kart Ailesi | Satır | Ham/Token | Kart Hex | Zemin Hex | Kontrast | Kova |
|---|---|---|---|---|---|---|---|
| hisse.html | 23 kart bloğu (search-modal, sig-stat-card ailesi, KAP/MTF/haber/share/story panelleri) | çoklu | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| hisse.html | 16 kart bloğu (search-close, hist-table iç yüzeyler) | çoklu | Token | #1c1b1f | #0e0e12 | 1.124:1 | (a) |
| hisse.html | `.other-card:hover` | 832 | Token | #201f21 | #0e0e12 | 1.173:1 | (a) — yalnız hover |
| hisse.html | `.hib-toast` | 289 | **HAM** | #161618 | #0e0e12 | 1.066:1 | (a)+(d) |
| hisse.html | KAP/Yahoo link chip ×2 | 2185, 2282 | **HAM** (`--bp-surface2` kopyası) | #1c1b1f | #0e0e12 | 1.124:1 | (a)+(d) |
| hisse.html | e-posta input alanı | 2395 | **HAM** (`--bp-surface` kopyası) | #141416 | #0e0e12 | 1.047:1 | (a)+(d) |
| hisse.html | `.related-chip:hover` | 1068 | **HAM** | #21202b | #0e0e12 | 1.198:1 | (a) — yalnız hover, eşiğin tam altı |
| varlik.html | 🔴 9 kart selector (header, .signal-card, .chart-card, .ind-card, .history-card, .commentary-card, .other-card, .loading-card, .nav-dropdown-menu) — yerel `:root` GitHub-dark kalıntısı | 42,97,135,151,163,180,194,213,291 | **HAM** (token DEĞİL) | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| varlik.html | 6 kart selector (.back-btn, .hist-table th, .other-card:hover, header-nav a:hover, category chip) | 49,173,198,276,285,322 | **HAM** | #1c2128 | #0e0e12 | 1.190:1 | (a)+(d) |
| sektor_harita.html | `.sector-card` (×5) | 52 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| sektor_harita.html | `.cmp-stat-pill`, `.metric-card` (×11) | 232, 240 | Token | #1c1b1f | #0e0e12 | 1.124:1 | (a) |
| sektor_harita.html | `.cmp-skeleton` gradient base-stop | 207 | **HAM** (`--bp-surface2` kopyası) | #1c1b1f | #0e0e12 | 1.124:1 | (a)+(d) |
| sektor_harita.html | `.cmp-skeleton` gradient mid-stop (geçici shimmer karesi) | 207 | **HAM**, benzersiz | #232124 | #0e0e12 | 1.206:1 | (b) ZAYIF — kalıcı durum değil |
| karsilastir.html | header, `.search-bar`, `.compare-table th`, `.ac-dropdown` (×5) | 49,73,114,226,650 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| karsilastir.html | `.share-btn`, `.top-nav-links a` (×4) | 57,64,65,97 | Token | #1c1b1f | #0e0e12 | 1.124:1 | (a) |
| karsilastir.html | `.skeleton` gradient base-stop | 184 | **HAM** (varlik.html ile aynı GitHub-dark değer) | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| bilanco_takvimi.html | header, `.stock-card` (×4) | 32,71,91,128 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| bilanco_takvimi.html | filtre pilleri (×2) | 40,58 | Token | #1c1b1f | #0e0e12 | 1.124:1 | (a) |
| bilanco_takvimi.html | `.top-nav-links a:hover/.active` | 47,48 | **HAM** (varlik.html ile aynı değer) | #1c2128 | #0e0e12 | 1.190:1 | (a)+(d) |

### 1.3 Diğer yüzeyler (Rapor 3 kapsamı — 16 birincil çift; `gucu_yuksek.html` repoda yok, `offline.html`/`_base.html`/`_header.html` kart içermiyor)

| Sayfa | Selector | Satır | Ham/Token | Kart Hex | Zemin Hex | Kontrast | Kova |
|---|---|---|---|---|---|---|---|
| profil.html | `.form-card` | 50 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| 404.html | `.search-card` | 50 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| 404.html | `.popular-grid a` | 86 | Token | #141416 | #0e0e12 | 1.047:1 | (a) |
| portfolio.html | `.sum-card` | 39 | **HAM** (body de literal) | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| portfolio.html | `.add-bar` | 44 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| portfolio.html | `.pf-table` | 54 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| portfolio.html | `#cloudModalDialog` (modal, inline) | 239 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| blog.html | `.blog-search` | 40 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| blog.html | `.blog-card` | 51 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| blog_article.html | `.prose pre` | 127 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| blog_article.html | `.rel-card` | 141 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| blog_article.html | `.rel-stock-card` | 148 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| blog_article.html | `.rel-stock-skeleton` (iskelet) | 346 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| metodoloji.html | `.signal-box` | 84 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| metodoloji.html | `.criterion` | 100 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |
| metodoloji.html | `.formula-box` | 110 | **HAM** | #161b22 | #0e0e12 | 1.114:1 | (a)+(d) |

### 1.4 İkincil/kapsam-dışı çiftler (kaynak raporlarca bilinçli olarak ayrı tutulmuş, ana kovaya dahil edilmedi)

| Sayfa | Selector | Kontrast | Neden kapsam dışı |
|---|---|---|---|
| tarama.html / kategori.html | `.sig-AL/.sig-SAT/.sig-BEKLE` | ölçülmedi | rgba overlay, satır-üstü badge — kart-vs-sayfa değil |
| gundem.html | skeleton gradient | 1.114:1 | shimmer animasyonu, resting-state değil |
| sektor_harita.html | `.cmp-skeleton` mid-stop | 1.206:1 (b) | geçici animasyon karesi |
| sinyal_performans.html | `.sig-al/.sig-sat` | — | opak durum-rozeti, kart-vs-sayfa semantiği değil |
| karsilastir.html | `.ticker-input` | 1.000:1 | form input, kenarlıkla ayrışıyor, kart ailesi dışı |
| profil.html | `.opt` (form-card içi) | 1.074:1 | nested (kart-üstü-kart), birincil zemin çifti değil |
| _mobile_nav_partial.html | `.mbn-sheet-item`/`.mbn-push-row` | 1.074:1 | nested, sheet-içi |
| _mobile_nav_partial.html | `.mbn-sheet` | ölçülemedi | backdrop kompozit, sabit zemin hex'i yok |

---

## 2) Kova Toplamları

**Baş bulgu (tartışmasız, bağımsız turca da doğrulandı):** Üç raporun ölçtüğü **hiçbir kalıcı-durum kart/zemin çifti ≥1.5:1 hedefine ulaşmıyor. (c) YETERLİ kovası üç raporda da 0.**

| Kapsam Grubu | Kaynağın kendi N'i | (a) SIFIR-AYRIM | (b) ZAYIF | (c) YETERLİ | (d) HAM-HEX (alt-küme) |
|---|---|---|---|---|---|
| Liste/Tablo (Rapor 1) | 26 (rapor metni) / **31** (tablo satır sayımı) | %100 | 0 | 0 | 13/26 (rapor iddiası) |
| Detay sayfaları (Rapor 2) | "86 satır" (grep-satır bazlı) / **19** (selector-ailesi bazlı) | 86/86 kalıcı (%100) | 0 kalıcı, 2 geçici | 0 | 22 satır |
| Diğer yüzeyler (Rapor 3) | 15 (rapor metni) / **16** (tablo satır sayımı) | %100 | 0 | 0 | 12/15 (rapor iddiası) |

**Ölçüm notu (üç raporun da kendi iç tutarlılığında sapma var — düzeltilmedi, işaretlendi):**
- Rapor 1 metninde "26/26" deniyor ama kendi tablosundaki satırlar toplamı **31**'dir (14+1+4+5+1+6).
- Rapor 2, iki farklı birim kullanıyor: tablo satırları **selector-ailesi** bazında (19 satır), kova toplamı ise ham `grep -c` **kod-satırı** bazında (86) — bu iki sayı kasıtlı olarak farklı granülaritede, toplanabilir değil.
- Rapor 3 metninde "15/15" deniyor ama kendi listelediği bileşenler (portfolio 4 + blog 2 + blog_article 4 + metodoloji 3 + profil 1 + 404 2) toplamı **16**'dır.

Bu yüzden tek bir "toplam N" rakamı vermek yanlış kesinlik yaratır — üç kapsam da kendi içinde farklı sayım birimleri (selector-ailesi vs. ham kod-satırı) kullanıyor. **Sabit ve tartışmasız olan:** 66 birincil satırın (31+19+16, bu sentezde satır bazında yeniden sayıldı) **tamamı** ya (a) SIFIR-AYRIM ya da sınırdaki tek (b) örnek (sektor_harita `.cmp-skeleton` mid-stop, geçici); **sıfır** satır (c) YETERLİ'ye ulaşıyor.

En düşük ölçülen: index.html `.stat-card` → **1.038:1**.
En yüksek ölçülen (kalıcı durum, tüm kapsamlar): ozet.html `.stock-card:hover` (`--bp-surface3`) → **1.173:1** — hedefin (≥1.5:1) hâlâ çok altında.

---

## 3) Backlog İddiası Değerlendirmesi: "1.05:1 → ≥1.5:1"

**Başlangıç rakamı (1.05:1): DOĞRU — üç raporun bağımsız hesaplaması da, ayrıca bu sentezi karşılaştıran dördüncü bağımsız doğrulama turu da aynı sayıda birleşiyor.**
`--bp-bg` (#0e0e12) vs `--bp-surface` (#141416) token çiftinin WCAG kontrastı tam **1.047:1** — dört ayrı bağımsız hesaplama (üç alt-ajan + bu sentezin çapraz-doğrulama turu) bu rakamı bağımsız doğruladı. Bu, kapsanan dosyaların büyük çoğunluğunda en sık tekrarlanan kart deseni.

**Hedef rakamı (≥1.5:1): şu an %0 karşılanıyor, ve bu backlog satırının söylemediği kritik bir ek gerçek var.**
Ham-hex'i token'a çevirmek (S7/T1.6/T5.4 reçetesi) TEK BAŞINA hedefi karşılamıyor: en derin kanonik token bile (`--bp-surface3` #201f21) sayfa zeminine karşı sadece 1.173:1 veriyor. Yani mevcut `--bp-surface/2/3` token'larının **kendi luminance değerleri** ≥1.5:1'e asla ulaşamaz — bu, migrasyon (kod) sorunu değil, **token-tasarım** sorunu.

**Sonuç: BAYAT değil, DOĞRU — ama eksik bir hedef tanımı.** Backlog satırı doğru bir ölçüme dayanıyor (1.047:1 gerçek ve güncel) ve hedef doğru yönde (mevcut durum yetersiz), ancak "≥1.5:1" hedefine giden yolun basit bir ham-hex→token migrasyonu olmadığı, token paletinin kendisinin revize edilmesi gerektiği dört bağımsız hesaplamada da ortaya çıktı.

---

## 4) Kenarlık (Border) Örtüşme Notu

`--bp-bkl-bd` / `--border` (`#30363d` / yerel `#30363d` varyantları) kenarlık token'ı S1/S7'de zaten sınıflandırılmış (98 ham kullanım/14 şablon); bu rapor yalnız kart/zemin (arka plan) eksenini kapsıyor, kenarlık rakamlarına ("1.28:1 → ≥3:1") tekrar dokunulmadı veya yeniden sınıflandırılmadı — üç alt-rapor da bunu ayrı ayrı teyit etti (varlik.html satır 33, portfolio.html satır 39/44/54/239 gibi aynı satırlarda kenarlık ve zemin bir arada geçse de yalnız zemin tarafı ölçüldü).

---

## 5) En Kritik 5 Bulgu

1. **sinyal_performans.html tamamen izole ve önceki turlarda kaçmış:** Sayfa zemini `#0b111f` — `--bp-bg`'den (#0e0e12) farklı, hiçbir `:root` alias'ı yok, `head_theme_color` meta-tag'i bile bunu yansıtıyor (doğrulandı: satır 1 ve _head.html:8). Kanonik token kullanan `header` bile (1.024:1) ham-hex kartlardan (1.090:1) **daha kötü** çıkıyor çünkü zeminin kendisi off-palette. T1.6'da yok, S7'de yok — yeni, ayrı bir migrasyon adayı.

2. **varlik.html'in kart ailesinin tamamı (9 selector) tokens.css'e hiç bağlı değil:** Kendi `<style>` bloğunda local `:root { --surface:#161b22; --surface2:#1c2128; }` tanımlıyor (doğrulandı, satır 30-31) — GitHub-dark kalıntısı, `--bp-surface` sıfır kullanım. Bu, memory'deki 🔴 "Şablon-Yerel :root Palet Sapması" bulgusuyla birebir örtüşüyor.

3. **Token'ların kendisi tavan sorunu taşıyor:** En iyi kanonik-token kombinasyonu bile (`--bp-surface3` vs `--bp-bg` = 1.173:1) ≥1.5:1 hedefinin altında kalıyor — S7/T1.6/T5.4'ün "ham hex'i token'a çevir" reçetesi burada **yetersiz**; token'ların hex değerlerinin kendisi yeniden tasarlanmadan hedef mümkün değil.

4. **portfolio.html hem token hem kart sorununu aynı anda taşıyor:** `body{background:#0e0e12}` bile `var(--bp-bg)` değil, literal hex; `.sum-card/.add-bar/.pf-table` ve **`#cloudModalDialog` modalı** hepsi `#161b22` literal — ve bu satırların aynılarında S7 kapsamındaki `#30363d` border de geçiyor (somut S1/S7 örtüşme kanıtı, satır 39/44/54/239).

5. **Evrensellik:** 66 ölçülen birincil kart/zemin çiftinin (22 şablon, 3 farklı yüzey grubu) **tamamı** 1.2:1 eşiğinin altında veya sınırında — tek bir istisna yok. Bu, izole bir sayfa kusuru değil, tokens.css'in `--bp-bg`/`--bp-surface(2/3)` ailesinin **tasarım seviyesinde** sistemik bir kontrast açığı olduğunu gösteriyor. **§8'de doğrulandığı gibi bu evrensellik 22 şablonun ötesine, en az 6 ek şablona daha uzanıyor.**

---

## 6) Migrasyon Kararı — Öneri (KARAR VERİLMEDİ, yalnız envanter)

Bu bulgu seti, S1/S7/T3.4/T5.2/T5.4/T8'in kullandığı karar kuyruğuna eklenmeyi gerektiriyor görünüyor, çünkü:
- Ham-hex→token migrasyonu (S7/T1.6/T5.4 paterni) burada da geçerli bir alt-adım (13+22+12≈47 ham-hex satırı `var(--bp-surfaceN)`'e çevrilebilir — bkz. varlik.html, portfolio.html, blog*.html, sinyal_performans.html, hisse.html — §8'deki 6 ek şablon dahil edilirse bu sayı büyür).
- Ancak bu migrasyon **tek başına yetersiz**: hedefin (≥1.5:1) karşılanması için `--bp-surface/2/3` token'larının kendi hex değerlerinin (luminance) yükseltilmesi gerekiyor — bu, mevcut token-migrasyon kararlarından **kapsam olarak farklı** bir karar (tasarım-token revizyonu), aynı kuyruğa eklenmeli ama ayrı bir alt-görev olarak işaretlenmeli.
- sinyal_performans.html ayrıca **kendi başına bir öncelik**: sayfa zemininin `--bp-bg`'ye taşınması (token migrasyonu) hedefe ulaşmasa da en azından diğer 21 dosyayla aynı sıfır-noktasına getirir.
- **Kapsam genişletme kararı** (§8): migrasyon işi planlanırken 22 değil, en az 28 şablon (22 + 6 yeni tespit edilen) hedeflenmeli.

Nihai karar (hangi adayın önce alınacağı, token hex revizyonunun kapsamı, sıralama, kapsam genişletmesi) CPO/Ozan'a bırakılmıştır — bu rapor yalnızca envanter ve gözlem sunar.

---

## 7) Kanıt Komutları (tekrarlanabilir, kaynak raporlardan derlendi ve VPS'te `7b750ac` üzerinde tek tek yeniden çalıştırılarak doğrulandı)

```bash
# tokens.css referans değerleri
grep -n "bp-bg\|bp-surface" static/css/tokens.css

# Liste/Tablo sayfaları
grep -c 'background:\s*var(--bp-surface)' templates/index.html          # 17  ✅ doğrulandı
grep -c 'var(--bp-surface)' templates/gundem.html                       # 8   ✅ doğrulandı
grep -cE 'var\(--bp-surface[23]?\)' templates/ozet.html                 # 20  ✅ doğrulandı
grep -c '#161b22' templates/sinyal_performans.html                      # 5   ✅ doğrulandı
grep -c '#0b111f' templates/sinyal_performans.html                      # 5 (+3 _head.html) ✅ doğrulandı

# Detay sayfaları
grep -oP 'background:\s*var\(--bp-surface\)'  templates/hisse.html | wc -l   # 23 ✅ doğrulandı
grep -oP 'background:\s*var\(--bp-surface2\)' templates/hisse.html | wc -l   # 16 ✅ doğrulandı
grep -oP 'background:\s*var\(--surface\)'     templates/varlik.html | wc -l # 9  ✅ doğrulandı (yerel, token DEĞİL)
grep -oP 'background:\s*var\(--surface2\)'    templates/varlik.html | wc -l # 6  ✅ doğrulandı
find templates -iname '*sektor*karsilastir*'                                # boş — dosya yok ✅ doğrulandı

# Diğer yüzeyler
find . -iname gucu_yuksek.html                                          # boş — dosya yok ✅ doğrulandı
grep -n 'background:#161b22\|background: #161b22' templates/portfolio.html \
  templates/blog.html templates/blog_article.html templates/metodoloji.html
grep -n 'background:\?\s*var(--bp-surface)\b' templates/profil.html templates/404.html
```

---

## 8) Kapsam Boşluğu — Bağımsız Doğrulama Turunda Tespit Edildi (YENİ)

Bağımsız doğrulama raporu 22 değil **32 şablonun tamamını** taradı. Karşılaştırma sonucu, sentezin 22-dosyalık kapsamının dışında kalan **10 şablon** var; bunlardan **6'sı** aynı sıfır-ayrım desenini taşıyor (`7b750ac` üzerinde tek tek doğrulandı):

| Dosya | Kanıt (satır) | Tip | Kova |
|---|---|---|---|
| gizlilik.html | `header{background:#161b22}` (22) | HAM | (a)+(d) |
| hakkinda.html | `background:#161b22` (30,115,132,152,168,183) | HAM | (a)+(d) |
| hisseler.html | `background:#161b22` (30,115,132,152,168,183,262,267,307) | HAM | (a)+(d) |
| iletisim.html | `header{background:#161b22}` (22), `.card{background:#161b22}` (31) | HAM | (a)+(d) |
| yasal.html | `header{background:#161b22}` (22), (50) | HAM | (a)+(d) |
| unsubscribe.html | `background:var(--bp-surface)` (15) | Token | (a) |

Diğer 4 dosya (`_head.html`, `_header_asset_price.html`, `_analytics.html`, `_stale_banner.html`) kart/zemin çifti içermiyor — mevcut `offline.html`/`_base.html`/`_header.html` dışlama mantığıyla aynı kategoride, kapsam dışı kalmaları doğru.

**Sonuç:** §5 madde 5'teki "evrensellik" iddiası 22 şablonla sınırlı değil — doğrulanan minimum kapsam **28 şablon**dır (22 + bu 6). §6'daki migrasyon kararı bu genişletilmiş kapsamla planlanmalı.

---

## 9) Çapraz Doğrulama Notu (Bu Sentez ile Bağımsız Rapor Karşılaştırması)

- **Mutabakat:** Kova toplamları nitel olarak birebir örtüşüyor (SIFIR-AYRIM ~%100, ZAYIF~0, YETERLİ=0); "1.05:1" iddiası her iki raporda da DOĞRU/güncel bulundu.
- **Bu sentezde hata bulunmadı:** ~25 satır/hex/sayı iddiası tek tek `7b750ac` üzerinde yeniden hesaplandı, tamamı doğrulandı (bkz. §7 ✅ işaretleri).
- **Bağımsız raporda düzeltilmesi gereken 3 nokta (bu sentezi etkilemiyor, ama referans alınırken dikkat edilmeli):**
  1. `grep -c 'background: var(--bp-surface);' templates/*.html` iddiası "73 (14 şablon)" — gerçek çalıştırıldığında **47 (11 şablon)**.
  2. `grep -c 'background: var(--bp-surface2);' templates/*.html` iddiası "77 (12 şablon)" — gerçek **49 (9 şablon)**; buna bağlı "~209" toplamı da düzeltilmeli → **155**.
  3. sinyal_performans.html `.back-btn`/`.clause-num`'ın `#21262d` ham-hex olduğu iddiası yanlış — o dosyada `.clause-num` yok, `.back-btn` ise `var(--bp-surface2)` (token).
- Bu 3 nokta bağımsız raporun **nitel sonucunu değiştirmiyor** (kova toplamları hâlâ doğru), yalnız kendi "grep -c ile doğrulanabilir" iddialarının bir kısmı literal olarak tekrarlanamıyor. Kapsam-genişletme bulgusu (§8) ise bağımsız raporun **gerçek katkısı** olarak bu senteze işlendi.

---

**Kod hiçbir raporda değiştirilmedi — bu sentez de yalnız envanter, çapraz-doğrulama ve karar önerisi sunar, uygulama kararı CPO/Ozan'a bırakılmıştır.**
