#!/usr/bin/env python3
"""D-38 — mevcut aktif aboneleri çift-onay şartından grandfather eder (tek seferlik;
tekrar koşmak zararsız). CPO-1823 karar (b): confirmed_at yoksa = subscribed_at.

Varsayılan KURU KOŞU: dosyaya dokunmaz, yalnız sayım basar (e-posta adresi basılmaz).
    python3 tools/migrate_confirm_grandfather.py                    # kuru koşu (subscribers.json)
    python3 tools/migrate_confirm_grandfather.py --apply            # yedek al + uygula + doğrula
    python3 tools/migrate_confirm_grandfather.py --restore <yedek>  # yedeği geri koy
    --file <yol>  başka dosya (test/sentetik veri)

Kapsam: yalnız `active: true` VE `confirmed_at` boş/yok kayıtlar. Pasif kayıtlara dokunmaz
(yeniden abone olurken D-38 akışından geçer). Bu script çalışmadan app.py'nin confirmed_at
gate'i deploy edilirse mevcut aktif aboneler digest'ten düşer (P0) — sıra: migrate --apply
önce, deploy sonra.
"""
import argparse
import copy
import fcntl
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import accounts  # noqa: E402


class _FileLock:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.fh = open(self.path, "w")
        fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


def _write(path, data):
    accounts.atomic_write_json(path, data)
    os.chmod(path, 0o600)


def grandfather(subs):
    """Döner: (değişen_sayısı, rapor). `subs` yerinde değiştirilir."""
    n = 0
    for email, rec in subs.items():
        if not isinstance(rec, dict):
            continue
        if rec.get("active", True) and not rec.get("confirmed_at"):
            rec["confirmed_at"] = rec.get("subscribed_at") or accounts.now_iso()
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default=os.path.join(ROOT, "subscribers.json"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", metavar="YEDEK")
    a = ap.parse_args(argv)
    path = a.file

    with _FileLock(path + ".lock"):
        if a.restore:
            src = json.load(open(a.restore, encoding="utf-8"))
            if not isinstance(src, dict):
                print("HATA: yedek sözlük değil"); return 2
            _write(path, src)
            print("geri yüklendi: %d kayıt <- %s" % (len(src), a.restore))
            return 0
        if not os.path.exists(path):
            print("dosya yok: %s (göç edilecek kayıt yok)" % path); return 0
        raw = open(path, "rb").read()
        subs = json.loads(raw.decode("utf-8"))
        if not isinstance(subs, dict):
            print("HATA: beklenmeyen biçim"); return 2
        work = copy.deepcopy(subs)
        n = grandfather(work)
        print(("UYGULA" if a.apply else "KURU KOŞU") + " grandfathered=%d toplam=%d" % (n, len(subs)))
        if not a.apply:
            return 0
        if n == 0:
            print("değişiklik yok (hepsi zaten confirmed_at'li)"); return 0
        bak = "%s.bak.d38-%s" % (path, time.strftime("%Y%m%d%H%M%S"))
        with open(bak, "wb") as f:
            f.write(raw)
        os.chmod(bak, 0o600)
        _write(path, work)
        back = json.load(open(path, encoding="utf-8"))
        ok = (set(back) == set(subs)
              and all(bool(back[e].get("confirmed_at")) for e in back
                      if isinstance(back.get(e), dict) and back[e].get("active", True)))
        print("yedek: %s (%d bayt)" % (bak, len(raw)))
        print("doğrulama: %s (%d kayıt)" % ("TAMAM" if ok else "HATA", len(back)))
        if not ok:
            shutil.copyfile(bak, path)
            print("HATA: yedek geri kondu"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
