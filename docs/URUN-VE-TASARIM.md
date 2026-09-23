# BorsaPusula — Ürün ve Tasarım Kanonu

> **Canlı belge.** Ozan'ın onayladığı ürün kararlarının ve sitenin tasarım dilinin **tek kaynağı**.
> Son güncelleme: **23.09.2026 22:00** (CPO). İş kuyruğu ve uygulama sırası: ops deposu `plans/2026-09-23-MASTER-PLAN.md`.
> Kural: yeni bir tasarım ya da ürün kararı önce taslak (mockup) olarak Ozan'a gider, onaydan sonra **önce bu belgeye**, sonra plana ve koda girer. CPO ve DEV1 ajanları dil kuralları ve tasarım dili için bu belgeyi okur.

---

## 1. Ürün yönü

- **Ana değer (Ozan, 23.09):** orta-uzun vadede yatırım yapılabilir şirketleri analiz etmek ve öne çıkarmak. Temel analiz ana eksendir; teknik trend **zamanlama** rolündedir.
- **Tek cümle:** "Her akşam BIST şirketlerini üç soruyla puanlıyoruz: finansalları nasıl, fiyatı makul mü, trend destekliyor mu?" Ana sayfa başlığı: **"Üç soruda BIST."** (O21).
- **Üç soru** (her hisse için): **Finansalları nasıl?** · **Fiyatı makul mü?** · **Trend destekliyor mu?** Hisse sayfasındaki özet kartının adı **"3 Soruda {HİSSE}"**.
- **Ürün tipi:** gün sonu (EOD). Sitede "ücretsiz" yazılmaz; ileride bazı analizler ücretli olabilir (Ozan). Gün içi canlılık makro şeritte (seansta 60 sn) ve ana sayfadaki "Seans içi · 15 dk gecikmeli" satırında.
- **Kapsam:** kademeli olarak Borsa İstanbul'daki tüm paylar (BIST TÜM, 584): önce BIST100'ün tamamı, sonra Yıldız Pazar, sonra kalanı. Gözaltı, Yakın İzleme ve Piyasa Öncesi İşlem Platformu'ndaki paylar kapsam dışı. Verisi yetersiz olan hisse "Sınırlı veri" etiketiyle gösterilir, listelere girmez.
- **Rakiplere göre konum** (23.09 incelemesi: Fintables, Midas, borsafolio, borsamix, borsacoo…): ücretsiz; Data-Art görsel kimliği; long-only ve tavsiye/hedef dili olmayan dürüst anlatım; sektör gruplu gerçek bir BIST100 ısı haritası (Türk rakiplerde yok); haberin site içinde, bizim verimizle okunması.

## 2. Kalıcı dil kuralları

1. **AL / SAT yazılmaz.** Durumlar: **Güçlü Trend** · **Yatay** · **Trend Bozuldu**.
2. **Teknik hedef dili yok:** TP1/TP2, "kâr al", "Hedef:" satırı, risk/ödül (R/R), "hedefe ulaştı", "prim potansiyeli". **İşlem yönetimi dili de yok** (CPO 23.09, O10'un devamı): "stop bölgesi", "stop seviyesi", "ideal giriş", "giriş bölgesi" yazılmaz; her durumda betimleyici "Trend dönüş seviyesi (Supertrend): X ₺ · fiyatın %Y altında/üstünde" kullanılır (3 Soruda Q3 tarifiyle aynı).
   - **İstisna:** analist hedef fiyatı bir değerleme göstergesidir ve kalır: "Analist hedef ortalaması X ₺ · fiyatın %Y üstünde · N analist". "Potansiyel" kelimesi ve "al" yeşili kullanılmaz; başlıkta (hero) gösterilmez.
3. **Long-only:** düşüşteki hisse "sat" demez, **sessizleşir**: soluk ton, katlanmış grup, kırmızı yok.
4. **Şirkete yargı değil, betim** (Ozan, 23.09): şirkete "Orta / Zayıf / sağlam değil" gibi etiket yazılmaz. Alan bazında betimlenir: "Nakit akışı güçlü, kârlılık zayıf". Skorlar sayı olarak yazılır: "57 / 100".
5. **Tek feragat:** sayfa başına 1 (en fazla 2) satır: "Bu sayfa bilgi amaçlıdır, yatırım tavsiyesi değildir."
6. **Karne/sicil yayınlanmaz** (O4). Kanıtsız başarı iddiası ("backtest ile doğrulandı" vb.) yazılmaz.
7. **Dürüstlük:**
   - Gün sonu ürünü "canlı" demez.
   - Gecikmeli veri "15 dk gecikmeli" diye yazılır.
   - Bayat veri görünür uyarıyla verilir: "Son veri 11.09 · güncellenmiyor" + sade neden.
   - **Göreli zaman yok** (Ozan, 23.09): gün sonu verisinin etiketinde "bugün / dün / günün" yazılmaz. Kesin tarih ("22 Eylül kapanışı") ya da "son seans" yazılır, çünkü veri ertesi gün de aynı görünür. Bölüm adları da buna uyar: "Günün hareketlileri" → "Son seansın hareketlileri", "Günün Gündemi" → **"Gündem"** (baskı tarihiyle: "23 Eylül · akşam baskısı"), tarama çipi "Son seansta Trend Bozuldu", takvimde "Bugün/Yarın" yerine tarih başlığı ("24 Eylül Perşembe").
   - **"Ücretsiz" yazılmaz** (Ozan, 23.09): amatör durur.
8. **Kaynak etiketi yok** (Ozan, 23.09): sitede rakamların ve haberlerin yanına kaynak yazılmaz. Doğruluk içeride sağlanır: KAP doğrulama kontrolü ve kaynak izi.
9. **Terimler:**
   - "Trend dönüş seviyesi (Supertrend)"
   - "BorsaPusula Skoru"
   - "Temel skor"
   - "RVOL" = 5 gün / 20 gün hacim oranı; "Günlük hacim oranı" = bugün / 20 gün
   - "Piyasa değeri"
   - "Özsermaye kârlılığı"
10. **Sayı biçimi (tr-TR):**
   - Yüzde önek: "%2,13", "+%2,13", "−%0,88". Eksi işareti U+2212.
   - Para: "299,75 ₺".
   - Büyük tutar: "409 Mrd ₺".
   - Tarih: "22 Eylül" / "22.09.2026".
   - Sayı sütunlarında `tabular-nums`.
11. **Türkçe büyük/küçük harf:** I↔ı ve İ↔i doğru çevrilir. Python `str.title()` / `lower()` doğrudan kullanılmaz (yoksa "ULAŞTIRMA" → "Ulaştirma" olur). JS'te `toLocaleUpperCase('tr-TR')` kullanılır.

## 3. Model

- **Durum:** 4 teknik koşuldan çıkar:
  1. Fiyat trend dönüş seviyesinin (Supertrend) üstünde.
  2. ADX ≥ 25.
  3. EMA 12 > EMA 99.
  4. DI+ > DI−.

  Koşullar **tak-çıkar** bir kayıtta tutulacak (plan D-47). Yeni koşul = kayda 1 satır + 1 test. Motor, API, hisse sayfasındaki koşul listesi ve /metodoloji aynı kayıttan okur (ikinci kanon yok).
- **BorsaPusula Skoru (yönlü, O2):** Finansallar (Temel skor) %60 + Trend %40.
  - Trend payı Güçlü Trend'de max(50, Teknik Güç), Yatay'da 50, Trend Bozuldu'da min(50, 100 − Teknik Güç).
  - Örnek (22.09): MGROS eski formülle 56, yönlü formülle 47. THYAO 61 → 57.
- **Temel skor:**
  - Bugün 4 kategori: kârlılık, nakit akışı, borç durumu, değerleme ve büyüme.
  - v2'de 5 eksen: kalite, değerleme/ucuzluk, büyüme, bilanço sağlığı, temettü. Sektör şablonları banka, sigorta ve GYO için.
  - Çeşitlendirme araştırması: ops `plans/2026-09-23-denetim/temel-cesitlendirme.md`.
- **Veri tanımları (23.09, `temel-cesitlendirme.md` ile KAP'a karşı doğrulandı):**
  - **Açıklanan veri ilkesi (Ozan, 23.09): temel analiz yalnız şirketin açıkladığı gerçek rakamlarla yapılır.** Kaynak KAP'taki finansal raporlardır. Her rakam hangi rapordan geldiğiyle birlikte **içeride** saklanır ve doğrulanır. **Sitede kaynak yazılmaz** (Ozan, 23.09: "hiçbir yerde kaynak belirtmemize gerek yok, sadece biz doğru olduğundan emin olalım"). **Kendi enflasyon/TÜFE düzeltmemizle rakam üretilmez.**
  - **Neden?** Enflasyon muhasebesinde (TMS 29, 2023'ten beri) şirket her yıllık raporda önceki yılı yeni yılın parasıyla yeniden yazar. Aynı yıl iki raporda iki farklı rakamla yer alır (TBORG 2023 cirosu: 2023 raporunda 17,14, 2024 raporunda 24,75 mlr TL). Yahoo her yıl için en son yazılmış rakamı alır. Sütunlar farklı raporlardan, farklı birimlerle geldiği için aralarındaki fark büyüme değildir (TBORG 2024: Yahoo farkı +%59,4, şirketin kendi raporu +%21,8).
  - **Büyüme** = şirketin aynı rapordaki cari yıl ile karşılaştırmalı yıl farkı, yani şirketin açıkladığı değişim. Her yılın değişimi o yılın kendi raporundan alınır. Farklı raporlardan gelen tutarlar tek seride birleştirilmez. Yahoo'nun `revenue_growth` alanı (tek çeyreğin nominal yıllık farkı) büyüme diye kullanılmaz.
  - **Çok yıllı grafik:** her yıl için "şirketin açıkladığı yıllık değişim" çubuğu. Tutar olarak yalnız son raporun iki yılı yan yana gösterilir (aynı birim, raporun kendi birim başlığıyla).
  - **Değerleme bandı:** yıl sonu piyasa değeri ÷ o yılın raporunda açıklanan özkaynak ya da net kâr. Aynı tarih, aynı birim; düzeltme yok.
  - Muhasebe esası (TMS 29 / nominal banka-sigorta / TL'ye çevrilmiş döviz / USD-EUR raporlayan) her hisse için bilinir ve gösterilir.
  - **Temettü verimi** = son 12 ayın gerçek ödemeleri / fiyat, etiketi "Temettü (son 12 ay)". Ödeme yoksa "Ödeme yok" yazılır. Yahoo'nun hazır oranı kullanılmaz; THYAO'da %2,28 gösteriyordu, oysa ödeme yok.
  - **Net borç** kiralamalar dahil hesaplanır. Oranlar (marj, ROE, borç/özkaynak) tek dönem içinde hesaplandığı için yamadan etkilenmez; tutarlar ve yıllar arası değişimler etkilenir.
  - Çeyrek serisinden yıllık toplam (TTM) ya da çeyreklik büyüme hesaplanmaz. **Çeyreklik değişim** yalnız o çeyreğin kendi raporundaki "3 aylık" cari/karşılaştırmalı sütunlarından okunur; dördüncü çeyrek ayrıca açıklanmadığı için yıllık rapordan türetilmez (yıllık − 9 ay iki raporun parasını karıştırır).
  - **"Son 12 ay" kârı (O22, varsayılan B — Ozan cevabı bekleniyor, son tarih 27.09 12:00):** son yıllık rapordaki kâr + içinde bulunulan yılın son ara dönem raporunda açıklanan fark (cari dönem − geçen yılın aynı dönemi, ikisi aynı rapordan). F/K ve özsermaye kârlılığı bununla hesaplanır. Doğrulama (22.09): Tüpraş F/K son yıllık kârla 25,9, bu yöntemle 11,3 (piyasa 11,3); Garanti BBVA 5,1 → 4,7 (piyasa 4,7). O22=A seçilirse yalnız son yıllık kâr kullanılır ve yanına ara dönem değişimi yazılır.
  - **PD/DD** = piyasa değeri ÷ son açıklanan (ara dönem dahil) ana ortaklık özkaynağı. **Değerleme bandı** = son beş yıl sonu değerleri (yıl sonu piyasa değeri ÷ o yılın raporu) + son kapanış + sektör ortancası (KAP sektörü, ≥5 şirket; banka ortancası 10 bankadan).
  - **Değişim grafikleri** yalnız aynı muhasebe esasındaki yılları gösterir: TMS 29 uygulayan şirkette 2023 ve sonrası (2022 ve öncesi raporlar düzeltmesiz); bankada tüm yıllar nominal ("nominal TL" birim notu). Marj ve özsermaye kârlılığı gibi oranlar yıllar boyunca gösterilir; son ara dönem ayrı, kesikli bir noktadır.
  - **Sağlamlık kontrolü:** sanayide Piotroski F-Skor'un 9 maddesi (son yıllık raporun iki sütunu); bankada 5 madde (net kâr > 0, özsermaye kârlılığı banka ortancasının üstünde, kredi/mevduat ≤ %100, özkaynak büyümesi ≥ varlık büyümesi, gider/gelir ≤ %40; takipteki kredi oranı rapor dipnotundan eklenecek). Madde "geçti / geçmedi" gösterilir, iki yılın değeriyle.
  - **Temettü geçmişi:** hisse başına brüt ödeme, ödendiği yılın parasıyla, bugünkü pay adedine göre (bedelsiz sonrası düzeltilmiş); açıklanmış ama ödenmemiş taksit son 12 ay verimine girmez.
  - **KAP okuma notu (23.09):** banka bilançoları 6 sütunlu (TP/YP/Toplam × cari/önceki); ilk 4 sayıyı alan basit okuyucu yanlış sütun verir. Sütun başlığına göre okuyan ayrıştırıcı: ops `plans/2026-09-23-denetim/kanit/tc/frparse.py`.
- **Veri:** Yahoo (yfinance) + KAP (O19=B: şimdilik ücretsiz). Bilinen sınırlar:
  - 4-5 yıl ve 5-7 çeyrek derinlik.
  - TMS 29 (enflasyon muhasebesi) farkları.
  - USD/EUR raporlayan şirketler: oranlar TL'ye çevrilerek hesaplanır, not düşülür.
  - Bankalarda BDDK kuralı farklı.

  Sitede "derin / 10 yıllık" iddiası yazılmaz. Lisanslı sağlayıcı teklifi ve BIST fiyat yayın lisansı konusu Ozan'dadır.
- **Yapay zekâ (O5b=A, "Analist Notu"):** günde bir toplu çalışır; yalnız sitenin kendi verisini ve KAP metnini okur.
  - Rakamları AI yazmaz; kod yerleştirir.
  - Yayından önce doğrulayıcı çalışır: sayı eşitliği + yasak dil (AL/SAT, teknik hedef, "tavsiye").
  - Metnin üstünde yalnız "AI ile yazıldı" etiketi olur (kaynak etiketi yok).
  - Web araması yalnız "Gündem"de yapılır. Kaynaklar içeride doğrulama için tutulur.
  - Önce 10 hisselik pilot yapılır; iki model yan yana okunup seçilir.

## 4. Bilgi mimarisi

- **Menü (O17=A; "Bugün" → "Piyasa", göreli zaman kuralı):** Piyasa · Keşfet · Haberler · Takip · Öğren (+ arama). Masaüstü ile mobil aynı.
- **Hisse sayfası:** 4 sekme — Özet · Grafik · Temel · Haberler. Özet'in sırası (C-M1 v2):
  1. Başlık: kimlik (kod, ad, sektör) + fiyat + günlük değişim ve kapanış günü + **4 temel gösterge** (Piyasa değeri · Özsermaye kârlılığı · Net kâr marjı · Temettü verimi) + eylemler (Takip et · Paylaş · Karşılaştır) | 1A/3A/1Y alan grafiği. **Başlıkta teknik durum hapı yok.**
  2. Sekme şeridi (mobilde yapışkan).
  3. **3 Soruda {HİSSE}** kartı (§5.6).
  4. Son haberler (3 KAP satırı → Haberler sekmesi).
  5. Kapalı akordeonlar: Teknik ayrıntılar; Sık sorulanlar ve yöntem (SEO metni DOM'da kalır).
  6. Tek feragat satırı.
- **Ana sayfa blok sırası (C-M2 taslağı):**
  1. Canlı makro şerit ("BIST verisi 15 dk gecikmeli").
  2. Kahraman: H1 **"Üç soruda BIST."** (O21=A) + tek cümle + 3 soru çipi + arama.
     - Arkada gerçek BIST100 son 30 gün dalgası: yükseliş/düşüş günleri alanda hafif yeşil/kırmızı. Kapanış kutusunda gün sonu değeri.
     - Seans içinde kutunun altında "Seans içi · 15 dk gecikmeli: BIST100 … BIST30 …" satırı; seans dışında gizli.
     - Sahte dalga yok.
  3. Tüm kapsamın durum şeridi (her çizgi bir hisse; yeşil / arduvaz / koyu).
  4. Güçlü Trend kartları: gün sayısı + BP halkası + "Finansallar" betimi.
  5. **BIST100 ısı haritası.**
  6. Son seansın hareketlileri 5+5 (tavan/taban etiketi).
  7. Öne çıkan şirketler: yazılı kural, 3 soru sütunu.
  8. Haberler: Gündem + şirket haberleri.
  9. Akşam Bülteni aboneliği.
  10. Tek feragat.
- **Haberler (W9):**
  - **Gündem:** Türkiye + Dünya; günde 2 baskı (~08:30 ve ~19:30); 5-8 madde. Her madde en az iki bağımsız kaynakla içeride doğrulanır; gün içi fiyat hareketi kapanışla karışmasın diye "gün içinde" diye yazılır (ör. "Brent gün içinde yeniden 100 doları aştı", kapanış 98,44). Her madde içeride güvenilir bir kaynakla doğrulanır; sayfada kaynak etiketi yok. Her maddede ilgili hisse/sektör çipleri var. Başka sitelerin metni kopyalanmaz.
  - **KAP akışı:** her bildirim site içinde kalıcı bir sayfa: tek cümle özet, önem oranı ("sözleşme tutarı yıllık hasılatın %4,7'si"), orijinal metin. Dış bağlantı ve kaynak etiketi yok. Rutin duyurular elenir.
  - **Takvim** sekmesi.
  - **Akşam Bülteni** `/bulten/<tarih>`.
- **Keşfet:** tarama + 4 hazır liste (Kaliteli ve makul fiyatlı · İstikrarlı temettü · Borçsuz büyüyenler · Sektörüne göre ucuz) + `/sektor-harita` tam ekran ısı haritası.

## 5. Tasarım dili (Data-Art)

### 5.1 İlke
Koyu tek tema. Cüretkâr, veriyi kodlayan görseller; referans ana sayfanın Data-Art dilidir, sadelikte Robinhood/Linear. Jenerik 4'lü KPI ızgarası ve eşit kart duvarı yok; her blok bir soruya cevap verir. Cüret tek yerde harcanır (sayfanın imza öğesi), çevresi sakin kalır.

### 5.2 Renk tokenları (`static/css/tokens.css`)
| Token | Değer | Rol |
|---|---|---|
| `--bp-bg` | #0e0e12 | zemin |
| `--bp-surface` / `2` / `3` | #141416 / #1c1b1f / #201f21 | yüzeyler |
| `--bp-border` / `2` | #2a2a2c / #46464d | çizgiler |
| `--bp-text` / `2` / `3` | #e5e1e4 / #c7c5cd / #909097 | metin |
| `--bp-brand` | #b8c3ff | marka periwinkle; birincil düğme, grafik çizgisi, aktif sekme |
| `--bp-al` | #00e290 | yükseliş, Güçlü Trend, BP Skoru kimliği, logo "Pusula" |
| `--bp-sat` | #f85149 | yalnız fiyat düşüşü |
| `--bp-accent-cyan` | #22d3ee | Temel skor kimliği, odak halkası |
| `--bp-art-violet` | #7c5cff | Teknik kimliği, logo gradyanı, dekoratif parıltı |
| `--bp-art-magenta` / `-orange` | #ff37d8 / #ff9d2e | yalnız dekoratif (ana sayfa sanatı) |
| `--bp-stale` | #f5c949 | bayat veri uyarısı |
| (yeni) arduvaz | #343a48 | Yatay durumu |

### 5.3 Renk rolleri
- **Yeşil ve kırmızı yalnız fiyat değişimi ve yön** için. Skorlar kimlik rengiyle çizilir: BP yeşil, Temel camgöbeği, Teknik mor (O12). Puan bandı renkle değil, sayıyla verilir.
- **Durum renkleri:**
  - Güçlü Trend: yeşil dolu hap, koyu metin.
  - Yatay: arduvaz #343a48.
  - Trend Bozuldu: koyu #232228, sessiz metin #b9b7c0 (kırmızı değil).
- **Grafik çizgisi** nötr periwinkle, gradyan dolgulu. Yeşil ya da kırmızı değildir; dönem değişimi yazıyla verilir.
- **Açık zemin** (belge, profil): yeşil #00a86b'ye koyulaşır.

### 5.4 Tipografi
- **Bricolage Grotesque 800:** fiyat, sayfa başlıkları, "3 Soruda" başlığı, sektör etiketleri, logo yazısı.
- **Space Grotesk:** veri, arayüz, sayılar (`tabular-nums`). Plan W2 kararıyla gövde metni de Space Grotesk'e geçer. Taslaklarda gövde için Manrope kullanıldı; uygulamada Manrope kalkar. Hedef: 2 aile, ≤70 KB, self-host.
- **Ölçek:** hero clamp(56–88) · display clamp(32–52) · title 24 · stat 32 · lg 18 · body 15 · sm 13 · xs 11 (yalnız büyük harfli etiket, harf aralığı ~.12em). Veri metni ≥13px.
- **Fiyat:** masaüstü 64–66px, mobil 40–42px, mobilde y ≤ 200px.

### 5.5 Biçim
- Köşe yarıçapı 4 kademe (6 / 10 / 20 / hap). Isı haritası kutusu 5px; kartlar 16–22px.
- Boşluk 8 kademe (4–64).
- Doku: %5 opaklıkta tanecik (grain) ve ölçülü radyal parıltılar (mor/camgöbeği). Yeşil yalnız 3 Soruda kartında.
- Odak: 2px camgöbeği halka. Hareket: `prefers-reduced-motion`'a saygı.

### 5.6 Bileşenler
- **3 Soruda {HİSSE} kartı:**
  - Başlık: "3 Soruda THYAO" (Bricolage).
  - Sağda BP halkası (yeşil, "57 / 100", alt satır "Finansallar %60 · Trend %40 (yönlü)").
  - Üç sütun (mobilde alt alta):
    1. **Finansalları nasıl?** Betimleyici cevap ("Nakit akışı güçlü, kârlılık zayıf"), Temel skor halkası (camgöbeği), 4 kategori çubuğu, tek cümle açıklama.
    2. **Fiyatı makul mü?** Cevap "Ucuz tarafta / Makul / Pahalı tarafta / Karışık". F/K ve PD/DD, sektör (akran <3 ise BIST) medyanıyla. Analist hedef satırı nötr. Para birimi notu (USD raporlayan).
    3. **Trend destekliyor mu?** Cevap "Evet · N gündür / Henüz değil · Yatay / Hayır · Trend Bozuldu". Teknik hüküm cümlesi, 4 koşul listesi (✓ / –), trend dönüş seviyesi satırı.
- **Skor halkası:** iz #26262c, yuvarlak uçlu yay, ortada sayı (Bricolage).
- **Temel hap bilgi (başlık):** 4 küçük kutu (etiket + değer), kimlik renksiz: Piyasa değeri · Özsermaye kârlılığı · Net kâr marjı · Temettü (son 12 ay).
- **Alan grafiği:** 1A / 3A / 1Y. Son nokta başlık fiyatına eşit (tek fiyat kaynağı). Başlangıç kesikli çizgisi, dokununca tarih ve fiyat.
- **BIST100 ısı haritası** (C-M5 onaylı; O16d=A, O20=A):
  - Kutu alanı = piyasa değeri (pay adedi × kapanış; sanity bandı 0,8–1,25). Hisseler KAP sektör kümelerinde (squarified treemap).
  - **3 renk modu:**
    - Değişim (varsayılan): ıraksak kırmızı ↔ nötr #1f1f25 ↔ yeşil.
    - BP Skoru: mor ↔ nötr ↔ yeşil, 50 merkezli.
    - Trend: kategorik. Kapsam dışı taralı.
  - **5 dönem** ve renk tavanı: 1G ±%3 · 1H ±%6 · 1A ±%12 · YB ±%50 · 1Y ±%80.
  - Üstte **nabız şeridi**: 100 hisse en kötüden en iyiye.
  - Sektör etiketinde ağırlıklı değişim.
  - Büyük kutularda 30 günlük çizgi.
  - Tavan/taban: parlak çerçeve + "▲ TAVAN / ▼ TABAN" etiketi.
  - Dokununca mini kart; hisse sayfasına bağlanır.
  - Mobilde sektörler alt alta, her biri kendi haritasıyla.
  - Gün sonu görüntüsü kapanıştan sonra dondurulur.
- **Koşul listesi:** ✓ (yeşil daire) / – (gri daire) + koşul adı + değer.

### 5.7 Logo v2 — A "Yumuşak Yıldız" (O7b=A)
```svg
<svg viewBox="0 0 120 120">
  <defs><linearGradient id="bpg" x1="18" y1="18" x2="102" y2="102" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#7c5cff"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs>
  <circle cx="60" cy="60" r="44" fill="none" stroke="url(#bpg)" stroke-width="7" stroke-linecap="round"
          stroke-dasharray="232 44.5" transform="rotate(-18 60 60)"/>          <!-- kuzeydoğuda açık çember -->
  <path d="M60 25 C62.8 50.5 69.5 57.2 95 60 C69.5 62.8 62.8 69.5 60 95 C57.2 69.5 50.5 62.8 25 60 C50.5 57.2 57.2 50.5 60 25 Z"
        fill="url(#bpg)" stroke="url(#bpg)" stroke-width="5" stroke-linejoin="round"/>  <!-- kavisli, yuvarlak uçlu yıldız -->
  <circle cx="91.1" cy="28.9" r="6.5" fill="#00e290"/>                         <!-- yön noktası -->
</svg>
```
- **Küçük boy (16–32 px):** çember kalınlığı 11, yıldız kontur 7, nokta 9.
- **Yazı:** Bricolage Grotesque 800, harf aralığı −.03em. "Borsa" metin rengi, "Pusula" #00e290 (açık zeminde #00a86b).
- **İsteğe bağlı alt satır:** "PİYASANIN YÖNÜ" (Space Grotesk 600, harf aralığı .2em).
- **Tek kaynak:** `_brand.html` makrosu. Kullanıldığı yerler: header, footer, favicon, PWA ikonları, og görseli, hata sayfaları, e-posta başlığı.

### 5.8 Mobil
- Sabit krom ≤152px (390×844).
- Fiyat 40px+ ve y ≤ 200.
- Sekme şeridi yapışkan.
- Dokunma hedefi ≥44px.
- Tablolar tek temsil. Isı haritası sektör yığını düzeninde.

### 5.9 Erişilebilirlik
- Kontrast WCAG AA.
- Renk tek başına anlam taşımaz: +/− işareti, tavan/taban etiketi, ✓/–.
- Klavye: sekmeler ok tuşlarıyla gezilir, açılır paneller Esc ile kapanır, odak görünür.
- `reduce-motion` açıkken animasyon yok.

## 6. Onaylı taslaklar

| Taslak | Bağlantı | Kopya (ops deposu) | Karar |
|---|---|---|---|
| BIST100 ısı haritası | https://claude.ai/artifact/XgdfkJQthV1iNrCzw5fMx4 | `plans/mockups/isi-haritasi.html` (+ `heatmap_data.json`, `build_heatmap_data.py`) | O16d A, O20 A (Değişim) |
| Logo v2 | https://claude.ai/artifact/BnQg57WyCGg7X7LtgVJmMZ | `plans/mockups/logo-v2.html` | O7b A (Yumuşak Yıldız) |
| Hisse Özet v2 | https://claude.ai/artifact/6Rx4X5tZFouMqN2bYUc1Qp | `plans/mockups/hisse-ozet.html` (+ `hisse_data.json`, `build_hisse_data.py`) | O16a B → notlarla v2 (23.09 16:2x) |
| Ana sayfa v2 | https://claude.ai/artifact/YDcRh13QSYCp3znHcVDo7y | `plans/mockups/anasayfa.html` (+ `home_data.json`, `build_home_data.py`) | O21 A ("Üç soruda BIST."), O16b B → notlarla v2 (23.09 21:5x), v3 "Gündem" adı |
| **Temel sekmesi v2 + Keşfet listeleri** (karar bekliyor) | https://claude.ai/artifact/6bQEHgLCJj8EqwsepfzwfR | `plans/mockups/temel-v2.html` (+ `temel-v2.tpl.html`, `build_temel_mock.py`; veri ops `kanit/tc/temel_data_TUPRS_GARAN.json`) | O16e + O22 bekliyor, son tarih 27.09 12:00 |
| **Tarama v2** (karar bekliyor) | https://claude.ai/artifact/MimW7U5gPTeFiFJdeRbtNQ | `plans/mockups/tarama.html` (+ `build_tarama_data.py`) | O16c bekliyor, son tarih 27.09 12:00 |
| **Haberler** (karar bekliyor) | https://claude.ai/artifact/45h9DvBjYLPSEm4Ct2apLE | `plans/mockups/haberler.html` (+ `build_haberler.py`, `haberler_data.json`; iç kaynak listesi `haberler_gundem_kaynaklari_ic.md`) | O16f bekliyor, son tarih 28.09 12:00 |
| **Takip** (karar bekliyor) | https://claude.ai/artifact/9u3m9ABRTcLiYUwVmCnnKX | `plans/mockups/takip.html` (+ `takip_data.json`, `build_takip_data.py`) | O16g bekliyor, son tarih 28.09 12:00 |
| 2. karar raporu | https://claude.ai/artifact/PtemWS4fRXGbiX5MSwbmCr | `ozan-dispatch/2026-09-23-1330-KARAR-ikinci-tur.md` | O1b, O5b, O6b, O11b, O17, O18, O19 |
| 1. karar raporu (dönüşüm planı) | https://claude.ai/artifact/F33GWwbEgqmGZ7q33QtGNb | `ozan-dispatch/2026-09-23-0850-KARAR-master-plan.md` | O1–O16 |

Taslak kodu bu depoya girmez: taslaklar ops deposunda durur, uygulama bu belgeye ve plana göre yapılır.

## 7. Karar kaydı (Ozan)

| # | Tarih | Karar |
|---|---|---|
| 17 | 23.09 | **Ana değer:** orta-uzun vade yatırım yapılabilir şirketler; temel analiz derinleşir ve genişler; ana sayfada sektör mozaiği yerine BIST100 hisse bazlı gün sonu ısı haritası. |
| O1 / O1b | 23.09 | Tek cümle A; hisse sayısı artacak. Cümle "Finansalları nasıl?" sorusuyla tutarlı hale getirildi (§1). |
| O2 | 23.09 | Yönlü BP Skoru, long-only. Tasarım CPO'ya bırakıldı (§2.3, §3). |
| O3 / O17 | 23.09 | 5 öğeli menü + Haberler. Takvim, Haberler'in sekmesi. Haberler yalnız KAP değil; günün Türkiye ve dünya gündemi de verilir. |
| O4 | 23.09 | Karne (/sicil) yok. |
| O5 / O5b | 23.09 | AI: "Analist Notu" (§3). |
| O6 / O6b | 23.09 | Çalışma modeli hibrit: iki zamanlanmış ajan uygular; etkileşimli oturum karar, taslak ve acil sorunlar için. |
| O7 / O7b | 23.09 | Logo yeşil kalır, yumuşak hatlı, her yerde aynı → A "Yumuşak Yıldız" (§5.7). |
| O8 | 23.09 | SSS'teki "prim potansiyeli nedir?" sorusu "{hisse} teknik görünümü nasıl?" olur. |
| O9 | 23.09 | PWA ölçüm parametresi kalkar, mağaza görseli şimdilik yok. |
| O10 | 23.09 | Teknik hedef dili yok. **Düzeltme:** analist hedef fiyatı değerleme göstergesi olarak kalır (§2.2). |
| O11 / O11b | 23.09 | "Otomatik özet" değil → **"3 Soruda {HİSSE}"**. Feragat 7'den 2'ye. |
| O12 | 23.09 | Halkalar sitenin diliyle: kimlik renkleri (CPO kararı, §5.3). |
| O13 | 23.09 | Tek alarm kanalı e-posta; makro şerit olabildiğince canlı (seansta 60 sn). |
| O14 | 23.09 | "Listemi getir" kodu silinir; gereksiz ne varsa kaldırılır (sadelik). |
| O15 | 23.09 | 5 saniye testi tasarım işleri bitince yapılır (Ozan). |
| O16 | 23.09 | Amiral sayfalar önce taslak. O16d ısı haritası A · O20 ilk renk Değişim · O16a hisse B (notlar §4, §5.6'ya işlendi). |
| O16a notları | 23.09 | Başlıkta teknik durum yok, yerine temel bilgi. "Şirket sağlam mı?" → "Finansalları nasıl?"; yargı değil betim. Temel veriyi çeşitlendirme araştırması (3. tura). 3 Soruda'dan önce küçük temel hap bilgi. **Teknik koşullar tak-çıkar olmalı** (D-47). |
| O18 | 23.09 | Kapsam kademeli BIST TÜM; riskli pazarlar hariç. |
| O21 / O16b | 23.09 | Ana sayfa başlığı "Üç soruda BIST.". Taslak değişiklikle: endeks eğrisinde hafif yön tonları; göreli zaman yok (menü "Piyasa"); seans içi BIST100/BIST30 satırı; "Ücretsiz" yazılmaz. |
| O19 | 23.09 | Şimdilik Yahoo + KAP; lisanslı sağlayıcı teklifi ve BIST fiyat lisansı Ozan'da. |

## 8. Bu belge nasıl güncellenir
- Ozan'dan yeni bir karar gelince önce §7'ye satır eklenir, sonra ilgili bölüm düzeltilir, sonra plana (ops `MASTER-PLAN` §8) işlenir.
- Tasarım dilini değiştiren her şey (renk, font, bileşen) önce taslakla Ozan'a gider. Onaylanmadan bu belge ve kod değişmez.
- Belge ile kod çelişirse **belge esastır** ve çelişki bir iş maddesi olarak plana yazılır.
