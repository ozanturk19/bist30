"""D-57: Gündem'de gerçek haber — AI derlemesi + kod denetimi + kaynak satırı (O27=A, O27k=A).

Akış (günde 2 baskı, hafta içi 08:30 ve 19:30 TR):
  1. Aday seçimi (KOD): D-45'in topladığı basın başlıkları (data/gundem_girdi/<gün>.json) baskı
     penceresine göre süzülür, aynı olayı anlatan başlıklar kümelenir (yayıncı düzeyinde
     bağımsızlık: "Dünya Ekonomi" + "Dünya Finans" tek yayıncı), açıklayıcı/SEO, yorum ve
     "iddia/kulis" başlıkları elenir, en çok 40 aday H1…H40 olur. Kendi verimiz (Gündem v1
     baskısının rakam maddeleri) F1…Fn, günün rutin dışı KAP bildirimleri K1…Kn.
  2. Yazım (Gemini flash-lite, grounding YOK, mevcut tavanlı `_gemini_call` yolu; baskı başına
     ≤4 çağrı): 5–8 madde, kendi cümlelerimizle, her cümle kanıt kimlikleriyle, yalnız JSON.
  3. Doğrulayıcı (KOD; geçemeyen cümle/madde yayına çıkmaz):
       - her cümle ≥1 geçerli H/F kanıtına eşlenir (yalnız K → AI şirket olgusu yazamaz);
       - sayılar ve "gün ay" tarihleri kanıt metninde birebir geçer;
       - özel adlar (kurum, kişi, ülke, şirket, hisse kodu) kanıt metninde geçer;
       - cümlenin içerik sözcüklerinin en az %40'ı kanıtta geçer (dayanaksız genel cümle atılır);
       - neden-sonuç bağı yalnız kanıt da kuruyorsa; yön (yükseldi/düştü) kanıtla çelişmez;
       - kaynak metinle ortak ≤7 sözcüklük dizi (FSEK m.36 / intihal koruması), başlık kopyası yok;
       - yasak dil: AL/SAT, işlem/hedef dili, göreli zaman, kaynak adı gövdede, iddia/kulis, "Ücretsiz";
       - madde ≥1 basın kanıtı + ≥2 bağımsız dayanak (iki yayıncı ya da yayıncı + kendi verimiz/KAP);
       - hisse çipi yalnız evrende olan ve adı/kodu kanıtta geçen şirket için.
  4. Kaynaklar (O27k=A): yalnız basın kanıtından — yayıncı adı + o yayıncının başlık bağlantısı
     (+ haber tarihi, FSEK m.36). Kendi verimiz ve KAP kaynak etiketi taşımaz.
  5. Saklama: data/gundem_haber/<gün>-<sabah|aksam>.json + latest.json (atomik) ve iç iz
     <gün>-<baskı>.audit.json (adaylar, model çıktısı, cümle cümle karar, maliyet).

Sözleşme (C-72 çizer): GET /api/gundem-haber ve SSR bağlam anahtarı "gundem_haber" →
  {"baski": "2026-10-02T08:30:00+03:00", "baski_label": "2 Ekim 2026 · 08:30",
   "maddeler": [{"id": "g-20261002-1", "kategori": "Türkiye"|"Dünya"|"Piyasa"|"Şirketler"|
                 "Merkez bankaları"|"Emtia", "baslik": "...", "ozet": "1–2 cümle", "hisseler": ["THYAO"],
                 "kaynaklar": [{"ad": "AA", "url": "https://...", "tarih": "2026-10-02"}],
                 "ai": true, "onemli": false}]}
  Akşam baskısında madde numaraları 11'den başlar (aynı gün iki baskının kimlikleri çakışmasın).

Kapatma: GUNDEM_AI=0 (yeni baskı yok). Acil kaldırma: latest.json silinir → API/SSR None.
Ağ yok, Gemini çağrısı yok: model çağrısı dışarıdan verilen `call_model(prompt, max_tokens)`
fonksiyonudur (app.py → `_gemini_call`). Python 3.9 uyumlu.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "data", "gundem_girdi")
OUT_DIR = os.path.join(BASE_DIR, "data", "gundem_haber")

ENABLED = os.environ.get("GUNDEM_AI", "1").strip() != "0"
MODEL = os.environ.get("GUNDEM_AI_MODEL", "gemini-2.5-flash-lite")


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


MAX_MONTH_USD = _env_float("GUNDEM_AI_MAX_USD", "4")   # strateji §6.8: aylık 4 $ üstü → baskı yok
MAX_CALLS = 4               # baskı başına Gemini çağrısı tavanı
MAX_TOKENS = 3000
MIN_ITEMS, MAX_ITEMS, MIN_PUBLISH = 5, 8, 3
MIN_BASES = 2               # madde başına bağımsız dayanak
MAX_CANDIDATES = 40
MAX_KAP = 15
SUPPORT_MIN = 0.4           # cümle içerik sözcüklerinin kanıtta geçme oranı
COPY_NGRAM = 8              # kaynakla ortak 8 sözcüklük dizi = kopya (≤7 serbest)
OZET_MAX, BASLIK_MAX = 260, 70
AUDIT_KEEP_DAYS = 30
SLOTS = (("sabah", 8, 30), ("aksam", 19, 30))
LATE_MAX_H = 4              # süreç baskı saatinde kapalıysa en çok 4 saat gecikmeyle basılır
KATEGORILER = ("Türkiye", "Dünya", "Piyasa", "Şirketler", "Merkez bankaları", "Emtia")

_TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
              "Eylül", "Ekim", "Kasım", "Aralık")
_TR_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
_MONTHS_LOW = None  # aşağıda doldurulur


def _lower_tr(s):
    return (s or "").replace("I", "ı").replace("İ", "i").lower()


_MONTHS_LOW = tuple(_lower_tr(m) for m in _TR_MONTHS)

# ----------------------------------------------------------------------------- yayıncılar

# (besleme adı öneki, görünen ad, izinli alan adları)
PUBLISHERS = (
    ("AA ", "AA", ("aa.com.tr",)),
    ("Dünya ", "Dünya", ("dunya.com",)),
    ("TRT Haber", "TRT Haber", ("trthaber.com",)),
    ("Bloomberg HT", "Bloomberg HT", ("bloomberght.com",)),
)


def publisher(feed_name):
    """'Dünya Finans' -> ('Dünya', ('dunya.com',)). Bilinmeyen besleme: ilk sözcük, alan kısıtı yok."""
    n = (feed_name or "").strip()
    for pre, ad, doms in PUBLISHERS:
        if n == pre.strip() or n.startswith(pre):
            return ad, doms
    return (n.split()[0] if n else ""), ()


def _url_ok(url, doms):
    m = re.match(r"^https?://([^/\s]+)/\S*$", url or "")
    if not m:
        return False
    host = m.group(1).lower()
    return not doms or any(host == d or host.endswith("." + d) for d in doms)


# ----------------------------------------------------------------------------- metin araçları

_WORD_RE = re.compile(r"[0-9A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû&]+")
_STOP = set("""ve ile için bir bu şu o da de den dan ki mi mı mu mü ne en çok daha olarak olan
olduğu olduğunu sonra önce kadar gibi ise ya veya hem ama fakat ancak yüzde göre üzerinde altında
arasında ilişkin yönelik kapsamında karşı tarafından ayrıca yeni son ilk tüm her bazı diğer aynı
oldu olacak etti eden edildi edilen yaptı yapılan yapacak verdi verilen açıkladı açıklandı açıklama
dedi belirtti bildirdi kaydetti ifade söyledi duyurdu olduğunu olmak olması olup var yok nin nın
ın in un ün dir dır milyon milyar trilyon bin dolar lira avro euro tl""".split())

_SEO_RE = re.compile(
    r"\?|\bne zaman\b|\bnedir\b|\bnasıl\b|\bkaç (?:tl|lira|para)\b|\bhangi\b|\bneden\b|\bkimdir\b|"
    r"\bcanlı\b|son dakika|ne kadar|\bişte\b|merak edilen|60 saniyede|piyasa özeti|güne nasıl")
_OPINION_RE = re.compile(r"\biddia|\bkulis|öğrenildi|söylenti|\bünlü\b|kritik uyarı|\bşok\b|\bbomba\b|\bflaş\b|"
                         r"köşe yazısı|\byorum:|\banaliz:")
_CONSUMER_RE = re.compile(r"emekli|maaş|memur|asgari ücret|\bkira|ikramiye|bayram|tatil|bedelli|vergi iadesi|"
                          r"\bzam\b|zammı|akaryakıt|benzin|motorin|\blpg\b|\bsgk\b|bağ-kur|kpss|ösym|\bokul")
_MARKET_RE = re.compile(
    r"borsa|endeks|hisse|faiz|merkez bankas|\bfed\b|\becb\b|enflasyon|petrol|brent|altın|gümüş|emtia|dolar|"
    r"\beuro\b|avro|tahvil|\bpmi\b|büyüme|gsyh|istihdam|işsizlik|ticaret|gümrük|tarife|opec|döviz|piyasa|ihracat|"
    r"ithalat|bütçe|cari açık|kredi|resesyon|nasdaq|s&p|dow jones|\bdax\b|nikkei|bitcoin|doğal gaz|bakır|"
    r"\btcmb\b|\bspk\b|\bbddk\b|hazine|tüik|rezerv|fon|halka arz|yatırım|şirket|banka|imf|dünya bankası|"
    r"yaptırım|enerji|sanayi|imalat|üretim|ihale|sözleşme|satın al|birleşme|tmsf")

# Yasak dil (cümlede biri → cümle atılır). Desen, _lower_tr(metin) üzerinde aranır.
_BANNED = (
    ("al_sat", re.compile(r"\b(?:al|sat|tut)\s+(?:sinyal|öneri|tavsiye|yönlü)|alım fırsat|satış fırsat|"
                          r"\bfırsat|tavsiye|\böner(?:i|il|ir|ilir)|güçlü trend|trend bozuldu")),
    ("islem_dili", re.compile(r"hedef\s*fiyat|fiyat\s*hedef|hedef\s*seviye|giriş\s*(?:fiyat|seviye|nokta)|"
                              r"\bstop\b|zarar\s*kes|k[âa]r\s*al|\br/r\b|risk\s*/\s*ödül|\blong\b|\bshort\b|"
                              r"potansiyel|kaçırma|\btp[12]\b|destek seviye|direnç seviye|alınabilir|satılabilir")),
    ("goreli_zaman", re.compile(r"\b(?:bugün|bugünkü|bugüne|dün|dünkü|yarın|yarınki|günün|bu sabah|bu akşam|"
                                r"bu gece|bu hafta|geçen hafta|gelecek hafta|önümüzdeki hafta|son dakika|"
                                r"az önce|şu anda|şu an|şimdi|geçtiğimiz gün|bu ay|geçen ay|gelecek ay|"
                                r"önümüzdeki ay|bu yıl|geçen yıl|gelecek yıl|önümüzdeki yıl)\b")),
    ("kaynak_govdede", re.compile(r"anadolu ajansı|\btrt\b|bloomberg\s?ht|dünya gazetesi|dunya\.com|"
                                  r"haberine göre|habere göre|kaynaklara göre|ajansa göre")),
    ("iddia", re.compile(r"\biddia|\bkulis|öğrenildi|söylenti")),
    ("gri", re.compile(r"ücretsiz|\bkısmi\b|sınırlı veri|veri tamlığı")),
)
_BANNED_CASED = re.compile(r"\b(?:AL|SAT|BEKLE|TUT)\b")   # büyük harfli sinyal sözcükleri
_SOURCE_CASED = re.compile(r"\bAA\b")                      # yayıncı kısaltması gövdede

_CAUSAL_RE = re.compile(r"nedeniyle|yüzünden|etkisiyle|ardından|sonrasında|sebebiyle|dolayı|bağlı olarak|"
                        r"yol açtı|tetikledi|sayesinde|neden oldu")
_UP_RE = re.compile(r"^(?:yüksel|art|çık|kazan|tırman|sıçra|güçlen|toparlan|rekor)")
_DOWN_RE = re.compile(r"^(?:düş|geril|azal|kaybet|değer kayb|in(?:di|er|miş)|çekil|zayıfla|sert düş)")

# Kanıtta aranmayan, her zaman serbest büyük harfli sözcükler (kökler, küçük harf)
_ENTITY_OK = {"türkiye", "türk", "tl", "borsa", "istanbul", "dolar", "euro", "avro", "merkez"}
_ENTITY_OK |= set(m.replace("I", "ı").replace("İ", "i").lower() for m in (
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"))
_SYNONYMS = {"avro": ("euro",), "euro": ("avro",), "abd": ("amerika", "abd"), "fed": ("federal",),
             "amerika": ("abd",), "tcmb": ("merkez bankası", "merkez bankas"), "ab": ("avrupa birliği", "ab"),
             "ecb": ("avrupa merkez",)}
_INDEX_NAMES = re.compile(r"\b(?:BIST\s?\d+|XU\d+|S&P\s?\d+|Nasdaq\s?\d+|G\d{1,2}|Euro\s?Stoxx\s?\d+|DAX\s?\d+|"
                          r"FTSE\s?\d+|Nikkei\s?\d+|CAC\s?\d+|[A-Z]-\d+|COVID-\d+)\b", re.I)
_NUM_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+\.\d+|\d+(?:,\d+)?)(?![\w])")
_DATE_RE = re.compile(r"\b(\d{1,2})\s+(%s)" % "|".join(_MONTHS_LOW))

# Şirket adı eşlemesi için elle takma adlar (basın kısaltmaları)
ALIASES = {
    "THYAO": ("thy", "türk hava yolları"), "TUPRS": ("tüpraş",), "BIMAS": ("bim",), "EREGL": ("erdemir",),
    "KRDMD": ("kardemir",), "SISE": ("şişecam",), "TCELL": ("turkcell",), "TTKOM": ("türk telekom",),
    "ISCTR": ("iş bankası",), "YKBNK": ("yapı kredi",), "VAKBN": ("vakıfbank",), "HALKB": ("halkbank",),
    "GARAN": ("garanti",), "AKBNK": ("akbank",), "PGSUS": ("pegasus",), "ASELS": ("aselsan",),
    "FROTO": ("ford otosan",), "TOASO": ("tofaş",), "KCHOL": ("koç holding",), "SAHOL": ("sabancı holding",),
    "ARCLK": ("arçelik",), "MGROS": ("migros",), "ENKAI": ("enka",), "TAVHL": ("tav havalimanları",),
    "OTKAR": ("otokar",), "SASA": ("sasa",), "PETKM": ("petkim",), "TTRAK": ("türk traktör",),
    "DOAS": ("doğuş otomotiv",), "AEFES": ("anadolu efes",), "CCOLA": ("coca-cola içecek",),
    "ULKER": ("ülker",), "SOKM": ("şok marketler",), "EKGYO": ("emlak konut",), "TKFEN": ("tekfen",),
}
_GENERIC_FIRST = {"türk", "türkiye", "anadolu", "global", "yapı", "emlak", "ak", "iş", "ege", "doğu", "batı",
                  "orta", "yeni", "büyük", "birleşik", "ulusal", "pasifik", "ral", "dünya", "doğan", "gübre",
                  "enerji", "çelik", "demir", "katılım", "yatırım", "teknoloji", "petrol", "gıda", "ticaret"}


def _words(s):
    return _WORD_RE.findall(s or "")


def _stem(w):
    w = _lower_tr(w)
    return w if (w.isdigit() or len(w) <= 5) else w[:5]


def _content_stems(s):
    out = []
    for w in _words(_strip_index_names(s)):
        lw = _lower_tr(w)
        if lw in _STOP or len(lw) < 3 or lw.isdigit():
            continue
        out.append(_stem(lw))
    return out


def _strip_index_names(s):
    """Endeks/ürün adlarındaki rakamlar (BIST100, S&P 500, G20, F-16) sayı sayılmaz. Uzunluk korunur
    (sayı konumları özgün metinle hizalı kalsın)."""
    return _INDEX_NAMES.sub(lambda m: " " * len(m.group(0)), s or "")


def parse_number(tok):
    """Türkçe biçim: '4.197,50' -> 4197.5; '4,5' -> 4.5; '2.5' -> 2.5; '2026' -> 2026.0"""
    t = tok
    if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$", t):
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return round(float(t), 6)
    except ValueError:
        return None


def numbers(s):
    out = []
    for m in _NUM_RE.finditer(_strip_index_names(s)):
        v = parse_number(m.group(1))
        if v is not None:
            out.append((m.group(1), v, m.start(), m.end()))
    return out


def dates(s):
    return set("%d %s" % (int(d), mth) for d, mth in _DATE_RE.findall(_lower_tr(s)))


def banned_hits(s):
    low = _lower_tr(s)
    hits = [code for code, rx in _BANNED if rx.search(low)]
    if _BANNED_CASED.search(s or ""):
        hits.append("al_sat")
    if _SOURCE_CASED.search(s or ""):
        hits.append("kaynak_govdede")
    return sorted(set(hits))


def _norm_words(s):
    return [_lower_tr(w) for w in _words(s)]


_NUMWORDS = {"milyar", "milyon", "bin", "trilyon", "yüzde"}


def _copy_words(s):
    """Kopya denetimi sözcük dizisi (strateji §6.4.5: özel ad ve sayı dizileri hariç): sayılar, sayı
    sözcükleri ve büyük harfle başlayan sözcükler (özel adlar, kısaltmalar) çıkarılır; kesme
    işaretinden sonraki ek atılır."""
    out = []
    for m in re.finditer(r"[0-9A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû&]+(?:['’][a-zçğıöşüâîû]+)?", s or ""):
        w = re.split(r"['’]", m.group(0))[0]
        if not w or w[0].isdigit() or w[0].isupper():
            continue
        lw = _lower_tr(w)
        if lw not in _NUMWORDS:
            out.append(lw)
    return out


def _ngrams(ws, n):
    return set(tuple(ws[i:i + n]) for i in range(len(ws) - n + 1))


def _longest_run(a, b):
    """İki sözcük dizisinin en uzun ortak ardışık alt dizisi (sözcük sayısı)."""
    best = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


_CONNECTORS = {"ayrıca", "öte", "buna", "bununla", "böylece", "ancak", "bu", "şu", "söz", "diğer", "yine",
               "aynı", "öyle", "dolayısıyla", "nitekim", "üstelik", "fakat", "ama", "özetle", "kısaca", "sonuç",
               "ilk", "son", "toplamda", "genel", "yani", "örneğin", "bunun", "bunlar"}


def _entity_roots(s, aliases=None):
    """Cümledeki özel ad kökleri: cümle başı dışındaki büyük harfle başlayan sözcükler + tüm
    BÜYÜK HARF kısaltmalar. Cümle başındaki sözcük ancak ad olduğu belliyse sayılır: kesme işaretli
    ek almış (Akbank'ın, Şimşek'e) ya da bir şirketin takma adı (Otokar). Ek atılır."""
    names = set()
    for al in (aliases or {}).values():
        names.update(a for a in al if " " not in a)
    out = []
    s2 = _strip_index_names(s)
    # cümle başları: metin başı ve . ! ? : sonrası
    starts = set([0])
    for m in re.finditer(r"[.!?:]\s+", s2):
        starts.add(m.end())
    for m in re.finditer(r"[0-9A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû&\-]+(?:['’][a-zçğıöşüâîû]+)?", s2):
        tok = m.group(0)
        root = re.split(r"['’]", tok)[0].strip("-")
        if not root or not root[0].isalpha():
            continue
        is_caps = len(root) >= 2 and root.upper() == root and any(c.isalpha() for c in root)
        is_cap = root[0].isupper()
        if m.start() in starts:
            nxt = s2[m.end():m.end() + 1]
            if is_caps or (is_cap and (tok != root or _lower_tr(root) in names or
                                       (nxt in ",:" and _lower_tr(root) not in _CONNECTORS))):
                out.append(root)
        elif is_caps or is_cap:
            out.append(root)
    return out


def _ev_words(text):
    return set(_lower_tr(w) for w in re.split(r"[^0-9A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû&]+", text or "") if w)


def _root_in(root, ev_words, ev_low):
    r = _lower_tr(root)
    if "-" in r:
        return all(_root_in(p, ev_words, ev_low) for p in r.split("-") if p)
    if r in _ENTITY_OK or r.startswith("bist"):
        return True
    alts = (r,) + _SYNONYMS.get(r, ())
    for a in alts:
        if " " in a:
            if a in ev_low:
                return True
        elif any(w.startswith(a) for w in ev_words):
            return True
    return False


def _direction(words_after):
    for w in words_after[:4]:
        if _UP_RE.match(w):
            return 1
        if _DOWN_RE.match(w):
            return -1
    return 0


# ----------------------------------------------------------------------------- baskı zamanı

def _iso(now):
    return now.strftime("%Y-%m-%dT%H:%M:00+03:00")


def baski_label(now):
    return "%d %s %d · %s" % (now.day, _TR_MONTHS[now.month - 1], now.year, now.strftime("%H:%M"))


def slot_key(now, slot):
    return "%s-%s" % (now.date().isoformat(), slot)


def done_keys(base_dir=None):
    try:
        return set(n[:-len(".audit.json")] for n in os.listdir(base_dir or OUT_DIR)
                   if re.match(r"^\d{4}-\d{2}-\d{2}-(?:sabah|aksam)\.audit\.json$", n))
    except OSError:
        return set()


def due(now, done, has_latest=True):
    """Hafta içi; saati geçmiş (≤LATE_MAX_H) ve henüz basılmamış baskı -> 'sabah'|'aksam'|None.
    İlk kurulumda (latest yok) hemen bir baskı."""
    if not has_latest and not done:
        # ilk kurulum: hiç baskı/iz yoksa hemen bir baskı (sonrası normal takvim)
        return "sabah" if now.hour < 12 else "aksam"
    if now.weekday() >= 5:
        return None
    pick = None
    for name, hh, mm in SLOTS:
        t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if t <= now <= t + timedelta(hours=LATE_MAX_H):
            pick = name
    if pick and slot_key(now, pick) not in done:
        return pick
    return None


def v1_ready(now, slot, v1_printed):
    """Gündem v1 (kendi verimiz) aynı baskıda basıldı mı? Basılmadıysa baskı saatinden 30 dk sonra
    v1'siz devam edilir (F olguları boş kalır, basın maddeleri yine yazılır)."""
    if "%s-%s" % (now.date().isoformat(), slot) in (v1_printed or ()):
        return True
    hh, mm = [(h, m) for n, h, m in SLOTS if n == slot][0]
    return now.hour * 60 + now.minute >= hh * 60 + mm + 30


def window_start(now, slot):
    """Aday penceresi: önceki baskı saatinden 2 saat öncesi; en az 14 saat geriye."""
    if slot == "aksam":
        prev = now.replace(hour=8, minute=30, second=0, microsecond=0)
    else:
        d = now.date() - timedelta(days=1)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        prev = datetime(d.year, d.month, d.day, 19, 30)
    return min(prev - timedelta(hours=2), now - timedelta(hours=14))


# ----------------------------------------------------------------------------- 1) aday seçimi

def load_inputs(now, start, base_dir=None):
    """Pencereye düşen günlerin girdi dosyalarındaki başlıklar (ts TR saatine çevrilir)."""
    base = base_dir or INPUT_DIR
    out, seen = [], set()
    d = start.date()
    while d <= now.date():
        try:
            with open(os.path.join(base, "%s.json" % d.isoformat()), encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, ValueError):
            doc = None
        for it in (doc or {}).get("items") or []:
            if not isinstance(it, dict) or not it.get("title") or it.get("id") in seen:
                continue
            ts = it.get("ts")
            try:
                t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=3) if ts else None
            except ValueError:
                t = None
            if t is None or t < start or t > now + timedelta(minutes=5):
                continue
            seen.add(it.get("id"))
            it = dict(it, _t=t)
            # RSS metinlerinde çift kaçışlı varlıklar ("54,5&#039;e") sayı/ad denetimini bozmasın
            it["title"] = _html.unescape(_html.unescape(it.get("title") or "")).strip()
            it["desc"] = _html.unescape(_html.unescape(it.get("desc") or "")).strip()
            out.append(it)
        d += timedelta(days=1)
    return out


_NAME_PHRASES = ((re.compile(r"Avrupa Birliği"), "AB"), (re.compile(r"Avrupa Merkez Bankası|\bAMB\b"), "ECB"),
                 (re.compile(r"Amerika Birleşik Devletleri"), "ABD"),
                 (re.compile(r"Türkiye Cumhuriyet Merkez Bankası"), "TCMB"))


def _named(title):
    """Başlıktaki adlar: kesme işaretli kökler (Otokar'dan), BÜYÜK HARF kısaltmalar (ABD, TCMB) ve
    baş harfi büyük iç sözcükler (Euro Bölgesi → bölgesi); ay/gün adları hariç."""
    out = set()
    for rx, rpl in _NAME_PHRASES:
        title = rx.sub(rpl, title or "")
    for i, m in enumerate(re.finditer(r"[0-9A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû&]+(['’][a-zçğıöşüâîû]+)?", title or "")):
        tok = m.group(0)
        root = re.split(r"['’]", tok)[0]
        if not root or not root[0].isalpha():
            continue
        caps = len(root) >= 2 and root.upper() == root
        if caps or m.group(1) or (i > 0 and root[0].isupper()):
            r = _lower_tr(root)
            if r not in _ENTITY_OK:
                out.add(r)
    return out


def _sig(it):
    t = set(_content_stems(it.get("title")))
    return t, t | set(_content_stems(it.get("desc"))), _named(it.get("title"))


def cluster(items):
    """Aynı olayı anlatan başlıkları kümeler (açgözlü; kümeler birbirine zincirlenmez).
    Başlık benzerliği: ortak kök ≥3 ve ortak/min ≥0,5; ya da başlık+açıklama ortak ≥6 ve ≥0,5.
    Küme gevşek kalabilir (aynı gün iki ayrı imalat verisi gibi); bu yüzden kaynak satırı ve dayanak
    sayısı kümeden değil, maddenin son metnini gerçekten destekleyen başlıklardan hesaplanır."""
    clusters = []
    for it in sorted(items, key=lambda x: x["_t"], reverse=True):
        t, f, nm = _sig(it)
        it["_sig"] = (t, f, nm)
        hit = None
        for c in clusters:
            for m in c["members"]:
                mt, mf, mnm = m["_sig"]
                it_ = len(t & mt)
                # başlık kuralı: adları olan iki başlığın adları ayrışıyorsa (ABD ↔ Euro Bölgesi) aynı olay değil
                same_names = not (nm and mnm) or bool(nm & mnm)
                if same_names and it_ >= 3 and it_ / float(max(1, min(len(t), len(mt)))) >= 0.5:
                    hit = c
                    break
                ifl = len(f & mf)
                if ifl >= 6 and ifl / float(max(1, min(len(f), len(mf)))) >= 0.5:
                    hit = c
                    break
            if hit:
                break
        if hit:
            hit["members"].append(it)
        else:
            clusters.append({"members": [it]})
    for c in clusters:
        pubs = []
        for m in c["members"]:
            for s in m.get("sources") or []:
                ad = publisher(s.get("name"))[0]
                if ad and ad not in pubs:
                    pubs.append(ad)
        c["pubs"] = pubs
    return clusters


def company_aliases(names, universe):
    """{ticker: (takma adlar…)} — kod, tam ad, ayırt edici ilk sözcük, elle takma adlar."""
    out = {}
    for t in universe:
        al = set([_lower_tr(t)])
        nm = _lower_tr(re.sub(r"\s*\((?:[A-Z])\)\s*$", "", names.get(t) or ""))
        nm = re.sub(r"\b(?:a\.ş\.|t\.a\.ş\.|a\.s\.)", "", nm).strip()
        if nm:
            al.add(nm)
            ws = nm.split()
            if len(ws) >= 2:
                al.add(" ".join(ws[:2]))
            if ws and len(ws[0]) >= 5 and ws[0] not in _GENERIC_FIRST:
                al.add(ws[0])
        for a in ALIASES.get(t, ()):
            al.add(a)
        out[t] = tuple(sorted(al, key=len, reverse=True))
    return out


def _mentions(text, aliases):
    """Metinde geçen evren hisseleri (kod BÜYÜK harf sözcük olarak ya da takma ad sözcük başında)."""
    low = " " + _lower_tr(text) + " "
    words = set(re.findall(r"\b[A-Z0-9]{4,6}\b", text or ""))
    hit = set()
    for t, al in aliases.items():
        if t in words:
            hit.add(t)
            continue
        for a in al:
            if a == _lower_tr(t):
                continue
            # tam sözcük eşleşmesi; özel ad ekleri kesme işaretiyle gelir (aselsan'ın, thy'nin)
            if re.search(r"(?<![0-9a-zçğıöşüâîû])" + re.escape(a) + r"(?![0-9a-zçğıöşüâîû])", low):
                hit.add(t)
                break
    return hit


def select_candidates(items, aliases, used_ids=(), limit=MAX_CANDIDATES):
    """Kümeler -> puanlı aday listesi. Önceki baskıda kullanılmış başlıklardan ibaret kümeler atlanır."""
    used = set(used_ids or ())
    cands = []
    for c in cluster(items):
        mem = [m for m in c["members"] if not _SEO_RE.search(_lower_tr(m["title"]))
               and not _OPINION_RE.search(_lower_tr(m["title"]))]
        if not mem:
            continue
        if all(m.get("id") in used for m in c["members"]):
            continue
        rep = max(mem, key=lambda m: (len(m.get("desc") or ""), m["_t"]))
        text = " ".join("%s %s" % (m["title"], m.get("desc") or "") for m in c["members"])
        low = _lower_tr(text)
        mk = len(set(_MARKET_RE.findall(low)))
        cos = _mentions(text, aliases)
        if not mk and not cos:
            continue
        score = 3 * len(c["pubs"]) + min(3, mk) + (2 if cos else 0)
        if _CONSUMER_RE.search(_lower_tr(rep["title"])):
            score -= 4
        groups = [m.get("group") for m in c["members"]]
        cands.append({"rep": rep, "members": c["members"], "pubs": c["pubs"], "score": score,
                      "group": max(set(groups), key=groups.count), "tickers": sorted(cos),
                      "t": max(m["_t"] for m in c["members"])})
    cands.sort(key=lambda x: (-x["score"], -x["t"].timestamp()))
    return cands[:limit]


_V1_FACT_IDS = ("bist", "sektor", "kur", "abd", "emtia", "mb")


def own_facts(v1_doc):
    """Gündem v1 baskısının rakam maddeleri (kod yazdı, kendi verimiz) -> F olguları."""
    out = []
    for g in (v1_doc or {}).get("groups") or []:
        for it in g.get("items") or []:
            if it.get("id") in _V1_FACT_IDS and it.get("p"):
                out.append("%s. %s" % ((it.get("h") or "").rstrip("."), it["p"]))
    return out


def kap_facts(kap_items, names, start, now, mentioned, limit=MAX_KAP):
    """Pencere içindeki rutin dışı KAP bildirimleri: basında adı geçen şirketler önce, sonra önem oranı."""
    s0, s1 = start.strftime("%Y-%m-%dT%H:%M"), now.strftime("%Y-%m-%dT%H:%M:59")
    rows = [it for it in kap_items or [] if isinstance(it, dict) and not it.get("rutin")
            and s0 <= (it.get("ts") or "") <= s1 and it.get("ticker")]
    def key(it):
        on = it.get("onem") or {}
        return (0 if it["ticker"] in mentioned else 1, -(on.get("pct") or 0.0), it.get("ts") or "")
    rows.sort(key=key)
    out, seen = [], set()
    for it in rows:
        if it.get("id") in seen:
            continue
        seen.add(it.get("id"))
        on = it.get("onem") or {}
        txt = "%s (%s) · %s · %s" % (it["ticker"], names.get(it["ticker"], it["ticker"]),
                                     it.get("class") or "", (it.get("title") or "").strip())
        if on.get("formula"):
            txt += " · %s" % on["formula"]
            if on.get("amount_txt"):
                txt += " · tutar %s" % on["amount_txt"]
        out.append({"text": txt, "ticker": it["ticker"], "kap_id": it.get("id")})
        if len(out) >= limit:
            break
    return out


def build_evidence(cands, facts, kaps):
    """Kimlik -> kanıt kaydı. H metni kümenin TÜM üyeleriyle (sayı/ad denetimi için)."""
    ev = {}
    for i, c in enumerate(cands, 1):
        pubs, mems = {}, []
        for m in sorted(c["members"], key=lambda x: x["_t"]):
            links = []
            for s in m.get("sources") or []:
                ad, doms = publisher(s.get("name"))
                url = (s.get("url") or "").strip()
                if ad and _url_ok(url, doms):
                    links.append({"ad": ad, "url": url, "tarih": m["_t"].date().isoformat()})
                    pubs.setdefault(ad, links[-1])
            text = "%s. %s" % (m["title"], m.get("desc") or "")
            mems.append({"id": m.get("id"), "text": text, "links": links,
                         "tstems": set(_content_stems(m["title"])), "astems": set(_content_stems(text))})
        ev["H%d" % i] = {"kind": "H", "text": " ".join(x["text"] for x in mems),
                         "titles": [m["title"] for m in c["members"]], "pubs": pubs, "group": c["group"],
                         "ids": [m.get("id") for m in c["members"]], "tickers": c["tickers"], "members": mems}
    for i, f in enumerate(facts, 1):
        ev["F%d" % i] = {"kind": "F", "text": f, "titles": [], "pubs": {}, "ids": [], "tickers": []}
    for i, k in enumerate(kaps, 1):
        ev["K%d" % i] = {"kind": "K", "text": k["text"], "titles": [], "pubs": {}, "ids": [],
                         "tickers": [k["ticker"]]}
    return ev


# ----------------------------------------------------------------------------- 2) istem

_PROMPT = """Sen BorsaPusula için ekonomi ve piyasa gündemi derleyen bir editörsün. Aşağıda {label} baskısı için toplanmış haber başlıkları (H…), sitemizin kendi piyasa verisi (F…) ve şirketlerin KAP bildirimleri (K…) var. Baskı tarihi: {tarih}.

GÖREV: Bu malzemeden piyasa ve ekonomi açısından en önemli {n} haberi seç; her birini KENDİ cümlelerinle yaz.

KURALLAR
1. Yalnız verilen malzemedeki bilgiyi kullan. Malzemede olmayan olgu, sayı, tarih, kişi, kurum, ülke ya da şirket adı yazma. Tahmin, yorum, değerlendirme ekleme.
2. Her cümlenin "kanit" listesine bilginin geldiği kimlikleri yaz (ör. ["H3"], ["H2","F1"]). Her cümlede en az bir H ya da F kimliği olsun. Her maddede en az bir H olsun.
3. Sayıları ve tarihleri kaynaktaki gibi aynen yaz (ör. "%2,92", "4,5", "22 Ekim"); yuvarlama, birim çevirme, hesap yapma.
4. Kopyalama: başlığı ve cümleleri kaynak başlıktan aynen alma; aynı bilgiyi başka sözcüklerle, sade Türkçeyle anlat. Bir kaynaktan art arda 5'ten fazla sözcüğü aynen kullanma.
5. Neden-sonuç bağını (nedeniyle, ardından, etkisiyle) yalnız kaynak metin bu bağı kuruyorsa yaz.
6. Şunları yazma: al/sat/tut önerisi, tavsiye, fırsat, potansiyel, hedef fiyat, stop, giriş seviyesi; göreli zaman sözcükleri (bugün, dün, yarın, bu hafta, bu yıl, geçen yıl; yerine kaynaktaki tarihi yaz ya da hiç yazma); yayın kuruluşu adları (kaynakları biz ayrıca gösteriyoruz); "iddia", "kulis", "öğrenildi" haberleri.
7. Şirketler hakkında yargı bildirme ("güçlü", "zayıf", "başarılı"); yalnız olanı betimle.
8. "baslik" en fazla 70 karakter. "cumleler" 1 ya da 2 cümle, toplam en fazla 260 karakter.
9. "kategori" şunlardan biri: "Türkiye", "Dünya", "Piyasa", "Şirketler", "Merkez bankaları", "Emtia". En az 2 madde Türkiye'den, en az 2 madde dünyadan olsun.
10. "hisseler": yalnız haberin doğrudan konusu olan ve kanıtta adı ya da kodu geçen Borsa İstanbul şirketlerinin kodları (K satırlarındaki kodlar). Emin değilsen boş bırak.
11. Çok yayıncıda geçen (yayıncı sayısı yüksek) haberleri öne al. Yalnız fiyat hareketini anlatan madde en fazla 1 tane olsun. Aynı olayı iki maddede anlatma.{extra}

ÇIKTI: Yalnız JSON, başka metin yok:
{{"maddeler":[{{"kategori":"...","baslik":"...","baslik_kanit":["H1"],"cumleler":[{{"metin":"...","kanit":["H1","F2"]}}],"hisseler":[]}}]}}

MALZEME
{material}
"""


def _clip(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"


def material(cands, ev, exclude=()):
    lines = []
    for hid, e in ev.items():
        if e["kind"] != "H" or hid in exclude:
            continue
        c = cands[int(hid[1:]) - 1]
        rep = c["rep"]
        alt = [m["title"] for m in c["members"] if m is not rep][:2]
        grp = "Türkiye" if c["group"] == "turkiye" else "Dünya"
        line = "%s [%s · %d yayıncı] %s — %s" % (hid, grp, len(c["pubs"]), rep["title"], _clip(rep.get("desc"), 300))
        if alt:
            line += " | Diğer başlıklar: " + " / ".join(alt)
        lines.append(line)
    for hid, e in ev.items():
        if e["kind"] in ("F", "K"):
            lines.append("%s %s" % (hid, e["text"]))
    return "\n".join(lines)


def build_prompt(cands, ev, now, slot, n=MAX_ITEMS, exclude=(), feedback=None):
    label = "%s %s" % (baski_label(now).split(" · ")[0], "sabah" if slot == "sabah" else "akşam")
    tarih = "%d %s %d %s" % (now.day, _TR_MONTHS[now.month - 1], now.year, _TR_DAYS[now.weekday()])
    extra = ""
    if feedback:
        extra = "\n12. " + feedback
    return _PROMPT.format(label=label, tarih=tarih, n=("6–%d" % n) if n > 6 else str(n), extra=extra,
                          material=material(cands, ev, exclude))


# ----------------------------------------------------------------------------- 3) doğrulayıcı

def parse_response(text):
    """Model metni -> madde listesi | None. ```json çitleri ve baştaki/sondaki gürültü temizlenir."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        obj = json.loads(t[i:j + 1])
    except ValueError:
        return None
    items = obj.get("maddeler") if isinstance(obj, dict) else None
    return [x for x in items if isinstance(x, dict)] if isinstance(items, list) else None


def _ids(v, ev):
    if isinstance(v, str):
        v = re.findall(r"[HFK]\d+", v)
    return [x.strip().upper() for x in (v or []) if isinstance(x, str) and x.strip().upper() in ev]


class Ctx(object):
    """Doğrulama bağlamı: kanıt kayıtları, kopya denetimi için tüm H metinleri, serbest tarihler."""

    def __init__(self, ev, allowed_dates=(), aliases=None, universe=(), year=None):
        self.ev = ev
        self.aliases = aliases or {}
        self.universe = set(universe or ())
        self.allowed_dates = set(allowed_dates or ())
        self.year = float(year) if year else None   # baskı yılı tarih olarak serbest
        self.h_texts = [_copy_words(e["text"]) for e in ev.values() if e["kind"] == "H"]
        self.h_ngrams = set()
        for ws in self.h_texts:
            self.h_ngrams |= _ngrams(ws, COPY_NGRAM)


def allowed_dates_for(now, close_day=None):
    out = set()
    for d in (now.date(), close_day):
        if d:
            out.add("%d %s" % (d.day, _MONTHS_LOW[d.month - 1]))
    return out


def check_text(text, ids, item_ids, ctx, is_title=False):
    """Bir cümle/başlık için ret sebepleri listesi (boş = geçti).
    ids: bu cümlenin kanıtları; item_ids: maddenin tüm kanıtları (sayı/ad/tarih denetimi bunlarla)."""
    reasons = []
    ev = ctx.ev
    if not is_title and not any(ev[i]["kind"] in ("H", "F") for i in ids):
        reasons.append("kanit_yok")
    pool = item_ids or ids
    ev_text = " ".join(ev[i]["text"] for i in pool)
    ev_low = _lower_tr(ev_text)
    ev_words = _ev_words(ev_text)
    for b in banned_hits(text):
        reasons.append("yasak_dil:%s" % b)
    ev_nums = set(v for _, v, _, _ in numbers(ev_text))
    sw = _norm_words(text)
    # "22 Ekim" gibi tarihlerin gün rakamı tarih denetimine kalır (sayı denetiminde atlanır)
    date_spans = [(m.start(), m.end()) for m in _DATE_RE.finditer(_lower_tr(_strip_index_names(text)))]
    for tok, v, st, en in numbers(text):
        if any(a <= st < b for a, b in date_spans):
            continue
        if v in ev_nums or (ctx.year is not None and v == ctx.year):
            continue
        reasons.append("sayi:%s" % tok)
    ev_dates = dates(ev_text)
    for d in dates(text):
        if d not in ev_dates and d not in ctx.allowed_dates:
            reasons.append("tarih:%s" % d)
    for root in _entity_roots(text, ctx.aliases):
        if not _root_in(root, ev_words, ev_low):
            reasons.append("ad:%s" % root)
    if _CAUSAL_RE.search(_lower_tr(text)) and not _CAUSAL_RE.search(ev_low):
        reasons.append("neden_bag")
    # yön: kanıtta işaretli yüzde (+%2,92 / −%0,10) ya da "yüzde N düştü" ile cümle çelişmesin
    low = _lower_tr(text)
    for tok, v, st, en in numbers(text):
        after = _norm_words(low[en:])[:4]
        sd = _direction(after)
        if not sd:
            continue
        for m in re.finditer(r"([+−\-])\s?%\s?" + re.escape(tok) + r"(?![\d,])", ev_text):
            evd = 1 if m.group(1) == "+" else -1
            if evd != sd:
                reasons.append("yon:%s" % tok)
            break
    # destek: içerik sözcüklerinin ≥%40'ı kanıtta
    cs = _content_stems(text)
    if cs:
        ev_stems = set(_stem(w) for w in ev_words)
        sup = sum(1 for s in cs if s in ev_stems) / float(len(cs))
        if sup < SUPPORT_MIN:
            reasons.append("dayanak:%.2f" % sup)
    # kopya: tüm H metinleriyle ortak 8 sözcüklük dizi (sayılar hariç)
    if _ngrams(_copy_words(text), COPY_NGRAM) & ctx.h_ngrams:
        reasons.append("kopya")
    if is_title:
        if len(text) > BASLIK_MAX:
            reasons.append("uzun_baslik")
        cw = _copy_words(text)
        n = len(cw)
        for i in pool:
            for t in ev[i]["titles"]:
                run = _longest_run(cw, _copy_words(t))
                if run > max(3, int(0.6 * n)):
                    reasons.append("baslik_kopya")
                    break
            else:
                continue
            break
    return sorted(set(reasons), key=reasons.index)


def _norm_kategori(k, group):
    k = (k or "").strip()
    for c in KATEGORILER:
        if _lower_tr(k) == _lower_tr(c):
            return c
    return "Dünya" if group == "dunya" else "Türkiye"


def validate_item(raw, ctx):
    """Model maddesi -> (yayımlanacak madde | None, rapor)."""
    ev = ctx.ev
    rep = {"baslik": raw.get("baslik"), "cumleler": [], "karar": None}
    sents = raw.get("cumleler")
    if isinstance(sents, str):
        sents = [{"metin": sents, "kanit": raw.get("kanit") or []}]
    if not isinstance(sents, list):
        sents = []
    sents = [s for s in sents if isinstance(s, dict) and isinstance(s.get("metin"), str) and s["metin"].strip()]
    title = (raw.get("baslik") or "").strip() if isinstance(raw.get("baslik"), str) else ""
    t_ids = _ids(raw.get("baslik_kanit"), ev)
    all_ids = list(dict.fromkeys(t_ids + [i for s in sents for i in _ids(s.get("kanit"), ev)]))
    kept, kept_ids = [], list(t_ids)
    for s in sents:
        sid = _ids(s.get("kanit"), ev)
        r = check_text(s["metin"].strip(), sid, all_ids, ctx)
        rep["cumleler"].append({"metin": s["metin"], "kanit": sid, "ret": r})
        if not r:
            kept.append(s["metin"].strip())
            kept_ids += sid
    if not title:
        rep["karar"] = "baslik_yok"
        return None, rep
    tr = check_text(title, t_ids or all_ids, all_ids, ctx, is_title=True)
    rep["baslik_ret"] = tr
    if tr:
        rep["karar"] = "baslik_ret"
        return None, rep
    ozet = ""
    for s in kept[:2]:
        cand = (ozet + " " + s).strip()
        if len(cand) > OZET_MAX:
            break
        ozet = cand
    if not ozet:
        rep["karar"] = "cumle_kalmadi"
        return None, rep
    used = [i for i in dict.fromkeys(kept_ids) if i in ev]
    hs = [i for i in used if ev[i]["kind"] == "H"]
    if not hs:
        rep["karar"] = "basin_kaniti_yok"
        return None, rep
    # Başlık düzeyinde dayanak: maddenin son metnini gerçekten destekleyen başlıklar
    # (başlık köklerinin ≥%40'ı metinde ya da metin köklerinin ≥%50'si başlık+açıklamada).
    final = title + " " + ozet
    fs = set(_content_stems(final))
    fnums = set(v for _, v, _, _ in numbers(final)) - set([ctx.year])
    support = []
    for i in hs:
        for m in ev[i]["members"]:
            r1 = len(m["tstems"] & fs) / float(len(m["tstems"])) if m["tstems"] else 0.0
            r2 = len(m["astems"] & fs) / float(len(fs)) if fs else 0.0
            nh = bool(fnums & set(v for _, v, _, _ in numbers(m["text"])))
            if r1 >= 0.4 or r2 >= 0.35 or (nh and r1 >= 0.25):
                support.append(m)
    own = [i for i in used if ev[i]["kind"] in ("F", "K")]
    if not support:
        rep["karar"] = "kaynak_eslesmedi"
        return None, rep
    # son metin, yalnız destekleyen başlıklar + kendi verimiz/KAP ile yeniden denetlenir
    sub = dict((k, v) for k, v in ev.items() if k in own)
    sub["_S"] = {"kind": "H", "text": " ".join(m["text"] for m in support), "titles": []}
    sctx = Ctx(sub, ctx.allowed_dates, None, (), ctx.year)
    sctx.h_ngrams = ctx.h_ngrams
    fr = [r for r in check_text(final, ["_S"] + own, ["_S"] + own, sctx)
          if r.split(":")[0] in ("sayi", "tarih", "ad", "neden_bag", "yon")]
    if fr:
        rep["karar"] = "kaynakta_yok:%s" % ",".join(fr)
        return None, rep
    kaynaklar, pubs = [], []
    for m in support:
        for ln in m["links"]:
            if ln["ad"] not in pubs:
                pubs.append(ln["ad"])
                kaynaklar.append(dict(ln))
    bases = len(pubs) + (1 if own else 0)
    if not kaynaklar:
        rep["karar"] = "kaynak_baglantisi_yok"
        return None, rep
    if bases < MIN_BASES:
        rep["karar"] = "tek_dayanak"
        return None, rep
    kaynaklar = kaynaklar[:4]
    # hisse çipleri: evrende + kanıtta (H/K) adı ya da kodu geçen
    ev_txt = " ".join(ev[i]["text"] for i in used if ev[i]["kind"] in ("H", "K"))
    in_ev = _mentions(ev_txt, {t: a for t, a in ctx.aliases.items()}) if ctx.aliases else set()
    for i in used:
        if ev[i]["kind"] == "K":
            in_ev |= set(ev[i]["tickers"])
    tick = []
    hl = raw.get("hisseler")
    hl = [hl] if isinstance(hl, str) else (hl if isinstance(hl, list) else [])
    for t in hl:
        t = (t or "").strip().upper() if isinstance(t, str) else ""
        if t and t in ctx.universe and t in in_ev and t not in tick:
            tick.append(t)
        elif t:
            rep.setdefault("hisse_ret", []).append(t)
    group = ev[hs[0]]["group"]
    rep["karar"] = "yayın"
    return {"kategori": _norm_kategori(raw.get("kategori"), group), "baslik": title, "ozet": ozet,
            "hisseler": tick[:3], "kaynaklar": kaynaklar, "ai": True, "onemli": False,
            "_h": hs, "_pubs": len(pubs)}, rep


def assemble(accepted, now, slot):
    """Kabul edilen maddeler -> sözleşme belgesi (≤8 madde, en çok yayıncılı madde 'onemli')."""
    out = []
    for it in accepted:
        if any(len(set(it["_h"]) & set(o["_h"])) * 2 >= len(it["_h"]) for o in out):
            continue   # aynı olay ikinci kez
        out.append(it)
        if len(out) >= MAX_ITEMS:
            break
    if out:
        top = max(out, key=lambda x: x["_pubs"])
        if top["_pubs"] >= 3:
            top["onemli"] = True
    base = 1 if slot == "sabah" else 11
    ymd = now.strftime("%Y%m%d")
    maddeler = []
    for n, it in enumerate(out):
        m = {"id": "g-%s-%d" % (ymd, base + n)}
        m.update({k: v for k, v in it.items() if not k.startswith("_")})
        maddeler.append(m)
    return {"baski": _iso(now), "baski_label": baski_label(now), "maddeler": maddeler}


# ----------------------------------------------------------------------------- 4) baskı

def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def previous_used_ids(base_dir=None):
    """Son baskının kullandığı başlık kimlikleri (aynı haber bir sonraki baskıda tekrarlanmasın)."""
    base = base_dir or OUT_DIR
    keys = sorted(done_keys(base))
    for k in reversed(keys):
        a = _read_json(os.path.join(base, "%s.audit.json" % k))
        if a and a.get("used_ids"):
            return a["used_ids"]
    return []


def read_cb_state(path):
    """Paylaşımlı Gemini kota sigortası dosyası (/tmp/bp_gemini_quota_cb.json) -> dict (okunamazsa {})."""
    d = _read_json(path) if path else None
    return d if isinstance(d, dict) else {}


def gate(budget_status=None, cb_state=None, now_ts=None):
    """Çağrıdan önce kapı: (True, None) | (False, sebep). Hiçbir durumda istem kurulmaz/çağrı atılmaz.
    budget_status: gemini_budget.status() çıktısı; cb_state: paylaşımlı kota sigortası dosyası."""
    if not ENABLED:
        return False, "GUNDEM_AI=0"
    st = budget_status or {}
    if st and not st.get("enabled", True):
        return False, "GEMINI_ENABLED=0"
    cb = cb_state or {}
    if cb.get("manual_hold"):
        return False, "manual_hold"
    if (cb.get("open_until") or 0) > (now_ts if now_ts is not None else time.time()):
        return False, "kota_sigortasi"
    if st and (st.get("usd_month") or 0) >= MAX_MONTH_USD:
        return False, "aylik_esik"
    if st and (st.get("daily_cap") or 0) - (st.get("calls_today") or 0) < MAX_CALLS:
        return False, "gunluk_tavan"
    return True, None


def run_edition(now, slot, call_model, v1_doc=None, kap_items=None, names=None, universe=(),
                close_day=None, budget_status=None, cb_state=None, base_dir=None, input_dir=None,
                usage_fn=None, log=None):
    """Bir baskı üretir ve kaydeder. call_model(prompt, max_tokens) -> metin | None.
    usage_fn() -> (çağrı_sayısı_bugün, usd_ay) (maliyet logu için; yoksa 0).
    Dönüş: {"durum": "basildi"|"atlandi"|"yetersiz", ...} (audit dosyasıyla aynı özet)."""
    base = base_dir or OUT_DIR
    ok, why = gate(budget_status, cb_state)
    if not ok:
        return {"durum": "atlandi", "sebep": why}
    names = names or {}
    aliases = company_aliases(names, universe or names.keys())
    start = window_start(now, slot)
    items = load_inputs(now, start, input_dir)
    cands = select_candidates(items, aliases, previous_used_ids(base))
    mentioned = set(t for c in cands for t in c["tickers"])
    facts = own_facts(v1_doc)
    kaps = kap_facts(kap_items, names, start, now, mentioned)
    ev = build_evidence(cands, facts, kaps)
    ctx = Ctx(ev, allowed_dates_for(now, close_day), aliases, universe or names.keys(), year=now.year)
    u0 = usage_fn() if usage_fn else (0, 0.0)
    audit = {"key": slot_key(now, slot), "baski": _iso(now), "model": MODEL, "pencere": [start.isoformat(),
             now.isoformat()], "girdi": len(items), "aday": len(cands),
             "adaylar": {k: {"titles": v["titles"][:4], "pubs": list(v["pubs"])} for k, v in ev.items()
                         if v["kind"] == "H"},
             "olgular": {k: v["text"] for k, v in ev.items() if v["kind"] in ("F", "K")},
             "turlar": []}
    accepted, calls, exclude, feedback = [], 0, set(), None
    if len(cands) < MIN_PUBLISH:
        audit.update({"durum": "aday_yetersiz", "cagri": 0})
        _finish(audit, None, base, now, log)
        return _summary(audit)
    while calls < MAX_CALLS and len(accepted) < MIN_ITEMS:
        need = MAX_ITEMS - len(accepted)
        prompt = build_prompt(cands, ev, now, slot, n=need, exclude=exclude, feedback=feedback)
        calls += 1
        text = call_model(prompt, MAX_TOKENS)
        raw = parse_response(text)
        tur = {"cagri": calls, "istem_karakter": len(prompt), "yanit": text, "maddeler": []}
        audit["turlar"].append(tur)
        if raw is None:
            if text is None and calls >= 2:
                break   # iki kez yanıt yok: Gemini kapalı/zaman aşımı — tavanı boşa harcama
            continue
        rejected = []
        for r in raw:
            it, rep = validate_item(r, ctx)
            tur["maddeler"].append(rep)
            if it:
                accepted.append(it)
                exclude |= set(it["_h"])
            else:
                rejected.append("\"%s\" (%s)" % (_clip(rep.get("baslik") or "", 60), _why(rep)))
        if len(raw) == 0:
            break
        feedback = ("Önceki taslakta şu maddeler kurallara uymadığı için yayımlanmadı: %s. "
                    "Yayımlanan maddelerin kanıtlarını (%s) tekrar kullanma; kurallara harfiyen uyan yeni "
                    "maddeler yaz. Sayıları kaynaktaki gibi aynen yaz, her cümleye kanıt kimliği ekle."
                    % ("; ".join(rejected[:6]) or "yok", ", ".join(sorted(exclude)) or "yok"))
    doc = assemble(accepted, now, slot) if len(accepted) >= MIN_PUBLISH else None
    u1 = usage_fn() if usage_fn else (0, 0.0)
    audit["cagri"] = calls
    audit["gemini_cagri_sayaci"] = max(0, (u1[0] or 0) - (u0[0] or 0))
    audit["maliyet_usd"] = round(max(0.0, (u1[1] or 0.0) - (u0[1] or 0.0)), 6)
    audit["durum"] = "basildi" if doc else "yetersiz"
    audit["madde"] = len(doc["maddeler"]) if doc else 0
    audit["atilan_cumle"] = sum(1 for t in audit["turlar"] for m in t["maddeler"]
                                for s in m.get("cumleler") or [] if s.get("ret"))
    audit["used_ids"] = sorted(set(i for it in accepted for h in it["_h"] for i in ev[h]["ids"] if i))
    if doc:
        audit["yayin"] = doc
    _finish(audit, doc, base, now, log)
    return _summary(audit)


_WHY = (("baslik_kopya", "başlık kaynak başlığa çok benziyor"), ("kopya", "cümle kaynaktan aynen alınmış"),
        ("sayi", "kaynakta olmayan sayı"), ("tarih", "kaynakta olmayan tarih"), ("ad", "kaynakta olmayan ad"),
        ("yasak_dil", "yasak sözcük"), ("kanit_yok", "kanıt kimliği yok ya da yalnız K"),
        ("dayanak", "kaynakta dayanağı yok"), ("neden_bag", "kaynakta olmayan neden-sonuç"),
        ("yon", "yön kaynakla çelişiyor"), ("uzun_baslik", "başlık 70 karakteri aşıyor"),
        ("tek_dayanak", "tek kaynak"), ("basin_kaniti_yok", "H kanıtı yok"), ("kaynakta_yok", "kaynakta yok"),
        ("cumle_kalmadi", "geçerli cümle kalmadı"), ("kaynak_eslesmedi", "kaynak başlıkla eşleşmedi"))


def _why(rep):
    codes = list(rep.get("baslik_ret") or []) + [r for c in rep.get("cumleler") or [] for r in (c.get("ret") or [])]
    codes.append(rep.get("karar") or "")
    out = []
    for c in codes:
        head = c.split(":")[0]
        for k, txt in _WHY:
            if head == k and txt not in out:
                out.append(txt)
    return ", ".join(out[:3]) or (rep.get("karar") or "")


def _summary(a):
    return {k: a.get(k) for k in ("key", "durum", "sebep", "madde", "cagri", "gemini_cagri_sayaci", "maliyet_usd",
                                  "atilan_cumle", "aday", "girdi")}


def _finish(audit, doc, base, now, log):
    """İz her zaman (baskı 'yapıldı' sayılır); belge yalnız yeterli maddeyle. Gemini'ye hiç çağrı
    gitmediyse (sigorta/tavan anlık) iz yazılmaz → sonraki turda yeniden denenir."""
    if audit.get("durum") != "aday_yetersiz" and not audit.get("gemini_cagri_sayaci") and \
            all(t.get("yanit") is None for t in audit.get("turlar") or []):
        audit["durum"] = "cagri_yapilamadi"
        if log:
            log("gündem-haber %s: Gemini yanıtı yok (çağrı sayacı artmadı) — sonraki turda yeniden" % audit["key"])
        return
    _atomic_write(os.path.join(base, "%s.audit.json" % audit["key"]), audit)
    if doc:
        _atomic_write(os.path.join(base, "%s.json" % audit["key"]), doc)
        _atomic_write(os.path.join(base, "latest.json"), doc)
    cutoff = (now.date() - timedelta(days=AUDIT_KEEP_DAYS)).isoformat()
    try:
        for n in os.listdir(base):
            if n.endswith(".audit.json") and n[:10] < cutoff:
                os.remove(os.path.join(base, n))
    except OSError:
        pass
    if log:
        log("gündem-haber %s: %s, %s madde, %s çağrı, $%.4f, %s cümle atıldı" % (
            audit["key"], audit.get("durum"), audit.get("madde", 0), audit.get("cagri", 0),
            audit.get("maliyet_usd") or 0.0, audit.get("atilan_cumle", 0)))


_CACHE = {}


def _public_ok(doc):
    return (isinstance(doc, dict) and isinstance(doc.get("maddeler"), list) and doc.get("baski")
            and doc.get("baski_label"))


def load_latest(base_dir=None):
    """Son baskı (sözleşme belgesi) | None. mtime önbellekli; dosya silinirse anında None."""
    path = os.path.join(base_dir or OUT_DIR, "latest.json")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        _CACHE.pop(path, None)
        return None
    hit = _CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    doc = _read_json(path)
    doc = doc if _public_ok(doc) and doc["maddeler"] else None
    _CACHE[path] = (mtime, doc)
    return doc


def empty_doc():
    return {"baski": None, "baski_label": None, "maddeler": []}


# ----------------------------------------------------------------------------- komut satırı (salt-okur)

def _cli(argv):
    """python3 gundem_haber.py --kuru [--tarih 2026-10-01T19:30] [--yanit model.json]
    Gemini ÇAĞIRMAZ: adayları ve istemi kurar; --yanit verilirse kayıtlı model yanıtını doğrular."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--tarih")
    ap.add_argument("--girdi-dizin")
    ap.add_argument("--v1")
    ap.add_argument("--yanit")
    ap.add_argument("--istem", action="store_true")
    ap.add_argument("--ozet", action="store_true", help="baskı izlerinin özeti (kabul ölçümü)")
    ap.add_argument("--dizin", help="çıktı dizini (varsayılan data/gundem_haber)")
    ap.add_argument("--gun", type=int, default=7)
    a = ap.parse_args(argv)
    if a.ozet:
        return _ozet(a.dizin or OUT_DIR, a.gun)
    now = datetime.strptime(a.tarih, "%Y-%m-%dT%H:%M") if a.tarih else datetime.utcnow() + timedelta(hours=3)
    slot = "sabah" if now.hour < 12 else "aksam"
    start = window_start(now, slot)
    items = load_inputs(now, start, a.girdi_dizin)
    names = {}
    aliases = company_aliases(names, ())
    cands = select_candidates(items, aliases)
    v1 = _read_json(a.v1) if a.v1 else None
    ev = build_evidence(cands, own_facts(v1), [])
    prompt = build_prompt(cands, ev, now, slot)
    multi = sum(1 for c in cands if len(c["pubs"]) >= 2)
    print("pencere %s → %s · girdi %d · aday %d (çok yayıncılı %d) · istem %d karakter (~%d token)" % (
        start, now, len(items), len(cands), multi, len(prompt), len(prompt) // 3))
    if a.istem:
        print(prompt)
    if a.yanit:
        with open(a.yanit, encoding="utf-8") as f:
            raw = parse_response(f.read())
        ctx = Ctx(ev, allowed_dates_for(now), aliases, (), year=now.year)
        acc = []
        for r in raw or []:
            it, rep = validate_item(r, ctx)
            print(json.dumps(rep, ensure_ascii=False))
            if it:
                acc.append(it)
        print(json.dumps(assemble(acc, now, slot), ensure_ascii=False, indent=1))
    return 0


def acceptance(base_dir=None, days=7, today=None):
    """Kabul ölçümü (salt-okur): son N günün baskıları -> satırlar + toplamlar.
    Yayımlanan her madde metni yasak dil süzgecinden yeniden geçirilir."""
    base = base_dir or OUT_DIR
    today = today or (datetime.utcnow() + timedelta(hours=3)).date()
    cutoff = (today - timedelta(days=days)).isoformat()
    rows, banned = [], []
    for k in sorted(done_keys(base)):
        if k[:10] < cutoff:
            continue
        a = _read_json(os.path.join(base, "%s.audit.json" % k)) or {}
        doc = _read_json(os.path.join(base, "%s.json" % k))
        for m in (doc or {}).get("maddeler") or []:
            for h in banned_hits(m.get("baslik", "") + " " + m.get("ozet", "")):
                banned.append("%s %s %s" % (k, m.get("id"), h))
        rows.append({"key": k, "durum": a.get("durum"), "madde": len((doc or {}).get("maddeler") or []),
                     "atilan_cumle": a.get("atilan_cumle", 0), "cagri": a.get("cagri", 0),
                     "maliyet_usd": a.get("maliyet_usd") or 0.0})
    return {"satirlar": rows, "baski": len(rows), "bes_ve_ustu": sum(1 for r in rows if r["madde"] >= MIN_ITEMS),
            "toplam_usd": round(sum(r["maliyet_usd"] for r in rows), 6), "yasak_dil": banned}


def _ozet(base, days):
    r = acceptance(base, days)
    for x in r["satirlar"]:
        print("%(key)s  %(durum)-10s madde %(madde)d  atılan cümle %(atilan_cumle)d  çağrı %(cagri)d  $%(maliyet_usd).4f" % x)
    print("son %d gün: %d baskı, %d baskıda ≥%d madde, toplam $%.4f, yayında yasak dil %d" % (
        days, r["baski"], r["bes_ve_ustu"], MIN_ITEMS, r["toplam_usd"], len(r["yasak_dil"])))
    for b in r["yasak_dil"]:
        print("  YASAK: " + b)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv[1:]))
