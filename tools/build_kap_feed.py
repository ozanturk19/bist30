#!/usr/bin/env python3
"""D-45: KAP akis deposunu elle doldurur / tazeler (VPS'te DEV1; normalde bist30-macro'daki
kap-feed dongusu bunu kendisi yapar). app.py import EDILMEZ (arka plan is parcaciklari baslamasin).

Kullanim:
  python3 tools/build_kap_feed.py --months 12          # 12 ay + bu ay geri besleme (ODA+FR+DG, ay basina 3 istek)
  python3 tools/build_kap_feed.py --poll               # tek artimli tur (dun+bugun, 4 sinif) + yeni metinler
  python3 tools/build_kap_feed.py --docs 40            # metni olmayan son 90 gunun rutin-disi kayitlari
  python3 tools/build_kap_feed.py --stats              # depo ozeti (ag yok)
Evren: last_cache.json (sitenin analiz evreni) x data/universe.json (KAP uye kimligi, mkk).
Nezaket: istekler arasi >= 2 sn; KAP 429/5xx -> temiz durus, cikis 2 (ayni komutla devam).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_feed  # noqa: E402


def universe():
    with open(os.path.join(ROOT, "last_cache.json"), encoding="utf-8") as f:
        stocks = json.load(f)
    with open(os.path.join(ROOT, "data", "universe.json"), encoding="utf-8") as f:
        comp = json.load(f)["companies"]
    tickers = sorted(s["ticker"] for s in stocks if s.get("ticker") and s["ticker"] not in ("XU030", "XU100"))
    names = {s["ticker"]: s.get("name") or s["ticker"] for s in stocks if s.get("ticker")}
    oids = sorted(set(comp[t]["mkk"] for t in tickers if (comp.get(t) or {}).get("mkk")))
    missing = [t for t in tickers if not (comp.get(t) or {}).get("mkk")]
    return set(tickers), oids, names, missing


def tcmb(day, cur, _cache={}):
    import requests
    d0 = datetime.strptime(day, "%Y-%m-%d").date()
    for back in range(6):
        d = d0 - timedelta(days=back)
        k = d.isoformat()
        if k not in _cache:
            r = requests.get(kap_feed.TCMB_URL % (d.strftime("%Y%m"), d.strftime("%d%m%Y")), timeout=15)
            _cache[k] = kap_feed.parse_tcmb(r.text) if r.status_code == 200 else {}
        if _cache[k].get(cur):
            return _cache[k][cur], k
    return None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=0)
    ap.add_argument("--poll", action="store_true")
    ap.add_argument("--docs", type=int, default=0)
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--base", default=None, help="depo klasoru (varsayilan data/kap_feed)")
    a = ap.parse_args(argv)
    store = kap_feed.Store(a.base)
    if a.stats:
        items = store.all_items()
        print("kayit=%d rutin=%d metinli=%d onemli=%d" % (
            len(items), sum(1 for x in items if x.get("rutin")), sum(1 for x in items if x.get("doc")),
            sum(1 for x in items if x.get("onem"))))
        print("gun (son 5):", Counter(x["ts"][:10] for x in items).most_common(5))
        print("meta:", store.meta())
        return 0
    uni, oids, names, missing = universe()
    print("evren=%d hisse, %d KAP kimligi; kimliksiz: %s" % (len(uni), len(oids), " ".join(missing) or "-"))
    client = kap_feed.KapClient()
    try:
        if a.months:
            n = kap_feed.backfill_months(store, client, oids, uni, months=a.months)
            print("  geri besleme: %d kayit, %d istek, aylar: %s" % (n, client.count, store.meta().get("backfilled")))
        if a.poll:
            st = kap_feed.poll_once(store, client, oids, uni, names, max_docs=15, fx_getter=tcmb)
            print("  tur:", st)
        if a.docs:
            n = kap_feed.backfill_docs(store, client, names, limit=a.docs, days=90, fx_getter=tcmb)
            print("  metin geri besleme: %d (istek=%d)" % (n, client.count))
    except kap_feed.KapStop as e:
        print("DURDU: %s -- ayni komutla devam edin" % e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
