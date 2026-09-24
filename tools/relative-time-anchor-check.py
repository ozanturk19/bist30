#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-CD (22.09.2026) — GORELI ZAMAN SOZCUGU OKUYUCUNUN TAKVIMINE BAGLIDIR.

"Bugun" / "Dun" / "Yarin" **indexical** sozcuklerdir: anlamlarini sayfayi
OKUYAN kisinin takviminden alirlar. Bir sayfa bu sozcugu baska bir referans
gune (arsiv gunu, anlik goruntu gunu, son islem gunu) gore uretirse, ortaya
sessiz degil GORUNUR bir yalan cikar -- ustelik cogu zaman mutlak tarihin
tam yaninda, AYNI OGENIN icinde.

22.09 CANLI OLCUM:
  · /ozet (otomatik son-islem-gunu geri donusu, gun icinde ~17 saat bu
    durumda): hisse kartlari **"Bugun · 21.09.2026"** basiyordu -- okuyucunun
    takviminde 22.09.2026. **21 kart**, canli.
  · /ozet/2026-09-18 (acik arsiv): **"Bugun · 18.09.2026" x7** ve
    **"Dun · 17.09.2026" x4**.
  · Sayfanin geri kalani arsiv modunda MUTLAK tarihe cevrilmisti (baslik,
    "... olustu" cipi, ust bant, <title>, meta) -- YALNIZ bu iki satir
    (ozet.html:245,272) atlanmisti: `signal_age_text(historical_date)`.

UC EKSEN:
  A1 JINJA: goreli-yas filtresine REFERANS GUN argumani verilmesi
     (`|signal_age_text(x)`, `|signal_age_phrase(x)`, `|signal_date_label(x)`).
     Yas HER YERDE okuyucunun bugununden hesaplanir; mutlak tarih zaten
     yaninda basili oldugu icin arsiv cercevesi kaybolmaz.
  A2 DAL: bir REFERANS-GUN degiskeninin DOGRU dalinda indexical sozcuk
     literali ({% if historical_date %}...Bugun...{% endif %}). Sozcuk
     listesi bu dosyada sabit (Bugun/Dun/Yarin).
  A3 JS: bpSignalDateLabel/bpSignalDateKey/bpSignalAge*'e IKINCI argument
     (referans gun) gecirilmesi -- ayni yeniden-capalama, JS yazimi.
     (⛔67. ders: bir kanonun SSR ve JS yazimi AYRI iki yazimdir.)

Kullanim:
  python3 tools/relative-time-anchor-check.py
  python3 tools/relative-time-anchor-check.py --ref SHA
"""
import os, re, sys, io, subprocess, tempfile, tarfile

AGE_FILTERS = ('signal_age_text', 'signal_age_phrase', 'signal_date_label')
JS_FNS      = ('bpSignalDateLabel', 'bpSignalDateKey', 'bpSignalAgeShort', 'bpSignalAgeText')

# Referans-gun degiskeni: arsiv/anlik-goruntu gunu tasiyan her ad.
REFVAR = re.compile(
    r"\b\w*(?:historical|archive|arsiv|arşiv|snapshot|gecmis|geçmiş|as_of|asof|ref_date)\w*\b",
    re.IGNORECASE)

# A1: |filtre(ARG)  -- bos parantez `()` serbest, argumanli olan yasak.
A1 = re.compile(r"\|\s*(" + "|".join(AGE_FILTERS) + r")\s*\(\s*([^)\s][^)]*)\)")

# A3: fn(a, b) -- ikinci argument.
A3 = re.compile(r"\b(" + "|".join(JS_FNS) + r")\s*\(([^()]*)\)")

JINJA_TAG = re.compile(r"\{%-?\s*(if|elif|else|endif)\b([^%]*?)-?%\}", re.S)


def indexical_words(root):
    """Indexical sozcukler: kanon goreli gun adini yasakladi (C-62), etiket artik
    takvim tarihi; kapi yine de arsiv gunu dalinda bu sozcuklerin donmesini
    yakalar. Sozcukler burada sabit (business_rules'ta artik kanon sozlugu yok)."""
    return sorted({'Bugün', 'Dün', 'Yarın'})


def true_branch_spans(text):
    """{% if <refvar> %} ... {% else %} bloklarinin DOGRU dal araliklari.

    `not <refvar>` icin dal ters cevrilir (yasak bolge else tarafidir).
    """
    spans, stack = [], []
    for m in JINJA_TAG.finditer(text):
        kind, cond = m.group(1), (m.group(2) or '').strip()
        if kind == 'if':
            is_ref = bool(REFVAR.search(cond))
            negated = bool(re.match(r"not\s", cond)) or ' not ' in cond
            stack.append({'ref': is_ref, 'neg': negated,
                          'start': m.end(), 'depth': len(stack)})
        elif kind in ('elif', 'else') and stack:
            top = stack[-1]
            if top['ref'] and top.get('start') is not None:
                if not top['neg']:
                    spans.append((top['start'], m.start()))
                top['start'] = None
            if kind == 'else' and top['ref'] and top['neg']:
                top['start'] = m.end()       # yasak bolge: else dali
        elif kind == 'endif' and stack:
            top = stack.pop()
            if top['ref'] and top.get('start') is not None:
                spans.append((top['start'], m.start()))
    return spans


def scan_tree(root):
    bad, words = [], indexical_words(root)
    for base in ('templates', 'static'):
        d = os.path.join(root, base)
        for dp, _, fns in os.walk(d):
            for fn in fns:
                if not fn.endswith(('.html', '.js')):
                    continue
                path = os.path.join(dp, fn)
                rel = os.path.relpath(path, root)
                src = io.open(path, encoding='utf-8', errors='replace').read()
                # yorumlari dusur: kural METNI ihlal sayilmasin (⛔52. ders'in tersi
                # degil -- burada aranan sey CALISAN ifade, aciklama degil)
                clean = re.sub(r"\{#.*?#\}", lambda m: re.sub(r"[^\n]", " ", m.group()),
                               src, flags=re.S)
                clean = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group()),
                               clean, flags=re.S)
                clean = re.sub(r"(?m)^\s*(//|\*|/\*).*$",
                               lambda m: " " * len(m.group()), clean)
                ln = lambda i: clean.count('\n', 0, i) + 1

                for m in A1.finditer(clean):
                    bad.append((rel, ln(m.start()), 'A1',
                                f"`|{m.group(1)}({m.group(2).strip()})` — goreli yas "
                                f"OKUYUCUNUN bugununden hesaplanmali; referans-gun "
                                f"argumani \"Bugun/Dun\"u baska bir gune capalar"))

                for s, e in true_branch_spans(clean):
                    seg = clean[s:e]
                    for w in words:
                        for k in re.finditer(r"(?<![\w>])" + re.escape(w) + r"(?![\w])", seg):
                            bad.append((rel, ln(s + k.start()), 'A2',
                                        f"referans-gun dalinda \"{w}\" literali — "
                                        f"arsiv/anlik-goruntu gunu okuyucunun bugunu DEGIL"))

                for m in A3.finditer(clean):
                    args = m.group(2)
                    if args.count(',') >= 1 and args.strip():
                        bad.append((rel, ln(m.start()), 'A3',
                                    f"`{m.group(1)}(…, …)` — ikinci argument referans "
                                    f"gundur; goreli etiket yeniden capalanamaz"))
    return bad


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='reltime-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    return d


def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    root = tree_at_ref(ref) if ref else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = scan_tree(root)
    tag = ' (ref ' + ref + ')' if ref else ''
    if not bad:
        print(f"K-CD OK — goreli zaman sozcukleri okuyucunun takvimine bagli{tag}.")
        return 0
    print(f"K-CD KIRIK — {len(bad)} ihlal{tag}:")
    for rel, l, kind, msg in sorted(bad):
        print(f"  [{kind}] {rel}:{l}  {msg}")
    print("\n  Kural: \"Bugun/Dun/Yarin\" SADECE okuyucunun takvimine gore yazilir.")
    print("         Arsiv/anlik-goruntu yuzeyi MUTLAK tarih basar (ozet.html:218,228).")
    return 1


if __name__ == '__main__':
    sys.exit(main())
