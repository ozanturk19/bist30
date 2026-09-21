/* CPO-1335 — kanonik göreli tarih etiketi (Bugün / Dün / gerçek tarih).

   KUSUR: Arayüz "Bugün"/"Dün" etiketini iki DONMUŞ eksenden türetiyordu:
     (a) signal_bars — veri setindeki bar sayısı. Ticker o gün tazelenmezse son
         bar dünün (veya daha eskisinin) barıdır, dolayısıyla bars=1 "bugün"
         demek değildir. Canlı kanıt 08.08.2026 (payda 215): bars=1 hem 07.08
         hem 06.08 signal_date'ine düşüyordu; bars=2 -> 06.08 ve 05.08;
         bars=3 -> 04.08 ve 05.08. Sapma tek tip DEĞİL, "hepsini bir gün geri
         al" düzeltmesi işe yaramaz.
     (b) is_new_signal — analyze() içinde (signal_date == today_str) olarak
         hesaplanıp payload'a donduruluyor. Ticker tazelenmezse eski günün
         True'su taşınıyor (RYSAS: is_new_signal=true, signal_date=06.08).

   KANONİK EKSEN: signal_date — payload'da 215/215 dolu, "DD.MM.YYYY", gerçek
   bar tarihinden türer. Etiket GERÇEK bugünle (Europe/Istanbul) karşılaştırarak
   RENDER ANINDA üretilir; hiçbir donmuş sayaç/bayrak kullanılmaz.

   TARİH BİLİNMİYORSA ETİKET ÜRETİLMEZ (null döner) — çağıran nötr bir şey
   basmalı. Eski `const b = bars || 1` deseni bilinmeyeni sessizce "Bugün"e
   düşürüyordu; bu dosya o tuzağı taşımaz.

   Sunucu aynası: business_rules.derive_signal_date_label() — eşikler birebir
   aynı, tests/test_cpo1335_signal_date_label.py ikisini birlikte kilitler.

   T1.3 notu: bu dosya Master Program T1.3'ün (bp-format.js) evi. Ticker/makro
   etiket haritası ve ondalık biçimlendirme T1.3'te BU dosyaya eklenecek —
   ayrı dosya açılmayacak. */

var BP_SIGNAL_DATE_LABELS = {
  TODAY: 'Bugün',
  YESTERDAY: 'Dün'
};

var BP_TZ_TR = 'Europe/Istanbul';

/* "DD.MM.YYYY" -> {y,m,d}. Ayrıştırılamazsa null (varsayım YOK). */
function bpParseTrDate(s) {
  if (typeof s !== 'string') return null;
  var m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(s.trim());
  if (!m) return null;
  var d = parseInt(m[1], 10), mo = parseInt(m[2], 10), y = parseInt(m[3], 10);
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  /* Takvimde gerçekten var mı (31.02 gibi uydurma tarihleri ele) */
  var probe = new Date(Date.UTC(y, mo - 1, d));
  if (probe.getUTCFullYear() !== y || probe.getUTCMonth() !== mo - 1 || probe.getUTCDate() !== d) return null;
  return { y: y, m: mo, d: d };
}

/* HERHANGİ BİR ANIN TR takvim günü. Kullanıcının cihaz saat dilimi ne olursa
   olsun BIST günü esas alınır (yurt dışındaki kullanıcı bir gün kaymasın).
   K-BL (21.09): bu fonksiyon `bpTodayTr()`den genelleştirildi — stale-banner
   "şu an"ı değil, `ageS` saniye ÖNCEKİ anı TR gününe çevirmek zorundaydı ve
   bunu kendi içinde getDate()/getMonth() ile, yani CİHAZ saat diliminde
   yapıyordu (aşağıdaki K-BD notuyla birebir aynı sınıf hata, ikinci çağrı
   yerinde). Kanon: görünen HER TR takvim günü bu fonksiyondan türer. */
function bpTrDatePartsAt(dateOrMs) {
  var when = (dateOrMs instanceof Date) ? dateOrMs : new Date(dateOrMs);
  if (isNaN(when.getTime())) return null;
  try {
    var parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: BP_TZ_TR, year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(when);
    var o = {};
    for (var i = 0; i < parts.length; i++) o[parts[i].type] = parts[i].value;
    if (o.year && o.month && o.day) {
      return { y: parseInt(o.year, 10), m: parseInt(o.month, 10), d: parseInt(o.day, 10) };
    }
  } catch (e) { /* Intl/timeZone desteklenmiyor — yerel güne düş */ }
  return { y: when.getFullYear(), m: when.getMonth() + 1, d: when.getDate() };
}

/* Bugünün TR takvim günü. */
function bpTodayTr() {
  return bpTrDatePartsAt(new Date());
}

/* ŞU ANIN BIST SAATİ, "HH:MM:SS". K-BL (21.09): header'daki canlı saat rozeti
   `new Date().getHours()` ile CİHAZIN saat diliminden okunuyordu — site ise
   her yerde BIST saatini esas alıyor ("~18:00 TR": metodoloji, hakkinda,
   yasal, hisse). Rozet bu yüzden bu dosyaya, TR takvim günü kanonunun yanına
   taşındı: aynı saat dilimi sabitinden (BP_TZ_TR) türeyen tek bir yer.
   Intl/timeZone yoksa null — çağıran rozeti GİZLER, yerel saati BIST saatiymiş
   gibi göstermez. */
function bpTrClock() {
  try {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: BP_TZ_TR, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }).format(new Date());
  } catch (e) { return null; }
}

/* signal_date ile bugün arasındaki TAKVİM GÜNÜ farkı. Bilinmiyorsa null. */
function bpSignalDateAgeDays(signalDate) {
  var sd = bpParseTrDate(signalDate);
  if (!sd) return null;
  var t = bpTodayTr();
  return Math.round(
    (Date.UTC(t.y, t.m - 1, t.d) - Date.UTC(sd.y, sd.m - 1, sd.d)) / 86400000
  );
}

/* Sinyal GERÇEKTEN bugüne mi ait — donmuş is_new_signal yerine bunu kullan. */
function bpIsSignalFromToday(signalDate) {
  return bpSignalDateAgeDays(signalDate) === 0;
}

/* "07.08.2026" -> "07.08.2026" (sıfır dolgulu, tek biçim). */
function bpFormatTrDate(signalDate) {
  var sd = bpParseTrDate(signalDate);
  if (!sd) return null;
  var p2 = function (n) { return (n < 10 ? '0' : '') + n; };
  return p2(sd.d) + '.' + p2(sd.m) + '.' + sd.y;
}

/* Kanonik görünen etiket.
   bugün -> "Bugün" · dün -> "Dün" · daha eski VEYA gelecek -> gerçek tarih.
   Tarih ayrıştırılamazsa null — çağıran nötr bir şey basmalı, "Bugün" DEĞİL. */
function bpSignalDateLabel(signalDate) {
  var age = bpSignalDateAgeDays(signalDate);
  if (age === null) return null;
  if (age === 0) return BP_SIGNAL_DATE_LABELS.TODAY;
  if (age === 1) return BP_SIGNAL_DATE_LABELS.YESTERDAY;
  return bpFormatTrDate(signalDate);
}

/* Sinyalin TAKVİM yaşı, metin olarak: "Bugün" / "Dün" / "N gün" / "—".
   Mutlak tarihin YANINDA gösterilen yerlerde kullanılır (gündem kartı, hisse
   detayı); tarihin görünmediği yerlerde bpSignalDateLabel tercih edilir, çünkü
   orada gerçek tarihi yazmak gerekir.

   NOT: eskiden bu değer `signal_bars` (BAR sayacı) idi ve "gün" diye
   sunuluyordu. Bar sayısı hafta sonlarını ve ticker'ın tazelenemediği günleri
   atlar — "5 bar" ile "5 gün" aynı şey değildir. Kaynak artık takvim. */
function bpSignalAgeText(signalDate) {
  var age = bpSignalDateAgeDays(signalDate);
  if (age === null) return '—';
  if (age === 0) return BP_SIGNAL_DATE_LABELS.TODAY;
  if (age === 1) return BP_SIGNAL_DATE_LABELS.YESTERDAY;
  if (age < 0) return bpFormatTrDate(signalDate);
  return age + ' gün';
}

/* Dar alanlar için kısa biçim: "3G" · bilinmiyorsa "—". */
function bpSignalAgeShort(signalDate) {
  var age = bpSignalDateAgeDays(signalDate);
  return age === null ? '—' : age + 'G';
}

/* Rozet/renk sınıfı seçmek için ayrık anahtar — şablonlar kendi CSS
   sınıflarını (today / yesterday / older) bu anahtarla eşler. */
function bpSignalDateKey(signalDate) {
  var age = bpSignalDateAgeDays(signalDate);
  if (age === null) return 'unknown';
  if (age === 0) return 'today';
  if (age === 1) return 'yesterday';
  return 'older';
}

/* ── K-BA — TÜRKÇE SAYI GİRDİSİ: TEK KAYNAK ──────────────────────────────
   KUSUR (canlıda ölçüldü, /tarama): fiyat filtreleri `type="number"`di.
   Türkçe konuşan kullanıcı "12,50" yazınca tarayıcı virgülü SESSİZCE atıyor
   ve `input.value` **"1250"** oluyor — `validity.valid` hâlâ true, badInput
   false, hiçbir hata yok. 216 hisse 5'e düşüyor, çip güvenle "Min 1250 ₺"
   yazıyor. Kullanıcı 100 kat sapmayı göremiyor.

   Bu hata daha ÖNCE bir kez bulunmuştu (portfolio.html "Alış ₺" alanı,
   r161-bughunt) ve YALNIZCA orada düzeltilmişti — /tarama'daki dört fiyat
   alanı fix'i miras almadı. Bu yüzden ayrıştırıcı artık burada, tek kopya.

   BELİRSİZLİK VE ÇÖZÜMÜ (kasıtlı, ölçülebilir):
     · virgül VARSA  → noktalar binlik ayracıdır, virgül ondalıktır:
                       "1.234,56" → 1234.56
     · virgül YOKSA ve NOKTA BİRDEN FAZLAYSA → hepsi binlik ayracıdır
                       ("1.234.567" tek bir ondalık nokta OLAMAZ) → 1234567
     · virgül YOKSA ve tek nokta varsa → KARARLAŞTIRILAMAZ ("1.234" hem
       1,234 hem 1234 olabilir). Makine biçimi (JSON/URL) varsayılır,
       DOKUNULMAZ: 1.234. Kullanıcı binlik kastediyorsa virgül yazmalı.
       (portfolio.html'in mevcut davranışı budur; değiştirilmedi.)

   Ayrıştırılamayan girdi için NaN döner — çağıran "filtre yok"a düşmeli ve
   alanı `aria-invalid` ile işaretlemeli. Sessizce 0'a düşürmek YASAK: bu,
   düzeltmeye çalıştığımız sessiz başarısızlığın ta kendisidir. */
function bpParseTrNumber(raw) {
  if (raw === null || raw === undefined) return NaN;
  raw = String(raw).trim();
  if (!raw) return NaN;
  if (raw.indexOf(',') !== -1) {
    raw = raw.replace(/\./g, '').replace(',', '.');
  } else if ((raw.match(/\./g) || []).length > 1) {
    raw = raw.replace(/\./g, '');
  }
  if (!/^[+-]?\d*\.?\d+$/.test(raw)) return NaN;
  return parseFloat(raw);
}

/* Sayıyı Türkçe biçimde GÖSTER (çip/etiket metni). Ayrıştırılamayanı
   uydurmaz — sonlu değilse boş dizge. */
function bpFormatTrNumber(n, maxFrac) {
  if (!isFinite(n)) return '';
  return Number(n).toLocaleString('tr-TR', {
    maximumFractionDigits: (maxFrac === undefined ? 2 : maxFrac)
  });
}

/* K-BD (21.09) — "BUGÜNÜN TARİHİ" DOSYA ADINDA UTC'DEN TÜRETİLİYORDU.
   Dışa aktarılan dosyaların adı `new Date().toISOString().slice(0,10)` ile
   üretiliyordu; bu UTC günüdür. TR saatiyle 00:00–02:59 arasında (UTC+3)
   kullanıcı portföyünü indirdiğinde dosya BİR ÖNCEKİ günün adını alıyor,
   içindeki alış tarihleri ise TR takvimiyle yazıldığı için dosya adı
   içerikle çelişiyordu. Aynı dosyada (portfolio.html) iki kanon yan yanaydı:
   yeni pozisyonun varsayılan tarihi Europe/Istanbul ile doğru türetilirken
   dosya adı UTC'den türüyordu.
   Kanon: görünen HER "bugün" değeri bpTodayTr()'den türer. */
function bpTodayTrIso() {
  var t = bpTodayTr();
  var p2 = function (n) { return (n < 10 ? '0' : '') + n; };
  return t.y + '-' + p2(t.m) + '-' + p2(t.d);
}

/* K-BJ: POZISYON SAYISAL DOGRULAMA — TEK KANON.
   Portfoye pozisyon yazan DORT yol vardi ve olcut UC ayri yerde yaziliydi:
     * addPosition()      (form)            -> lot tamsayi>0<=1e9, price>0<=1e9
     * importPortfolio()  (dosya)           -> ayni olcut, ikinci kez yazilmis
     * loadCloudToken/loadFromCloud (bulut) -> sayisal dogrulama YOK
     * togglePortfolio()  (hisse detay)     -> dogrulama YOK; dahasi fiyat
       okunamadiginda _hibCurrentPrice() 0 donup MALIYET olarak 0 yaziyordu.
   price=0 pozisyon tabloda cost=0 uretir; pnl = deger - 0 = pozisyonun TAM
   degeri "kar" gorunur ve toplam K/Z kutusunu da sisirir.
   Kanon: pozisyon sayisi yazan/dogrulayan HER yol bu ikisini cagirir. */
function bpIsValidLot(lot) {
  var n = Number(lot);
  return Number.isFinite(n) && Number.isInteger(n) && n > 0 && n <= 1e9;
}
function bpIsValidPrice(price) {
  var n = Number(price);
  return Number.isFinite(n) && n > 0 && n <= 1e9;
}

/* K-BP (21.09): YON EKSENI (degisim / getiri / K-Z) — TEK KANON.

   Sitede AYNI IS icin IKI KANON vardi:
     (a) `x > 0 ? AL : x < 0 ? SAT : NOTR`  -> /tarama, /gundem, /sektor-harita
     (b) `x >= 0 ? AL : SAT`                -> /karsilastir, /portfolio, /ozet,
                                               /hisse, anasayfa serit, blog widget
   (b) yolunda DEGISMEYEN bir hisse "+0,00%" ve YESIL goruruyordu. Canli kanit
   (21.09, /api/data 217 hisse): ALARK/DOAS/ARCLK/CEMTS/ISMEN change_pct = 0.
   AYNI GUN, AYNI HISSE -> /tarama "0,00%" gri rgb(199,197,205),
   /karsilastir "+0,00%" yesil rgb(0,226,144). Site kendi kendisiyle celisiyordu.
   Yesil "yukselis" vaadidir; 0 bir yukselis DEGILDIR ve "+" bir kazanc ima eder.

   Ikinci kural K-BO'dan miras: ESIKLENEN SAYI, KULLANICININ OKUDUGU SAYI
   OLMALI. -0,004 ekranda "0,00%" yazip KIRMIZI olamaz. Bu yuzden yon, once
   GORUNTU ONDALIGINA yuvarlanmis deger uzerinden belirlenir.

   Kanon: >0 -> --bp-al · <0 -> --bp-sat · =0 -> NOTR (hem renk hem isaret). */

/* -1 / 0 / +1, veya sayi degilse null. `frac` = ekranda gosterilen ondalik. */
function bpDir(n, frac) {
  var v = (typeof n === 'string') ? parseFloat(n) : n;
  if (typeof v !== 'number' || !isFinite(v)) return null;
  var f = (typeof frac === 'number') ? frac : 2;
  var r = parseFloat(v.toFixed(f));          /* KULLANICININ OKUDUGU SAYI */
  return r > 0 ? 1 : (r < 0 ? -1 : 0);
}

/* '+' YALNIZ gercekten pozitif GORUNEN sayida. 0 ve gecersiz -> ''. */
function bpDirSign(n, frac) {
  return bpDir(n, frac) === 1 ? '+' : '';
}

/* Yon rengi (CSS degiskeni metni). Notr varsayilan: --bp-text2. */
function bpDirColor(n, frac, neutralVar) {
  var d = bpDir(n, frac);
  var neu = neutralVar || 'var(--bp-text2)';
  if (d === null) return 'var(--bp-text3)';
  return d === 1 ? 'var(--bp-al)' : (d === -1 ? 'var(--bp-sat)' : neu);
}

/* Yon sinifi. names = [pozitif, negatif, notr]; varsayilan ['up','down','neu'].
   Sinif adlari sayfadan sayfaya degisir (up/dn, chg-pos/chg-neg/chg-neu,
   pos-pnl/neg-pnl/neu-pnl) — degismeyen sey KARARIN kendisidir. */
function bpDirClass(n, frac, names) {
  var nm = names || ['up', 'down', 'neu'];
  var d = bpDir(n, frac);
  if (d === null) return '';
  return d === 1 ? nm[0] : (d === -1 ? nm[1] : nm[2]);
}

/* Gosterimde sifira yuvarlanan degeri GERCEK 0 yapar — boylece para/sayi
   bicimleyicileri (toLocaleString) "-0,00 ₺" gibi isaretli sifir yazamaz.
   Notr renkle eksi isaretinin ayni hucrede bulunmasini engeller. */
function bpZero(n, frac) {
  return bpDir(n, frac) === 0 ? 0 : n;
}

/* Yuzde metni: isaret + TR ondalik + '%'. Yon ile AYNI yuvarlamayi kullanir,
   boylece -0,004 "-0,00%" degil "0,00%" yazar (isaretli sifir yok). */
function bpFormatPct(n, frac) {
  var v = (typeof n === 'string') ? parseFloat(n) : n;
  if (typeof v !== 'number' || !isFinite(v)) return '—';
  var f = (typeof frac === 'number') ? frac : 2;
  var r = parseFloat(v.toFixed(f));
  if (r === 0) r = 0;                        /* -0 -> 0 */
  return (r > 0 ? '+' : '') + r.toFixed(f).replace('.', ',') + '%';
}

/* ── K-BQ (21.09): SUPERTREND SEVIYESI ≠ "STOP" ──────────────────────────
   `sl_level` Supertrend bandinin GUNCEL degeridir ve sinyal yonunden bagimsiz
   HER hissede hesaplanir. Long-only bir urunde bu sayiya "Stop" demek yalnizca
   band fiyatin ALTINDAYKEN (yukselis sinyali) anlamlidir.

   CANLI OLCUM (21.09, /api/data 217 hisse): `sl_level > price` olan **197**
   hisse (72/72 SAT + 125/138 BEKLE). MARTI: fiyat 2,01 ₺ iken "Hap Bilgi"de
   "Stop Seviyesi 2,74 ₺" — %36 YUKARIDA; ayni sayfa iki satir yukarida "Net
   sinyal olmadigi icin tanimli bir giris bolgesi yok" diyordu. Ayrica bandin
   fiyatin USTUNDE oldugu durumda alt-etiket "ST destegi" yaziyordu: fiyatin
   ustundeki bir seviye destek degil DIRENCTIR.

   Kanon: ad her yerde "Supertrend Seviyesi" (karsilastir.html'in zaten dogru
   olan emsali); "stop" kelimesi YALNIZCA signal==='AL' ve band fiyatin
   altindayken. Yon eki fiyatla karsilastirilarak turer, sinyalden degil. */
function bpStLevelRole(sl, price, signal) {
  var s = (typeof sl === 'string') ? parseFloat(sl) : sl;
  var p = (typeof price === 'string') ? parseFloat(price) : price;
  if (typeof s !== 'number' || !isFinite(s) || typeof p !== 'number' || !isFinite(p) || p === 0) return null;
  var above = s > p;
  return {
    above: above,
    /* Uzaklik bir BUYUKLUKTUR — isareti etiket tasir, sayi tasimaz (K-BP). */
    pct: Math.abs((s - p) / p * 100),
    label: (!above && signal === 'AL') ? 'Riske uzaklık' : (above ? 'ST direnci' : 'ST desteği')
  };
}

/* ── K-BR (22.09): GOSTERGE SAYISI TEK KANON (1 ondalik, TR) ─────────────
   ADX ve RSI 0-100 olcegindedir ve ADX'in **25** esigi urunun sinyal kurali.
   Tam sayiya yuvarlamak iki sey birden bozar:
     1. `|int` ASAGI KESER -> ISDMR ADX 25,9 "ADX 25 — Guclu trend (esik: 25)"
        diye basiliyordu: kullaniciya "kil payi gecti" diye okunur.
     2. Ayni sayfada `|round|int` 26 der -> AYNI SAYI IKI YERDE 25 ve 26.
   Canli olcum (22.09, /api/data 217 hisse): `int(adx) != round(adx)` olan
   **91** hisse; ADX 25,0-25,9 bandinda **14** hisse (esikle cakisma riski).
   Site kanonu zaten 1 ondaliktir (/tarama `toFixed(1)`, /karsilastir
   `renderAdx/renderRsi`) — sapan yalniz /hisse'nin SSR tarafi ve anasayfa
   spotlight'iydi. Jinja tarafinda esdegeri: `'%.1f'|format(x)|replace('.', ',')`. */
function bpIndNum(v) {
  var n = (typeof v === 'string') ? parseFloat(v) : v;
  if (typeof n !== 'number' || !isFinite(n)) return '—';
  return n.toFixed(1).replace('.', ',');
}

/* ── K-BS (22.09): GOSTERGE PANELI TEK AGIZDAN KONUSUR ───────────────────
   Uc ayri kusurun ortak koku: rozet bir kaynaktan, hemen altindaki teknik
   satir BASKA bir kaynaktan/yuvarlamadan okuyor.

   1) BASILAN CIFT, YAZILAN SONUCU DESTEKLEMELI (K-BO kanonunun ikizi).
      Canli 22.09 /hisse/DURDO: rozet "Vade Uyumu — Kısa > Uzun" (yesil) derken
      hemen altindaki teknik satir "EMA12: 4,9 · EMA99: 4,9" basiyordu. Iki
      esit sayinin altina "biri digerinden buyuk" yazmak, okura sayfanin
      kendisini yanlis okutur. Gercek fark %0,137 — yani sonuc DOGRU, GOSTERIM
      eksik. Sayiyi buyutemedigimiz yerde (chart ozeti 1 ondalikta geliyor)
      dogru davranis, farki UZLASTIRAN kisa bir not dusmektir.
      `dir`: 1 => "a > b" iddia edildi, -1 => "a < b", 0 => iddia yok.

   2) RSI BOLGE ADI BIR VAAT TASIYABILIR. `rsi_zone` backend'de sinyalden
      BAGIMSIZ turetilir; "Ideal Giris Penceresi" (RSI 45-60) long-only bir
      urunde ancak AL sinyaliyle anlamlidir. Canli 22.09: bu bolge adini tasiyan
      46 hissenin **45'i AL DEGIL** (FROTO/MGROS/MAVI dahil 3'u SAT). Rengi
      CPO-DEV2-031/033 zaten notrlemisti — KELIMELER kalmisti. */
function bpNumPairNote(aStr, bStr, dir) {
  if (!dir || aStr == null || bStr == null) return '';
  var a = parseFloat(String(aStr).replace(',', '.'));
  var b = parseFloat(String(bStr).replace(',', '.'));
  if (!isFinite(a) || !isFinite(b)) return '';
  var shown = a > b ? 1 : (a < b ? -1 : 0);
  if (shown === dir) return '';
  return shown === 0
    ? ' (gösterilen basamakta eşit)'
    : ' (gösterilen değerler yuvarlanmış)';
}

function bpRsiZoneText(zone, signal) {
  var z = zone || '';
  if (z.indexOf('İdeal Giriş') === 0 && signal !== 'AL') return 'Nötr bölge';
  return z;
}
