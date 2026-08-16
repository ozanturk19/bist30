# `${...}` Template-Literal "Sızıntısı" İddiası — Sınıflandırma Raporu (16.08.2026, DEV2-139)

**Kaynak backlog maddesi (Master Program, Bölüm 4, KÜÇÜK TEMİZLİK):**
> `templates/**/*.html` içindeki 38 (13 şablona yayılı) işlenmemiş `${...}` template-literal sızıntısı `<template>` etiketine taşınsın — crawler'lar bunları sahte link sanıp 404 üretiyor.

**Yöntem:** S1/S7/T3.4/T5.2/T5.4/T8-tipografi/T8-başlık/T1.5/anasayfa-yük/api-macro/api-data ile aynı desen. Workflow ile 4 paralel salt-okur sınıflandırma ajanı (17 dosya 4 gruba bölünmüş, birbirini görmedi, her aday satırı `<script>` blok aralığına göre elle sınıflandırdı) → 1 sentez ajanı → 1 tamamen bağımsız kör doğrulama ajanı (sentezi görmeden kendi `grep -c` + script-blok-aralığı turunu sıfırdan yaptı, rastgele satırları elle açtı).

## Sonuç — İDDİA GEÇERSİZ (sayı hatası değil, mekanizma hatası)

| Metrik | İddia | Ölçülen (payda: TÜM eşleşmeler, örneklem değil) |
|---|---:|---:|
| Satır sayısı | 38 | **463** |
| Dosya sayısı | 13 | **17** |
| GERÇEK-SIZINTI-HTML-METİN (script-dışı, işlenmemiş) | (iddia edilen tüm 38'i) | **0** |
| SCRIPT-İÇİ-MEŞRU (JS backtick template literal) | 0 | **463 (%100)** |

**463/463 satırın tamamı bir `<script>...</script>` bloğu içinde geçen JS backtick template literal kullanımı** (`` `<div>${x}</div>` `` kalıbı, çoğunlukla `.innerHTML`/`.textContent` atamasına kaynak). Bağımsız doğrulama ajanı, her dosyanın `<script>`/`</script>` satır aralıklarını çıkarıp 463 eşleşmenin tamamını bu aralıklarla eşleştirdi — istisna sıfır. Ayrıca dosya bazlı `grep -c` sayıları iki bağımsız ölçümde birebir eşleşti (463/463).

**İddianın mekanizması teknik olarak imkânsız:**
1. `${...}` Jinja2 syntax'ı değil — Jinja değişken interpolasyonu `{{ }}` kullanır. Jinja bu satırları hiç görmez/"işlemez" çünkü zaten kendi sözdizimi değil.
2. `<script>` içeriği tarayıcıda DOM'a link/attribute olarak parse edilmez, JS motoruna gönderilir; `${s.ticker}` yalnızca JS çalıştıktan SONRA gerçek değerle değişip `innerHTML` üzerinden DOM'a yazılır — kaynak HTML'de literal `${...}` metni crawler'a hiç gitmez.
3. JS çalıştırmayan crawler'lar script gövdesini opak metin bloğu sayar, içindeki string literal'leri href olarak izlemez.
4. JS çalıştıran crawler'lar (Googlebot) DOM render sonrası zaten tamamlanmış gerçek URL'leri (`/hisse/THYAO`) görür, `${s.ticker}` değil.

"Sahte link → 404" senaryosunun gerçekleşebileceği hiçbir kanal yok.

## Tekrarlayan desen not

Bu, S7 (104→98), `/api/macro` (17→15 sayfa, 60s→180s) ve `/api/data` (blog_article.html iddiası zaten çözülmüş) ile aynı sınıfın dördüncü örneği ama en keskin biçimi: öncekiler sayı/güncellik hatasıydı, bu seferki hem sayı hem **mekanizma** yanlış — iddia edilen bug türü zaten var olamaz.

## Ek gözlem — kod kalitesi (aksiyon önerisi değil, yalnız kayıt)

`loadMacroBar()` fonksiyonu (makro ticker şeridi) 8 şablonda (bilanco_takvimi, blog, blog_article, ozet, portfolio, sektor_harita, sinyal_performans, metodoloji) karakter karakter aynı minify tek-satır JS olarak tekrarlanıyor — T1.7/format-lint kapsamı dışında, T5.x komponent kütüphanesi çalışmasıyla ilgili olabilecek bir gözlem, ayrı bilet açılmadı.

## Sonuç

Aksiyon gerekmiyor — kod tarafında hiçbir değişiklik yok, gerçek sızıntı sıfır. Master Program'daki KÜÇÜK TEMİZLİK maddesi "SINIFLANDIRMA TAMAM, İDDİA GEÇERSİZ" notuyla kapatıldı.
