#!/usr/bin/env python3
"""KAPI 58 -- K-CM: /metodoloji sozlugunun "NEREDE GORULUR" vaadi.

KANAL: `templates/metodoloji.html` icindeki `<span class="term-where">` metni.
57 kapinin hicbiri bunu okumuyordu. Bu bir NESIR degil, URUN HAKKINDA
DOGRULANABILIR BIR IDDIA: "bu terimi su sayfalarda gorursun". Vaat edilen
yuzeyde terim yoksa, kullanici metodolojinin gonderdigi yerde aradigini
bulamaz -- /hakkinda'nin kendi icinde celiskisiyle (K-CE) ayni sinif.

BULDUGU (K-CM, canli 22.09):
  1. "💎 Yuksek Skor · Orta Skor" -> vaat: "Tarama listesi, karsilastirma".
     /tarama'da "Orta Skor" ifadesi HIC gecmiyordu: 70+ 💎 aliyor, 56-69
     bandi YALNIZ mavi renkle ayirt ediliyordu, adi hicbir yerde yoktu.
  2. "RVOL 5g / 20g" -> vaat: "... karsilastirma". /api/karsilastir `rvol`
     alanini HIC dondurmuyor (alan listesi dogrulandi) -- vaat yapisal
     olarak karsilanamazdi, sayfa yillardir o sayiyi gosteremezdi.

OLCUM NOTU (77. dersin HTML karsiligi): YORUMLAR YAYIMLANMAZ. `index.html`
"Orta Skor"u iki kez aniyor ama ikisi de JS yorumu -- ham grep bunu "vaat
karsilandi" sanirdi. Jinja `{# #}` ve `<script>` icindeki JS yorumlari
metinden DUSURULUR, ardindan aranir.

BEYAZ LISTE ANAHTARI (K-BD dersi): satir numarasi DEGIL, `<dt>` metninin
kendisi. Sozluk satiri tasinirsa kural tasinir; metni degisirse kapi
"bilinmeyen terim" diye duser ve esleme bilincli olarak guncellenir.

Kullanim: python3 tools/glossary-where-check.py [--verbose] [--ref GIT_REF]
Cikis: ihlal varsa 1.
"""
import re, sys, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Yuzey adi (term-where'de gectigi gibi) -> onu ciziyor olmasi gereken sablon.
YUZEY = {
    "hisse sayfası":        "hisse.html",
    "tarama":               "tarama.html",
    "karşılaştırma":        "karsilastir.html",
    "anasayfa":             "index.html",
    "sektör ısı haritası":  "sektor_harita.html",
    "bilanço":              "bilanco_takvimi.html",
    "temettü takvimi":      "temettu_takvimi.html",
    "csv dışa aktarımı":    "tarama.html",   # CSV uretimi tarama.html icinde
    "sinyal kolonu":        "tarama.html",
}

# `<dt>` metni -> o satirin URUNDE aranacak ifadeleri. Bir dt birden fazla
# terim tasiyabilir ("💎 Yuksek Skor · Orta Skor"); HEPSI aranir.
TERIM_IFADELERI = {
    "Güçlü Trend · Trend Bozuldu · Yatay":  ["Güçlü Trend", "Trend Bozuldu", "Yatay"],
    "Teknik Güç Skoru 0–100":               ["Teknik Güç"],
    "Trend Gücü ADX":                       ["Trend Gücü"],
    "Günlük Hacim Oranı son seans / 20g":   ["Günlük Hacim Oranı"],
    "RVOL 5g / 20g":                        ["RVOL"],
    "💎 Yüksek Skor · Orta Skor":           ["Yüksek Skor", "Orta Skor"],
    "⭐ Hacim Onaylı":                      ["Hacim Onaylı"],
    "BorsaPusula Skoru 0–100":              ["BorsaPusula Skoru"],
}

RE_JINJA_YORUM = re.compile(r"\{#.*?#\}", re.S)
RE_SCRIPT      = re.compile(r"(<script[^>]*>)(.*?)(</script>)", re.S | re.I)
RE_JS_SATIR    = re.compile(r"(?<![:'\"])//[^\n]*")
RE_JS_BLOK     = re.compile(r"/\*.*?\*/", re.S)
RE_HTML_YORUM  = re.compile(r"<!--.*?-->", re.S)


def _read(ref, relpath):
    if ref:
        return subprocess.run(["git", "show", f"{ref}:{relpath}"], cwd=ROOT,
                              capture_output=True, text=True).stdout
    p = ROOT / relpath
    return p.read_text(encoding="utf-8") if p.exists() else ""


def yayimlanan_metin(src):
    """Kullaniciya GERCEKTEN ulasan metin: yorumlar dusurulur."""
    src = RE_JINJA_YORUM.sub(" ", src)
    src = RE_HTML_YORUM.sub(" ", src)

    def _temizle(m):
        govde = RE_JS_BLOK.sub(" ", m.group(2))
        govde = RE_JS_SATIR.sub(" ", govde)
        return m.group(1) + govde + m.group(3)

    return RE_SCRIPT.sub(_temizle, src)


def tara(ref=None, verbose=False):
    met = _read(ref, "templates/metodoloji.html")
    if not met:
        print("  metodoloji.html okunamadi"); return [("R0", "metodoloji.html", "okunamadi")]

    out, n_vaat, n_satir = [], 0, 0
    onbellek = {}

    for blok in re.findall(r'<div class="term-row">(.*?)</div>', met, re.S):
        dt = re.search(r"<dt>(.*?)</dt>", blok, re.S)
        wh = re.search(r'<span class="term-where">(.*?)</span>', blok, re.S)
        if not dt:
            continue
        n_satir += 1
        baslik = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", dt.group(1))).strip()

        # R2 -- her sozluk satiri "nerede gorulur" demeli (vaat YOKLUGU da bulgudur)
        if not wh:
            out.append(("R2", f"metodoloji.html:{baslik}",
                        "sozluk satirinda `term-where` YOK -- terim tanimli ama "
                        "urunde nerede gorulecegi soylenmiyor"))
            continue

        # R3 -- kapi kor kalmasin: bilinmeyen dt eslenemez
        if baslik not in TERIM_IFADELERI:
            out.append(("R3", f"metodoloji.html:{baslik}",
                        "sozlukte yeni/degismis terim -- TERIM_IFADELERI eslemesi "
                        "yok, bu satirin vaadi DOGRULANMIYOR (kapi kor)"))
            continue

        ham = re.sub(r"<[^>]+>", "", wh.group(1))
        ham = ham.replace("&laquo;", "«").replace("&raquo;", "»")
        for parca in ham.split(","):
            p = re.sub(r"\s+", " ", parca).strip().lower()
            if not p:
                continue
            hedefler = sorted({f for ad, f in YUZEY.items() if ad in p})
            if not hedefler:
                # R4 -- adlandirilan yuzey bir sayfaya eslenemiyor
                out.append(("R4", f"metodoloji.html:{baslik}",
                            f'vaat edilen yuzey "{parca.strip()}" bilinen bir '
                            f"sayfaya eslenemedi -- YUZEY tablosu guncellenmeli"))
                continue
            for hedef in hedefler:
                n_vaat += 1
                if hedef not in onbellek:
                    onbellek[hedef] = yayimlanan_metin(_read(ref, f"templates/{hedef}"))
                govde = onbellek[hedef]
                for ifade in TERIM_IFADELERI[baslik]:
                    if ifade in govde:
                        continue
                    # R1 -- vaat edilen yuzeyde terim YOK
                    out.append(("R1", f"{hedef}",
                                    f'/metodoloji "{baslik}" icin "{parca.strip()}" '
                                    f'yuzeyini vaat ediyor ama "{ifade}" o sayfanin '
                                    f"YAYIMLANAN metninde gecmiyor"))

    if verbose:
        print(f"  tarandi: {n_satir} sozluk satiri / {n_vaat} (terim,yuzey) vaadi")
    return out


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    ref = None
    if "--ref" in sys.argv:
        ref = sys.argv[sys.argv.index("--ref") + 1]
    out = tara(ref, verbose)
    if out:
        for kural, nerede, mesaj in out:
            print(f"  [{kural}] {nerede}: {mesaj}")
        print(f"  TOPLAM {len(out)} ihlal")
        return 1
    print("KAPI 58 OK — sozlugun \"nerede gorulur\" vaatleri urunle tutarli")
    return 0


if __name__ == "__main__":
    sys.exit(main())
