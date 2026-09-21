#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/merge-report-check.py — K-BI: BIRLESTIRME SAYIMI TEK KANON

SORU: "Portfoye N pozisyon eklendi" diyen mesaj, GERCEKTEN eklenen sayiyi mi
soyluyor, yoksa gelen listenin uzunlugunu mu?

OLCULDU (21.09.2026, fix oncesi agac -- templates/portfolio.html):
  * importPortfolio (dosyadan ice aktarma) -> `added` sayaci tutuyor, DOGRU
  * loadCloudToken  (buluttan yukleme)     -> hic saymiyor,
        `${data.positions.length - skipped} pozisyon`
    yani mevcut portfoyde ZATEN bulundugu icin EKLENMEYEN kayitlari da
    "yuklendi" diye sayiyordu. Ayni token ikinci kez yuklendiginde 0 pozisyon
    eklenirken ekranda "Yuklendi! 5 pozisyon." yaziyordu.
  Yinelenen-kayit olcutu de iki yerde ayri yazilmisti
  (`x.price === p.price` vs `+x.price === +p.price`).

KANON: gelen pozisyonlari portfoye ekleyen TEK yol `_pfMergePositions(list)`;
  kullaniciya gosterilen sayi DAIMA onun donusunden (`added`/`duplicate`)
  gelir, gelen listenin uzunlugundan DEGIL.

IHLAL SINIFLARI (tabani SIFIR):
  A) KACAK PUSH   -- `portfolio.push(` kanon disi bir fonksiyonda
  B) KANONU ATLAMA-- birlestirme yolu `_pfMergePositions(` cagirmiyor
  C) UZUNLUKTAN SAYIM -- birlestirme yolunda `.length - ` ile sayi turetme
     (defektin tam bicimi: `positions.length - skipped`)

OLCUM DISIPLINI: blok yorumlar SOYULUR (bu dosyadaki ve sablondaki kendi
aciklamalarim bulgu uretmesin) ve POZITIF KONTROL calisir --
`--self-test` fix ONCESI kodu sentetik degil GERCEK bicimde verir ve kapinin
EXIT=1 verdigini dogrular; dedektor ihlali goremiyorsa sonuc "temiz" degil
"olculemedi"dir.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "templates", "portfolio.html")

PUSH_ALLOWED = ("_pfMergePositions", "addPosition")
MERGE_CALLERS = ("importPortfolio", "loadCloudToken")
CANON = "_pfMergePositions("


def strip_block_comments(src):
    """/* ... */ -> ayni uzunlukta bosluk (satir/sutun konumlari korunur)."""
    out = []
    i, n = 0, len(src)
    while i < n:
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j == -1:
                j = n
            else:
                j += 2
            out.append("".join("\n" if c == "\n" else " " for c in src[i:j]))
            i = j
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def function_body(src, name):
    """`function name(` basindan suslu parantez dengesiyle govdeyi dondurur."""
    m = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", src)
    if not m:
        return None
    start = src.find("{", m.end())
    if start == -1:
        return None
    depth, i, n = 0, start, len(src)
    while i < n:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return None


def audit(src):
    """Donus: ihlal mesajlari listesi."""
    src = strip_block_comments(src)
    problems = []

    bodies = {}
    for fn in set(PUSH_ALLOWED + MERGE_CALLERS):
        b = function_body(src, fn)
        if b is None:
            problems.append("EKSIK FONKSIYON: %s -- kanon yeri bulunamadi" % fn)
        bodies[fn] = b or ""

    # A) kacak push
    total_push = src.count("portfolio.push(")
    inside = sum(bodies[fn].count("portfolio.push(") for fn in PUSH_ALLOWED)
    if total_push != inside:
        problems.append(
            "A) KACAK PUSH: %d `portfolio.push(` var, %d tanesi kanon "
            "fonksiyonlarinda (%s) -- %d tanesi disarida"
            % (total_push, inside, "/".join(PUSH_ALLOWED), total_push - inside)
        )

    for fn in MERGE_CALLERS:
        body = bodies[fn]
        # B) kanonu atlama
        if CANON not in body:
            problems.append("B) KANONU ATLAMA: %s() `%s` cagirmiyor" % (fn, CANON))
        # C) uzunluktan sayim
        for m in re.finditer(r"\.length\s*-\s*", body):
            snippet = body[max(0, m.start() - 40):m.end() + 20].replace("\n", " ")
            problems.append(
                "C) UZUNLUKTAN SAYIM: %s() icinde `.length - ` ... %s"
                % (fn, snippet.strip())
            )
    return problems


def self_test():
    """POZITIF KONTROL: fix oncesi (gercek) bicim kapiya takilmali."""
    broken = """
function _pfMergePositions(list) { let added=0; portfolio.push({}); return {added}; }
function addPosition() { portfolio.push({}); }
function importPortfolio(e) {
  const _impMerge = _pfMergePositions(positions);
  showToast(`${_impMerge.added} pozisyon (${positions.length - _impMerge.added} zaten vardi).`);
}
function loadCloudToken() {
  let skipped = 0;
  data.positions.forEach(p => { if (!p.ticker) { skipped++; return; }
    const exists = portfolio.some(x => x.ticker === p.ticker);
    if (!exists) portfolio.push({...p});
  });
  _setCloudMsg(`Yuklendi! ${data.positions.length - skipped} pozisyon.`);
}
"""
    probs = audit(broken)
    kinds = {p.split(")")[0] for p in probs if p[:1] in "ABC"}
    ok = {"A", "B", "C"} <= kinds
    print("POZITIF KONTROL: %s (%d ihlal, siniflar=%s)"
          % ("GECTI" if ok else "DUSTU", len(probs), ",".join(sorted(kinds))))
    for p in probs:
        print("   . " + p)
    return 0 if ok else 1


def main():
    if "--self-test" in sys.argv:
        return self_test()

    if self_test() != 0:
        print("KAPI OLCEMEDI: pozitif kontrol dustu, sonuc 'temiz' sayilmaz.")
        return 1

    with open(TARGET, encoding="utf-8") as fh:
        src = fh.read()
    problems = audit(src)
    if problems:
        print("MERGE-REPORT-CHECK: %d IHLAL (templates/portfolio.html)" % len(problems))
        for p in problems:
            print("  X " + p)
        return 1
    print("MERGE-REPORT-CHECK: temiz -- birlestirme tek kanon (_pfMergePositions), "
          "sayim gelen listenin uzunlugundan turetilmiyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
