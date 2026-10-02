#!/usr/bin/env python3
"""DEV-2 kanonik rota->sablon haritasi.

Neden var: `render_template(` cagrisi app.py'de COK SATIRLI olabiliyor; sablon adi
bir sonraki satirda duruyor. Satir-bazli grep bunlari sessizce dusurur ve paydayi
EKSIK gosterir (DEV2-011 §1: hisseler.html bir kez "olu sablon" damgasi yedi).
Bu yuzden ayristirma AST ile yapiliyor, regex ile degil.

Cikti: TSV  ->  sablon <TAB> rota <TAB> ornek_url
"""
import ast
import re
import sys
from pathlib import Path

APP = Path(sys.argv[1] if len(sys.argv) > 1 else "/root/bist30/app.py")
TPL_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "/root/bist30/templates")

# Kanonik payda = TAM DOKUMAN render eden sablonlar. Partial'lar (parca uretir) girmez.
# T2.2 sonrasi sayfa sablonlarinda artik "<head>" YOK — kabuk _base.html'e tasindi.
# Bu yuzden olcut IKI FORMU da tanir; aksi halde payda 27 -> 1'e duser ve
# bundan sonraki her "27/27" iddiasi kirik paydaya karsi olculur.
#   post-T2.2 : {% extends '_base.html' %}  tasiyan dosya      -> sayfa
#   pre-T2.2  : "<head>" tasiyan dosya                          -> sayfa
# _base.html kabugun KENDISI: <head> tasir ama sayfa DEGILDIR -> disarida.
EXTENDS_RE = re.compile(r"{%-?\s*extends\s+['\"]([^'\"]+)['\"]")
SHELL = "_base.html"


# Jinja yorumu {# ... #} icindeki ornek kod DEDEKTORU YANILTIR: _head.html'in
# sozlesme notuna ornek olarak yazilan "{% extends '_base.html' %}" satiri
# partial'i SAYFA saydirdi ve payda 27 -> 28 oldu (olculdu). Yorumlar once
# soyuluyor. Ayrica alt-cizgiyle baslayan dosya PARTIAL'dir; parca uretir,
# tam dokuman degil -> kanonik paydaya hicbir kosulda girmez.
COMMENT_RE = re.compile(r"{#.*?#}", re.S)


def head_bearing():
    out = set()
    for f in sorted(TPL_DIR.glob("*.html")):
        if f.name.startswith("_"):
            continue
        try:
            txt = COMMENT_RE.sub("", f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if EXTENDS_RE.search(txt) or "<head>" in txt:
            out.add(f.name)
    return out


# rota parametrelerine somut, canlida 200 donen ornek degerler
SAMPLE = {
    "ticker": "THYAO",
    "symbol": "THYAO",
    "sembol": "THYAO",
    "slug": "bist100-nedir",
    "kategori": "analiz",
    "category": "analiz",
    "token": "TESTTOKEN",
    "code": "THYAO",
    "asset": "BTC-USD",
    "varlik": "BTC-USD",
}


def fill(rule):
    """/hisse/<ticker> -> /hisse/THYAO"""
    def sub(m):
        raw = m.group(1)
        name = raw.split(":")[-1]
        return SAMPLE.get(name, "TEST")
    return re.sub(r"<([^>]+)>", sub, rule)


def main():
    tree = ast.parse(APP.read_text(encoding="utf-8", errors="replace"))
    heads = head_bearing()
    rows = []          # (template, rule)
    seen_tpl = set()
    dynamic = []       # degiskenle render_template cagrilari

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        rules = []
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            fn = dec.func
            nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if nm != "route":
                continue
            if dec.args and isinstance(dec.args[0], ast.Constant):
                methods = None
                for kw in dec.keywords:
                    if kw.arg == "methods":
                        try:
                            methods = ast.literal_eval(kw.value)
                        except Exception:
                            methods = None
                if methods and "GET" not in [m.upper() for m in methods]:
                    continue        # POST-only rota GET ile olculemez
                rules.append(dec.args[0].value)
        if not rules:
            continue
        # bu fonksiyonun govdesindeki render_template cagrilari (COK SATIRLI DAHIL:
        # AST satir sonlarini gormez, cagri tek dugumdur)
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Call) and
                    getattr(sub.func, "id", getattr(sub.func, "attr", "")) == "render_template"):
                continue
            if not sub.args:
                continue
            a0 = sub.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                tpl = a0.value
                seen_tpl.add(tpl)
                for r in rules:
                    rows.append((tpl, r))
            else:
                dynamic.append((node.name, rules[0]))

    # CPO-1361 §6-1 DUZELTME — eskiden burada `best[tpl]` her sablon icin YALNIZ
    # en kisa rotayi tutuyordu ve tabloya sablon basina TEK satir basiliyordu.
    # Sonuc: her kapsam iddiasinin paydasi sistematik olarak KUCUK cikiyordu.
    # Olculdu: varlik.html tek basina 11 rota tasiyor, tabloda 1 gorunuyordu;
    # palet sapmasi bu yuzden "3 sayfa" diye cerceveleniyordu.
    # Yeni davranis: TUM rotalar basilir. Kanonik ornek (en kisa) korunur ama
    # artik 4. sutundaki etiketle isaretlenir — eski tuketiciler satiri
    # `split("\t")[:3]` ile ayristirdigi icin 4. sutun onlari KIRMAZ
    # (dogrulandi: tools/dev2_shell_hash.py:41 — ve o `set()` uyguluyor).
    per_tpl = {}
    for tpl, rule in rows:
        if tpl not in heads:
            continue
        per_tpl.setdefault(tpl, set()).add(rule)

    toplam_rota = 0
    for tpl in sorted(per_tpl):
        # kanonik = en az parametreli, sonra en kisa
        kurallar = sorted(per_tpl[tpl], key=lambda r: (r.count("<"), len(r), r))
        for i, rule in enumerate(kurallar):
            etiket = "CANONICAL" if i == 0 else "ALT"
            print(f"{tpl}\t{rule}\t{fill(rule)}\t{etiket}")
            toplam_rota += 1

    missing = sorted(heads - set(per_tpl))
    print(f"# head_tasiyan={len(heads)} sablon_eslesen={len(per_tpl)} "
          f"TOPLAM_ROTA={toplam_rota} eslesmeyen={len(missing)}",
          file=sys.stderr)
    coklu = {t: len(r) for t, r in per_tpl.items() if len(r) > 1}
    if coklu:
        print("# COK-ROTALI SABLONLAR (eski tablo bunlari 1 sayiyordu): "
              + " ".join(f"{t}={n}" for t, n in sorted(coklu.items(), key=lambda kv: -kv[1])),
              file=sys.stderr)
    if missing:
        print(f"# ESLESMEYEN: {' '.join(missing)}", file=sys.stderr)
    if dynamic:
        print(f"# DEGISKENLI render_template: {dynamic}", file=sys.stderr)


if __name__ == "__main__":
    main()
