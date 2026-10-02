"""D-23: sektör taksonomisi — KAP resmi alt sektörü → BIST sektör endeksine hizalı okunur kova.
D-23b: KAP'ın yatırımcıya yanlış görünen sınıflarına açık, gerekçeli düzeltme tablosu (OVERRIDES).

Sitenin TEK sektör kaynağı: /hisse sektör etiketi, JSON-LD "category", ilgili hisseler ve
Karşılaştır akranları, /tarama sektör filtresi, /sektor-harita, /hisseler, ana sayfa en güçlü
sektör, EOD temel skor sektör havuzu (sector_stats) ve ısı haritası grupları (heatmap.py `g`).

Kova sırası (ticker → kova):
  1. OVERRIDES: KAP sınıfı sıradan yatırımcının "bu şirketin sektörü" diyeceğinden farklıysa
     (FROTO "Metal Eşya", SISE "Holding" gibi) elle, tek satır gerekçeyle. Liste kısa tutulur.
  2. KAP alt sektörü → BUCKETS. KAP alt sektörünün kaynağı: evren dosyası `companies[t].sector`
     (haftalık KAP Sektörler sayfası, D-46) → EXPLICIT (KAP sektör sayfasında sektörsüz gelen 22 kod)
     → kap_sirket_bilgileri.json `kap_alt_sektor` (D-46b).
Yeni hisse kovasını KAP sektöründen kendisi alır; tanınmayan/boş sektör "Diğer"e düşer ve
çağırana bildirilir (uyarı), asla hata fırlatmaz.

Saf modül (py3.9, app.py'ye bağımlı değil); yan etkisi yok.
"""

OTHER = "Diğer"

# (kova, BIST sektör endeksi, KAP alt sektörleri). Sıra = liste/harita varsayılan sırası.
# Kova adı sitede görünen addır: Borsa İstanbul / KAP adı, okunur, kısaltmasız.
# KAP alt sektörü boş olan kovalar (Otomotiv, Dayanıklı Tüketim) yalnız OVERRIDES'tan dolar;
# BIST'te ayrı endeksleri yok, endeks sütunu üyelerinin KAP'taki endeksidir (XMESY).
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
    ("Otomotiv", "XMESY", ()),                   # D-23b: araç üreticileri + yan sanayi + DOAS
    ("Dayanıklı Tüketim", "XMESY", ()),          # D-23b: beyaz eşya, elektronik, mobilya
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
    # D-23b: "Sağlık" → "İlaç ve Sağlık" (hastaneler + OVERRIDES'taki ilaç ve tıbbi cihaz şirketleri)
    ("İlaç ve Sağlık", "XUHIZ", ("İNSAN SAĞLIĞI VE SOSYAL HİZMETLER",)),   # BIST Hizmetler üst endeksi
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

# D-23b (Ozan 02.10: "FROTO, TOASO metal eşya ve makine sektöründe, bu doğru mu?"): KAP sınıfı
# yerine kova. Ölçüt: sıradan yatırımcı bu şirketin sektörüne ne der; dayanak KAP faaliyet konusu
# ve gelir kaynağı. Yalnız gerçek çok iş kollu holdingler Holding'de kalır. Her satır:
# ticker: (kova, tek satır gerekçe). Gerekçe Türkçe, sitede görünmez; değişiklik tablosu buradan.
OVERRIDES = {
    # ── Otomotiv: araç üreticileri (KAP: Metal Eşya Makine ... Ulaşım Araçları) ──
    "FROTO": ("Otomotiv", "Ford Otosan: ticari araç ve otomobil üreticisi"),
    "TOASO": ("Otomotiv", "Tofaş: otomobil ve hafif ticari araç üreticisi"),
    "OTKAR": ("Otomotiv", "Otokar: otobüs, kamyon ve askeri kara aracı üreticisi; satışın çoğu ticari araç"),
    "ASUZU": ("Otomotiv", "Anadolu Isuzu: kamyon, otobüs ve hafif ticari araç üreticisi"),
    "KARSN": ("Otomotiv", "Karsan: otobüs ve hafif ticari araç üreticisi"),
    "TTRAK": ("Otomotiv", "Türk Traktör: traktör üreticisi; yatırımcı dilinde otomotiv grubunda"),
    "TMSN": ("Otomotiv", "Tümosan: traktör ve dizel motor üreticisi; Türk Traktör ile aynı grup"),
    # ── Otomotiv: yan sanayi ve lastik (aynı otomobil üretim döngüsü; ayrı 4-5 hisselik grup
    #    sektör kıyası için çok küçük kalırdı) ──
    "EGEEN": ("Otomotiv", "Ege Endüstri: kamyon aksı üreten otomotiv yan sanayi"),
    "FMIZP": ("Otomotiv", "Federal-Mogul İzmit: motor pistonu üreten otomotiv yan sanayi"),
    "JANTS": ("Otomotiv", "Jantsa: taşıt jantı üreten otomotiv yan sanayi"),
    "PARSN": ("Otomotiv", "Parsan: taşıt şanzıman ve aktarma parçası üreten otomotiv yan sanayi"),
    "BRISA": ("Otomotiv", "Brisa: taşıt lastiği üreticisi (KAP: Kimya, Lastik); 233 hisselik kapsamda değil"),
    # ── Otomotiv: dağıtıcı (KAP: Toptan Ticaret) ──
    "DOAS": ("Otomotiv", "Doğuş Otomotiv: Volkswagen grubu markalarının ithalatçısı ve satıcısı"),
    # ── Dayanıklı Tüketim (TÜİK tanımı: beyaz eşya, tüketici elektroniği, mobilya) ──
    "ARCLK": ("Dayanıklı Tüketim", "Arçelik: beyaz eşya ve tüketici elektroniği (KAP: Metal Eşya)"),
    "VESTL": ("Dayanıklı Tüketim", "Vestel: televizyon ve beyaz eşya (KAP: Metal Eşya)"),
    "VESBE": ("Dayanıklı Tüketim", "Vestel Beyaz Eşya: buzdolabı, çamaşır makinesi, klima (KAP: Metal Eşya)"),
    "ARZUM": ("Dayanıklı Tüketim", "Arzum: küçük ev aletleri markası (KAP: Toptan Ticaret)"),
    "YATAS": ("Dayanıklı Tüketim", "Yataş: yatak ve mobilya (KAP: Tekstil)"),
    # ── Holding sayılan tek işli şirketler (KAP: Holdingler ve Yatırım Şirketleri) ──
    "SISE": ("Taş ve Toprak", "Şişecam: cam üreticisi (cam Borsa İstanbul'da taş ve toprak sektörü)"),
    "TAVHL": ("Ulaştırma", "TAV: havalimanı işletmecisi; tek ana iş havacılık hizmeti"),
    # ── Restoran zinciri (KAP: Yiyecek ve İçecek Hizmetleri → Turizm) ──
    "TABGD": ("Gıda ve İçecek", "TAB Gıda: hızlı servis restoran zinciri (Burger King, Popeyes); turizm değil"),
    # ── İlaç ve tıbbi ürün (KAP: Toptan Ticaret / Kimya) ──
    "GENIL": ("İlaç ve Sağlık", "Gen İlaç: ilaç üreticisi ve ithalatçısı (KAP: Toptan Ticaret)"),
    "SELEC": ("İlaç ve Sağlık", "Selçuk Ecza Deposu: ilaç dağıtıcısı (KAP: Toptan Ticaret)"),
    "MEDTR": ("İlaç ve Sağlık", "Meditera: tıbbi cihaz ve sarf malzemesi üreticisi (KAP: Kimya)"),
}

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
OVERRIDE_BUCKET = {t: label for t, (label, _) in OVERRIDES.items()}


def is_known(kap_sub):
    return norm(kap_sub) in _BY_KAP


def bucket(kap_sub):
    """KAP alt sektörü → kova adı; boş ya da tanınmayan → 'Diğer'. (Düzeltme tablosuna bakmaz:
    ticker biliniyorsa bucket_of_ticker kullanılır.)"""
    return _BY_KAP.get(norm(kap_sub), OTHER)


def bucket_of_ticker(ticker, kap_sub):
    """Ticker + KAP alt sektörü → kova: önce OVERRIDES, sonra KAP alt sektörü."""
    return OVERRIDE_BUCKET.get(ticker) or bucket(kap_sub)


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
    """Ticker → kova (OVERRIDES önce). KAP sektörü hiçbir kaynakta yoksa ve düzeltme yoksa
    `default` (ısı haritası yeniden gruplamasında None: donmuş grup korunur)."""
    if ticker in OVERRIDE_BUCKET:
        return OVERRIDE_BUCKET[ticker]
    return kap_bucket_for(ticker, companies, kap_info, default)


def kap_bucket_for(ticker, companies=None, kap_info=None, default=OTHER):
    """Ticker → yalnız KAP alt sektöründen kova (OVERRIDES'a bakmaz; BIST sektör endeksi). Görünen
    ad değil: sektör ortancası yedeği için (kovada geçerli akran < 5 ise ortanca KAP sektöründen,
    D-23 öncesi davranış; D-23b hiçbir hissenin ortancasını kaldırmasın)."""
    sub = kap_sector(ticker, companies, kap_info)
    return bucket(sub) if sub else default


def build(tickers, companies=None, kap_info=None):
    """(ticker→kova, kova→[ticker] (BUCKETS sırası, yalnız dolu kovalar, 'Diğer' sonda),
    sorunlar [(ticker, KAP alt sektörü ya da None)]). Sorun = düzeltme yok ve KAP sektörü yok ya
    da tanınmıyor; ikisi de 'Diğer'e düşer. Aynı ticker iki kez gelirse ilk sıra korunur."""
    t2b, problems = {}, []
    for t in tickers:
        if t in t2b:
            continue
        if t in OVERRIDE_BUCKET:
            t2b[t] = OVERRIDE_BUCKET[t]
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


# Eski sektör adı → güncel kova. Yalnız birebir karşılığı olanlar: D-23 öncesi "Sanayi" birçok
# kovaya bölündü, tek karşılığı yok (eski bağlantı boş liste verir). D-23b: "Sağlık" → "İlaç ve Sağlık".
LEGACY_ALIASES = {
    "Holding": "Holding ve Yatırım", "Enerji": "Elektrik", "Perakende": "Ticaret",
    "Teknoloji": "Bilişim", "Telekom": "İletişim", "Ulaşım": "Ulaştırma",
    "GYO": "Gayrimenkul", "Kimya/Malzeme": "Kimya, Petrol ve Plastik",
    "İlaç/Sağlık": "İlaç ve Sağlık", "Sağlık": "İlaç ve Sağlık",
}


def canonical_label(name):
    """?sector= değerini güncel kova adına çevirir (bilinmeyen değer aynen döner)."""
    return LEGACY_ALIASES.get(name, name)
