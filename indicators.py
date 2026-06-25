"""Technical indicator pure functions — extracted from app.py Bölüm 3."""
import numpy as np
import pandas as pd


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


def compute_rsi(close, period=14):
    """RSI (Relative Strength Index) — EWM yöntemi."""
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_atr(high, low, close, period=14):
    """ATR(14) — Wilder smoothing. Bağımsız helper; giriş optimizasyonu için kullanılır."""
    hi = high.values; lo = low.values; cl = close.values
    n  = len(cl)
    tr      = np.empty(n)
    tr[0]   = hi[0] - lo[0]
    tr[1:]  = np.maximum(hi[1:] - lo[1:],
              np.maximum(np.abs(hi[1:] - cl[:-1]),
                         np.abs(lo[1:] - cl[:-1])))
    atr = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return pd.Series(atr, index=close.index)


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
