# FAZ8 Backlog Sınıflandırması — "Gerçek mono font" iddiası

**Tarih:** 17.08.2026 · **DEV2-142** · **Kod değişmedi** (saf sınıflandırma/envanter turu)

## Backlog cümlesi (Master Dönüşüm Programı, Bölüm 3, FAZ8 Tipografi/performans)

> "Gerçek mono font (fiyat/yüzde hizası için — Space Grotesk mono DEĞİL, şu an rakamlar hizasız)"

## Yöntem

S1/S7/T3.4/T5.2/T5.4/T8-tipografi/T8-başlık/T1.5/anasayfa-yük/api-macro/api-data/template-literal serisiyle aynı desen: Workflow ile **3 paralel salt-okur sınıflandırma ajanı** (tablo/liste sayfaları · tekli-varlık detay sayfaları · JS format katmanı+tokens.css — birbirini görmedi) → **1 sentez ajanı** → **1 tamamen bağımsız kör doğrulama ajanı** (sentezi görmeden kendi SSH grep+read turunu sıfırdan yaptı). Hiçbir dosya değiştirilmedi.

## Sonuç — iddia büyük ölçüde BAYAT/YANLIŞ, küçük bir gerçek çekirdek var

**Ana bulgu:** `font-variant-numeric:tabular-nums` (rakam genişliğini eşitleyen standart CSS tekniği, gerçek monospace font gerektirmez) site genelinde **10 dosyada 55-65 kez** (grep deseni farkına göre değişiyor) zaten uygulanmış — index/hisse/varlik/tarama/ozet/sektor_harita/kategori/sinyal_performans şablonlarının tamamında ve `bp-search.js`'de. Ayrıca gerçek bir OS-native monospace stack (`--bp-font-mono: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas...`, tokens.css:476) **zaten token olarak var ve 9 şablonda fiilen kullanılıyor** — en kritik gerçek-`<table>` yüzeyi olan `karsilastir.html`'deki hisse karşılaştırma tablosu dahil.

`tokens.css:459-467` kod tabanının kendi yorumu bunu önceden belgelemiş: "SAYISAL/TABULAR eksen — fiyat, ticker, oran. Canlıda 'Space Grotesk', monospace, sans-serif yazımıyla ve **daima** font-variant-numeric:tabular-nums ile birlikte geçiyor. BU EKSEN TOKEN ALMADI — Ozan'ın marka kararı (`--bp-font-num` planlı, henüz açılmamış)." Yani "gerçek mono font yok, rakamlar hizasız" iddiasının teknik önermesi (mono font olmadan hizalama sağlanamaz) **yanlış temelli** — `tabular-nums` proportional fontta bile rakamları eşit genişlikte render eder, ve kod tabanı bu çözümü zaten bilinçli şekilde uygulamış.

**Bağımsız doğrulama ajanının nihai değerlendirmesi:** "İDDİA BAYAT / BÜYÜK ÖLÇÜDE YANLIŞ" — api-macro/api-data/template-literal serisiyle aynı sınıf.

## Küçük gerçek çekirdek — kapsam tutarsız, migrasyon değil tek-satır ekleme yeterli

Sentez ve sınıflandırma ajanları, iddianın "rakamlar hizasız" kısmının tamamen çürümediğini not etti: `tabular-nums` kapsaması **tutarsız** uygulanmış, aynı bileşende bir alan kapsanmışken bitişiği kapsanmamış. Somut örnekler (migrasyon kararı değil, yalnız envanter — CPO/Ozan onayı olmadan uygulanmadı):

- `hisse.html:3380/3387` — Sinyal Geçmişi tablosunda Giriş Fiyatı sütunu `tabular-nums`'lı ama bitişik Getiri% sütunu değil (aynı satırda kanıtlı tutarsızlık)
- Makro ticker bandı deseni — 5 sayfada (`hisse.html`, `varlik.html`, `kategori.html`, `ozet.html`, `gundem.html`) tekrarlanan `.macro-item`/`.sc-price` kalıbı, çoğu kapsam dışı
- `gundem.html` — **sayfa genelinde sıfır `tabular-nums`** (bağımsız doğrulama da bunu ayrıca teyit etti), tek dosyada en yoğun açık
- `sektor_harita.html:259` `.cmp-stock-rvol` — bilinçli sütun hizalaması (`min-width:38px; text-align:right`) var ama `tabular-nums` yok
- `kategori.html:73,85,86` `.ac-chg/.ac-adx/.ac-sl` — asset kart grid'i, fiyat kapsanmış değişim%/gösterge değil
- `bilanco_takvimi.html:113` `.sc-price` — bağımsız doğrulama turunda da ayrıca bulunan tek izole boşluk

## Değerlendirme

Backlog maddesinin önerdiği kapsamlı "gerçek mono font migrasyonu" **gereksiz** — teknik çözüm (tabular-nums) zaten kurulu ve yaygın. Gerçek kalan iş (varsa) mevcut `.xx-price{tabular-nums}` deseninin birkaç eksik class'a/sayfaya (özellikle gundem.html) yayılması — tek satırlık CSS eklentisi sınıfında, yeni font yükleme/token migrasyonu değil. `--bp-font-num` token'ının resmileştirilmesi ayrı, marka kararı gerektiren bir konu (zaten S1/S7/T5.2/T5.4/T8-tipografi ile aynı karar kuyruğunun kapsamında olabilir, ama bu backlog maddesinin iddia ettiği "rakamlar hizasız" bug'ı değil).

**Aksiyon gerekmiyor.** Kod değişmedi. Migrasyon/tamamlama isteniyorsa CPO onayı sonrası ayrı, düşük-riskli bir T-kodu olarak ele alınabilir.
