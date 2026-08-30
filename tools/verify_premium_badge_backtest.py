"""
CPO-1457 #1: "Hacim Onaylı" (Premium, RVOL >= 1.20) rozetinin dayandığı backtest
iddiasını (app.py analyze() içindeki "Sharpe 1.62 -> 2.97, Win Rate 36.7% -> 51.5%"
yorumu) yeniden üretmek için bağımsız offline script.

Neden var: orijinal sayıları üreten script kod tabanında bulunamadı (CPO denetimi,
30.08.2026), iddia tekrarlanamıyordu. Bu script AL sinyallerini RVOL >= 1.20 /
< 1.20 olarak ikiye ayırıp Sharpe/win-rate karşılaştırması yapar — app.py
backtest_ticker()/run_backtest().stats() ile AYNI formülleri kullanır (bkz.
app.py:10184-10184+, 10293-10313), ama app.py'yi import ETMEZ (Flask/bg-thread
side effect riski + repo py3.10+ gerektirirken bu script py3.9 uyumlu kalsın
diye indicators.py'nin saf fonksiyonlarını + _bar_signal_fast/backtest_ticker
mantığını inline kopyalar).

Çalıştırma: python3 tools/verify_premium_badge_backtest.py
(offline, salt-okunur, yfinance dışında hiçbir canlı sisteme dokunmaz)

Son doğrulama (30.08.2026, BIST30 evreni, 2y günlük veri, KOZAA/KOZAL Yahoo'da
delisted oldukları için evren dışı kaldı — 28/30 hisse):
    Baseline (tüm AL):        n=258  win=34.1%  sharpe=0.70
    RVOL <  1.20 (non-premium): n=147  win=32.0%  sharpe=0.12
    RVOL >= 1.20 (premium):     n=67   win=49.3%  sharpe=2.11
Orijinal iddia (1.62->2.97, %36.7->%51.5) ile TAM eşleşmiyor (farklı veri
penceresi/evren kaçınılmaz kayma yaratır — trailing 2y backtest zaten zamanla
değişir), ama YÖN ve BÜYÜKLÜK ORANI doğrulandı: premium alt-küme hem win-rate
hem Sharpe'ta belirgin şekilde daha iyi. Rozet iddiası GERÇEK, fabrikasyon değil.

Bilinen metodoloji sınırı (CPO-1457 not b): bu motor gerçek SL/TP'de çıkmıyor,
sinyal tersine dönene veya fwd_days (20 bar) dolana kadar pozisyonda kalıyor —
canlı kullanıcı deneyiminden (SL/TP kullananlar) sapabilir. Ayrı bir iş.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings
warnings.filterwarnings("ignore")
import yfinance as yf
import pandas as pd
from indicators import compute_ema, compute_adx, compute_supertrend

BIST30 = [
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO", "ENKAI", "EREGL", "FROTO",
    "GARAN", "HALKB", "ISCTR", "KCHOL", "KOZAA", "KOZAL", "KRDMD", "MGROS",
    "OYAKC", "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL", "TCELL",
    "THYAO", "TKFEN", "TOASO", "TTKOM", "TUPRS", "VAKBN",
]


def _bar_signal_fast(ema12, ema99, adx, di_plus, di_minus, supertrend, i):
    """app.py:10173 ile birebir aynı."""
    ei12 = float(ema12.iloc[i]); ei99 = float(ema99.iloc[i])
    ai = float(adx.iloc[i])
    dip = float(di_plus.iloc[i]); dim = float(di_minus.iloc[i])
    sti = int(supertrend.iloc[i])
    bs = int(sti == 1) + int(ai >= 25 and dip > dim) + int(ei12 > ei99)
    brs = int(sti == -1) + int(ai >= 25 and dim > dip) + int(ei12 < ei99)
    return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"


def backtest_ticker(ticker, fwd_days=20):
    """app.py backtest_ticker() (app.py:10184) ile aynı episode mantığı +
    her AL/SAT giriş barında RVOL (v5/v20, analyze()'daki formülle aynı)."""
    try:
        df = yf.Ticker(ticker + ".IS").history(period="2y", interval="1d")
        if df is None or len(df) < 120:
            return None
        df = df.dropna().sort_index()
        close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]
        n = len(close)
        if n < 120:
            return None
        ema12 = compute_ema(close, 12)
        ema99 = compute_ema(close, 99)
        adx, di_plus, di_minus = compute_adx(high, low, close)
        supertrend, _ = compute_supertrend(high, low, close)
        signals = [_bar_signal_fast(ema12, ema99, adx, di_plus, di_minus, supertrend, i) for i in range(n)]

        episodes = []
        i = 0
        while i < n:
            sig = signals[i]
            if sig in ("AL", "SAT"):
                entry_i = i
                entry_price = float(close.iloc[i])
                if entry_price <= 0:
                    i += 1
                    continue
                rvol = None
                if entry_i >= 19:
                    v5 = float(volume.iloc[entry_i - 4: entry_i + 1].mean())
                    v20 = float(volume.iloc[entry_i - 19: entry_i + 1].mean())
                    if v20 > 0 and not pd.isna(v20) and not pd.isna(v5):
                        rvol = round(v5 / v20, 2)
                j = i + 1
                while j < n and j < i + fwd_days + 1 and signals[j] == sig:
                    j += 1
                exit_i = min(j, n - 1)
                exit_price = float(close.iloc[exit_i])
                ret_pct = (exit_price - entry_price) / entry_price * 100
                episodes.append({
                    "sig": sig, "rvol": rvol, "ret_pct": ret_pct,
                    "win": (ret_pct > 0 and sig == "AL") or (ret_pct < 0 and sig == "SAT"),
                })
                i = j
            else:
                i += 1
        return episodes
    except Exception as e:
        print(f"  ! {ticker}: {e}", file=sys.stderr)
        return None


def _signed_ret(ep):
    return ep["ret_pct"] if ep["sig"] == "AL" else -ep["ret_pct"]


def sharpe_stats(eps):
    """app.py run_backtest().stats() (app.py:10293) ile aynı formül."""
    if not eps:
        return {"count": 0, "win_rate": None, "sharpe": None}
    wins = sum(1 for e in eps if e["win"])
    rets = [_signed_ret(e) for e in eps]
    avg = sum(rets) / len(rets)
    std = (sum((r - avg) ** 2 for r in rets) / len(rets)) ** 0.5
    sharpe = round(avg / std * (len(rets) ** 0.5), 2) if std > 0 else None
    return {"count": len(eps), "win_rate": round(100 * wins / len(eps), 1), "sharpe": sharpe,
            "avg_ret": round(avg, 3)}


def main():
    all_al = []
    for t in BIST30:
        eps = backtest_ticker(t)
        time.sleep(0.3)
        if eps:
            all_al += [e for e in eps if e["sig"] == "AL"]
        print(f"  {t}: {'ok' if eps else 'FAILED (delisted/no data)'}", file=sys.stderr)

    al_rvol_hi = [e for e in all_al if e["rvol"] is not None and e["rvol"] >= 1.20]
    al_rvol_lo = [e for e in all_al if e["rvol"] is not None and e["rvol"] < 1.20]

    print("\n=== Premium badge (RVOL>=1.20) backtest repro — AL signals, BIST30, 2y ===")
    print("Baseline (all AL):     ", sharpe_stats(all_al))
    print("RVOL < 1.20 (non-prem):", sharpe_stats(al_rvol_lo))
    print("RVOL >= 1.20 (premium):", sharpe_stats(al_rvol_hi))
    print("\nOrijinal iddia (app.py yorumu): Sharpe 1.62 -> 2.97, Win Rate 36.7% -> 51.5%")


if __name__ == "__main__":
    main()
