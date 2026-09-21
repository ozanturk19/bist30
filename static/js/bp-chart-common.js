/* BorsaPusula ortak grafik motoru (CPO-DEV2-096) — lightweight-charts config/seri/tooltip
   tek kaynak. index.html (#chartMain, XU100/XU30) VE hisse.html (/hisse/<ticker>) BUNU
   kullanir; ikisi de kendi ayri getBaseOpts()/EmaFill sinifini tutuyordu (iki yerde elle
   bakim = drift riski). Zaman ekseni farkli (index: tarih string/epoch, hisse: sequential
   index - hafta sonu gap'siz) oldugu icin buildChart()'in kendisi paylasilmiyor, sadece
   config/seri/tooltip katmani. */
(function () {
  'use strict';

  var MTHS = ['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];

  /* Eksen/crosshair tarih formati: "10" -> "Nis 10". time: 'YYYY-MM-DD' string |
     unix saniye (number) | {year,month,day} objesi | sequential index (caller kendi
     tickMarkFormatter'inda index->tarih cevirip bu fonksiyona STRING olarak verir). */
  function fmtTickDate(time, type) {
    var yr, mo, dy;
    if (typeof time === 'string') {
      var p = time.split('-'); yr = +p[0]; mo = +p[1] - 1; dy = +p[2];
    } else if (typeof time === 'number') {
      var d = new Date(time * 1000); yr = d.getUTCFullYear(); mo = d.getUTCMonth(); dy = d.getUTCDate();
    } else if (time && typeof time === 'object') {
      yr = time.year; mo = (time.month || 1) - 1; dy = time.day;
    } else { return ''; }
    if (type === 0) return String(yr);
    if (type === 1) return MTHS[mo] || '';
    if (type === 2) return (MTHS[mo] || '') + ' ' + dy;
    return '';
  }

  /* Kanonik base options. LC parametre olarak verilir (CrosshairMode enum'u icin) -
     global degiskene sessizce baglanmak yerine caller kendi LC referansini gecer.
     withVolume=true ise sag fiyat eksenine altta hacim barlari icin bosluk birakilir. */
  function baseOpts(LC, withVolume) {
    return {
      /* K-BG: palet _tok()'tan okunur (hex yalniz yedek). Bu dosyanin KENDI
         kanonu zaten buydu (addEmaPair 20.09'da gecmisti) ama baseOpts ve
         addCandleSeries ham hex'te kalmisti -- ayni dosyada iki kanon. */
      layout: { background: { color: _tok('--bp-surface', '#141416') }, textColor: _tok('--bp-text2', '#c7c5cd') },
      grid: { vertLines: { color: _tok('--bp-border-subtle', '#21262d') }, horzLines: { color: _tok('--bp-border-subtle', '#21262d') } },
      crosshair: {
        mode: LC.CrosshairMode.Normal,
        vertLine: { color: _tok('--bp-chart-crosshair', '#3d5a80'), labelBackgroundColor: _tok('--bp-brand', '#b8c3ff'), width: 1, style: 0 },
        horzLine: { color: _tok('--bp-chart-crosshair', '#3d5a80'), labelBackgroundColor: _tok('--bp-brand', '#b8c3ff'), width: 1, style: 0 },
      },
      rightPriceScale: {
        borderColor: 'rgba(' + _hexRgb(_tok('--bp-bkl-bd', '#30363d'), '48,54,61') + ',0.6)',
        scaleMargins: withVolume ? { top: 0.08, bottom: 0.26 } : { top: 0.08, bottom: 0.08 },
      },
      handleScroll: true,
      handleScale: true,
      localization: {
        locale: 'tr-TR',
        priceFormatter: function (v) {
          return (+v).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },
      },
    };
  }

  /* Kanonik mum serisi. */
  function addCandleSeries(chart) {
    return chart.addCandlestickSeries({
      upColor: _tok('--bp-al', '#00e290'), downColor: _tok('--bp-sat', '#f85149'),
      borderUpColor: _tok('--bp-al', '#00e290'), borderDownColor: _tok('--bp-sat', '#f85149'),
      wickUpColor: _tok('--bp-al', '#00e290'), wickDownColor: _tok('--bp-sat', '#f85149'),
      priceLineVisible: false, lastValueVisible: true,
    });
  }

  /* Kanonik hacim histogramı — kendi (gizli, priceScaleId:'') eksenine, alt %18'e
     sıkıştırılmış. Backend (_compute_chart_data) her bar icin {time,value,color}
     ONCEDEN renklendirilmis dondurur (kapanis>=acilis yesil, degilse kirmizi) -
     ek bir renklendirme mantigi gerekmez. */
  function addVolumeSeries(chart) {
    return chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      scaleMargins: { top: 0.82, bottom: 0 },
      priceLineVisible: false,
      lastValueVisible: false,
    });
  }

  /* EMA bantlari arasi dolgu (bull/bear) - iki sayfada BIREBIR AYNI custom primitive'di,
     tek kopyaya indirildi. */
  function EmaFillPrimitive(chart, e12data, e99data, bullCol, bearCol) {
    this._chart = chart;
    this._e12 = {}; this._e99 = {};
    for (var i = 0; i < e12data.length; i++) this._e12[e12data[i].time] = e12data[i].value;
    for (var j = 0; j < e99data.length; j++) this._e99[e99data[j].time] = e99data[j].value;
    this._times = e12data.filter(function (p) { return this._e99[p.time] !== undefined; }, this).map(function (p) { return p.time; });
    this._bullCol = bullCol; this._bearCol = bearCol; this._series = null;
  }
  EmaFillPrimitive.prototype.attached = function (o) { this._series = o.series; };
  EmaFillPrimitive.prototype.detached = function () { this._series = null; };
  EmaFillPrimitive.prototype.updateAllViews = function () {};
  EmaFillPrimitive.prototype.paneViews = function () {
    var self = this;
    return [{
      renderer: function () {
        return {
          draw: function (target) {
            if (!self._series) return;
            target.useBitmapCoordinateSpace(function (scope) {
              var ctx = scope.context, hr = scope.horizontalPixelRatio, vr = scope.verticalPixelRatio;
              var ts = self._chart.timeScale();
              var pts1 = [], pts2 = [];
              for (var k = 0; k < self._times.length; k++) {
                var t = self._times[k];
                var x = ts.timeToCoordinate(t);
                var y1 = self._series.priceToCoordinate(self._e12[t]);
                var y2 = self._series.priceToCoordinate(self._e99[t]);
                if (x == null || y1 == null || y2 == null) continue;
                pts1.push({ x: x * hr, y: y1 * vr, v: self._e12[t] });
                pts2.push({ x: x * hr, y: y2 * vr, v: self._e99[t] });
              }
              if (pts1.length < 2) return;
              ctx.save();
              for (var m = 1; m < pts1.length; m++) {
                var a1 = pts1[m - 1], b1 = pts1[m], a2 = pts2[m - 1], b2 = pts2[m];
                ctx.fillStyle = b1.v > b2.v ? self._bullCol : self._bearCol;
                ctx.beginPath();
                ctx.moveTo(a1.x, a1.y); ctx.lineTo(b1.x, b1.y);
                ctx.lineTo(b2.x, b2.y); ctx.lineTo(a2.x, a2.y);
                ctx.closePath(); ctx.fill();
              }
              ctx.restore();
            });
          }
        };
      }
    }];
  }

  /* 20.09 CPO: lightweight-charts canvas'a yazar, yani `var(--bp-x)` string'ini
     COZEMEZ — bu yuzden renkler burada literal duruyordu ve tokens.css'ten
     KOPUKTU. _tok() token'i calisma aninda okur, cozulmezse bugunku literali
     yedek olarak dondurur (davranis degismez, tek kaynak kazanilir). */
  /* "#30363d" -> "48,54,61". Token rgb degilse yedek dizgeyi dondurur --
     uydurmaz. */
  function _hexRgb(hex, yedek) {
    var m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());
    if (!m) return yedek;
    var n = parseInt(m[1], 16);
    return ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255);
  }

  function _tok(ad, yedek) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(ad).trim();
      return v || yedek;
    } catch (e) { return yedek; }
  }

  /* Kanonik EMA12/EMA99 çizgi çifti + fill primitive. Renkler: EMA12 marka rengi
     (--bp-brand, hisse.html'in secimiydi - index.html'in jenerik #58a6ff'i
     yerine bu kanonik oldu), EMA99 --bp-accent-yellow (20.09'da token'landi: ayni deger
     bu dosyada, hisse.html gostergesinde, /metodoloji ve blog duzyazisinda
     birbirinden BAGIMSIZ yaziliydi; duzyazi urunun GERCEK rengini iddia
     ettigi icin biri kaysa digerleri urunu yanlis anlatirdi). */
  function addEmaPair(chart, ema12Data, ema99Data) {
    var e99 = chart.addLineSeries({ color: _tok('--bp-accent-yellow', '#e3b341'), lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false });
    e99.setData(ema99Data);
    var e12 = chart.addLineSeries({ color: _tok('--bp-brand', '#b8c3ff'), lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false });
    e12.setData(ema12Data);
    e12.attachPrimitive(new EmaFillPrimitive(chart, ema12Data, ema99Data,
      'rgba(' + _tok('--bp-al-rgb', '0,226,144') + ',0.13)',
      'rgba(' + _tok('--bp-sat-rgb', '248,81,73') + ',0.11)'));
    return { e12: e12, e99: e99 };
  }

  /* Kanonik OHLC hover tooltip — chart-engineering.md "Custom Tooltip (Overlay Div)"
     deseni, TR etiket + kenar-kelepceleme (r137'nin tarih-etiketi clamp'iyle ayni
     ilke: .chart-section/.chart-accordion'un overflow:hidden'i disina tasan bir div'i
     kirpar, elMain sinirlari icinde tutulmali).
     dateFmt(time) -> caller kendi zaman eksenine gore (string tarih ya da sequential
     index) tarihi Turkce bicimde dondurur. */
  function attachOhlcTooltip(chart, candleSeries, elMain, dateFmt) {
    var tip = document.createElement('div');
    tip.style.cssText =
      'position:absolute;display:none;padding:8px 10px;background:var(--bp-surface);' +
      'border:1px solid var(--bp-border);border-radius:6px;color:var(--bp-text);font-size:11px;' +
      'line-height:1.55;font-variant-numeric:tabular-nums;pointer-events:none;' +
      'z-index:var(--bp-z-chart-legend);white-space:nowrap;box-shadow:var(--bp-shadow-sm)';
    elMain.style.position = 'relative';
    elMain.appendChild(tip);

    function fmt(v) { return v == null ? '—' : (+v).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

    chart.subscribeCrosshairMove(function (param) {
      if (!param.time || !param.point) { tip.style.display = 'none'; return; }
      var bar = param.seriesData.get(candleSeries);
      if (!bar) { tip.style.display = 'none'; return; }
      tip.style.display = 'block';
      tip.innerHTML =
        '<div style="color:var(--bp-text3);margin-bottom:4px;font-weight:600">' + dateFmt(param.time) + '</div>' +
        '<div>A: <span style="color:var(--bp-text)">' + fmt(bar.open) + '</span>' +
        '&nbsp;&nbsp;Y: <span style="color:' + _tok('--bp-al', '#00e290') + '">' + fmt(bar.high) + '</span></div>' +
        '<div>D: <span style="color:' + _tok('--bp-sat', '#f85149') + '">' + fmt(bar.low) + '</span>' +
        '&nbsp;&nbsp;K: <span style="color:var(--bp-text);font-weight:700">' + fmt(bar.close) + ' ₺</span></div>';
      /* Konteyner sinirlari icinde kelepcele (r137: .chart-section overflow:hidden
         disina tasarsa kirpilir) - once olc, sonra konumlandir. */
      var tw = tip.offsetWidth, th = tip.offsetHeight;
      var x = param.point.x + 14;
      if (x + tw > elMain.clientWidth) x = param.point.x - tw - 14;
      if (x < 0) x = 4;
      var y = param.point.y - th - 10;
      if (y < 0) y = param.point.y + 14;
      tip.style.left = x + 'px';
      tip.style.top = y + 'px';
    });

    return tip;
  }

  window.BPChart = {
    tok: _tok,               /* K-BG: sablonlar KENDI okuyucusunu yazmasin */
    fmtTickDate: fmtTickDate,
    baseOpts: baseOpts,
    addCandleSeries: addCandleSeries,
    addVolumeSeries: addVolumeSeries,
    addEmaPair: addEmaPair,
    EmaFillPrimitive: EmaFillPrimitive,
    attachOhlcTooltip: attachOhlcTooltip,
  };
})();
