# -*- coding: utf-8 -*-
"""FAZ8-P1 / CPO-1360 §4(a) — sablon-yerel :root palet sapmasinin WCAG kalemi.

KAPSAM: YALNIZ --text3. Gerekce, token bazinda olculdu (DEV2-016 §2):
  * --text3 #484f58 -> canli /tarama'da 1313 GORUNUR metin ogesi, 1312'si
    --surface uzerinde => kontrast 2.09:1 (WCAG AA 4.5:1 esiginin YARISI).
    1070'i 10-10.5px, yani "buyuk metin" muafiyeti de YOK.
    Kanonik --bp-text3 #909097 ayni yuzeyde 5.45:1 => GECER.
  * --text3 icin 4 sablonda :root DISINDA ham #484f58 kalintisi: 0 adet.
    Yani cevrim YARIM MIGRASYON uretmez (diger token'larda uretirdi: 73 kalinti).
  * 19 tuketicinin 17'si color (on plan, dark tema => IYILESIR),
    2'si dekoratif arka plan (.trend-bar-fill.weak, .rvol-dot.low) — metin tasimaz.
  * Marka karari DEGIL: gri -> gri, ton acilir. --brand/--al/--gold DISARIDA
    birakildi (marka/sinyal kimligi + 50 ham kalinti => Ozan'a eskale, DEV2-016 §3).

Desen: yerel :root'ta zaten kullanilan alias bicimi (--bg:var(--bp-bg),
--sat:var(--bp-sat)). Yeni bir sozluk uretmez, tokens.css'i tek kaynak yapar.

0 eslesmede GURULTULU basarisizlik.
"""
import io
import sys

HEDEF = ["tarama", "kategori", "abd_tarama", "varlik"]
ESKI = u"--text3:#484f58;"
YENI = u"--text3:var(--bp-text3);"

hata = []
for ad in HEDEF:
    p = "templates/%s.html" % ad
    s = io.open(p, encoding="utf-8").read()
    n = s.count(ESKI)
    if n != 1:
        hata.append("%s: %d eslesme (beklenen 1)" % (p, n))
        continue
    # KALINTI KAPISI: :root disinda ham #484f58 kalirsa palet BOLUNUR
    kalan = s.replace(ESKI, u"").count(u"#484f58")
    if kalan:
        hata.append("%s: :root disinda %d adet ham #484f58 kaldi -> YARIM MIGRASYON" % (p, kalan))
        continue
    io.open(p, "w", encoding="utf-8").write(s.replace(ESKI, YENI))
    print("  OK  %-16s --text3 -> var(--bp-text3)  (ham kalinti: 0)" % (ad + ".html"))

print()
if hata:
    print("APPLY: BASARISIZ (%d)" % len(hata))
    for h in hata:
        print("  ", h)
    sys.exit(1)
print("APPLY: TAMAM (%d sablon)" % len(HEDEF))
