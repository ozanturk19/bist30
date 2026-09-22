#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/dynamic-tip-canon-check.py — K-CX (kapı 69)
DURUM DEĞİŞİNCE ERİŞİLEBİLİR KANAL DA GÜNCELLENMELİ.

SORU — daha önce hiç sorulmadı:
  K-AH (21.09) native `title=`i yasakladı: dokunmatikte ve klavye ODAĞINDA hiç
  gösterilmez, kanonik kanal `[data-tip]` (bp-tooltip.js). Ama K-AH'nin kapısı
  (title-tooltip-check.js) `data-tip` VARLIĞINI bir sahte-pozitif muafiyeti
  sayar — TAZELİĞİNİ değil. Bir eleman açılışta doğru `data-tip` taşıyıp,
  DURUMU değiştiğinde açıklamayı yalnız `el.title`a yazarsa:
    · kapı geçer (data-tip var),
    · fare kullanıcısı güncel metni görür,
    · dokunmatik/klavye kullanıcısı AÇILIŞ metnini görmeye devam eder.
  Canlı ölçüm 22.09 (/hisse/ASELS, izleme listesi dolu): buton "Takipte ✓"
  gösterirken `data-tip` hâlâ "Sinyal değişiminde bildirim al" diyordu —
  yıkıcı eylem (listeden çıkarma) TERS tarif ediliyordu.

ÖLÇÜT (taban SIFIR):
  R1 — Şablon/JS kodunda native `title` özniteliğine RUNTIME yazma yasak:
       `<expr>.title = ...` ve `setAttribute('title', ...)`.
       Muaf: `document.title` (sayfa başlığı, tooltip değil),
             `<iframe>`e title verme (SC 4.1.2 zorunlu) — `iframe` geçen satır.
       Kanonik yazıcı: `_bpTip(el, text)` → data-tip yazar + title siler.
  R2 — Aynı elemanda AYNI ANDA statik `title=` ve `data-tip=` bulunamaz
       (iki kanal = iki kanon; hangisi doğru sorusu kullanıcıya kalır).

⛔ Bu kapı STATİK ölçer ve bilerek öyle: K-AH'nin canlı DOM koşusu durum,
   hata ve gizli-sekme dallarını HİÇ tetiklemiyor (canlı doğrulandı: anomali
   rozeti canlı evrende 0/217, AI kaynak rozeti ?tab=ai olmadan display:none).
   Bir kusur ancak ÇALIŞAN dalda görünüyorsa, onu arayan kapı kördür.

Kullanım: python3 tools/dynamic-tip-canon-check.py [--kill-fix] [--self-test]
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def strip_comments(src, is_html):
    """HTML, Jinja ve JS yorumlarını boşlukla değiştirir (satır sayısı korunur)."""
    def blank(m):
        return re.sub(r'[^\n]', ' ', m.group(0))
    if is_html:
        src = re.sub(r'<!--.*?-->', blank, src, flags=re.S)
        src = re.sub(r'\{#.*?#\}', blank, src, flags=re.S)
    src = re.sub(r'/\*.*?\*/', blank, src, flags=re.S)
    src = re.sub(r'(?m)^(\s*)//.*$', lambda m: m.group(1) + ' ' * (len(m.group(0)) - len(m.group(1))), src)
    return src

R1_ASSIGN  = re.compile(r'(?<![\w$])([\w$.\[\]\'"]+)\.title\s*=(?!=)')
R1_SETATTR = re.compile(r'setAttribute\(\s*[\'"]title[\'"]\s*,')
# statik etikette hem title= hem data-tip=
TAG        = re.compile(r'<[a-zA-Z][^>]*>', re.S)

def scan(files):
    out = []
    for f in files:
        rel = os.path.relpath(f, ROOT)
        raw = open(f, encoding='utf-8').read()
        is_html = f.endswith('.html')
        src = strip_comments(raw, is_html)
        for i, line in enumerate(src.split('\n'), 1):
            if 'iframe' in line.lower():
                continue
            for m in R1_ASSIGN.finditer(line):
                if m.group(1).endswith('document') or m.group(1) == 'document':
                    continue
                out.append((rel, i, 'R1', line.strip()[:110]))
            if R1_SETATTR.search(line):
                out.append((rel, i, 'R1', line.strip()[:110]))
        for m in TAG.finditer(src):
            tag = m.group(0)
            if tag.lower().startswith('<iframe'):
                continue
            if re.search(r'(?<![\w-])title\s*=', tag) and 'data-tip' in tag:
                ln = src[:m.start()].count('\n') + 1
                out.append((rel, ln, 'R2', tag.strip().replace('\n', ' ')[:110]))
    return out

def main():
    files = sorted(glob.glob(os.path.join(ROOT, 'templates', '*.html'))) + \
            sorted(glob.glob(os.path.join(ROOT, 'static', 'js', '*.js')))
    if '--self-test' in sys.argv:
        import tempfile
        cases = [
            ("btn.title = 'x';", 1, 'R1 duz atama'),
            ("  el.setAttribute('title', t);", 1, 'R1 setAttribute'),
            ("document.title = 'Sayfa';", 0, 'document.title muaf'),
            ("<iframe title=\"Harita\" data-tip=\"x\"></iframe>", 0, 'iframe muaf'),
            ("// btn.title = 'x';", 0, 'JS satir yorumu ayiklanir'),
            ("<!-- btn.title = 'x'; -->", 0, 'HTML yorumu ayiklanir'),
            ("<span title=\"A\" data-tip=\"B\">x</span>", 1, 'R2 iki kanal'),
            ("<span data-tip=\"B\">x</span>", 0, 'yalniz data-tip temiz'),
            ("_bpTip(btn, 'Portföyde');", 0, 'kanonik yazici temiz'),
        ]
        ok = 0
        d = tempfile.mkdtemp()
        for src, exp, name in cases:
            p = os.path.join(d, 'x.html')
            open(p, 'w', encoding='utf-8').write(src + '\n')
            got = len(scan([p]))
            mark = 'PASS' if got == exp else 'FAIL'
            if got == exp: ok += 1
            print(f"  [{mark}] {name}: beklenen={exp} olculen={got}")
        print(f"self-test {ok}/{len(cases)}")
        return 0 if ok == len(cases) else 1

    if '--kill-fix' in sys.argv:
        # POZITIF KONTROL: kusuru geri ENJEKTE et, dedektor yakalamali.
        import tempfile, shutil
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'kill.html')
        open(p, 'w', encoding='utf-8').write(
            "<script>\nfunction u(b){ b.title = 'Takipte'; }\n</script>\n"
            "<button title=\"A\" data-tip=\"B\">x</button>\n")
        hits = scan([p])
        print(f"kill-fix: enjekte edilen 2 kusurdan {len(hits)} tanesi yakalandi")
        for h in hits: print("   ", h[2], h[3])
        return 0 if len(hits) == 2 else 1

    hits = scan(files)
    for rel, ln, rule, txt in hits:
        print(f"{rule}  {rel}:{ln}  {txt}")
    print(f"\ndynamic-tip-canon-check: {len(hits)} ihlal (taban 0)")
    return 1 if hits else 0

if __name__ == '__main__':
    sys.exit(main())
