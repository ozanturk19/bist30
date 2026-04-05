from flask import Flask, jsonify, render_template, Response
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import threading
import collections
import logging
import time
import json

app = Flask(__name__)

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
    """ATR(10,3). Returns (direction_series, st_line_series).
    direction: +1=bullish, -1=bearish
    st_line : destek (bull) veya direnç (bear) — stop loss seviyesi."""
    hl2 = (high + low) / 2
    tr  = pd.concat([high - low,
                     (high - close.shift(1)).abs(),
                     (low  - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()

    for i in range(1, len(close)):
        fu_prev = final_upper.iloc[i - 1]
        fl_prev = final_lower.iloc[i - 1]
        c_prev  = close.iloc[i - 1]
        final_upper.iloc[i] = (basic_upper.iloc[i]
                                if basic_upper.iloc[i] < fu_prev or c_prev > fu_prev
                                else fu_prev)
        final_lower.iloc[i] = (basic_lower.iloc[i]
                                if basic_lower.iloc[i] > fl_prev or c_prev < fl_prev
                                else fl_prev)

    direction = pd.Series(1, index=close.index, dtype=int)
    st_line   = pd.Series(np.nan, index=close.index)
    for i in range(1, len(close)):
        prev = direction.iloc[i - 1]
        if prev == 1:
            direction.iloc[i] = 1 if close.iloc[i] >= final_lower.iloc[i] else -1
        else:
            direction.iloc[i] = -1 if close.iloc[i] <= final_upper.iloc[i] else 1
        st_line.iloc[i] = (final_lower.iloc[i] if direction.iloc[i] == 1
                           else final_upper.iloc[i])
    return direction, st_line


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
        sl_val  = round(float(st_line.iloc[-1]), 2)

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
            "sl_level":      sl_val if signal != "BEKLE" else None,
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

                price = float(closes.iloc[-1])
                prev  = float(closes.iloc[-2])
                chg   = ((price - prev) / prev * 100) if prev else 0

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
        return jsonify({
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
    """XU030 grafik verisi + Supertrend çizgisi + sinyal işaretçileri."""
    DISPLAY_BARS = 500
    WARMUP_MIN   = 200

    try:
        df = yf.Ticker("XU030.IS").history(period="5y", interval="1d", auto_adjust=True)
        if df is None or len(df) < WARMUP_MIN + 50:
            return None

        df    = df[["Open", "High", "Low", "Close"]].dropna()
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

        # Supertrend çizgisi — bull=yeşil / bear=kırmızı, SL göstergesi
        st_line_data = []
        for ts in show_idx:
            try:
                stl = float(st_line_s[ts])
                std = int(supertrend[ts])
                if pd.isna(stl): continue
                st_line_data.append({
                    "time":  ts.strftime("%Y-%m-%d"),
                    "value": round(stl, 2),
                    "bull":  std == 1,
                })
            except Exception:
                continue

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
        st_val  = int(supertrend.iloc[-1])
        sl_val  = round(float(st_line_s.iloc[-1]), 2)

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


_chart_cache = {"data": None, "updated_at": None}


def refresh_chart():
    d = get_chart_data()
    if d:
        with _lock:
            _chart_cache["data"] = d
            _chart_cache["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")


@app.route("/api/chart")
def api_chart():
    with _lock:
        return jsonify({
            "chart":      _chart_cache["data"],
            "updated_at": _chart_cache["updated_at"],
            "loading":    _chart_cache["data"] is None,
        })


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
