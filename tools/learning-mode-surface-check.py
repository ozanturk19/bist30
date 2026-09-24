#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-DH (22.09.2026) — OGRENME MODU CAPASI OLAN HER SAYFA OZELLIGI YUKLUYOR MU?

Ogrenme Modu (SPEC-015) sozlukten tanim gosteren bir urun ozelligi: acik
iken `.jargon-term` capalarinin yanina "?" dugmesi enjekte edilir. Capayi
UC kaynak basar:
  * sablonda dogrudan `class="jargon-term"`,
  * `sigLabelTooltip()` (bp-vocab.js) -- HER sinyal cipini bununla sarar,
  * `bp-vocab.js`in kendisi (kanonik uretici).

CANLI OLCUM 22.09 (render SONRASI DOM, `document.querySelectorAll`):
  /tarama            433 capa · learning-mode.js VAR
  /hisse/THYAO         7 capa · VAR
  /metodoloji          1 capa · VAR
  /bilanco-takvimi    46 capa · YOK   <- "?" hic cikmiyordu
  /temettu-takvimi    28 capa · YOK   <-
  /karsilastir (2 hisse) 4 capa · YOK <-
  /portfolio     (pozisyon basina) · YOK
  /sektor-harita (sektor panelinde 3) · YOK

Yani kullanici /tarama'da Ogrenme Modu'nu aciyor, localStorage'a yaziliyor,
sonraki sayfada ozellik SESSIZCE yok oluyor. 141. dersin ozellik bicimi:
bir ozelligin ISARETI (capa) yayildi, MOTORU (betik) yayilmadi.

IKINCI BULGU (ayni turda, kodda): ozelligin TEK kontrolu
`@media (max-width:600px){header .bp-lm-toggle{display:none}}` ile
mobilde tamamen gizleniyordu -- telefonda Ogrenme Modu hic acilamiyordu.

OLCUT (taban SIFIR):

  R1  CAPA -> MOTOR: `.jargon-term` capasi basan her sablon
      learning-mode.js'i YUKLEMELI. Capa yazimlari: `class="jargon-term"`,
      `sigLabelTooltip(`. Yorumlar ve Jinja yorumlari SOYULUR (137. ders):
      dosya adini yorumda anmak ne capa ne yuklemedir.
  R2  MOTOR -> CAPA (bayat yukleme): learning-mode.js yukleyen sablonda hic
      capa yoksa girdi BAYAT demektir; ya capa silinmis ya betik gereksiz.
      metodoloji.html muaf DEGIL -- orada da capa var.
  R3  KONTROL HER KIRILMA NOKTASINDA ULASILABILIR: `.bp-lm-toggle`i
      `display:none` yapan bir kural ANCAK yerine gecen bir varyant
      (`createToggleButton('sheet')`, mobil menu karti) MOUNT EDILIYORSA
      mesrudur; o varyant da gizliyse ihlal. "Gizlemek" ile "tasimak"
      farkli seylerdir -- kapi ikincisini SUBSTITUTE VARLIGINA baglar.
      320px olcumu bunu zorunlu kildi: baslikta daraltilmis cip bile
      `bp-refresh-btn`i ekran disina itiyordu.
  R4  SOZLUK CAPALI: GLOSSARY'deki her anahtar en az bir `data-term` ile
      ulasilabilir olmali (K-CA/K-CH'nin olu anahtar sinifi) -- bu kural
      UYARI uretir, FAIL degil: terim ekranda cikmadan once sozluge
      yazilabilir (sira serbest), ama olu kalmasi izlenmeli.
  R5  KAPSAM TABANI: en az 6 capa basan sablon gorulmeli.

Kullanim:
  python3 tools/learning-mode-surface-check.py [--verbose]
  python3 tools/learning-mode-surface-check.py --ref SHA
  python3 tools/learning-mode-surface-check.py --self-test
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = 'learning-mode.js'
MIN_ANCHOR_TEMPLATES = 3  # C-11 (24.09): sinyal rozeti capasi kalkti, 5 sayfa motoru birakti

RE_ANCHOR = re.compile(r'class="[^"]*\bjargon-term\b|sigLabelTooltip\s*\(')
RE_ENGINE_TAG = re.compile(r'src="/static/' + re.escape(ENGINE) + r'\?')
RE_HIDE_TOGGLE = re.compile(r'\.bp-lm-toggle\s*\{[^}]*display\s*:\s*none')
# Dar ekranda baslik varyanti gizlenebilir -- AMA yalnizca baska bir varyant
# MOUNT EDILIYORSA. "Kontrolu gizlemek" ile "kontrolu tasimak" farkli seylerdir;
# kapi ikincisini bir SUBSTITUTE VARLIGI sartina baglar (K-DH, 151. ders).
RE_SHEET_MOUNT = re.compile(r"createToggleButton\s*\(\s*'sheet'\s*\)")
RE_SHEET_HIDDEN = re.compile(r'\.bp-lm-sheet[^{]{0,40}\{[^}]*display\s*:\s*none')


def strip_comments(src):
    """HTML yorumu, Jinja yorumu ve JS // /* */ yorumlarini bosluga cevirir."""
    src = re.sub(r'<!--.*?-->', lambda m: ' ' * len(m.group(0)), src, flags=re.S)
    src = re.sub(r'\{#.*?#\}', lambda m: ' ' * len(m.group(0)), src, flags=re.S)
    src = re.sub(r'/\*.*?\*/', lambda m: ' ' * len(m.group(0)), src, flags=re.S)
    src = re.sub(r'(?m)^\s*//.*$', lambda m: ' ' * len(m.group(0)), src)
    return src


def scan(read, listdir):
    viol, warn = [], []
    anchors, engines = [], []

    for fn in sorted(listdir('templates')):
        if not fn.endswith('.html'):
            continue
        rel = 'templates/' + fn
        raw = read(rel)
        if raw is None:
            continue
        clean = strip_comments(raw)
        has_anchor = bool(RE_ANCHOR.search(clean))
        has_engine = bool(RE_ENGINE_TAG.search(clean))
        if has_anchor:
            anchors.append(fn)
        if has_engine:
            engines.append(fn)
        if has_anchor and not has_engine:
            viol.append((rel, 'R1', 'jargon capasi basiyor ama %s yuklenmiyor' % ENGINE))
        if has_engine and not has_anchor:
            viol.append((rel, 'R2', '%s yukluyor ama hic jargon capasi yok (bayat yukleme)' % ENGINE))

    js = read('static/' + ENGINE)
    if js is None:
        viol.append(('static/' + ENGINE, 'R3', 'motor dosyasi yok'))
        js = ''
    js_clean = strip_comments(js)
    if RE_HIDE_TOGGLE.search(js_clean):
        if not RE_SHEET_MOUNT.search(js_clean):
            viol.append(('static/' + ENGINE, 'R3',
                         'kontrol (.bp-lm-toggle) display:none ediliyor ama YERINE gecen '
                         'bir varyant mount EDILMIYOR -- o genislikte ozellik yok demektir'))
        elif RE_SHEET_HIDDEN.search(js_clean):
            viol.append(('static/' + ENGINE, 'R3',
                         'yerine gecen varyant (.bp-lm-sheet) de display:none -- '
                         'iki kontrol de gizli'))

    # R4 — olu sozluk anahtari (UYARI)
    keys = set()
    m = re.search(r'var GLOSSARY\s*=\s*\{', js_clean)
    if m:
        depth, i = 0, m.end() - 1
        while i < len(js_clean):
            if js_clean[i] == '{':
                depth += 1
            elif js_clean[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        keys = set(re.findall(r"'([^']+)'\s*:", js_clean[m.end():i]))
    terms = set()
    for d in ('templates', 'static'):
        for fn in sorted(listdir(d)):
            if not fn.endswith(('.html', '.js')):   # ikili varliklar (png/ico/woff) atlanir
                continue
            raw = read(d + '/' + fn)
            if raw is None or not isinstance(raw, str):
                continue
            terms |= set(re.findall(r'data-term="([^"]*)"', strip_comments(raw)))
    dead = sorted(keys - terms)
    if dead:
        warn.append('sozlukte capasiz (olu) anahtar: ' + ', '.join(dead))

    return viol, warn, anchors, engines


def fs_reader(base):
    def read(rel):
        p = os.path.join(base, rel)
        if not os.path.isfile(p):
            return None
        try:
            return io.open(p, encoding='utf-8').read()
        except UnicodeDecodeError:
            return None

    def listdir(rel):
        p = os.path.join(base, rel)
        return os.listdir(p) if os.path.isdir(p) else []
    return read, listdir


def git_reader(ref):
    def read(rel):
        try:
            return subprocess.check_output(['git', 'show', '%s:%s' % (ref, rel)],
                                           cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8')
        except (subprocess.CalledProcessError, UnicodeDecodeError):
            return None

    def listdir(rel):
        try:
            return subprocess.check_output(['git', 'ls-tree', '--name-only', '%s:%s' % (ref, rel)],
                                           cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8').split()
        except subprocess.CalledProcessError:
            return []
    return read, listdir


def self_test():
    cases = [
        ('dogrudan capa', '<a class="jargon-term" data-term="adx">ADX</a>', True),
        ('sigLabelTooltip capasi', "h += sigLabelTooltip(s.signal);", True),
        ('HTML yorumundaki capa', '<!-- <a class="jargon-term">x</a> -->', False),
        ('Jinja yorumundaki capa', '{# sigLabelTooltip( #}', False),
        ('JS blok yorumundaki capa', '/* sigLabelTooltip( kullanilir */', False),
        ('ilgisiz metin', '<div class="jargon">x</div>', False),
    ]
    hit = 0
    for desc, src, expect in cases:
        got = bool(RE_ANCHOR.search(strip_comments(src)))
        ok = got == expect
        hit += ok
        print("   %s %s" % ('✓' if ok else '✗', desc))
    hide_cases = [
        ('gizleme + YEDEK YOK -> ihlal',
         "'@media (max-width:600px){header .bp-lm-toggle{display:none}}'", True),
        ('gizleme + sheet varyanti mount -> ihlal DEGIL',
         "'@media (max-width:600px){header .bp-lm-toggle{display:none}}' ; createToggleButton('sheet')", False),
        ('gizleme + sheet mount AMA sheet de gizli -> ihlal',
         "'header .bp-lm-toggle{display:none}' ; '.bp-lm-sheet{display:none}' ; createToggleButton('sheet')", True),
        ('yalniz padding daraltmasi', "'@media (max-width:600px){header .bp-lm-toggle{padding:6px 8px}}'", False),
        ('etiket gizleme (kontrol duruyor)', "'header .bp-lm-toggle .bp-lm-label{display:none}'", False),
    ]
    for desc, src, expect in hide_cases:
        c = strip_comments(src)
        got = bool(RE_HIDE_TOGGLE.search(c)) and (
            not RE_SHEET_MOUNT.search(c) or bool(RE_SHEET_HIDDEN.search(c)))
        ok = got == expect
        hit += ok
        print("   %s %s" % ('✓' if ok else '✗', desc))
    return hit, len(cases) + len(hide_cases)


def main():
    if '--self-test' in sys.argv:
        hit, tot = self_test()
        print("learning-mode-surface-check --self-test: %d/%d" % (hit, tot))
        return 0 if hit == tot else 2

    if '--ref' in sys.argv:
        read, listdir = git_reader(sys.argv[sys.argv.index('--ref') + 1])
        label = 'ref ' + sys.argv[sys.argv.index('--ref') + 1]
        gated = False
    else:
        read, listdir = fs_reader(ROOT)
        label = 'calisan agac'
        gated = True

    viol, warn, anchors, engines = scan(read, listdir)
    print("learning-mode-surface-check (K-DH Ogrenme Modu yuzey envanteri) — %s" % label)
    print("  capa basan sablon: %d · motoru yukleyen: %d" % (len(anchors), len(engines)))
    if '--verbose' in sys.argv:
        print("    capa: %s" % ', '.join(anchors))
        print("    motor: %s" % ', '.join(engines))
    for w in warn:
        print("  ⚠ %s" % w)
    if gated and len(anchors) < MIN_ANCHOR_TEMPLATES:
        print("  ✗ kapsam tabani altinda (%d/%d) — dedektor korlesmis" % (len(anchors), MIN_ANCHOR_TEMPLATES))
        return 2
    if viol:
        print("  ✗ %d ihlal:" % len(viol))
        for f, rule, why in viol:
            print("      · %-32s %-4s %s" % (f, rule, why))
        return 1
    print("  ✓ capa basan her sablon motoru yukluyor, kontrol her genislikte ulasilabilir")
    return 0


if __name__ == '__main__':
    sys.exit(main())
