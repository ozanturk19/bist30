/* BorsaPusula — KANONİK VARLIK SÖZLÜĞÜ (Master Program T1.3)

   NE ÇÖZÜYOR
   ──────────
   Makro şeridi 17 şablonda render ediliyor ve etiket/ondalık haritası
   17 YERDE AYRI AYRI kopyalanmıştı — 4 farklı değişken adı altında
   (_ML / MACRO_LABELS / LABELS / L) ve 5 farklı anahtar kümesiyle.
   Kopyalar zamanla ayrıştı; sonuç kullanıcıya görünen çelişkiydi:

     ALTIN  -> "Altın"  10 şablonda   |  "ALTIN"  7 şablonda
     GUMUS  -> "Gümüş"  10 şablonda   |  "GÜMÜŞ"  7 şablonda
     PETROL -> "PETROL"  4 şablonda haritalı, 13 şablonda HİÇ YOK
               (`_ML[k]||k` fallback'i ham anahtarı basıyordu, yani
               "Altın · Gümüş · PETROL" gibi kendi içinde tutarsız şerit)

   Ondalık tarafında da 3 aile vardı (14 / 9 / 7 anahtar). Ondalıklar
   TESADÜFEN aynı sonucu veriyordu: eksik anahtarlar `??2` fallback'ine
   düşüyor, kanonik değer de zaten 2. Yani ondalık çatalı GÖRÜNMEZDİ ama
   LATENTTİ — haritaya ALTIN:3 gibi bir değer eklendiği an 10 şablon
   sessizce eski değerde kalırdı. Bu dosya o tuzağı kapatıyor.

   KANONİK KARARLAR (gerekçeli — CPO geri çevirebilir)
   ───────────────────────────────────────────────────
   1. Başlık-Harf kazandı: "Altın", "Gümüş", "Petrol".
      Gerekçe (a) çoğunluk: 10/17 şablon zaten böyle yazıyordu.
      Gerekçe (b) iç tutarlılık — şeritteki DİĞER hiçbir kalem BÜYÜK
      HARF değil: BIST100, BIST30, USD/TRY, EUR/TRY, BTC, S&P500,
      NASDAQ. "ALTIN" tek başına aykırıydı, kural değil istisnaydı.
      Bu bir marka/zevk kararı değil tutarlılık kararı olduğu için
      dur-ve-sor listesine alınmadı; CPO aksini isterse tek satır.

   2. Ondalık kümesi 15-anahtarlı üst kümedir. Hiçbir mevcut değeri
      DEĞİŞTİRMEZ — yalnız eksik anahtarları açık hale getirir.

   3. Anahtar bilinmiyorsa etiket olarak ham anahtar döner (şeridin
      boş kalmaması için) AMA bu bir kusur işaretidir: payload'a yeni
      bir varlık eklenirse buraya da eklenmelidir. bpAssetLabelIsKnown()
      ile sorgulanabilir; T1.7 format-lint bunu guard'layabilir.

   ÖLÜ ANAHTARLAR — bilerek duruyor, silinmedi
   ────────────────────────────────────────────
   /api/macro bugün 10 kalem yayınlıyor:
     XU100 XU030 USDTRY EURTRY BTC ALTIN GUMUS PETROL SP500 NASDAQ
   Haritada bunlara ek olarak ETH, SOL, BNB, DOGALGAZ ve BIST30 var.
   Bunlar payload'da YOK — 4 şablondaki eski kopyalardan devralındı.
   ESKİ GEREKÇE GEÇERSİZ (CPO-DEV2-065, 22.08): /varlik rotaları (ETH/SOL/BNB/
   DOGALGAZ, /api/chart/<VARLIK>) 19.08 CPO-DEV2-036 sayfa kaldırmasının
   unutulmuş bir parçasıydı, artık tamamen kaldırıldı. Bu 4 anahtar burada hâlâ
   zararsız duruyor (şeritte render edilmiyor) ama artık hiçbir aktif rotaya
   atıfta bulunmuyorlar — sadece tarihsel kalıntı.
   BIST30 anahtarı XU030'un ölü ikizidir (payload asla BIST30 göndermez).

   Kardeş dosya: static/bp-format.js (tarih/etiket biçimlendirme, CPO-1335).
   Bu ikisi birlikte "sözlük evi"nin istemci tarafını oluşturur; sunucu
   tarafı karşılığı business_rules.py'dir.
*/

/* Kanonik görünen ad. Anahtar = /api/macro'nun `label` alanı. */
var BP_ASSET_LABELS = {
  XU100:    'BIST100',
  XU030:    'BIST30',
  USDTRY:   'USD/TRY',
  EURTRY:   'EUR/TRY',
  BTC:      'BTC',
  ETH:      'ETH',
  SOL:      'SOL',
  BNB:      'BNB',
  ALTIN:    'Altın',
  GUMUS:    'Gümüş',
  PETROL:   'Petrol',
  DOGALGAZ: 'Doğalgaz',
  SP500:    'S&P500',
  NASDAQ:   'NASDAQ',
  /* Ölü ikiz — payload göndermiyor, eski kopyalardan devralındı. */
  BIST30:   'BIST30'
};

/* Kanonik ondalık basamak. Eksik anahtar 2'ye düşer (BP_ASSET_DECIMALS_DEFAULT). */
var BP_ASSET_DECIMALS = {
  XU100:    0,
  XU030:    0,
  USDTRY:   4,
  EURTRY:   4,
  BTC:      0,
  ETH:      2,
  SOL:      2,
  BNB:      2,
  ALTIN:    2,
  GUMUS:    2,
  PETROL:   2,
  DOGALGAZ: 3,
  SP500:    0,
  NASDAQ:   0,
  BIST30:   0
};

var BP_ASSET_DECIMALS_DEFAULT = 2;

/* Bu anahtar sözlükte tanımlı mı? Yeni varlık eklendiğinde sessizce ham
   anahtar basılmasını yakalamak için — "PETROL" kusuru tam buydu. */
function bpAssetLabelIsKnown(key) {
  return Object.prototype.hasOwnProperty.call(BP_ASSET_LABELS, key);
}

/* Kanonik görünen ad; bilinmiyorsa ham anahtar (şerit boş kalmasın). */
function bpAssetLabel(key) {
  return bpAssetLabelIsKnown(key) ? BP_ASSET_LABELS[key] : key;
}

/* Kanonik ondalık basamak sayısı. */
function bpAssetDecimals(key) {
  var d = BP_ASSET_DECIMALS[key];
  return (typeof d === 'number') ? d : BP_ASSET_DECIMALS_DEFAULT;
}

/* Varlık fiyatını kanonik ondalıkla, TR ayırıcılarıyla biçimlendir.
   Sayı değilse '—' döner — uydurma değer basmaz. */
function bpFormatAssetPrice(key, price) {
  if (typeof price !== 'number' || !isFinite(price)) return '—';
  var dec = bpAssetDecimals(key);
  return price.toLocaleString('tr-TR', {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec
  });
}

/* Sinyal etiketi — kanonik harita, 6 sablonda (hisse/index/portfolio/
   sektor_harita/tarama/bilanco_takvimi) ayri ayri kopyalanmisti
   (DEV2-r104 takip bulgusu, CPO-DEV2-078 ailesi). Global 'sigLabel' adiyla
   expose ediyoruz ki cagiran sablonlarin mevcut sigLabel(...) call site'lari
   HIC degismesin — sadece yerel tanimlar kaldirildi. */
var BP_SIG_LABELS = { AL: 'Güçlü Trend', SAT: 'Trend Bozuldu', BEKLE: 'Yatay' };
function sigLabel(sig) {
  return BP_SIG_LABELS[sig] || sig;
}

/* Giris kalitesi etiketi — kanonik harita, 3 sablonda (gundem/karsilastir/
   tarama) ayri ayri kopyalanmisti (105. bagimsiz bug-hunt turu bulgusu).
   index.html'in kendi ikon-onekli varyanti KASITLI bir tasarim farki
   (r41, commit fd4d9f5, tooltip baglaminda) — buraya TASINMADI, dokunulmadi.
   Global 'eqLabel' adiyla expose ediyoruz ki cagiran sablonlarin mevcut
   kullanimlari degismesin. */
var BP_EQ_LABELS = { IDEAL: 'İdeal', IYI: 'İyi', DIKKATLI: 'Dikkatli', UZAK: 'Uzak' };
function eqLabel(code) {
  return BP_EQ_LABELS[code] || code;
}

/* HTML escape + guvenli href — kanonik, 4 sablonda (bilanco_takvimi/
   gundem/karsilastir/tarama) birebir ayni kopyalanmisti (105. bagimsiz
   bug-hunt turu bulgusu). hisse.html kendi 'escHtml' adiyla ayri bir
   fonksiyon kullaniyor (8+ call site farkli isim) — buraya TASINMADI,
   ayri/dusuk-oncelikli konu. Global 'escapeHtml'/'safeHref' adiyla expose
   ediyoruz ki cagiran sablonlarin mevcut call site'lari degismesin. */
function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, function(c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}
function safeHref(url) {
  return /^https?:\/\//i.test(url || '') ? escapeHtml(url) : '#';
}
