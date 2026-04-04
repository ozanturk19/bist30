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

# ── Logging ──────────────────────────────────────────────────────────────────
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
_live_prices = {}          # {ticker: {price, change_pct, updated}}
_lock        = threading.Lock()
_sse_clients = []          # aktif SSE bağlantıları için event listesi
_sse_lock    = threading.Lock()


def _push_sse(payload: dict):
    """Tüm SSE istemcilerine mesaj gönder. deque.append thread-safe (O(1))."""
    msg = f"data: {json.dumps(payload)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.append(msg)          # deque.append — atomik, O(1)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


def compute_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return histogram


def compute_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, lower


def compute_supertrend(high, low, close, period=10, multiplier=3):
    """ATR 10, çarpan 3 — skill referansıyla eşleşiyor."""
    hl2 = (high + low) / 2
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low  - close.shift(1)).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
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

    supertrend = pd.Series(1, index=close.index, dtype=int)
    for i in range(1, len(close)):
        prev = supertrend.iloc[i - 1]
        if prev == 1:
            supertrend.iloc[i] = 1 if close.iloc[i] >= final_lower.iloc[i] else -1
        else:
            supertrend.iloc[i] = -1 if close.iloc[i] <= final_upper.iloc[i] else 1

    return supertrend


def compute_adx(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    atr = tr.ewm(com=period - 1, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(com=period - 1, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(com=period - 1, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(com=period - 1, adjust=False).mean()
    return adx, plus_di, minus_di


def compute_obv(close, volume):
    """On-Balance Volume — hacim yönünü takip eder."""
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (direction * volume).cumsum()


def _weekly_trend(ticker: str) -> int:
    """Haftalık EMA20 yönünü döner: +1 yükselen, -1 düşen, 0 belirsiz.
    Hata durumunda 0 (gate bypass) döner."""
    try:
        wdf = yf.download(ticker, period="1y", interval="1wk",
                          progress=False, auto_adjust=True, timeout=20)
        if wdf is None or len(wdf) < 25:
            return 0
        if isinstance(wdf.columns, pd.MultiIndex):
            wdf.columns = wdf.columns.get_level_values(0)
            wdf = wdf.loc[:, ~wdf.columns.duplicated()]
        wdf = wdf.dropna()
        wclose = wdf["Close"].squeeze()
        wema20 = compute_ema(wclose, 20)
        if len(wema20) < 2:
            return 0
        # Son iki haftalık EMA20 değeri yükseliyorsa +1, düşüyorsa -1
        return 1 if float(wema20.iloc[-1]) > float(wema20.iloc[-2]) else -1
    except Exception:
        return 0   # hata → gate bypass


def analyze(ticker_base):
    ticker = ticker_base + ".IS" if ticker_base != "XU030" else "XU030.IS"

    try:
        # Haftalık trend gate — büyük trend yönünü belirler
        weekly_dir = _weekly_trend(ticker)  # +1 / -1 / 0

        # 2 yıllık veri → EMA99, Supertrend vb. için yeterli warmup
        df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True, timeout=30)
        if df is None or len(df) < 120:
            return None

        # MultiIndex'i düzleştir
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]

        df    = df.dropna()
        close  = df["Close"].squeeze()
        high   = df["High"].squeeze()
        low    = df["Low"].squeeze()
        volume = df["Volume"].squeeze() if "Volume" in df.columns else pd.Series(0, index=df.index)

        ema20  = compute_ema(close, 20)
        ema50  = compute_ema(close, 50)
        ema200 = compute_ema(close, 200)
        ema12  = compute_ema(close, 12)
        ema99  = compute_ema(close, 99)
        rsi       = compute_rsi(close)
        macd_hist = compute_macd(close)
        bb_upper, bb_lower = compute_bollinger(close)
        adx, di_plus, di_minus = compute_adx(high, low, close)
        supertrend = compute_supertrend(high, low, close)
        obv        = compute_obv(close, volume)

        def v(s):  return float(s.iloc[-1])
        def v2(s): return float(s.iloc[-2])

        c    = v(close)
        e20  = v(ema20);  e50 = v(ema50);  e200 = v(ema200)
        e12  = v(ema12);  e99 = v(ema99)
        e12p = v2(ema12); e99p = v2(ema99)
        rsi_val   = v(rsi)
        macd_val  = v(macd_hist);  macd_prev = v2(macd_hist)
        bbu       = v(bb_upper);   bbl       = v(bb_lower)
        bb_mid    = (bbu + bbl) / 2
        adx_val   = v(adx)
        di_p      = v(di_plus);    di_m      = v(di_minus)
        st_val    = v(supertrend)   # +1 = bullish, -1 = bearish
        obv_val   = v(obv);        obv_prev  = v2(obv)

        prev_c     = v2(close) if len(close) > 1 else c
        change_pct = ((c - prev_c) / prev_c) * 100 if prev_c != 0 else 0

        # ── Sinyal koşulları ──────────────────────────────────
        # 1) EMA 50/200 hizası — uzun vadeli trend doğrulaması
        ema_bull  = e50 > e200
        ema_bear  = e50 < e200

        # 2) EMA 12/99 crossover (2pt) veya pozisyon (1pt)
        e12_cross_bull = (e12p < e99p) and (e12 > e99)
        e12_cross_bear = (e12p > e99p) and (e12 < e99)
        e12_pos_bull   = (not e12_cross_bull) and (e12 > e99)
        e12_pos_bear   = (not e12_cross_bear) and (e12 < e99)

        # 3) Supertrend yönü
        st_bull   = st_val == 1
        st_bear   = st_val == -1

        # 4) ADX ≥ 30 + DI yönü (eşik 25→30: güçlü trend filtresi)
        adx_bull  = adx_val >= 30 and di_p > di_m
        adx_bear  = adx_val >= 30 and di_m > di_p

        # 5) MACD sıfır çizgisi geçişi veya momentum devamı
        macd_bull = macd_val > 0 and macd_val > macd_prev
        macd_bear = macd_val < 0 and macd_val < macd_prev

        # ── Puanlama: max 7 (crossover 2pt dahil), eşik 4 ────
        bull_score = (
            int(ema_bull) +
            (2 if e12_cross_bull else int(e12_pos_bull)) +
            int(st_bull) + int(adx_bull) + int(macd_bull)
        )
        bear_score = (
            int(ema_bear) +
            (2 if e12_cross_bear else int(e12_pos_bear)) +
            int(st_bear) + int(adx_bear) + int(macd_bear)
        )

        # ── Haftalık gate: büyük trend ters yönde ise AL/SAT üretme ──
        # weekly_dir == 0 → belirsiz / hata → gate bypass (sinyal üret)
        if bull_score >= 4 and weekly_dir != -1:
            signal = "AL"
        elif bear_score >= 4 and weekly_dir != 1:
            signal = "SAT"
        else:
            signal = "BEKLE"

        # EMA12/99 durumu için label
        if e12_cross_bull:   e12_label = "EMA12↑99"
        elif e12_cross_bear: e12_label = "EMA12↓99"
        elif e12 > e99:      e12_label = f"12>{e99:.0f}"
        else:                e12_label = f"12<{e99:.0f}"

        # ── Sinyal tarihi: geçmiş bar sinyallerini kontrol et ───────────────
        # Yeni motorla birebir aynı mantık (5 kriter, eşik 4, weekly gate yok)
        def bar_signal(i):
            ei50  = float(ema50.iloc[i]);   ei200 = float(ema200.iloc[i])
            ei12  = float(ema12.iloc[i]);   ei99  = float(ema99.iloc[i])
            mi    = float(macd_hist.iloc[i])
            mp    = float(macd_hist.iloc[i-1]) if i > 0 else mi
            ai    = float(adx.iloc[i])
            dip_i = float(di_plus.iloc[i]);  dim_i = float(di_minus.iloc[i])
            sti   = int(supertrend.iloc[i])
            e12p_ = float(ema12.iloc[i-1]) if i > 0 else ei12
            e99p_ = float(ema99.iloc[i-1]) if i > 0 else ei99
            ecb   = (e12p_ < e99p_) and (ei12 > ei99)
            ecbr  = (e12p_ > e99p_) and (ei12 < ei99)
            ep_b  = (not ecb)  and (ei12 > ei99)
            ep_br = (not ecbr) and (ei12 < ei99)
            bs  = (int(ei50 > ei200) + (2 if ecb  else int(ep_b)) +
                   int(sti == 1)    + int(ai >= 30 and dip_i > dim_i) +
                   int(mi > 0 and mi > mp))
            brs = (int(ei50 < ei200) + (2 if ecbr else int(ep_br)) +
                   int(sti == -1)   + int(ai >= 30 and dim_i > dip_i) +
                   int(mi < 0 and mi < mp))
            return "AL" if bs >= 4 else "SAT" if brs >= 4 else "BEKLE"

        today_str = datetime.now().strftime("%d.%m.%Y")
        signal_date = today_str   # default: bugün
        signal_bars = 1           # kaç bar boyunca bu sinyal devam ediyor
        try:
            n = len(close)
            for i in range(n-2, max(n-120, 0), -1):
                if bar_signal(i) != signal:
                    signal_date = close.index[i+1].strftime("%d.%m.%Y")
                    signal_bars = (n - 1) - (i + 1) + 1   # kaç bar geçti
                    break
            else:
                signal_date = close.index[max(n-120, 0)].strftime("%d.%m.%Y")
                signal_bars = n - max(n-120, 0)
        except Exception:
            pass

        is_new_signal = (signal_date == today_str)
        # 3 bar konfirmasyon: sinyal en az 3 gün boyunca tutarlıysa onaylı
        confirmed = signal != "BEKLE" and signal_bars >= 3

        return {
            "ticker":        ticker_base,
            "price":         round(c, 2),
            "change_pct":    round(change_pct, 2),
            "signal":        signal,
            "signal_date":   signal_date,
            "signal_bars":   signal_bars,
            "is_new_signal": is_new_signal,
            "confirmed":     confirmed,    # 3+ bar boyunca aynı sinyal
            "bull_score":    bull_score,
            "bear_score":    bear_score,
            "weekly_trend":  weekly_dir,   # +1 yükselen / -1 düşen / 0 belirsiz
            "indicators": {
                "ema5200": {
                    "label": "EMA50/200",
                    "value": f"{e50:.0f}/{e200:.0f}",
                    "bull": ema_bull,   "bear": ema_bear,
                },
                "ema1299": {
                    "label": e12_label,
                    "value": f"{e12:.0f}/{e99:.0f}",
                    "bull": e12_cross_bull or e12_pos_bull,
                    "bear": e12_cross_bear or e12_pos_bear,
                    "cross": e12_cross_bull or e12_cross_bear,
                },
                "supertrend": {
                    "label": "ST",
                    "value": "LONG" if st_bull else "SHORT",
                    "bull": st_bull,   "bear": st_bear,
                },
                "adx": {
                    "label": f"ADX {adx_val:.0f}",
                    "value": f"DI+{di_p:.0f}/DI-{di_m:.0f}",
                    "bull": adx_bull,  "bear": adx_bear,
                },
                "macd": {
                    "label": "MACD",
                    "value": f"{macd_val:.2f}",
                    "bull": macd_bull, "bear": macd_bear,
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
        0 if x.get("is_new_signal") else 1,                               # bugün sinyal verenler önce
        0 if x["signal"] == "AL" else 1 if x["signal"] == "SAT" else 2,  # AL > SAT > BEKLE
        -x["bull_score"] if x["signal"] == "AL" else -x["bear_score"]
    ))

    with _lock:
        _cache["data"] = results
        _cache["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def fetch_live_prices():
    """Tek API çağrısıyla tüm BIST30 canlı fiyatlarını çek ve SSE ile yayınla."""
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
                # group_by="ticker" → Level 0: ticker, Level 1: price
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

                price  = float(closes.iloc[-1])
                prev   = float(closes.iloc[-2])
                chg    = ((price - prev) / prev * 100) if prev else 0

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
    """Her 15 saniyede bir canlı fiyat çek."""
    while True:
        fetch_live_prices()
        time.sleep(30)


def background_refresh():
    while True:
        refresh_chart()
        refresh_data()
        time.sleep(900)  # 15 dakikada bir indikatörleri güncelle


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    with _lock:
        return jsonify({
            "stocks": _cache["data"],
            "updated_at": _cache["updated_at"],
            "loading": len(_cache["data"]) == 0
        })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=refresh_data, daemon=True).start()
    return jsonify({"status": "refreshing"})


@app.route("/api/stream")
def api_stream():
    """SSE endpoint — canlı fiyatları iter."""
    client_queue = collections.deque()   # thread-safe, O(1) append/popleft
    with _sse_lock:
        _sse_clients.append(client_queue)

    # Bağlanır bağlanmaz mevcut fiyatları hemen gönder
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
                    yield client_queue.popleft()   # O(1), thread-safe
                time.sleep(0.5)
        finally:
            with _sse_lock:
                if client_queue in _sse_clients:
                    _sse_clients.remove(client_queue)

    response = Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":      "keep-alive",
        },
    )
    return response


def _safe_float(val):
    """Scalar veya 1-elemanlı Series/ndarray'den float al."""
    if hasattr(val, "iloc"):
        return float(val.iloc[0])
    if hasattr(val, "item"):
        return float(val.item())
    return float(val)


def get_chart_data():
    """
    5 yıllık veri çek → indikatörleri TÜM veri üzerinde hesapla (warmup için)
    → grafikte yalnızca son DISPLAY_BARS barı göster.
    Böylece EMA99, Supertrend vb. ilk bardan itibaren doğru değerde başlar.
    """
    DISPLAY_BARS = 500   # ~2 yıl
    WARMUP_MIN   = 200   # en az bu kadar warmup barı

    try:
        # yf.Ticker().history() kullan → bağımsız session,
        # eşzamanlı yf.download() çağrılarıyla veri çakışması olmaz.
        df = yf.Ticker("XU030.IS").history(period="5y", interval="1d", auto_adjust=True)

        if df is None or len(df) < WARMUP_MIN + 50:
            return None

        # history() her zaman flat sütun (Open/High/Low/Close) döner
        df    = df[["Open", "High", "Low", "Close"]].dropna()
        close = df["Close"]
        high  = df["High"]
        low   = df["Low"]
        open_ = df["Open"]

        # ── İndikatörleri FULL veri üzerinde hesapla ─────
        ema20      = compute_ema(close, 20)
        ema50      = compute_ema(close, 50)
        ema200     = compute_ema(close, 200)
        ema12      = compute_ema(close, 12)
        ema99      = compute_ema(close, 99)
        rsi        = compute_rsi(close)
        bbu, bbl   = compute_bollinger(close)
        adx, di_plus_s, di_minus_s = compute_adx(high, low, close)
        supertrend = compute_supertrend(high, low, close)
        volume_s   = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)
        obv_s      = compute_obv(close, volume_s)

        macd_fast  = compute_ema(close, 12)
        macd_slow  = compute_ema(close, 26)
        macd_line  = macd_fast - macd_slow
        sig_line   = compute_ema(macd_line, 9)
        macd_hist  = macd_line - sig_line

        # ── Gösterim için son DISPLAY_BARS barı kes ───────
        show_idx  = df.index[-DISPLAY_BARS:]
        show_set  = set(show_idx.strftime("%Y-%m-%d"))

        def series(s):
            out = []
            for ts, val in s.items():
                if pd.isna(val): continue
                d = ts.strftime("%Y-%m-%d")
                if d not in show_set: continue
                out.append({"time": d, "value": round(float(val), 4)})
            return out

        # OHLC — güvenli scalar erişim
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

        # MACD renkli histogram
        macd_colored = []
        for ts, val in macd_hist.items():
            if pd.isna(val): continue
            d = ts.strftime("%Y-%m-%d")
            if d not in show_set: continue
            v = float(val)
            macd_colored.append({
                "time":  d,
                "value": round(v, 2),
                "color": "#3fb950" if v >= 0 else "#f85149",
            })

        # ── Son bar değerleri (sinyal) ────────────────────
        c        = float(close.iloc[-1])
        prev_c   = float(close.iloc[-2])
        chg      = ((c - prev_c) / prev_c) * 100 if prev_c else 0
        rsi_val  = float(rsi.iloc[-1])
        adx_val  = float(adx.iloc[-1])
        di_p     = float(di_plus_s.iloc[-1]);  di_m = float(di_minus_s.iloc[-1])
        macd_val = float(macd_hist.iloc[-1])
        macd_prv = float(macd_hist.iloc[-2])
        e20_val  = float(ema20.iloc[-1]);  e50_val = float(ema50.iloc[-1])
        e200_val = float(ema200.iloc[-1])
        e12_val  = float(ema12.iloc[-1])
        e99_val  = float(ema99.iloc[-1])
        e12_prv  = float(ema12.iloc[-2])
        e99_prv  = float(ema99.iloc[-2])
        bbu_v    = float(bbu.iloc[-1]);    bbl_v  = float(bbl.iloc[-1])
        bb_mid_v = (bbu_v + bbl_v) / 2
        st_val   = int(supertrend.iloc[-1])
        obv_val  = float(obv_s.iloc[-1]);  obv_prv = float(obv_s.iloc[-2])
        vol_today = float(volume_s.iloc[-1])
        vol_avg20 = float(volume_s.iloc[-20:].mean()) if len(volume_s) >= 20 else 1
        vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 1.0

        # ── Sinyal koşulları (analyze() ile aynı mantık) ─
        ema_bull       = e20_val > e50_val > e200_val
        ema_bear       = e20_val < e50_val < e200_val
        e12_cross_bull = (e12_prv < e99_prv) and (e12_val > e99_val)
        e12_cross_bear = (e12_prv > e99_prv) and (e12_val < e99_val)
        e12_pos_bull   = (not e12_cross_bull) and (e12_val > e99_val)
        e12_pos_bear   = (not e12_cross_bear) and (e12_val < e99_val)
        bb_bull        = c > bb_mid_v
        bb_bear        = c < bb_mid_v
        macd_bull      = macd_val > 0 and macd_val > macd_prv
        macd_bear      = macd_val < 0 and macd_val < macd_prv
        rsi_bull       = 50 <= rsi_val <= 75
        rsi_bear       = 25 <= rsi_val <= 50
        adx_bull       = adx_val > 25 and di_p > di_m
        adx_bear       = adx_val > 25 and di_m > di_p
        st_bull        = st_val == 1
        st_bear        = st_val == -1
        vol_bull       = vol_ratio > 1.5 and c > prev_c
        vol_bear       = vol_ratio > 1.5 and c < prev_c
        obv_bull       = obv_val > obv_prv
        obv_bear       = obv_val < obv_prv

        bull_score = (
            int(ema_bull) +
            (2 if e12_cross_bull else int(e12_pos_bull)) +
            int(bb_bull) + int(macd_bull) + int(rsi_bull) +
            int(adx_bull) + int(st_bull) + int(vol_bull) + int(obv_bull)
        )
        bear_score = (
            int(ema_bear) +
            (2 if e12_cross_bear else int(e12_pos_bear)) +
            int(bb_bear) + int(macd_bear) + int(rsi_bear) +
            int(adx_bear) + int(st_bear) + int(vol_bear) + int(obv_bear)
        )
        signal = "AL" if bull_score >= 5 else "SAT" if bear_score >= 5 else "BEKLE"

        return {
            "ohlc":     ohlc,
            "ema12":    series(ema12),
            "ema99":    series(ema99),
            "bb_upper": series(bbu),
            "bb_lower": series(bbl),
            "macd":     macd_colored,
            "rsi":      series(rsi),
            "adx":      series(adx),
            "summary": {
                "price":          round(c, 2),
                "change_pct":     round(chg, 2),
                "signal":         signal,
                "bull_score":     bull_score,
                "bear_score":     bear_score,
                "rsi":            round(rsi_val, 1),
                "adx":            round(adx_val, 1),
                "macd":           round(macd_val, 2),
                "e12":            round(e12_val, 1),
                "e99":            round(e99_val, 1),
                "ema_bull":       ema_bull,
                "ema_bear":       ema_bear,
                "ema_cross_bull": e12_cross_bull,
                "ema_cross_bear": e12_cross_bear,
                "bb_bull":        bb_bull,   "bb_bear":   bb_bear,
                "macd_bull":      macd_bull, "macd_bear": macd_bear,
                "rsi_bull":       rsi_bull,  "rsi_bear":  rsi_bear,
                "adx_bull":       adx_bull,  "adx_bear":  adx_bear,
                "st_bull":        st_bull,   "st_bear":   st_bear,
                "vol_bull":       vol_bull,  "vol_bear":  vol_bear,
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




# ── Arka plan thread'leri ─────────────────────────────────────────────────────
# background_refresh / background_live_prices zaten ilk iterasyonlarında
# refresh_data / fetch_live_prices çağırıyor; ayrıca direkt çağırmaya gerek yok.
# refresh_chart() diğer yf.download() çağrılarından önce tamamlanmalı (race condition).
def _startup():
    # 1) Grafik verisini çek (bağımsız Ticker.history() session'ı)
    refresh_chart()
    # 2) 3 saniye bekle, sonra sinyal + fiyat döngülerini başlat
    time.sleep(3)
    threading.Thread(target=background_refresh,     daemon=True).start()
    threading.Thread(target=background_live_prices, daemon=True).start()

threading.Thread(target=_startup, daemon=True).start()

logger.info("=" * 50)
logger.info("  BIST30 Sinyal Paneli başlatıldı")
logger.info("  http://localhost:8003 adresini aç")
logger.info("  SSE canlı fiyat: /api/stream")
logger.info("=" * 50)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003, debug=False)
