"""D-P1-2210-6: "Ozet Bilgi" basligi olmayan sayfalarda (Finansal Rapor turu) eski
parse_detail() start=0'a dusup sayfa basi arama widget'ini + CSS iskelet metnini
govde saniyordu. Fix sonrasi bu kayitlarin onbellegi (data/kap_feed/docs/<id>.json)
hala eski (kirli) govdeyi tasir -- bu betik KAP'tan yeniden ceker ve guncel
parse_detail() ile yeniden yazar.

Varsayilan kuru kosu (yalnuz etkilenen id'leri listeler). `--apply` ile KAP'a tek
istemciyle (>= 2 sn araliklarla) yeniden istek atar ve doc'u Store.save_doc ile yazar.

Kullanim: python3 tools/kap_govde_reparse.py [--apply]
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_feed as kf  # noqa: E402

_JUNK_MARKERS = ("css-", "Bugün Gelen Bildirimler", "{position")


def _is_dirty(doc):
    text = doc.get("text") or ""
    blob = text + " ".join(doc.get("lines") or []) + " ".join(" ".join(f) for f in doc.get("fields") or [])
    return any(m in blob for m in _JUNK_MARKERS)


def _affected_ids(store):
    out = []
    try:
        names = os.listdir(store.docs_dir)
    except OSError:
        return out
    for name in sorted(names):
        if not name.endswith(".json"):
            continue
        idx = int(name[:-5])
        doc = store.doc(idx)
        if doc and _is_dirty(doc):
            out.append(idx)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    store = kf.Store()
    ids = _affected_ids(store)
    print("etkilenen kayit: %d" % len(ids))
    for idx in ids:
        print(" -", idx)
    if not args.apply or not ids:
        return

    client = kf.KapClient()
    fixed = 0
    for i, idx in enumerate(ids):
        try:
            old = store.doc(idx) or {}
            detail = kf.parse_detail(client.page(idx))
        except kf.KapStop as e:
            # KAP 429/5xx: nazikce dur -- bu betik idempotent (kirli kalanlar bir
            # sonraki kosuda tekrar secilir), kalanlari zorlamaya calismaz.
            print("KAP durdu (%s), %d/%d islendi, kalan bir sonraki kosuda" % (e, i, len(ids)))
            break
        doc = {**old, **detail}
        store.save_doc(idx, doc)
        if not _is_dirty(doc):
            fixed += 1
    print("yeniden ayristirildi: %d/%d" % (fixed, len(ids)))


if __name__ == "__main__":
    main()
