"""D-66 / D-67: yönlendirme ve dizinleme hijyeni — saf yardımcılar (Flask/app.py'yi import etmez).

D-66  /ozet/<gün>: o günün Akşam Bülteni varsa tek 301 → /bulten/<gün> (soru H1'li, Article
      JSON-LD'li aynı gün sayfası); bülteni olmayan eski günler noindex, follow (app.py).
"""


def ozet_hedefi(tarih, bulten_gunleri):
    """/ozet/<tarih> için 301 hedefi ya da None (bülten yok → sayfa noindex, follow ile kalır)."""
    return "/bulten/" + tarih if tarih in set(bulten_gunleri or ()) else None
