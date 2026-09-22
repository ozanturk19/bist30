#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-BS (22.09.2026) — GOSTERGE PANELI TEK AGIZDAN KONUSUR.

Bir rozet ile hemen altindaki teknik detay satiri AYNI gostergeyi anlatiyorsa,
ikisi AYNI kaynaktan ve AYNI kanondan okumak zorundadir. Uc ihlal sinifi canli
olarak dogrulandi (22.09, /api/data 217 hisse + tarayici olcumu):

  A) KAYNAK SAPMASI. CPO-1665 `detail`/`ok` alanlarini otoriter kaynaga
     (signalData.indicators) tasidi, kardes alan `techDetail` chart ozetinde
     (`s.st_bull` vb.) kaldi -> /hisse/TAVHL rozet "↓ Düşüş" derken teknik
     satir "Supertrend(10,3): LONG" basiyordu.

  B) K-BO SINIF ADI UZERINDEN. Hacim yon-bagimsiz bir buyukluktur; kapi 34
     token/ham-hex ariyor, SINIF ADINI degil. hisse.html hacim rozetini
     `ind-bull` (= --bp-al) ile boyuyordu -> vol_ratio >= 3 olan 4 hissenin
     DORDU DE BEKLE, ikisi o gun dusmus (SASA -1,70% · USAK -3,85%).

  C) BOLGE ADI BIR VAAT TASIR. `rsi_zone` sinyalden bagimsiz turetilir;
     "İdeal Giriş Penceresi" long-only bir urunde ancak AL'da anlamlidir.
     Canli: bu bolge adini tasiyan 46 hissenin 45'i AL DEGIL (3'u SAT).
     Tek kanon bp-format.js `bpRsiZoneText(zone, signal)`.

YORUMLAR SOYULUR (K-BN dersi 35 + K-BQ dersi 42: soyulan yorum ayni uzunlukta
BOSLUGA cevrilir, satir numarasi kaymaz; yakinlik pencereleri ANLAMLI karakter
sayar).

Kullanim:
  python3 tools/indicator-panel-canon-check.py            # calisan agac
  python3 tools/indicator-panel-canon-check.py --ref SHA  # o commit'in agaci
"""
import os, re, sys, subprocess, tempfile, tarfile, io

# ── A) Otoriter olmayan bull/bear bayraklari ────────────────────────────────
# `s.*` = chart ozeti (ayri onbellek dongusu, gunlerce geride kalabilir).
# Otoriter kaynak `signalData.indicators.*`. Tek MESRU kullanim: ternary'nin
# FALLBACK dali (`? _siInd.x.bull : s.x_bull`) — yani ayni satirda `_siInd`
# gecmeli.
STALE_FLAG = re.compile(r'\bs\.(st_bull|st_bear|adx_bull|adx_bear|e12_bull|e12_bear)\b')
FALLBACK_OK = re.compile(r'_siInd')

# ── B) Hacim + yon sinif adi ───────────────────────────────────────────────
# K-BO'nun SINIF ADI kanali. `ind-bull`/`ind-bear` --bp-al/--bp-sat'e cozulur;
# `tech-row-bull`/`-bear`, `.up`/`.dn` de yon eksenidir.
VOL_ID = re.compile(r'(?<![a-zA-Z])(r_?vol|avg_?rvol|vol_ratio|volratio|vr)(?![a-zA-Z])')
DIR_CLASS = re.compile(r'\b(ind-(?:bull|bear)|tech-row-(?:bull|bear)|tile-(?:up|down)|sc-chg\s+(?:up|dn))\b')

# ── C) rsi_zone kanonu ─────────────────────────────────────────────────────
RSI_ZONE_USE = re.compile(r'\brsi_zone\b')
RSI_ZONE_CANON = re.compile(r'\bbpRsiZoneText\s*\(')
# Bolge adini ham metin olarak basan yuzeyler (kanondan gecmeden)
IDEAL_LITERAL = re.compile(r'İdeal Giriş Penceresi')

TARGET_EXT = ('.html', '.js')
SCAN_DIRS = ('templates', 'static')
# bp-format.js kanonun KENDISI: bpRsiZoneText govdesinde 'İdeal Giriş' gecer.
CANON_FILE = 'static/bp-format.js'


def _blank(t):
    """Ayni uzunlukta bosluk, SATIR SONLARI korunur (K-BN dersi 35)."""
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_comments(src, path):
    """JS blok/satir yorumlari + Jinja {# #} + HTML <!-- -->. Hepsi bosluga."""
    def rep(m):
        return _blank(m.group(0))
    src = re.sub(r'\{#.*?#\}', rep, src, flags=re.S)
    src = re.sub(r'<!--.*?-->', rep, src, flags=re.S)
    # JS yorumlari: `//` ve `/* */`. Dikkat — `https://` ve regex literali
    # yanlis pozitif uretmesin diye `//` yalniz satir basi/bosluk sonrasi.
    src = re.sub(r'/\*.*?\*/', rep, src, flags=re.S)
    src = re.sub(r'(?m)(^|[\s;{(])//[^\n]*', lambda m: m.group(1) + _blank(m.group(0)[len(m.group(1)):]), src)
    return src


def iter_files(root):
    for d in SCAN_DIRS:
        base = os.path.join(root, d)
        for dp, _dn, fn in os.walk(base):
            for f in fn:
                if f.endswith(TARGET_EXT):
                    yield os.path.join(dp, f)


def check_tree(root):
    viol = []
    for path in iter_files(root):
        rel = os.path.relpath(path, root)
        try:
            raw = io.open(path, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        src = strip_comments(raw, rel)
        lines = src.split('\n')
        raw_lines = raw.split('\n')

        for i, line in enumerate(lines, 1):
            # A) bayat bull/bear bayragi, fallback disinda
            for m in STALE_FLAG.finditer(line):
                if not FALLBACK_OK.search(line):
                    viol.append((rel, i, 'A', 'otoriter olmayan `s.%s` (signalData.indicators kullan)' % m.group(1),
                                 raw_lines[i - 1].strip()[:150]))

            # B) hacim tanimlayicisi + yon sinif adi ayni deyimde
            if VOL_ID.search(line) and DIR_CLASS.search(line):
                viol.append((rel, i, 'B', 'hacim (yon-bagimsiz) YON sinifiyla boyaniyor: %s'
                             % DIR_CLASS.search(line).group(1),
                             raw_lines[i - 1].strip()[:150]))

        # C) rsi_zone tuketen bir dosya kanonu cagirmiyorsa
        if rel != CANON_FILE:
            if RSI_ZONE_USE.search(src) and not RSI_ZONE_CANON.search(src):
                ln = next((i for i, l in enumerate(lines, 1) if RSI_ZONE_USE.search(l)), 0)
                viol.append((rel, ln, 'C', '`rsi_zone` basiliyor ama bpRsiZoneText kanonundan gecmiyor',
                             raw_lines[ln - 1].strip()[:150] if ln else ''))
            for i, line in enumerate(lines, 1):
                if IDEAL_LITERAL.search(line) and 'metodoloji' not in rel and 'blog' not in rel:
                    # Kosulsuz ham literal (ozet.html gibi ZATEN AL-filtreli
                    # listeler haric: orada baslik kendi filtresinin altinda).
                    # K-CH (22.09): bu kural "KOSULSUZ ham literal" diyordu ama
                    # kosulu HIC test etmiyordu -- yalnizca iki YOL (metodoloji,
                    # blog) muafti. Oysa muafiyetin gerekcesi yol degil TUR:
                    # o yuzeyler adi RENDER etmiyor, TANIMLIYOR ve kosulunu de
                    # yaziyor. Ayni tur `static/learning-mode.js` sozlugunde de
                    # var (Ogrenme Modu = /metodoloji'nin satir-ici hali).
                    # Kural artik beyanina uyuyor: adi KOSULUYLA BIRLIKTE yazan
                    # bir satir (hem "Güçlü Trend" hem "Nötr Bölge" geciyorsa)
                    # kanonu ogretiyordur, ihlal etmez. Yol muafiyeti yerine
                    # genellenebilir kosul testi -- her yuzey icin gecerli.
                    ogretici = 'Güçlü Trend' in line and 'Nötr Bölge' in line
                    if 'ideal_al' not in line and 'İdeal Giriş Noktası' not in line and not ogretici:
                        viol.append((rel, i, 'C', 'bolge adi ham literal olarak basiliyor',
                                     raw_lines[i - 1].strip()[:150]))
    return viol


def export_ref(ref):
    tmp = tempfile.mkdtemp(prefix='k-bs-')
    tar = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(tmp)
    return tmp


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
        os.chdir(root)
        root = export_ref(ref)
    viol = check_tree(root)
    if not viol:
        print('K-BS OK — gosterge paneli tek kanon (A/B/C temiz).')
        return 0
    print('K-BS IHLAL: %d' % len(viol))
    for rel, ln, cls, msg, snip in viol:
        print('  [%s] %s:%s  %s' % (cls, rel, ln, msg))
        if snip:
            print('        %s' % snip)
    return 1


if __name__ == '__main__':
    sys.exit(main())
