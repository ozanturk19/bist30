#!/usr/bin/env python3
"""D-17 paralel koşu ölçümü: eski last_macro.json ile yeni last_macro.new.json etiket etiket.

  python3 -m pipeline.compare_macro [--log /var/log/bp-intraday-compare.log]
Çıktı satırı: <utc> <etiket> eski=<p> yeni=<p> dprice%=<x> dchange_pp=<y>
Kabul (plan D-17): 24 saatte etiket başına |dprice%| ≤ 0,05 (medyan) — iki dosyanın ts farkı
(≤3 dk) yüzünden tek örnek sapabilir, karar medyanla verilir.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def diff_rows(old, new):
    o = {i["label"]: i for i in (old.get("data") or [])}
    n = {i["label"]: i for i in (new.get("data") or [])}
    rows = []
    for label in sorted(set(o) | set(n)):
        a, b = o.get(label), n.get(label)
        if not a or not b:
            rows.append((label, a and a["price"], b and b["price"], None, None))
            continue
        dp = (b["price"] - a["price"]) / a["price"] * 100 if a["price"] else None
        rows.append((label, a["price"], b["price"],
                     None if dp is None else round(dp, 4), round(b["change"] - a["change"], 2)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=os.path.join(_ROOT, "last_macro.json"))
    ap.add_argument("--new", default=os.path.join(_ROOT, "last_macro.new.json"))
    ap.add_argument("--log")
    args = ap.parse_args(argv)
    with open(args.old) as f:
        old = json.load(f)
    with open(args.new) as f:
        new = json.load(f)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = ["%s %s eski=%s yeni=%s dprice%%=%s dchange_pp=%s" % ((now,) + r) for r in diff_rows(old, new)]
    text = "\n".join(lines) + "\n"
    if args.log:
        with open(args.log, "a") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
