# T2.4 — 769-900px Desktop Nav Boşluğu Sınıflandırması

**Backlog maddesi (07.08.2026, Master Dönüşüm Programı FAZ2):**
> "769-900px nav boşluğu kapat (kanonik kırılım 900px'te tek); `/heatmap` ve `/profil`'e desktop nav SIFIRDAN ekle (bugün 769px'in ÜSTÜNDE bile hiç yok). Kabul ölçütü: 769/820/834/899px'te en az bir nav yüzeyi görünür — otomatik testle."

**Yöntem:** 2 bağımsız paralel salt-okur SSH ajanı (birbirini görmeden, farklı yaklaşımla) → 1 sentez ajanı → 1 tamamen bağımsız kör doğrulama ajanı (kendi sıfırdan araştırmasını yapıp sentezle karşılaştırdı). S1/S7/T3.4/T5.2/T5.4/T8-serisi/T1.5-serisi/api-macro/api-data/template-literal/mono-font/kart-zemin ile aynı desen. Sonuç: **sıfır anlaşmazlık**, doğrulama ajanı "ONAY" ile başladı.

## SONUÇ: İDDİA GEÇERSİZ / ZATEN ÇÖZÜLMÜŞ

Backlog maddesi 07.08.2026'da loglanmış, **2 gün sonra** (`5f85b93`, 09.08.2026 11:26 UTC, "feat(t2.4): 769-900px nav bosluk kapatildi + /heatmap, /profil desktop nav") ayrı ve hedefli bir commit ile kapatılmış — T2.2'nin (kanonik kabuk) yan etkisi değil. Sonrasında `/heatmap` sayfası T4.1 kapsamında (`723278c`, 15.08.2026 05:16 UTC) tamamen kaldırılıp `/sektor-harita`'ya 301 redirect'e çevrilmiş. Her iki commit de HEAD'in (`cf5701f`) atası (`git merge-base --is-ancestor` ile doğrulandı).

### 1) Kök neden — eski uyumsuzluk
`5f85b93` öncesi: `.bp-main-nav` (masaüstü) 900px'te gizleniyordu, `.mobile-bottom-nav` (mobil alt bar) ise 768px'te gizleniyordu — 769-900px aralığında İKİSİ DE gizliydi (gerçek boşluk). `5f85b93` mobil alt nav eşiğini 768→900px'e çekerek iki nav yüzeyini tek kırılımda senkronize etti.

### 2) Canlı doğrulama — repo'nun kendi test script'i
`tools/check_t24_nav_gap.py` (backlog maddesinin öngördüğü otomatik test, `5f85b93` ile birlikte gelmiş) iki bağımsız çalıştırmada karakter karakter aynı çıktıyı verdi:
```
[_mobile_nav_partial.html] .mobile-bottom-nav görünürlük eşiği: [900]
[.bp-main-nav / .header-nav kullanan şablon sayısı]: 21 — Tümü max-width:900px ile hizalı (sapma yok)
[profil.html] _header.html include: True | _mobile_nav_partial.html include: True | .bp-main-nav CSS present: True
PASS: 0 sayfa nav'siz kalıyor
```

### 3) 21 şablon — tek desen, istisnasız
Her biri kendi `<style id="bp-critical-css">` bloğunda `@media (max-width:900px){.bp-main-nav{display:none}}` taşıyor (satır numaraları iki ajan tarafından ayrı ayrı doğrulandı, birebir eşleşti):
bilanco_takvimi.html:174, blog_article.html:235, blog.html:79, gizlilik.html:41, gundem.html:205, hakkinda.html:248, hisse.html:1192, hisseler.html:248, iletisim.html:46, index.html:1915, karsilastir.html:312, kategori.html:135, metodoloji.html:189, ozet.html:262, portfolio.html:169, profil.html:179, sektor_harita.html:269, sinyal_performans.html:113, tarama.html:433, varlik.html:304, yasal.html:92.

`_mobile_nav_partial.html:105-106` → `@media (max-width:900px){.mobile-bottom-nav{display:block}}`. Tek kanonik kırılım: **900px**.

### 4) /heatmap
`templates/heatmap.html` fiziksel olarak yok. `app.py:4240-4242` route hâlâ var ama yalnız `return redirect("/sektor-harita", code=301)`. `/sektor-harita` (`sektor_harita.html`) `{% extends '_base.html' %}` kullanıyor, nav tam. Backlog'un bu kısmı artık **moot** (sayfa yok).

### 5) /profil
`profil.html:1` → `{% extends '_base.html' %}`. Satır 179 diğer 20 şablonla birebir aynı critical-CSS. Satır 182 `{% include '_header.html' %}` (masaüstü nav), satır ~385 `{% include '_mobile_nav_partial.html' %}` (mobil nav). Çatışan kural yok, tek tanım noktası.

### 6) Kapsam dışı, düşük öncelikli yan bulgu (aksiyon alınmadı)
3 şablonda kullanılmayan ("ölü") nav CSS kalıntısı var — tanımlı ama karşılık gelen eleman yok, işlevsel etkisi sıfır:
- `hisse.html:342-377` — `.header-nav{...}` (0 kullanım)
- `varlik.html:267-302` — `.header-nav{...}` (0 kullanım)
- `ozet.html:72-76` — `.top-nav-links{...}` (0 kullanım)

T2.4 kapsamının parçası değil, kod değiştirmeyen bir "ölü CSS temizliği" fırsatı olarak not düşüldü — ayrı bilet açılmadı.

## Öneri
Master Dönüşüm Programı FAZ2 tablosunda T2.4 satırı **"TAMAMLANDI (09.08.2026, `5f85b93`)"** olarak işaretlensin; `/heatmap` referansı "T4.1'de kaldırıldı (`723278c`), nav'lı `/sektor-harita`'ya 301 yönlendiriliyor" notuyla güncellensin.

Kod tarafında hiçbir değişiklik gerekmiyor — bu yalnızca backlog/rapor kapama işlemi.
