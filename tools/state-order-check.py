#!/usr/bin/env python3
"""
K-G  DURUM KURALI VARYANTININ ALTINDA KALIYOR — BLOKLAYICI, taban SIFIR
      (CPO, 20.09.2026)

NEDEN AYRI BIR KAPI: `:hover` bir SOZDE-SINIFTIR, yani `.a:hover` ile `.a.b`
OZGULLUK BAKIMINDAN ESITTIR (0,2,0). Esitlikte karari KAYNAK SIRASI verir.
Bu yuzden bir durum kurali (hover/focus/active) ayni ogenin varyant
bilesiklerinden ONCE yazilirsa, varyantin da tanimladigi her ozellik icin
durum kurali SESSIZCE OLUR — ne tarayici uyarir, ne mevcut kapilardan biri
gorur, ne de grep "kural var" demekten oteye gider.

20.09'da olculen gercek bedel (fix 443d0c5): /bilanco-takvimi ve
/temettu-takvimi'nde `.stock-card:hover{border-color:var(--bp-brand)}` kurali
`.stock-card.sig-al`/`.sig-sat` bilesiklerinin USTUNDE duruyordu -> marka
rengi hover cercevesi 46 kartin 29'unda ve 28 kartin 4'unde HIC uygulanmadi.
Ironi: yalnizca RENKSIZ kartlarda calisiyordu.

K-A/K-F ile ayni kusur sinifi: yazili bir sozlesme calistigi SANILIYOR.

YANLIS-POZITIF SAVUNMALARI (uc tanesi mekanik, biri belgeli):
  1. Varyantin KENDI durum kurali varsa (`.a.b:hover`, 0,3,0) atlanir —
     affordance korunuyor demektir (ornek: portfolio `.btn-action.danger`).
  2. Iki kural AYNI OGEYI hedeflemiyorsa atlanir: karsilastirma seciciNIN
     OZNESI (son bilesik) uzerinden yapilir, ata zinciri ayrica eslesmeli
     (ornek: `.gauge:hover` vs `.gauge .gauge-ring` — farkli ogeler).
  3. Sonraki kural o ozelligi `!important` ile yaziyorsa atlanir: yazar
     kasitli olarak durum kuralini eziyor (ornek: makro seridin
     `[data-paused="true"]` duraklatmasi hover duraklatmasini ezmeli).
  4. Ikisi de DURUM ise cakisma degil, oncelik siralamasidir
     (`:hover` vs `:disabled`) — atlanir.
  5. GOZDEN GECIRILMIS_KASITLI: "secili/aktif gorunum hover'i ezsin"
     karari mesru bir tasarim tercihidir, ama SESSIZ kalmamali — bu tur her
     cift asagida GEREKCESIYLE listelenir. Listede olmayan yeni bir cift
     kapiyi kirar; karar ya kural sirasini duzeltmek ya da buraya
     gerekce yazmaktir.

Kullanim:  python3 tools/state-order-check.py [--verbose]
"""
import re, sys, pathlib

# Varyantin durum kuralini ezmesinin KASITLI oldugu, gozden gecirilmis ciftler.
# Bicim: (dosya, durum-secici, sonraki-secici): gerekce
GOZDEN_GECIRILMIS_KASITLI = {
  ('static/css/pages/hisse.css', '.hib-action-btn:hover', '.hib-action-btn.active-portfolio'):
    'Portfoyde/bildirimi acik durum rozet gibi okunuyor; hover onu silmemeli. '
    'Butonun tiklanabilirligi imlecten (cursor:pointer) ve :active svg '
    'kuculmesinden anlasiliyor.',
  ('static/css/pages/hisse.css', '.hib-action-btn:hover', '.hib-action-btn.active-bell'):
    'Ayni gerekce (bkz. active-portfolio).',
  ('static/css/pages/profil.css', '.opt:hover', '.opt.selected'):
    'Secili secenek gorunumu hover ile bulanmamali — secim geri bildirimi '
    'hover geri bildiriminden onceliklidir.',
  ('static/css/pages/sektor_harita.css', '.sekt-tab-btn:hover', '.sekt-tab-btn.active'):
    'Aktif sekme gorunumu korunur (standart sekme davranisi).',
  ('static/css/pages/sektor_harita.css', '.chip:hover', '.chip.sel-1'):
    'Secili karsilastirma cipinin kimlik rengi hover ile degismemeli.',
  ('static/css/pages/sektor_harita.css', '.chip:hover', '.chip.sel-2'):
    'Ayni gerekce (bkz. sel-1).',
  ('static/css/pages/sektor_harita.css', '.chip:hover', '.chip.sel-3'):
    'Ayni gerekce (bkz. sel-1).',
  ('static/css/shared.css', '.mbn-sheet-item:active', '.mbn-sheet-item.active'):
    'Mobil sayfada bulundugun satirin isaretli gorunumu, basili-tutma geri '
    'bildiriminden onceliklidir.',
}

DURUM = re.compile(r':(hover|focus|focus-visible|focus-within|active|visited|target)\b')
# Sozde-sinif ama DURUM degil: bunlar da bir "durum" gibi davranir (oncelik siralamasi)
DIGER_DURUM = re.compile(r':(disabled|enabled|checked|indeterminate|placeholder-shown|read-only|invalid|valid|required)\b')

KISAYOL = {
  'border':     {'border-color','border-width','border-style'},
  'background': {'background-color','background-image'},
  'outline':    {'outline-color','outline-width','outline-style'},
  'font':       {'font-size','font-weight','font-family','font-style'},
  'margin':     {'margin-top','margin-right','margin-bottom','margin-left'},
  'padding':    {'padding-top','padding-right','padding-bottom','padding-left'},
}

def genislet(p):
    out = {p}
    for k, v in KISAYOL.items():
        if p == k: out |= v
        if p in v: out.add(k)
    return out

def ozgulluk(sel):
    """(id, sinif-benzeri, tip). Sozde-sinif = sinif; sozde-oge = tip."""
    s = sel
    pe = len(re.findall(r'::[a-z-]+', s))
    s = re.sub(r'::[a-z-]+', '', s)
    ids = len(re.findall(r'#[\w-]+', s))
    cls = (len(re.findall(r'\.[\w-]+', s)) + len(re.findall(r'\[[^\]]+\]', s))
           + len(re.findall(r':(?!:)(?!not\(|is\(|where\()[a-z-]+(?:\([^)]*\))?', s)))
    typ = len(re.findall(r'(?:^|[\s>+~])([a-z][\w-]*)', s)) + pe
    return (ids, cls, typ)

def bilesenler(sel):
    """Seciciyi bilesenlere ayirir (' ', '>', '+', '~' birlestiricilerinde)."""
    return [c for c in re.split(r'\s*[>+~]\s*|\s+', sel.strip()) if c]

def sinif_kumesi(bilesen):
    return frozenset(re.findall(r'\.[\w-]+', bilesen))

def ozne_ayni_oge(a, b):
    """Iki secici AYNI OGEYI mi hedefliyor? Ozne (son bilesen) sinif kumesi
    alt-kume olmali VE ata zinciri birebir eslesmeli."""
    ba, bb = bilesenler(a), bilesenler(b)
    if len(ba) != len(bb): return False
    # atalar: sozde-siniflar atilarak birebir
    tem = lambda c: re.sub(r':(?!:)[a-z-]+(?:\([^)]*\))?', '', c)
    for x, y in zip(ba[:-1], bb[:-1]):
        if tem(x) != tem(y): return False
    sa, sb = sinif_kumesi(tem(ba[-1])), sinif_kumesi(tem(bb[-1]))
    return bool(sa) and sa <= sb

def bildirimler(body):
    """{ozellik: important_mi}"""
    out = {}
    for decl in re.split(r';(?![^(]*\))', body):
        if ':' not in decl: continue
        ad, deger = decl.split(':', 1)
        ad = ad.strip().lower()
        if not ad or ad.startswith('--') or ' ' in ad: continue
        imp = '!important' in deger.lower()
        for p in genislet(ad):
            out[p] = out.get(p, False) or imp
    return out

def kurallar(text):
    """Kaba CSS ayristirici; @media/@supports baglamini korur."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    out, i, n, kosul, buf = [], 0, len(text), [], ''
    while i < n:
        ch = text[i]
        if ch == '{':
            head = buf.strip(); buf = ''
            if head.startswith('@'):
                kosul.append(head); i += 1; continue
            j, d = i + 1, 1
            while j < n and d:
                if text[j] == '{': d += 1
                elif text[j] == '}': d -= 1
                j += 1
            out.append((tuple(kosul), head, text[i+1:j-1]))
            i = j; continue
        if ch == '}':
            if kosul: kosul.pop()
            buf = ''; i += 1; continue
        buf += ch; i += 1
    return out

def tara(kok='static/css', verbose=False):
    bulgular, kasitli_gorulen = [], set()
    for f in sorted(pathlib.Path(kok).rglob('*.css')):
        yol = str(f)
        duz = []
        for idx, (kosul, head, body) in enumerate(kurallar(f.read_text())):
            b = bildirimler(body)
            for sel in head.split(','):
                sel = sel.strip()
                if sel: duz.append((idx, kosul, sel, b))
        # varyantin KENDI durum kurallari (savunma 1)
        durum_secicileri = {s for _, _, s, _ in duz if DURUM.search(s)}
        for oi, ok, osel, op in duz:
            if not DURUM.search(osel): continue
            for ni, nk, nsel, np in duz:
                if ni <= oi or nk != ok: continue
                if DURUM.search(nsel) or DIGER_DURUM.search(nsel): continue   # savunma 4
                if ozgulluk(nsel) != ozgulluk(osel): continue
                if not ozne_ayni_oge(osel, nsel): continue                     # savunma 2
                # savunma 1: `.a.b:hover` var mi?
                durum_eki = DURUM.search(osel).group(0)
                if any(ozne_ayni_oge(nsel, s.replace(durum_eki, '')) and durum_eki in s
                       for s in durum_secicileri if s != osel):
                    continue
                olen = sorted(p for p in op
                              if p in np and not np[p]                        # savunma 3
                              and p not in KISAYOL)
                if not olen: continue
                anahtar = (yol, osel, nsel)
                if anahtar in GOZDEN_GECIRILMIS_KASITLI:
                    kasitli_gorulen.add(anahtar); continue                    # savunma 5
                bulgular.append((yol, osel, nsel, olen))
    return bulgular, kasitli_gorulen

def main():
    verbose = '--verbose' in sys.argv
    bulgular, gorulen = tara(verbose=verbose)
    bayat = set(GOZDEN_GECIRILMIS_KASITLI) - gorulen
    print("state-order-check (K-G: durum kurali varyantin ALTINDA kalmali)")
    print("  gozden gecirilmis-kasitli cift: %d (eslesen %d)"
          % (len(GOZDEN_GECIRILMIS_KASITLI), len(gorulen)))
    if verbose:
        for (yol, o, n), gerekce in sorted(GOZDEN_GECIRILMIS_KASITLI.items()):
            isaret = '✓' if (yol, o, n) in gorulen else '· (artik eslesmiyor)'
            print("    %s %s  %s > %s\n        %s" % (isaret, yol, o, n, gerekce))
    if bayat:
        print("  NOT: %d kasitli cift artik CSS'te eslesmiyor (kural degismis "
              "olabilir, listeden dusurun):" % len(bayat))
        for yol, o, n in sorted(bayat):
            print("    - %s  %s > %s" % (yol, o, n))
    if bulgular:
        print("\n  ✗ K-G KIRIK — %d durum kurali kendi varyantinin ALTINDA kaliyor:"
              % len(bulgular))
        for yol, o, n, olen in bulgular:
            print("    %s\n      DURUM : %s\n      SONRA : %s  (esit ozgullukte, sonra geliyor)"
                  "\n      OLEN  : %s" % (yol, o, n, ', '.join(olen)))
        print("\n  Cozum: durum kuralini varyant bilesiklerinin ALTINA tasi, ya da")
        print("  karar kasitliysa GOZDEN_GECIRILMIS_KASITLI'ye GEREKCESIYLE ekle.")
        return 1
    print("  ✓ K-G PASS — durum kurallarinin hepsi varyantlarinin altinda.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
