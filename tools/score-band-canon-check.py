#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAPI 68 -- K-CW: TEKNIK GUC SKORU'NUN BANT KANONU (renk + ad) TEK KAYNAKTAN MI?

Kusur (22.09 canli olculdu):
  Ayni sayi (Teknik Guc Skoru) sitede IKI ayri renk sozlugune gore boyaniyordu.
    * /tarama scoreCell() ve /hisse skor halkasi ve /karsilastir TIER_META:
      kanonik `tier` alanindan (app.py _derive_tier) -> guclu_sinyal = mor
      (--bp-premium), standart = periwinkle (--bp-brand), rozet-yok = notr.
    * index.html scoreColorVar(): HAM SKORU 70/56 esigine sokup
      --bp-al / --bp-volume / --bp-sat donduruyordu.
  Olcum (22.09 canli, getComputedStyle):
    ENERY 72  anasayfa rgb(0,226,144) yesil   <-> /tarama rgb(168,85,247) mor
    TUPRS 62  anasayfa rgb(255,200,80) turuncu <-> /tarama rgb(184,195,255) mavi
    AYGAZ 49  anasayfa rgb(248,81,73) KIRMIZI  <-> /tarama rgb(144,144,151) gri
    BIMAS 43  anasayfa rgb(248,81,73) KIRMIZI  <-> /tarama rgb(144,144,151) gri
    4/4 uyusmazlik. Dahasi --bp-sat SAT sinyalinin kanonik rengi: "en yuksek
    skorlar" izgarasinda 7 karttan 3'u KIRMIZI halka + YESIL "Guclu Trend"
    rozeti tasiyordu (ayni kartta iki zit renk-anlam).
  Ve bant ADLARI ucuncu bir kanondu: anasayfa lejanti "Guclu / Orta / Zayif",
  kanonik adlar (/metodoloji, /tarama, /karsilastir) "Yuksek Skor / Orta Skor /
  rozetsiz". "Guclu" ayni sayfada AL sinyalinin adiydi ("Guclu Trend") ve ayni
  rengi tasiyordu -- CPO-1682'nin yasakladigi tam cakisma.

Kurallar:
  R1  `guclu_sinyal` / `standart` literaline dallanan her RENK atamasi kanonik
      sozlukten olmali (guclu_sinyal -> --bp-premium, standart -> --bp-brand;
      CSS sinif adlari beyaz listede).
  R2  Teknik Guc Skoru bandi HAM SKOR esiginden turetilemez: ayni fonksiyon
      govdesinde `56` esigi + renk donusu = tier kanonunu atlayan ikinci sozluk.
      (56 bu skora ozgudur; BorsaPusula/saglik skoru kanonik bandi 70/50'dir.)
  R3  Kullaniciya gorunen bant adi kanonik olmali. Skor bandi baglaminda
      "Guclu Sinyal" (CPO-1682 isim cakismasi) ve renk kutusuyla birlikte
      kullanilan "Guclu"/"Zayif" bant adlari yasak.

Kullanim:
  python3 tools/score-band-canon-check.py            # calisan agac
  python3 tools/score-band-canon-check.py --self-test
  python3 tools/score-band-canon-check.py --ref 9d347bf
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    'templates/index.html', 'templates/tarama.html', 'templates/hisse.html',
    'templates/karsilastir.html', 'templates/metodoloji.html',
    'templates/sektor_harita.html', 'templates/bilanco_takvimi.html',
    'templates/temettu_takvimi.html',
]

CANON = {'guclu_sinyal': '--bp-premium', 'standart': '--bp-brand'}
# tarama.html tier -> CSS sinif adlari (renk CSS'te, token degil): ic isimlendirme,
# kullaniciya gorunmez (CPO-DEV2-053/055 notu). Beyaz liste SATIR NUMARASI DEGIL,
# ifadenin kendisi (K-BD dersi: beyaz liste anahtari satir numarasi olamaz).
CLASS_ALIAS = {'guclu_sinyal': {'premium'}, 'standart': {'plus'}}
COLOR_TOKEN = re.compile(r'--bp-(?:premium|brand|al|sat|volume|text3|bkl)\b')
BANNED_BAND = re.compile(r'Güçlü\s+Sinyal', re.I)
# renk kutusu (lejant swatch) ile ayni satirda bant adi
SWATCH_LINE = re.compile(r'class="sw"')
BAND_WORD = re.compile(r'\b(Güçlü|Zayıf)\b')


def strip_comments(text):
    """Jinja {# #}, HTML <!-- -->, JS // ve /* */ yorumlarini bosluga cevirir
    (satir sayisi korunur). Ders: iddia olusturulmus metinde yasar."""
    def blank(m):
        return re.sub(r'[^\n]', ' ', m.group(0))
    text = re.sub(r'\{#.*?#\}', blank, text, flags=re.S)
    text = re.sub(r'<!--.*?-->', blank, text, flags=re.S)
    text = re.sub(r'/\*.*?\*/', blank, text, flags=re.S)
    text = re.sub(r'(?m)^\s*//.*$', blank, text)
    text = re.sub(r'(?m)(?<=[;,\)\}])\s*//[^\n"\']*$', blank, text)
    return text


def split_bodies(text):
    """(baslangic_satiri, govde) -- kaba fonksiyon/makro bloklari."""
    lines = text.split('\n')
    out, cur, start = [], [], 1
    for i, ln in enumerate(lines, 1):
        if re.search(r'\b(function\s+\w+\s*\(|=>\s*\{|\{%-?\s*macro\b)', ln):
            if cur:
                out.append((start, '\n'.join(cur)))
            cur, start = [ln], i
        else:
            cur.append(ln)
    if cur:
        out.append((start, '\n'.join(cur)))
    return out


def check_text(path, raw):
    v = []
    text = strip_comments(raw)
    lines = text.split('\n')

    # --- R1: tier literaline dallanan renk atamasi ---
    for i, ln in enumerate(lines, 1):
        for tier, want in CANON.items():
            if "'%s'" % tier not in ln and '"%s"' % tier not in ln:
                continue
            # dalin hemen sagindaki ilk renk/sinif ifadesi
            seg = ln.split(tier, 1)[1]
            seg = seg.split(':', 1)[0] if ':' in seg[:140] else seg[:140]
            toks = COLOR_TOKEN.findall(seg)
            if toks:
                got = '--bp-' + toks[0].split('--bp-')[-1] if False else toks[0]
                if got != want:
                    v.append((path, i, 'R1',
                              "tier '%s' dali %s veriyor, kanon %s" % (tier, got, want)))
                continue
            alias = CLASS_ALIAS.get(tier, set())
            if alias and any(("'%s'" % a) in seg or ('"%s"' % a) in seg for a in alias):
                continue
            # renk de sinif da yoksa bu dal renklendirme yapmiyordur -- sessiz gec

    # --- R2: ham skor esiginden bant rengi ---
    for start, body in split_bodies(text):
        if not re.search(r'>=\s*56\b', body):
            continue
        if not COLOR_TOKEN.search(body):
            continue
        off = body.split('\n')
        hit = next((k for k, l in enumerate(off) if re.search(r'>=\s*56\b', l)), 0)
        v.append((path, start + hit, 'R2',
                  "56 esigi + renk donusu: Teknik Guc Skoru bandi ham skordan "
                  "turetilmis (kanon: tier alani)"))

    # --- R3: bant adi ---
    for i, ln in enumerate(lines, 1):
        if BANNED_BAND.search(ln):
            v.append((path, i, 'R3', "'Guclu Sinyal' bant adi yasak (CPO-1682: "
                                     "'Sinyal' yalniz YON icin) -- kanon 'Yuksek Skor'"))
        if SWATCH_LINE.search(ln):
            m = BAND_WORD.search(ln)
            if m:
                v.append((path, i, 'R3',
                          "renk kutusuyla birlikte '%s' bant adi -- kanonik adlar "
                          "'Yuksek Skor / Orta Skor / Rozetsiz'" % m.group(1)))
    return v


def read_ref(ref, path):
    try:
        return subprocess.check_output(['git', 'show', '%s:%s' % (ref, path)],
                                       cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8')
    except subprocess.CalledProcessError:
        return None


def run(ref=None):
    v = []
    for p in TARGETS:
        raw = read_ref(ref, p) if ref else (
            open(os.path.join(ROOT, p), encoding='utf-8').read()
            if os.path.exists(os.path.join(ROOT, p)) else None)
        if raw is None:
            continue
        v += check_text(p, raw)
    return v


SELF = [
    # (ad, govde, beklenen_kural)
    ("R1 yanlis renk",
     "const c = tier === 'guclu_sinyal' ? 'var(--bp-al)' : 'var(--bp-text3)';", 'R1'),
    ("R1 standart yanlis",
     "if (tier === 'standart') return 'var(--bp-volume)';", 'R1'),
    ("R2 ham skor bandi",
     "function f(v){\n if (v >= 70) return 'var(--bp-al)';\n if (v >= 56) return 'var(--bp-volume)';\n return 'var(--bp-sat)';\n}", 'R2'),
    ("R3 eski bant adi",
     '<div class="da-legend-item"><span class="sw" style="background:var(--bp-al)"></span>70–100 Güçlü</div>', 'R3'),
    ("R3 Guclu Sinyal",
     '<span class="score-verdict">Güçlü Sinyal</span>', 'R3'),
    ("NEGATIF: kanonik kod ihlal DEGIL",
     "const c = tier === 'guclu_sinyal' ? 'var(--bp-premium)' : tier === 'standart' ? 'var(--bp-brand)' : 'var(--bp-text3)';", None),
    ("NEGATIF: yorumdaki kusur sayilmaz",
     "// eski hali: tier === 'guclu_sinyal' ? 'var(--bp-al)' : x  -- Güçlü Sinyal\nconst c = 'var(--bp-premium)';", None),
]


def self_test():
    ok = 0
    for name, body, want in SELF:
        got = check_text('<self>', body)
        rules = {g[2] for g in got}
        good = (want in rules) if want else (not got)
        print('  %s %s%s' % ('PASS' if good else 'FAIL', name,
                             '' if good else '  -> %s' % sorted(rules)))
        ok += 1 if good else 0
    print('self-test %d/%d' % (ok, len(SELF)))
    return ok == len(SELF)


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    viol = run(ref)
    if viol:
        print('KAPI 68 (K-CW) -- %d ihlal%s:' % (len(viol), ' [%s]' % ref if ref else ''))
        for p, i, r, m in viol:
            print('  %s:%s  [%s] %s' % (p, i, r, m))
        sys.exit(1)
    print('KAPI 68 (K-CW) PASS -- skor bant kanonu tek kaynaktan%s.' % (' [%s]' % ref if ref else ''))
    sys.exit(0)
