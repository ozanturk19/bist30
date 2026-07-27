/* CPO-1125 İş Kolu B — kanonik stale banner render + polling.
   Kaynak: index.html'in mevcut renk/metin mantığı (DEV-1474 spec), 6 sayfaya
   merkezileştirildi. Kanonik veri: data_quality + stocks_age_s — /api/health.status
   BANNER'A GİRMEZ (SENECA drift bulgusunun kökü, tarama.html'de düzeltildi).
   Not: index.html critical metninde "Yenileniyor..." vardı, hisse.html'de yoktu —
   merkezileşirken index.html'in metni kanonik alındı (iki kopya arası tutarsızlık
   fix, görsel/renk mantığı değişmedi). */
function bpUpdateStaleBanner(dq, ageS) {
  var banner = document.getElementById('staleBanner');
  var bTxt   = document.getElementById('staleBannerText');
  if (!banner) return;
  var mins = ageS ? Math.floor(ageS / 60) : '?';
  if (dq === 'critical') {
    if (bTxt) bTxt.textContent = 'Veriler ' + mins + ' dakikadır güncellenemiyor. Yenileniyor...';
    banner.style.background  = 'rgba(248,81,73,0.12)';
    banner.style.borderColor = '#f85149';
    banner.style.display     = 'block';
  } else if (dq === 'stale') {
    if (bTxt) bTxt.textContent = 'Veriler ' + mins + ' dk önce güncellendi — yenileniyor...';
    banner.style.background  = '';
    banner.style.borderColor = '';
    banner.style.display     = 'block';
  } else {
    banner.style.display = 'none';
  }
}

/* tarama/hisseler/sinyal_performans — /api/data (216 kayıt) çekmiyorlar, hafif
   /api/data-quality endpoint'ini (CPO-1121 §1) 60s'de bir çekip aynı fonksiyona post eder. */
function bpPollDataQuality() {
  fetch('/api/data-quality', {cache: 'no-store'})
    .then(function(r) { return r.json(); })
    .then(function(j) { bpUpdateStaleBanner(j.data_quality, j.stocks_age_s); })
    .catch(function() {});
}
function bpStartDataQualityPolling() {
  bpPollDataQuality();
  setInterval(bpPollDataQuality, 60000);
}
