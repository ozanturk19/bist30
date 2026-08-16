# T5.2 — sig-badge/signal-badge Kod Tekrarı Sınıflandırması (KOD DEĞİŞMEDİ)

**Tarih:** 16.08.2026 · **Kapsam:** Yalnız sınıflandırma + konsolidasyon fizibilite önerisi (DEV2-129'un bağımsız denetiminde bulduğu "T5.2 gerilemiş" bulgusunun devamı — CPO'ya kod-değiştirmeyen envanter adımı olarak sunuldu, ayrı onay istenmedi, S1/S7/T3.4/FAZ8-6-8 deseniyle aynı). Bu turda hiçbir CSS/HTML/JS değişmedi.

## Kaynak veri

```
grep -rln '\.sig-badge\b' templates/*.html   →  4 şablon: bilanco_takvimi, kategori, tarama, varlik
grep -rln '\.signal-badge\b' templates/*.html →  3 şablon: hisse, index, portfolio
```

Workflow: 7 paralel ajan (her biri yalnız kendi şablonuna baktı, birbirini görmedi) → 1 sentez/sınıflandırma ajanı → 1 bağımsız doğrulama ajanı (7 dosyayı iddiaya bakmadan sıfırdan yeniden grep'ledi + `tokens.css`'i doğrudan okudu). Doğrulama turu **DUZELTME_GEREKLI** verdi, 2 gerçek hata buldu (aşağıda), ikisi de bu dokümanda düzeltilmiş haliyle yer alıyor. CPO tarafında da `tokens.css` + 3 şablonun `:root` bloğu bağımsız olarak (üçüncü kez) doğrudan okunarak teyit edildi.

## Sonuç tablosu

| Dosya | Aile / isim | Base tanım satırı | Varyant sayısı (aktif+ölü) | state-soon | bull/bear/neutral (ölü) | Renk yöntemi | Markup kullanım | Case convention |
|---|---|---|---|---|---|---|---|---|
| bilanco_takvimi.html | `.sig-badge` | 104-107 | 3 (al/sat/bkl) | Yok | Yok | ham RGB + `var(--bp-al/sat/bkl)` (FARKLI token öneki) | 1 | lowercase (`sig-al`) |
| kategori.html | `.sig-badge` | 76 | 4 (AL/SAT/BEKLE + state-soon) | Var | Yok | ham RGB + `var(--al/sat/bkl)` (yerel override) | 1 statik + 3 JS-dinamik | UPPERCASE |
| tarama.html | `.sig-badge` | 263-266 | 3 (AL/SAT/BEKLE) | Yok | Yok | kategori ile birebir aynı | 2 | UPPERCASE |
| varlik.html | `.sig-badge` | 110-113 | 7 (AL/SAT/BEKLE + state-soon + bull/bear/neutral) | Var | Var (3, ölü) | kategori/tarama ile aynı + büyük boyut varyantı | 4 | UPPERCASE |
| hisse.html | `.signal-badge` | 379-386 | 6 (AL/SAT/BEKLE + bull/bear/neutral) | Yok | Var (3, ölü) | yarı tokenize; SAT metni ham hex `#ff7b72` | 3 | UPPERCASE (`signal-AL`) |
| index.html | `.signal-badge` | 1287-1292 | 6 (AL/SAT/BEKLE + bull/bear/neutral) | Yok | Var (3, ölü) | tam tokenize (`var(--bp-al-bg/-bd)`) | 5 | UPPERCASE |
| portfolio.html | `.signal-badge` | 64 | 3 (AL/SAT/BEKLE) | Yok | Yok | %100 ham hex (dahil `#30363d`) | 1 | UPPERCASE |
| **TOPLAM (7 dosya)** | 2 aile adı, 1 kavram | 7 base tanım | **32** | 2/7 dosyada | 3/7 dosyada (varlik, hisse, index) | 3 farklı tokenizasyon seviyesi | **20** ✓ (düzeltildi, ilk taslak 17 yazmıştı) | 6/7 UPPERCASE, 1/7 lowercase |

## Tekrar derecesi — 3+1 deseni (sig-badge ailesi)

kategori.html, tarama.html, varlik.html birbirine neredeyse özdeş: `.sig-AL/.sig-SAT/.sig-BEKLE`, aynı case, aynı renk formülü (`rgba(63,185,80,.12)` bg / `var(--al)` / `rgba(63,185,80,.3)` border — AL; `rgba(var(--bp-sat-rgb),.12)`/`var(--sat)` — SAT; `rgba(139,148,158,.1)`/`var(--bkl)`/`rgba(139,148,158,.2)` — BEKLE). Aralarındaki fark yalnız layout: varlik.html büyük/hero boyut (padding 6px 16px + `var(--bp-text-base)`), kategori/tarama küçük/liste boyutu (padding 3px 9-10px + `var(--bp-text-xs)`) — kasıtlı bir boyut varyantı, renk tekrarı değil.

bilanco_takvimi.html bu üçlünün dışında kalıyor: class case'i lowercase (`sig-al` — diğerleri UPPERCASE), alpha değeri farklı (bg 0.15 vs .12), token öneki farklı (`var(--bp-al)` — diğer üçü `var(--al)` kullanıyor).

`state-soon` yalnız kategori + varlik'te var (ikisi de aynı yorum metnini taşıyor — "T7.5.1/T7.5.3, FAZ 7.5 eki §2a" — bilinçli, birlikte tasarlanmış bir karar), bilanco_takvimi ve tarama'da yok. `.sig-badge.bull/.bear/.neutral` yalnız varlik.html'de tanımlı ve markup'ta hiç kullanılmıyor (ölü CSS, tek-dosya kapsamında doğrulandı — bkz. açık riskler).

bilanco_takvimi.html'de `sig-al/sig-sat` isimleri ayrıca satır 99-100'de `.stock-card` ile compound selector olarak da (farklı opaklıkla, 0.05 vs 0.15) tekrar kullanılıyor — badge ailesinin parçası değil ama aynı class ismini paylaşıyor, konsolidasyonda isim çakışması riski taşır.

## İkinci aile (signal-badge) neden ayrı — kavramsal fark yok, isimlendirme driftı

"signal-badge" (hisse, index, portfolio) kavramsal olarak sig-badge'den farklı değil — aynı üç-durumlu (AL/SAT/BEKLE) sinyal rozetini aynı işlevsel rolde (hisse detay hero'su, ana sayfa piyasa tablosu, portföy tablosu) gösteriyor; layout özellikleri (inline-flex, gap, padding, border-radius, font-weight 600-700, letter-spacing) neredeyse birebir aynı desende. Muhtemelen farklı bir geliştirme evresinde yazılmış aynı bileşenin ikinci isimlendirmesi ("signal-" vs kısaltılmış "sig-") — [[reference_sayfa_kabugu_drift]] (17 şablon kabuğu drift) deseninin bir başka tezahürü.

signal-badge ailesinin içinde sig-badge'den daha büyük bir renk-yöntemi sapması var, üç farklı tokenizasyon seviyesinde:
- **index.html**: tam tokenize — `var(--bp-al-bg)/var(--bp-al-bd)` hazır bg/border token'ları, ham renk yok.
- **hisse.html**: yarı tokenize — `rgba(var(--bp-al-rgb),.10)` kullanıyor AMA `.signal-SAT` metin rengi ham hex: `color:#ff7b72`.
- **portfolio.html**: sıfır tokenizasyon — üç durumun hepsi ham hex (`#1a4731/#3fb950/#238636`, `#3d0f0f/#f85149/#da3633`, `#21262d/#8b949e/#30363d`). `#30363d` [[reference_bkl_token_mavi_ama_asil_kalinti_ham_hex]] kaydıyla eşleşen somut bir örnek.

hisse.html SAT metin rengi `#ff7b72` ile portfolio.html SAT metin rengi `#f85149` **farklı** kırmızı tonları — aynı "SAT" durumu iki sayfada iki farklı kırmızıyla gösteriliyor, kasıtlı olması olası değil.

## Kritik bulgu — `--al`/`--bkl` kanonik değil, gerçek renk sapması (doğrulama turunun yakaladığı, 3 kez teyitli)

İlk sentez taslağı bunu yalnız "bilanco_takvimi'nin token-öneki sapması" gibi çerçevelemiş ve "tokens.css okunmadan doğrulanamaz" diye açık bırakmıştı. Bağımsız doğrulama ajanı `tokens.css`'i doğrudan okuyup soruyu kapattı, CPO tarafında da üçüncü kez doğrudan `grep` ile teyit edildi:

```
tokens.css:29   --bp-al:  #00e290
tokens.css:34   --bp-sat: #f85149
tokens.css:39   --bp-bkl: #909097

kategori.html:26 / tarama.html:26 / varlik.html:34 (kendi :root'ları):
  --al:#3fb950; --sat:var(--bp-sat); --bkl:#8b949e;
```

- **`--sat`** doğru aliaslanmış (`var(--bp-sat)` — SAT renginde risk yok).
- **`--al`**: yerel `#3fb950` (yeşil) vs kanonik `--bp-al:#00e290` (yeşil-turkuaz) — **gerçek renk farkı**, alias değil. `--bp-al` ailesine geçiş bu 3 dosyanın AL rozetlerinde görünür bir renk değişikliğine yol açar.
- **`--bkl`**: yerel `#8b949e` vs kanonik `--bp-bkl:#909097` — birbirine yakın ama özdeş değil iki gri, küçük ama gerçek bir sapma.

Bu, [[reference_sablon_yerel_root_palet_sapmasi]] (4 şablon eski sözlük, 16 rota/30 URL) kaydının kategori/tarama/varlik özelinde somut bir örneği — S1'deki `--border2` rol tersliği riskiyle **aynı sınıf**: konsolidasyon renk kaynağı olarak doğrudan `var(--bp-al)` seçilirse, 3/4 sig-badge dosyasını (yalnız bilanco_takvimi'ni değil) etkileyen sessiz bir görsel değişiklik olur.

## Konsolidasyon fizibilitesi (öneri, uygulama DEĞİL — S1/S7 deseniyle birebir)

Teknik olarak 7 tanımı tek bir `.bp-signal-badge` (+ `--al/--sat/--bekle` modifier veya `data-signal="AL|SAT|BEKLE"` seçici) altında toplamak mümkün — çekirdek layout ve üç-renk mantığı 7 dosyada da aynı kavramsal iskelete oturuyor.

**Üstüne binebilecek (Δ≈0, görsel fark riski düşük):**
- kategori.html + tarama.html: birebir aynı AL/SAT/BEKLE üçlüsü + aynı boyut → doğrudan birleştirilebilir.
- state-soon: kategori + varlik'te birebir aynı değer ve aynı tasarım kararı → tek tanıma indirilebilir.
- bull/bear/neutral: 3 dosyada (varlik, hisse, index) tek-dosya kapsamında ölü CSS olarak raporlandı — kanonikleştirmeden bağımsız, ayrı bir "önce sil" adımı olarak değerlendirilebilir (siteneli çapraz doğrulama YAPILMADI, aşağıdaki açık riske bakınız).

**Riskli/binmeyen noktalar:**
- Renk kaynağı seçimi (`--al` vs `--bp-al`) yukarıdaki bulgu nedeniyle 3/4 sig-badge dosyasını etkiler — görsel QA olmadan otomatik "aynı" varsayılamaz.
- portfolio.html'nin ham-hex paleti (`#30363d`, `#ff7b72` vs `#f85149` farkı) — token'a geçiş gerçek bir renk kararı, salt refactor değil.
- varlik.html'nin büyük/hero boyut varyantı (padding 6px 16px, text-base) kanonik component'e size-modifier olarak taşınmalı, kaybedilmemeli.
- bilanco_takvimi'ndeki `.stock-card.sig-al` compound-selector kullanımı, badge dışı bir bağlamda aynı class ismini taşıyor — kanonik isim değişikliği bu satırları da etkileyebilir.

**Önerilen migrasyon şekli (S1 deseni — ekle, ezme):**
1. Ortak katmana yeni `.bp-signal-badge` + `--al/--sat/--bekle/--state-soon` modifier tanımlarını EKLE; mevcut `.sig-badge`/`.signal-badge` tanımlarına dokunma.
2. Renk kaynağı: `--bp-al`'e geçiş kategori/tarama/varlik'te görünür bir yeşil tonu değişikliği yaratacağı için (yukarıdaki bulgu), bu adım ayrı bir görsel-onay gerektiren karar — otomatik ilerlenmez.
3. En düşük riskliden (kategori+tarama, birebir aynı) başlayarak markup'ı yeni class'a geçir, eski class paralel kalabilir (isim farklı, çakışma yok).
4. portfolio.html ve hisse.html'nin ham-hex/karışık-hex noktaları son sıraya alınır — CPO/Ozan onayı olmadan otomatik "aynı" varsayılmaz.
5. bull/bear/neutral ölü CSS temizliği konsolidasyondan bağımsız, ayrı bir düşük-riskli adım — ama siteneli grep ile çapraz doğrulanmadan silinmemeli (bu turda yalnız tek-dosya kapsamında "ölü" bulundu).

## Açık riskler (CPO/Ozan kararı gerektirebilir — bu turda hiçbiri karara bağlanmadı)

1. `--al`/`--bkl` yerel override'larının kanonik `--bp-al`/`--bp-bkl`'e taşınması gerçek bir renk değişikliği — 3 dosyayı (kategori, tarama, varlik) etkiler, görsel onay gerekir.
2. hisse.html SAT metni (`#ff7b72`) ile portfolio.html SAT metni (`#f85149`) farklı — kasıtlı mı hata mı belirsiz.
3. portfolio.html'nin ham `#30363d` kullanımı — [[reference_bkl_token_mavi_ama_asil_kalinti_ham_hex]] kapsamına girip girmediği ayrıca değerlendirilmeli.
4. bull/bear/neutral'ın "ölü kod" tespiti yalnız tek-dosya kapsamında yapıldı (7 ajan birbirini görmedi) — siteneli (JS dosyaları, ortak component'ler dahil) çapraz doğrulama YAPILMADI, silmeden önce ayrıca taranmalı.
5. state-soon'un bilanco_takvimi ve tarama'da olmaması — ürün kararı mı (bu sayfalarda ihtiyaç yok) yoksa UX açığı mı, belirsiz.
6. varlik.html'nin hero boyut varyantı migrasyon sırasında kaybolmamalı — size-modifier olarak taşınmalı.

## Bağımsız doğrulama özeti

Ayrı bir ajan 7 dosyayı SSH ile sıfırdan (ilk taslağı görmeden) yeniden grep'ledi ve `tokens.css`'i doğrudan okudu. **DUZELTME_GEREKLI** verdi, 2 hata buldu:
- `markup_usages_total` ilk taslakta **17** yazılmıştı, dosya-bazlı tablonun kendi toplamı bile **20**'ydi (aritmetik hata) — bu dokümanda 20 olarak düzeltildi.
- `--al`/`--bp-al` alias mı değil mi sorusu ilk taslakta açık bırakılmıştı; doğrulama `tokens.css` okuyarak kapattı: **alias değil, gerçek renk farkı** (yukarıdaki "Kritik bulgu" bölümü). CPO tarafında üçüncü kez doğrudan grep ile teyit edildi.

`css_definitions` (7) ve `variant_classes_total` (32) doğru, tüm nitel tespitler (case convention, token adı farkları, alpha değer farkları, state-soon kapsamı, ham-hex noktaları, bull/bear/neutral ölü kod, compound selector) satır satır doğrulandı, hiçbirinde düzeltme gerekmedi.

## Sıradaki

Bu doküman yalnız sınıflandırma + fizibilite — migrasyon kararı (kanonik component adı, renk kaynağı seçimi, bull/bear/neutral silme onayı) CPO/Ozan onayı bekliyor; S7/T3.4 emsaliyle aynı karar kuyruğuna eklenmesi önerilir. Büyük ölçekli migrasyona bu turda GİRİLMEDİ.
