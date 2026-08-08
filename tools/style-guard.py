#!/usr/bin/env python3
"""Sablon stil guard'i — T1.7 format-lint v2'nin ikinci parcasi.

`tools/css-token-guard.py` YALNIZ `static/css/*.css` dosyalarini denetliyor (2 dosya).
Oysa T1.5 migrasyonundan sonra sablonlarin icinde 2339 adet `var(--bp-*)` kullanimi var
ve bunlarin hicbiri hicbir kapida denetlenmiyordu. Iki kusur sinifi olculdu ve
bu guard tam olarak ikisini kapatir:

K-A  TANIMSIZ var()  — BLOKLAYICI, taban 0
     Bir sayfada kullanilan token o sayfada gorunur DEGILSE deger sessizce
     ilk-deger/bos'a duser. Tarayici hata vermez, HTTP 200 doner, grep dosyanin
     icinde token adini BULUR. Tek kirmizi olcut getComputedStyle'di; bu guard onu
     statik olarak, deploy'dan ONCE yapar.
     Kapsam kurali: CSS ozel ozellikleri DOM uzerinden miras alinir, DOSYALAR
     ARASINDA DEGIL. Bir sablonun `:root`unda tanimli token BASKA sablonu kurtarmaz.
     Bu yuzden denetim SAYFA BAZINDADIR (global css + o sayfanin kendi tanimlari +
     her sayfaya giren kabuk partial'lari).
     Bugunku taban: 27/27 sayfada 0 tanimsiz — guard bugun YESIL, yani kirmiziya
     donduren sey bundan sonraki bir REGRESYONDUR.

K-B  KANONIK-DEGERLI HAM HEX — RATCHET, bloklamaz ama ARTAMAZ
     Token'i olan bir rengin ham hex yazimi (`#f85149` yerine `var(--bp-sat)`).
     Bugun 506 occurrence var; hepsini bir gecede cevirmek GORSEL REGRESYON riski
     tasir (T1.5b olcumu: 601 adayin yalnizca 112'si kosulsuz guvenli). Bu yuzden
     mutlak yasak degil, KADEMELI KAPI: dosya basina sayim ARTARSA hata.
     Yani mevcut borc bloklamaz, YENI borc bloklar. Master Program §7'nin
     "once yeni commit'lere zorunlu, sonra geriye donuk" tavsiyesi budur.

     Ratchet dosyasi token IMZASINI da saklar: `tokens.css`e yeni bir token
     eklenince kanonik deger kumesi buyur ve sayimlar sablon degismeden artabilir.
     O durum ayri bir mesajla raporlanir — sucu sablona atmaz.

Kullanim:
    python3 tools/style-guard.py             # denetle (deploy kapisi)
    python3 tools/style-guard.py --baseline  # ratchet'i bugunku duruma sabitle
    python3 tools/style-guard.py --verbose   # dosya bazinda tam tablo
Cikis: 0 = temiz, 1 = ihlal (deploy engellenmeli)
"""
import json
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "templates"
CSS_DIR = ROOT / "static" / "css"
RATCHET = ROOT / "tools" / "style_guard_ratchet.json"

# Her sayfaya fiilen giren kabuk partial'lari: buradaki tanimlar tum sayfalarda gecerli.
# T2.2: _header.html + _header_asset_price.html EKLENDI. Eklenmeden once
# 16 sayfanin kanonik header-i HICBIR kapida denetlenmiyordu ve ratchet
# toplami 491->475 dusmus gorunuyordu — borc ODENMEDI, denetlenmeyen bir
# dosyaya TASINDI. Bu satir olmadan K-A/K-B kapsam iddiasi sahtedir.
KABUK_PARTIALS = ("_base.html", "_head.html", "_header.html",
                  "_header_asset_price.html")

COMMENT_RE = re.compile(r"{#.*?#}", re.S)
TANIM_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
TOKEN_DEGER_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})\s*;")

sys.path.insert(0, str(ROOT / "tools"))
try:
    from lint_scope import sayfa_sablonlari
except ImportError:                                    # pragma: no cover
    sayfa_sablonlari = None


def _oku(p):
    return p.read_text(encoding="utf-8", errors="replace")


def global_tanimlar():
    """static/css/*.css + her sayfaya giren kabuk partial'larinin tanimladigi token'lar."""
    toks = set()
    for f in sorted(CSS_DIR.glob("*.css")):
        toks |= set(TANIM_RE.findall(_oku(f)))
    for n in KABUK_PARTIALS:
        p = TPL_DIR / n
        if p.exists():
            toks |= set(TANIM_RE.findall(_oku(p)))
    return toks


def kanonik_hex_haritasi():
    """deger -> [token adlari].  Yalnizca dogrudan hex ATANAN token'lar."""
    m = {}
    for f in sorted(CSS_DIR.glob("*.css")):
        for tok, val in TOKEN_DEGER_RE.findall(_oku(f)):
            m.setdefault(val.lower(), set()).add(tok)
    return {k: sorted(v) for k, v in m.items()}


def sayfalar():
    if sayfa_sablonlari is not None:
        return sayfa_sablonlari()
    return [f for f in sorted(TPL_DIR.glob("*.html"))
            if not f.name.startswith("_") and ".bak" not in f.name]


def hex_say(metin, harita):
    n = 0
    for h in HEX_RE.findall(metin):
        hl = h.lower()
        if len(hl) in (4, 7, 9) and hl in harita:
            n += 1
    return n


def denetle():
    gtok = global_tanimlar()
    harita = kanonik_hex_haritasi()
    imza = "%d:%s" % (len(harita), ",".join(sorted(harita)[:8]))

    tanimsiz = {}
    hex_sayim = {}
    for f in sayfalar():
        txt = _oku(f)
        yerel = set(TANIM_RE.findall(txt))
        eksik = {}
        for tok in set(VAR_RE.findall(txt)):
            if tok not in gtok and tok not in yerel:
                eksik[tok] = len(re.findall(r"var\(\s*" + re.escape(tok), txt))
        if eksik:
            tanimsiz[f.name] = eksik
        hex_sayim[f.name] = hex_say(txt, harita)

    # ── KABUK PARTIAL'LARI DA TARA (T2.2 dersi) ─────────────────────────────
    # KABUK_PARTIALS su ana kadar YALNIZ global_tanimlar()'da kullaniliyordu,
    # yani partial'larin TANIMLADIGI token'lar biliniyor ama KULLANDIKLARI
    # var() ve icerdikleri ham hex HIC SAYILMIYORDU. Olculdu (09.08.2026):
    # _header.html 12 ham hex tasiyor, 1'i kanonik degerli (#b8c3ff = --bp-brand);
    # _head.html 4 tasiyor, 1'i kanonik (#0e0e12 = --bp-bg). Bunlar 16 ve 27
    # sayfaya giriyor ama ratchet'te GORUNMUYORLARDI. 065b6a6'da toplam 491->475
    # dustu; dususun bir kismi borcun ODENMESI degil, denetlenmeyen bir dosyaya
    # TASINMASIYDI. Partial'lar her sayfaya girdigi icin K-A'da yerel :root
    # kurtarmasi YOK — global tanimlara karsi olculurler (en siki olcut).
    for n in KABUK_PARTIALS:
        pf = TPL_DIR / n
        if not pf.exists():
            continue
        txt = COMMENT_RE.sub("", _oku(pf))     # dokuman blogu olcume girmez
        eksik = {}
        for tok in set(VAR_RE.findall(txt)):
            if tok not in gtok:
                eksik[tok] = len(re.findall(r"var\(\s*" + re.escape(tok), txt))
        if eksik:
            tanimsiz[n] = eksik
        hex_sayim[n] = hex_say(txt, harita)
    return gtok, harita, imza, tanimsiz, hex_sayim


def yerel_root_sayim():
    """Sablon-yerel :root bloklarini say (T9.4-d).

    NEDEN BLOKLAYICI DEGIL RATCHET: CSS ozel ozellikleri DOM uzerinden miras
    alinir, DOSYALAR ARASINDA DEGIL. Bir sablonun kendi :root'u tokens.css'i
    o sayfada EZER ve hicbir arac bunu fark etmez — grep token adini bulur,
    tarayici hata vermez. Olculdu (09.08.2026): 4 sablonda yerel :root var ve
    tanimladiklari 13 token'in 11'i tokens.css'teki karsiligindan FARKLI degerde
    (ornek: --brand #1f6feb vs --bp-brand #b8c3ff; --text3 #484f58 = 2.09:1
    kontrast, FAZ 8'in P0 kalemi). Yani /tarama, /kripto, /abd-tarama fiilen
    BASKA BIR PALETLE render ediliyor. Bunu bu turda DUZELTMEDIM (gorsel karar,
    marka rengi Ozan'da) ama ARTMASINI engelliyorum.
    """
    from lint_scope import sayfa_sablonlari
    out = {}
    for f in sayfa_sablonlari():
        n = f.read_text(encoding="utf-8").count(":root")
        if n:
            out[f.name] = n
    return out


def main(argv):
    verbose = "--verbose" in argv
    gtok, harita, imza, tanimsiz, hex_sayim = denetle()
    toplam_sayfa = len(hex_sayim)

    if "--baseline" in argv:
        RATCHET.write_text(json.dumps(
            {"_not": "T1.7 style-guard ratchet — kanonik-degerli ham hex, dosya basina TAVAN. "
                     "Sayim yalniz DUSEBILIR; artis deploy'u bloklar. Yeni token eklenince "
                     "token_imzasi degisir ve bu dosya --baseline ile yenilenir.",
             "token_imzasi": imza,
             "dosyalar": dict(sorted(hex_sayim.items())),
             "yerel_root": dict(sorted(yerel_root_sayim().items()))},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("baseline yazildi: %d sayfa, toplam %d kanonik-degerli ham hex"
              % (toplam_sayfa, sum(hex_sayim.values())))
        return 0

    hata = 0
    print("style-guard  (kapsam: %d sayfa sablonu, %d kanonik token degeri)"
          % (toplam_sayfa, len(harita)))

    # ── K-A: tanimsiz var() — BLOKLAYICI ────────────────────────────────────
    if tanimsiz:
        hata = 1
        print("  KIRIK  K-A tanimsiz var(): %d sayfada" % len(tanimsiz))
        for ad in sorted(tanimsiz):
            for tok, n in sorted(tanimsiz[ad].items()):
                print("         %-28s %-24s %d kullanim" % (ad, tok, n))
        print("         Bu token o sayfada GORUNUR degil; deger sessizce bosa duser.")
        print("         Tarayici hata vermez, HTTP 200 doner, grep token adini BULUR.")
    else:
        print("  TEMIZ  K-A tanimsiz var(): %d/%d sayfada 0" % (toplam_sayfa, toplam_sayfa))

    # ── K-B: ham hex ratchet — ARTAMAZ ──────────────────────────────────────
    try:
        ratchet = json.loads(RATCHET.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("  ATLANDI K-B ham hex ratchet: %s yok — once `--baseline` calistirin." % RATCHET.name)
        print("         (Bu bir SESSIZ ATLAMA degil: acikca raporlanir ve deploy'u bloklamaz,")
        print("          ama kapinin bu yarisi devrede DEGILDIR.)")
        return hata

    taban = ratchet.get("dosyalar", {})
    artan = []
    for ad, n in sorted(hex_sayim.items()):
        t = taban.get(ad)
        if t is None:
            if n > 0:
                artan.append((ad, 0, n, "YENI DOSYA"))
        elif n > t:
            artan.append((ad, t, n, ""))
    if ratchet.get("token_imzasi") != imza:
        print("  UYARI  K-B: kanonik token kumesi DEGISTI (tokens.css'e token eklendi/cikarildi).")
        print("         Sayimlar sablon degismeden kayabilir — dogruladiktan sonra `--baseline`.")
    if artan:
        hata = 1
        print("  KIRIK  K-B ham hex ARTTI: %d dosya" % len(artan))
        for ad, t, n, not_ in artan:
            print("         %-28s %d -> %d  %s" % (ad, t, n, not_))
        print("         Token'i olan renk ham hex yazilmis. `var(--bp-*)` kullanin.")
        print("         Mevcut borc bloklamaz; YENI borc bloklar (kademeli kapi).")
    else:
        toplam = sum(hex_sayim.values())
        tt = sum(taban.values())
        print("  TEMIZ  K-B ham hex ratchet: %d occurrence (taban %d, artis yok)" % (toplam, tt))

    # ── K-C: sablon-yerel :root ratchet — ARTAMAZ ───────────────────────────
    yr = yerel_root_sayim()
    yr_taban = ratchet.get("yerel_root")
    if yr_taban is None:
        print("  ATLANDI K-C yerel :root: ratchet'te taban yok — `--baseline` calistirin.")
    else:
        yr_artan = [(ad, yr_taban.get(ad, 0), n) for ad, n in sorted(yr.items())
                    if n > yr_taban.get(ad, 0)]
        if yr_artan:
            hata = 1
            print("  KIRIK  K-C sablon-yerel :root ARTTI: %d dosya" % len(yr_artan))
            for ad, t, n in yr_artan:
                print("         %-28s %d -> %d" % (ad, t, n))
            print("         Yerel :root tokens.css'i O SAYFADA sessizce ezer.")
            print("         Yeni token TANIMI tokens.css'e; sayfaya DEGIL.")
        else:
            print("  TEMIZ  K-C yerel :root: %d sablon (taban %d, artis yok)"
                  % (sum(yr.values()), sum(yr_taban.values())))

    if verbose:
        print("\n  %-32s %6s %6s" % ("sablon", "hex", "taban"))
        for ad, n in sorted(hex_sayim.items(), key=lambda kv: -kv[1]):
            print("  %-32s %6d %6s" % (ad, n, taban.get(ad, "-")))

    return hata


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
