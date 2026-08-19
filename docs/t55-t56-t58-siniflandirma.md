# T5.5 / T5.6 / T5.8 — Sınıflandırma Raporu (KOD DEĞİŞMEDİ)

**Yöntem:** S1/S7/T3.4/T5.2/T5.4/T8/T1.5 deseni — 3 paralel sınıflandırma ajanı + her kalem için ayrı bağımsız kör doğrulama ajanı. T5.5'te doğrulama sınıflandırmayı reddetti (düzeltilmiş rakamlarla aşağıda), T5.6/T5.8'de doğrulama birebir mutabık kaldı.

---

## T5.5 — Tooltip komponenti (SIFIRDAN, dokunmatik destekli)

**Backlog iddiası:** "125× title=, mobilde ölü, SIFIRDAN 9 gün, focus/touchstart ile açılır."

**DURUM: KISMEN — rakam ve "sıfırdan" öncülü çürütüldü, gerçek kapsam daraltılmalı**

**Doğrulanmış rakamlar (bağımsız kör doğrulama turundan sonra):**
- Gerçek `title=` occurrence sayısı: **104** (125 değil — %20 abartı; ilk sınıflandırmanın çıkardığı 106 da 2 sahte-pozitif içeriyordu: `data-title=`, `hdr_title=` Jinja değişkeni).
- span/div/li/th üzerinde (tıklanamaz, dokunmatikte native fallback'i sıfır — gerçek "içerik yalnız hover'da" tooltip): **44** (span 30 + div 12 + li 1 + th 1).
- button/a üzerinde (ikincil ipucu, click zaten birincil eylemi yapıyor): **58**, bunların **12**'si zaten `aria-label` ile ikilenmiş (ekran okuyucu etkilenmiyor).
- Native form elemanı (`input`/`select`/`option`/`textarea`) üzerinde `title=`: **0**.
- En yoğun 5 şablon: index.html 40, hisse.html 22, portfolio.html 10, tarama.html 9, sinyal_performans.html 7.

**Kritik düzeltme — PageInfoPanel iddiası YANLIŞ:** İlk sınıflandırma "proje zaten dokunmatik-native, 3 sayfada onaylı bir PageInfoPanel komponenti taşıyor, sıfırdan gerekmeyebilir" demişti. Bağımsız doğrulama bunu **çürüttü**: `static/js/page-info-panel.js`/`.css` **hiçbir şablonda yüklenmiyor** (`grep -rln templates/` = 0 sonuç), yalnızca bir Playwright smoke-test dosyasında (`tests/test_page_info_panel.spec.js`) çağrılıyor; iddia edilen 3 sayfadan biri (`gucu.html`) codebase'de mevcut değil; kod içi yorum entegrasyonun **gerçekleştiğini değil**, onay olmadan gerçekleşMEyeceğini belirten ileriye-dönük bir kapı notu. Yani proje bugün **hiçbir çalışan tooltip/popover altyapısına sahip değil** — `grep -in 'tooltip\|popover\|data-tip' static/js/*.js static/css/*.css` tek eşleşme veriyor: kullanılmayan ölü token `--bp-z-tooltip: 9000` (tokens.css:318, sıfır tüketici).

**Değerlendirme:** Gerçek kullanıcı-değeri kaybı olan nokta sayısı 104/125 değil, **~44** (RVOL/backtest/Sharpe/Drawdown/Profit Factor/anomali-nedeni/skor-metodolojisi gibi başka hiçbir yerde görünmeyen finansal bilgi). Kalan 58'i büyük ölçüde buton/link üzerinde ikincil ipucu, düşük risk. "SIFIRDAN 9 gün" tahmini bu daraltılmış paydaya göre yeniden ölçülmeli; PageInfoPanel canlı/onaylı olmadığı için "mevcut komponenti genişlet" argümanı da zayıf bir temele dayanıyor (entegrasyon + Ozan onay süreci baştan yapılmalı).

**Öneri (implementasyon değil):** (a) Backlog rakamını 104 + 44/58 kırılımıyla düzelt. (b) Kapsamı yüksek-değerli ~44 noktaya daraltmayı değerlendir. (c) PageInfoPanel'in "zaten onaylı" olmadığını not düş — CSS/JS iskeleti yeniden kullanılabilir olsa da entegrasyon işi baştan yapılmalı. (d) 58 buton/link title'ının çoğu bu kalem kapsamı dışında bırakılabilir. Nihai kapsam/süre kararı CPO/Ozan'da.

---

## T5.6 — Tablo→kart dönüşümünü tüm liste sayfalarına yay

**Backlog iddiası:** "bugün yalnız 2/10 (index, tarama), /gucu-yuksek + /sinyal-performans + /portfolio kart görünümü kazanır."

**DURUM: SINIFLANDIRMA TAMAM — backlog paydası (10) hatalı, gerçek kapsam 2 sayfa. Bağımsız doğrulama birebir mutabık.**

**Doğrulanmış durum:**
- **Zaten tablo+mobil-kart (DONE):** index.html, tarama.html — gerçek `@media(max-width:768px)` ile masaüstü-tablo/mobil-kart ikilisi.
- **Redirect, ayrı şablon YOK:** `/gucu-yuksek` → 301 `/tarama` (T4.2, 15.08, `562a531`) — backlog'un "/gucu-yuksek kart görünümü kazanır" maddesi geçersiz öncüle dayanıyor, zaten /tarama'nın mobil kartını miras alıyor.
- **Zaten kart, tablo hiç olmamış:** ozet.html, gundem.html, bilanco_takvimi.html — üçü de `.stock-card`/`.stock-grid`, sıfır `<table>` (T5.4 raporu bunları zaten card ailesinde sınıflandırmıştı).
- **Gerçek T5.6 adayı — yalnız 2 sayfa:** sinyal_performans.html (2 `<table>`, `overflow:hidden` — scroll değil **kırpma**, 7 kolonlu tablo mobilde 6 kolon kalıyor) ve portfolio.html (1 `<table>`, `overflow:hidden`, 12 kolondan 9'u mobilde kırpılmış konteynerde kalıyor — kullanıcının kendi finansal pozisyon verisi, en yüksek risk).
- **Kapsam dışı bırakılmalı:** karsilastir.html (kasıtlı `overflow-x:auto` yatay-kaydırma, "karşılaştırma" semantiği farklı), hisseler.html (tablo yok, SEO link-dizini), sektor_harita.html (tablo hiç olmamış, tile/heatmap deseni).

**Öneri (implementasyon değil):** (1) Backlog paydasını "10" yerine gerçek kapsamla (7 gerçek liste-sayfası adayı, 5'i zaten kart, 2'si saf tablo) düzelt, "/gucu-yuksek" maddesini kaldır. (2) Gerçek iş: yalnız sinyal_performans.html + portfolio.html, öncelik portfolio (daha yüksek risk). (3) Migrasyondan önce marka/tasarım kararı gerekiyor: yeni kartlar `.mc` (index) mi `.mr-card` (tarama) mı temel alınsın — üçüncü/dördüncü bağımsız varyant T5.4'ün zaten işaretlediği card-ailesi driftini büyütür, kanonik seçim önerilir. (4) Sonraki adım implementasyon değil, portfolio/sinyal_performans için ayrı mockup/tasarım turu (CPO/Ozan onayı gerektirir, özellikle portfolio'da K/Z gibi karar-kritik alanların kart düzeni).

---

## T5.8 — Heatmap sıfırdan yeniden yazım

**Backlog iddiası:** "hücreler `<a href>` içinde, aria-label, tooltip focus/touch, kontrast kalibrasyonu, tier→üçlü dönüşüm, 215 hücrenin tamamı erişilir, T3.4 bağımlılığı."

**DURUM: SINIFLANDIRMA TAMAM — backlog'un hedef sayfası artık yok, öncül geçersiz. Bağımsız doğrulama birebir mutabık.**

**Doğrulanmış durum:**
- T4.1 (`723278c`, 15.08) `/heatmap` route'unu ve `templates/heatmap.html` + `static/js/heatmap.js`'i **tamamen sildi** — `/heatmap` artık `/sektor-harita`'ya 301. Silinen eski heatmap.html gerçekten backlog'un tarif ettiği yapıdaydı (215 hücrelik SVG treemap, sıfır aria-label, tier tabanlı Premium/Plus/Standart renk lejantı) — ama o sayfa artık kod tabanında yok.
- Hayatta kalan `/sektor-harita` tamamen farklı bir desen: 215 hücre değil, **12 sektör kartı** ana etkileşim birimi, her biri `div[role=link][tabindex=0]` + click/keydown(Enter) — **zaten klavye+dokunmatik erişilebilir**. Yalnız `aria-label` eksik (title= var, aria-label yok — 12 kart).
- Sektör kartı içindeki hisse-chip'leri: AL+SAT sinyalli 52 hisse her zaman `<a href>`; BEKLE'li 163 hisseden yalnız sektör başına ilk 6'sı link, kalan **101 hisse (%47, tamamı BEKLE)** yalnız statik "+N" metni — doğrudan link/tabindex yok (sektör kartı üzerinden `/tarama?sector=X`'e dolaylı erişim var).
- "Kontrast kalibrasyonu" maddesi zaten `docs/faz8-kart-zemin-siniflandirma.md`'de (1.047:1, SIFIR-AYRIM kovası) site-geneli bir kalem olarak sınıflandırılmış — T5.8 altında tekrarlamak mükerrer iş.
- "tier→üçlü dönüşüm" maddesi bu sayfada **anlamsız**: sektor_harita.html tier alanını/💎⭐ hiç kullanmıyor, yalnız is_premium (tek alan, zaten token'lı pill-prem class'ında). Dönüştürülecek tier kodu yok — T3.4 bağımlılığı bu sayfa için fiilen ortadan kalkmış.

**Öneri (implementasyon değil):** (1) T5.8'i olduğu haliyle KAPATILMIŞ/GEÇERSİZ işaretle — hedef sayfa T4.1 ile zaten kaldırıldı. (2) Gerçek kalıntı varsa çok daha dar yeni bir kalem aç: "sektor_harita.html: 12 sector-card'a aria-label ekle + 101 gizli BEKLE hissesine erişim kararı (tam liste linki mi, +N span'i link yapmak mı)". (3) Kontrast ve tier maddelerini T5.8'den tamamen çıkar (ilki başka yerde zaten kapsanıyor, ikincisi hedefsiz). (4) Nihai karar CPO/Ozan'a: "ÇÖZÜLDÜ (öncül geçersiz)" mü, yoksa dar aria-label/BEKLE-erişim kalemi mi yeni ticket olsun.

---

## Genel özet

Üç kalemin de ortak deseni: backlog rakamları/öncülleri bayat (T5.5: rakam abartılı + varsayılan altyapı canlı değil; T5.6: payda yanlış, /gucu-yuksek zaten birleşmiş; T5.8: hedef sayfa tamamen kaldırılmış). Gerçek açık iş yükü backlog'un ima ettiğinden küçük: T5.5 için ~44 gerçek nokta (106/125 değil), T5.6 için 2 sayfa (10 değil), T5.8 için tek-şablon küçük ek (sıfırdan yeniden yazım değil). Üçünde de kod değişmedi; migrasyon/implementasyon kararları CPO/Ozan onayı gerektiriyor, karar kuyruğuna eklenmeleri öneriliyor.
