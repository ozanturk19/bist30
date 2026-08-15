# S7 — Ham `#30363d` Sınıflandırması (FAZ8, CPO-DEV2-006 onayı, KOD DEĞİŞMEDİ)

**Tarih:** 14.08.2026 · **Kapsam:** Yalnız sınıflandırma + kontrast ölçümü (CPO-DEV2-006, Cum 14.08 16:01 TR: "önce sınıflandırma yap ... büyük ölçekli migrasyona sınıflandırma bitmeden girme"). Bu turda hiçbir CSS/HTML/JS değişmedi — migrasyon kararı bu doküman ışığında CPO onayına bağlı.

## Kaynak veri

```
grep -rn '#30363d' templates/ static/  →  104 ham kullanım, 14 şablon + tokens.css
```

Workflow: elle tam sınıflandırma (104/104, örneklem değil) + arithmetik çapraz-doğrulama (her dosyanın kendi `grep -c` toplamıyla eşleşiyor) + bağımsız eleştiri ajanı (ayrı SSH oturumuyla veriyi sıfırdan yeniden üretti, kontrast rakamlarını bağımsız hesapladı, 1 atıf hatası dışında sıfır düzeltme ile ONAY verdi — atıf hatası yalnız bu dokümanın taslak metnindeydi, sınıflandırma toplamlarını etkilemedi).

## Sonuç tablosu

| Kategori | Adet | Örnek |
|---|---|---|
| **STATİK** (resting-state border/background/scrollbar — migrasyon hedefi) | **88** | `header{border-bottom:1px solid #30363d}`, `.card{border:1px solid #30363d}`, tablo `border-bottom` ayracı — 14 şablonda tekrarlayan "eski sayfa kabuğu" deseni |
| **HOVER** (`:hover` state, arka plan `#30363d`'ye dönüyor) | 9 | `.back-btn:hover{background:#30363d}` — 9 farklı şablonda birebir aynı komponent (blog_article, blog, gizlilik, gucu_yuksek, hakkinda, hisseler, iletisim, metodoloji, yasal) |
| **DISABLED** (`:disabled` state) | 1 | `sinyal_performans.html:91` `.btn-run:disabled{background:#30363d}` |
| **NÖTR GÖSTERGE** (JS/CSS, sınır değil, "boş/nötr" durum rengi) | 3 | `index.html:1320` `.sig-tip-ck.no{color:#30363d}`, `:5305` JS bull/bear/nötr ikon rengi, `:5350` boş skor noktası `○` rengi |
| **HARİÇ — kanonik tokenın kendi tanımı** | 1 | `tokens.css:41` `--bp-bkl-bd:#30363d` (BEKLİYOR sinyali border tokenı, S7 kapsamı DIŞI — farklı anlam) |
| **HARİÇ — şablon-yerel `:root` sapması (T1.6 konusu, S7 değil)** | 2 | `kategori.html:24`, `varlik.html:32` — ikisi de kendi `:root{--border:#30363d}` tanımı, ham kullanım değil, ayrı bir bilinen sorunun (312 kullanımlık şablon-yerel `:root` GitHub-paleti drifti) parçası |
| **TOPLAM** | **104** | 88+9+1+3+1+2 = 104 ✓ |

İki JS-tabanlı satır (`blog_article.html:326` onblur, `:454` setTimeout) STATİK kovaya sayıldı — ikisi de geçici bir odak/hata rengini varsayılan ayraç rengine GERİ DÖNDÜRÜYOR, kalıcı bir etkileşim aksanı değil, CSS `:focus`/`:invalid` yerine JS ile yazılmış aynı statik davranış.

## Kontrast ölçümü (WCAG bağıl parlaklık, `--bp-surface:#141416` zemine karşı)

| Renk | Kontrast | Not |
|---|---|---|
| `--bp-border-subtle` `#21262d` (S1'de eklenen yeni token) | **1.21:1** | en silik, statik ayraç |
| `--bp-border` `#2a2a2c` (kanonik varsayılan) | **1.28:1** | bugünkü "standart" statik ayraç |
| **ham `#30363d`** | **1.51:1** | **`--bp-border`'dan %18 daha görünür** |
| `--bp-border2` `#46464d` (hover tokenı) | **1.97:1** | en belirgin, hover/vurgu |

Sıralama monotonik: subtle(1.21) < border(1.28) < **ham #30363d(1.51)** < border2/hover(1.97). Ham değer, mevcut iki statik token'dan da belirgin ölçüde daha görünür — S1'deki `--border2` rol tersliğiyle **aynı risk sınıfı**: `#30363d`'yi doğrudan `--bp-border`'a alias'lamak 88 statik kullanımın tamamını görsel olarak soldurur (1.51→1.28, %15 kontrast kaybı).

## Öneri (uygulama DEĞİL, yalnız öneri — S1 deseniyle birebir)

S1'de kurulan desen ("mevcut hiyerarşiyi bozma, değeri koruyan yeni token ekle") burada da uygulanabilir:

- **Yeni token:** `--bp-border-strong: #30363d` (mevcut merdivene `border-subtle → border → border-strong → border2(hover)` olarak eklenir, hiçbir mevcut tokenın değeri değişmez)
- **88 STATİK kullanım** → `var(--bp-border-strong)`'a migrate edilir (sıfır görsel değişiklik, S1'deki gibi)
- **9 HOVER + 1 DISABLED kullanım** → mevcut `var(--bp-border2)` (hover tokenı, 1.97:1) ile DEĞİL, kendi ham değeriyle bırakılabilir YA DA aynı `--bp-border-strong`'a bağlanabilir (görsel fark yok, ikisi de #30363d) — CPO'nun tercihi, ayrı bir karar gerektirmiyor çünkü değer aynı kalıyor.
- **3 NÖTR GÖSTERGE kullanımı** (`.sig-tip-ck.no`, JS bull/bear/nötr, boş skor noktası) — bunlar `border` değil `color` kullanıyor, semantik olarak "sınır" değil "durum rengi". Aynı `--bp-border-strong` değerini `color` için de kullanmak (isim "border" ama `color:` property'sinde de tutarlı) tartışmaya açık — alternatif: ayrı bir `--bp-neutral-ink` tokenı (aynı hex, farklı isim, "bu bir metin/ikon rengi" niyetini taşır). Küçük kapsam (3 kullanım), CPO tercihi.
- **2 HARİÇ (kategori.html, varlik.html şablon-yerel `:root`)** → S7 kapsamı dışı, T1.6'nın (5 şablon/312 kullanım şablon-yerel `:root` temizliği) parçası olarak orada ele alınmalı, burada dokunulmadı.

## a11y yan-bulgu (ayrı, S7 dışı)

`metodoloji.html:363` — footer feragatname metni `color:#30363d` kullanıyor (`--bp-bg:#0e0e12` zemine karşı ölçülen kontrast **1.58:1**), yani bu bir BORDER değil bir METİN rengi ve WCAG AA metin eşiğinin (4.5:1) çok altında — neredeyse görünmez feragatname. Bu S7'nin STATİK kovasına dahil (104 sayıma dahil) ama migrasyon önerisi farklı: `--bp-border-strong`'a değil, mevcut `--bp-text3` (6.07:1) ailesine taşınmalı — okunabilir bir feragatname metni bir ayraç rengiyle karıştırılmamalı. FAZ8 kontrast backlog'una ayrı madde olarak not düşülüyor, bu dokümanın migrasyon kapsamı dışı tutuluyor.

## Bağımsız eleştiri özeti

Ayrı bir ajan SSH ile veriyi sıfırdan yeniden üretti (104 kayıt, 15 dosya, case-insensitive tarama dahil — büyük/küçük harf varyantı yok), her HOVER/DISABLED/NÖTR/HARİÇ satırını bağlamıyla tekrar okudu, kontrast rakamlarını bağımsız hesapladı (1.507/1.285/1.209 — üçü de iddia edilen değerlerle örtüşüyor) ve dosya-bazlı aritmetiği tek tek doğruladı (15/15 dosya kendi `grep -c` toplamıyla eşleşiyor). Tek bulgu: taslak metinde iki satırın (`:326`/`:454`) yanlışlıkla `index.html`e atfedilmişti, doğrusu `blog_article.html` — sınıflandırma toplamlarını etkilemeyen bir atıf düzeltmesiydi, bu dokümanda düzeltilmiş haliyle yer alıyor. Sonuç: **88/9/1/3/1/2 dağılımı olduğu gibi rapor edilmeye hazır.**

## Sıradaki

Migrasyon kararı (yeni token ekle mi, hangi isimle, 3 nötr-gösterge kullanımını nasıl ele al) CPO onayı bekliyor — S1'in devamı sayılan bağımsız bir T-kodu olarak mı yoksa Ozan'a S1-tarzı ayrı bir soru olarak mı götürüleceği CPO-DEV2-006'da zaten "kapsam sınırlı ONAY" ile DEV2'ye bırakılmıştı; bu doküman o onayın gerektirdiği sınıflandırmayı tamamlıyor. Büyük ölçekli migrasyona (88+9+1 kullanımın `var()`'a bağlanması) bu turda GİRİLMEDİ, CPO'nun "sınıflandırma bitmeden migrasyona girme" talimatına sadık kalındı.
