#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/tr-calendar-day-check.py — K-BD: TR TAKVIM GUNU KANONU

SORU: "Bugun hangi gun?" sorusu istemcide KAC farkli yoldan cevaplaniyor?

OLCULDU (21.09.2026, deploy oncesi yerel agac):
  * portfolio.html JSON disa aktarim  -> dosya adi `new Date().toISOString().slice(0,10)`
  * portfolio.html CSV  disa aktarim  -> ayni
  * tarama.html    CSV  disa aktarim  -> ayni
  `toISOString()` **UTC** gunudur. TR saatiyle 00:00-02:59 arasinda (UTC+3)
  indirilen dosya BIR ONCEKI gunun adini aliyordu; dosyanin ICINDEKI alis
  tarihleri ise TR takvimiyle yazildigi icin ad ile icerik celisiyordu.
  Ayni dosyada (portfolio.html) iki kanon yan yanaydi: yeni pozisyonun
  varsayilan tarihi Europe/Istanbul ile DOGRU turetilirken dosya adi UTC'den
  turuyordu -- "ayni is icin iki kanon" sinifi (K-BA/K-BB/K-BC ile ayni mercek).

KANON: gorunen her "bugun" degeri bp-format.js'teki `bpTodayTr()` /
  `bpTodayTrIso()`den turer. Bu dosya (static/bp-format.js) kanonun EVIDIR,
  taramanin disindadir.

IHLAL SINIFLARI (tabani SIFIR):
  A) UTC-GUN      -- `new Date()` + `.toISOString()` + tarih-dilimi (slice/substring/split)
  B) IKINCI KANON -- `Intl.DateTimeFormat(...).format(new Date())` kanon evi disinda
  C) YEREL-GUN    -- `new Date().getFullYear()/getMonth()/getDate()/getDay()`

MUAF: tam zaman damgasi (`new Date().toISOString()` tarih-dilimi YOK) -- makine
  ust verisi, Z son ekiyle belirsizlik tasimaz. Belirli bir tarihi BICIMLEME
  (`someDate.toLocaleDateString('tr-TR', {timeZone:...})`) de muaf: "bugun"
  turetmiyor, verilen tarihi gosteriyor.

OLCUM DISIPLINI: yorumlar SOYULUR (kendi aciklamam bulgu uretmesin), ve
POZITIF KONTROL calisir -- dedektor ihlali goremiyorsa sonuc "temiz" degil
"olculemedi"dir.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON_HOME = os.path.join('static', 'bp-format.js')

SCRIPT_RE = re.compile(r'<script\b[^>]*>(.*?)</script>', re.S | re.I)

# A) UTC gunu: new Date() -> toISOString() -> tarih dilimi
RE_UTC_DAY = re.compile(
    r'new\s+Date\s*\(\s*\)\s*\.\s*toISOString\s*\(\s*\)\s*\.\s*'
    r'(?:slice|substring|substr)\s*\(\s*0\s*,\s*10\s*\)'
    r'|new\s+Date\s*\(\s*\)\s*\.\s*toISOString\s*\(\s*\)\s*\.\s*split\s*\(')
# B) ikinci kanon: Intl ile bugun
RE_INTL_TODAY = re.compile(
    r'Intl\s*\.\s*DateTimeFormat\s*\([^)]*\)\s*\.\s*format\s*\(\s*new\s+Date\s*\(\s*\)\s*\)')
# C) yerel gun getter'lari
RE_LOCAL_DAY = re.compile(
    r'new\s+Date\s*\(\s*\)\s*\.\s*get(?:FullYear|Month|Date|Day)\s*\(')

CLASSES = (
    ('UTC-GUN', RE_UTC_DAY),
    ('IKINCI-KANON', RE_INTL_TODAY),
    ('YEREL-GUN', RE_LOCAL_DAY),
)


def strip_js_comments(src):
    """// ve /* */ yorumlarini bosluga cevirir (satir sayisi korunur)."""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in '"\'`':
            q = c
            out.append(c)
            i += 1
            while i < n:
                if src[i] == '\\' and i + 1 < n:
                    out.append('  ')
                    i += 2
                    continue
                out.append('\n' if src[i] == '\n' else src[i])
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            while i < n and not (src[i] == '*' and i + 1 < n and src[i + 1] == '/'):
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            out.append('  ')
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def js_chunks(path, text):
    """(baslangic_satiri, js_kaynak) listesi."""
    if path.endswith('.js'):
        return [(1, text)]
    chunks = []
    for m in SCRIPT_RE.finditer(text):
        chunks.append((text[:m.start(1)].count('\n') + 1, m.group(1)))
    return chunks


def scan_text(path, text):
    hits = []
    for base_line, src in js_chunks(path, text):
        clean = strip_js_comments(src)
        for label, rx in CLASSES:
            for m in rx.finditer(clean):
                line = base_line + clean[:m.start()].count('\n')
                snippet = src.splitlines()[line - base_line].strip() if 0 <= line - base_line < len(src.splitlines()) else ''
                hits.append((label, path, line, snippet[:120]))
    return hits


def targets():
    out = []
    for rel_dir in ('templates', 'static', os.path.join('static', 'js')):
        d = os.path.join(ROOT, rel_dir)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            if not (name.endswith('.html') or name.endswith('.js')):
                continue
            rel = os.path.relpath(p, ROOT)
            if rel == CANON_HOME:
                continue
            out.append((rel, p))
    return out


def main():
    files = targets()
    if not files:
        print('K-BD OLCULEMEDI: taranacak dosya bulunamadi.')
        return 2

    hits = []
    for rel, p in files:
        with open(p, encoding='utf-8') as fh:
            hits.extend(scan_text(rel, fh.read()))

    # POZITIF KONTROL — her sinif icin dedektor gercekten goruyor mu?
    probes = [
        ('UTC-GUN', "<script>var a = new Date().toISOString().slice(0,10);</script>"),
        ('IKINCI-KANON', "<script>var b = new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Istanbul'}).format(new Date());</script>"),
        ('YEREL-GUN', "<script>var c = new Date().getFullYear();</script>"),
    ]
    pos_ok = 0
    for label, probe in probes:
        found = [h for h in scan_text('__probe__.html', probe) if h[0] == label]
        if found:
            pos_ok += 1
        else:
            print('  ! POZITIF KONTROL DUSTU: %s yakalanamadi' % label)

    # NEGATIF KONTROL — muaf desenler bulgu URETMEMELI
    neg_probes = [
        "<script>var t = new Date().toISOString();</script>",                      # tam zaman damgasi
        "<script>var d = someDate.toLocaleDateString('tr-TR',{timeZone:'Europe/Istanbul'});</script>",
        "<script>/* new Date().toISOString().slice(0,10) — yorumda */</script>",   # yorum
    ]
    neg_ok = 0
    for probe in neg_probes:
        if not scan_text('__probe__.html', probe):
            neg_ok += 1
        else:
            print('  ! NEGATIF KONTROL DUSTU: muaf desen bulgu uretti -> %s' % probe[:70])

    print('tr-calendar-day-check (K-BD TR takvim gunu kanonu)')
    print('  taranan dosya: %d · kanon evi: %s (kapsam disi)' % (len(files), CANON_HOME))
    print('  pozitif kontrol: %d/%d · negatif kontrol: %d/%d'
          % (pos_ok, len(probes), neg_ok, len(neg_probes)))

    if pos_ok != len(probes) or neg_ok != len(neg_probes):
        print('K-BD OLCULEMEDI — dedektor kendi kontrolunu gecemedi (sonuc "temiz" DEGIL).')
        return 2

    if hits:
        print('K-BD IHLAL — "bugun" degeri kanon disi turetiliyor (%d):' % len(hits))
        for label, path, line, snippet in hits:
            print('  [%s] %s:%d  %s' % (label, path, line, snippet))
        print('  DUZELTME: bp-format.js -> bpTodayTrIso() (veya bpTodayTr()) kullan.')
        return 1

    print('  ✓ her "bugun" degeri bpTodayTr()/bpTodayTrIso() kanonundan turuyor')
    print('  ✓ tr-calendar-day-check PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
