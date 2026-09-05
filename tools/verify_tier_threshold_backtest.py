"""
CPO out-of-box test (05.09.2026): "Guclu Sinyal / Standart" tier esiklerinin
(signal_strength >= 70 / >= 56, app.py _derive_tier) backtest performansiyla
ne kadar orantili oldugunu olcen bagimsiz offline script.

Onemli baglam (app.py _derive_tier docstring'inden, CPO-DEV2-053/055 22.08):
esikler backtest'ten degil, 54 aktif CANLI sinyalin skor DAGILIMINDAKI DOGAL
BOSLUKLARDAN kalibre edilmis ve o zamanki CPO tarafindan onaylanmis. Yani bu
script'in amaci "esikler yanlis" demek DEGIL -- dagilim-tabanli kalibrasyonun
performans-tabanli bir ayrima da denk gelip gelmedigini kontrol etmek.

Metodoloji (basitlestirme, acikca belirtiliyor): compose_score() (app.py:1490)
her AL/SAT episode'unun GIRIS barinda hesaplanir (ADX/vol_ratio/RSI o barda),
"confirmed" (signal_bars>=3) HER episode icin True varsayilir -- gerçek
kullanici sadece confirmed sinyal gorur, bu script confirmed-oncesi/sonrasi
ayrimini modellemiyor (bilinen sinirlama, tools/verify_premium_badge_backtest.py
ile ayni ruhta).

vol_ratio (compose_score'un Hacim bileseni) = son gun hacmi / 20-gunluk ort.
hacim -- bu, Premium/rvol rozetinin kullandigi v5/v20 formulunden FARKLI bir
metriktir (ayri bir alan, app.py'de rvol adiyla ayri hesaplaniyor).

Calistirma: python3 verify_tier_threshold_backtest.py
(offline, salt-okunur, sadece yfinance okur)

Son doğrulama (05.09.2026, BIST30, 2y günlük veri, KOZAA/KOZAL delisted, 28/30 hisse,
AL+SAT birlikte, n=401 episode):
    guclu_sinyal (>=70): n=29   win=37.9%  sharpe=0.36
    standart     (56-69): n=176  win=40.3%  sharpe=0.61
    rozetsiz     (<56):   n=196  win=24.5%  sharpe=-3.66
    Baseline (tümü):      n=401  win=32.4%  sharpe=-1.56

Bulgu: alt sınır (56) net bir ayrım yaratıyor (rozetsiz belirgin şekilde daha kötü,
beklenen), AMA "guclu_sinyal" (üst tier) backtest'te "standart"tan DAHA İYİ değil,
her iki metrikte de hafifçe daha kötü — iki bandın kendi arasındaki üst-eşik (70)
performans farkını yansıtmıyor gibi görünüyor. Küçük n (29) ve bilinen metodoloji
sınırları (confirmed=True basitleştirmesi, SL/TP simüle etmeyen motor, sadece
BIST30 alt-kümesi) yüzünden KESİN bir "üst eşik bozuk" sonucu DEĞİL — ama alt
sınırın (56) tuttuğu, üst sınırın (70) şu haliyle ayrıştırıcı olmadığı, gelecekte
daha büyük örneklemle (BIST100) tekrar bakılmaya değer bir sinyal.

Son doğrulama #2 (05.09.2026, TAM BIST100, 2y günlük veri, AL+SAT, n=2994 episode
— Ozan: "tüm hisseleri kontrol et aynı gözle"):
    guclu_sinyal (>=70): n=334   win=37.7%  sharpe=1.87
    standart     (56-69): n=1454  win=35.6%  sharpe=2.43
    rozetsiz     (<56):   n=1206  win=31.7%  sharpe=-0.18
    Baseline (tümü):      n=2994  win=34.2%  sharpe=2.6

Büyük örneklem BIST30 bulgusunu DOĞRULADI: alt sınır (56) hâlâ net (rozetsiz
belirgin şekilde daha kötü hem win-rate hem Sharpe'ta). Üst sınır (70) bu kez
win-rate'te hafif öne geçti (37.7% vs 35.6%) AMA Sharpe'ta hâlâ standart'ın
GERİSİNDE (1.87 vs 2.43) — karışık sinyal, "guclu_sinyal her açıdan daha iyi"
iddiasını desteklemiyor. n=2994 ile artık istatistiksel gürültü ihtimali düşük,
bu gerçek bir desen gibi görünüyor.
"""
import sys, os, time
sys.path.insert(0, "/root/bist30")
import warnings
warnings.filterwarnings("ignore")
import yfinance as yf
import pandas as pd
from indicators import compute_ema, compute_adx, compute_supertrend, compute_rsi

# app.py:774 BIST100 listesinin birebir kopyası (05.09 genişletme, Ozan: "tüm
# hisseleri kontrol et aynı gözle") — app.py'yi import ETMİYORUZ (bg-thread/
# Flask side-effect riski, bkz. verify_premium_badge_backtest.py aynı disiplin),
# XU030 (endeks, hisse değil) hariç tutuldu.
BIST100 = [
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO",
    "EREGL", "FROTO", "GARAN", "HEKTS", "ISCTR",
    "KCHOL", "KRDMD", "MGROS", "ODAS", "OYAKC",
    "PGSUS", "SAHOL", "SASA", "SISE", "SOKM",
    "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO",
    "TUPRS", "VAKBN", "YKBNK",
    "AEFES", "AGHOL", "AKSA",  "AKSEN", "ALARK",
    "ALBRK", "ALFAS", "ALGYO", "ALKIM",
    "ANHYT", "ANSGR", "ASUZU", "BJKAS", "BRSAN",
    "BRYAT", "BUCIM", "CCOLA", "CIMSA", "CWENE",
    "DOAS",  "DOHOL", "EGEEN", "ENJSA", "ENKAI",
    "EUPWR", "FENER", "GENIL", "GLYHO", "GUBRF",
    "HALKB", "INDES", "ISDMR", "ISGYO",
    "ISMEN", "IZMDC", "JANTS", "KARTN", "KCAER",
    "KLNMA", "KONTR", "KORDS",
    "LOGO",  "MAVI",  "NETAS", "NTHOL",
    "OTKAR", "PARSN", "PETKM", "PRKAB", "RYSAS",
    "SARKY", "SELEC", "SMRTG", "TATGD", "TTKOM",
    "TTRAK", "TURSG", "ULKER", "VESBE", "VESTL",
    "YATAS", "ZOREN",
    "ADEL",  "ADESE", "AKMGY", "AKGRT", "ARSAN",
    "AYCES", "BIOEN", "BOSSA", "CEMTS",
    "CEMAS", "CLEBI", "CRDFA", "DENGE", "DNISI",
    "DOGUB", "DURDO", "DYOBY", "ECILC",
    "EDIP",  "EGGUB", "EGPRO", "EMKEL", "ERBOS",
    "ERSU",  "ESCOM", "FMIZP", "FORMT", "GESAN",
    "GSDHO", "GSRAY", "GOKNR", "HDFGS", "HLGYO",
    "HTTBT", "IEYHO", "ISKPL", "ISFIN",
    "KAPLM", "KATMR", "KMPUR", "KONYA",
    "KRSTL", "LKMNH", "LUKSK", "MAKTK", "MPARK",
    "MEDTR", "MEGAP", "MTRKS",
    "NATEN", "NIBAS", "NUHCM", "ORGE",
    "ASTOR", "PEKGY", "PASEU", "MIATK", "CANTE",
    "KLRHO", "PSGYO", "QUAGR", "IZENR", "EUREN",
    "ALKLC", "YEOTK", "BINHO", "FZLGY", "SKBNK",
    "MAGEN", "SURGY", "ESEN", "REEDR", "ALTNY",
    "ENERY", "BTCIM", "SDTTR", "BURCE", "TUKAS",
    "MARTI", "FONET", "AGROT", "MRGYO", "TUREX",
    "LILAK", "TCKRC", "PENGD", "PAPIL", "AYGAZ",
    "TSKB", "FORTE", "AKFYE", "TEKTU", "LMKDC",
    "ECZYT", "ARENA", "USAK", "MARKA", "BERA",
    "LINK", "MERCN", "ARDYZ", "KZBGY", "GMTAS",
    "AHGAZ",
    "KAREL", "ARZUM", "AKCNS", "MERKO", "KARSN",
    "POLHO", "TABGD", "GENTS", "ANELE", "HATSN",
    "SMART", "PKART", "AYEN", "EDATA", "TMSN",
    "AYDEM", "SNGYO", "YESIL", "LRSHO", "DERHL",
]


def _bar_signal_fast(ema12, ema99, adx, di_plus, di_minus, supertrend, i):
    ei12 = float(ema12.iloc[i]); ei99 = float(ema99.iloc[i])
    ai = float(adx.iloc[i])
    dip = float(di_plus.iloc[i]); dim = float(di_minus.iloc[i])
    sti = int(supertrend.iloc[i])
    bs = int(sti == 1) + int(ai >= 25 and dip > dim) + int(ei12 > ei99)
    brs = int(sti == -1) + int(ai >= 25 and dim > dip) + int(ei12 < ei99)
    return "AL" if bs >= 3 else "SAT" if brs >= 3 else "BEKLE"


def compose_score(adx, vol_ratio, rsi, signal, confirmed=True):
    """app.py:1490 compose_score() ile birebir ayni formul."""
    import math
    def _finite(v, default):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return default
        return v if math.isfinite(v) else default
    s = 0.0
    s += min(_finite(adx, 0), 50) / 50 * 30
    s += min(_finite(vol_ratio, 1.0), 5) / 5 * 25
    s += 10 if confirmed else 0
    rsi = _finite(rsi, 50)
    if signal == "SAT":
        if 25 <= rsi <= 50: s += 10
        elif rsi < 25: s += 5
    else:
        if 50 <= rsi <= 75: s += 10
        elif rsi > 75: s += 5
    return int(round(s * 100 / 75))


def tier_of(score):
    if score >= 70: return "guclu_sinyal"
    if score >= 56: return "standart"
    return "rozetsiz"


def backtest_ticker(ticker, fwd_days=20):
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
        rsi_series = compute_rsi(close, 14)
        vol_avg20 = volume.rolling(20).mean()
        signals = [_bar_signal_fast(ema12, ema99, adx, di_plus, di_minus, supertrend, i) for i in range(n)]

        episodes = []
        i = 0
        while i < n:
            sig = signals[i]
            if sig in ("AL", "SAT"):
                entry_i = i
                entry_price = float(close.iloc[i])
                if entry_price <= 0 or entry_i < 20:
                    i += 1
                    continue
                va = float(vol_avg20.iloc[entry_i])
                vol_ratio = float(volume.iloc[entry_i]) / va if va > 0 else 1.0
                adx_i = float(adx.iloc[entry_i])
                rsi_i = float(rsi_series.iloc[entry_i])
                score = compose_score(adx_i, vol_ratio, rsi_i, sig, confirmed=True)
                j = i + 1
                while j < n and j < i + fwd_days + 1 and signals[j] == sig:
                    j += 1
                exit_i = min(j, n - 1)
                exit_price = float(close.iloc[exit_i])
                ret_pct = (exit_price - entry_price) / entry_price * 100
                episodes.append({
                    "sig": sig, "score": score, "tier": tier_of(score), "ret_pct": ret_pct,
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
    if not eps:
        return {"count": 0, "win_rate": None, "sharpe": None}
    wins = sum(1 for e in eps if e["win"])
    rets = [_signed_ret(e) for e in eps]
    avg = sum(rets) / len(rets)
    std = (sum((r - avg) ** 2 for r in rets) / len(rets)) ** 0.5
    sharpe = round(avg / std * (len(rets) ** 0.5), 2) if std > 0 else None
    return {"count": len(eps), "win_rate": round(100 * wins / len(eps), 1), "sharpe": sharpe}


def main():
    all_eps = []
    for t in BIST100:
        eps = backtest_ticker(t)
        time.sleep(0.3)
        if eps:
            all_eps += eps
        print(f"  {t}: {'ok (' + str(len(eps)) + ' episodes)' if eps else 'FAILED'}", file=sys.stderr)

    print("\n=== Tier esigi (70/56) backtest performans korelasyonu — AL+SAT, BIST100, 2y ===")
    print("(confirmed=True varsayimi, vol_ratio=gunluk/20g-ort, methodoloji notlari script basinda)\n")
    for tier in ["guclu_sinyal", "standart", "rozetsiz"]:
        bucket = [e for e in all_eps if e["tier"] == tier]
        print(f"{tier:15s}:", sharpe_stats(bucket))
    print("\nBaseline (tumu):  ", sharpe_stats(all_eps))

    scores = sorted(set(e["score"] for e in all_eps))
    print(f"\nSkor dagilimi ozet: min={min(scores) if scores else None} max={max(scores) if scores else None} n_unique={len(scores)}")


if __name__ == "__main__":
    main()
