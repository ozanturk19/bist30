/* CPO-1335 test koşumu — static/bp-format.js'i sabit bir "bugün" ile çalıştırır.

   tests/test_cpo1335_signal_date_label.py bunu node ile çağırıp çıktıyı
   business_rules.py'nin çıktısıyla karşılaştırır. Amaç: sunucu ve istemci
   eşiklerinin AYRIŞMASINI yakalamak (iki dilde iki kopya kural var, biri
   değişip diğeri kalırsa etiket yüzeyden yüzeye çatallanır).

   Kullanım: node bp_format_probe.js <bp-format.js yolu> <vakalar.json yolu>
   Vaka biçimi: [{"signal_date": "07.08.2026", "today": [2026, 8, 8]}, ...] */
const fs = require('fs');

const src = fs.readFileSync(process.argv[2], 'utf8');
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

const results = cases.map(function (c) {
  const sd = JSON.stringify(c.signal_date);
  /* Her vaka kendi kapsamında çalışır; bpTodayTr sabitlenir ki test gerçek
     saate bağlı olmasın (gece yarısı geçişinde kırılgan test istemiyoruz). */
  const run = new Function('__TODAY', src + `
    bpTodayTr = function () { return __TODAY; };
    return {
      label: bpSignalDateLabel(${sd}),
      key:   bpSignalDateKey(${sd}),
      age:   bpSignalDateAgeDays(${sd}),
      today: bpIsSignalFromToday(${sd})
    };
  `);
  return run({ y: c.today[0], m: c.today[1], d: c.today[2] });
});

console.log(JSON.stringify(results));
