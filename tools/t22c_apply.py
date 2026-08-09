# -*- coding: utf-8 -*-
"""T2.2 C sinifi (desen 2) — nav link kumesi farki olan 2 sablonu kanonige bagla.

CPO-1357 §3 kararlari:
  (2) hisseler kendine link VERMEZ  -> davranis KORUNUR, mekanizma _header.html'de kosullu
  (3) blog_article eksik nav        -> BUG, kanonige donulur

CPO-1357 §3'teki `request.endpoint` onerisinden SAPMA — IKI olculmus gerekce:

 (i) endpoint adi 'hisseler' DEGIL, 'hisseler_hub'
     (app.py:10287-10288  @app.route("/hisseler")  def hisseler_hub).
     'hisseler' yazilsaydi kosul HER sayfada dogru olur, self-link /hisseler'de de
     gorunurdu — yani korunmasi istenen davranis SESSIZCE bozulurdu.

(ii) DAHA AGIRI: `request` Flask'te Jinja GLOBAL'idir (Flask.create_jinja_environment
     rv.globals.update(request=request, ...)), yani `request is not defined` kontrolu
     ASLA dogru olmaz — sahte bir guard. Istek baglami DISINDA render edilen her
     sablonda `request.endpoint` RuntimeError("Working outside of request context")
     atar. tools/t22_predeploy_gate.py bunu kosarak yakaladi.

Cozum: istek baglamina HIC dokunmayan parametre tabanli guard (hdr_self).
Deterministik, duz Jinja ortaminda test edilebilir, baglam disinda patlamaz.

0 eslesmede GURULTULU basarisizlik (sessiz sifir-eslesme sinifi yasak)."""
import io
import re
import sys

hata = []


def oku(p):
    return io.open(p, encoding="utf-8").read()


def yaz(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def degistir(p, eski, yeni, etiket, beklenen=1):
    s = oku(p)
    n = s.count(eski)
    if n != beklenen:
        hata.append("%s: %s -> %d eslesme (beklenen %d)" % (p, etiket, n, beklenen))
        return False
    yaz(p, s.replace(eski, yeni))
    print("  OK  %-22s %s (%d eslesme)" % (p.split("/")[-1], etiket, n))
    return True


# --- 1) _header.html: /hisseler self-link kosullu ------------------------------
SELF = (
    u'      <a href="/hisseler" role="menuitem">'
    u'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
    u'<rect x="3" y="3" width="18" height="18" rx="2"/>'
    u'<line x1="9" y1="3" x2="9" y2="21"/>'
    u'<line x1="15" y1="3" x2="15" y2="21"/>'
    u'<line x1="3" y1="9" x2="21" y2="9"/>'
    u'<line x1="3" y1="15" x2="21" y2="15"/></svg>'
    u"Tüm Hisseler</a>\n"
)
KOSUL_AC = u"{% if hdr_self is not defined or hdr_self != '/hisseler' %}"
KOSUL_KAPA = u"{% endif %}"
degistir("templates/_header.html", SELF, KOSUL_AC + SELF + KOSUL_KAPA, "self-link kosullu")

# _header.html sozlesme dokumantasyonu: yeni parametre kaydedilir
SOZ_ANKOR = (u"      hdr_trailing_include str  vars. yok  -> </nav> ile arama dugmesi "
             u"arasina eklenecek partial\n")
SOZ_YENI = SOZ_ANKOR + (
    u"      hdr_self             str  vars. yok  -> sayfanin KENDI nav href'i; verilirse\n"
    u"                                             o oge menude GIZLENIR (bulundugun sayfaya\n"
    u"                                             link verme deseni). Bugun tek kullanici:\n"
    u"                                             hisseler.html -> hdr_self='/hisseler'.\n"
    u"                                             NEDEN request.endpoint DEGIL: `request`\n"
    u"                                             Flask'te Jinja global'idir, `is not defined`\n"
    u"                                             asla dogru olmaz ve istek baglami disinda\n"
    u"                                             render RuntimeError atar (olculdu).\n")
degistir("templates/_header.html", SOZ_ANKOR, SOZ_YENI, "sozlesme dokumani")

# --- 2) inline header -> kanonik include ---------------------------------------
for tpl, yerine in (
    (
        "templates/hisseler.html",
        u"{% with hdr_title = 'Tüm BIST Hisseleri', hdr_self = '/hisseler' %}"
        u"{% include '_header.html' %}{% endwith %}",
    ),
    ("templates/blog_article.html", u"{% include '_header.html' %}"),
):
    s = oku(tpl)
    m = re.findall(r"<header\b.*?</header>", s, re.S)
    if len(m) != 1:
        hata.append("%s: <header> blogu %d adet (beklenen 1)" % (tpl, len(m)))
        continue
    yaz(tpl, s.replace(m[0], yerine))
    print(
        "  OK  %-22s inline header -> include (%d bayt -> %d bayt)"
        % (tpl.split("/")[-1], len(m[0]), len(yerine))
    )

# --- 3) blog_article.html: include sonrasi OLU kalan CSS kurallari -------------
# Bu iki kural YALNIZCA silinen <div class="header-right"><div class="page-title">
# icin vardi; include sonrasi hicbir elemana eslesmiyorlar.
for kural, etiket in (
    (u"  .header-right { min-width:0; }\n", "olu .header-right"),
    (
        u"  .page-title { font-size:18px; font-weight:700; color:#f0f6fc; "
        u"white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }\n",
        "olu .page-title",
    ),
):
    degistir("templates/blog_article.html", kural, u"", etiket)

print()
if hata:
    print("APPLY: BASARISIZ (%d)" % len(hata))
    for h in hata:
        print("  ", h)
    sys.exit(1)
print("APPLY: TAMAM")
