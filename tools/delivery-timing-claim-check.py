#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 60 (K-CO, 22.09.2026) — TESLIMAT/TEPKI ANINDALIGI IDDIA DEDEKTORU.

NEDEN BU KAPI VAR
-----------------
Kapi 50 (`intraday-claim-check`) VERININ gun-ici olup olmadigini olcer:
"gun ici", "anlik fiyat", "gercek zamanli", "canli veri". Ama urunun
kullaniciya verdigi ikinci bir zamanlama sozu daha var ve o sozlukte HIC
gecmiyor: **ne zaman haber alacaksin?**

Mimari EOD-only (CPO-1703, app.py:4166): sinyal degisimi tespiti gunde TEK
kez, kapanis sonrasi EOD turunda yapilir (`_eod_fetch_trigger_ready_after()`
= 18:10 TR, app.py:4412-4467). `_notify_signal_changes()` yalnizca o turun
sonunda (app.py:3973) ve gunde bir catch-up turunda (app.py:4238) cagrilir.
Dolayisiyla "aninda mail" mimari olarak **gunde bir kez** demektir.

K-CO'da bu sinifla celisen 6 canli yuzey bulundu (4 yuzey / 3 kanal):
  * /profil   "⚡ Anında — her sinyal değişimi olduğunda hemen"
  * /profil   "... Güçlü Trend sinyalleri, anında (oluştuğunda hemen)"
  * app.py    hosgeldin maili: "Anlık bildirim istersen ... 'Anında' seç"
  * app.py    hosgeldin maili tercih listesi ("günlük özet, anında, ...")
  * /gizlilik tercih listesi ("günlük/anında/haftalık/sadece premium")
  * /metodoloji "sinyal rozeti ... bu geçişi anında yansıtır"

Son madde en agiri: kapi 50'nin sozlugunde ("anlık FIYAT/VERI") yer almadigi
icin 59 kapidan hicbiri gormemisti — iddia FIYATIN degil URUNUN TEPKISININ
gun-ici oldugunu soyluyordu.

NE TARANIR (76./83. ders — kanal envanteri)
-------------------------------------------
  templates/*.html      gorunur metin + attribute + inline JS dizeleri
  app.py                yayimlanan string literalleri (kapi 52 yontemi: ast,
                        docstring/serbest-blok haric)
  static/**/*.js        dize literalleri
  blog_content.py       makale govdesi (R1 yalniz teslimat nesnesiyle atesler,
                        "piyasa emri anında gerceklesir" finans egitimidir)

MUAFIYET ANLAM KURALIDIR (43. ders — beyaz liste anahtari satir no olamaz)
--------------------------------------------------------------------------
* Anindalik sozcugunun 60 karakter komsulugunda bir TESLIMAT NESNESI
  (bildirim/mail/uyari/sinyal/rozet/guncelle/yansit) yoksa ihlal degildir:
  "kriterlere uyan hisseleri anında listele" ISTEMCI TARAFI filtredir ve
  gercekten anindadir.
* Ayni parca iddiayi olumsuzluyorsa ("... hemen almak DEGIL") ihlal degildir.

R2 — TERCIH ADI PARITESI ("ayni is icin iki kanon" mercegi)
------------------------------------------------------------
Kullanicinin /profil'de GORDUGU dort tercih adi, tercihlerin sayildigi her
yuzeyde (gizlilik metni + hosgeldin maili) ayni yazilmalidir. K-CO oncesi
/gizlilik "sadece premium" diyordu — kullanicinin hicbir ekranda gormedigi
bir VERI ANAHTARI, nesir icinde tercih adi gibi sunulmustu.
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")

# ── 97. ders: yayimlanan metni tarayan her dedektor kacislari ONCE cozer ──
_RE_U = re.compile(r"\\u([0-9a-fA-F]{4})")
def coz(s):
    return _RE_U.sub(lambda m: chr(int(m.group(1), 16)), s)

# ── R1 sozlugu ────────────────────────────────────────────────────────────
# ⛔ KELIME SINIRI ZORUNLU: "or|anında", "yan|ında", "veritaban|ında",
#    "enflasyon or|anında" -- Turkce'de "-ında" cok yaygin bir ek. `\b` yetmez
#    (onceki karakter harf olabilir), ONCESINDE harf OLMAMALI kurali gerekir.
_ONEK = r"(?<![0-9A-Za-zÇĞİIÖŞÜçğıöşü])"
RE_ANINDA = re.compile(
    _ONEK + r"(anında|anlık|hemen|gecikmeden|gecikmesiz|saniyeler\s+içinde|"
    r"oluşur\s+oluşmaz|an\s+be\s+an)", re.IGNORECASE)
# ANLAM MUAFIYETI: anindalik OKUYUCUNUN edimine bagliysa (blog egitimi:
# "hızlı sinyal geldi, hemen al") urun vaadi degildir.
RE_OKUYUCU_EDIMI = re.compile(
    r"^\W{0,3}(al|alın|alalım|sat|satın|satalım|gir|girin|çık|çıkın|koş|kaç)\b",
    re.IGNORECASE)
# teslimat/tepki nesnesi: urunun kullaniciya haber verme ya da ekrani
# guncelleme edimi. ("fiyat"/"veri" kapi 50'nin alani, burada tekrarlanmaz.)
RE_TESLIMAT = re.compile(
    r"(bildirim|uyarı|uyarılar|alarm|mail|e-posta|e-mail|posta|push|"
    r"sinyal|rozet|yansıt|güncelle|haber\s+ver|bilgilendir)", re.IGNORECASE)
RE_DISCLAIM = re.compile(
    r"değildir|değil\b|olmaz|yoktur|sunulm[au]|sunmuyor|retire|kaldırıl|"
    r"planlanmıyor|desteklenmiyor", re.IGNORECASE)
NEAR = 60  # karakter komsulugu

# ── R3: emekli tercih adi ─────────────────────────────────────────────────
RE_EMEKLI_PREF = re.compile(r"[\"'“”]\s*Anında\s*[\"'“”]|tercih\w*[^.]{0,40}anında",
                            re.IGNORECASE)

# ── R2: kanonik tercih adlari /profil'den okunur ──────────────────────────
PREF_KEYS = ("daily", "instant", "premium", "weekly")
RE_PREF_OPT = re.compile(
    r"""data-v=["'](daily|instant|premium|weekly)["'][^>]*>(.*?)</button>""",
    re.S)
# tercihlerin SAYILDIGI nesir: bu cumlelerde dort adin dordu de gecmeli
PREF_ENUM_HINT = re.compile(r"mail\s+sıklığı|mail\s+tercih|mail\s+sıklığını", re.I)


def strip_comments(src):
    src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"(?m)^\s*//.*$", "", src)
    return src


def tpl_segments(src):
    """(satir, metin) — gorunur dugumler, meta content'leri ve dize literalleri.
    98. ders: kullaniciya gorunen attribute'lar ayri blok olarak cikarilir."""
    out = []
    for m in re.finditer(r">([^<>]{1,600})<", src):
        out.append((src[:m.start()].count("\n") + 1, m.group(1)))
    for m in re.finditer(
            r"""\b(?:content|data-tip|aria-label|title|placeholder|alt)="""
            r"""["']([^"']{1,600})["']""", src, re.I | re.S):
        out.append((src[:m.start()].count("\n") + 1, m.group(1)))
    for m in re.finditer(r"""(['"`])((?:\\.|(?!\1)[^\\\n])*)\1""", src):
        if len(m.group(2)) > 3:
            out.append((src[:m.start()].count("\n") + 1, m.group(2)))
    return out


def py_published(path):
    """Yayimlanan string literalleri (kapi 52 yontemi)."""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    skip = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
               and isinstance(first.value.value, str):
                skip.add(id(first.value))
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            skip.add(id(node.value))
        # logger.info("Anında sinyal e-postası gönderildi") OPS LOG'udur,
        # kullaniciya basilmaz -- kanal disi (etiket != koken, DEV dersi).
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr in ("debug", "info", "warning", "warn", "error",
                                  "exception", "critical"):
            for a in list(node.args) + [k.value for k in node.keywords]:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    skip.add(id(a))
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in skip]


def js_strings(path):
    src = strip_comments(open(path, encoding="utf-8").read())
    out = []
    for m in re.finditer(r"""(['"`])((?:\\.|(?!\1)[^\\\n])*)\1""", src):
        if len(m.group(2)) > 3:
            out.append((src[:m.start()].count("\n") + 1, m.group(2)))
    return out


def scan_r1_r3(text):
    """[(kural, parca)] — metin bir teslimat anindaligi vaat ediyor mu?"""
    t = coz(text)
    hits = []
    if not RE_DISCLAIM.search(t):
        for m in RE_ANINDA.finditer(t):
            if RE_OKUYUCU_EDIMI.match(t[m.end():m.end() + 14]):
                continue  # "hemen al" -> okuyucuya tavsiye, urun vaadi degil
            lo, hi = max(0, m.start() - NEAR), m.end() + NEAR
            if RE_TESLIMAT.search(t[lo:hi]):
                hits.append(("R1", t[lo:hi].strip()))
                break
    m = RE_EMEKLI_PREF.search(t)
    if m:
        hits.append(("R3", m.group(0).strip()))
    return hits


def canonical_pref_names():
    """/profil radiogroup'undaki dort tercih adi (em-dash'e kadar olan bas)."""
    src = open(os.path.join(TPL, "profil.html"), encoding="utf-8").read()
    names = {}
    for key, inner in RE_PREF_OPT.findall(src):
        txt = re.sub(r"<[^>]+>", "", inner)
        txt = re.sub(r"\{[%{].*?[%}]\}", "", txt, flags=re.S)
        txt = coz(txt).replace("\n", " ").strip()
        head = re.split(r"\s+—\s+", txt)[0].strip()
        # bas emoji ("📰 ") ad degil, isarettir -- nesir yuzeyleri emoji tasimaz
        head = re.sub(r"^[^0-9A-Za-zÇĞİIÖŞÜçğıöşü]+", "", head).strip()
        if head:
            names[key] = head
    return names


def collect_units():
    """[(etiket, satir, metin)] — taranan TUM kanallarin girdi kumesi."""
    units, sizes = [], {}
    tpls = sorted(f for f in os.listdir(TPL) if f.endswith(".html"))
    n = 0
    for f in tpls:
        src = strip_comments(open(os.path.join(TPL, f), encoding="utf-8").read())
        for line, text in tpl_segments(src):
            units.append(("templates/" + f, line, text)); n += 1
    sizes["templates"] = (len(tpls), n)

    for pyf in ("app.py", "blog_content.py"):
        p = os.path.join(ROOT, pyf)
        if not os.path.exists(p):
            continue
        got = py_published(p)
        for line, text in got:
            units.append((pyf, line, text))
        sizes[pyf] = (1, len(got))

    jsn, jsf = 0, 0
    for base, _dirs, files in os.walk(os.path.join(ROOT, "static")):
        for f in sorted(files):
            if not f.endswith(".js"):
                continue
            p = os.path.join(base, f)
            rel = os.path.relpath(p, ROOT)
            jsf += 1
            for line, text in js_strings(p):
                units.append((rel, line, text)); jsn += 1
    sizes["static/**/*.js"] = (jsf, jsn)
    return units, sizes


def _line_blobs_html(path):
    """HTML'i (satir, satir-metni) olarak dondur -- R2 satir no basabilsin."""
    src = strip_comments(open(path, encoding="utf-8").read())
    return [(i + 1, ln) for i, ln in enumerate(src.split("\n")) if ln.strip()]


def run(verbose=False):
    units, sizes = collect_units()
    viol, seen = [], set()
    for rel, line, text in units:
        for code, frag in scan_r1_r3(text):
            key = (rel, line, code, frag[:60].lower())
            if key in seen:
                continue
            seen.add(key)
            viol.append((rel, line, code, frag[:150]))

    # ── R2: tercih adi paritesi ──
    canon = canonical_pref_names()
    if len(canon) != len(PREF_KEYS):
        viol.append(("templates/profil.html", 0, "R2",
                     "tercih radiogroup'u ayristirilamadi (%d/4 ad) — kapi kor"
                     % len(canon)))
    else:
        enum_sources = [("templates/gizlilik.html", _line_blobs_html(
                            os.path.join(TPL, "gizlilik.html")))]
        enum_sources.append(("app.py", py_published(os.path.join(ROOT, "app.py"))))
        want = [v.lower() for v in canon.values()]
        for rel, blobs in enum_sources:
            for lineno, blob in blobs:
                if not PREF_ENUM_HINT.search(blob):
                    continue
                # SAYIM = parantez icinde >=2 ayirici. "Mail tercihleriniz
                # güncellendi." bir sayim DEGILDIR; kapi onu denetlemez.
                for g in re.finditer(r"\(([^()]{10,240})\)", coz(blob)):
                    inner = g.group(1)
                    if len(re.findall(r"[/,]|\bveya\b", inner)) < 2:
                        continue
                    # SAYI listesi sayim degildir: rgba(184,195,255,0.06)
                    parts = [q for q in re.split(r"[/,]|\bveya\b", inner)
                             if len(re.findall(r"[A-Za-zÇĞİIÖŞÜçğıöşü]", q)) >= 3]
                    if len(parts) < 3:
                        continue
                    low = inner.lower()
                    missing = [v for v in want if v not in low]
                    if missing:
                        viol.append((rel, lineno, "R2",
                                     "tercih sayimi /profil adlariyla uyusmuyor "
                                     "— eksik: %s | sayim: %s"
                                     % (", ".join(missing), inner[:90])))
    if verbose:
        for k, (nf, ns) in sizes.items():
            print("  girdi: %-16s %d dosya / %d metin blogu" % (k, nf, ns))
        print("  kanonik tercih adlari: %s" % canon)
    return viol, sizes


def self_test():
    """Pozitif kontrol (85. ders) — sentetik ihlaller, gercek agaca dokunmadan."""
    cases = [
        ("R1", "Sinyal degisiminde anında bildirim gonderilir"),
        ("R1", "Rozet bu geçişi anında yansıtır"),
        ("R3", 'profilinden "Anında" seçeneğini seçebilirsin'),
    ]
    ok = 0
    for want, text in cases:
        got = [c for c, _f in scan_r1_r3(text)]
        print("  [%s] %-52s -> %s" % ("OK" if want in got else "FAIL",
                                      text[:52], got or "-"))
        ok += want in got
    neg = [
        "Kriterlere uyan hisseleri anında listele",
        "kombinasyonlarını anında bulun",
        "bir sinyal oluştuğunda hemen almak değil, beklemekten gelir",
    ]
    for text in neg:
        got = [c for c, _f in scan_r1_r3(text)]
        print("  [%s] NEGATIF %-44s -> %s" % ("OK" if not got else "FAIL",
                                              text[:44], got or "-"))
        ok += not got
    return 0 if ok == len(cases) + len(neg) else 1


def main():
    if "--self-test" in sys.argv:
        print("KAPI 60 pozitif/negatif kontrol:")
        return self_test()
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    viol, sizes = run(verbose)
    total = sum(n for _f, n in sizes.values())
    if total == 0:
        print("KAPI 60 KOR — 0 metin blogu ayristirildi (93. ders)")
        return 1
    if viol:
        print("KAPI 60 — TESLIMAT ANINDALIGI / TERCIH ADI IHLALI: %d" % len(viol))
        print("Mimari EOD-only: sinyal degisimi gunde TEK kez, kapanis sonrasi")
        print("EOD turunda tespit edilir (app.py:3973/4412). 'Anında bildirim'")
        print("mimari olarak 'gunde bir kez' demektir.\n")
        for rel, line, code, frag in sorted(viol):
            print("  %s:%s  [%s]" % (rel, line or "-", code))
            print("      …%s…" % frag.replace("\n", " "))
        print("\nKanon: teslimat zamani SAATIYLE yazilir — 'kapanış sonrası (≈18:30)',")
        print("'19:00'da 1 mail', 'bir sonraki gün sonu turunda'.")
        return 1
    print("KAPI 60 OK — teslimat anindaligi iddiasi yok "
          "(%d metin blogu / %s)" % (total, ", ".join(
              "%s:%d" % (k, n) for k, (_f, n) in sizes.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
