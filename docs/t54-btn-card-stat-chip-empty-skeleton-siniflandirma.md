# T5.4 — btn/card/stat/filtre-chip/boş-durum/skeleton-spinner Kod Tekrarı Sınıflandırması (KOD DEĞİŞMEDİ)

**Tarih:** 16.08.2026 · **Kapsam:** Yalnız sınıflandırma + konsolidasyon fizibilite önerisi. Bu turda hiçbir CSS/HTML/JS değişmedi. Format ve disiplin S1/S7/T3.4/T5.2/FAZ8-6-8 emsaliyle birebir aynı: 6 paralel aile-bulucu ajan (her biri yalnız kendi ailesine baktı, birbirini görmedi) → 1 sentez ajanı (bu doküman). **Bağımsız doğrulama turu bu belgede yapıldı** (SSH grep/read, sentez ajanının akıl yürütmesi görülmeden) — 3 küçük düzeltme dışında tüm iddialar teyit edildi.

## Genel özet tablosu

| Aile | Şablon sayısı | Toplam markup kullanımı | Ajan-bildirimli varyant sayısı | Sentezde yeniden sayılan varyant sayısı | Ham-hex bayraklı varyant |
|---|---|---|---|---|---|
| `.btn` / `.btn-*` | 7 (6 sayfa + 1 partial) | 16 ✓ | 10 | 10 ✓ (uyumlu, grep ile teyit) | 4/10 |
| `.card` / kart aileleri | 19 | 91 | 33 | **38** ⚠ (uyumsuz, aşağıda) | 11/38 (+9 "sahte-token" yerel-alias) |
| `.stat` / istatistik kutusu | 8 | 142 | 28 | 28 ✓ (uyumlu) | 13/28 |
| filtre-chip / chip | 5 | 58 | 21 | 21 ✓ (uyumlu) | 10/21 |
| boş-durum / empty-state | 9 | 25 | 15 | 15 ✓ (uyumlu, grep ile teyit) | 0/15 ✓ (grep ile teyit) |
| skeleton-spinner | 11 | 145 | 28 | 28 ✓ (uyumlu) | 11/28 |
| **TOPLAM** | **~35 benzersiz şablon** (çakışmalarla) | **477** ✓ | **135** ✓ | **~140** ✓ | **49/140 (~%35)** ✓ |

⚠ **card ailesinde sayım tutarsızlığı bulundu:** card ajanının `distinct_variants` dizisini satır satır saydığımda **38** benzersiz tanım (dosya×selector çifti) var, ama ajan `total_distinct_variant_count: 33` bildirmiş. Fark aritmetik olarak açıklanabilir: ajan muhtemelen aynı isimli 3 kopyayı (`.stock-card` × 3 dosya → 1 sayılmış, −2) ve `.other-card` × 2 dosyayı (−1) tek isim olarak saymış, ayrıca 2 SINIR-BELİRSİZ varyantı (`.sig-stat-card`, `.mc`) toplam dışı bırakmış (−2) → 38−5=33 tam oturuyor. Bu rapor **38**'i esas alıyor çünkü konsolidasyon açısından önemli olan "aynı isim aynı yerde mi" değil, "kaç FARKLI görsel sözleşme var" — `.stock-card` 3 dosyada 3 farklı piksel sonucu üretiyor, tek satır sayılması yanıltıcı (T5.2'nin "17 vs 20" aritmetik hatasıyla aynı sınıf bir bulgu). **Bağımsız doğrulama notu:** `.stock-card`'ın 3 dosyadaki (`bilanco_takvimi`, `gundem`, `ozet`) padding ve radius değerleri gerçekten üçü de farklı; ama arka plan **token kaynağı** iddiadaki gibi "hepsi farklı" değil — `bilanco_takvimi` ve `gundem` ikisi de `var(--bp-surface)` kullanıyor, yalnız `ozet` `var(--bp-surface2)` ile ayrışıyor. `.other-card`'ın hisse.html (`var(--bp-surface2)`/`var(--bp-border)`, kanonik) ve varlik.html (`var(--surface)`/`var(--border)`, yerel sahte-token) tanımları gerçekten farklı token sistemlerine bağlı — bu kısım doğrulandı.

---

## 1. `.btn` / buton ailesi

| Şablon | Class'lar | Markup kullanım |
|---|---|---|
| profil.html | `btn`, `btn-secondary` | 3 |
| unsubscribe.html | `btn` (bağımsız 2. tanım) | 1 |
| portfolio.html | `btn-add`, `btn-del`, `btn-action`, `btn-entry` | 8 |
| sinyal_performans.html | `btn-run` | 2 |
| tarama.html | `btn-reset` | 2 |
| index.html + _mobile_nav_partial.html | `btn-refresh` | **0** (ölü) |

**10 benzersiz varyant, 16 markup kullanımı** — Python ile `class="..."` içindeki tam token eşleşmesi taranarak doğrulandı: profil=3, unsubscribe=1, portfolio=8, sinyal_performans=2, tarama=2, index=0, toplam=16. Kritik bulgular:
- `.btn-refresh` tamamen **ölü CSS** — JS (`index.html:4335`) var olmayan bir `id="bpRefreshBtn"`'i arıyor, hiçbir template'te class veya id kullanılmıyor. (Doğrulandı: `index.html` üzerinde class-bazlı `.btn-refresh` kullanımı sıfır çıktı, yalnız CSS tanımları ve bir media-query override'ı var.)
- Aynı isim `.btn`, iki bağımsız dosyada (profil/unsubscribe) tanımlı — kabuk-drift.
- `.btn-add` (`background:#1f6feb; ...hover:#388bfd`) ile `.btn-run` (`background:#1f6feb; ...hover:#388bfd`) birbirinden bağımsız olarak **birebir aynı** ham-hex mavisini tekrarlıyor — doğrulandı, satır satır aynı.
- `.btn-action` (`border:1px solid #30363d; color:#8b949e`) bilinen [[reference_bkl_token_mavi_ama_asil_kalinti_ham_hex]] deseniyle örtüşen ham-hex kalıntısı — doğrulandı.
- `.btn-entry` (portfolio.html) `background:rgba(63,185,80,.1)` / `color:#3fb950` ile ham-hex — doğrulandı.
- `.btn-reset` (tarama.html) kanonik `--bp-*` değil, tarama.html'in yerel `:root`'undaki `--text2:#8b949e` / `--border:var(--bp-bkl-bd)` takma adlarına bağlı — [[reference_sablon_yerel_root_palet_sapmasi]] deseninin somut örneği, doğrulandı.

**SINIR-BELİRSİZ aday (btn ajanının bilinçli dışarıda bıraktığı):** `blog_article.html`'deki `.cta-btn-primary`/`.cta-btn-secondary` — isim sırası ters ("cta-btn-" öneki) ama semantik olarak profil.html'deki `.btn`/`.btn-secondary` birincil/ikincil çiftiyle aynı kavram. **Sentez kararı: bu aileye dahil edilmeli** (11. varyant olarak).

**Kapsam dışı, ayrı bir aile:** btn ajanı 20'den fazla bağımsız `*-btn` SONEKLİ class buldu (`macro-pause-btn`, `filter-btn`, `sector-btn`, `share-btn`, `compare-btn`, `th-sort-btn`, `alarm-btn`, `alert-settings-btn`, `sub-toast-btn`, vb. — geniş bir grep ile en az 13 farklı sonek-class doğrulandı) — bunlar `.btn`/`.btn-*` ÖNEK ailesinin dışında, isim benzerliği yüzeysel.

---

## 2. `.card` / kart ailesi

19 şablona dağılmış, 91 markup kullanımı, **38 benzersiz tanım** (bkz. yukarıdaki sayım notu).

| Şablon grubu | Örnek class'lar | Not |
|---|---|---|
| iletisim, blog, blog_article, hakkinda/hisseler, portfolio, yasal | `.card`, `.blog-card`, `.rel-card`, `.rel-stock-card`, `.feature-card`/`.tech-card`/`.market-card`, `.sum-card`, `.section-card` | Hepsi doğrudan ham hex `#161b22`/`#30363d` (var() bile yok) — doğrulandı, hepsinde `background:#161b22; border:1px solid #30363d;` harfiyen |
| varlik, kategori, tarama | `.chart-card`, `.ind-card`, `.history-card`, `.commentary-card`, `.loading-card`, `.signal-card`, `.other-card`, `.asset-card`, `.mr-card` | "Token" görünümlü ama şablonun kendi yerel `:root`'unda `--surface:#161b22`/`--border:#30363d` yeniden tanımlanmış — kanonik `--bp-surface:#141416` DEĞİL (doğrulandı: varlik.html ve kategori.html `:root` blokları satır satır kontrol edildi) |
| hisse, index, ozet, profil, sektor_harita, gundem, 404 | `.content-card`, `.info-card`, `.endeks-card`, `.gnm-card`, `.counter-card`, `.form-card`, `.sector-card`, `.stock-card`(gundem), `.search-card` | Çoğunlukla doğru kanonik `var(--bp-surface)`/`var(--bp-border)` — **doğrulama notu:** `.gnm-card` (index.html) gerçekte `var(--bg2)` kullanıyor, `var(--bp-surface)` değil; `--bg2` tokens.css'te ayrı bir token (`#141416`) olarak tanımlı ve değeri kanonikle aynı olduğu için piksel sonucu doğru, ama token adı bu grupta iddia edildiği gibi doğrudan `--bp-surface` değil |

**En kritik bulgu:** yukarıdaki ilk iki grup (toplam ~20 varyant) piksel olarak **aynı** `#161b22` grisini üretiyor ama biri hardcoded, diğeri sahte-token yoluyla — ikisi de kanonik `#141416`'dan sapıyor. Yani kod tabanının kart ailesinin **yarısına yakını** yanlış/eski gri tonunu gösteriyor, azınlık bir kalıntı değil.

Diğer önemli noktalar (grep ile doğrulandı):
- `.stock-card` 3 şablonda (bilanco_takvimi, gundem, ozet) **3 farklı** tanım — radius (`--bp-radius-lg` / `--bp-radius` / `--bp-radius-md`) ve padding (`12px 14px` / `14px 16px` / `12px 13px`) üçü de farklı. **Düzeltme:** bg-token kaynağı "hepsi farklı" DEĞİL — bilanco_takvimi ve gundem ikisi de `var(--bp-surface)`, yalnız ozet `var(--bp-surface2)` kullanıyor.
- `hisseler.html`'deki `.feature-card`/`.tech-card`/`.market-card` bloğu `hakkinda.html`'den **birebir kopya** (diff ile teyit edildi, sıfır fark) ama 0 markup kullanımı — tam ölü CSS, doğrulandı.
- `.metric-card` (sektor_harita) ailedeki **tek borderless** kart; `.bp-hero-card` ve `.tldr-card` ailedeki tek gradient/hero kartlar — bunlar konsolidasyon dışı tutulmalı (kasıtlı özel tasarım).

**SINIR-BELİRSİZ (card ajanının kendi işaretlediği):**
- `.sig-stat-card` (hisse.html) — hem stat ajanı hem card ajanı bağımsız olarak aynı class'ı bulup ambiguous işaretlemiş.
- `.mc` (index.html) — isminde "card" geçmiyor ama kod yorumu açıkça "Glass card" diyor.

---

## 3. `.stat` / istatistik kutusu ailesi

8 şablona dağılmış, **142 markup kullanımı**, 28 benzersiz tanım.

**Kritik bulgu: ÜÇ farklı çakışan `.stat-card` tanımı** — doğrulandı satır satır:
- gundem: `background: var(--bp-surface); border: 1px solid var(--bp-border); ... padding: 18px 16px;` (token)
- index: `background: rgba(var(--bp-surface-rgb),0.8); ... backdrop-filter: blur(8px); ... padding: 14px 20px;` (token + blur)
- sinyal_performans: `background:#161b22; border:1px solid #30363d; ... padding:20px;` (**tamamen ham hex**)

Aynı class adı, üç görsel olarak farklı kutu — teyit edildi.

**Naming-drift — aynı kavramın 4 ek kopyası:** `sig-stat-*` (hisse), `hh-stat*` (hisseler), `ms-stat*` (index), `cmp-stat-pill*` (sektor_harita) — toplamda **7 farklı isim** ailesi aynı kavramı taşıyor.

- `index.html`'de `.stat-premium .stat-num { color: #ffc850; }` tek başına ham-hex, kardeşleri (`.stat-al`→`var(--bp-al)`, `.stat-sat`→`var(--bp-sat)`, `.stat-bekle`→`var(--bp-bkl)`, `.stat-total`→`var(--bp-brand)`) token — satır satır doğrulandı, S7/T5.2 emsaliyle aynı "ailede tek ham-hex kalıntısı" deseni.
- `.stat-box` (hisseler.html) hakkinda.html'den birebir kopya ama 0 markup kullanımı.

---

## 4. Filtre-chip / chip ailesi

5 şablona dağılmış, 58 markup kullanımı, 21 benzersiz tanım.

**En kritik bulgu — isim çakışması, farklı sözleşme:** `.chip-al`/`.chip-sat` sektor_harita.html'de **tam chip** (`background:rgba(0,226,144,.10); color:#00e290; border:1px solid rgba(0,226,144,.22);`) iken hisse.html'de **sadece renk utility'si** (`.chip-al { color: var(--bp-al); }`, kutu stili yok) — doğrulandı, aynı isim iki bağımsız ve görsel olarak uyumsuz sözleşme.

- `.active-chip`/`.chip-x`/`.chip-clear-all` (tarama.html) kanonik `--bp-*` yerine `var(--text, #e6edf3)`/`var(--text2, #8b949e)` fallback'li parallel değişkenler kullanıyor — doğrulandı, bp-vocab.js sözlüğü dışında bir alt-sistem.
- Radius token çeşitliliği: aynı "pill" şekli için **7 farklı** radius token'ı doğrulandı — `--bp-radius-pill` (preset-chip), `--bp-radius-14` (afb-chip), `--bp-radius-xl` (adv-chip), `--bp-radius-20` (sektor_harita `.chip`, tarama `.active-chip`), `--bp-radius-16` (tarama `.chip-clear-all`), `--bp-radius-md` (related-chip, sum-chip), `--bp-radius` (stock-chip, varsayılan) — tam 7, iddia doğrulandı.

---

## 5. Boş-durum / empty-state ailesi

9 şablona dağılmış, 25 markup kullanımı, **15 benzersiz tanım.** 13 farklı class adı doğrulandı: `no-results`, `no-data`, `empty-state`(×2 dosya), `cmp-empty-state`, `empty-box`, `hp-empty`, `sac-empty`, `ac-empty`, `kap-empty`, `search-empty`(×4 dosya), `macro-news-empty`, `ap-empty`, `empty-msg`(×2 dosya).

**Olumlu istisna — doğrulandı:** 15 varyantın **hiçbiri** ham hex kullanmıyor — tümü `var(--bp-text3)`/`var(--bp-text2)`/`var(--bp-surface)`/`var(--bp-border)` (veya tarama.html'in yerel-alias `var(--text2)`) token'larına bağlı; tek tek 15 tanım açılıp kontrol edildi.

- **3 ayrı ölü-CSS örneği doğrulandı:** `index.html .no-data` (grep'te yalnız CSS satırı çıktı, 0 markup), `ozet.html .empty-msg` (0 markup), `.search-empty` 4 şablonda (hisse/index/ozet/sektor_harita) birebir kopya, 4'ünde de 0 markup kullanımı.
- `tarama.html .empty-state` gerçekten `var(--text2)` (tarama'nın yerel `#8b949e`) kullanıyor, `karsilastir.html`'deki aynı adlı class ise `var(--bp-text3)`/`var(--bp-text2)` kanonik — doğrulandı, [[reference_sablon_yerel_root_palet_sapmasi]].
- `.empty-msg` iki dosyada padding: ozet 20px vs portfolio 60px — tam 3 kat, doğrulandı.

---

## 6. Skeleton-spinner (yükleniyor göstergesi) ailesi

11 şablona dağılmış, **145 markup kullanımı**, **28 benzersiz tanım.**

**Kritik bulgular (doğrulandı):**
- `.spinner` **tek isim altında 6 tanım, 5 farklı gerçek piksel boyutu**: 16px (`#ptr-spinner`), 18px (hisse), 20px (kategori), 24px (tarama — `varlik.html`'in birebir kopyası), 28px (index). Not: tarama/varlik'in 24px'i aynı değer — "6 farklı boyut" değil, "6 tanım / 5 farklı boyut" doğru ifade.
- Üç ayrı ham-hex shimmer renk ailesi, doğrulandı: `#161b22/#1e2530` (gundem+karsilastir, birebir aynı `linear-gradient`), `#141416/#1e1e22` (`.gnm-sk` class hali), `#1c1b1f/#232124` (`.cmp-skeleton`).
- `index.html`'de **aynı `@keyframes gnm-shimmer`** iki farklı gerçek renk tarifiyle kullanılıyor: class hali (`.gnm-sk`) tam ham-hex (`#141416`/`#1e1e22`), satır-içi hali `var(--bp-surface)` (token) + `#1e1e22` (ham-hex) karışık — doğrulandı, satır satır karşılaştırıldı.
- `.ms-sk-line`'ın `rgba(48,54,61,...)` = `#30363d` matematiksel olarak doğrulandı (48=0x30, 54=0x36, 61=0x3d) — [[reference_bkl_token_mavi_ama_asil_kalinti_ham_hex]] deseninin skeleton ailesindeki tekrarı.
- `tarama.html`/`varlik.html` `.spinner` tanımları birebir aynı (`width:24px; height:24px; border:3px solid var(--border); ...`) — doğrulandı.

---

## Cross-family SINIR-BELİRSİZ kararları

(Değişmedi — sentez ajanının atama mantığı incelendi, tutarlı bulundu.)

| Class | Flagleyen ajan(lar) | Sentez kararı | Gerekçe |
|---|---|---|---|
| `.sig-stat-card`/`.sig-stat-val/-lbl` | card **ve** stat | **stat** ailesine ata | Yapısal olarak stat kutusu |
| `.mc` (index.html glass card) | card | **card** ailesine ata | Yalnız card ajanı bulmuş |
| `.stat-card` (3 varyant) | stat | **stat** ailesinde kalır | card ajanı zaten kapsam dışı bırakmış |
| `.sum-chip` | filtre-chip | **stat** ailesine öneri | İşlevi filtre değil özet-sayaç kutusu |
| `.chip-al/-sat/-bekle` (hisse.html utility) | filtre-chip | **T5.2 kapsamına yakın, ayrı** | AL/SAT/BEKLE kavramının 3. bağımsız isimlendirmesi |
| `.cta-btn-primary/-secondary` | btn | **btn** ailesine dahil et | Aynı birincil/ikincil kavramı |
| `#ptr-spinner`, `#inlineSpinner`, inline `gnm-shimmer`, `.rel-stock-skeleton` | skeleton-spinner | **skeleton-spinner** ailesinde kalır | ID/inline notuyla |

---

## Ham-hex vs token ayrımı — aile bazlı

| Aile | Ham-hex bayraklı | Toplam | Oran | Not |
|---|---|---|---|---|
| btn | 4 | 10 | %40 | `.btn-add/-action/-entry/-run` — doğrulandı |
| card | 11 (+9 sahte-token yerel-alias) | 38 | %29 (~%53 sahte-token dahil) | En büyük risk |
| stat | 13 | 28 | %46 | `.stat-premium` tek-ham-hex-istisna deseni |
| filtre-chip | 10 | 21 | %48 | Hover/active durumunda ham-hex'e kayma |
| boş-durum | 0 | 15 | **%0** | Doğrulandı, ailenin tek "temiz" örneği |
| skeleton-spinner | 11 | 28 | %39 | 3 farklı, birbiriyle uyumsuz ham-hex ton ailesi — doğrulandı |

Toplam ham-hex: 4+11+13+10+0+11=49, toplam varyant: 10+38+28+21+15+28=140, oran %35 — aritmetik doğrulandı.

---

## Master Program eski sayılarla karşılaştırma

(Değişmedi — hedge'li ifadeler ["muhtemelen", "doğrulanamadı"] uygun, iddia olarak sunulmamış.)

| Aile | Eski sayı | Bu turun bulgusu | Değerlendirme |
|---|---|---|---|
| btn | 34 varyant / 26 kullanım | 10 varyant (+1 önerilen=11) / 16 kullanım, 7 şablon | Muhtemelen yanlış ölçüt, doğrulanamadı |
| card | 46 varyant / 23 şablon | 38 (veya 33) varyant / 19 şablon | Kabaca hâlâ doğru, hafif küçük |
| skeleton | 17 varyant | 28 varyant / 11 şablon | Artık doğru değil, büyümüş |

---

## Konsolidasyon önerisi (UYGULAMA DEĞİL, yalnız öneri)

(Değişmedi — bu bölüm fizibilite haritası, doğrulama kapsamı dışında kaldı çünkü henüz uygulanacak somut bir kod değişikliği içermiyor.)

### Üstüne binebilecek (Δ≈0)
- **btn:** `.btn-add` ↔ `.btn-run` — birebir aynı ham-hex mavi.
- **card:** `hisseler.html`'deki `.feature-card`/`.tech-card`/`.market-card` (0 kullanım) — önce **sil**.
- **stat:** `hisseler.html`'deki `.stat-box`/`.stats-row` (0 kullanım) — önce sil.
- **filtre-chip:** `.afb-clear-all` ↔ `.chip-clear-all`.
- **boş-durum:** `.search-empty`'nin 4 şablondaki kopyası (hepsi 0 kullanım); `.no-data`, `.empty-msg`(ozet.html).
- **skeleton-spinner:** `tarama.html`/`varlik.html` `.spinner` (birebir aynı).

### Gerçek görsel/marka kararı gerektiren
- **card:** `--bp-surface`/`--bp-border` mi yoksa `#161b22`/`#30363d` mi "doğru" kart rengi.
- **stat:** 7 farklı isim → kanonik isim + kanonik renk kaynağı seçimi.
- **filtre-chip:** `.chip-al`/`.chip-sat` isim çakışması — kanonikleştirme öncesi ayrıştırılmalı.
- **skeleton-spinner:** `.spinner`'ın 5 farklı boyutu (6 tanım) kasıtlı mı kazara mı; 3 ham-hex shimmer ton ailesinden hangisi kanonik.
- **btn:** `.btn-action`'ın ham-hex çifti token'a geçerken görsel fark yaratmayacağı varsayılmamalı.

### Önerilen sıralama
1. Ölü CSS temizliği (0-kullanımlı tanımlar).
2. Birebir-aynı kopyaları ortak class'a taşı.
3. Renk kaynağı kararları CPO/Ozan kuyruğuna.
4. İsim çakışması taşıyan class'lar ayrıştırılmalı.
5. `.sig-stat-card`/hisse.html `.chip-al` bir sonraki tur için not edildi.

---

## Açık riskler (CPO/Ozan kararı gerektirebilir)

1. card ailesinin ~yarısının kanonik `#141416`/`#2a2a2c`'e geçişi — görsel onay gerekir.
2. stat ailesindeki 7 isimli tekrarın kanonik isim seçimi.
3. `.chip-al`/`.chip-sat` isim çakışması — kanonikleştirme öncesi ayrıştırma.
4. `.spinner`'ın 5 farklı boyutunun (6 tanım) kasıtlı mı kazara mı olduğu belirsiz.
5. Master Program'daki "34/26" (btn) rakamının ölçütü doğrulanamadı.
6. `.sig-stat-card` ve hisse.html `.chip-al/-sat/-bekle` T5.2 sınırında kalan ek isimlendirmeler.

---

## Sıradaki

Bu doküman yalnız sınıflandırma + fizibilite — migrasyon kararları CPO/Ozan onayı bekliyor. Büyük ölçekli migrasyona bu turda GİRİLMEDİ. **Bağımsız doğrulama bu turda yapıldı ve 3 küçük düzeltme dışında raporun tüm iddiaları grep/read ile teyit edildi** — sonraki turlarda yeniden doğrulama gerekmez, yalnız bu 3 düzeltilen nokta not edilmeli.

---

## Bağımsız doğrulama notu (ham)

## Doğrulama Sonucu: DÜZELTME_GEREKLİ (küçük ölçekli, 3 nokta)

Raporun neredeyse tüm somut iddialarını (renk kodları, token/ham-hex ayrımı, ölü CSS, markup sayıları, sınıf isimleri) bağımsız grep/read ile SSH üzerinden tek tek doğruladım. Btn ailesinin 10/16 sayımı, boş-durum ailesinin %0 ham-hex + 13 isim + 4×0-kullanım `.search-empty` iddiası, stat ailesinin üç çakışan `.stat-card` tanımı, `.stat-premium` tek-ham-hex deseni, chip ailesinin 7 farklı radius token'ı, `.chip-al/-sat` sözleşme çakışması, skeleton ailesinin 3 ayrı shimmer renk ailesi ve `.ms-sk-line` rgba(48,54,61)=#30363d eşitliği — hepsi harfiyen doğrulandı. Genel toplam tablosundaki aritmetik (477, 135, ~140, 49/140=%35) de satır satır toplanıp doğru bulundu. Yine de 3 somut, grep-kanıtlı hata buldum:

**1) Card ailesi — `.gnm-card` yanlış grupta / yanlış token adıyla anılmış**
Rapor `.gnm-card`'ı "kanonik `var(--bp-surface)`" kullanan 3. grupta listeliyor. Gerçekte:
```
templates/index.html:837:  .gnm-card { background: var(--bg2); border: 1px solid var(--bp-border); ...
static/css/tokens.css:98:  --bg2: #141416;
```
`--bg2` `--bp-surface` değil, ayrı bir token — değeri aynı (#141416) olduğu için piksel sonucu doğru ama rapor iddiası ("`var(--bp-surface)` kullanıyor") teknik olarak yanlış.

**2) Card ailesi — `.stock-card` "bg-token kaynağı hepsi farklı" iddiası yanlış**
```
bilanco_takvimi.html:90:  .stock-card { background:var(--bp-surface); ...
gundem.html:91:          .stock-card { background: var(--bp-surface); ...
ozet.html:128:           .stock-card { background: var(--bp-surface2); ...
```
`bilanco_takvimi` ve `gundem` **aynı** token'ı (`--bp-surface`) kullanıyor; yalnız `ozet` farklı (`--bp-surface2`). Yani bg-token kaynağı "hepsi farklı" değil, 2/3 aynı. (Radius ve padding gerçekten üçü de farklı — bu kısım doğru; yalnız bg-token cümlesi hatalı.)

**3) Skeleton ailesi — `.spinner` "6 farklı gerçek piksel boyutu" iç-tutarsız**
```
index.html:1356    width:28px  hisse.html:444  width:18px  kategori.html:107  width:20px
tarama.html:302     width:24px  varlik.html:219 width:24px  #ptr-spinner:5501 width:16px
```
Gerçek **farklı** değer sayısı 5'tir (16/18/20/24/28) — tarama ve varlik'in 24px'i raporun kendi metninde de "birebir kopya" diye not düşülmüş, yani aynı değer. "6 farklı boyut" ifadesi kendi parantetik açıklamasıyla çelişiyor; doğrusu "6 tanım, 5 farklı boyut".

Bunların dışında hiçbir hata bulamadım — btn/stat/chip/boş-durum/skeleton ailelerinin sayıları, token/ham-hex iddiaları, SINIR-BELİRSİZ kararları ve card ailesinin 33 vs 38 uyuşmazlık açıklaması (stock-card 3 kopya, other-card 2 kopya, hisseler.html'nin feature/tech/market-card'ının hakkinda.html'den birebir + 0-kullanım kopyası) grep ile teyit edildi.
