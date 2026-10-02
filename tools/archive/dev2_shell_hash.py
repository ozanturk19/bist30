#!/usr/bin/env python3
"""DEV-2 canli kabuk hash'i — kayipsizlik kaniti icin pair-set hash.

Neden var: "goze ayni geldi" veya "dosya sunuluyor" kayipsizlik kaniti DEGILDIR
(feedback_kayipsizlik_pair_set_hash). Bu arac deploy ONCESI ve SONRASI ayni
yuzey kumesini masaustu + mobil UA ile ceker ve bayt hash'ini karsilastirir.

Sayfalar piyasa kapaliyken bayt-stabil olduguna gore normalize ETMIYORUZ —
normalizasyon gercek regresyonu da maskeleyebilir. Bunun yerine her surum icin
IKI ardisik cekim alinir; ikisi farkliysa o yuzey "VOLATIL" isaretlenir ve
kanit paydasindan DUSULUR (sessizce "gecti" sayilmaz).

Kullanim:
  python3 tools/dev2_shell_hash.py snap  /tmp/dev2hash/before.json
  python3 tools/dev2_shell_hash.py snap  /tmp/dev2hash/after.json
  python3 tools/dev2_shell_hash.py diff  /tmp/dev2hash/before.json /tmp/dev2hash/after.json
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = "http://127.0.0.1:8003"
UA_D = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

ROUTE_MAP = Path(__file__).with_name("dev2_route_map.py")


def urls():
    """Yuzey listesi rota tablosundan turetilir — elle tasinmaz."""
    r = subprocess.run([sys.executable, str(ROUTE_MAP)], capture_output=True, text=True)
    out = []
    for ln in (r.stdout or "").splitlines():
        if ln.startswith("#") or "\t" not in ln:
            continue
        tpl, _route, sample = ln.split("\t")[:3]
        out.append((tpl, sample))
    # rota tablosunda karsiligi olmayan kanonik yuzeyler
    out.append(("404.html", "/bu-sayfa-yok-404-testi"))
    return sorted(set(out))


def fetch(url, ua):
    r = subprocess.run(
        ["curl", "-s", "-m", "20", "-A", ua, "-w", "\n@@HTTP@@%{http_code}", BASE + url],
        capture_output=True,
    )
    body = r.stdout
    code = ""
    if b"\n@@HTTP@@" in body:
        body, _, tail = body.rpartition(b"\n@@HTTP@@")
        code = tail.decode(errors="replace").strip()
    return body, code


def snap(path):
    rows = []
    for tpl, url in urls():
        rec = {"tpl": tpl, "url": url}
        for key, ua in (("d", UA_D), ("m", UA_M)):
            a, ca = fetch(url, ua)
            time.sleep(0.25)
            b, cb = fetch(url, ua)
            stable = (a == b) and (ca == cb)
            rec[key] = {
                "http": ca,
                "md5": hashlib.md5(a).hexdigest(),
                "len": len(a),
                "stable": stable,
            }
        rows.append(rec)
        print(f"  {tpl:<26} {url:<28} d={rec['d']['http']}/{rec['d']['md5'][:8]}"
              f"{'' if rec['d']['stable'] else ' VOLATIL'}"
              f"  m={rec['m']['http']}/{rec['m']['md5'][:8]}"
              f"{'' if rec['m']['stable'] else ' VOLATIL'}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(rows, indent=1))
    print(f"\nyazildi: {path}  ({len(rows)} yuzey x 2 UA)")


def diff(p1, p2):
    A = {(r["tpl"], r["url"]): r for r in json.loads(Path(p1).read_text())}
    B = {(r["tpl"], r["url"]): r for r in json.loads(Path(p2).read_text())}
    keys = sorted(set(A) | set(B))
    same = diff_ = volatile = missing = 0
    print(f"{'sablon':<26} {'yuzey':<28} {'masaustu':<12} {'mobil':<12}")
    for k in keys:
        a, b = A.get(k), B.get(k)
        if not a or not b:
            missing += 1
            print(f"{k[0]:<26} {k[1]:<28} {'EKSIK':<12} {'EKSIK':<12}")
            continue
        cells = []
        for key in ("d", "m"):
            if not a[key]["stable"] or not b[key]["stable"]:
                cells.append("VOLATIL")
                volatile += 1
            elif a[key]["md5"] == b[key]["md5"] and a[key]["http"] == b[key]["http"]:
                cells.append("BIREBIR")
                same += 1
            else:
                cells.append(f"FARKLI({a[key]['len']}->{b[key]['len']})")
                diff_ += 1
        print(f"{k[0]:<26} {k[1]:<28} {cells[0]:<12} {cells[1]:<12}")
    tot = len(keys) * 2
    print(f"\nPAYDA (yuzey x UA) = {tot}")
    print(f"  BIREBIR   : {same}/{tot}")
    print(f"  FARKLI    : {diff_}/{tot}")
    print(f"  VOLATIL   : {volatile}/{tot}   <- olculemedi, kanit paydasindan DUSULUR")
    print(f"  EKSIK     : {missing}")
    return 0 if diff_ == 0 else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "snap"
    if cmd == "snap":
        snap(sys.argv[2] if len(sys.argv) > 2 else "/tmp/dev2hash/snap.json")
    else:
        sys.exit(diff(sys.argv[2], sys.argv[3]))
