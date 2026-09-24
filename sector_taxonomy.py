"""D-23: sektör taksonomisi — KAP resmi alt sektörü → BIST sektör endeksine hizalı okunur kova.

Sitenin TEK sektör kaynağı: /hisse sektör etiketi, JSON-LD "category", ilgili hisseler ve
Karşılaştır akranları, /tarama sektör filtresi, /sektor-harita, /hisseler, ana sayfa en güçlü
sektör, EOD temel skor sektör havuzu (sector_stats) ve ısı haritası grupları (heatmap.py `g`).

Kaynak sırası (ticker → KAP alt sektörü): evren dosyası `companies[t].sector` (haftalık KAP
Sektörler sayfası, D-46) → EXPLICIT (KAP sektör sayfasında sektörsüz gelen 22 kod) →
kap_sirket_bilgileri.json `kap_alt_sektor` (D-46b). Yeni hisse kovasını KAP sektöründen kendisi
alır; tanınmayan/boş sektör "Diğer"e düşer ve çağırana bildirilir (uyarı), asla hata fırlatmaz.

Saf modül (py3.9, app.py'ye bağımlı değil); yan etkisi yok.
"""

OTHER = "Diğer"

# (kova, BIST sektör endeksi, KAP alt sektörleri). Sıra = liste/harita varsayılan sırası.
# Kova adı sitede görünen addır: Borsa İstanbul / KAP adı, okunur, kısaltmasız.
BUCKETS = (
    ("Bankacılık", "XBANK", ("BANKALAR",)),
    ("Finansal Hizmetler", "XAKUR + XFINK", (
        "ARACI KURUMLAR",
        "FİNANSAL KİRALAMA VE FAKTORİNG ŞİRKETLERİ",
        "FİNANSMAN ŞİRKETLERİ",
        "VARLIK YÖNETİM ŞİRKETLERİ",
    )),
    ("Sigorta", "XSGRT", ("SİGORTA ŞİRKETLERİ",)),
    ("Holding ve Yatırım", "XHOLD", (
        "HOLDİNGLER VE YATIRIM ŞİRKETLERİ",
        "GİRİŞİM SERMAYESİ YATIRIM ORTAKLIKLARI",
    )),
    ("Gayrimenkul", "XGMYO", (
        "GAYRİMENKUL YATIRIM ORTAKLIKLARI",
        "GAYRİMENKUL FAALİYETLERİ",
    )),
    ("İnşaat", "XINSA", (
        "İNŞAAT VE BAYINDIRLIK İŞLERİ",
        "MİMARLIK VE MÜHENDİSLİK FAALİYETLERİ; TEKNİK MUAYENE VE ANALİZ",
    )),
    ("Elektrik", "XELKT", ("ELEKTRİK GAZ VE BUHAR",)),
    ("Gıda ve İçecek", "XGIDA", ("GIDA, İÇECEK VE TÜTÜN",)),
    ("Kimya, Petrol ve Plastik", "XKMYA", ("KİMYA İLAÇ PETROL LASTİK VE PLASTİK ÜRÜNLER",)),
    ("Ana Metal Sanayi", "XMANA", ("ANA METAL SANAYİ",)),
    ("Metal Eşya ve Makine", "XMESY", ("METAL EŞYA MAKİNE ELEKTRİKLİ CİHAZLAR VE ULAŞIM ARAÇLARI",)),
    ("Taş ve Toprak", "XTAST", ("TAŞ VE TOPRAĞA DAYALI",)),
    ("Madencilik", "XMADN", (
        "METAL CEVHERİ MADENCİLİĞİ",
        "KÖMÜR VE LİNYİT MADENCİLİĞİ",
        "HAM PETROL VE DOĞAL GAZ ÇIKARTILMASI",
        "DİĞER MADENCİLİK VE TAŞ OCAKÇILIĞI",
    )),
    ("Tekstil ve Deri", "XTEKS", ("TEKSTİL, GİYİM EŞYASI VE DERİ",)),
    ("Orman, Kağıt ve Basım", "XKAGT", (
        "KAĞIT VE KAĞIT ÜRÜNLERİ BASIM",
        "ORMAN ÜRÜNLERİ VE MOBİLYA",
    )),
    ("Ticaret", "XTCRT", ("PERAKENDE TİCARET", "TOPTAN TİCARET")),
    ("Ulaştırma", "XULAS", ("ULAŞTIRMA VE DEPOLAMA", "KİRALAMA VE LEASING FAALİYETLERİ")),
    ("Turizm", "XTRZM", (
        "KONAKLAMA",
        "YİYECEK VE İÇECEK HİZMETLERİ",
        "SEYAHAT ACENTESİ, TUR OPERATÖRÜ VE DİĞER REZERVASYON HİZMETLERİ İLE İLGİLİ FAALİYETLER",
    )),
    ("Bilişim", "XBLSM", ("BİLİŞİM",)),
    ("Savunma", "XUTEK", ("SAVUNMA",)),          # BIST Teknoloji üst endeksi (Bilişim + Savunma)
    ("İletişim", "XILTM", ("TELEKOMÜNİKASYON", "YAYIMCILIK", "BİLGİ HİZMET FAALİYETLERİ")),
    ("Spor", "XSPOR", (
        "SPOR FAALİYETLERİ EĞLENCE VE OYUN FAALİYETLERİ",
        "SPOR EĞLENCE BOŞ ZAMANLARI DEĞERLENDİRME HİZMETLERİ",
    )),
    ("Sağlık", "XUHIZ", ("İNSAN SAĞLIĞI VE SOSYAL HİZMETLER",)),   # BIST Hizmetler üst endeksi
    # Bilinen ama BIST sektör endeksi olmayan KAP alt sektörleri: bilerek "Diğer" (uyarı yok).
    (OTHER, "", (
        "DİĞER İMALAT SANAYİİ",
        "TARIM VE HAYVANCILIK AVCILIK VE İLGİLİ HİZMET FAALİYETLERİ",
        "BALIKÇILIK VE SU ÜRÜNLERİ",
        "HUKUK VE MUHASEBE FAALİYETLERİ",
        "REKLAMCILIK VE PAZAR ARAŞTIRMASI",
        "BÜRO YÖNETİMİ, BÜRO DESTEĞİ VE DİĞER ŞİRKET DESTEK FAALİYETLERİ",
    )),
)

# KAP "Sektörler" sayfasında sektörsüz gelen 22 kod (evren dosyası sector=None, 24.09): bankalar,
# aracı kurumlar ve Kardemir'in A/B/D payları. Değer = KAP alt sektörü (şirketin KAP sayfasındaki).
EXPLICIT = {
    "ALBRK": "BANKALAR", "GARAN": "BANKALAR", "HALKB": "BANKALAR", "ICBCT": "BANKALAR",
    "ISATR": "BANKALAR", "ISBTR": "BANKALAR", "ISCTR": "BANKALAR", "SKBNK": "BANKALAR",
    "TSKB": "BANKALAR", "VAKBN": "BANKALAR", "YKBNK": "BANKALAR",
    "A1CAP": "ARACI KURUMLAR", "GLBMD": "ARACI KURUMLAR", "INFO": "ARACI KURUMLAR",
    "ISMEN": "ARACI KURUMLAR", "OSMEN": "ARACI KURUMLAR", "OYYAT": "ARACI KURUMLAR",
    "SKYMD": "ARACI KURUMLAR", "TERA": "ARACI KURUMLAR",
    "KRDMA": "ANA METAL SANAYİ", "KRDMB": "ANA METAL SANAYİ", "KRDMD": "ANA METAL SANAYİ",
}

_TR_UPPER = str.maketrans({"i": "İ", "ı": "I"})


def norm(s):
    """KAP adı karşılaştırma anahtarı: Türkçe büyük harf, tek boşluk ('Gıda,  içecek' → 'GIDA, İÇECEK')."""
    if not isinstance(s, str):
        return ""
    return " ".join(s.translate(_TR_UPPER).upper().split())


_BY_KAP = {norm(k): label for label, _, kaps in BUCKETS for k in kaps}
LABELS = tuple(label for label, _, _ in BUCKETS)
INDEX_OF = {label: idx for label, idx, _ in BUCKETS}


def is_known(kap_sub):
    return norm(kap_sub) in _BY_KAP


def bucket(kap_sub):
    """KAP alt sektörü → kova adı; boş ya da tanınmayan → 'Diğer'."""
    return _BY_KAP.get(norm(kap_sub), OTHER)


def kap_sector(ticker, companies=None, kap_info=None):
    """Ticker'ın KAP alt sektörü (evren dosyası → EXPLICIT → kap_sirket_bilgileri) ya da None."""
    c = (companies or {}).get(ticker)
    if isinstance(c, dict) and isinstance(c.get("sector"), str) and c["sector"].strip():
        return c["sector"]
    if ticker in EXPLICIT:
        return EXPLICIT[ticker]
    k = (kap_info or {}).get(ticker)
    if isinstance(k, dict) and isinstance(k.get("kap_alt_sektor"), str) and k["kap_alt_sektor"].strip():
        return k["kap_alt_sektor"]
    return None


def bucket_for(ticker, companies=None, kap_info=None, default=OTHER):
    """Ticker → kova. KAP sektörü hiçbir kaynakta yoksa `default` (ısı haritası yeniden
    gruplamasında None: donmuş grup korunur)."""
    sub = kap_sector(ticker, companies, kap_info)
    return bucket(sub) if sub else default


def build(tickers, companies=None, kap_info=None):
    """(ticker→kova, kova→[ticker] (BUCKETS sırası, yalnız dolu kovalar, 'Diğer' sonda),
    sorunlar [(ticker, KAP alt sektörü ya da None)]). Sorun = KAP sektörü yok ya da tanınmıyor;
    ikisi de 'Diğer'e düşer. Aynı ticker iki kez gelirse ilk sıra korunur."""
    t2b, problems = {}, []
    for t in tickers:
        if t in t2b:
            continue
        sub = kap_sector(t, companies, kap_info)
        if not is_known(sub):
            problems.append((t, sub))
        t2b[t] = bucket(sub)
    by_bucket = {label: [] for label in LABELS}
    for t, b in t2b.items():
        by_bucket[b].append(t)
    ordered = {label: by_bucket[label] for label in LABELS if label != OTHER and by_bucket[label]}
    if by_bucket[OTHER]:
        ordered[OTHER] = by_bucket[OTHER]
    return t2b, ordered, problems


# Türkçe alfabe sıralaması (locale'siz; 'İnşaat' Z'den sonra değil H-J arasında).
_TR_ORDER = {ch: i for i, ch in enumerate("aAbBcCçÇdDeEfFgGğĞhHıIiİjJkKlLmMnNoOöÖpPrRsSşŞtTuUüÜvVyYzZ")}


def tr_key(name):
    return [_TR_ORDER.get(ch, 1000 + ord(ch)) for ch in (name or "")]


def sort_labels(labels):
    """Kova adları Türkçe alfabetik, 'Diğer' en sonda (/tarama filtresi, /hisseler)."""
    return sorted(labels, key=lambda s: (s == OTHER, tr_key(s)))
