"""
BIST30 Backtest & Strateji Analizi
Mevcut sinyal motoru + alternatif stratejiler karşılaştırması
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─── BIST30 Hisseleri ──────────────────────────────────────────────────────────
BIST30 = [
    "AKBNK","ARCLK","ASELS","BIMAS","EKGYO","ENKAI","EREGL","FROTO",
    "GARAN","HALKB","ISCTR","KCHOL","KOZAA","KOZAL","KRDMD","MGROS",
    "OYAKC","PETKM","PGSUS","SAHOL","SASA","SISE","TAVHL","TCELL",
    "THYAO","TKFEN","TOASO","TTKOM","TUPRS","VAKBN"
]

# ─── İndikatör Hesapları ────────────────────────────────────────────────────────
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def compute_supertrend(high, low, close, period=10, mult=3.0):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    hl2 = (high + low) / 2
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr

    st = pd.Series(np.nan, index=close.index)
    direction = pd.Series(0, index=close.index)
    final_upper = upper.copy()
    final_lower = lower.copy()

    for i in range(1, len(close)):
        fu_prev = final_upper.iloc[i-1]
        fl_prev = final_lower.iloc[i-1]
        c = close.iloc[i]
        cp = close.iloc[i-1]

        fu = upper.iloc[i]
        fl = lower.iloc[i]

        final_upper.iloc[i] = fu if fu < fu_prev or cp > fu_prev else fu_prev
        final_lower.iloc[i] = fl if fl > fl_prev or cp < fl_prev else fl_prev

        if direction.iloc[i-1] == -1:
            direction.iloc[i] = 1 if c > final_upper.iloc[i] else -1
        else:
            direction.iloc[i] = -1 if c < final_lower.iloc[i] else 1

        st.iloc[i] = final_lower.iloc[i] if direction.iloc[i] == 1 else final_upper.iloc[i]

    return direction  # +1 = bull, -1 = bear

def compute_adx(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()

    up = high.diff()
    dn = -low.diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)

    plus_dm = pd.Series(plus_dm, index=high.index).ewm(span=period, adjust=False).mean()
    minus_dm = pd.Series(minus_dm, index=high.index).ewm(span=period, adjust=False).mean()

    plus_di = 100 * plus_dm / atr
    minus_di = 100 * minus_dm / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx, plus_di, minus_di

def compute_macd(close, fast=12, slow=26, signal=9):
    e_fast = close.ewm(span=fast, adjust=False).mean()
    e_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = e_fast - e_slow
    sig_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, sig_line

# ─── Strateji Tanımları ─────────────────────────────────────────────────────────

def build_signals(df, strategy="current"):
    """
    Returns Series of signals: 1=AL, -1=SAT, 0=BEKLE
    """
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    e12  = ema(close, 12)
    e26  = ema(close, 26)
    e50  = ema(close, 50)
    e99  = ema(close, 99)
    e200 = ema(close, 200)

    st_dir = compute_supertrend(high, low, close, 10, 3.0)
    adx, plus_di, minus_di = compute_adx(high, low, close, 14)
    macd_line, _ = compute_macd(close)

    signals = pd.Series(0, index=close.index)
    n = len(close)

    for i in range(200, n):
        c   = close.iloc[i]
        e12i= e12.iloc[i];  e12p = e12.iloc[i-1]
        e26i= e26.iloc[i]
        e50i= e50.iloc[i]
        e99i= e99.iloc[i];  e99p = e99.iloc[i-1]
        e200i=e200.iloc[i]
        sti = st_dir.iloc[i]
        ai  = adx.iloc[i]
        dip = plus_di.iloc[i]; dim = minus_di.iloc[i]
        mi  = macd_line.iloc[i]; mp = macd_line.iloc[i-1]

        if strategy == "current":
            # Mevcut: EMA50/200 + EMA12/99 cross(2)/pos(1) + ST + ADX≥30 + MACD  →  threshold 4
            cross_bull = (e12p < e99p) and (e12i > e99i)
            cross_bear = (e12p > e99p) and (e12i < e99i)
            pos_bull   = (not cross_bull) and (e12i > e99i)
            pos_bear   = (not cross_bear) and (e12i < e99i)

            bs = (int(e50i > e200i)
                  + (2 if cross_bull else int(pos_bull))
                  + int(sti == 1)
                  + int(ai >= 30 and dip > dim)
                  + int(mi > 0 and mi > mp))

            brs = (int(e50i < e200i)
                   + (2 if cross_bear else int(pos_bear))
                   + int(sti == -1)
                   + int(ai >= 30 and dim > dip)
                   + int(mi < 0 and mi < mp))

            if bs >= 4:   signals.iloc[i] = 1
            elif brs >= 4: signals.iloc[i] = -1

        elif strategy == "ema_cross_only":
            # Basit EMA50/200 golden/death cross
            prev_bull = e50.iloc[i-1] > e200.iloc[i-1]
            curr_bull = e50i > e200i
            if not prev_bull and curr_bull: signals.iloc[i] = 1
            elif prev_bull and not curr_bull: signals.iloc[i] = -1

        elif strategy == "supertrend_only":
            # Sadece Supertrend yön değişimi
            prev_st = st_dir.iloc[i-1]
            if prev_st != 1 and sti == 1:   signals.iloc[i] = 1
            elif prev_st != -1 and sti == -1: signals.iloc[i] = -1

        elif strategy == "triple_ema":
            # EMA12 > EMA26 > EMA50 hepsi aynı yönde
            if e12i > e26i > e50i: signals.iloc[i] = 1
            elif e12i < e26i < e50i: signals.iloc[i] = -1

        elif strategy == "adx_trend":
            # ADX≥25 + DI+/DI- yönü (trend sürekliliği)
            prev = signals.iloc[i-1]
            if ai >= 25 and dip > dim: signals.iloc[i] = 1
            elif ai >= 25 and dim > dip: signals.iloc[i] = -1
            else: signals.iloc[i] = prev  # ADX düşükse pozisyonu koru

        elif strategy == "st_adx":
            # Supertrend + ADX≥25
            if sti == 1 and ai >= 25 and dip > dim:  signals.iloc[i] = 1
            elif sti == -1 and ai >= 25 and dim > dip: signals.iloc[i] = -1

        elif strategy == "high_conviction":
            # Güçlü trend: EMA50/200 + ST + ADX≥30 + EMA12/99 pozisyon  →  threshold 4/5
            pos_bull = e12i > e99i
            pos_bear = e12i < e99i
            bs = (int(e50i > e200i) + int(pos_bull) + int(sti == 1)
                  + int(ai >= 30 and dip > dim) + int(mi > 0))
            brs = (int(e50i < e200i) + int(pos_bear) + int(sti == -1)
                   + int(ai >= 30 and dim > dip) + int(mi < 0))
            if bs >= 4:   signals.iloc[i] = 1
            elif brs >= 4: signals.iloc[i] = -1

        elif strategy == "weekly_regime":
            # Haftalık EMA trend tespiti: sadece 20-günlük ort. yönünde işlem
            e20 = ema(close, 20)
            weekly_bull = e20.iloc[i] > e20.iloc[i-5]  # 5 gün öncesiyle kıyasla
            pos_bull = e12i > e99i
            pos_bear = e12i < e99i
            cross_bull2 = (e12p < e99p) and (e12i > e99i)
            cross_bear2 = (e12p > e99p) and (e12i < e99i)
            bs = (int(e50i > e200i)
                  + (2 if cross_bull2 else int(pos_bull))
                  + int(sti == 1) + int(ai >= 30 and dip > dim)
                  + int(mi > 0 and mi > mp))
            brs = (int(e50i < e200i)
                   + (2 if cross_bear2 else int(pos_bear))
                   + int(sti == -1) + int(ai >= 30 and dim > dip)
                   + int(mi < 0 and mi < mp))
            if bs >= 4 and weekly_bull:    signals.iloc[i] = 1
            elif brs >= 4 and not weekly_bull: signals.iloc[i] = -1

    return signals


def apply_3bar_confirm(signals):
    """3 bar onayı: aynı yön 3 bar üst üste gelince sinyal ver"""
    confirmed = pd.Series(0, index=signals.index)
    bar_count = 0
    current_dir = 0
    for i in range(len(signals)):
        s = signals.iloc[i]
        if s == current_dir and s != 0:
            bar_count += 1
        elif s != 0:
            current_dir = s
            bar_count = 1
        else:
            bar_count = 0
            current_dir = 0
        if bar_count >= 3:
            confirmed.iloc[i] = current_dir
    return confirmed


# ─── Backtest Motoru ────────────────────────────────────────────────────────────

def backtest(close, raw_signals, use_confirm=False, stop_pct=None, trail_pct=None):
    """
    Simple long/short backtest.
    Returns: trades list, equity curve
    """
    if use_confirm:
        signals = apply_3bar_confirm(raw_signals)
    else:
        signals = raw_signals

    trades = []
    equity = [1.0]
    position = 0   # 0=yok, 1=long, -1=short
    entry_price = None
    entry_idx = None
    peak_price = None

    prices = close.values
    sig_vals = signals.values
    dates = close.index

    for i in range(1, len(prices)):
        price = prices[i]
        sig   = sig_vals[i]

        # Stop-loss / trailing stop
        if position != 0 and entry_price is not None:
            if position == 1:
                if stop_pct and price < entry_price * (1 - stop_pct):
                    sig = -1  # zorla kapat
                if trail_pct:
                    peak_price = max(peak_price, price)
                    if price < peak_price * (1 - trail_pct):
                        sig = -1
            else:
                if stop_pct and price > entry_price * (1 + stop_pct):
                    sig = 1
                if trail_pct:
                    peak_price = min(peak_price, price)
                    if price > peak_price * (1 + trail_pct):
                        sig = 1

        # Pozisyon değişimi
        if sig != 0 and sig != position:
            if position != 0:
                # Kapat
                ret = (price - entry_price) / entry_price * position
                trades.append({
                    "entry_date": dates[entry_idx],
                    "exit_date": dates[i],
                    "direction": "AL" if position == 1 else "SAT",
                    "entry": entry_price,
                    "exit": price,
                    "ret": ret,
                    "bars": i - entry_idx
                })
                equity.append(equity[-1] * (1 + ret))
                position = 0

            if sig in (1, -1):
                position = sig
                entry_price = price
                peak_price = price
                entry_idx = i

        else:
            equity.append(equity[-1])

    # Açık pozisyonu kapat
    if position != 0 and entry_idx is not None:
        price = prices[-1]
        ret = (price - entry_price) / entry_price * position
        trades.append({
            "entry_date": dates[entry_idx],
            "exit_date": dates[-1],
            "direction": "AL" if position == 1 else "SAT",
            "entry": entry_price,
            "exit": price,
            "ret": ret,
            "bars": len(prices) - 1 - entry_idx
        })
        equity.append(equity[-1] * (1 + ret))

    return trades, equity


def calc_stats(trades, equity):
    if not trades:
        return {}
    rets = [t["ret"] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]

    total_return = equity[-1] - 1.0
    n = len(rets)
    win_rate = len(wins) / n * 100 if n else 0
    avg_win  = np.mean(wins) * 100 if wins else 0
    avg_loss = np.mean(losses) * 100 if losses else 0

    # Max drawdown
    eq_arr = np.array(equity)
    peak = np.maximum.accumulate(eq_arr)
    dd = (eq_arr - peak) / peak
    max_dd = dd.min() * 100

    # Sharpe (basit, risk-free=0)
    eq_rets = np.diff(eq_arr) / eq_arr[:-1]
    sharpe = (eq_rets.mean() / eq_rets.std() * np.sqrt(252)) if eq_rets.std() > 0 else 0

    avg_bars = np.mean([t["bars"] for t in trades])
    profit_factor = (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else np.inf

    return {
        "n_trades": n,
        "win_rate": win_rate,
        "total_return_pct": total_return * 100,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "max_drawdown_pct": max_dd,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
        "avg_bars": avg_bars,
    }


# ─── Ana Çalıştırıcı ────────────────────────────────────────────────────────────

STRATEGIES = [
    ("Mevcut (5kr, thr=4)",           "current",        False, None,  None),
    ("Mevcut + 3-bar onay",           "current",        True,  None,  None),
    ("Mevcut + %8 stop",              "current",        False, 0.08,  None),
    ("Mevcut + %12 trailing",         "current",        False, None,  0.12),
    ("Mevcut + 3-bar + %10 trail",    "current",        True,  None,  0.10),
    ("EMA Golden/Death Cross",        "ema_cross_only", False, None,  None),
    ("Supertrend Flip",               "supertrend_only",False, None,  None),
    ("Triple EMA (12>26>50)",         "triple_ema",     False, None,  None),
    ("ADX≥25 Trend",                  "adx_trend",      False, None,  None),
    ("Supertrend + ADX≥25",           "st_adx",         False, None,  None),
    ("Yüksek Konviksiyon (5/5)",      "high_conviction",False, None,  None),
    ("Weekly Regime Gate",            "weekly_regime",  False, None,  None),
    ("Weekly Regime + %12 trail",     "weekly_regime",  False, None,  0.12),
]

def run_all():
    print("=" * 80)
    print(f"BIST30 BACKTEST RAPORU — {datetime.today().strftime('%Y-%m-%d')}")
    print("Dönem: 3 yıl günlük veri | Long+Short | Komisyon yok")
    print("=" * 80)

    all_results = {name: [] for name, *_ in STRATEGIES}
    per_stock_best = {}

    ticker_data = {}
    print(f"\n[1/3] Veri indiriliyor ({len(BIST30)} hisse × 3 yıl)...")

    for base in BIST30:
        ticker = base + ".IS"
        try:
            df = yf.download(ticker, period="3y", interval="1d",
                             auto_adjust=True, progress=False)
            if df is None or len(df) < 250:
                continue
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            ticker_data[base] = df
        except Exception as e:
            print(f"  {base}: hata — {e}")

    print(f"  {len(ticker_data)} hisse yüklendi.\n")
    print("[2/3] Backtest çalışıyor...\n")

    # Her hisse için her strateji
    for base, df in ticker_data.items():
        close = df["Close"].dropna()
        high  = df["High"].dropna()
        low   = df["Low"].dropna()
        df2   = df.loc[close.index]

        stock_results = {}
        for name, strat, confirm, stop, trail in STRATEGIES:
            try:
                raw_sig = build_signals(df2, strat)
                trades, equity = backtest(close, raw_sig, confirm, stop, trail)
                stats = calc_stats(trades, equity)
                if stats:
                    all_results[name].append(stats)
                    stock_results[name] = stats
            except Exception as e:
                pass

        # En iyi strateji bu hisse için
        best_name = None; best_ret = -999
        for name, st in stock_results.items():
            if st.get("total_return_pct", -999) > best_ret:
                best_ret = st["total_return_pct"]
                best_name = name
        if best_name:
            per_stock_best[base] = (best_name, best_ret)

    # ─── RAPOR ──────────────────────────────────────────────────────────────────
    print("[3/3] Sonuçlar\n")
    print("=" * 80)
    print("STRATEJİ KARŞILAŞTIRMASI (Tüm BIST30 ortalaması)")
    print("=" * 80)

    header = f"{'Strateji':<35} {'İşlem':>6} {'Kazanma%':>9} {'Toplam%':>9} {'MaxDD%':>8} {'Sharpe':>7} {'PF':>6}"
    print(header)
    print("-" * 80)

    ranked = []
    for name, strat, *_ in STRATEGIES:
        data = all_results[name]
        if not data:
            continue
        avg = {k: np.mean([d[k] for d in data if k in d]) for k in data[0]}
        ranked.append((name, avg))

    ranked.sort(key=lambda x: x[1].get("sharpe", 0), reverse=True)

    for name, avg in ranked:
        pf_str = f"{avg['profit_factor']:.2f}" if avg['profit_factor'] < 50 else "∞"
        print(f"{name:<35} {avg['n_trades']:>6.0f} {avg['win_rate']:>9.1f} "
              f"{avg['total_return_pct']:>9.1f} {avg['max_drawdown_pct']:>8.1f} "
              f"{avg['sharpe']:>7.2f} {pf_str:>6}")

    print()
    print("=" * 80)
    print("HİSSE BAZLI EN İYİ STRATEJİ (Toplam getiriye göre)")
    print("=" * 80)
    print(f"{'Hisse':<10} {'En İyi Strateji':<35} {'Getiri%':>9}")
    print("-" * 60)

    for base in sorted(per_stock_best, key=lambda x: per_stock_best[x][1], reverse=True):
        name, ret = per_stock_best[base]
        print(f"{base:<10} {name:<35} {ret:>9.1f}")

    print()
    print("=" * 80)
    print("STRATEJİ DETAYLARI (En yüksek Sharpe'a göre ilk 5)")
    print("=" * 80)

    for name, avg in ranked[:5]:
        print(f"\n▶ {name}")
        print(f"   İşlem sayısı:    {avg['n_trades']:.0f}")
        print(f"   Kazanma oranı:   %{avg['win_rate']:.1f}")
        print(f"   Ort. kazanan:    %{avg['avg_win_pct']:.1f}")
        print(f"   Ort. kaybeden:   %{avg['avg_loss_pct']:.1f}")
        print(f"   Maks. drawdown:  %{avg['max_drawdown_pct']:.1f}")
        print(f"   Sharpe ratio:    {avg['sharpe']:.2f}")
        pf = avg['profit_factor']
        print(f"   Profit factor:   {pf:.2f}" if pf < 50 else f"   Profit factor:   ∞")
        print(f"   Ort. tutuş (bar):{avg['avg_bars']:.0f}")
        print(f"   3Y toplam getiri:%{avg['total_return_pct']:.1f}")

    print()
    print("=" * 80)
    print("MEVCUT STRATEJİ ANALİZİ")
    print("=" * 80)

    current_data = all_results["Mevcut (5kr, thr=4)"]
    if current_data:
        pos_returns = [d for d in current_data if d['total_return_pct'] > 0]
        neg_returns = [d for d in current_data if d['total_return_pct'] <= 0]
        print(f"Karlı hisse sayısı:     {len(pos_returns)}/{len(current_data)}")
        print(f"Zarar eden hisse:       {len(neg_returns)}/{len(current_data)}")
        print(f"Ortalama işlem/hisse:   {np.mean([d['n_trades'] for d in current_data]):.0f}")
        print(f"En yüksek getiri:       %{max(d['total_return_pct'] for d in current_data):.1f}")
        print(f"En düşük getiri:        %{min(d['total_return_pct'] for d in current_data):.1f}")

    print()
    print("=" * 80)
    print("ÖZET ÖNERİLER")
    print("=" * 80)

    best_name_overall = ranked[0][0] if ranked else "—"
    best_avg = ranked[0][1] if ranked else {}

    print(f"""
En yüksek Sharpe stratejisi: {best_name_overall}
  → Sharpe: {best_avg.get('sharpe', 0):.2f}
  → Ortalama 3Y getiri: %{best_avg.get('total_return_pct', 0):.1f}
  → Kazanma oranı: %{best_avg.get('win_rate', 0):.1f}
  → Max drawdown: %{best_avg.get('max_drawdown_pct', 0):.1f}

Öneriler:
  1. Trailing stop, max drawdown'ı önemli ölçüde azaltır.
  2. 3-bar onay, whipsaw işlem sayısını düşürür ama gecikme ekler.
  3. ADX≥25 filtresi, range (yatay) piyasada işlem yapmayı engeller.
  4. Supertrend + ADX kombinasyonu trend yakalamada güçlüdür.
  5. EMA golden/death cross sinyaller az ama güçlü trendleri yakalar.
""")

    print("=" * 80)
    print("Backtest tamamlandı.")


if __name__ == "__main__":
    run_all()
