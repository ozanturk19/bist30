#!/usr/bin/env python3
"""Kanonik lint kapsami — "kapsam elle secilmez, kapsam TURETILIR" (K6 dersi).

NEDEN VAR (T1.7, DEV-2, 08.08.2026):
`tools/format-lint.sh` sablon listesini app.py'den TEK SATIRLIK bir
`grep render_template(` ile turetiyordu. Cagri cok satirli yazilmissa sablon adi
bir sonraki satirda kalir ve grep onu SESSIZCE dusurur. Olculdu:

    AST turetimi (kanonik)     : 27 sayfa sablonu
    format-lint'in tek-satir grep'i: 26  -> `hisseler.html` HICBIR kategoride denetlenmiyordu
    ayrica `404.html` errorhandler ile kayitli; `render_template` grep'i onu
    yakaliyor ama bir ROTA'ya baglamak mumkun degil.

Hicbir arac hata vermiyordu, hicbir exit kodu 1 degildi: klasik SESSIZ ATLAYAN GUARD.

COZUM — kapsami rota tablosundan degil, SABLONUN KENDISINDEN turet:
bir dosya "sayfa" sayilir ancak ve ancak TAM DOKUMAN uretiyorsa. T2.2 sonrasi bunun
iki gecerli formu var:

    post-T2.2 : {% extends '_base.html' %}   tasiyor
    pre-T2.2  : "<head>"                     tasiyor

Alt cizgiyle baslayan dosya PARTIAL'dir (parca uretir) -> kapsama girmez.
Jinja yorumlari ({# ... #}) once soyulur: `_head.html`in sozlesme notundaki ORNEK
`{% extends %}` satiri bir kez paydayi 27 -> 28 yapmisti (olculdu, commit e4d6c4a).

RATCHET: gercek sayi `tools/lint_scope_expected.txt`teki sayidan KUCUKSE hata.
Dedektor bir gun sessizce daralirsa (ornegin kabuk formu tekrar degisirse) kapsam
sifira dogru kayar ve ondan sonraki her "27/27" iddiasi KIRIK PAYDAYA karsi olculur.
Ratchet tam olarak bunu engeller. Yeni sayfa eklendiginde beklenen sayi ELLE yukseltilir
(`--baseline`) — bu bilincli bir islemdir, sessiz genisleme degil.

Kullanim:
    python3 tools/lint_scope.py              # sayfa sablonlarini satir satir bas
    python3 tools/lint_scope.py --check      # ratchet denetimi (deploy kapisi)
    python3 tools/lint_scope.py --baseline   # beklenen sayiyi bugunku degere sabitle
Cikis: 0 = tamam, 1 = kapsam daralmis, 2 = dedektor kirik (0 sayfa bulundu)
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "templates"
EXPECTED_FILE = ROOT / "tools" / "lint_scope_expected.txt"

EXTENDS_RE = re.compile(r"{%-?\s*extends\s+['\"][^'\"]+['\"]")
COMMENT_RE = re.compile(r"{#.*?#}", re.S)


def sayfa_sablonlari(tpl_dir=TPL_DIR):
    """TAM DOKUMAN ureten sablonlar. Partial ve .bak disarida."""
    out = []
    for f in sorted(tpl_dir.glob("*.html")):
        if f.name.startswith("_") or ".bak" in f.name:
            continue
        try:
            txt = COMMENT_RE.sub("", f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if EXTENDS_RE.search(txt) or "<head>" in txt:
            out.append(f)
    return out


def beklenen():
    try:
        return int(EXPECTED_FILE.read_text(encoding="utf-8").split("#")[0].strip())
    except (OSError, ValueError):
        return None


def main(argv):
    sayfalar = sayfa_sablonlari()
    n = len(sayfalar)

    if "--baseline" in argv:
        EXPECTED_FILE.write_text(
            "%d  # kanonik sayfa sablonu sayisi — YENI SAYFA eklenince bilincli yukselt\n" % n,
            encoding="utf-8",
        )
        print("baseline yazildi: %d sayfa" % n)
        return 0

    if "--check" in argv:
        if n == 0:
            print("KIRIK  lint_scope: 0 sayfa sablonu bulundu — DEDEKTOR BOZUK.")
            print("       (extends/<head> olcutu artik eslesmiyor olabilir; kapsam sifira dustu)")
            return 2
        bek = beklenen()
        if bek is None:
            print("KIRIK  lint_scope: %s okunamadi/gecersiz — beklenen sayi yok." % EXPECTED_FILE.name)
            return 2
        if n < bek:
            eksik = {f.name for f in sayfa_sablonlari()}
            print("KIRIK  lint_scope: kapsam DARALDI — bulunan %d < beklenen %d" % (n, bek))
            print("       bulunan: %s" % " ".join(sorted(eksik)))
            print("       Sayfa silindiyse `--baseline` ile bilincli olarak dusur;")
            print("       silinmediyse dedektor kor kalmis demektir (SESSIZ ATLAYAN GUARD).")
            return 1
        if n > bek:
            print("TEMIZ  lint_scope: %d sayfa (beklenen %d — yeni sayfa var, `--baseline` ile sabitleyin)" % (n, bek))
            return 0
        print("TEMIZ  lint_scope: %d/%d sayfa sablonu" % (n, bek))
        return 0

    for f in sayfalar:
        print(f.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
