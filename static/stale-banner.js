/* CPO-1125 İş Kolu B — kanonik stale banner render + polling.
   Kaynak: index.html'in mevcut renk/metin mantığı (DEV-1474 spec), 6 sayfaya
   merkezileştirildi. Kanonik veri: data_quality + stocks_age_s — /api/health.status
   BANNER'A GİRMEZ (SENECA drift bulgusunun kökü, tarama.html'de düzeltildi).
   CPO-1151 §3: ageS bilinmediğinde '?' yerine dürüst metin; "Yenileniyor..."
   yalnız /api/data.refreshing===true iken eklenir (refreshing 3. parametre,
   /api/data-quality'yi kullanan çağıranlarda undefined → ek metin yok). */
/* T7.2 — insan dili yaş formatı: <60dk "dk", <48sa "sa dk", ustu "gun sa".
   Onceki: ham dakika (orn "5115 dakikadir") — coklu-gunluk bayatlikta okunmaz
   hale geliyordu (bkz FAZ7.5/T7.2 canli olcum, stocks_age_seconds~85 saat). */
function bpFmtAge(ageS) {
  var totalMin = Math.floor(ageS / 60);
  if (totalMin < 60) return totalMin + ' dk';
  var totalHour = Math.floor(totalMin / 60);
  var remMin = totalMin % 60;
  if (totalHour < 48) return totalHour + ' sa ' + remMin + ' dk';
  var days = Math.floor(totalHour / 24);
  var remHour = totalHour % 24;
  return days + ' gün ' + remHour + ' sa';
}

function bpUpdateStaleBanner(dq, ageS, refreshing) {
  var banner = document.getElementById('staleBanner');
  var bTxt   = document.getElementById('staleBannerText');
  if (!banner) return;
  var hasAge = ageS != null && !isNaN(ageS);
  var ageTxt = hasAge ? bpFmtAge(ageS) : null;
  var suffix = refreshing === true ? ' Yenileniyor...' : '';
  if (dq === 'critical') {
    var critTxt = hasAge
      ? 'Veriler ' + ageTxt + ' boyunca güncellenemiyor.'
      : 'Veriler güncellenemiyor — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) bTxt.textContent = critTxt + suffix;
    banner.style.background  = 'rgba(248,81,73,0.12)';
    banner.style.borderColor = '#f85149';
    banner.style.display     = 'block';
  } else if (dq === 'stale') {
    var staleTxt = hasAge
      ? 'Veriler ' + ageTxt + ' önce güncellendi.'
      : 'Veriler bayat olabilir — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) bTxt.textContent = staleTxt + suffix;
    banner.style.background  = 'rgba(245,201,73,.10)';
    banner.style.borderColor = 'rgba(245,201,73,.4)';
    banner.style.display     = 'block';
  } else if (dq === 'seans_disi') {
    /* CPO-1338: seans dışı stale by-design — banner KASITLI gizli (fresh ile
       karıştığı için değil, bu dal açıkça o kararı veriyor). */
    banner.style.display = 'none';
  } else {
    banner.style.display = 'none';
  }
}

/* tarama/hisseler/sinyal_performans — /api/data (216 kayıt) çekmiyorlar, hafif
   /api/data-quality endpoint'ini (CPO-1121 §1) 60s'de bir çekip aynı fonksiyona post eder. */
function bpPollDataQuality() {
  fetch('/api/data-quality', {cache: 'no-store', signal: AbortSignal.timeout(10000)})
    .then(function(r) { return r.json(); })
    .then(function(j) { bpUpdateStaleBanner(j.data_quality, j.stocks_age_s); })
    .catch(function(e) { console.error('data-quality polling basarisiz', e); });
}
function bpStartDataQualityPolling() {
  bpPollDataQuality();
  setInterval(bpPollDataQuality, 60000);
}
