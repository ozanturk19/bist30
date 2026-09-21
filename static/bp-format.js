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

/* Bugünün TR takvim günü. Kullanıcının cihaz saat dilimi ne olursa olsun
   BIST günü esas alınır (yurt dışındaki kullanıcı bir gün kaymasın). */
function bpTodayTr() {
  try {
    var parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: BP_TZ_TR, year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(new Date());
    var o = {};
    for (var i = 0; i < parts.length; i++) o[parts[i].type] = parts[i].value;
    if (o.year && o.month && o.day) {
      return { y: parseInt(o.year, 10), m: parseInt(o.month, 10), d: parseInt(o.day, 10) };
    }
  } catch (e) { /* Intl/timeZone desteklenmiyor — yerel güne düş */ }
  var n = new Date();
  return { y: n.getFullYear(), m: n.getMonth() + 1, d: n.getDate() };
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
