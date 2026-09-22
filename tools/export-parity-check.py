#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-CC (22.09.2026) — INDIRILEN DOSYA, EKRANDAKI SAYIYI VERMELI.

Kullanicinin "CSV indir" ile aldigi dosya, ekrandaki tablonun BASKA bir
yazimidir; ayni alanin orada baska bir sayiyla/adla cikmasi sessiz bir
celiskidir — kullanici iki kaynagi yan yana koydugunda hangisinin dogru
oldugunu bilemez, ve Excel'de filtre/esik uygularken sitenin KENDI bandina
gore YANLIS tarafa duser.

22.09 CANLI OLCUM (/api/data, 217 hisse):
  · /tarama "Hacim Orani" ekranda 2 ondalik (`rvolCell` -> "1,46×"), CSV'de
    1 ondalikti ("1,5×") -> **195/217 hissede sayi FARKLI**, **14 hisse**
    sayfanin kendi bandini (>=1,5 "Yuksek hacim") karsi tarafa geciyordu.
  · `s.vol_ratio ?` (falsy) yuzunden vol_ratio TAM 0 olan **5 hissede**
    hucre BOS kaliyordu; ekran "0,00× · Dusuk hacim" diyordu.
  · "Giris Kalitesi" sutunu ham makine kodu basiyordu (IDEAL/IYI/DIKKATLI/
    UZAK); ekranda eqLabel() ile "Ideal/Iyi/Dikkatli/**Kovalama**" —
    UZAK->Kovalama eslemesi CSV okuyucusu icin tamamen kayipti (217/217).
  · /portfolio K/Z % ekranda bpFormatPct(...,1) ("+3,4%"), CSV'de
    `.toFixed(2)` ve ISARETSIZ ("3,40") — ayni satir, iki sayi.

DORT EKSEN (hepsi export fonksiyonunun GOVDESINDE aranir):
  P1 HASSASIYET: ayni alan export'ta `toFixed(A)`, dosyanin geri kalaninda
     (ekran yolu) `toFixed(B)` / `bpFormatPct(...,B)` ile basiliyorsa A!=B.
  P2 FALSY: sayisal alanda `X.f ? ... : ''` — 0 gecerli bir degerdir,
     `!= null` kullanilmali.
  P3 `|| 0` / `or 0`: bilinmeyeni bir IDDIAYA ("0,0") cevirir.
  P4 HAM KOD: dosya bir alan icin etiket esleyici (eqLabel/sigLabel)
     kullaniyorsa export de AYNI alanda onu cagirmali.

Kullanim:
  python3 tools/export-parity-check.py
  python3 tools/export-parity-check.py --ref SHA
"""
import os, re, sys, io, subprocess, tempfile, tarfile

EXPORT_FN = re.compile(r"function\s+(exportCSV|exportJSON|downloadCSV)\s*\([^)]*\)\s*\{")
FIELD_FIXED = re.compile(r"\b(\w{1,20})\.(\w{1,30})\s*\)?\s*\.toFixed\((\d)\)")
FIELD_PCT   = re.compile(r"bpFormatPct\(\s*(\w{1,20})\.(\w{1,30})\s*,\s*(\d)\s*\)")

# ── P1 icin ETIKET cikarimi ────────────────────────────────────────────────
# Alan adi bicimleme yerinde cogu zaman GORUNMEZ: ekran yolu `rvolCell(s.vol_ratio)`
# cagirir, sayiyi yardimci fonksiyonun govdesindeki `v.toFixed(2)` basar; disa
# aktarim ise `s.vol_ratio.toFixed(1)` yazar. Ad-eslemesi yapmadan kapi K-CC'nin
# ASIL bulgusunu goremez (ilk yazimda tam olarak bu oldu).
# ⛔ DERS: bir paritenin kapisini yazarken iki tarafin AYNI SOZDIZIMINI
#    kullandigini varsayma; ortak anahtari (alan adi) once CIKAR.
ANY_FIXED   = re.compile(r"([A-Za-z_$][\w$]{0,29})\s*\)?\s*\.toFixed\((\d)\)")
ANY_PCT     = re.compile(r"bpFormatPct\(\s*[^,()]{0,60}?([A-Za-z_$][\w$]{0,29})\s*,\s*(\d)\s*\)")
ASSIGN_FIXED= re.compile(r"(?:var|let|const)\s+([A-Za-z_$][\w$]{0,29})\s*=[^;\n]{0,160}?\.toFixed\((\d)\)")
ASSIGN_PCT  = re.compile(r"(?:var|let|const)\s+([A-Za-z_$][\w$]{0,29})\s*=[^;\n]{0,160}?bpFormatPct\([^;\n]{0,60}?,\s*(\d)\s*\)")
FN_DEF      = re.compile(r"(?:function\s+([A-Za-z_$][\w$]{0,29})\s*\(|(?:var|let|const)\s+([A-Za-z_$][\w$]{0,29})\s*=\s*\([^)]{0,80}\)\s*=>)")
# Ad normalizasyonu: pnlVal/_pnlNum/pnlPct gibi yerel kopyalar ayni anahtara duser.
def _norm(name):
    return re.sub(r"^_+", "", name).lower()
FALSY       = re.compile(r"\b(\w{1,20})\.(\w{1,30})\s*\?[^:\n]{0,120}:\s*''")
OR_ZERO     = re.compile(r"\b(\w{1,20})\.(\w{1,30})\s*\|\|\s*0\b")
LABELER     = re.compile(r"\b(eqLabel|sigLabel)\(\s*(\w{1,20})\.(\w{1,30})")
RAW_FIELD   = re.compile(r"\b(\w{1,20})\.(\w{1,30})\b")

# Metin/tarih alanlari: `? ... : ''` bunlarda mesru (bos metin = bos hucre).
TEXT_FIELDS = {'ticker', 'name', 'sector', 'signal', 'date', 'signal_date',
               'entry_quality', 'rsi_zone', 'adx_label', 'tier', 'kap_url'}

def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)

def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'(?<![:\'"\\])//[^\n]*', lambda m: _blank(m.group(0)), s)
    return s

def body_of(src, start):
    """Kaba ama yeterli: acilis susluyu dengeleyerek fonksiyon govdesi."""
    i = src.index('{', start)
    depth, j = 0, i
    while j < len(src):
        if src[j] == '{': depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                return i, j + 1
        j += 1
    return i, len(src)

def scan_tree(root):
    bad = []
    tdir = os.path.join(root, 'templates')
    for dp, _, fns in os.walk(tdir):
        for fn in sorted(fns):
            if not fn.endswith('.html'):
                continue
            path = os.path.join(dp, fn)
            rel  = os.path.relpath(path, root)
            src  = strip_comments(io.open(path, encoding='utf-8', errors='replace').read())
            for m in EXPORT_FN.finditer(src):
                b0, b1 = body_of(src, m.start())
                body   = src[b0:b1]
                screen = src[:b0] + src[b1:]
                line0  = src[:b0].count('\n')

                def ln(off):
                    return line0 + body[:off].count('\n') + 1

                # ── yardimci fonksiyon govdelerindeki hassasiyet ──────────
                helper_prec = {}
                for k in FN_DEF.finditer(src):
                    hname = k.group(1) or k.group(2)
                    if not hname:
                        continue
                    try:
                        h0, h1 = body_of(src, k.start())
                    except ValueError:
                        continue
                    ds = {int(x.group(2)) for x in ANY_FIXED.finditer(src[h0:h1])}
                    ds |= {int(x.group(2)) for x in ANY_PCT.finditer(src[h0:h1])}
                    if ds:
                        helper_prec[hname] = ds

                def prec_map(text):
                    out = {}
                    for pat in (ANY_FIXED, ANY_PCT):
                        for k in pat.finditer(text):
                            out.setdefault(_norm(k.group(1)), set()).add(int(k.group(2)))
                    for pat in (ASSIGN_FIXED, ASSIGN_PCT):
                        for k in pat.finditer(text):
                            out.setdefault(_norm(k.group(1)), set()).add(int(k.group(2)))
                    # HELPER(x.field) -> alan adina yardimcinin hassasiyeti
                    for hname, ds in helper_prec.items():
                        for k in re.finditer(re.escape(hname) + r"\(\s*\w{1,20}\.(\w{1,30})", text):
                            out.setdefault(_norm(k.group(1)), set()).update(ds)
                    return out

                scr = prec_map(screen)
                # ── ekran yolunun etiketlenen alanlari ────────────────────
                labeled = {}
                for k in LABELER.finditer(screen):
                    labeled.setdefault(k.group(3), set()).add(k.group(1))

                # P1
                seen = set()
                for pat in (ANY_FIXED, ANY_PCT, ASSIGN_FIXED, ASSIGN_PCT):
                    for k in pat.finditer(body):
                        f, d = _norm(k.group(1)), int(k.group(2))
                        if f not in scr or d in scr[f] or (f, d) in seen:
                            continue
                        seen.add((f, d))
                        bad.append((rel, ln(k.start()), 'P1',
                                    f"`{k.group(1)}` disa aktarimda {d} ondalik, ekranda "
                                    f"{sorted(scr[f])} — indirilen dosya ekrandakinden "
                                    f"BASKA bir sayi veriyor"))
                # P2
                for k in FALSY.finditer(body):
                    f = k.group(2)
                    if f in TEXT_FIELDS:
                        continue
                    bad.append((rel, ln(k.start()), 'P2',
                                f"`{f} ? ... : ''` — 0 GECERLI bir degerdir, falsy kontrol "
                                f"onu bos hucreye cevirir (`!= null` kullan)"))
                # P3
                for k in OR_ZERO.finditer(body):
                    bad.append((rel, ln(k.start()), 'P3',
                                f"`{k.group(2)} || 0` — bilinmeyen deger bir IDDIAYA "
                                f"(\"0\") ceviriliyor"))
                # P4
                for f, fns_ in labeled.items():
                    used = [k for k in RAW_FIELD.finditer(body) if k.group(2) == f]
                    if not used:
                        continue
                    if not any(l + '(' in body[max(0, k.start()-40):k.start()+2]
                               for k in used for l in fns_):
                        bad.append((rel, ln(used[0].start()), 'P4',
                                    f"`{f}` disa aktarimda HAM basiliyor; ekran "
                                    f"{sorted(fns_)} ile etiketliyor (ayni is, iki kanon)"))
    return bad

def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='exportparity-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    return d

def main():
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    root = tree_at_ref(ref) if ref else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = scan_tree(root)
    if not bad:
        print(f"K-CC OK — disa aktarim ekranla ayni sayiyi/adi veriyor"
              f"{' (ref '+ref+')' if ref else ''}.")
        return 0
    print(f"K-CC KIRIK — {len(bad)} ihlal{' (ref '+ref+')' if ref else ''}:")
    for rel, l, kind, msg in sorted(bad):
        print(f"  [{kind}] {rel}:{l}  {msg}")
    print("\n  Kural: indirilen dosya ekrandaki SAYIYI ve ADI verir.")
    print("         Kanon: bp-format.js (bpFormatPct/bpDirSign/bpZero) + bp-vocab.js (eqLabel/sigLabel)")
    return 1

if __name__ == '__main__':
    sys.exit(main())
