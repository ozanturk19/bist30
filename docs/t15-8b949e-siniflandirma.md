# T1.5 GitHub-Legacy Palet Migrasyonu — Ham `#8b949e` Sınıflandırması

**Tarih:** 16.08.2026 · **Durum:** SINIFLANDIRMA TAMAM, KOD DEĞİŞMEDİ · **Desen:** S1/S7/T5.2/T5.4/T8-tipografi/T8-başlık ile aynı disiplin (paralel sınıflandırma → sentez → bağımsız doğrulama, tamamı salt-okuma SSH)

**Kapsam:** T1.5'in ("GitHub-legacy palet migrasyonu: eşleme tablosu + mekanik sed, 935 hit/23 sayfa") parçası olan `#0d1117\|#161b22\|#30363d\|#8b949e\|...` grep desenindeki renklerden **`#30363d` zaten S7'de sınıflandırılmıştı** (106/16, `0bd66aa`); bu doküman aynı ailenin sınıflandırılmamış ikinci büyük kalemi olan **`#8b949e`**'yi kapsıyor. `#161b22`/`#0d1117` bu turun kapsamı dışında (ayrı bir tur gerektirir).

**Yöntem:** Workflow ile 4 paralel sınıflandırma ajanı (20 şablon 5'erli 4 gruba bölünmüş, her biri yalnız kendi kapsamına SSH salt-okuma grep+read ile baktı, birbirini görmedi) → 1 sentez ajanı → 1 tamamen bağımsız doğrulama ajanı (sentezi görmeden kendi grep'lerini sıfırdan çalıştırdı, rastgele 3 dosyayı elle yeniden okudu). Hiçbir dosya değiştirilmedi, hiçbir git komutu çalıştırılmadı.

---

## 1. Özet

**Toplam ham `#8b949e` kullanımı: 180**, 20/20 şablonda en az 1 kullanım (0 kullanımlı dosya yok). Bağımsız doğrulama ajanı sıfırdan aynı grep'i çalıştırıp dosya-bazlı sayıların **tamamını birebir doğruladı** — tutarsızlık yok.

**Kova dağılımı (doğrulama düzeltmesi uygulanmış hali — bkz. §7):**

| Kova | Adet | Yüzde | Aday kanonik token |
|---|---|---|---|
| MUTED-TEXT | 128 | %71.1 | `--bp-text2` (#c7c5cd) |
| NEUTRAL-INDICATOR | 41 | %22.8 | `--bp-bkl` (#909097) |
| DIGER | 11 | %6.1 | (ayrı karar gerekir, aşağıda §5) |
| **Toplam** | **180** | **%100** | |

*(Sentezin ilk hali 129/40/11 vermişti; bağımsız doğrulama `gundem.html:503`'ün NEUTRAL-INDICATOR olması gerektiğini — MUTED-TEXT değil — bulup düzeltti, bkz. §7.)*

---

## 2. Tam Envanter Tablosu

| Dosya | Satır | Kova | Gerekçe |
|---|---|---|---|
| _premium_modal.html | 169 | MUTED-TEXT | "⏳ Kayıt yapılıyor…" ikincil durum metni |
| _premium_modal.html | 210 | MUTED-TEXT | "⏳ Kontrol ediliyor…" ikincil durum metni |
| bilanco_takvimi.html | 44 | MUTED-TEXT | `.page-sub` sayfa alt-başlık metni |
| bilanco_takvimi.html | 46 | MUTED-TEXT | `.top-nav-links a` ikincil nav link metni |
| bilanco_takvimi.html | 81 | NEUTRAL-INDICATOR | `.badge-upcoming` — "gelecek dönem" nötr/pasif durum rozeti |
| bilanco_takvimi.html | 133 | MUTED-TEXT | `.sum-lbl` özet chip etiket metni |
| bilanco_takvimi.html | 145 | MUTED-TEXT | `footer a` footer link rengi |
| bilanco_takvimi.html | 167 | NEUTRAL-INDICATOR | `.mc-neu` makro ticker nötr değişim |
| bilanco_takvimi.html | 195 | NEUTRAL-INDICATOR | `#sumBkl` inline stil, BEKLE sayacı |
| blog.html | 24 | MUTED-TEXT | `.back-btn` geri linki |
| blog.html | 27 | MUTED-TEXT | `.page-sub` |
| blog.html | 29 | MUTED-TEXT | `.top-nav-links a` |
| blog.html | 36 | MUTED-TEXT | `.cat-btn` kategori filtre chip metni |
| blog.html | 52 | DIGER | `.blog-card:hover` border-color, hover vurgusu |
| blog.html | 55 | MUTED-TEXT | `.bc-desc` açıklama metni |
| blog.html | 60 | MUTED-TEXT | `footer a` |
| blog.html | 77 | NEUTRAL-INDICATOR | `.mc-neu` makro nötr |
| blog_article.html | 104 | MUTED-TEXT | `.back-btn` |
| blog_article.html | 106 | MUTED-TEXT | `.page-sub` |
| blog_article.html | 113 | MUTED-TEXT | `.art-desc` |
| blog_article.html | 139 | MUTED-TEXT | `.related-title` |
| blog_article.html | 142 | DIGER | `.rel-card:hover` border-color |
| blog_article.html | 149 | DIGER | `.rel-stock-card:hover` border-color |
| blog_article.html | 155 | NEUTRAL-INDICATOR | `.rel-stock-sig.bekle` |
| blog_article.html | 175 | MUTED-TEXT | `.faq-a` |
| blog_article.html | 207 | MUTED-TEXT | `footer a` |
| blog_article.html | 224 | NEUTRAL-INDICATOR | `.mc-neu` |
| blog_article.html | 319 | MUTED-TEXT | bülten kutusu ikincil açıklama |
| gizlilik.html | 23 | MUTED-TEXT | `.back-btn` |
| gizlilik.html | 27 | MUTED-TEXT | `.top-nav-links a` |
| gizlilik.html | 38 | MUTED-TEXT | `footer a` |
| gundem.html | 203 | NEUTRAL-INDICATOR | `.mc-neu` |
| gundem.html | 227 | MUTED-TEXT | "AI Piyasa Özeti" eyebrow etiketi |
| gundem.html | 434 | NEUTRAL-INDICATOR | `dotClr` JS, nötr bilanço dönem noktası |
| gundem.html | 463 | NEUTRAL-INDICATOR | `sigCls` JS, AL/SAT/BEKLE nötr kol |
| gundem.html | 503 | **NEUTRAL-INDICATOR** ⚠️ | `IMP.LOW` önem seviyesi rengi — yapısal olarak satır 463 (`sigCls`) ile birebir aynı 3-kollu renk-fonksiyonu deseni; **bağımsız doğrulama turunda MUTED-TEXT'ten düzeltildi** |
| gundem.html | 541 | MUTED-TEXT (sınırda) | haber kaynağı uppercase etiket — rozet-stilli (rgba arkaplan+border), `.badge-upcoming` ile yapısal benzer; hem sentez hem doğrulama "sınırda, CPO/Ozan onayı önerilir" diye işaretledi |
| hakkinda.html | 42 | MUTED-TEXT | `.back-btn` |
| hakkinda.html | 49 | MUTED-TEXT | `.top-nav-links a` |
| hakkinda.html | 87 | MUTED-TEXT | `.hero-sub` |
| hakkinda.html | 122 | MUTED-TEXT | `.stat-lbl` |
| hakkinda.html | 142 | MUTED-TEXT | `.feature-desc` |
| hakkinda.html | 158 | MUTED-TEXT | `.tech-desc` |
| hakkinda.html | 178 | MUTED-TEXT | `.market-card li` |
| hakkinda.html | 218 | NEUTRAL-INDICATOR | `.rl-todo` roadmap nötr durum |
| hakkinda.html | 239 | MUTED-TEXT | `footer a` |
| hakkinda.html | 322 | MUTED-TEXT | metodoloji açıklama paragrafı |
| hisse.html | 3019 | NEUTRAL-INDICATOR | `ageHexColor` else-dalı, sinyal-yaşı nötr varsayılan |
| hisse.html | 3138 | MUTED-TEXT | R/R satırı etiketi ("Sinyal başından") |
| hisse.html | 3142 | MUTED-TEXT | R/R satırı etiketi ("Şu an girersen") |
| hisseler.html | 42 | MUTED-TEXT | `.back-btn` |
| hisseler.html | 49 | MUTED-TEXT | `.top-nav-links a` |
| hisseler.html | 87 | MUTED-TEXT | `.hero-sub` |
| hisseler.html | 122 | MUTED-TEXT | `.stat-lbl` |
| hisseler.html | 142 | MUTED-TEXT | `.feature-desc` |
| hisseler.html | 158 | MUTED-TEXT | `.tech-desc` |
| hisseler.html | 178 | MUTED-TEXT | `.market-card li` |
| hisseler.html | 218 | NEUTRAL-INDICATOR | `.rl-todo` |
| hisseler.html | 239 | MUTED-TEXT | `footer a` |
| hisseler.html | 264 | MUTED-TEXT | `.hh-hero .hh-stat span` |
| hisseler.html | 283 | MUTED-TEXT | `.hh-tab` seçili olmayan sekme metni |
| hisseler.html | 297 | MUTED-TEXT | `.hh-count` sayaç rozeti metni |
| hisseler.html | 321 | MUTED-TEXT | `.hh-name` hisse adı ikincil metni |
| iletisim.html | 23 | MUTED-TEXT | `.back-btn` |
| iletisim.html | 27 | MUTED-TEXT | `.top-nav-links a` |
| iletisim.html | 37 | MUTED-TEXT | `.contact-lbl` |
| iletisim.html | 43 | MUTED-TEXT | `footer a` |
| iletisim.html | 73 | MUTED-TEXT | form label (Ad Soyad) |
| iletisim.html | 77 | MUTED-TEXT | form label (E-posta) |
| iletisim.html | 82 | MUTED-TEXT | form label (Konu) |
| iletisim.html | 92 | MUTED-TEXT | form label (Mesaj) |
| iletisim.html | 130 | MUTED-TEXT | başarı mesajı ikincil açıklama |
| index.html | 1322 | MUTED-TEXT | `.sig-tip-footer` |
| index.html | 1327 | MUTED-TEXT | `.sig-price` |
| index.html | 1337 | MUTED-TEXT | `.sl-pct` |
| index.html | 1537 | MUTED-TEXT | `.chart-loading` |
| index.html | 1620 | MUTED-TEXT | `.sig-date` |
| index.html | 1638 | MUTED-TEXT | `.alert-modal-row label` |
| index.html | 1646 | MUTED-TEXT | `.alert-modal-close` ikon rengi |
| index.html | 2484 | MUTED-TEXT | `<th>` "Hisse" |
| index.html | 2485 | MUTED-TEXT | `<th>` "Fiyat" |
| index.html | 2486 | MUTED-TEXT | `<th>` "Değişim" |
| index.html | 2487 | MUTED-TEXT | `<th>` "Sinyal" |
| index.html | 2488 | MUTED-TEXT | `<th>` "Tarih" |
| index.html | 2489 | MUTED-TEXT | `<th>` "Giriş ₺" |
| index.html | 2490 | MUTED-TEXT | `<th>` "SL ₺" |
| index.html | 2491 | MUTED-TEXT | `<th>` "Güç" |
| index.html | 2492 | MUTED-TEXT | `<th>` "İndikatörler" |
| index.html | 3156 | NEUTRAL-INDICATOR | `mChangeEl` değişim=0 nötr |
| index.html | 3639 | NEUTRAL-INDICATOR | `sentColor` "⚪ Yatay" nötr sentiment |
| index.html | 3936 | NEUTRAL-INDICATOR | `chgColor` artış/düşüş/nötr üçlemesi |
| index.html | 4086 | NEUTRAL-INDICATOR | haftalık trend "–" fallback |
| index.html | 4112 | NEUTRAL-INDICATOR | giriş fiyatı yok "—" |
| index.html | 4116 | NEUTRAL-INDICATOR | SL seviyesi yok "—" |
| index.html | 4124 | MUTED-TEXT | `sectorHtml` sektör adı |
| index.html | 5211 | NEUTRAL-INDICATOR | `sigColor` BEKLE (autocomplete) |
| index.html | 5291 | NEUTRAL-INDICATOR | `sigColor` BEKLE (tooltip başlığı) |
| index.html | 5323 | NEUTRAL-INDICATOR | "Trend henüz net değil" metni |
| karsilastir.html | 154 | NEUTRAL-INDICATOR | `.badge.bkl` BEKLE rozeti metin rengi |
| karsilastir.html | 220 | NEUTRAL-INDICATOR | `.mc-neu` makro nötr |
| karsilastir.html | 578 | NEUTRAL-INDICATOR | `verdictColor()` JS "Nötr" etiketi |
| kategori.html | 25 | MUTED-TEXT (tanım) | 🔴 şablon-yerel `:root { --text2:#8b949e }` |
| kategori.html | 26 | NEUTRAL-INDICATOR (tanım) | 🔴 aynı blok `--bkl:#8b949e` — `--text2` ile AYNI ham değer (çelişki, bkz §3) |
| metodoloji.html | 44 | MUTED-TEXT | `.back-btn` |
| metodoloji.html | 51 | MUTED-TEXT | `.top-nav-links a` |
| metodoloji.html | 108 | MUTED-TEXT | `.crit-desc` |
| metodoloji.html | 147 | NEUTRAL-INDICATOR | `.tldr-gray .tldr-label` |
| metodoloji.html | 167 | MUTED-TEXT | `footer a` |
| metodoloji.html | 187 | NEUTRAL-INDICATOR | `.mc-neu` |
| metodoloji.html | 335 | MUTED-TEXT | AL sinyal kutusu açıklama `<small>` |
| metodoloji.html | 340 | MUTED-TEXT | SAT sinyal kutusu açıklama `<small>` |
| ozet.html | 380 | MUTED-TEXT | loading placeholder metni |
| ozet.html | 628–638 (11 satır) | MUTED-TEXT | footer navigasyon linkleri (tek desen) |
| portfolio.html | 30 | MUTED-TEXT | `.page-sub` |
| portfolio.html | 32 | MUTED-TEXT | `.top-nav-links a` |
| portfolio.html | 41 | MUTED-TEXT | `.sum-lbl` |
| portfolio.html | 52 | MUTED-TEXT | `.add-lbl` |
| portfolio.html | 56 | MUTED-TEXT | `thead th` |
| portfolio.html | 67 | NEUTRAL-INDICATOR | `.signal-BEKLE` |
| portfolio.html | 71 | NEUTRAL-INDICATOR | `.neu-pnl` K/Z nötr üyesi |
| portfolio.html | 83 | MUTED-TEXT | `.btn-action` |
| portfolio.html | 138 | MUTED-TEXT | `footer a` |
| portfolio.html | 150 | MUTED-TEXT | `.xu030-compare` |
| portfolio.html | 167 | NEUTRAL-INDICATOR | `.mc-neu` |
| portfolio.html | 240 | DIGER | modal kapatma "×" ikon-buton rengi |
| portfolio.html | 242 | MUTED-TEXT | Cloud Sync modal açıklama |
| portfolio.html | 256 | MUTED-TEXT | "Aktif Token:" etiketi |
| portfolio.html | 259 | DIGER | kopyala ikon-buton rengi |
| portfolio.html | 268 | MUTED-TEXT | "Unut" butonu etiket rengi |
| portfolio.html | 273 | NEUTRAL-INDICATOR | `#cloudMsg` varsayılan renk |
| portfolio.html | 610 | MUTED-TEXT | tablo hücresi, pozisyon tarihi |
| portfolio.html | 614 | MUTED-TEXT | tablo hücresi, maliyet |
| portfolio.html | 704 | NEUTRAL-INDICATOR | `_setCloudMsg('Oluşturuluyor…')` |
| portfolio.html | 723 | NEUTRAL-INDICATOR | `_setCloudMsg('Yükleniyor…')` |
| portfolio.html | 747 | NEUTRAL-INDICATOR | `_setCloudMsg('Kaydediliyor…')` |
| portfolio.html | 768 | NEUTRAL-INDICATOR | `_setCloudMsg('Yükleniyor…')` |
| portfolio.html | 786 | NEUTRAL-INDICATOR | token-unutuldu bilgi mesajı |
| portfolio.html | 800 | NEUTRAL-INDICATOR | `_setCloudMsg` varsayılan fallback |
| sinyal_performans.html | 30 | MUTED-TEXT | `.page-sub` |
| sinyal_performans.html | 37 | MUTED-TEXT | `.stat-lbl` |
| sinyal_performans.html | 38 | MUTED-TEXT | `.stat-sub` |
| sinyal_performans.html | 43 | MUTED-TEXT | `.sec-head span` |
| sinyal_performans.html | 48 | MUTED-TEXT | `thead th` |
| sinyal_performans.html | 71 | MUTED-TEXT | `.computing` gövde metni |
| sinyal_performans.html | 76 | MUTED-TEXT | `.info-box` paragraf metni |
| sinyal_performans.html | 85 | MUTED-TEXT | `.ozet-metric-sub` |
| sinyal_performans.html | 91 | MUTED-TEXT | `.btn-run:disabled` |
| sinyal_performans.html | 94 | MUTED-TEXT | `footer a` |
| sinyal_performans.html | 111 | NEUTRAL-INDICATOR | `.mc-neu` |
| sinyal_performans.html | 150 | NEUTRAL-INDICATOR | aktif sinyal sayısı 0 ise nötr/gri ternary |
| sinyal_performans.html | 295 | MUTED-TEXT | `#perfFilterCount` |
| sinyal_performans.html | 333 | MUTED-TEXT | `.hm` ham tarih hücresi |
| tarama.html | 25 | MUTED-TEXT (tanım) | 🔴 şablon-yerel `:root { --text2:#8b949e }` |
| tarama.html | 26 | NEUTRAL-INDICATOR (tanım) | 🔴 aynı blok `--bkl:#8b949e` — çelişki |
| tarama.html | 178 | MUTED-TEXT | `var(--text2,#8b949e)` chip-x kapatma ikonu (fallback) |
| tarama.html | 193 | MUTED-TEXT | `var(--text2,#8b949e)` chip-clear-all etiketi (fallback) |
| varlik.html | 33 | MUTED-TEXT (tanım) | 🔴 şablon-yerel `:root { --text2:#8b949e }` |
| varlik.html | 34 | NEUTRAL-INDICATOR (tanım) | 🔴 aynı blok `--bkl:#8b949e` — çelişki |
| varlik.html | 386 | MUTED-TEXT | `#emaLegend` ikincil metin |
| varlik.html | 576 | DIGER | lightweight-charts JS `textColor` — canvas `var()` tüketemez (bilinen kısıt) |
| yasal.html | 23 | MUTED-TEXT | `.back-btn` |
| yasal.html | 27 | MUTED-TEXT | `.top-nav-links a` |
| yasal.html | 79 | MUTED-TEXT | `.clause-num` |
| yasal.html | 87 | MUTED-TEXT | `footer a` |
| yasal.html | 115 | DIGER | SVG ikon `stroke` (belge ikonu) |
| yasal.html | 147 | DIGER | SVG ikon `stroke` (kalkan ikonu) |
| yasal.html | 163 | DIGER | SVG ikon `stroke` (info-circle) |
| yasal.html | 179 | DIGER | SVG ikon `stroke` (kilit ikonu) |
| yasal.html | 189 | DIGER | SVG ikon `stroke` (zarf ikonu) |
| yasal.html | 197 | MUTED-TEXT | KVKK bilgilendirme paragrafı |

---

## 3. Şablon-Yerel `:root` Sapması — en kritik bulgu

**3 şablonda** (`kategori.html`, `tarama.html`, `varlik.html`) yerel `:root` bloğu hem `--text2` hem `--bkl`'yi **aynı ham değere** (`#8b949e`) sabitliyor:

| Dosya | `:root` blok | `--text2` satırı | `--bkl` satırı |
|---|---|---|---|
| kategori.html | ~22–28 | 25 | 26 |
| tarama.html | ~22–28 | 25 | 26 |
| varlik.html | ~30–37 | 33 | 34 |

Kanonik `tokens.css`'te bu ikisi **farklı** (`--bp-text2`=#c7c5cd, `--bp-bkl`=#909097) — bu 3 şablonda ayrım yok, tek tona ezilmiş. Bağımsız doğrulama ajanı `:root` içeren TÜM şablonları tarayıp bu çakışmanın **yalnızca bu 3 dosyada** olduğunu (kaçırılan 4. dosya yok) teyit etti.

**Latent/gizli bug:** kategori.html (~satır 80-82) ve varlik.html (~satır 121-124) kodun içinde zaten bilinçli bir ayrım kodlanmış — `.sig-badge.state-soon` (T7.5 veri-bekleyen rozeti) için yorum satırıyla açıkça "Bilerek `--bkl` DEĞİL `--text2`" deniyor ve `color:var(--text2)` yazılmış. **Ama** üstteki `:root` bloğu ikisini aynı değere eşitlediği için, bu bilinçli ayrımın **şu an hiçbir görsel etkisi yok** — kod niyeti var, render sonucu yok. Token'ları kanonik değerlerine ayırmak bu niyeti ilk kez görünür kılacak (yani 3 şablonda **görünür bir UI değişikliği** anlamına gelir, sessiz bir renk-kodu düzeltmesi değil).

**Diğer 17 şablonda** yerel `:root` override'ı yok — kanonik `tokens.css` tanımları ezilmeden geçerli, kullanımlar doğrudan inline/class seviyesinde.

**Kaç Flask rotası/URL etkileniyor: BİLİNMİYOR.** Bu tur route haritalaması yapmadı. Memory'deki `reference_sablon_yerel_root_palet_sapmasi.md`'de geçen "4 şablon, 16 rota/30 URL" rakamı **daha geniş bir palet-sapması denetiminden** geliyor ve bu turun 3-şablonluk text2/bkl-özel bulgusuyla birebir uzlaştırılmadı — aynı sayı sanılmamalı, ayrı bir doğrulama gerekir.

---

## 4. `_premium_modal.html` Durumu

**ÖLÜ DEĞİL — aktif yüzey.** İki bağımsız sınıflandırma grubu + doğrulama ajanı üçü de aynı sonuca ulaştı:

```
grep -n 'premium_modal' app.py            → sonuç yok (app.py'de referans yok)
grep -rln 'premium_modal' templates/*.html → templates/index.html
templates/index.html:5484: {% include '_premium_modal.html' %}
```

Koşulsuz include — index.html her render edildiğinde bu şablon da render ediliyor. Dosya kendi içinde 2 ham `#8b949e` kullanımı barındırıyor (ikisi de MUTED-TEXT, "durum" metinleri).

---

## 5. Migrasyon Fizibilitesi (yalnız değerlendirme — UYGULAMA DEĞİL)

**Mekanik olarak `--bp-text2`/`--bp-bkl`'ye eşlenebilir: 169/180 (%93.9)** — 128 MUTED-TEXT + 41 NEUTRAL-INDICATOR (6'sı kategori/tarama/varlik'teki tanım satırlarının kendisi).

**Ozan/CPO kararı gerektirenler:**
1. **DIGER — 11 kullanım:** SVG ikon `stroke` (yasal.html ×5), hover `border-color` (blog.html, blog_article.html ×2), ikon-buton rengi (portfolio.html ×2), canvas JS `textColor` (varlik.html) — metin/sinyal semantiği taşımıyor, `--bp-text2`/`--bp-bkl` ikilisine mekanik eşlenemez; ayrı bir token (`--bp-border-muted`/`--bp-icon-muted` gibi) veya vaka-bazlı karar gerekir.
2. **Sınırda vaka — gundem.html:541:** rozet-stilli haber-kaynağı etiketi, MUTED-TEXT'e bucket'landı ama hem sentez hem doğrulama "NEUTRAL-INDICATOR'a daha yakın, CPO onayı önerilir" diye işaretledi.
3. **En yüksek riskli 6 satır — kategori.html:25-26, tarama.html:25-26, varlik.html:33-34:** Bu token *tanımlarının kendisi*. Mekanik olarak `#8b949e`→`#c7c5cd`/`#909097` triviyal ama bu 3 dosyada `var(--text2)`/`var(--bkl)` kullanan **downstream tüketiciler bu turda envanterlenmedi** (kapsam yalnız ham-hex idi). Token'ları ayırmak §3'teki latent ayrımı görünür UI değişikliğine çevirir — ayrı bir `var(--text2\|--bkl)` tüketici taraması + görsel doğrulama + Ozan/CPO onayı gerekir, rollout öncesi.

---

## 6. Açık Riskler / Çelişkiler

- **Rota/URL etki sayısı bilinmiyor** — §3'te detaylandırıldı, ayrı doğrulama gerekir.
- **`var(--text2\|--bkl)` tüketici taraması eksik** — kategori/tarama/varlik için token ayrıştırma kararından önce yapılmalı.
- **DIGER kategorisi (11 satır) için token stratejisi tanımlı değil** — migrasyon bu satırları şu an kapsayamaz.
- **Sınırda vaka (gundem.html:541)** otomatik kabul edilmemeli, CPO/Ozan gözden geçirmeli.
- **Ayrı konuda, bu turda çözülmemiş açık çelişki:** Bağımsız doğrulama ajanı, S7 raporunun (memory + `0bd66aa`) "106 ham `#30363d`/16 şablon" rakamını kontrol amacıyla tazeledi ve **97** buldu (fark 9). Bu, bu turun `#8b949e` sonuçlarını etkilemiyor (farklı renk) ama S7'nin güncelliğine dair açık bir soru işareti — S7'den bu yana kod değişmiş olabilir ya da ölçüm kapsamı/yöntemi farklıydı. Ayrı bir hızlı-doğrulama turu önerilir, "106" rakamı bu haliyle güncel kabul edilmemeli.

---

## 7. Bağımsız Doğrulama Özeti

Doğrulama ajanı sentezi görmeden kendi grep'ini sıfırdan çalıştırdı:
- **Toplam sayım (180) ve 20 dosyanın her birinin kendi sayısı**: TAM EŞLEŞME, tutarsızlık yok.
- **Rastgele 3 dosya (bilanco_takvimi, portfolio, gundem) elle yeniden okundu**: bilanco_takvimi ve portfolio'nun tüm atamaları doğrulandı; **gundem.html'de 1 hata bulundu** — satır 503 (`IMP.LOW` önem-seviyesi rengi) yapısal olarak satır 463 (`sigCls`, doğru şekilde NEUTRAL-INDICATOR) ile birebir aynı 3-kollu renk-fonksiyonu deseni taşıyor ama sentezde yanlışlıkla MUTED-TEXT'e konmuştu. **Bu dokümanda düzeltildi** (§1, §2 tabloları güncel/doğru hali yansıtıyor: 128/41/11).
- **`_premium_modal.html` "ölü değil" iddiası**: DOĞRULANDI.
- **3 şablonlu `:root` çakışması, tam kapsam (4. dosya yok)**: DOĞRULANDI.
- **S7 `#30363d` sayısı (106) ile taze grep (97) arasında uyuşmazlık**: bulundu, bu turun kapsamı dışında bırakıldı, §6'da açık risk olarak kayda geçti.

Hiçbir dosya değiştirilmedi, hiçbir git komutu çalıştırılmadı — tüm işlem salt-okuma SSH grep/read idi.
