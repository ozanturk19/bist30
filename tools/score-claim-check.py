#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K-CN / kapi 59 — "Teknik Güç Skoru"nun BILESEN IDDIASI ve kosullu ad vaadi.

NEDEN (22.09.2026):
  Urunun basligi olan sayi `compose_score()` (app.py) ile uretilir ve
  bilesenleri KESIN: ADX(30) + gunluk hacim orani(25) + Teyit(10) + RSI(10).
  Supertrend ve EMA12/99 bu skora HIC girmez — onlar sinyalin YONUNU
  (AL/SAT/BEKLE) uretir. Buna ragmen 22.09'da dort yuzeyde bilesen listesi
  birbiriyle ve kodla celisiyordu:
    1) index.html hero (sitenin en cok okunan cumlesi): "Supertrend, ADX ve
       EMA12/99'u tek bir Teknik Güç Skoru'nda birlestiriyoruz" — uc addan
       ikisi skora hic girmiyor.
    2) hisse.html teknik-gauge data-tip: "Supertrend + ADX + hacim teyidi"
       — Supertrend yok, RSI eksik. AYNI SAYFA 360 satir yukarida (645)
       dogru listeyi yaziyordu: sayfa kendi kendisiyle celisiyordu.
    3) index.html vitrin data-tip: "ADX, hacim teyidi ve RSI" — Hacim(25p)
       ile Teyit(10p) IKI AYRI bilesendir, "hacim teyidi" bigram'i ikisini
       tek ada eritiyordu.
    4) hisse.html:2856 RSI `?` data-tip: "45-60 ideal giris penceresi"
       KOSULSUZ. K-CH (08915eb) bu iddiayi static/learning-mode.js'te,
       CPO-1769 (29147f3) sablon inline JS'te kapatmisti — ama bu kopya
       `ideal giriş` diye YAZILMISTI: iki kapi da Turkce harfi aradigi
       icin dizeyi hic gormedi. Ayni satirda badge `bpRsiZoneText` ile
       "Nötr Bölge" basiyordu; rozet ile yanindaki `?` celisiyordu.

KAPININ OLCTUGU (hatanin YAZIMINI degil KENDISINI — 56. ders):
  R0  Taranan her dosyada \\uXXXX kacislari ONCE cozulur. 4. bulgunun iki
      kapiyi birden atlatmasinin tek sebebi buydu.
  R2  "Teknik Güç Skoru" gecen CUMLEDE Supertrend/EMA anilamaz (acik dislama
      ifadesi -- "girmez", "yonunu belirler" vb. -- varsa serbest).
  R4  Ayni cumle bilesen sayiyorsa (>=2 grup) DORDU birden anilmali.
      "hacim teyidi/teyit" bitisik bigram'i YALNIZ hacim sayilir.
  R3  "ideal giris" vaadi, kosulunu ayni cumlede tasimali (Güçlü Trend /
      AL sinyal / Nötr Bölge).
  R5  Pozitif kontrol: cozumlenen cumle sayisi 0 ise kapi FAIL verir
      (85. ders — hicbir sey olcmeyen kapi "OK" demesin).

Kullanim:
  python3 tools/score-claim-check.py [--verbose] [--ref <sha>]
"""
import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = (
    sorted(str(p.relative_to(ROOT)) for p in (ROOT / "templates").glob("*.html"))
    + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "static").rglob("*.js"))
    + ["blog_content.py", "app.py"]
)

PHRASE = "Teknik Güç Skoru"

# Bilesen gruplari — compose_score() ile birebir (app.py:1574-1582)
GROUPS = {
    "ADX": re.compile(r"\bADX\b", re.I),
    "Hacim": re.compile(r"hacim", re.I),
    "RSI": re.compile(r"\bRSI\b", re.I),
    "Teyit": re.compile(r"teyi[td]", re.I),
}
# "hacim teyidi" bitisik bigram'i: TEK bilesen adi gibi okunur -> teyit sayilmaz
RE_MERGED = re.compile(r"hacim\s+teyi[td]\w*", re.I)

RE_FOREIGN = re.compile(r"supertrend|\bEMA\s?1?2?/?9?9?\b|\bEMA\b", re.I)
RE_EXCLUDED = re.compile(
    r"girmez|dahil değil|dahil edilmez|hesaba katılmaz|yönünü belirler|yönünü üretir",
    re.I,
)

RE_IDEAL = re.compile(r"ideal\s+giriş", re.I)
# R3 yalniz RSI BANDI adlandirmasini hedefler: /ozet'teki "İdeal Giriş Noktası"
# (entry_quality rozeti) ve app.py'deki "İdeal giriş bölgesi" (FIYAT araligi)
# AYRI kavramlardir, ikisi de zaten AL dalinda uretiliyor.
RE_IDEAL_SCOPE = re.compile(r"\bRSI\b|45\s*[-–]\s*60", re.I)
RE_IDEAL_COND = re.compile(r"güçlü trend|AL sinyal|nötr bölge", re.I)

RE_UESC = re.compile(r"\\u([0-9a-fA-F]{4})")
RE_JINJA_C = re.compile(r"\{#.*?#\}", re.S)
RE_HTML_C = re.compile(r"<!--.*?-->", re.S)
RE_BLOCK_C = re.compile(r"/\*.*?\*/", re.S)
RE_LINE_C = re.compile(r"^[ \t]*(?://|\*|#)[^\n]*$", re.M)
RE_TAG = re.compile(r"<[^>]+>")
# ⛔ POZITIF KONTROLUN YAKALADIGI KAPI KUSURU (22.09): kapinin ilk yazimi
#    RE_TAG ile etiketleri siliyordu — ama 4 bulgunun 3'u data-tip ATTRIBUTE'unda
#    yasiyordu, yani kapi tam da olcecegi metni ATIYORDU (--ref HEAD 4 yerine 1
#    ihlal buldu). Kullaniciya GORUNEN attribute'lar etiket silinmeden once
#    ayri metin bloklari olarak cikarilir.
RE_TEXT_ATTR = re.compile(
    r'(?:data-tip|aria-label|title|placeholder|alt|content)\s*=\s*"([^"]*)"', re.I)
# Cumle siniri: . ! ? ; satir sonu, HTML &#10; ve JS \n kacisi
RE_SENT = re.compile(r"(?:[.!?;]\s|\n|&#10;|\\n)")


def load(path, ref=None):
    if ref:
        try:
            return subprocess.check_output(
                ["git", "show", f"{ref}:{path}"], cwd=ROOT, stderr=subprocess.DEVNULL
            ).decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            return None
    p = ROOT / path
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None


def normalize(raw):
    """R0: \\uXXXX coz, yorumlari at, etiketleri/entity'leri duzlestir."""
    txt = RE_UESC.sub(lambda m: chr(int(m.group(1), 16)), raw)
    txt = RE_JINJA_C.sub(" ", txt)
    txt = RE_HTML_C.sub(" ", txt)
    txt = RE_BLOCK_C.sub(" ", txt)
    txt = RE_LINE_C.sub(" ", txt)
    txt = txt.replace("&#10;", "\n")
    attrs = RE_TEXT_ATTR.findall(txt)
    txt = RE_TAG.sub(" ", txt)
    if attrs:
        txt = txt + "\n" + "\n".join(attrs)
    txt = html.unescape(txt)
    return txt


def sentences(txt):
    return [s.strip() for s in RE_SENT.split(txt) if s.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--ref", default=None)
    args = ap.parse_args()

    violations = []
    scanned_sent = 0
    score_windows = 0

    for path in TARGETS:
        raw = load(path, args.ref)
        if raw is None:
            continue
        txt = normalize(raw)
        for sent in sentences(txt):
            scanned_sent += 1

            # R3 — kosullu ad vaadi (her yuzeyde gecerli)
            if (RE_IDEAL.search(sent) and RE_IDEAL_SCOPE.search(sent)
                    and not RE_IDEAL_COND.search(sent)):
                violations.append(
                    ("R3", path, '"ideal giriş" kosulsuz yaziliyor', sent[:180])
                )

            if PHRASE not in sent:
                continue
            score_windows += 1

            # R2 — sinyal motorunun bilesenleri skora atfedilemez
            if RE_FOREIGN.search(sent) and not RE_EXCLUDED.search(sent):
                violations.append(
                    ("R2", path, "Supertrend/EMA skorun bileseni gibi aniliyor", sent[:180])
                )

            # R4 — bilesen sayiyorsa dordu birden
            probe = RE_MERGED.sub("hacim", sent)
            present = {k for k, rx in GROUPS.items() if rx.search(probe)}
            # >=3: gercek bir BILESEN LISTESI esigi. 2 grup tek-bilesen
            # cumlesinde de olusur (yasal.html: "hacim, ayri bir teyit/guc
            # bileseni olarak ... dahil edilir") — o bir liste iddiasi degil.
            if len(present) >= 3 and len(present) < 4:
                violations.append(
                    ("R4", path, "eksik bilesen: " + ",".join(sorted(set(GROUPS) - present)),
                     sent[:180])
                )

    # R5 — pozitif kontrol: hicbir sey cozumlenmediyse kapi kirilmistir
    if scanned_sent == 0 or score_windows == 0:
        print("✗ R5 POZITIF KONTROL: cozumlenen cumle=%d, skor penceresi=%d — kapi "
              "hicbir sey olcmedi." % (scanned_sent, score_windows))
        return 1

    if args.verbose:
        print("cozumlenen cumle: %d | '%s' gecen cumle: %d | dosya: %d"
              % (scanned_sent, PHRASE, score_windows, len(TARGETS)))

    if violations:
        for rule, path, why, sent in violations:
            print("✗ %s %s — %s" % (rule, path, why))
            print("    …%s…" % sent)
        print("\n%d ihlal." % len(violations))
        return 1

    if args.verbose:
        print("✓ ihlal yok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
