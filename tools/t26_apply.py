#!/usr/bin/env python3
"""T2.6 — skip-link (WCAG 2.4.1 Bypass Blocks) 11/27 -> 26/27.

Uygulama ilkeleri:
  * METIN-ESLESTIRMELI degisiklik; satir numarasi KULLANILMAZ. Curutme turunda
    16 ajanin ortak bulgusu: ayni dosyada birden fazla ekleme yapilinca satir
    numaralari kayar ve plan sessizce yanlis yere yazar.
  * Her eslesme once BENZERSIZ mi diye sayilir; benzersiz degilse dosya ATLANIR
    ve rapora yazilir. Sessiz kismi uygulama YOK.
  * CSS 15 yere kopyalanmaz: `_head.html` 27/27 sablon tarafindan include
    ediliyor (T2.1-C1 ile kanoniklesti) -> tek yere yazilir.

KAPSAM DISI (gerekcesi raporda):
  * offline.html — sayfada header/nav YOK; atlanacak tekrarli blok yok,
    WCAG 2.4.1 uygulanmaz. Kalici muaf.
"""
import re
import shutil
import sys
from pathlib import Path

T = Path("/root/bist30/templates")
DRY = "--apply" not in sys.argv

ANCHOR = '<a href="#main-content" class="skip-link">Ana içeriğe atla</a>'

# 11 kanonik sablonda bugun BIREBIR bu dize var; _head.html'e tasiniyor.
CSS = (
    ".skip-link{position:absolute;top:-40px;left:0;background:#1f6feb;color:#fff;"
    "padding:8px 16px;z-index:9999;text-decoration:none;font-size:14px;font-weight:600;"
    "border-radius:0 0 4px 0}.skip-link:focus{top:0}"
    ":focus-visible{outline:2px solid #1f6feb;outline-offset:2px}"
    ":focus:not(:focus-visible){outline:none}"
)
# Kanonik desenin OLCULMUS iki kusuru (11/11'inde de var, kronik):
#   1) hedefin ustundeki 60px sticky header icerigi ortuyor -> scroll-margin-top
#   2) odak hedefe TASINMIYOR (activeElement BODY kaliyor)  -> tabindex="-1"
CSS_FIX = "#main-content{scroll-margin-top:70px}#main-content:focus{outline:none}"

HEAD_STYLE = (
    "<style>/* T2.6 skip-link (WCAG 2.4.1) — 27 sablonun tek kaynagi */"
    + CSS + CSS_FIX + "</style>\n"
)

# curutme turundan gecmis hedef kapsayicilar (dosya -> mevcut acilis etiketi)
TARGETS = {
    "404.html": "<main>",
    "abd_tarama.html": '<div class="container">',
    "bilanco_takvimi.html": '<div class="container">',
    "blog.html": '<div class="container">',
    "blog_article.html": '<div class="container">',
    "gizlilik.html": '<div class="container">',
    "hakkinda.html": '<main class="container">',
    "heatmap.html": "<main>",
    "iletisim.html": '<div class="container">',
    "kategori.html": '<div class="container">',
    "metodoloji.html": '<div class="container">',
    "profil.html": "<main>",
    "sektor_harita.html": '<div class="container">',
    "sektor_karsilastir.html": '<div class="container">',
    "yasal.html": '<div class="container">',
}

# skip-link'i ZATEN olan 11 sablon: yalniz tabindex kazanacaklar
MEVCUT_11 = ["gucu_yuksek.html", "gundem.html", "hisse.html", "hisseler.html",
             "index.html", "karsilastir.html", "ozet.html", "portfolio.html",
             "sinyal_performans.html", "tarama.html", "varlik.html"]

rapor = []


def oku(f):
    return (T / f).read_text(encoding="utf-8")


def yaz(f, s):
    if DRY:
        return
    p = T / f
    shutil.copy2(p, str(p) + ".t26bak")
    p.write_text(s, encoding="utf-8")


def benzersiz(s, needle):
    return s.count(needle)


def isle(f):
    s = oku(f)
    orig = s
    notlar = []

    # --- 1) anchor: ^<body>$ satirindan hemen sonra
    if "skip-link" in s:
        notlar.append("anchor: ZATEN VAR, atlandi")
    else:
        n = len(re.findall(r"(?m)^<body>$", s))
        if n != 1:
            rapor.append((f, "HATA", f"^<body>$ {n} kez (benzersiz degil)"))
            return
        s = re.sub(r"(?m)^<body>$", "<body>\n" + ANCHOR, s, count=1)
        notlar.append("anchor: eklendi")

    # --- 2) hedef: id + tabindex
    if 'id="main-content"' in s:
        # mevcut 11 -> yalniz tabindex ekle
        m = re.search(r'<(main|div)([^>]*?)id="main-content"([^>]*?)>', s)
        if not m:
            rapor.append((f, "HATA", "id=main-content var ama acilis etiketi ayristirilamadi"))
            return
        if "tabindex" in m.group(0):
            notlar.append("hedef: tabindex ZATEN VAR")
        else:
            yeni = m.group(0)[:-1] + ' tabindex="-1">'
            if benzersiz(s, m.group(0)) != 1:
                rapor.append((f, "HATA", f"hedef etiketi benzersiz degil: {m.group(0)}"))
                return
            s = s.replace(m.group(0), yeni, 1)
            notlar.append(f'hedef: tabindex eklendi -> {yeni}')
    else:
        tgt = TARGETS.get(f)
        if not tgt:
            rapor.append((f, "HATA", "hedef tanimli degil"))
            return
        c = benzersiz(s, tgt)
        if c != 1:
            rapor.append((f, "HATA", f"hedef {tgt!r} {c} kez (benzersiz degil)"))
            return
        yeni = tgt[:-1] + ' id="main-content" tabindex="-1">'
        s = s.replace(tgt, yeni, 1)
        notlar.append(f"hedef: {tgt} -> {yeni}")

    if s != orig:
        yaz(f, s)
    rapor.append((f, "OK", " · ".join(notlar)))


def head_css():
    f = "_head.html"
    s = oku(f)
    if "skip-link" in s:
        rapor.append((f, "OK", "CSS zaten var, atlandi"))
        return
    # PWA meta blogunun sonuna, endif'ten SONRA ekle
    if not s.endswith("\n"):
        s += "\n"
    s += HEAD_STYLE
    yaz(f, s)
    rapor.append((f, "OK", "kanonik .skip-link + #main-content CSS eklendi (27 sablonu kapsar)"))


head_css()
for f in sorted(TARGETS):
    isle(f)
for f in MEVCUT_11:
    isle(f)

print("MOD:", "KURU CALISMA (yazma yok)" if DRY else "UYGULANDI")
print(f"{'dosya':26} {'durum':6} not")
for f, d, n in rapor:
    print(f"{f:26} {d:6} {n}")
hata = [r for r in rapor if r[1] == "HATA"]
print(f"\ntoplam={len(rapor)}  ok={len(rapor)-len(hata)}  HATA={len(hata)}")
sys.exit(1 if hata else 0)
