"""D-43a (O18=A, Ozan 23.09): analiz kapsamı dışındaki paylar.

Riskli pazarlardaki (Gözaltı, Yakın İzleme, Piyasa Öncesi İşlem Platformu) ve
borsada işlem görmeyen paylar analiz evreninden (app.BIST100) çıkar. Sayfaları
200 döner ama sinyal/skor yerine bu modülün notunu taşır; sitemap'e girmez;
portföyünde tutan kullanıcı bayrağı görür. Metinler burada tek yerde durur
(ürün dili: AL/SAT yok, göreli zaman yok, kaynak etiketi yok).
Saf modül: app.py'ye bağımlı değil (py3.9 yerel test).
"""
from __future__ import annotations

# ticker -> neden (pazar adı ya da durum). Pazar bilgisi KAP şirket özetinden (23.09).
OUT_OF_SCOPE = {
    "KONTR": "Gözaltı Pazarı'nda işlem gördüğü",
    "MEGAP": "Yakın İzleme Pazarı'nda işlem gördüğü",
    "KLNMA": "Piyasa Öncesi İşlem Platformu'nda işlem gördüğü",
    "MARKA": "borsada işlem görmediği",
}

LABEL = "Kapsam dışı"


def note(ticker):
    """Kapsam dışı pay için {etiket, neden, metin}; kapsam içindeyse None."""
    reason = OUT_OF_SCOPE.get((ticker or "").upper())
    if not reason:
        return None
    t = ticker.upper()
    return {
        "etiket": LABEL,
        "neden": reason,
        "metin": ("%s, %s için analiz kapsamı dışında. Bu hisse için sinyal ve skor "
                  "üretilmiyor." % (t, reason)),
    }


def faq(ticker):
    """Kapsam dışı sayfanın tek SSS girdisi (JSON-LD FAQPage için)."""
    n = note(ticker)
    if not n:
        return None
    return {"q": "%s için neden sinyal ve skor yok?" % ticker.upper(), "a": n["metin"]}


def portfolio_flags(positions):
    """Portföy pozisyonlarında kapsam dışı olanlar: {ticker: {etiket, metin}}."""
    out = {}
    for p in positions or []:
        if not isinstance(p, dict):
            continue
        t = p.get("ticker")
        n = note(t) if isinstance(t, str) else None
        if n:
            out[t.upper()] = {"etiket": n["etiket"], "metin": n["metin"]}
    return out
