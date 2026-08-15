# T9.2 — `blog_content.py` "TL" Yazım Sınıflandırması (FAZ9, DEV2-115'in devamı, KOD DEĞİŞMEDİ)

**Tarih:** 15.08.2026 · **Kapsam:** DEV2-115'te (14.08) yapılan dry-run'ın ("format-lint v2 kapsamına `blog_content.py`/`static/*.js`/`*.css` eklensin mi") tek eksik kalan kısmı — Kategori 3 ("TL" yazımı, ₺ sembolü yerine) 53 kaydın tek tek sınıflandırması. JS/CSS tarafı zaten 0/0 (DEV2-115), Kategori 1-2 zaten 0/0 — bu doküman yalnız Kategori 3'ü kapatıyor. Bu turda hiçbir kod değişmedi; migrasyon kararı bu doküman ışığında CPO onayına bağlı (S7 desenine [[reference: docs/faz8-s7-30363d-siniflandirma.md]] birebir uyumlu).

## Kaynak veri

```
grep -c '\bTL\b' blog_content.py (mevcut format-lint Kategori 3 regex'i)  →  53 ham eşleşme
```

Yöntem: Python ile satır bazlı tam tarama (167 toplam "TL" geçişi, 53'ü sayı-bitişik desene uyuyor, 114'ü düzyazı/para-birimi-adı kullanımı) + her satırın bağlamı elle okunarak sınıflandırıldı.

## Sonuç tablosu (53/53)

| Kategori | Adet | Örnek | Değerlendirme |
|---|---|---|---|
| **GERÇEK TUTAR İHLALİ** — worked-example hesaplama (ATR/stop-loss/destek-direnç/temettü/pozisyon büyüklüğü) | **37** | `"ATR = 2.5 TL, giriş 85 TL... Stop = ... 81.25 TL"` (satır 1425-1426), `"100.000 TL portföy, %1 risk = 1.000 TL... 16.650 TL"` (satır 6407, tek satırda 6 kez) | Migrasyon adayı — site konvansiyonuna göre ₺ sembolü almalı |
| **GERÇEK TUTAR İHLALİ** — yuvarlak sayı / psikolojik seviye örneği | 5 | `"Yuvarlak sayılar (100 TL, 50 TL gibi)"` (1579), `"100 TL, 50 TL, 10 TL gibi yuvarlak rakamlar"` (6789) | Migrasyon adayı |
| **GERÇEK TUTAR İHLALİ** — eşik/minimum tutar tavsiyesi | 7 | `"Minimum 10.000 TL önerilir"` (1375), `"10.000-20.000 TL ile VİOP işlemine başlanabilir"` (4431), `"230.000 TL'yi (2026 tahmini sınır)"` (2747 — istisna tutarı, yıllık güncellenen resmi limit) | Migrasyon adayı |
| **GERÇEK TUTAR İHLALİ** — birikim/projeksiyon örneği | 2 | `"Aylık 1.000 TL yatırım... yaklaşık 270.000 TL"` (7149/7151) | Migrasyon adayı |
| **YANLIŞ-POZİTİF** — regex'in yanlış eşleştirdiği, gerçek tutar DEĞİL | **2** | `"BIST100 TL bazında yükselirken"` (806 — "BIST100" endeks adının parçası "100", "TL bazında" = para birimi cinsinden ifadesi, tutar değil), `"2018 TL krizi"` (6743 — "2018" bir YIL, "TL krizi" = "Türk Lirası krizi" ifadesi, tutar değil) | Migrasyona GİRMEMELİ — regex sayı-bitişiklik testi burada yanılıyor |
| **TOPLAM (regex ham eşleşme)** | **53** | | 37+5+7+2+2 = 53 ✓ |
| *(kapsam dışı, referans)* düzyazı/para-birimi-adı kullanımı ("TL değer kaybı", "dolar/TL", "TL bazlı") | 114 | `"TL'nin değer kaybettiği dönemlerde"` | İhlal DEĞİL — "TL" burada bir tutar değil, para biriminin kendisinin öznesi |

## Neden mekanik lint yeterli değil (DEV2-115'in "regex ikisini ayırt edemiyor" notunun somutlaşmış hali)

Kategori 3 regex'i (`\bTL\b` varlığı) hem 51 gerçek ihlali hem 2 yanlış-pozitifi aynı torbaya koyuyor — "sayıya bitişik mi" testi bile yetersiz: **806. satırdaki "BIST100"un içindeki "100" bir endeks adı parçası**, tutar değil; kelime sınırı regex'i bunu ayırt edemez. Bu, S7'nin "104 ham `#30363d`'nin 88'i statik, ama sınıflandırma mekanik grep ile yapılamaz" dersiyle aynı desen: format-lint v2'ye bu kategoriyi mekanik guard olarak eklemek, ilk günden itibaren en az 2 yanlış-pozitif üretecek bir kural eklemek anlamına gelir.

## Öneri (uygulama DEĞİL, yalnız öneri — S7 deseniyle birebir)

- **51 gerçek tutar ihlali** → `blog_content.py`'de sayı+"TL" kalıbı ₺ sembolüne çevrilir (örn. `"85 TL"` → `"₺85"` veya site konvansiyonunun kullandığı `"85₺"`/`"₺85"` sırası neyse ona göre — mevcut ₺ kullanım konvansiyonu diğer blog içeriğinde zaten var, aynı format tekrarlanır). Bu saf metin-formatı düzeltmesi, marka/renk/font kararı DEĞİL — CPO onayı yeterli olmalı (S7'deki "teknik/tutarlılık kararı" sınıfıyla aynı).
- **2 yanlış-pozitif** (806, 6743) → format-lint Kategori 3 kuralına GİRMEMELİ; ileride mekanik guard eklenirse bu iki satır için ya elle istisna listesi ya da daha sıkı bir regex (örn. `\d{1,3}(\.\d{3})*\s*TL\b` — bin ayracı olmayan çıplak "2018"/"100" gibi yıl/endeks numaralarını ayıklayan) gerekir.
- **114 düzyazı kullanımı** → hiç dokunulmaz, zaten doğru.

## Sıradaki

Migrasyon kararı (51 satırın ₺'ye çevrilmesi) CPO onayı bekliyor. Onay gelirse: 51 satır mekanik `sed`/script ile değil, worked-example bağlamları (özellikle 6407 gibi 6 farklı tutarın aynı satırda geçtiği hesaplama örnekleri) elle doğrulanarak değiştirilmeli — otomatik sed riski: `"90 TL"` gibi tekrarlayan değerlerin farklı bağlamlarda (destek fiyatı vs stop-loss fiyatı) yanlış sırayla değişmesi. T9.2/T1.7 (format-lint v2 wiring) bu migrasyon bitmeden devreye alınmamalı — aksi halde ilk gün 51 kırmızı satır + 2 kalıcı yanlış-pozitif üretir.
