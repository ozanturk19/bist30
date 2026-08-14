# FAZ5 — Çekirdek Komponentler (Kart Dili, Tipografi, Spacing) — Envanter + Plan + Bağımsız Eleştiri

Üretildi: Cum 14.08.2026 TR, DEV2 (workflow: 5 harita ajanı + 1 tasarım sentezi ajanı + 1 bağımsız eleştiri ajanı, ardından DEV2'nin kendi doğrulama turu)
Kapsam: yalnız route/render/template/CSS/JS (görüntü katmanı). `business_rules.py`, `analyze()`/`compose_score` matematiği, Yahoo fetch, leader election **DEV1 alanı — bu dokümanda dokunulmaz, çözüm önerilmez.**

---

## 1. Mevcut Durum Özeti

**Token altyapısı (FAZ1) tam ama bağlı değil.** `tokens.css`'te spacing (`--bp-space-0..40`), tipografi (`--bp-text-2xs..42`), radius (`--bp-radius-xs..pill`) ve renk (surface/border/text/sinyal) token setleri eksiksiz tanımlı. Ama:

- **Spacing: sıfır tüketici.** 2501 padding/margin/gap kullanımı şablon/CSS/JS/Python genelinde hâlâ ham px; `--bp-space-*` hiçbir yerde referans alınmıyor. 33 ayrık değerin %82'si mevcut basamaklara kayıpsız oturuyor; 387 tek-sayı kullanım (3/5/7/9/11/13/17px) ladder'a oturmuyor, backlog'da bekliyor.
- **Radius: disiplinli.** `.signal-badge`, `.ind-badge`, `.mc`, `.mc-bell`, `.stat-card`, `.endeks-card` hepsi `var(--bp-radius-*)` kullanıyor.
- **Tipografi: iskelet var, hiyerarşi resmi değil.** 19 basamaklı `--bp-text-*` seti mevcut ama "display/heading/body/mono-fiyat" gibi anlamsal eşleme hiçbir yerde tanımlı değil.
- **Aynı bileşen, 3+ farklı görsel gerçeklik.** `.signal-badge` üç şablonda (`index.html`, `hisse.html`, `portfolio.html`) üç kez tanımlanmış: `portfolio.html` tamamen ham hex + eski GitHub-dark paleti (AL rengi `#3fb950`, token `#00e290`'dan belirgin farklı; radius 12px köşeli, 20px pill değil); `hisse.html` kısmen `var()` kullanıyor ama SAT rengi (`#ff7b72`) token değerinden (`#f85149`) sapıyor, font-size/weight/letter-spacing index.html'den farklı. Hafızadaki "🔴 Şablon-Yerel :root Palet Sapması" bulgusunun somut örneği.
- **"Kart ailesi" aslında iki farklı fizik kullanıyor.** `.stat-card` (index.html:992) gerçek katmanlı yüzey (`rgba(surface,.8)` + `backdrop-filter blur(8px)`) ve gerçek dikey elevasyon (`translateY(-2px)` + `box-shadow: var(--bp-shadow-md)`) taşıyor — TradingView diline en yakın mevcut bileşen. `.endeks-card` (index.html:1442) düz opak arka plan, gölgesiz glow-ring hover ve `transition` listesine bile girmemiş bir `transform` ile "focus ring" gibi davranıyor.
- **Aynı "hisse satırı" kavramı 3 şablonda 3 kez sıfırdan yazılmış.** `index.html` (`renderTable()`, 3910-4150, client JS), `tarama.html` (`renderResults()`, 862-964, client JS), `sinyal_performans.html` (298-330, server-side Jinja) — hiçbir class ismi ortak değil. Tahmini ~340+ satır JS render + ~70+ satır CSS üç yerde tekrar ediyor.
- **Performans notu:** `renderTable()` her çağrıda (canlı fiyat polling, filtre, sıralama) hem masaüstü `tbody` hem mobil `.mc` listesini **görünürlükten bağımsız** tam `innerHTML` replace ile yeniden yazıyor — ~215 satır × 9 hücre potansiyel 1900+ DOM node, üstüne `.mc` başına ayrı `backdrop-filter: blur(12px)`.

---

## 2. Önerilen Kart Dili Spesifikasyonu

CPO talebi: "yumuşak köşe + katmanlı yüzey + hover elevasyonu". Referans model `.stat-card` — mevcut kod tabanında bu üç özelliği zaten gerçek biçimde taşıyan tek bileşen.

### 2.1 Kanonik yüzey/kart (`bp-card` — stat-card/endeks-card ailesi)

| Özellik | Değer | Kaynak |
|---|---|---|
| border-radius | `var(--bp-radius-lg)` (10px) standart, `var(--bp-radius-xl)` (12px) vurgulu | mevcut token |
| surface | `rgba(var(--bp-surface-rgb), .8)` + `backdrop-filter: blur(8px)` | `.stat-card`'dan |
| border | `1px solid var(--bp-border)` → hover `var(--bp-border2)` | mevcut |
| hover elevasyon | `transform: translateY(-2px)` + `box-shadow: var(--bp-shadow-md)` | mevcut token, `.stat-card`'dan |
| transition | `border-color .2s, transform .2s, box-shadow .2s` | `.endeks-card`'ın eksik bıraktığı budur |

### 2.2 Kanonik chip/rozet (`bp-chip` — signal-badge, ind-badge, anomaly-badge, sentiment-badge)

| Özellik | Değer | Not |
|---|---|---|
| padding | `var(--bp-space-4) var(--bp-space-10)` | ladder'da ikisi de mevcut |
| border-radius | `var(--bp-radius-pill)` (999px) **veya** `var(--bp-radius-20)` (20px) | **CPO onayı gerekir — §6** |
| renk | `var(--bp-al)/--bp-sat/--bp-bkl` + `-bg`/`-bd` varyantları | token zaten FAZ1'de karara bağlı, sadece hizalama |
| font | `--bp-text-xs` (11px) / `700` weight / `0.4px` letter-spacing | index.html'in mevcut değeri kanonik alınıyor |

### 2.3 Yeni token ihtiyacı yok

Kart ve chip spesifikasyonu tamamen mevcut `tokens.css` setinden karşılanıyor.

---

## 3. Önerilen Tipografi Ölçeği

| Katman | Token | px | Kullanım |
|---|---|---|---|
| Mikro-etiket | `--bp-text-xs` | 11 | signal-badge, ind-badge, anomaly/sentiment-badge |
| Body | `--bp-text-base` | 13 | tablo hücresi — zaten fiilî standart |
| Heading L3 | `--bp-text-md`→`--bp-text-lg` | 14-16 | alt başlıklar |
| Heading L2 | `--bp-text-xl` | 18 | bölüm başlığı |
| Heading L1 | `--bp-text-2xl` | 20 | üst düzey başlık |
| Mono-fiyat | `--bp-text-base`/`--bp-text-lg` | 13-16 | `.price`/`.mc-price`, `tabular-nums` zorunlu |
| Display/hero-stat | `--bp-text-26`…`--bp-text-36` | 26-36 | stat-card/endeks-card değeri — "gerçek drift yok" bandı |

**Açık nokta:** `--bp-font-num` (Space Grotesk mono/sayısal aile) henüz token değil, Ozan'ın S1b marka kararına bağlı — §6.

---

## 4. Önerilen Spacing Ritmi (4px Grid)

Token seti zaten var (`--bp-space-0/px/2/4/6/8/10/12/14/16/18/20/24/28/32/40`, 2px taban + 4px adım) — iş **tanım değil bağlama**.

| Bileşen | Ham değer | Token karşılığı |
|---|---|---|
| `td`/`thead th` | `10px 16px` | `var(--bp-space-10) var(--bp-space-16)` |
| `.signal-badge` | `4px 10px` | `var(--bp-space-4) var(--bp-space-10)` |
| `.stat-card` | `14px 20px` | `var(--bp-space-14) var(--bp-space-20)` |
| `.endeks-card` | `14px 16px` | `var(--bp-space-14) var(--bp-space-16)` |

**Kırık nokta:** 387 kullanım (3/5/7/9/11/13/17px) ladder'a düz oturmuyor — CPO kararı gerekir (§6).

**"Bol negatif alan" hedefi somut değil** — token bağlama tek başına bunu sağlamaz, kart-içi padding/kartlar-arası gap'in bir basamak yukarı taşınması ayrı bir görsel karar (before/after mockup ile CPO'ya götürülmeli).

---

## 5. Uygulama Sırası (Risk Artan) — Eleştiri sonrası DÜZELTİLMİŞ

> Bağımsız eleştiri iki iç tutarsızlık buldu (bkz. §8, madde 2-3): Adım 1'in dosya kapsamı Adım 3 ile uyuşmuyordu (tarama.html dışarıda unutulmuştu), ve "çakışan hover kuralı birleştirme" Adım 0'ın içine "sıfır risk" etiketiyle gömülüydü. Aşağıdaki sıra bu iki maddeyi düzeltir.

### Adım 0a — Ön-kontrol (uygulama değil, doğrulama) — YAPILDI, bu doküman ile birlikte
Eleştirinin CİDDİ #1 bulgusu: token bağlamadan önce her şablonun yerel `:root` bloğunun `--bp-space-*`/`--bp-radius-*` adlarını gölgeleyip gölgelemediği doğrulanmalı. **Kontrol edildi (DEV2, bu turda):** `index.html`, `hisse.html`, `portfolio.html`'de hiç `:root` bloğu yok; `tarama.html`'in tek `:root` bloğu (satır 22-29) kendi yerel isimlerini kullanıyor (`--bg`, `--surface`, `--border`, `--text`, `--al`, `--sat`, `--bkl`, `--brand`, `--gold`) — `--bp-space-*`/`--bp-radius-*` adlarıyla **çakışma yok**. Adım 0b bu doğrulamayla güvenle ilerleyebilir.

### Adım 0b — Token bağlama, değer SIFIR değişir (düşük risk, doğrulandı)
Ham px değerlerini aynı sayısal karşılığa sahip `var(--bp-space-*)`/`var(--bp-radius-*)` ile değiştirmek. Görsel fark yok.
- **Dosyalar:** `templates/index.html`, `hisse.html`, `portfolio.html`, `tarama.html` `<style>` blokları.
- **Tahmini satır:** ~150-250 CSS deklarasyonu, find/replace niteliğinde.
- **Risk:** DÜŞÜK. **Kabul kriteri computed style ile doğrulanmalı** (aynı px sonucu vermeli, `<style>` metnine bakmak yetmez — [[feedback_kabul_olcutu_style_degil_computed]]).

### Adım 0c — (Adım 0'dan AYRILDI) Çakışan hover kuralı birleştirme
`tbody tr:hover` (1274) / `#tableBody tr:hover` (1623) çakışan tanımı — bu bir specificity/cascade refactor'ü, salt değer-kaynağı değişimi DEĞİL. Ayrı, izole test edilecek adım.
- **Risk:** ORTA (davranış testi gerekir, "aynı yönde çalıştığı" önce doğrulanmalı).

### Adım 1 — Chip/rozet renk ve radius'unu kanonikleştirme (4 şablon, TAM kapsam)
`portfolio.html`'in ham hex GitHub-dark paletini (`#3fb950`, `#21262d`, `#1a4731` vb.) ve 12px köşeli radius'unu; `hisse.html`'in SAT renk sapmasını (`#ff7b72`→`var(--bp-sat)`); **ve tutarlılık için `tarama.html`'in kendi `sig-badge`/`eq-badge` tanımlarını da** aynı taramaya dahil etmek (Adım 3 ile kapsam tutarlı olsun diye — eleştiri madde 2).
- **Dosyalar:** `portfolio.html` (~15-20 satır), `hisse.html` (~10 satır), `tarama.html` (kapsam bu turda ölçülmedi, ayrı harita gerekebilir).
- **Risk:** DÜŞÜK-ORTA — görsel değişiklik fark edilir ama FAZ1'de zaten kanonikleşmiş tokenlere hizalama.

### Adım 2 — `.endeks-card`'ı `.stat-card` ailesine hizalama
Katmanlı yüzey + gerçek elevasyon eklemek.
- **Risk:** ORTA + **performans notu (eleştiri madde 4):** `.mc` kartlarında (215 adet) zaten bilinen `backdrop-filter` GPU maliyeti varken bu adım ikinci bir blur katmanı ekliyor — bu adımdan ÖNCE ya da bu adımla BİRLİKTE görünürlük-guard'lı render iyileştirmesi (Adım 4'ün opsiyonel parçası) değerlendirilmeli, "Stabilite > UX" ilkesi gereği.

### Adım 3 — Tipografi hiyerarşisini 4 şablon arası hizalama
`.signal-badge` font-size/weight/letter-spacing farklarını tekilleştirmek.
- **Risk:** ORTA — mobil `.mc-ticker`/`.mc-price` taşma riski, somut test prosedürü gerekli (en uzun ticker + en yüksek fiyat kombinasyonu).

### Adım 4 — Ortak "hisse satırı" partial/JS modülü (en yüksek risk)
`index.html`/`tarama.html`/`sinyal_performans.html` implementasyonlarını tek paylaşılan bileşene indirgemek.
- **Risk:** YÜKSEK — canlı fiyat polling döngüsünde çalışan kod. **Bu doküman kapsamını tarif eder, uygulamayı bu turda önermez** — ayrı bir ticket/RFC olarak planlanmalı.
- **Kabul kriteri şartı:** component "sadece backend alanını render eder, eşik/renk mantığı tanımlamaz" — §8 RSI notuna bağlı.

---

## 6. Belirsiz / Ozan-CPO Onayı Gereken Kararlar

1. **Chip radius:** `--bp-radius-pill` (999px, gerçek pill) mi yoksa mevcut `--bp-radius-20` (20px) mi kanonik?
2. **`--bp-font-num`** (mono-fiyat font ailesi) henüz token değil — Ozan'ın S1b marka kararına bağlı.
3. **Spacing ladder'ın 387 tek-sayı kullanımı** (3/5/7/9/11/13/17px): odd-step token eklensin mi (radius setindeki 5/7/9/11 emsaliyle) yoksa en yakın çift basamağa mı yuvarlansın?
4. **"Bol negatif alan" hedefi** — hangi spacing (satır yüksekliği/kart-arası gap/sayfa marjı) ne kadar artacak, somut px hedefi CPO ile mockup üzerinden.
5. **Portfolio.html'in eski paleti** (`#3fb950` yeşil) — bugfix/migrasyon mu, kasıtlı ikinci marka kimliği mi?
6. **`.endeks-card`'a ikinci `backdrop-filter` katmanı** — estetik/performans trade-off, CPO bilerek onaylamalı.

---

## 7. Uygulama Notu — Bu Turda Ne Yapılmadı, Neden

Bu doküman CPO-DEV2-005'in "FAZ5 çekirdek komponentler = en görünür kalem" önceliğine yanıt olarak üretildi, ama **hiçbir CSS/JS değişikliği bu turda deploy edilmedi.** Gerekçe: bağımsız eleştiri 2 CİDDİ + 8 ORTA/DÜŞÜK bulgu çıkardı (§8) — en azından §6'daki 6 karar CPO/Ozan'dan gelmeden Adım 1-3'e girmek, T4.4'te zaten bir kez terk edilen "varsayımla ilerleme" hatasını tekrarlar. Adım 0a (ön-kontrol) tek istisna — DEV2 kendi başına doğrulayabildiği, kod değiştirmeyen bir adım olduğu için bu turda yapıldı ve sonucu yukarıda (§5) raporlandı.

---

## 8. Bağımsız Eleştirinin Tam Bulgu Listesi

1. **CİDDİ** — Adım 0'ın "sıfır risk" varsayımı yerel `:root` gölgeleme riskini kontrol etmiyordu → **bu turda DEV2 tarafından doğrulandı, çakışma yok (§5, Adım 0a)**, risk kapandı.
2. **CİDDİ** — Adım 1 (chip/badge) kapsamı Adım 3 (tipografi) ile tutarsızdı, tarama.html dışarıda unutulmuştu → **plan §5'te düzeltildi**, tarama.html Adım 1 kapsamına eklendi (ayrı harita gerekebileceği notuyla).
3. **ORTA** — Hover kuralı birleştirmesi Adım 0 içine "düşük risk" etiketiyle gömülüydü, aslında cascade-değiştiren refactor → **plan §5'te ayrı Adım 0c olarak çıkarıldı**.
4. **ORTA** — Adım 2 (yeni blur katmanı) performans riskini büyütürken asıl performans düzeltmesi (görünürlük guard) Adım 4'e erteleniyordu → **plan §5'te not eklendi**, Adım 2'nin performans iyileştirmesiyle birlikte/önce değerlendirilmesi gerektiği işaretlendi.
5. **ORTA** — AL/SAT renk migrasyonu + translüsent kart yüzeyi (blur) aynı fazda çakışıyor, WCAG kontrast doğrulaması plan içinde yok — **açık kaldı, Adım 1/2 uygulanırken kontrast ölçümü zorunlu tutulmalı.**
6. **ORTA** — Masaüstü/mobil parite disiplini insana bağlı, otomatik mekanizma yok — **açık kaldı, backlog notu.**
7. **DÜŞÜK-ORTA** — "Şablon-Yerel :root Palet Sapması" hafıza bulgusu 4 şablon diyor, Adım 1 yalnız 2'sini kapsıyordu → **plan §5'te 3.'sü (tarama.html) eklendi, 4.'sü hangi şablon olduğu bu turda tespit edilmedi, ayrı grep gerekir.**
8. **DÜŞÜK** — Font-size/spacing değişiklikleri CLS riski taşıyabilir, değerlendirilmemiş — **açık kaldı.**
9. **DÜŞÜK** — Yeni `--bp-radius-chip` alias'ının `bp-vocab.js` sözlüğüne kaydı belirsiz — **açık kaldı, uygulanırsa sözlüğe eklenmesi şart koşulmalı.**
10. **DÜŞÜK** — Adım 3 taşma riski için somut test prosedürü yok — **açık kaldı.**
