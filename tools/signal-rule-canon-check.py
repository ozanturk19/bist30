#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-DK (22.09.2026) — SINYAL URETIM KURALI HER KANALDA TAM MI ANLATILIYOR?

Urunun cekirdek kurali kodda tek satir (app.py `_bar_signal_fast`):

    bs  = int(sti ==  1) + int(ai >= 25 and dip > dim) + int(ei12 > ei99)
    brs = int(sti == -1) + int(ai >= 25 and dim > dip) + int(ei12 < ei99)

Yani DORT kosul var: Supertrend yonu · ADX >= 25 · DI yonu (DI+ vs DI-) ·
EMA12/EMA99 hizalamasi. `dip > dim` ADX esiginin YANINDA duruyor, ayri ve
zorunlu bir kosul.

CANLI OLCUM 22.09 (/api/data): 4/4 AL hissesinde DI+ > DI-, 87 SAT
hissesinin 86'sinda DI- > DI+ (kalan 1'i panelde tam sayiya yuvarlanmis).
Kosul gercekten sinyali belirliyor.

KURAL BES KANALDA ANLATILIYORDU, DI KOSULUNU YALNIZ BIRI ICERIYORDU:

  * /metodoloji  — DOGRU (4 kosul, AL ve SAT icin ayri ayri)
  * /hakkinda    — formul kutusu 3 kosul; DI satiri YOKTU
  * /hisse       — AL/SAT kriter checklist'i 3 madde + "3/3 kriter uyumlu",
                   SSR Teknik Ozet ve sayfa alti metodoloji kutusu da 3
  * blog         — "uclu filtre sistemi ... Ucu ayni anda" (SSS),
                   "uclu kritere dayanir"; USTELIK ayni yazidaki AL listesi
                   4 madde sayarken paragrafi "su uc kriter" diyordu
  * /tarama meta — kisa tanitim, kural beyani degil (tetiklemez)

Kullanici sonucu: "ST LONG + ADX 26 + EMA12 > EMA99" saglanan bir hissede
AL bekleyip BEKLE goren biri, /metodoloji disinda HICBIR yerde sebebini
bulamiyordu. 4. kez olculen sinif: ayni is icin iki kanon (K-hub ortak mercek).

OLCUT (taban SIFIR):

  R1  KURAL BEYANI TAM — bir metin blogu Supertrend + ADX esigi + EMA12
      ucunu BIRLIKTE iceriyorsa o blok sinyal uretim kuralini anlatiyor
      demektir; DI'yi de ANMALIDIR. Blok = gercek yayim birimi (</p>,
      </ul>, </div>, <br><br>, Jinja dal siniri, bos satir) ile ayrilir --
      +-N satirlik komsuluk DEGIL (139/140. ders: komsuluk kapsam degildir).
  R2  SAYIM BEYANI DOGRU — ayni blokta "3 kriter" / "uc kriter" / "uclu
      kriter" / "uclu filtre" / "3/3 kriter" / "Ucu ayni anda" gibi sinyal
      kuralina ait bir SAYIM varsa FAIL: kosul sayisi 4'tur. (Gosterge
      sayisi 3'tur -- "3 teknik gosterge" ifadesi serbesttir, kapi
      "gosterge"/"indikator" gecen sayimi saymaz.)

Yayimlanmayan metin soyulur (77/102. ders): HTML yorumlari, Jinja {# #},
Python satir yorumlari ve modul/fonksiyon docstring'leri. blog_content.py'de
metin bir DEGER (dict/list icinde) oldugu icin TARANIR -- yayimlanir.

Kullanim:
  python3 tools/signal-rule-canon-check.py              # calisan agac
  python3 tools/signal-rule-canon-check.py --ref SHA    # o commit'in agaci
  python3 tools/signal-rule-canon-check.py --self-test  # sahte-poz/negatif
"""
import io
import os
import re
import sys
import ast
import tarfile
import tempfile
import subprocess

SCAN_DIRS = ['templates', 'static']
SCAN_FILES = ['blog_content.py', 'app.py']
SCAN_EXT = ('.html', '.js', '.py')

# --- C-60 (24.09): kalici dil kurallari (Ozan 23.09, kanon §2) -------------
# "Ucretsiz" yazilmaz, veri kaynagi adi yazilmaz, LONG/SHORT yok, islem
# yonetimi dili yok (Stop Loss, ideal giris, giris fiyati). Yalniz
# yayimlanan HTML/JS metni (yorumlar soyulmus); .py kod dizeleri kapsam
# disi (LONG/SHORT mantik degeri). Hukuki metin istisnasi: yasal, gizlilik.
RE_BANNED = re.compile(
    r'[Üü]cretsiz|ÜCRETSİZ|Yahoo|yfinance|\bLONG\b|\bSHORT\b|Stop Loss|'
    r'[İi]deal Giriş(?! Penceresi)|Giriş fiyatı|'
    # C-52 (24.09): teknik hedef + islem yonetimi dili (kanon §2.2). Analist
    # hedef fiyati KALIR -- "Hedef" tek basina taranmaz, yalniz satir etiketi.
    r'\bTP[12]\b|\bR/R\b|[Rr]isk ?/ ?[Öö]dül|[Ss]top (?:bölgesi|seviyesi)|'
    r'[İi]deal giriş|[Gg]iriş bölgesi|[Pp]rim potansiyel|hedefe ulaştı|'
    r'>\s*Hedef\s*(?:\d\s*)?:|Hedef:</')
# C-61 (24.09): C-60 tam yazim aradigi icin "Giriş Fiyatı", "stop-loss",
# "Kovalama", "Kazanma Oranı" kaldi. Buyuk/kucuk harf + tire/bosluk duyarsiz
# (Python re.I Turkce İ/ı'yi katlamaz -> sinif ile). "Penceresi" C-60 kalan
# (RSI bolge adi gecis eslemesi) silinince eklenir.
RE_BANNED_CI = re.compile(
    r'g[iİI]r[iİI][şŞ][ \-](?:f[iİI]yat[ıI]|kal[iİI]tes[iİI]|b[öÖ]lges[iİI]|anal[iİI]z[iİI])|'
    r'stop[ \-]?loss|kovalama|kazanma oran[ıI]', re.I)
# GECICI: RSI bolge adi "İdeal Giriş Penceresi" business_rules.derive_rsi_zone'dan
# gelir ve kapi 16/47 onu /metodoloji'de arar -- backend adi degisince (D) kalkar.
BANNED_EXEMPT = ('templates/yasal.html', 'templates/gizlilik.html')
# JS mantik karsilastirmasi (ornek: z.indexOf('İdeal Giriş') -- kaynak
# dizesini ESLER, yayimlamaz) muaf.
RE_BANNED_LOGIC = re.compile(r"indexOf\('[^']*'\)")

# --- kural beyani imzasi -----------------------------------------------------
RE_ST = re.compile(r'Supertrend|\bST\s*(?:=\s*)?(?:LONG|SHORT|yukarı|aşağı)', re.I)
RE_ADX_THR = re.compile(r'ADX\s*(?:\(14\))?\s*(?:&[lg]?t;|[>≥<])?\s*[≥>]=?\s*25'
                        r'|ADX\s*(?:\(14\))?\s*&gt;=?\s*25'
                        r'|ADX\s*(?:\(14\))?\s*≥\s*25', re.I)
# C-02: R1 esiksiz ADX animinda da tetiklenir -- "Supertrend, ADX ve EMA12/99:
# sinyal bu 3 testin oybirligiyle dogar" esik yazmadan kural beyan ediyordu.
RE_ADX_ANY = re.compile(r'\bADX\b')
# Esiksiz yolda " + " ve ok gosterge LISTESI de olabilir ("Supertrend + ADX +
# EMA12/99 teknik analiz") -- yalniz gercek birlestirme sozcukleri sayilir.
# AND buyuk harfle (kural notasyonu): .py kodundaki kucuk 'and' sayilmaz.
RE_CONJ_STRONG = re.compile(
    r'ayn\u0131\s+anda|(?-i:\bAND\b)|tamam\u0131|sa\u011fland\u0131\u011f\u0131nda'
    r'|oybirli\u011f|kriter|ko\u015fullar', re.I | re.U)
RE_EMA = re.compile(r'EMA\s*12', re.I)
RE_DI = re.compile(r'DI\s*[+−\-]', re.I)

# Kural beyani kosullari BIRLESTIRIR. Uc gostergeyi yan yana anan bir tanitim
# cumlesi ("... gostergelerinin nasil calistigi") kural beyani DEGILDIR.
RE_CONJ = re.compile(
    r'ayn\u0131\s+anda|\bAND\b|tamam\u0131|birlikte|sa\u011fland\u0131\u011f\u0131nda'
    r'|uyum\s+sa\u011fla|oybirli\u011f|kriter|ko\u015ful|filtre\s+sistemi|&nbsp;\+&nbsp;'
    r'|\s\+\s|\u2192|-&gt;', re.I | re.U)

# Basliklar (title/og:title/twitter:title) tam kural beyani tasiyamaz -- kisalik
# zorunlulugu var; aciklama (description) alanlari cumle kurar, TARANIR.
RE_TITLE_FIELD = re.compile(r'<title>|(?:og|twitter):title', re.I)

# R2 icin sinyal baglami: sayim, kuralin tam metnini yazmayan bir blokta da
# (or. og:description) yanlis olabilir.
RE_SIGNAL_CTX = re.compile(
    r'sinyal|G\u00fc\u00e7l\u00fc\s+Trend|Trend\s+Bozuldu', re.I | re.U)

# --- sayim beyani ------------------------------------------------------------
# C-02: test/sart/onay da kosul sayimidir ("3 bagimsiz testin oybirligi").
def _count_re(cnt):
    ind = r'(?:ba\u011f\u0131ms\u0131z\s*)?(?:teknik\s*)?'
    return re.compile(
        r'(?:\b3\s*/\s*3\s*' + cnt + r'|\b3\s*' + ind + cnt +
        r'|\b\u00fc\u00e7\s*' + ind + cnt +
        r'|\b\u00fc\u00e7l\u00fc\s*' + cnt + r')', re.I | re.U)
RE_COUNT = _count_re(r'(?:kriter|ko\u015ful|test|\u015fart|onay)')
# GOSTERGE sayimi 3'tur ve DOGRUdur: "3 teknik gosterge", "uclu filtre
# sistemi", "ucunun ayni anda ayni yonu gostermesi" serbesttir -- kapi
# yalnizca KRITER/KOSUL sozcugu ile yapilan 3'lu sayimi yasaklar (4 kosul var).
# "3 teknik gosterge" / "3 indikator" sayimi DOGRUdur: kapi bunlari saymaz.
RE_COUNT_OK = re.compile(r'\b(?:3|üç)\s*(?:teknik\s*)?(?:gösterge|gosterge|indikatör|indikator)', re.I | re.U)

# --- blok sinirlari ----------------------------------------------------------
RE_BLOCK_SPLIT = re.compile(
    r'</p>|</ul>|</ol>|</div>|</h[1-6]>|</td>|<br\s*/?>\s*<br\s*/?>'
    r'|</title>|(?=<meta\b)|(?=<link\b)'
    r'|\{%-?\s*(?:if|elif|else|endif|for|endfor|block|endblock)[^%]*-?%\}'
    r'|\n\s*\n', re.I)

RE_HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)
RE_JINJA_COMMENT = re.compile(r'\{#.*?#\}', re.S)
RE_BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.S)
RE_SCRIPT = re.compile(r'<script\b[^>]*>.*?</script>', re.S | re.I)
RE_LINE_COMMENT = re.compile(r'(?<!:)//[^\n]*')


def strip_unpublished_html(text):
    """HTML ve Jinja yorumlarini ayni uzunlukta bosluga cevirir (satir korunur)."""
    def blank(m):
        return re.sub(r'[^\n]', ' ', m.group(0))
    text = RE_HTML_COMMENT.sub(blank, text)
    text = RE_JINJA_COMMENT.sub(blank, text)
    text = RE_BLOCK_COMMENT.sub(blank, text)
    text = RE_SCRIPT.sub(lambda m: RE_LINE_COMMENT.sub(blank, m.group(0)), text)
    return text


def strip_unpublished_py(text):
    """Python satir yorumlarini ve modul/fonksiyon/sinif docstring'lerini siler.

    blog_content.py'de yayimlanan metin bir DEGER (dict/list ogesi) -- o
    KALIR. Docstring ise Expr(Constant(str)) konumundadir, yayimlanmaz."""
    out = []
    for line in text.split('\n'):
        st = line.lstrip()
        out.append(re.sub(r'[^\n]', ' ', line) if st.startswith('#') else line)
    text = '\n'.join(out)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, 'body', [])
            if body and isinstance(body[0], ast.Expr) and \
               isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                d = body[0]
                if getattr(d, 'end_lineno', None):
                    spans.append((d.lineno, d.end_lineno))
    if not spans:
        return text
    lines = text.split('\n')
    for a, b in spans:
        for i in range(a - 1, min(b, len(lines))):
            lines[i] = re.sub(r'[^\n]', ' ', lines[i])
    return '\n'.join(lines)


def blocks(text):
    """(baslangic_satiri, blok_metni) uretir -- gercek yayim birimleri."""
    pos = 0
    for m in RE_BLOCK_SPLIT.finditer(text):
        seg = text[pos:m.start()]
        if seg.strip():
            yield text.count('\n', 0, pos) + 1, seg
        pos = m.end()
    tail = text[pos:]
    if tail.strip():
        yield text.count('\n', 0, pos) + 1, tail


def scan_text(rel, text):
    bad = []
    text = strip_unpublished_py(text) if rel.endswith('.py') else strip_unpublished_html(text)
    for ln, blk in blocks(text):
        if RE_TITLE_FIELD.search(blk):
            continue                      # baslik alani: kisalik zorunlulugu
        base = bool(RE_ST.search(blk)) and bool(RE_EMA.search(blk))
        is_rule = base and ((bool(RE_ADX_THR.search(blk)) and bool(RE_CONJ.search(blk)))
                            or (bool(RE_ADX_ANY.search(blk))
                                and bool(RE_CONJ_STRONG.search(blk))))
        if is_rule and not RE_DI.search(blk):
            bad.append((rel, ln, 'R1',
                        'kural beyani DI kosulunu anmiyor (kod: ai>=25 AND dip>dim)'))
        if is_rule or RE_SIGNAL_CTX.search(blk):
            cm = RE_COUNT.search(blk)
            if cm and not RE_COUNT_OK.search(cm.group(0)):
                bad.append((rel, ln + blk.count('\n', 0, cm.start()), 'R2',
                            'kosul sayimi yanlis: "%s" -- 4 kosul var' % cm.group(0).strip()))
    if not rel.endswith('.py') and rel.replace(os.sep, '/') not in BANNED_EXEMPT:
        for i, line in enumerate(text.split('\n'), 1):
            _ln = RE_BANNED_LOGIC.sub('', line)
            m = RE_BANNED.search(_ln) or RE_BANNED_CI.search(_ln)
            if m:
                bad.append((rel, i, 'R3',
                            'kalici dil kurali: "%s" yazilmaz (kanon §2)' % m.group(0)))
    return bad


def scan_tree(root):
    bad = []
    targets = []
    for d in SCAN_DIRS:
        p = os.path.join(root, d)
        for dirpath, _dirs, files in os.walk(p):
            for fn in files:
                if fn.endswith(SCAN_EXT):
                    targets.append(os.path.join(dirpath, fn))
    for fn in SCAN_FILES:
        p = os.path.join(root, fn)
        if os.path.exists(p):
            targets.append(p)
    for p in sorted(targets):
        rel = os.path.relpath(p, root)
        try:
            txt = io.open(p, encoding='utf-8').read()
        except Exception:
            continue
        bad.extend(scan_text(rel, txt))
    return bad


# --- self-test ---------------------------------------------------------------
FIX = [
    # (ad, metin, beklenen_ihlal_sayisi)
    ("tam kural (4 kosul)",
     "<p>Supertrend yukarı + ADX ≥ 25 + DI+ &gt; DI− + EMA12 &gt; EMA99</p>", 0),
    ("DI eksik",
     "<p>Supertrend yukarı + ADX ≥ 25 + EMA12 &gt; EMA99</p>", 1),
    ("DI eksik + yanlis sayim",
     "<p>3 kriter: Supertrend, ADX ≥ 25, EMA12/EMA99</p>", 2),
    ("gosterge sayimi serbest",
     "<p>3 teknik gösterge: Supertrend, ADX ≥ 25, DI+ &gt; DI−, EMA12/EMA99</p>", 0),
    ("kural degil (sadece ADX)",
     "<p>ADX ≥ 25 güçlü trend demektir.</p>", 0),
    ("kural degil (ST + EMA, esik yok)",
     "<p>Supertrend ve EMA12 birlikte okunur.</p>", 0),
    ("HTML yorumu muaf",
     "<!-- Supertrend + ADX ≥ 25 + EMA12 -->\n<p>Merhaba</p>", 0),
    ("Jinja yorumu muaf",
     "{# Supertrend + ADX ≥ 25 + EMA12 #}\n<p>Merhaba</p>", 0),
    ("ayri bloklar birlesmez",
     "<p>Supertrend yukarı</p>\n<p>ADX ≥ 25</p>\n<p>EMA12 &gt; EMA99</p>", 0),
    ("Jinja dali izole",
     "{% if x %}<p>Supertrend + ADX ≥ 25 + DI+ &gt; DI− + EMA12</p>"
     "{% else %}<p>Supertrend + ADX ≥ 25 + EMA12</p>{% endif %}", 1),
    ("uclu FILTRE serbest (gosterge sayimi)",
     "<p>Supertrend, ADX ≥ 25, DI+ &gt; DI− ve EMA12/EMA99: üçlü filtre sistemi.</p>", 0),
    ("uclu KRITER ihlal",
     "<p>Supertrend, ADX ≥ 25 ve EMA12/EMA99: üçlü kriter sistemi.</p>", 2),
    ("SEO tanitim cumlesi kural degil",
     '<meta name="description" content="Supertrend(10,3), ADX\u226525 ve EMA12/99 '
     'g\u00f6stergelerinin nas\u0131l \u00e7al\u0131\u015ft\u0131\u011f\u0131.">', 0),
    ("og:description sayim ihlali taranir",
     '<meta property="og:description" content="teknik temeli: 3 kriter ayn\u0131 anda '
     'Supertrend + ADX \u2265 25 + EMA12/99 ye\u015fil.">', 2),
    ("og:title muaf",
     '<meta property="og:title" content="Supertrend + ADX \u2265 25 + EMA12/99">', 0),
    ("sayim tek basina (sinyal baglami)",
     '<meta property="og:description" content="teknik temel: 3 kriter ayn\u0131 anda '
     'ye\u015fil oldu\u011funda trend sinyali \u00fcretilir.">', 1),
    ("sayim sinyal disi baglamda muaf",
     '<p>Portf\u00f6y kurarken 3 kriter kullan\u0131n: sekt\u00f6r, b\u00fcy\u00fckl\u00fck, likidite.</p>', 0),
    ("JS blok yorumu muaf",
     '<script>/* SSR 3 kriter checklist sinyal */</script>', 0),
    ("JS satir yorumu muaf (URL korunur)",
     '<script>// 3 kriter sinyal rozeti\nvar u="https://x/y";</script>', 0),
    ("C-02 eski hero: esiksiz ADX + 3 test",
     "<p>Supertrend, ADX ve EMA12/99 \u2014 sinyal bu 3 ba\u011f\u0131ms\u0131z testin "
     "oybirli\u011fiyle do\u011far.</p>", 2),
    ("C-02 uc onay sayimi",
     "<p>G\u00fc\u00e7l\u00fc Trend sinyali \u00fc\u00e7 onay ister.</p>", 1),
    ("C-02 arti isaretli liste kural degil",
     "<p>Supertrend(10,3) + ADX + EMA12/99 teknik analiz sinyali.</p>", 0),
    ("C-02 gosterge listesi kural degil",
     "<p>Supertrend, ADX, EMA12/99 tabanl\u0131 teknik analiz.</p>", 0),
    ("liste bloğu butun kalir",
     "<ul><li>Supertrend</li><li>ADX ≥ 25</li><li>DI+ &gt; DI−</li>"
     "<li>EMA12 &gt; EMA99</li></ul>", 0),
    ("C-60 Ucretsiz", "<p>Tamamen Ücretsiz</p>", 1),
    ("C-60 kaynak adi", "<div>Veri kaynağı: Yahoo Finance</div>", 1),
    ("C-60 LONG", "<li>ST LONG trendi</li>", 1),
    ("C-60 Stop Loss", "<small>Stop Loss: alt bant</small>", 1),
    ("C-60 ideal giris", "<h2>İdeal Giriş Noktası</h2>", 1),
    ("C-52 Hedef satiri", "<span><strong>Hedef:</strong>12 ₺</span>", 1),
    ("C-52 TP1", "<span>TP1</span>", 1),
    ("C-52 R/R", "<span>R/R </span><strong>1:2,0</strong>", 1),
    ("C-52 stop bolgesi", "<p>Fiyat stop bölgesine yakın</p>", 1),
    ("C-52 analist hedef kalir", "<span>Analist Hedef Fiyatı</span>", 0),
    ("C-61 Giriş Fiyatı buyuk harf", "<div>Giriş Fiyatı</div>", 1),
    ("C-61 stop-loss tireli", "<p>stop-loss seviyeleri</p>", 1),
    ("C-61 GİRİŞ KALİTESİ", "<th>GİRİŞ KALİTESİ</th>", 1),
    ("C-61 Kovalama", "<span>Kovalama</span>", 1),
    ("C-61 Kazanma Oranı", "<div>Sinyal Kazanma Oranı</div>", 1),
    ("C-60 yorum muaf", "<!-- yfinance Ücretsiz LONG -->", 0),
    ("C-60 indexOf esleme muaf", "<script>if (z.indexOf('İdeal Giriş') === 0) x=1;</script>", 0),
]

PY_FIX = [
    ("py docstring muaf",
     '"""Supertrend + ADX ≥ 25 + EMA12 kurali."""\nX = 1\n', 0),
    ("py deger taranir",
     'D = {"a": "Supertrend + ADX ≥ 25 + EMA12/EMA99 üçlü kriter"}\n', 2),
    ("py satir yorumu muaf",
     '# Supertrend + ADX ≥ 25 + EMA12\nX = 1\n', 0),
]


def self_test():
    ok = total = 0
    for name, txt, want in FIX:
        total += 1
        got = len(scan_text('t.html', txt))
        if got == want:
            ok += 1
        else:
            print("  FAIL %-28s bekle %d, bulundu %d" % (name, want, got))
    for name, txt, want in PY_FIX:
        total += 1
        got = len(scan_text('t.py', txt))
        if got == want:
            ok += 1
        else:
            print("  FAIL %-28s bekle %d, bulundu %d" % (name, want, got))
    print("self-test %d/%d" % (ok, total))
    return 0 if ok == total else 1


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='sigrule-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    return d


def main():
    if '--self-test' in sys.argv:
        return self_test()
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = tree_at_ref(ref) if ref else repo
    bad = scan_tree(root)
    tag = " (ref %s)" % ref if ref else ""
    if not bad:
        print("K-DK OK — sinyal uretim kuralini anlatan her blok DI kosulunu "
              "aniyor ve kosul sayimi dogru%s." % tag)
        return 0
    print("K-DK KIRIK — %d ihlal%s:" % (len(bad), tag))
    for rel, ln, kind, msg in sorted(bad):
        print("  [%s] %s:%s  %s" % (kind, rel, ln, msg))
    print("\n  Kanon (app.py _bar_signal_fast): Supertrend yonu + ADX >= 25 +")
    print("  DI yonu (DI+ vs DI-) + EMA12/EMA99 -> 3 gosterge, 4 KOSUL.")
    print("  /metodoloji formul kutusu bu dordunu birlikte yaziyor.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
