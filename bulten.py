"""D-45(c): Akşam Bülteni — resmi kapanış turundan (D-04c) sonra bir kez üretilip
data/bulten/<gün>.json'a dondurulur. Sözleşme (CPO buna göre yazar): GET
/api/bulten/<tarih> -> {tarih, bist100, hareketliler, durum_degisimleri,
isi_haritasi_ozet, onemli_bildirimler, yarin_takvim, updated_at, frozen}.
Saf modül (app.py'ye bağımlı değil); dondurma heatmap.py'nin <gün>.json-yoksa-yaz
desenini tekrarlar (os.link ile üzerine yazmaz), "tarih" alanına göre.
Ürün dili: AL/SAT/yön yok — durum adları business_rules.SIGNAL_LABELS'tan.

D-56 (Bülten v2, O28=A) ek alanlar — hepsi dondurma anında, kural tabanlı (AI yok):
  ozet_cumlesi / ozet_parcalar  günün tek cümlesi (sayfa H1 altı, og:description, JSON-LD);
                                parçalar [[metin, vurgu]] (vurgu '' | 'b' | 'up' | 'dn')
  bist100.seri                  son 30 kapanış [[gün, kapanış]] (günün kendisi resmi kapanış)
  bist100.esik                  {yon: 'dusuk'|'yuksek', tarih|None, seans} — kapanış en az 20
                                seansın en düşüğü/en yükseğiyse; tarih = daha düşük/yüksek
                                kapanışın görüldüğü son gün ("15 Ocak'tan bu yana"); yön resmi
                                değişimin işaretinden. Grafik geçmişi bir önceki işlem gününe
                                (tarih + resmi önceki kapanış ±%0,5) ulaşmıyorsa seri [] ve eşik None.
  sayim                         {n, up, down, flat} — ısı haritası görüntüsünün sayımı (harita
                                cümlesiyle aynı sayı)
  durum_degisimleri[].ad/fiyat/degisim_pct
  isi_haritasi_ozet[]           TEK TANIM: templates/_heatmap.html grup etiketiyle aynı —
                                piyasa değeriyle ağırlıklı ortalama + hisse_sayisi
  onemli_bildirimler[].onem_alanlar  {temel, tutar, yil, yuzde, oran_txt, yaklasik}; oran %0,1'in
                                altındaysa önem hiç yazılmaz
  takvim_gunu, yarin_takvim     sonraki işlem günü ve olayları (temettü tutarları, makro ayrıntı)
  yaklasan                      sonraki işlem günü boşsa sonraki beş işlem gününün olayları (≤5)
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date, timedelta

SIGNAL_LABELS = {"AL": "Güçlü Trend", "SAT": "Trend Bozuldu", "BEKLE": "Yatay"}
_DAY_FILE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\.json\Z")

AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
         "Ekim", "Kasım", "Aralık")
# ayrılma eki ("15 Ocak'tan bu yana")
_AY_ABL = ("Ocak'tan", "Şubat'tan", "Mart'tan", "Nisan'dan", "Mayıs'tan", "Haziran'dan", "Temmuz'dan",
           "Ağustos'tan", "Eylül'den", "Ekim'den", "Kasım'dan", "Aralık'tan")
SERI_N = 30            # hero çizgisi: son 30 işlem günü
ESIK_MIN_SEANS = 20    # "X'ten bu yana en düşük/yüksek" en az bu kadar seansı geçerse yazılır
ESIK_YIL_SEANS = 250   # seride daha düşük/yüksek yoksa ve bu kadar seans varsa "son bir yılın"
SUREKLILIK_TOL = 0.005 # grafik geçmişinin son kapanışı resmi önceki kapanıştan en çok %0,5 sapabilir
ONEM_MIN_PCT = 0.1     # bunun altındaki önem oranı gösterilmez (%0,0 anlamsız)
YAKLASAN_GUN = 5
YAKLASAN_MAX = 5
_TAKVIM_ALANLAR = ("date", "kind", "sub", "date_kind", "ticker", "name", "title", "period", "time",
                   "region", "detail", "donem", "brut_tl", "net_tl", "yield_pct", "pay_date", "taksit")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v


# ── Türkçe biçim yardımcıları ────────────────────────────────────────────────
def iyelik(n):
    """3. tekil iyelik eki (kesmeli), sayının okunuşuna göre: 91'i, 9'u, 2'si, 100'ü, 0'ı.
    templates/_heatmap.html _poss() ile aynı tablo."""
    n = abs(int(n))
    u, t = n % 10, (n // 10) % 10
    if n == 0:
        return "'ı"
    if u:
        return "'" + ["", "i", "si", "ü", "ü", "i", "sı", "si", "i", "u"][u]
    if t:
        return "'" + ["", "u", "si", "u", "ı", "si", "ı", "i", "i", "ı"][t]
    return "'ü" if (n // 100) % 10 else "'i"


def ayrilma(n):
    """Sayıya ayrılma eki: 2025'ten, 2026'dan, 2030'dan, 2040'tan, 2000'den."""
    n = abs(int(n))
    u, t = n % 10, (n // 10) % 10
    if u:
        return "'" + ["", "den", "den", "ten", "ten", "ten", "dan", "den", "den", "dan"][u]
    if t:
        return "'" + ["", "dan", "den", "dan", "tan", "den", "tan", "ten", "den", "dan"][t]
    return "'den"


def bulunma(n):
    """Sayıya bulunma eki: 2026'da, 2025'te, 2023'te."""
    return ayrilma(n)[:-1]


def sayi(v, nd=2):
    """12592.76 -> '12.592,76' (tr-TR)."""
    s = "{:,.{nd}f}".format(abs(float(v)), nd=nd).replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" + s) if float(v) < 0 and round(abs(float(v)), nd) else s


def yuzde_mutlak(v, nd=2):
    """2.38 / -2.38 -> '%2,38' (işaretsiz; yön kelimeyle söylenir)."""
    return "%" + sayi(abs(v), nd)


def tarih_uzun(iso, yil=True):
    y, m, d = (int(x) for x in iso[:10].split("-"))
    return "%d %s%s" % (d, AYLAR[m - 1], (" %d" % y) if yil else "")


def _since(iso, day_iso):
    """'15 Ocak'tan' (aynı yıl) / '15 Ocak 2025'ten' (önceki yıl)."""
    y, m, d = (int(x) for x in iso[:10].split("-"))
    if y == int(day_iso[:4]):
        return "%d %s" % (d, _AY_ABL[m - 1])
    return "%d %s %d%s" % (d, AYLAR[m - 1], y, ayrilma(y))


def oran_iyelik(txt):
    """'%16,1' -> "%16,1'i" ; '%41,6' -> "%41,6'sı" ; '%10,0' -> "%10'u" (okunuştaki son sayıya göre)."""
    s = txt.lstrip("~").replace("%", "")
    whole, _, frac = s.partition(",")
    if frac and int(frac or "0"):
        return "%" + whole + "," + frac + iyelik(int(frac))
    return "%" + whole + iyelik(int(whole or "0"))


# ── Endeks ───────────────────────────────────────────────────────────────────
def _index_row(rec, code):
    row = ((rec or {}).get("indices") or {}).get(code) or {}
    close, prev = row.get("close"), row.get("prev_close")
    chg = round((close - prev) / prev * 100, 2) if close and prev else None
    return {"kapanis": close, "degisim_pct": chg}


def onceki_kapanis(close, degisim_pct):
    """Resmi kapanış + resmi % değişimden önceki kapanış (D-56 öncesi görüntüde prev_close yok;
    2 ondalık yüzde yuvarlaması ~%0,005 hata — süreklilik payının çok altında)."""
    if not (_num(close) and close > 0 and _num(degisim_pct)) or degisim_pct <= -100:
        return None
    return close / (1 + degisim_pct / 100.0)


def endeks_gecmisi(ohlc, day_iso, close, onceki_kapanis=None, onceki_gun=None):
    """Grafik barlarından (Yahoo, chart_xu100.json) günden ÖNCEKİ kapanışlar + günün resmi
    kapanışı: [(gün, kapanış)] artan. Günün kapanışı yoksa günden önceki barlar.
    Süreklilik: günün kapanışı eklenecekse geçmişin son barı bir önceki işlem günü olmalı
    (onceki_gun verilirse) ve resmi önceki kapanışa %0,5 içinde yakın olmalı (onceki_kapanis
    verilirse); değilse [] — grafik dosyası bayat/eksikse çizgi ve eşik iddiası hiç yazılmaz."""
    pts = []
    for p in ohlc or []:
        t = str(p.get("time") or "")[:10]
        c = p.get("close")
        if len(t) == 10 and t < day_iso and _num(c) and c > 0:
            pts.append((t, float(c)))
    pts.sort()
    if _num(close) and close > 0:
        if pts and ((onceki_gun and pts[-1][0] != onceki_gun) or
                    (_num(onceki_kapanis) and onceki_kapanis > 0 and
                     abs(pts[-1][1] / onceki_kapanis - 1) > SUREKLILIK_TOL)):
            return []
        pts.append((day_iso, float(close)))
    return pts


def endeks_serisi(pts, day_iso, n=SERI_N):
    """Son n kapanış [[gün, kapanış]]; seri günün kendisiyle bitmiyorsa [] (eksik seri çizilmez)."""
    if not pts or pts[-1][0] != day_iso or len(pts) < 2:
        return []
    return [[d, round(c, 2)] for d, c in pts[-n:]]


def endeks_esik(pts, day_iso, degisim_pct, min_seans=ESIK_MIN_SEANS):
    """Günün kapanışı en az min_seans seansın en düşüğü/en yükseği mi? Yön RESMİ değişimin
    işaretinden (grafikteki komşu bardan değil — cümlenin kendi yüzdesiyle çelişmesin).
    -> {yon, tarih, seans} | None. tarih: daha düşük (düşüş günü) / daha yüksek (yükseliş günü)
    kapanışın görüldüğü son gün; seride hiç yoksa None (o zaman ≥ESIK_YIL_SEANS seans şartı)."""
    if not pts or pts[-1][0] != day_iso or len(pts) < 2:
        return None
    if not _num(degisim_pct) or round(degisim_pct, 2) == 0:
        return None
    i = len(pts) - 1
    c = pts[i][1]
    down = degisim_pct < 0
    j = i - 1
    while j >= 0 and (pts[j][1] > c if down else pts[j][1] < c):
        j -= 1
    seans = i - j - 1
    if j >= 0:
        if seans < min_seans:
            return None
        return {"yon": "dusuk" if down else "yuksek", "tarih": pts[j][0], "seans": seans}
    if seans < ESIK_YIL_SEANS:
        return None
    return {"yon": "dusuk" if down else "yuksek", "tarih": None, "seans": seans}


# ── Isı haritası özeti (tek tanım) ───────────────────────────────────────────
def sayim(heatmap_snap):
    """Isı haritası cümlesiyle aynı sayım: görüntünün counts'u; yoksa satırlardan, görünen
    (2 ondalık) değişimle (templates/_heatmap.html ile aynı yedek)."""
    if not heatmap_snap:
        return None
    rows = heatmap_snap.get("rows") or []
    n = heatmap_snap.get("n") or len(rows)
    c = heatmap_snap.get("counts")
    if c:
        return {"n": n, "up": c.get("up") or 0, "down": c.get("down") or 0, "flat": c.get("flat") or 0}
    up = down = flat = 0
    for r in rows:
        d1 = (r.get("ch") or {}).get("d1")
        if not _num(d1):
            continue
        v = round(d1, 2)
        if v > 0:
            up += 1
        elif v < 0:
            down += 1
        else:
            flat += 1
    return {"n": n, "up": up, "down": down, "flat": flat}


def isi_haritasi_ozet(heatmap_snap):
    """Sektör başına PİYASA DEĞERİYLE AĞIRLIKLI günlük değişim + hisse sayısı (donmuş ısı
    haritası görüntüsünden; D-42). templates/_heatmap.html grup etiketi ve /sektor-harita
    sıralamasıyla BİREBİR aynı tanım: piyasa değeri olan satırlar sayılır, değişimi olanlar
    piyasa değeriyle tartılır. Böylece bülten sayfasında haritadaki ve çubuk grafikteki sektör
    yüzdesi aynı sayıdır (D-56: "tek sayı tanımı")."""
    if not heatmap_snap:
        return []
    groups = {}
    order = []
    for r in heatmap_snap.get("rows") or []:
        g, m = r.get("g"), r.get("mcap")
        if not g or not _num(m) or not m:
            continue
        if g not in groups:
            groups[g] = [0, 0.0, 0.0]
            order.append(g)
        st = groups[g]
        st[0] += 1
        d1 = (r.get("ch") or {}).get("d1")
        if _num(d1):
            st[1] += d1 * m
            st[2] += m
    out = [{"sektor": g, "ortalama_degisim_pct": round(groups[g][1] / groups[g][2], 4),
            "hisse_sayisi": groups[g][0]} for g in order if groups[g][2]]
    out.sort(key=lambda x: -x["ortalama_degisim_pct"])
    return out


# ── Günün cümlesi ────────────────────────────────────────────────────────────
def ozet_parcalar(day_iso, bist100, esik, say):
    """Kural tabanlı tek cümle, vurgulu parçalar hâlinde:
    'BIST100 %2,38 düşüşle 12.592,76 puanda kapandı, 15 Ocak'tan bu yana en düşük kapanış;
     endeksteki 100 hissenin 91'i düştü, 9'u yükseldi.'  Kapanış yoksa None."""
    close = (bist100 or {}).get("kapanis")
    if not _num(close):
        return None
    chg = (bist100 or {}).get("degisim_pct")
    P = [["BIST100 ", ""]]
    if _num(chg) and round(chg, 2) != 0:
        down = chg < 0
        P += [[yuzde_mutlak(chg), "dn" if down else "up"], [" düşüşle " if down else " yükselişle ", ""]]
    elif _num(chg):
        P.append(["değişmeden ", ""])
    P += [[sayi(close), "b"], [" puanda kapandı", ""]]
    if esik:
        en = "en düşük" if esik["yon"] == "dusuk" else "en yüksek"
        if esik.get("tarih"):
            P.append([", %s bu yana %s kapanış" % (_since(esik["tarih"], day_iso), en), ""])
        else:
            P.append([", son bir yılın %s kapanışı" % en, ""])
    if say and say.get("n") and (say.get("up") or say.get("down")):
        n, up, dn = say["n"], say.get("up") or 0, say.get("down") or 0
        P.append(["; endeksteki %d hissenin " % n, ""])
        if up == n:
            P += [["tamamı", "up"], [" yükseldi", ""]]
        elif dn == n:
            P += [["tamamı", "dn"], [" düştü", ""]]
        else:
            a = [(dn, "dn", " düştü"), (up, "up", " yükseldi")]
            if up > dn:
                a.reverse()
            first = True
            for k, cls, verb in a:
                if not k:
                    continue
                if not first:
                    P.append([", ", ""])
                P += [["%d%s" % (k, iyelik(k)), cls], [verb, ""]]
                first = False
    P.append([".", ""])
    # komşu düz parçaları birleştir (şablon daha az düğüm basar)
    out = []
    for txt, cls in P:
        if out and not cls and not out[-1][1]:
            out[-1][0] += txt
        else:
            out.append([txt, cls])
    return out


def ozet_cumlesi(parcalar):
    return "".join(p[0] for p in parcalar) if parcalar else None


# ── Durum değişimleri ────────────────────────────────────────────────────────
def durum_degisimleri(changes, stocks=None):
    """changes: [{ticker, old, new}] (resmi kapanış sinyali, önceki gün snapshot'ına göre).
    AL/SAT kodları kanonik etikete çevrilir; etiket değişmeyen (ör. iki BEKLE alt durumu) atılır.
    stocks {ticker: {name, price, change_pct}} verilirse satıra ad/fiyat/degisim_pct eklenir
    (hareketlilerle aynı kaynak: dondurma anındaki resmi kapanış satırı)."""
    out = []
    for c in changes or []:
        old_lbl = SIGNAL_LABELS.get(c.get("old"))
        new_lbl = SIGNAL_LABELS.get(c.get("new"))
        if not new_lbl or not old_lbl or old_lbl == new_lbl:
            continue
        row = {"ticker": c["ticker"], "onceki": old_lbl, "yeni": new_lbl}
        s = (stocks or {}).get(c["ticker"])
        if s:
            if s.get("name"):
                row["ad"] = s["name"]
            if _num(s.get("price")):
                row["fiyat"] = s["price"]
            if _num(s.get("change_pct")):
                row["degisim_pct"] = round(s["change_pct"], 2)
        out.append(row)
    return out


# ── Bildirimler ──────────────────────────────────────────────────────────────
_PARA = {"USD": "$", "EUR": "€", "TRY": "₺"}


def kisa_tutar(v, isaret):
    """441624108 -> '441,6 Mn $' ; 1.0085e9 -> '1,0 Mrd €' ; 950000 -> '950.000 $'."""
    if abs(v) >= 1e9:
        return "%s Mrd %s" % (("%.1f" % (v / 1e9)).replace(".", ","), isaret)
    if abs(v) >= 1e6:
        return "%s Mn %s" % (("%.1f" % (v / 1e6)).replace(".", ","), isaret)
    return "%s %s" % (sayi(v, 0), isaret)


def onem_alanlar(onem):
    """kap_feed.compute_onem çıktısı -> sayfanın cümlesi için yapılandırılmış alanlar
    ('İhale bedeli 137 Mn ₺, şirketin 2025 hasılatının %16,1'i'). Oran %0,1'in altındaysa None."""
    if not isinstance(onem, dict) or not _num(onem.get("pct")) or onem["pct"] < ONEM_MIN_PCT:
        return None
    temel = (onem.get("basis") or "Tutar").split(" / ")[0]
    approx = bool(onem.get("approx"))
    tutar = onem.get("amount_try_txt") or onem.get("amount_txt")
    fx = onem.get("fx") or {}
    if approx:   # döviz: kendi para biriminde kısa yazım (441,6 Mn $), TL karşılığı oranın içinde
        tutar = onem.get("amount_txt")
        if _num(onem.get("amount_try")) and _num(fx.get("rate")) and fx["rate"] > 0:
            tutar = kisa_tutar(onem["amount_try"] / fx["rate"], _PARA.get(fx.get("cur"), fx.get("cur") or ""))
    txt = onem.get("txt") or ("%" + ("%.1f" % onem["pct"]).replace(".", ","))
    return {
        "temel": temel, "tutar": tutar, "yil": onem.get("rev_year"), "yuzde": onem["pct"],
        "yaklasik": approx, "oran_txt": ("yaklaşık " if approx else "") + oran_iyelik(txt),
    }


def onemli_bildirimler(kap_items, n=5):
    """kap_items: kap_feed.public_item(...) çıktısı, o günün rutin-olmayan bildirimleri.
    Sıra: önem oranı (varsa) azalan, sonra en yeni. onem henüz çoğu kayıtta boş
    (metin geri beslemesi birkaç gün sürer) — o durumda yalnız zaman sırası geçerli.
    %0,1'in altındaki oran yazılmaz (onem ve onem_alanlar None)."""
    items = sorted(
        kap_items or [],
        key=lambda it: ((it.get("onem") or {}).get("pct") or 0, it.get("date") or ""),
        reverse=True,
    )[:n]
    out = []
    for it in items:
        al = onem_alanlar(it.get("onem"))
        out.append({
            "ticker": it.get("ticker"), "company": it.get("company"), "title": it.get("title"),
            "href": it.get("href"), "onem": (it.get("onem") or {}).get("txt") if al else None,
            "onem_alanlar": al,
        })
    return out


# ── Takvim ───────────────────────────────────────────────────────────────────
def _takvim_olay(e):
    return {k: e.get(k) for k in _TAKVIM_ALANLAR if e.get(k) is not None}


def _kesin(e):
    """Bülten yalnız tarihi kesin olayları yazar: tahmini bilanço tarihi / genel kurulu beklenen
    temettü bir olay değildir (takvim sayfası onları kendi etiketiyle gösterir)."""
    return e.get("date_kind") in (None, "kesin")


def yarin_takvim(events, next_day_iso):
    """events: takvim.build()['events'] (bilanço/temettü/makro); yalnız ertesi işlem günü.
    Satır sayfanın yazdığı her alanı taşır (temettü brüt/net/verim/ödeme, makro bölge/ayrıntı)."""
    return [_takvim_olay(e) for e in (events or []) if e.get("date") == next_day_iso and _kesin(e)]


def onceki_islem_gunu(day_iso, is_trading_day):
    """day_iso'dan ÖNCEKİ işlem günü (iso) — grafik geçmişi süreklilik denetimi için."""
    d = date.fromisoformat(day_iso)
    for _ in range(14):
        d = d - timedelta(days=1)
        if is_trading_day(d):
            return d.isoformat()
    return None


def sonraki_islem_gunleri(day_iso, n, is_trading_day):
    """day_iso'dan SONRAKİ n işlem günü (iso, artan)."""
    d = date.fromisoformat(day_iso)
    out = []
    for _ in range(n * 3 + 14):
        d = d + timedelta(days=1)
        if is_trading_day(d):
            out.append(d.isoformat())
            if len(out) >= n:
                break
    return out


def yaklasan_takvim(events, gunler, n=YAKLASAN_MAX):
    """Sonraki işlem günü boşken: gunler (sonraki beş işlem günü) içindeki olaylar, takvim
    sırasıyla, en çok n."""
    gs = set(gunler or [])
    return [_takvim_olay(e) for e in (events or []) if e.get("date") in gs and _kesin(e)][:n]


# ── Görüntü ──────────────────────────────────────────────────────────────────
def build(day_iso, rec, movers, changes, heatmap_snap, kap_items, takvim_events, next_day_iso, updated_at,
          xu100_ohlc=None, stocks=None, takvim_gunleri=None, onceki_gun=None):
    """takvim_gunleri: next_day_iso'dan başlayan sonraki beş işlem günü (yaklaşan olaylar için).
    onceki_gun: bir önceki işlem günü (grafik geçmişi süreklilik denetimi)."""
    ix = _index_row(rec, "XU100")
    prev = (((rec or {}).get("indices") or {}).get("XU100") or {}).get("prev_close")
    pts = endeks_gecmisi(xu100_ohlc, day_iso, ix["kapanis"], onceki_kapanis=prev,
                         onceki_gun=onceki_gun) if xu100_ohlc else []
    esik = endeks_esik(pts, day_iso, ix["degisim_pct"])
    ix["seri"] = endeks_serisi(pts, day_iso)
    ix["esik"] = esik
    say = sayim(heatmap_snap)
    parts = ozet_parcalar(day_iso, ix, esik, say)
    yarin = yarin_takvim(takvim_events, next_day_iso)
    yaklasan = [] if yarin else yaklasan_takvim(takvim_events, takvim_gunleri or [next_day_iso])
    return {
        "tarih": day_iso,
        "bist100": ix,
        "ozet_cumlesi": ozet_cumlesi(parts),
        "ozet_parcalar": parts,
        "sayim": say,
        "hareketliler": movers or {"up": [], "down": []},
        "durum_degisimleri": durum_degisimleri(changes, stocks),
        "isi_haritasi_ozet": isi_haritasi_ozet(heatmap_snap),
        "onemli_bildirimler": onemli_bildirimler(kap_items),
        "takvim_gunu": next_day_iso,
        "yarin_takvim": yarin,
        "yaklasan": yaklasan,
        "updated_at": updated_at,
        "frozen": True,
    }


def eksikleri_tamamla(snap, heatmap_snap=None, xu100_ohlc=None, stocks=None, kap_by_href=None,
                      onceki_gun=None):
    """D-56 öncesi dondurulmuş görüntüye yeni alanları EKLER (tools/bulten_v2_tamamla.py).
    Var olan değerlere dokunmaz; tek istisna isi_haritasi_ozet — tanım ağırlıklıya geçtiği için
    aynı donmuş ısı haritası görüntüsünden yeniden hesaplanır (gün verisi değişmez, yalnız
    toplama kuralı). Grafik geçmişi yok/boş ya da güne kesintisiz ulaşmıyorsa seri/eşik (ve
    onlara bağlı cümle) YAZILMAZ — sonraki koşu doldurur. Değişen anahtar listesini döner."""
    day = snap["tarih"]
    changed = []
    ix = snap.setdefault("bist100", {"kapanis": None, "degisim_pct": None})
    if xu100_ohlc and ("seri" not in ix or "esik" not in ix):
        pts = endeks_gecmisi(xu100_ohlc, day, ix.get("kapanis"),
                             onceki_kapanis=onceki_kapanis(ix.get("kapanis"), ix.get("degisim_pct")),
                             onceki_gun=onceki_gun)
        seri = endeks_serisi(pts, day)
        if seri:
            ix["seri"] = seri
            ix["esik"] = endeks_esik(pts, day, ix.get("degisim_pct"))
            changed.append("bist100.seri/esik")
    if heatmap_snap is not None:
        if "sayim" not in snap:
            snap["sayim"] = sayim(heatmap_snap)
            changed.append("sayim")
        yeni = isi_haritasi_ozet(heatmap_snap)
        if yeni and yeni != snap.get("isi_haritasi_ozet"):
            snap["isi_haritasi_ozet"] = yeni
            changed.append("isi_haritasi_ozet")
    if "ozet_parcalar" not in snap and "esik" in ix:
        parts = ozet_parcalar(day, ix, ix.get("esik"), snap.get("sayim"))
        snap["ozet_parcalar"] = parts
        snap["ozet_cumlesi"] = ozet_cumlesi(parts)
        changed.append("ozet")
    if stocks:
        for row in snap.get("durum_degisimleri") or []:
            s = stocks.get(row.get("ticker")) or {}
            for k_src, k_dst in (("name", "ad"), ("price", "fiyat"), ("change_pct", "degisim_pct")):
                if k_dst not in row and s.get(k_src) is not None:
                    row[k_dst] = round(s[k_src], 2) if k_dst == "degisim_pct" else s[k_src]
                    if "durum_degisimleri" not in changed:
                        changed.append("durum_degisimleri")
    if kap_by_href is not None:
        for row in snap.get("onemli_bildirimler") or []:
            if "onem_alanlar" in row:
                continue
            al = onem_alanlar((kap_by_href.get(row.get("href")) or {}).get("onem"))
            row["onem_alanlar"] = al
            if not al:
                row["onem"] = None
            if "onemli_bildirimler" not in changed:
                changed.append("onemli_bildirimler")
    if "takvim_gunu" not in snap:
        snap["takvim_gunu"] = None
    return changed


# ── Donmuş görüntü (disk) ─────────────────────────────────────────────────────
def save_frozen(snap, dir_):
    """<dir>/<tarih>.json atomik ve YALNIZ YOKSA yazılır (os.link: var olanın üzerine
    yazmaz). Yazıldıysa yol, o gün zaten donmuşsa None."""
    os.makedirs(dir_, exist_ok=True)
    path = os.path.join(dir_, "%s.json" % snap["tarih"])
    if os.path.exists(path):
        return None
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            return None
    finally:
        os.unlink(tmp)
    return path


def days(dir_):
    """Donmuş görüntüsü olan günler, artan ('2026-09-25', ...); klasör yoksa []."""
    try:
        return sorted(n[:-5] for n in os.listdir(dir_) if _DAY_FILE.match(n))
    except OSError:
        return []


def latest_path(dir_):
    d = days(dir_)
    return os.path.join(dir_, d[-1] + ".json") if d else None


_ARSIV_MEM = {}   # {yol: (mtime, satır)}


def arsiv(dir_):
    """/bulten/arsiv ve sayfa altı şeridi: her donmuş gün için {tarih, kapanis, degisim_pct,
    ozet_cumlesi}, YENİDEN ESKİYE. Dosya mtime'ına göre bellekte (her istekte tüm klasör
    okunmaz); okunamayan gün atlanır."""
    out = []
    for d in reversed(days(dir_)):
        path = os.path.join(dir_, d + ".json")
        try:
            mt = os.path.getmtime(path)
        except OSError:
            continue
        hit = _ARSIV_MEM.get(path)
        if not hit or hit[0] != mt:
            try:
                with open(path, encoding="utf-8") as f:
                    s = json.load(f)
            except (OSError, ValueError):
                continue
            ix = s.get("bist100") or {}
            hit = (mt, {"tarih": d, "kapanis": ix.get("kapanis"), "degisim_pct": ix.get("degisim_pct"),
                        "ozet_cumlesi": s.get("ozet_cumlesi")})
            _ARSIV_MEM[path] = hit
        out.append(hit[1])
    return out
