#!/usr/bin/env python3
"""KAPI 81 -- K-DO: JS'IN YAZDIGI HEDEF KALICI GIZLI BIR AGACTA OLMAMALI.

KANAL: `_header.html`in `hdr_sub` / `hdr_sub_id` parametreleri ve onlarin
urettigi `.page-sub` dugumu. 80 kapinin hicbiri "yazilan metin GORUNUYOR
MU" sorusunu sormuyordu.

BULDUGU (K-DO, canli 22.09):
  `_bp_critical_css.html` anti-CLS kurali sarmalayiciyi gizliyor:
      header > div:has(> .page-sub){display:none !important}
  Bes sayfa VERI TAZELIK DAMGASINI tam oraya yaziyordu:
      gundem(updatedAt) · sektor-harita(lastUpdate) · bilanco-takvimi
      (lastUpdate) · temettu-takvimi(lastUpdate) · karsilastir(compareSubtitle)
  Canli olcum: `#lastUpdate`.textContent = "Son güncelleme: 22.09.2026 07:50",
  getBoundingClientRect() = 0x0, parent display=none. Damga 13 saat eski bir
  veriyi isaret ediyordu ve kullanici onu HIC GORMUYORDU. Dahasi dugum
  `role="status" aria-live="polite"` tasiyordu: `display:none` alt agaci
  erisilebilirlik agacindan duser, yani canli bolge EKRAN OKUYUCUYA DA hic
  duyurulmuyordu -- kanal IKI YONLU oluydu. Iki P0'i (38 hisse 43sa · 217/217
  85sa bayat veri) olan bir urunde tazelik damgasinin gorunmezligi bir
  guven yuzeyi kaybidir.

UC KURAL
  R1 hicbir sablon `_header.html`e `hdr_sub` / `hdr_sub_id` GECMEMELI
     (uretilen dugum tanimi geregi kalici gizli).
  R2 `_bp_critical_css.html` `.page-sub` sarmalayicisini gizleyen kurali
     TASIMAYA DEVAM ETMELI. Tasimazsa R1'in gerekcesi cokmus demektir ve
     kural bilincli olarak gozden gecirilmelidir (kural da kanitlanmali).
  R3 JS'in `getElementById(X).textContent` ile yazdigi her X, o sablonda
     bir yerde TANIMLI olmali. `hdr_sub_id` kaldirilirken dugumu <main>'e
     tasimayi unutmak sessiz bir ReferenceError/`null` hatasi uretirdi --
     164. dersin uygulamasi: kapiyi, korumak icin yazildigi hatayi enjekte
     ederek sina (self-test "id-tasinmadi" senaryosu).

OLCUM NOTU: R3'un id arayisi Jinja yorumlarini DUSURUR (77. ders) -- bu
dosyanin ya da sablonun aciklama yorumunda gecen bir id "tanimli" sayilmaz.

Kullanim: python3 tools/hidden-write-target-check.py [--verbose] [--ref GIT_REF]
          python3 tools/hidden-write-target-check.py --self-test
Cikis: ihlal varsa 1.
"""
import re, sys, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent

RE_HDR_SUB   = re.compile(r"\bhdr_sub(?:_id)?\s*=")
RE_JINJA_CMT = re.compile(r"\{#.*?#\}", re.S)
RE_WRITE     = re.compile(
    r"""getElementById\(\s*['"]([A-Za-z0-9_\-]+)['"]\s*\)\s*\.\s*(?:textContent|innerHTML|innerText)\s*=""")
RE_ID_DEF    = re.compile(r"""\bid\s*=\s*["']([A-Za-z0-9_\-]+)["']""")
# Ayni dugumu JS'in kendisi de yaratmis olabilir (sablonda statik id yok).
RE_ID_IN_JS  = re.compile(r"""id\s*=\s*\\?["']([A-Za-z0-9_\-]+)\\?["']""")

CRITICAL_CSS = "_bp_critical_css.html"
RE_PAGESUB_HIDE = re.compile(
    r"header\s*>\s*div:has\(\s*>\s*\.page-sub\s*\)[^{]*\{[^}]*display\s*:\s*none", re.I)


def denetle(kaynak, verbose=False):
    ihlaller = []
    for ad in sorted(kaynak):
        src = kaynak[ad]
        if ad.startswith("_header"):
            continue                      # partial'in KENDI dokumantasyonu
        govde = RE_JINJA_CMT.sub(" ", src)

        # R1
        for m in RE_HDR_SUB.finditer(govde):
            ihlaller.append(
                "%s R1: `%s` geciriliyor -- uretilen .page-sub dugumu anti-CLS "
                "kuraliyla KALICI gizli (yazilan metin de aria-live de olu)"
                % (ad, govde[m.start():m.end()].strip()))

        # R3
        tanimli = set(RE_ID_DEF.findall(govde)) | set(RE_ID_IN_JS.findall(govde))
        for eid in sorted(set(RE_WRITE.findall(govde))):
            if eid not in tanimli:
                ihlaller.append(
                    "%s R3: JS `#%s` dugumune yaziyor ama o id sablonda hicbir "
                    "yerde tanimli degil" % (ad, eid))
        if verbose and (RE_HDR_SUB.search(govde) or RE_WRITE.search(govde)):
            print("  %-26s yazilan id: %s"
                  % (ad, ",".join(sorted(set(RE_WRITE.findall(govde)))) or "-"))

    # R2 -- gerekce hala ayakta mi
    css = kaynak.get(CRITICAL_CSS)
    if css is None:
        ihlaller.append("%s R2: dosya bulunamadi -- R1'in gerekcesi dogrulanamiyor"
                        % CRITICAL_CSS)
    elif not RE_PAGESUB_HIDE.search(css):
        ihlaller.append(
            "%s R2: `.page-sub` sarmalayicisini gizleyen anti-CLS kurali YOK. "
            "R1'in gerekcesi cokmus olabilir -- kurali gozden gecirin, sessizce "
            "gevsetmeyin." % CRITICAL_CSS)
    return ihlaller


def _oku_disk():
    return {p.name: p.read_text(encoding="utf-8")
            for p in sorted((ROOT / "templates").glob("*.html"))}


def _oku_ref(ref):
    out = {}
    names = subprocess.run(["git", "ls-tree", "--name-only", "%s:templates" % ref],
                           cwd=ROOT, capture_output=True, text=True).stdout.split()
    for n in names:
        if n.endswith(".html"):
            r = subprocess.run(["git", "show", "%s:templates/%s" % (ref, n)],
                               cwd=ROOT, capture_output=True, text=True)
            if r.returncode == 0:
                out[n] = r.stdout
    return out


_CSS_OK = {CRITICAL_CSS: "header > div:has(> .page-sub){display:none !important}"}

SELF = [
    ("temiz", dict(_CSS_OK, **{"x.html":
        '<p class="da-updated" id="lastUpdate"></p>'
        '<script>document.getElementById("lastUpdate").textContent = "a";</script>'}), 0),
    ("r1-gercek-hata (K-DO oncesi)", dict(_CSS_OK, **{"x.html":
        "{% with hdr_title='T', hdr_sub='Yükleniyor…', hdr_sub_id='lastUpdate' %}"
        "{% include '_header.html' %}{% endwith %}"
        '<script>document.getElementById("lastUpdate").textContent = "a";</script>'}), 2),
    ("r1-yalniz-hdr_sub", dict(_CSS_OK, **{"x.html":
        "{% with hdr_title='T', hdr_sub='alt' %}{% include '_header.html' %}{% endwith %}"}), 1),
    ("r1-yorumda-anilmasi-ihlal-degil (77. ders)", dict(_CSS_OK, **{"x.html":
        "{#- hdr_sub = 'x' kullanmayin -#}<p id=\"u\"></p>"
        '<script>document.getElementById("u").textContent = "a";</script>'}), 0),
    ("r3-id-tasinmadi (164. ders enjeksiyonu)", dict(_CSS_OK, **{"x.html":
        "{% with hdr_title='T' %}{% include '_header.html' %}{% endwith %}"
        '<script>document.getElementById("lastUpdate").textContent = "a";</script>'}), 1),
    ("r3-id-JS-icinde-uretilmis", dict(_CSS_OK, **{"x.html":
        '<script>el.innerHTML = \'<p id="u2"></p>\';'
        'document.getElementById("u2").textContent = "a";</script>'}), 0),
    ("r2-anti-CLS-kurali-kaybolmus",
     {CRITICAL_CSS: ".page-title{display:none}", "x.html": "<p></p>"}, 1),
    ("r2-css-dosyasi-yok", {"x.html": "<p></p>"}, 1),
    ("_header-kendi-dokumantasyonu-muaf",
     dict(_CSS_OK, **{"_header.html": "hdr_sub = kullanmayin", "x.html": "<p></p>"}), 0),
]


def self_test():
    ok = 0
    for ad, kaynak, bekle in SELF:
        n = len(denetle(kaynak))
        if n == bekle:
            ok += 1
        else:
            print("  FAIL %-44s bekleniyordu %d, cikti %d" % (ad, bekle, n))
            for i in denetle(kaynak):
                print("        -> %s" % i)
    print("self-test %d/%d" % (ok, len(SELF)))
    return 0 if ok == len(SELF) else 1


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        sys.exit(self_test())
    verbose = "--verbose" in args
    ref = args[args.index("--ref") + 1] if "--ref" in args else None
    kaynak = _oku_ref(ref) if ref else _oku_disk()
    print("KAPI 81 -- gizli yazma hedefi (%s, %d sablon)"
          % (ref or "calisan agac", len(kaynak)))
    ihlaller = denetle(kaynak, verbose)
    for i in ihlaller:
        print("  IHLAL: %s" % i)
    print("  ihlal: %d" % len(ihlaller))
    sys.exit(1 if ihlaller else 0)


if __name__ == "__main__":
    main()
