#!/usr/bin/env python3
"""KAPI 52 — app.py'nin YAYIMLANAN metin kapisi (K-CG, 22.09.2026).

Neden var (76. dersin ikinci uygulamasi):
  Kapi 50 (`intraday-claim-check`) yalnizca `templates/`, kapi 51
  (`blog-claim-check`) yalnizca `blog_content.py` tarar. Oysa urunun
  kullaniciya BASTIGI metnin bir bolumu `app.py` icinde yasiyor:
  e-posta govdeleri (`_build_welcome_email`, `_build_signal_email`),
  e-posta KONU satirlari, SSS/JSON-LD uretecleri ve AI prompt sozlugu.
  Bu kanal 51 kapinin hicbirinin girdi kumesinde degildi; K-CG'de
  /profil "⭐ Sadece Hacim Onaylı" derken ayni tercihten uretilen mail
  "💎 Premium Sinyal Değişimi" konusuyla geliyordu.

Yontem (77. ders): `ast` ile YALNIZ string literalleri; docstring'ler
(Module/Func/Class'in ilk Expr'i) ve serbest `Expr` string bloklari
YAYIMLANMAZ, bu yuzden haric tutulur. Boylece yorum/docstring bagisikligi
bedavaya gelir ve kapi hatanin YAZIMINI degil KENDISINI arar (52. ders).

Kanon (kaynak: templates/metodoloji.html:221-226, templates/profil.html:44):
  ⭐ = "Hacim Onaylı"      -> is_premium / RVOL >= 1.20
  💎 = "Yüksek Skor"       -> Teknik Güç Skoru 70+ (tier=guclu_sinyal)
  "Premium" sozcugu CPO-DEV2-053/055 ile EMEKLI (paywall cagrisimi).
  Skorun kanonik adi: "Teknik Güç Skoru" (app.py:1622-1623, 39 yuzey).

Cikis: ihlal varsa satir+kural+metin, exit 1.
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "app.py")

# mail_pref degeri "premium" bir VERI ANAHTARI (kullaniciya gosterilmez) --
# yalnizca karsilastirma/sozluk anahtari olarak gecen tam-esit dizeler muaf.
DATA_KEY_EXACT = {"premium", "is_premium", "mail_pref", "guclu_sinyal",
                  "only_premium"}  # URL/JSON anahtarlari -- adres cubugunda gecse de
                                   # API sozlesmesidir, yeniden adlandirmak bookmark kirar

RULES = [
    # (kod, regex, aciklama)
    ("R1", re.compile(r"[Pp]remium"),
     "'Premium' sozcugu emekli (CPO-DEV2-053/055) -- kanon: 'Hacim Onaylı'"),
    ("R2", re.compile(r"\U0001F48E"),
     "💎 = 'Yüksek Skor' (Teknik Güç Skoru 70+); hacim teyidi icin ⭐ kullanilir"),
    ("R3", re.compile(r"(?i)\b(sinyal skoru|güç puanı|sinyal puanı|skor gücü)\b"),
     "skorun kanonik adi 'Teknik Güç Skoru' (bkz. metodoloji + 39 yuzey)"),
    ("R4", re.compile(r"(?i)(backtest performans raporu|sinyal performans analizi|performans raporu)"),
     "emekli yuzey adi -- /backtest ve /sinyal-performans 301 ile /tarama'ya gider"),
]


def published_strings(path):
    """Yayimlanan string literalleri (docstring ve serbest string bloklari haric)."""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    skip = set()
    for node in ast.walk(tree):
        # docstring: Module/FunctionDef/AsyncFunctionDef/ClassDef ilk ifadesi
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
               and isinstance(first.value.value, str):
                skip.add(id(first.value))
        # serbest string ifadesi (blok-yorum deseni)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            skip.add(id(node.value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            out.append((node.lineno, node.value))
    return out


def main():
    violations = []
    for lineno, text in published_strings(TARGET):
        if text.strip() in DATA_KEY_EXACT:
            continue
        for code, pat, why in RULES:
            m = pat.search(text)
            if m:
                frag = text[max(0, m.start() - 45):m.end() + 45].replace("\n", " ")
                violations.append((lineno, code, why, frag.strip()))
    if violations:
        print("KAPI 52 — app.py yayimlanan metin ihlalleri (%d):" % len(violations))
        for lineno, code, why, frag in sorted(violations):
            print("  app.py:%-6d %s  %s" % (lineno, code, why))
            print("           …%s…" % frag[:150])
        return 1
    print("KAPI 52 OK — app.py yayimlanan metni kanonik (%d literal tarandi)"
          % len(published_strings(TARGET)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
