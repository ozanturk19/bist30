# T1.5 — Ham `#161b22` / `#0d1117` Sınıflandırması (GitHub-legacy palet, KOD DEĞİŞMEDİ)

**Tarih:** 16.08.2026 · **Kapsam:** Yalnız sınıflandırma — S7 (`#30363d`) ve T1.5-8b949e (`#8b949e`) ile aynı yöntem, T1.5'in geri kalan iki GitHub-legacy arka plan/yüzey rengi için. Bu turda hiçbir CSS/HTML/JS değişmedi; migrasyon kararı bu doküman ışığında CPO/Ozan onayına bağlı.

## Kaynak veri

```
grep -rn '#161b22' templates/ static/  →  48 ham kullanım, 15 şablon
grep -rn '#0d1117' templates/ static/  →   6 ham kullanım,  3 şablon (index.html, portfolio.html, static/maintenance.html)
```

Yöntem: 4 paralel sınıflandırma ajanı (15 dosya 4 gruba bölünmüş, salt-okur SSH grep+read, birbirini görmedi) → 1 sentez ajanı → 1 tamamen bağımsız doğrulama ajanı (sentezi görmeden kendi grep'ini sıfırdan çalıştırdı, 9 satırı elle açıp bağlamını yeniden okudu). Doğrulama **ONAY** verdi — sıfır düzeltme, hiçbir kova ataması/satır no hatası bulunmadı. (Sentezin kendi ilk taslağı Grup A'nın metin özetinde 9 vs 8 satır tutarsızlığı fark edip kendi kendini düzeltti; 48/6 toplamlarını etkilemedi.)

## Sonuç tablosu

| Kova | Satır | Dosya | Not |
|---|---|---|---|
| **STATİK-ARKAPLAN** | 44 | 11 | Kart/panel/header/tablo/input resting-state background — en büyük kova |
| **GRADIENT/DEKORATIF** | 4 | 3 | Skeleton shimmer `linear-gradient` stopları (blog_article.html:350-351, gundem.html:159, karsilastir.html:184) — resting bg değil |
| **HARİÇ — şablon-yerel `:root`** | 4 | 4 | tarama.html:23, kategori.html:23, varlik.html:31 (`--surface:#161b22`), static/maintenance.html:10 (`--bg:#0d1117`, tokens.css'e hiç bağlı değil, T1.6'nın diğer örneklerinden bile daha izole) — T1.6 kapsamı, burada dokunulmadı |
| **KONTRAST-METİN** (yeni kova) | 2 | 1 | index.html:1083 (`.active-today`), :1240 (`.adv-chip.adv-active`) — `background` değil `color`, altın/marka rengi zemin üzerinde okunabilirlik metni. S7/T1.5-8b949e şemasındaki hiçbir kovaya uymadığı için yeni tanımlandı |
| **TOPLAM** | **54** | 17 (tekil) | 48 (#161b22) + 6 (#0d1117), gruplar arası çapraz kontrol ✅, bağımsız doğrulama ✅ |

Bu turda **HOVER, DISABLED, HARİÇ-kanonik-tanım** kovalarına giren satır yok — S7/T1.5-8b949e'nin aksine, çünkü bu iki renk sistematik olarak `background` (border/text değil), kart hover'ları farklı hex'lere geçiyor (örn. `#1c2128`, ayrı bir tur konusu).

## Öne çıkan bulgular

- **"header" deseni 8 şablonda birebir tekrarlıyor**: `header{background:#161b22}` — blog_article, yasal, gizlilik, blog, hisseler, iletisim, metodoloji, hakkinda.
- **hisseler.html ve hakkinda.html neredeyse birebir kopya**: `.stat-box`(115), `.feature-card`(132), `.tech-card`(152), `.market-card`(168), `.method-box`(183) — aynı selector, aynı satır numaraları, iki dosya, tümü `#161b22`. Copy-paste kökeni güçlü kanıt; tek sed/regex iki dosyada aynı anda uygulanabilir.
- **portfolio.html'de iki-katmanlı derinlik sinyali**: dış modal (`#cloudModalDialog`, satır 239) `#161b22`, iç input + iç-içe kutu (satır 250/257) `#0d1117`. Kanonik `--bp-surface2`/`--bp-surface3` üç-katmanlı hiyerarşinin fiilen ihtiyaç duyulduğu tek somut örnek.
- **T5.4 bulgusuyla örtüşme doğrulandı**: T5.4 önceden "card ailesinin ~yarısı kanonik `#141416` yerine `#161b22`/`#30363d` gösteriyor" demişti — bu tur en az 16 farklı card-ailesi selector'ının 12 şablonda ham `#161b22` kullandığını doğruladı.
- **index.html'deki `#0d1117`'nin 2/3'ü arka plan migrasyonunun kapsamı dışında** — gerçekte `color:` (metin), background değil.

## Renk mesafesi — kanonik token adayları

| Ham hex | RGB | En yakın kanonik token | Öklid mesafesi | Diğer aday |
|---|---|---|---|---|
| `#161b22` | (22,27,34) | **`--bp-surface2` `#1c1b1f`** (28,27,31) | **6.7** | `--bp-surface` `#141416` → 14.0 (2× uzak) |
| `#0d1117` | (13,17,23) | **`--bp-bg` `#0e0e12`** (14,14,18) | **5.9** | `--bp-surface` `#141416` → 7.7 |

`#161b22` görsel olarak `--bp-surface` ile `--bp-surface2` arasında duruyor ama sayısal olarak surface2'ye belirgin şekilde daha yakın — T5.4'ün "kartlar kanonikten sapıyor" gözlemiyle tutarlı (kartlar bugün kanonik surface'ten daha açık bir tona oturuyor).

## Öneri (uygulama DEĞİL, yalnız öneri — S1/S7 deseniyle birebir)

1. **STATİK-ARKAPLAN (44 satır, 11 dosya) → `--bp-surface2` adayı.** Renk mesafesi en yakın seçenek, ancak bu kartların bugünküne göre biraz daha açık bir tona kayması demek. **CPO/Ozan kararı gerekiyor**: görsel hedef `--bp-surface` (koyulaşır, T5.4'ün "olması gereken" dediği değer) mi yoksa `--bp-surface2` (renk mesafesi olarak en sadık) mi? "header" (8 dosya) + "kopya kart seti" (hisseler+hakkinda, 10 satır) tek kararla toplu migre edilebilir — en yüksek etki/efor oranı burada.
2. **GRADIENT/DEKORATIF (4 satır, 3 dosya) → otomatik migrasyon riskli**, ayrı görsel QA gerektirir (shimmer kontrastı/görünürlüğü token'a geçince değişebilir).
3. **HARİÇ-şablon-yerel-:root (4 satır) → T1.6'ya devredilir**, bu turun kapsamı dışı. `maintenance.html` özel not: tokens.css'e hiç bağlı değil, T1.6'nın diğer 3 örneğinden (tokens.css'i kısmen kullanıp yalnız `--surface`'i yerelde ham hex bırakan) bile daha köklü bir istisna — T1.6 içinde ayrı alt-görev olarak ele alınmalı.
4. **KONTRAST-METİN (2 satır) → arka plan/yüzey migrasyonunun kapsamı dışında bırakılmalı.** CPO kararı gerekiyor: yeni bir "vurgu-zemini-üzerinde-metin" tokenı (örn. `--bp-on-accent`) mi tanımlanmalı, yoksa ham hex kontrast garantisi nedeniyle bilinçli mi kalmalı?
5. **portfolio.html'in iki-katmanlı kullanımı → CPO'ya özel işaretlendi.** Migrasyon pilotu için aday: dış modal → surface2, iç input/kutu → surface3.
6. **`#0d1117`'nin kalan STATİK-ARKAPLAN kullanımları (index.html:1639, portfolio.html:250/257) bağlama göre ayrışıyor.** Sayısal en yakın `--bp-bg` olsa da hiçbiri sayfa zemini değil (nested input/kutu) — derinlik semantiği `--bp-surface3` ile daha tutarlı olabilir, görsel QA ile teyit önerilir (n=3, tek dosya ağırlıklı örneklem, ham RGB mesafesi tek başına yanıltıcı olabilir).

## Bağımsız doğrulama özeti

Ayrı bir ajan SSH ile veriyi sıfırdan yeniden üretti: `grep -rn` ile 48+6=54 satırın tamamı, dosya bazlı `grep -c` toplamlarıyla tek tek eşleşti (54/54, sıfır fark), 9 satır elle açılıp bağlamı yeniden okundu (hepsi kova atamasıyla uyumlu bulundu), renk mesafesi hesapları bağımsız olarak makul değerlendirildi. **Sonuç: ONAY, düzeltme gerekmedi.**

## Ayrı bulgu — S7 (`#30363d`) toplam sayısı düzeltmesi

Bu turun hazırlığı sırasında (klasik grep, ajan dışı) S7 raporunun (14.08, `docs/faz8-s7-30363d-siniflandirma.md`) kendi baseline commit'i (`0bd66aa`) üzerinde bile taze `grep -rn '#30363d' templates/ static/` ile **98** satır verdiği, raporun kova toplamının (88+9+1+3+1+2=**104**) buna göre **6 fazla** olduğu doğrulandı. 14 dosyanın hiçbiri o commit'ten bu yana değişmemiş (dosya bazlı diff sıfır) — yani bu bir **kod driftı değil, S7 raporunun kendi aritmetiğindeki orijinal bir hata** (rapor yazıldığı andan itibaren mevcut). T1.5-8b949e'nin (DEV2-134) bağımsız doğrulama turunda not düşülen "106 vs 97" rakamları da bu gerçek 104-vs-98 farkının yanlış hatırlanmış bir biçimi görünüyor — ikisi de doğru sayı değil. **Doğru taban: 98 kullanım / 14 şablon.** S7'nin kendisi kod değiştirmediği (yalnız sınıflandırma) için canlı etkisi yok; ancak S7'nin migrasyon kararı ileride onaylanırsa, uygulama öncesi 98/14 üzerinden taze bir tek-satır doğrulama yapılmalı, 104 rakamı referans alınmamalı.

## Sıradaki

Kalan sınıflandırılmamış GitHub-legacy renk adayı yok — T1.5'in 4 ana rengi (`#0d1117`, `#161b22`, `#30363d`, `#8b949e`) artık hepsi SINIFLANDIRMA TAMAM durumunda. Migrasyon kararlarının kendisi (bu doküman + S7 + T1.5-8b949e) aynı karar kuyruğuna eklenmeli, CPO/Ozan onayı bekliyor.
