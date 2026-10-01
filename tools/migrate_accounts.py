#!/usr/bin/env python3
"""D-50 — mevcut aboneleri hesaba çevirir (tek seferlik; tekrar koşmak zararsız).

Varsayılan KURU KOŞU: dosyaya dokunmaz, yalnız sayım basar (e-posta adresi basılmaz).
    python3 tools/migrate_accounts.py                    # kuru koşu (subscribers.json)
    python3 tools/migrate_accounts.py --apply            # yedek al + göç et + doğrula
    python3 tools/migrate_accounts.py --restore <yedek>  # yedeği geri koy
    --file <yol>  başka dosya (test/sentetik veri)

Göç (accounts.migrate_record): izleme listesi = tickers ∪ follow ∪ alerts anahtarları;
`tickers` boşsa bülten açık (eski davranış: tüm değişimler), doluysa yalnız liste; portföy
boş; confirmed_at/kvkk_consent_ts boş (ilk kodlu girişte yazılır); `follow` alanı listeye
taşınır. Uygulama çalışırken güvenlidir: app ile aynı kilit dosyası (subscribers.json.lock,
fcntl.flock) tutulur; yazım atomik (tempfile + fsync + os.replace), dosya izni 0600.
Uygulama göç koşmadan da doğru çalışır (eski kayıt okunurken aynı görünüm türetilir).
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
        rep = accounts.migrate_all(work)
        print(("UYGULA" if a.apply else "KURU KOŞU") + " " + json.dumps(rep, ensure_ascii=False, sort_keys=True))
        if not a.apply:
            return 0
        if rep["migrated"] == 0:
            print("değişiklik yok (hepsi zaten hesap)"); return 0
        bak = "%s.bak.d50-%s" % (path, time.strftime("%Y%m%d%H%M%S"))
        with open(bak, "wb") as f:
            f.write(raw)
        os.chmod(bak, 0o600)
        _write(path, work)
        back = json.load(open(path, encoding="utf-8"))
        ok = (set(back) == set(subs)
              and all(isinstance(r, dict) and r.get("account_v") == 1 for r in back.values() if isinstance(r, dict)))
        print("yedek: %s (%d bayt)" % (bak, len(raw)))
        print("doğrulama: %s (%d kayıt)" % ("TAMAM" if ok else "HATA", len(back)))
        if not ok:
            shutil.copyfile(bak, path)
            print("HATA: yedek geri kondu"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
