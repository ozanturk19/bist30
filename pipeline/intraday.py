#!/usr/bin/env python3
"""D-17 / A1 — makro şerit + RSS zamanlayıcı işi (app.py'yi import ETMEZ).

Eski yol: bist30-macro (macro_worker.py → app import → _macro_bg_loop, 10 alt süreç).
Yeni yol: bp-intraday.timer her dakika bu betiği çalıştırır; `gate` seans içinde
(hafta içi 09:55-18:15 TR) her dakika, dışında 5 dakikada bir izin verir. Tek
`yf.download` (10 sembol, günlük bar: son bar = anlık fiyat, bir önceki = önceki
kapanış) → `last_macro.json` şemasıyla atomik yazım. Saatte bir RSS →
`last_macro_news.json`.

Kullanım (WorkingDirectory=/root/bist30):
  python3 -m pipeline.intraday                      # kapıdan geçerse yaz (timer)
  python3 -m pipeline.intraday --force --out /tmp/x.json   # kapısız, başka dosyaya
  python3 -m pipeline.intraday --news-only          # yalnız RSS
Geri alma: systemctl disable --now bp-intraday.timer && systemctl enable --now bist30-macro
"""
import argparse
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("bp-intraday")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACRO_PATH = os.path.join(_ROOT, "last_macro.json")
NEWS_PATH = os.path.join(_ROOT, "last_macro_news.json")
PREV_PATH = os.path.join(_ROOT, "last_macro_prev.json")

_TZ_TR = timezone(timedelta(hours=3))

# (etiket, Yahoo sembolü) — tek kaynak; app.py buradan okur (D-49: PETROL = Brent).
MACRO_TICKERS = [
    ("XU100", "XU100.IS"),
    ("XU030", "XU030.IS"),
    ("USDTRY", "USDTRY=X"),
    ("EURTRY", "EURTRY=X"),
    ("BTC", "BTC-USD"),
    ("ALTIN", "GC=F"),
    ("GUMUS", "SI=F"),
    ("PETROL", "BZ=F"),
    ("SP500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
]

MACRO_RSS_SOURCES = [
    ("Reuters TR", "https://tr.reuters.com/rssFeed/businessNews"),
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),
    ("Dünya", "https://www.dunya.com/rss/ekonomi.xml"),
    ("Haberler.com", "https://www.haberler.com/ekonomi/rss/"),
    ("AA Ekonomi", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
]

# 7/24 semboller: Yahoo günlük barının "önceki barı" fast_info.previous_close'tan farklı
# (BTC +0,48 ↔ +0,18; USDTRY +0,13 ↔ +0,08). Eski yolla aynı `change` için önceki kapanış
# fast_info'dan alınır, saatte bir yenilenir (günde ≤72 çağrı).
PREV_FASTINFO = ("USDTRY=X", "EURTRY=X", "BTC-USD")
_PREV_TTL_S = 3600

_BIST_DELAY_MIN = 15  # Yahoo'da BIST (.IS) verisi 15 dk gecikmeli (C-54 dürüstlük notu)
_MIN_ITEMS = 5        # bundan az sembol gelirse yazılmaz (kısmi Yahoo hatası eski dosyayı ezmesin)


def should_run(now_utc, force=False):
    """Kapı: hafta içi 09:55-18:15 TR her dakika; diğer zamanlar yalnız dakika % 5 == 0."""
    if force:
        return True
    tr = now_utc.astimezone(_TZ_TR)
    hm = tr.hour * 60 + tr.minute
    if tr.weekday() < 5 and 9 * 60 + 55 <= hm <= 18 * 60 + 15:
        return True
    return tr.minute % 5 == 0


def news_due(now_utc):
    """RSS saatte bir: TR saatinin 0. dakikası."""
    return now_utc.astimezone(_TZ_TR).minute == 0


def build_items(closes_by_sym, tickers=MACRO_TICKERS, prev_override=None):
    """{sembol: Close serisi (NaN'siz, eskiden yeniye)} → last_macro.json `data` listesi.

    price = son bar, change = (son / önceki kapanış − 1) × 100 (D-49: günlük bar tabanı;
    `prev_override` verilen sembollerde önceki kapanış oradan). Önceki kapanış yoksa
    (bar < 2 ve override yok) ya da fiyat ≤ 0 ise sembol atlanır.
    """
    prev_override = prev_override or {}
    items = []
    for label, sym in tickers:
        closes = closes_by_sym.get(sym)
        if closes is None or len(closes) < 1:
            continue
        price = float(closes.iloc[-1])
        prev = prev_override.get(sym)
        if not prev:
            if len(closes) < 2:
                continue
            prev = float(closes.iloc[-2])
        prev = float(prev)
        if not (price > 0 and prev > 0):
            continue
        items.append({
            "label": label,
            "price": round(price, 2),
            "change": round((price - prev) / prev * 100, 2),
            "source_delay_min": _BIST_DELAY_MIN if sym.endswith(".IS") else 0,
        })
    return items


def fetch_closes(tickers=MACRO_TICKERS, downloader=None):
    """Tek toplu Yahoo çağrısı → {sembol: Close serisi}. `downloader` testte sahtelenir."""
    if downloader is None:
        import yfinance as yf

        def downloader(syms):
            return yf.download(syms, period="7d", interval="1d", group_by="ticker",
                               auto_adjust=False, progress=False, threads=True, timeout=20)
    syms = [s for _, s in tickers]
    df = downloader(syms)
    out = {}
    if df is None or getattr(df, "empty", True):
        return out
    for sym in syms:
        try:
            out[sym] = df[sym]["Close"].dropna()
        except Exception:
            continue
    return out


def load_prev(path, now=None, fetcher=None):
    """7/24 sembollerin önceki kapanışı: dosya <1 sa ise oradan, değilse fast_info'dan yenile."""
    now = time.time() if now is None else now
    try:
        with open(path) as f:
            d = json.load(f)
        if now - d.get("ts", 0) < _PREV_TTL_S and d.get("prev"):
            return d["prev"]
    except Exception:
        d = {}
    if fetcher is None:
        def fetcher(sym):
            import yfinance as yf
            return yf.Ticker(sym).fast_info.previous_close
    prev = {}
    for sym in PREV_FASTINFO:
        try:
            v = fetcher(sym)
            if v and float(v) > 0:
                prev[sym] = float(v)
        except Exception as e:
            logger.debug("prev_close %s: %s", sym, e)
    for sym, v in (d.get("prev") or {}).items():   # yenileme kısmen düştüyse eski değer kalır
        prev.setdefault(sym, v)
    if prev:
        atomic_write_json(path, {"prev": prev, "ts": now})
    return prev


def is_valid(items):
    """_guards._is_valid_macro ile aynı sözleşme: XU030 var, USDTRY sayısal."""
    try:
        from _guards import _is_valid_macro
    except Exception:  # _guards yoksa (yalıtılmış test) eşdeğer kural
        kv = {i["label"]: i.get("price") for i in items}
        return ("XU030" in kv and isinstance(kv["XU030"], (int, float))
                and isinstance(kv.get("USDTRY", 0), (int, float))), "inline"
    return _is_valid_macro({i["label"]: i.get("price") for i in items})


def atomic_write_json(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".intraday-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def fetch_rss_once(sources=MACRO_RSS_SOURCES, parse=None):
    """Kaynak başına ≤6 girdi, son 24 saat, yayın zamanına göre ilk 20 (eski app davranışı)."""
    if parse is None:
        import feedparser
        parse = feedparser.parse
    results = []
    cutoff = datetime.now() - timedelta(hours=24)
    for source_name, url in sources:
        try:
            feed = parse(url)
            for entry in (feed.entries or [])[:6]:
                try:
                    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                    pub = datetime(*parsed[:6]) if parsed else datetime.now()
                    if pub < cutoff:
                        continue
                    title = (entry.get("title") or "").strip()
                    link = (entry.get("link") or "").strip()
                    if not title:
                        continue
                    pub_tr = pub.replace(tzinfo=timezone.utc).astimezone(_TZ_TR)
                    results.append({
                        "title": title, "url": link, "source": source_name,
                        "published": pub_tr.strftime("%H:%M"),
                        "date_str": pub_tr.strftime("%d.%m"),
                        "pub_ts": pub.timestamp(),
                        "category": "makro",
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug("RSS fetch [%s]: %s", source_name, e)
    results.sort(key=lambda x: x.get("pub_ts", 0), reverse=True)
    return results[:20]


def run_macro(out_path, downloader=None, now=None, prev_path=PREV_PATH, prev_fetcher=None):
    """Makro dosyasını yazar. Dönüş: (yazıldı_mı, mesaj). Başarısızlıkta eski dosya korunur."""
    closes = fetch_closes(downloader=downloader)
    prev = load_prev(prev_path, now=now, fetcher=prev_fetcher) if closes else {}
    items = build_items(closes, prev_override=prev)
    if len(items) < _MIN_ITEMS:
        return False, "yetersiz sembol (%d < %d)" % (len(items), _MIN_ITEMS)
    ok, reason = is_valid(items)
    if not ok:
        return False, "geçersiz: %s" % reason
    atomic_write_json(out_path, {"data": items, "ts": now if now is not None else time.time()})
    return True, "%d sembol" % len(items)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="zaman kapısını yok say")
    ap.add_argument("--out", default=MACRO_PATH)
    ap.add_argument("--news-out", default=NEWS_PATH)
    ap.add_argument("--prev-path", default=PREV_PATH)
    ap.add_argument("--news-only", action="store_true")
    ap.add_argument("--no-news", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    now = datetime.now(timezone.utc)
    if not should_run(now, args.force):
        return 0
    rc = 0
    if not args.news_only:
        t0 = time.time()
        ok, msg = run_macro(args.out, prev_path=args.prev_path)
        logger.info("macro %s: %s (%.1f sn)", "OK" if ok else "ATLANDI", msg, time.time() - t0)
        rc = 0 if ok else 1
    if args.news_only or (not args.no_news and news_due(now)):
        try:
            news = fetch_rss_once()
            if news:
                atomic_write_json(args.news_out, {"items": news, "ts": time.time()})
            logger.info("news: %d girdi", len(news))
        except Exception as e:
            logger.warning("news hata: %s", e)
    return rc


if __name__ == "__main__":
    sys.exit(main())
