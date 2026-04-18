from flask import Flask, jsonify, render_template, Response, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
import threading
import collections
import logging
import time
import json

app = Flask(__name__)


def _clean(obj):
    """NaN/Inf değerlerini None'a çevir — JSON'da NaN geçersiz, JS crash yapar."""
    import math
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def safe_json(data):
    """NaN-temizlenmiş JSON Response döner."""
    return Response(
        json.dumps(_clean(data)),
        mimetype="application/json",
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bist30")

BIST30 = [
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO",
    "EREGL", "FROTO", "GARAN", "HEKTS", "ISCTR",
    "KCHOL", "KRDMD", "MGROS", "ODAS",
    "OYAKC", "PGSUS", "SAHOL", "SASA", "SISE",
    "SOKM", "TAVHL", "TCELL", "THYAO", "TKFEN",
    "TOASO", "TUPRS", "VAKBN", "YKBNK", "XU030"
]

STOCK_NAMES = {
    "AKBNK": "Akbank T.A.Ş.",
    "ARCLK": "Arçelik A.Ş.",
    "ASELS": "Aselsan Elektronik Sanayi",
    "BIMAS": "BİM Birleşik Mağazalar",
    "EKGYO": "Emlak Konut GYO",
    "EREGL": "Ereğli Demir ve Çelik",
    "FROTO": "Ford Otomotiv Sanayi",
    "GARAN": "Garanti BBVA",
    "HEKTS": "Hektaş Ticaret T.A.Ş.",
    "ISCTR": "İş Bankası (C)",
    "KCHOL": "Koç Holding A.Ş.",
    "KRDMD": "Kardemir Karabük Demir Çelik",
    "MGROS": "Migros Ticaret A.Ş.",
    "ODAS":  "Odaş Elektrik Üretim",
    "OYAKC": "Oyak Çimento Fabrikaları",
    "PGSUS": "Pegasus Hava Taşımacılığı",
    "SAHOL": "Sabancı Holding",
    "SASA":  "Sasa Polyester Sanayi",
    "SISE":  "Türkiye Şişe ve Cam Fabrikaları",
    "SOKM":  "Şok Marketler Ticaret",
    "TAVHL": "TAV Havalimanları Holding",
    "TCELL": "Turkcell İletişim Hizmetleri",
    "THYAO": "Türk Hava Yolları",
    "TKFEN": "Tekfen Holding A.Ş.",
    "TOASO": "Tofaş Türk Otomobil Fabrikası",
    "TUPRS": "Tüpraş Türkiye Petrol Rafinerileri",
    "VAKBN": "Vakıfbank",
    "YKBNK": "Yapı ve Kredi Bankası",
    "XU030": "BIST 30 Endeksi",
}

_cache       = {"data": [], "updated_at": None}
_live_prices = {}
_lock        = threading.Lock()
_sse_clients = []
_sse_lock    = threading.Lock()


def _push_sse(payload: dict):
    msg = f"data: {json.dumps(payload)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.append(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


def compute_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def compute_adx(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    plus_dm  = high.diff()
    minus_dm = -low.diff()
    plus_dm  = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    atr      = tr.ewm(com=period - 1, adjust=False).mean()
    plus_di  = 100 * plus_dm.ewm(com=period - 1, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(com=period - 1, adjust=False).mean() / atr

    dx  = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(com=period - 1, adjust=False).mean()
    return adx, plus_di, minus_di


def compute_supertrend(high, low, close, period=10, multiplier=3):
    """ATR(10,3) — numpy tabanlı.
    Returns (direction Series, st_line Series); warmup barları NaN."""
    hl2 = (high.values + low.values) / 2
    cl  = close.values
    hi  = high.values
    lo  = low.values
    n   = len(cl)

    # True Range
    tr_arr      = np.empty(n)
    tr_arr[0]   = hi[0] - lo[0]
    tr_arr[1:]  = np.maximum(hi[1:] - lo[1:],
                  np.maximum(np.abs(hi[1:] - cl[:-1]),
                             np.abs(lo[1:] - cl[:-1])))

    # ATR — Wilder smoothing (SMA seed)
    atr         = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = np.mean(tr_arr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr_arr[i]) / period

    basic_upper = hl2 + multiplier * atr   # NaN where atr is NaN
    basic_lower = hl2 - multiplier * atr

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    direction   = np.ones(n, dtype=int)
    st_line     = np.full(n, np.nan)

    # Geçerli ilk index (ATR warmup sonrası)
    start = period  # atr[period-1] geçerli, ama final band için period'dan başla

    for i in range(start, n):
        pu = final_upper[i - 1]
        pl = final_lower[i - 1]

        # NaN warmup koruması
        if np.isnan(pu):
            pu = basic_upper[i]
        if np.isnan(pl):
            pl = basic_lower[i]

        bu = basic_upper[i]
        bl = basic_lower[i]

        final_upper[i] = bu if (np.isnan(bu) or bu < pu or cl[i - 1] > pu) else pu
        final_lower[i] = bl if (np.isnan(bl) or bl > pl or cl[i - 1] < pl) else pl

        if direction[i - 1] == 1:
            direction[i] = 1 if cl[i] >= final_lower[i] else -1
        else:
            direction[i] = -1 if cl[i] <= final_upper[i] else 1

        st_line[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

    dir_series = pd.Series(direction, index=close.index)
    stl_series = pd.Series(st_line,   index=close.index)
    return dir_series, stl_series


def _fill_intraday_gaps(df, ticker):
    """Günlük data'da eksik günleri 1m data'dan OHLC sentezleyerek doldur.
    yfinance bazen son 1-2 günün daily barını geciktiriyor."""
    try:
        df5d = yf.download(ticker, period="5d", interval="1m",
                           progress=False, auto_adjust=True, timeout=20)
        if df5d is None or df5d.empty:
            return df
        if isinstance(df5d.columns, pd.MultiIndex):
            df5d.columns = df5d.columns.get_level_values(0)
            df5d = df5d.loc[:, ~df5d.columns.duplicated()]

        last_daily = df.index[-1].date()
        added = False
        for day in sorted(set(df5d.index.date)):
            if day <= last_daily:
                continue
            day_bars = df5d[df5d.index.map(lambda x: x.date()) == day].dropna()
            if len(day_bars) < 30:   # kısmen gelen gün, geç
                continue
            ts = pd.Timestamp(day, tz=df.index.tz)
            synth = pd.DataFrame({
                "Open":   float(day_bars["Open"].iloc[0]),
                "High":   float(day_bars["High"].max()),
                "Low":    float(day_bars["Low"].min()),
                "Close":  float(day_bars["Close"].iloc[-1]),
                "Volume": float(day_bars["Volume"].sum()) if "Volume" in day_bars else 0,
            }, index=pd.DatetimeIndex([ts]))
            df = pd.concat([df, synth[df.columns]])
            added = True
        if added:
            logger.info("_fill_intraday_gaps(%s): eksik gun(ler) 1m'den eklendi", ticker)
        return df
    except Exception as e:
        logger.warning("_fill_intraday_gaps(%s): %s", ticker, e)
        return df


def _weekly_trend(ticker: str) -> int:
    """Haftalık EMA20 yönü: +1 yükselen, -1 düşen, 0 belirsiz/hata."""
    try:
        wdf = yf.download(ticker, period="1y", interval="1wk",
                          progress=False, auto_adjust=True, timeout=20)
        if wdf is None or len(wdf) < 25:
            return 0
        if isinstance(wdf.columns, pd.MultiIndex):
            wdf.columns = wdf.columns.get_level_values(0)
            wdf = wdf.loc[:, ~wdf.columns.duplicated()]
        wdf    = wdf.dropna()
        wclose = wdf["Close"].squeeze()
        wema20 = compute_ema(wclose, 20)
        if len(wema20) < 2:
            return 0
        return 1 if float(wema20.iloc[-1]) > float(wema20.iloc[-2]) else -1
    except Exception:
        return 0


def analyze(ticker_base):
    ticker = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"

    try:
        weekly_dir = _weekly_trend(ticker)

        df = yf.download(ticker, period="2y", interval="1d",
                         progress=False, auto_adjust=True, timeout=30)
        if df is None or len(df) < 120:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]

        df    = df.dropna()
        df    = _fill_intraday_gaps(df, ticker)   # yfinance gecikmeli günleri 1m'den tamamla
        df    = df.sort_index()
        close = df["Close"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()

        ema12                  = compute_ema(close, 12)
        ema99                  = compute_ema(close, 99)
        adx, di_plus, di_minus = compute_adx(high, low, close)
        supertrend, st_line    = compute_supertrend(high, low, close)

        def v(s):  return float(s.iloc[-1])
        def v2(s): return float(s.iloc[-2])

        c       = v(close)
        e12     = v(ema12);   e99 = v(ema99)
        adx_val = v(adx)
        di_p    = v(di_plus); di_m = v(di_minus)
        st_val  = int(v(supertrend))
        _sl_raw = float(st_line.iloc[-1])
        sl_val  = round(_sl_raw, 2) if not np.isnan(_sl_raw) else None

        prev_c     = v2(close)
        change_pct = ((c - prev_c) / prev_c) * 100 if prev_c != 0 else 0

        # ── 3-Kriter Sinyal Motoru: ST + ADX≥25 + EMA12/99 ─────────────
        st_bull  = st_val == 1
        st_bear  = st_val == -1
        adx_bull = adx_val >= 25 and di_p > di_m
        adx_bear = adx_val >= 25 and di_m > di_p
        e12_bull = e12 > e99
        e12_bear = e12 < e99

        bull_score = int(st_bull) + int(adx_bull) + int(e12_bull)  # max 3
        bear_score = int(st_bear) + int(adx_bear) + int(e12_bear)  # max 3

        # Haftalık gate: büyük ters trendde sinyal üretme
        if bull_score >= 3 and weekly_dir != -1:
            signal = "AL"
        elif bear_score >= 3 and weekly_dir != 1:
            signal = "SAT"
        else:
            signal = "BEKLE"

        # ── Sinyal tarihi & süre ─────────────────────────────────────────
        def bar_signal(i):
            ei12  = float(ema12.iloc[i]);  ei99  = float(ema99.iloc[i])
            ai    = float(adx.iloc[i])
            dip_i = float(di_plus.iloc[i]); dim_i = float(di_minus.iloc[i])
            sti   = int(supertrend.iloc[i])
            bs  = int(sti == 1)  + int(ai >= 25 and dip_i > dim_i) + int(ei12 > ei99)
            brs = int(sti == -1) + int(ai >= 25 and dim_i > dip_i) + int(ei12 < ei99)
            return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"

        today_str   = datetime.now().strftime("%d.%m.%Y")
        signal_date = today_str
        signal_bars = 1
        n = len(close)
        try:
            for i in range(n - 2, max(n - 120, 0), -1):
                if bar_signal(i) != signal:
                    signal_date = close.index[i + 1].strftime("%d.%m.%Y")
                    signal_bars = (n - 1) - (i + 1) + 1
                    break
            else:
                signal_date = close.index[max(n - 120, 0)].strftime("%d.%m.%Y")
                signal_bars = n - max(n - 120, 0)
        except Exception:
            pass

        # Sinyal başındaki kapanış fiyatı
        signal_start = max(0, (n - 1) - (signal_bars - 1))
        signal_price = round(float(close.iloc[signal_start]), 2) if signal != "BEKLE" else None

        is_new_signal = (signal_date == today_str)
        confirmed     = signal != "BEKLE" and signal_bars >= 3

        return {
            "ticker":        ticker_base,
            "price":         round(c, 2),
            "change_pct":    round(change_pct, 2),
            "signal":        signal,
            "signal_date":   signal_date,
            "signal_bars":   signal_bars,
            "signal_price":  signal_price,
            "sl_level":      sl_val,
            "is_new_signal": is_new_signal,
            "confirmed":     confirmed,
            "bull_score":    bull_score,
            "bear_score":    bear_score,
            "weekly_trend":  weekly_dir,
            "indicators": {
                "supertrend": {
                    "label": "ST",
                    "value": "LONG" if st_bull else "SHORT",
                    "bull":  st_bull,  "bear": st_bear,
                },
                "adx": {
                    "label": f"ADX {adx_val:.0f}",
                    "value": f"DI+{di_p:.0f}/DI-{di_m:.0f}",
                    "bull":  adx_bull, "bear": adx_bear,
                },
                "ema1299": {
                    "label": "EMA12/99",
                    "value": f"{e12:.0f}/{e99:.0f}",
                    "bull":  e12_bull, "bear": e12_bear,
                },
            },
        }
    except Exception as e:
        logger.error("analyze(%s): %s", ticker_base, e, exc_info=True)
        return None


def refresh_data():
    results = []
    for t in BIST30:
        r = analyze(t)
        if r:
            results.append(r)
        time.sleep(0.3)

    results.sort(key=lambda x: (
        0 if x.get("is_new_signal") else 1,
        0 if x["signal"] == "AL" else 1 if x["signal"] == "SAT" else 2,
        -x["bull_score"] if x["signal"] == "AL" else -x["bear_score"]
    ))

    with _lock:
        _cache["data"] = results
        _cache["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def fetch_live_prices():
    tickers_str = " ".join(t + ".IS" for t in BIST30)
    try:
        df = yf.download(
            tickers_str, period="2d", interval="1m",
            progress=False, auto_adjust=True, group_by="ticker", timeout=30
        )
        if df is None or df.empty:
            return

        payload = {}
        now_str  = datetime.now().strftime("%H:%M:%S")

        for t in BIST30:
            try:
                sym = t + ".IS"
                if isinstance(df.columns, pd.MultiIndex):
                    lvls = df.columns.get_level_values(0)
                    if sym in lvls:
                        closes = df[sym]["Close"].dropna()
                    else:
                        continue
                else:
                    closes = df["Close"].dropna()

                if closes is None or len(closes) < 2:
                    continue

                price      = float(closes.iloc[-1])
                today_date = closes.index[-1].date()
                prev_bars  = closes[closes.index.map(lambda x: x.date()) < today_date]
                prev       = float(prev_bars.iloc[-1]) if len(prev_bars) > 0 else float(closes.iloc[-2])
                chg        = ((price - prev) / prev * 100) if prev else 0

                payload[t] = {
                    "price":      round(price, 2),
                    "change_pct": round(chg, 2),
                    "updated":    now_str,
                }
            except Exception:
                continue

        if payload:
            with _lock:
                _live_prices.update(payload)
            _push_sse({"type": "prices", "data": payload, "ts": now_str})

    except Exception as e:
        logger.error("fetch_live_prices: %s", e, exc_info=True)


def background_live_prices():
    while True:
        fetch_live_prices()
        time.sleep(30)


def background_refresh():
    while True:
        refresh_chart()
        refresh_data()
        time.sleep(900)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    with _lock:
        return safe_json({
            "stocks":     _cache["data"],
            "updated_at": _cache["updated_at"],
            "loading":    len(_cache["data"]) == 0
        })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=refresh_data, daemon=True).start()
    return jsonify({"status": "refreshing"})


@app.route("/api/stream")
def api_stream():
    client_queue = collections.deque()
    with _sse_lock:
        _sse_clients.append(client_queue)

    with _lock:
        initial = dict(_live_prices)
    initial_msg = (
        f"data: {json.dumps({'type': 'prices', 'data': initial, 'ts': datetime.now().strftime('%H:%M:%S')})}\n\n"
        if initial else ""
    )

    def generate():
        try:
            if initial_msg:
                yield initial_msg
            while True:
                while client_queue:
                    yield client_queue.popleft()
                time.sleep(0.5)
        finally:
            with _sse_lock:
                if client_queue in _sse_clients:
                    _sse_clients.remove(client_queue)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


def _safe_float(val):
    if hasattr(val, "iloc"):
        return float(val.iloc[0])
    if hasattr(val, "item"):
        return float(val.item())
    return float(val)


def get_chart_data():
    """XU030 grafik verisi — _compute_chart_data wrapper (5y period)."""
    DISPLAY_BARS = 500
    WARMUP_MIN   = 200

    try:
        df = yf.Ticker("XU030.IS").history(period="5y", interval="1d", auto_adjust=True)
        if df is None or len(df) < WARMUP_MIN + 50:
            return None

        df    = df[["Open", "High", "Low", "Close"]].dropna()
        df    = _fill_intraday_gaps(df, "XU030.IS")   # eksik günleri tamamla
        df    = df.sort_index()
        close = df["Close"]
        high  = df["High"]
        low   = df["Low"]
        open_ = df["Open"]

        # ── İndikatörleri FULL veri üzerinde hesapla (warmup) ────────────
        ema12                      = compute_ema(close, 12)
        ema99                      = compute_ema(close, 99)
        adx, di_plus_s, di_minus_s = compute_adx(high, low, close)
        supertrend, st_line_s      = compute_supertrend(high, low, close)

        # ── Gösterim için son DISPLAY_BARS barı kes ───────────────────────
        show_idx = df.index[-DISPLAY_BARS:]
        show_set = set(show_idx.strftime("%Y-%m-%d"))

        def series(s):
            out = []
            for ts, val in s.items():
                if pd.isna(val): continue
                d = ts.strftime("%Y-%m-%d")
                if d not in show_set: continue
                out.append({"time": d, "value": round(float(val), 4)})
            return out

        # OHLC
        ohlc = []
        for ts in show_idx:
            try:
                ohlc.append({
                    "time":  ts.strftime("%Y-%m-%d"),
                    "open":  round(_safe_float(open_[ts]),  2),
                    "high":  round(_safe_float(high[ts]),   2),
                    "low":   round(_safe_float(low[ts]),    2),
                    "close": round(_safe_float(close[ts]),  2),
                })
            except Exception:
                continue

        # Supertrend çizgisi — iloc ile eriş (loc/label indexing sorununu önler)
        st_line_data = []
        stl_arr = st_line_s.values
        std_arr = supertrend.values
        all_dates = [ts.strftime("%Y-%m-%d") for ts in df.index]
        for i, d_str in enumerate(all_dates):
            if d_str not in show_set: continue
            stl = stl_arr[i]
            if np.isnan(stl): continue
            st_line_data.append({
                "time":  d_str,
                "value": round(float(stl), 2),
                "bull":  int(std_arr[i]) == 1,
            })

        # ── Sinyal değişim işaretçileri (grafik okleri) ──────────────────
        def bar_sig(i):
            ei12  = float(ema12.iloc[i]);  ei99  = float(ema99.iloc[i])
            ai    = float(adx.iloc[i])
            dip_i = float(di_plus_s.iloc[i]); dim_i = float(di_minus_s.iloc[i])
            sti   = int(supertrend.iloc[i])
            bs  = int(sti == 1)  + int(ai >= 25 and dip_i > dim_i) + int(ei12 > ei99)
            brs = int(sti == -1) + int(ai >= 25 and dim_i > dip_i) + int(ei12 < ei99)
            return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"

        markers   = []
        prev_bsig = "BEKLE"
        for i in range(200, len(close)):
            sig = bar_sig(i)
            if sig != prev_bsig and sig != "BEKLE":
                d_str = close.index[i].strftime("%Y-%m-%d")
                if d_str in show_set:
                    markers.append({
                        "time":     d_str,
                        "position": "belowBar" if sig == "AL" else "aboveBar",
                        "color":    "#3fb950"  if sig == "AL" else "#f85149",
                        "shape":    "arrowUp"  if sig == "AL" else "arrowDown",
                        "text":     "AL"       if sig == "AL" else "SAT",
                    })
            prev_bsig = sig

        # ── Son bar değerleri ────────────────────────────────────────────
        c       = float(close.iloc[-1])
        prev_c  = float(close.iloc[-2])
        chg     = ((c - prev_c) / prev_c) * 100 if prev_c else 0
        adx_val = float(adx.iloc[-1])
        di_p    = float(di_plus_s.iloc[-1]); di_m = float(di_minus_s.iloc[-1])
        e12_val = float(ema12.iloc[-1])
        e99_val = float(ema99.iloc[-1])
        st_val   = int(supertrend.iloc[-1])
        _sl_raw  = float(st_line_s.iloc[-1])
        sl_val   = round(_sl_raw, 2) if not np.isnan(_sl_raw) else None

        st_bull  = st_val == 1;   st_bear  = st_val == -1
        adx_bull = adx_val >= 25 and di_p > di_m
        adx_bear = adx_val >= 25 and di_m > di_p
        e12_bull = e12_val > e99_val; e12_bear = e12_val < e99_val

        bull_score = int(st_bull) + int(adx_bull) + int(e12_bull)
        bear_score = int(st_bear) + int(adx_bear) + int(e12_bear)
        signal = "AL" if bull_score >= 3 else "SAT" if bear_score >= 3 else "BEKLE"

        return {
            "ohlc":      ohlc,
            "ema12":     series(ema12),
            "ema99":     series(ema99),
            "st_line":   st_line_data,
            "markers":   markers,
            "summary": {
                "price":      round(c, 2),
                "change_pct": round(chg, 2),
                "signal":     signal,
                "bull_score": bull_score,
                "bear_score": bear_score,
                "sl_level":   sl_val,
                "adx":        round(adx_val, 1),
                "e12":        round(e12_val, 1),
                "e99":        round(e99_val, 1),
                "st_bull":    st_bull,  "st_bear":  st_bear,
                "adx_bull":   adx_bull, "adx_bear": adx_bear,
                "e12_bull":   e12_bull, "e12_bear": e12_bear,
            }
        }
    except Exception as e:
        logger.error("chart error: %s", e, exc_info=True)
        return None


_chart_cache       = {"data": None, "updated_at": None}
_stock_chart_cache = {}          # {ticker: {"data": ..., "ts": float, "updated_at": str}}
_STOCK_CACHE_TTL   = 900         # 15 dakika


def _generate_commentary(ticker, signal, signal_bars, signal_date, adx, di_p, di_m, e12, e99, st_bull):
    """Algoritmik teknik yorum metni üretir (SEO + kullanıcı için)."""
    name = STOCK_NAMES.get(ticker, ticker)
    adx_quality = "çok güçlü" if adx >= 40 else "güçlü" if adx >= 30 else "orta güçte" if adx >= 25 else "zayıf"

    if signal == "AL":
        trend_dir  = "yükseliş"
        st_text    = "yükseliş yönünde"
        ema_text   = f"EMA12 ({e12:.0f} ₺), EMA99 ({e99:.0f} ₺) üzerinde seyrediyor"
        di_text    = f"DI+ {di_p:.0f} DI- {di_m:.0f}'i geçmiş durumda"
        dur_text   = f"Son {signal_bars} gündür AL sinyali aktif" if signal_bars > 1 else "Bugün AL sinyali oluştu"
        if signal_date:
            dur_text += f" ({signal_date} tarihinden itibaren)" if signal_bars > 1 else ""
        return (
            f"{ticker} ({name}) hissesi {dur_text}. "
            f"Supertrend göstergesi {st_text}, ADX {adx:.0f} ile {adx_quality} bir {trend_dir} trendi işaret ediyor. "
            f"{ema_text}. {di_text}."
        )
    elif signal == "SAT":
        trend_dir  = "düşüş"
        st_text    = "düşüş yönünde"
        ema_text   = f"EMA12 ({e12:.0f} ₺), EMA99 ({e99:.0f} ₺) altında seyrediyor"
        di_text    = f"DI- {di_m:.0f} DI+ {di_p:.0f}'ün üzerinde"
        dur_text   = f"Son {signal_bars} gündür SAT sinyali aktif" if signal_bars > 1 else "Bugün SAT sinyali oluştu"
        if signal_date:
            dur_text += f" ({signal_date} tarihinden itibaren)" if signal_bars > 1 else ""
        return (
            f"{ticker} ({name}) hissesi {dur_text}. "
            f"Supertrend göstergesi {st_text}, ADX {adx:.0f} ile {adx_quality} bir {trend_dir} trendi işaret ediyor. "
            f"{ema_text}. {di_text}."
        )
    else:
        mixed = ""
        if st_bull and e12 > e99:
            mixed = "Supertrend ve EMA yükselen ancak ADX trend gücü henüz yetersiz."
        elif not st_bull and e12 < e99:
            mixed = "Supertrend ve EMA düşen ancak ADX trend gücü yetersiz."
        else:
            mixed = "İndikatörler birbirini teyit etmiyor, karmaşık bir görünüm var."
        return (
            f"{ticker} ({name}) hissesi şu anda net bir AL/SAT sinyali üretmiyor. "
            f"{mixed} "
            f"ADX {adx:.0f} ({adx_quality}), EMA12 {e12:.0f} / EMA99 {e99:.0f}."
        )


# ── Ortak grafik verisi hesaplama (XU030 + bireysel hisseler) ─────────────────
def _compute_chart_data(ticker_base, period="2y"):
    """Herhangi bir hisse için grafik verisi hesaplar (OHLC, EMA, ST, sinyal geçmişi)."""
    ticker      = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"
    DISPLAY_BARS = 500
    WARMUP_MIN   = 150

    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True, timeout=30)
        if df is None or len(df) < WARMUP_MIN:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]

        has_volume = "Volume" in df.columns
        cols = ["Open", "High", "Low", "Close"] + (["Volume"] if has_volume else [])
        df    = df[cols].dropna(subset=["Open", "High", "Low", "Close"])
        df    = _fill_intraday_gaps(df, ticker)
        df    = df.sort_index()

        close  = df["Close"]
        high   = df["High"]
        low    = df["Low"]
        open_  = df["Open"]
        volume = df["Volume"] if has_volume else None

        ema12                      = compute_ema(close, 12)
        ema99                      = compute_ema(close, 99)
        adx, di_plus_s, di_minus_s = compute_adx(high, low, close)
        supertrend, st_line_s      = compute_supertrend(high, low, close)

        show_idx = df.index[-DISPLAY_BARS:]
        show_set = set(show_idx.strftime("%Y-%m-%d"))

        def series(s):
            out = []
            for ts, val in s.items():
                if pd.isna(val): continue
                d = ts.strftime("%Y-%m-%d")
                if d not in show_set: continue
                out.append({"time": d, "value": round(float(val), 4)})
            return out

        # OHLC
        ohlc = []
        for ts in show_idx:
            try:
                ohlc.append({
                    "time":  ts.strftime("%Y-%m-%d"),
                    "open":  round(_safe_float(open_[ts]),  2),
                    "high":  round(_safe_float(high[ts]),   2),
                    "low":   round(_safe_float(low[ts]),    2),
                    "close": round(_safe_float(close[ts]),  2),
                })
            except Exception:
                continue

        # Supertrend çizgisi
        st_line_data = []
        stl_arr  = st_line_s.values
        std_arr  = supertrend.values
        all_dates = [ts.strftime("%Y-%m-%d") for ts in df.index]
        for i, d_str in enumerate(all_dates):
            if d_str not in show_set: continue
            stl = stl_arr[i]
            if np.isnan(stl): continue
            st_line_data.append({
                "time":  d_str,
                "value": round(float(stl), 2),
                "bull":  int(std_arr[i]) == 1,
            })

        # Sinyal fonksiyonu (tek bar)
        def bar_sig(i):
            ei12  = float(ema12.iloc[i]);   ei99  = float(ema99.iloc[i])
            ai    = float(adx.iloc[i])
            dip_i = float(di_plus_s.iloc[i]); dim_i = float(di_minus_s.iloc[i])
            sti   = int(supertrend.iloc[i])
            bs  = int(sti == 1)  + int(ai >= 25 and dip_i > dim_i) + int(ei12 > ei99)
            brs = int(sti == -1) + int(ai >= 25 and dim_i > dip_i) + int(ei12 < ei99)
            return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"

        # Grafik marker'ları ve sinyal geçmişi
        markers        = []
        signal_history = []
        prev_sig       = "BEKLE"
        for i in range(200, len(close)):
            sig = bar_sig(i)
            if sig != prev_sig and sig != "BEKLE":
                d_str = close.index[i].strftime("%Y-%m-%d")
                if d_str in show_set:
                    markers.append({
                        "time":     d_str,
                        "position": "belowBar" if sig == "AL" else "aboveBar",
                        "color":    "#3fb950"  if sig == "AL" else "#f85149",
                        "shape":    "arrowUp"  if sig == "AL" else "arrowDown",
                        "text":     sig,
                    })
                signal_history.append({
                    "date":   close.index[i].strftime("%d.%m.%Y"),
                    "signal": sig,
                    "price":  round(float(close.iloc[i]), 2),
                })
            prev_sig = sig
        signal_history = list(reversed(signal_history[-15:]))   # en yeni başta, max 15

        # Özet (son bar)
        c       = float(close.iloc[-1])
        prev_c  = float(close.iloc[-2])
        chg     = ((c - prev_c) / prev_c) * 100 if prev_c else 0
        adx_val = float(adx.iloc[-1])
        di_p    = float(di_plus_s.iloc[-1]); di_m = float(di_minus_s.iloc[-1])
        e12_val = float(ema12.iloc[-1])
        e99_val = float(ema99.iloc[-1])
        st_val  = int(supertrend.iloc[-1])
        _sl_raw = float(st_line_s.iloc[-1])
        sl_val  = round(_sl_raw, 2) if not np.isnan(_sl_raw) else None

        st_bull  = st_val == 1;   st_bear  = st_val == -1
        adx_bull = adx_val >= 25 and di_p > di_m
        adx_bear = adx_val >= 25 and di_m > di_p
        e12_bull = e12_val > e99_val; e12_bear = e12_val < e99_val
        bull_score = int(st_bull) + int(adx_bull) + int(e12_bull)
        bear_score = int(st_bear) + int(adx_bear) + int(e12_bear)
        signal     = "AL" if bull_score >= 3 else "SAT" if bear_score >= 3 else "BEKLE"

        # ── Volume histogram (gösterim barları) ──────────────────────────
        vol_data = []
        if volume is not None:
            avg_vol = float(volume.iloc[-60:].mean()) if len(volume) >= 60 else float(volume.mean())
            for ts in show_idx:
                try:
                    v = float(volume[ts]) if not pd.isna(volume[ts]) else 0
                    cl_ = float(close[ts]); op_ = float(open_[ts])
                    color = "#3fb950" if cl_ >= op_ else "#f85149"
                    # yüksek hacim biraz daha parlak
                    if avg_vol > 0 and v > avg_vol * 2:
                        color = "#3fb950cc" if cl_ >= op_ else "#f85149cc"
                    vol_data.append({"time": ts.strftime("%Y-%m-%d"), "value": v, "color": color})
                except Exception:
                    continue

        # ── 52 haftalık yüksek / düşük (yaklaşık 252 işlem günü) ─────────
        week52_bars = min(252, len(close))
        w52_close   = close.iloc[-week52_bars:]
        w52_high    = round(float(w52_close.max()), 2)
        w52_low     = round(float(w52_close.min()), 2)

        # ── Güncel sinyal süresi (son sinyal değişiminden beri) ───────────
        signal_bars = 1
        signal_date_str = signal_history[0]["date"] if signal_history else ""
        if signal_history:
            # son al/sat değişimi
            signal_bars = 1
            for idx2 in range(len(close) - 1, -1, -1):
                if bar_sig(idx2) != signal:
                    signal_bars = (len(close) - 1) - idx2
                    break

        # ── Otomatik teknik yorum metni ───────────────────────────────────
        commentary = _generate_commentary(
            ticker_base, signal, signal_bars, signal_date_str,
            adx_val, di_p, di_m, e12_val, e99_val, st_bull
        )

        return {
            "ohlc":           ohlc,
            "ema12":          series(ema12),
            "ema99":          series(ema99),
            "st_line":        st_line_data,
            "markers":        markers,
            "signal_history": signal_history,
            "volume":         vol_data,
            "week52":         {"high": w52_high, "low": w52_low},
            "commentary":     commentary,
            "summary": {
                "price":      round(c, 2),
                "change_pct": round(chg, 2),
                "signal":     signal,
                "bull_score": bull_score,
                "bear_score": bear_score,
                "sl_level":   sl_val,
                "adx":        round(adx_val, 1),
                "di_plus":    round(di_p, 1),
                "di_minus":   round(di_m, 1),
                "e12":        round(e12_val, 1),
                "e99":        round(e99_val, 1),
                "st_bull":    st_bull,  "st_bear":  st_bear,
                "adx_bull":   adx_bull, "adx_bear": adx_bear,
                "e12_bull":   e12_bull, "e12_bear": e12_bear,
            }
        }
    except Exception as e:
        logger.error("_compute_chart_data(%s): %s", ticker_base, e, exc_info=True)
        return None


def refresh_chart():
    d = get_chart_data()
    if d:
        with _lock:
            _chart_cache["data"] = d
            _chart_cache["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")


@app.route("/api/chart")
def api_chart():
    with _lock:
        return safe_json({
            "chart":      _chart_cache["data"],
            "updated_at": _chart_cache["updated_at"],
            "loading":    _chart_cache["data"] is None,
        })


# ── Bireysel Hisse Sayfaları ──────────────────────────────────────────────────
@app.route("/hisse/<ticker>")
def stock_page(ticker):
    ticker = ticker.upper()
    if ticker not in BIST30:
        return render_template("index.html"), 404
    name = STOCK_NAMES.get(ticker, ticker)
    others = [t for t in BIST30 if t != ticker and t != "XU030"]
    return render_template("hisse.html",
                           ticker=ticker,
                           name=name,
                           others=others,
                           stock_names=STOCK_NAMES)


@app.route("/api/hisse/<ticker>/chart")
def api_stock_chart(ticker):
    ticker = ticker.upper()
    if ticker not in BIST30:
        return safe_json({"error": "Hisse bulunamadı"}), 404

    now = time.time()
    with _lock:
        cached = _stock_chart_cache.get(ticker)
        if cached and (now - cached["ts"]) < _STOCK_CACHE_TTL:
            return safe_json({
                "chart":      cached["data"],
                "updated_at": cached["updated_at"],
                "loading":    False,
            })

    # Cache yok veya bayat → taze hesapla
    data = _compute_chart_data(ticker, period="2y")
    if data:
        upd = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        with _lock:
            _stock_chart_cache[ticker] = {"data": data, "ts": now, "updated_at": upd}
        return safe_json({"chart": data, "updated_at": upd, "loading": False})

    return safe_json({"chart": None, "loading": True})


# ── SEO: sitemap, robots, favicon ────────────────────────────────────────────
@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": "/",            "priority": "1.0", "changefreq": "hourly"},
        {"loc": "/ozet",        "priority": "0.9", "changefreq": "daily"},
        {"loc": "/metodoloji",  "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/hakkinda",    "priority": "0.6", "changefreq": "monthly"},
    ]
    for t in BIST30:
        if t != "XU030":
            pages.append({"loc": f"/hisse/{t}", "priority": "0.85", "changefreq": "daily"})
    today = date.today().isoformat()
    xml   = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    base  = "https://borsapusula.com"   # Domain eklenince burası güncellenir
    for p in pages:
        xml.append(f"  <url><loc>{base}{p['loc']}</loc>"
                   f"<lastmod>{today}</lastmod>"
                   f"<changefreq>{p['changefreq']}</changefreq>"
                   f"<priority>{p['priority']}</priority></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "Sitemap: https://borsapusula.com/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


@app.route("/favicon.ico")
def favicon():
    import os
    fpath = os.path.join(app.root_path, "static", "favicon.svg")
    if os.path.exists(fpath):
        with open(fpath, "rb") as f:
            return Response(f.read(), mimetype="image/svg+xml")
    return "", 404


# ── Günlük Özet Sayfası ───────────────────────────────────────────────────────
@app.route("/ozet")
def ozet_page():
    with _lock:
        stocks = list(_cache["data"])
        updated_at = _cache.get("updated_at", "")
        loading = len(stocks) == 0

    al_list    = [s for s in stocks if s["signal"] == "AL"]
    sat_list   = [s for s in stocks if s["signal"] == "SAT"]
    bekle_list = [s for s in stocks if s["signal"] == "BEKLE"]
    new_signals = [s for s in stocks if s.get("is_new_signal")]

    today_str = date.today().strftime("%d.%m.%Y")
    return render_template("ozet.html",
        stocks=stocks, loading=loading, updated_at=updated_at,
        al_list=al_list, sat_list=sat_list, bekle_list=bekle_list,
        new_signals=new_signals, today_str=today_str,
        stock_names=STOCK_NAMES)


# ── Eğitim Sayfaları ──────────────────────────────────────────────────────────
@app.route("/metodoloji")
def metodoloji():
    return render_template("metodoloji.html")


@app.route("/hakkinda")
def hakkinda():
    return render_template("hakkinda.html")


# ── Startup ───────────────────────────────────────────────────────────────────
def _startup():
    refresh_chart()
    time.sleep(3)
    threading.Thread(target=background_refresh,     daemon=True).start()
    threading.Thread(target=background_live_prices, daemon=True).start()

threading.Thread(target=_startup, daemon=True).start()

logger.info("=" * 50)
logger.info("  BIST30 Sinyal Paneli başlatıldı")
logger.info("  http://localhost:8003")
logger.info("=" * 50)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003, debug=False)
