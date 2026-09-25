#!/usr/bin/env python3
"""D-42 / D-54: eski kodla (4a1dc40 öncesi) dondurulmuş ısı haritası günlerindeki yanlış "bayat" bayrağını onarır.

Hata: heatmap.build analiz satırının `bar_date`'ini (D-06, GG.AA.YYYY) ISO günle kıyaslıyordu, eşleşme hiç olmadı;
o kodla dondurulan HER gün 100/100 satır stale=true (kutular soluk + taralı + "Veri gecikmeli"). Donmuş dosyanın
üzerine yazılmaz (heatmap.save_frozen), yani 4a1dc40 canlıya çıkmadan önce dondurulan her gün onarım ister:
25.09 ve deploy hafta içi 19:05 sonrasına kalırsa o günün ~18:47 görüntüsü de.

Aday gün: dosya adı = asof, TÜM satırlar stale=true ve en az bir satır kuralla bayat değil.
Kural (düzeltilmiş build'in bar_date dışındaki kısmı): stale = d1 yok ya da |d1| > heatmap.STALE_ABS_D1.
d1 o günün resmi kapanış kaydından gelir (bar_date'ten bağımsız); 25.09 ölçümü: /api/data 233/233 satırda
bar_date = o gün. Onarım yalnız "stale" değerlerini değiştirir (aynı json.dump biçimi, dosya kipi/sahibi korunur).
Onarılan günün türetilmiş görselleri (<gün>.png, <gün>-kare.png) silinir; ilk istekte yeni veriyle üretilir.
Hepsi heatmap_image.ensure ile aynı kilit (.harita.lock) altında.

Ne zaman: 4a1dc40'ı yükleyen restart'tan ÖNCE (o anda diskteki her gün eski kodla dondurulmuştur). Restart'tan
sonra koşulursa --son-gun <eski kodun dondurduğu son gün> verilmeli (yeni kodla gerçekten tümü bayat bir gün
onarılmasın). İdempotent: onarılmış gün bir daha aday olmaz.

Kullanım: python3 tools/heatmap_bayat_onarim.py [--dir data/heatmap] [--son-gun YYYY-AA-GG] [--yaz]
Varsayılan kuru koşu (yalnız listeler). Silinen görsel varsa CF'de temizlenecek URL'leri yazar (geçmiş gün
görseli 'immutable' servis edilmiş olabilir: tarayıcı önbelleği temizlenemez, bu yüzden restart'tan önce koş).
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import heatmap  # noqa: E402

DAY_FILE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})\.json\Z")
LOCK_NAME = ".harita.lock"                       # heatmap_image.ensure ile aynı kilit
PNG_NAMES = ("%s.png", "%s-kare.png")             # heatmap_image.file_name
SITE = "https://borsapusula.com"


def rule_stale(row):
    d1 = (row.get("ch") or {}).get("d1")
    return d1 is None or abs(d1) > heatmap.STALE_ABS_D1


def is_candidate(snap, day):
    rows = (snap or {}).get("rows") or []
    return (snap.get("asof") == day and bool(rows) and all(r.get("stale") is True for r in rows)
            and not all(rule_stale(r) for r in rows))


def repair(snap):
    """Yerinde onarır; (önce, sonra) bayat sayısı."""
    rows = snap.get("rows") or []
    before = sum(1 for r in rows if r.get("stale"))
    for r in rows:
        r["stale"] = rule_stale(r)
    return before, sum(1 for r in rows if r["stale"])


def dump(snap):
    return json.dumps(snap, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _replace(path, data):
    st = os.stat(path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, stat.S_IMODE(st.st_mode))
        try:
            os.chown(tmp, st.st_uid, st.st_gid)
        except OSError:
            pass
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def run(dir_, last_day=None, write=False, out=print):
    """Aday günleri listeler / onarır. Döner: [{day, before, after, md5_old, md5_new, removed, latest}]."""
    days = sorted(m.group(1) for m in map(DAY_FILE.match, os.listdir(dir_)) if m)
    latest = days[-1] if days else None
    done = []
    lock_fd = os.open(os.path.join(dir_, LOCK_NAME), os.O_CREAT | os.O_RDWR, 0o644) if write else None
    try:
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        for day in days:
            if last_day and day > last_day:
                continue
            path = os.path.join(dir_, day + ".json")
            with open(path, "rb") as f:
                raw = f.read()
            snap = json.loads(raw.decode("utf-8"))
            if not is_candidate(snap, day):
                continue
            before, after = repair(snap)
            data = dump(snap)
            item = {"day": day, "before": before, "after": after, "latest": day == latest,
                    "md5_old": hashlib.md5(raw).hexdigest(), "md5_new": hashlib.md5(data).hexdigest(),
                    "removed": []}
            if write:
                _replace(path, data)
                for pat in PNG_NAMES:
                    p = os.path.join(dir_, pat % day)
                    if os.path.isfile(p):
                        os.unlink(p)
                        item["removed"].append(pat % day)
            done.append(item)
            out("%s: bayat %d/%d -> %d  md5 %s -> %s  %s%s" % (
                day, before, len(snap["rows"]), after, item["md5_old"], item["md5_new"],
                "ONARILDI" if write else "kuru (--yaz ile yazar)",
                ("  silinen gorsel: " + ", ".join(item["removed"])) if item["removed"] else ""))
    finally:
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    if not done:
        out("aday gun yok (onarilacak bir sey yok)")
    purge = ["%s/harita/%s" % (SITE, n) for it in done for n in it["removed"]]
    if purge:
        out("CF temizle (gorsel onceden servis edilmis olabilir; gecmis gunse 'immutable'):")
        for u in purge:
            out("  " + u)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=os.path.join(ROOT, "data", "heatmap"))
    ap.add_argument("--son-gun", default=None, help="yalniz bu gun ve oncesi (YYYY-AA-GG)")
    ap.add_argument("--yaz", action="store_true", help="onar ve yaz (varsayilan kuru kosu)")
    a = ap.parse_args(argv)
    if a.son_gun and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", a.son_gun):
        ap.error("--son-gun YYYY-AA-GG olmali")
    if not os.path.isdir(a.dir):
        print("klasor yok: %s (aday gun yok)" % a.dir)
        return 0
    run(a.dir, a.son_gun, a.yaz)
    return 0


if __name__ == "__main__":
    sys.exit(main())
