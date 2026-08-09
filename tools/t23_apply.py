#!/usr/bin/env python3
"""T2.3 — mobil alt bar tekillestirme uygulayicisi.

hisse.html / ozet.html / sektor_harita.html icindeki INLINE mobil alt bar
(CSS + <nav> + sheet + script) silinir; dosyanin sonundaki
{% include '_mobile_nav_partial.html' %} tek kaynak olarak kalir.

Silme SINIRLARI hesaplanir, elle satir numarasi yazilmaz. Her sinir bir
KAPI ile dogrulanir; kapi tutmazsa HICBIR SEY yazilmaz (kismi yazma yok).

Kullanim: t23_apply.py <templates_dir> [--dry-run]
"""
import io
import re
import sys
from pathlib import Path

HEDEFLER = ["hisse.html", "ozet.html", "sektor_harita.html"]
PARTIAL = "_mobile_nav_partial.html"


def css_sinirlari(L):
    """CSS blogu: '/* Mobile Bottom Nav' yorumundan, .mobile-bottom-nav'i
    iceren @media blogunun kapanisina kadar."""
    bas = None
    for i, l in enumerate(L):
        if "Mobile Bottom Nav" in l and l.strip().startswith("/*"):
            bas = i
            break
    if bas is None:
        return None, "CSS baslangic yorumu '/* Mobile Bottom Nav' bulunamadi"

    # bitis: .mobile-bottom-nav { display: block; } iceren @media blogunun kapanisi
    med = None
    for i in range(bas, len(L)):
        if "@media" in L[i]:
            # bu media blogu icinde display:block var mi
            derinlik = 0
            j = i
            while j < len(L):
                derinlik += L[j].count("{") - L[j].count("}")
                if derinlik == 0 and j > i:
                    break
                j += 1
            govde = "\n".join(L[i:j + 1])
            if ".mobile-bottom-nav" in govde and "display: block" in govde:
                med = j
                break
    if med is None:
        return None, "kapanis @media (.mobile-bottom-nav display:block) bulunamadi"
    return (bas, med), None


def markup_sinirlari(L):
    """Markup+script blogu: <nav class="mobile-bottom-nav"> ...
    closeMbnSheet tanimindan sonraki ilk </script>."""
    try:
        bas = next(i for i, l in enumerate(L) if '<nav class="mobile-bottom-nav"' in l)
    except StopIteration:
        return None, '<nav class="mobile-bottom-nav"> bulunamadi'
    try:
        kapat = next(i for i, l in enumerate(L) if "function closeMbnSheet()" in l)
    except StopIteration:
        return None, "function closeMbnSheet() bulunamadi"
    if kapat < bas:
        return None, "closeMbnSheet nav'dan ONCE geliyor — beklenmeyen yapi"
    try:
        son = next(i for i in range(kapat, len(L)) if "</script>" in L[i])
    except StopIteration:
        return None, "closeMbnSheet sonrasi </script> bulunamadi"
    # bu blogun hemen oncesindeki <script> acilisini da al
    acilis = None
    for i in range(kapat, bas - 1, -1):
        if "<script" in L[i]:
            acilis = i
            break
    if acilis is None:
        return None, "script acilisi bulunamadi"
    return (bas, son), None


def main():
    if len(sys.argv) < 2:
        print("kullanim: t23_apply.py <templates_dir> [--dry-run]", file=sys.stderr)
        return 2
    tdir = Path(sys.argv[1])
    dry = "--dry-run" in sys.argv

    if not (tdir / PARTIAL).exists():
        print("HATA: kanonik partial yok: %s" % (tdir / PARTIAL), file=sys.stderr)
        return 2

    planlar = []
    for ad in HEDEFLER:
        p = tdir / ad
        if not p.exists():
            print("HATA: hedef sablon yok: %s" % p, file=sys.stderr)
            return 2
        src = io.open(p, encoding="utf-8").read()
        L = src.split("\n")

        # KAPI 1 — include GERCEKTEN var mi (silince yerine gececek olan)
        if not re.search(r"{%\s*include\s+['\"]_mobile_nav_partial\.html['\"]\s*%}", src):
            print("HATA: %s icinde partial include'u YOK — inline'i silmek bari"
                  " tamamen kaldirirdi. ABORT." % ad, file=sys.stderr)
            return 1

        css, e1 = css_sinirlari(L)
        if e1:
            print("HATA: %s CSS siniri: %s" % (ad, e1), file=sys.stderr)
            return 1
        mk, e2 = markup_sinirlari(L)
        if e2:
            print("HATA: %s markup siniri: %s" % (ad, e2), file=sys.stderr)
            return 1

        # KAPI 2 — iki blok cakisiyor mu
        if not (css[1] < mk[0]):
            print("HATA: %s CSS blogu (%d..%d) markup blogu (%d..%d) ile cakisiyor"
                  % (ad, css[0] + 1, css[1] + 1, mk[0] + 1, mk[1] + 1), file=sys.stderr)
            return 1

        # KAPI 3 — silinecek CSS icindeki body telafisi partial'da VAR mi
        css_govde = "\n".join(L[css[0]:css[1] + 1])
        par = io.open(tdir / PARTIAL, encoding="utf-8").read()
        for kural in ["padding-bottom: calc(64px"]:
            if kural in css_govde and kural not in par:
                print("HATA: %s — silinecek CSS'te '%s' var ama partial'da YOK."
                      " Telafi sahipsiz kalirdi. ABORT." % (ad, kural), file=sys.stderr)
                return 1

        # KAPI 4 — silinecek markup icinde partial'da OLMAYAN href var mi
        def hrefs(s):
            return set(re.findall(r'<a\s[^>]*href="([^"]+)"', s))
        mk_govde = "\n".join(L[mk[0]:mk[1] + 1])
        kayip = hrefs(mk_govde) - hrefs(par)
        if kayip:
            print("HATA: %s — silinecek blokta partial'da OLMAYAN link(ler): %s. ABORT."
                  % (ad, sorted(kayip)), file=sys.stderr)
            return 1

        planlar.append((p, ad, L, css, mk))

    # --- hepsi gecti, simdi yaz ---
    print("=== T2.3 UYGULAMA %s ===" % ("(KURU CALISMA)" if dry else "(YAZILDI)"))
    toplam = 0
    for p, ad, L, css, mk in planlar:
        sil = set(range(css[0], css[1] + 1)) | set(range(mk[0], mk[1] + 1))
        yeni = [l for i, l in enumerate(L) if i not in sil]
        n = len(sil)
        toplam += n
        print("  %-20s CSS %d..%d (%d satir) + markup %d..%d (%d satir) = %d satir silindi"
              % (ad, css[0] + 1, css[1] + 1, css[1] - css[0] + 1,
                 mk[0] + 1, mk[1] + 1, mk[1] - mk[0] + 1, n))
        if not dry:
            io.open(p, "w", encoding="utf-8").write("\n".join(yeni))

    print("\n  TOPLAM silinen satir: %d" % toplam)
    if toplam == 0:
        print("UYARI: hicbir satir silinmedi — zaten uygulanmis olabilir. EXIT=3",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
