#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/global-collision-check.py — K-BE: KURESEL AD CAKISMASI

SORU: bir sablonun satir-ici betigi, o sayfanin YUKLEDIGI paylasilan bir
dosyanin ust duzey adini yeniden tanimliyor mu?

OLCULDU (21.09.2026): hisse.html hem `safeHref`i satir-ici tanimliyordu hem de
`bp-vocab.js`i yukluyordu -- o dosya da ayni adi UST DUZEYDE tanimlar.
`bp-vocab.js` `defer` ile yuklendigi icin belge ayristirmasi BITTIKTEN sonra
calisir ve satir-ici tanimi EZER. Yani sayfadaki 4 cagri (KAP/haber baglantisi,
hepsi async fetch sonrasi) sablonda YAZAN kodu degil, paylasilan dosyadakini
kullaniyordu. Iki uygulama bugun ayni davraniyordu -- kusur GORUNMUYORDU; ama
birini degistiren sonraki tur icin sessiz bir tuzakti: kazanani `defer`
zamanlamasi belirler, yazan kisi degil.

⛔ BU, BILEREK KAPSAM DISI BIRAKILMIS BIR MADDENIN BEDELIDIR: bp-vocab.js'in
kendi yorumu "hisse.html kendi escHtml adiyla ayri bir fonksiyon kullaniyor --
buraya TASINMADI, ayri/dusuk-oncelikli konu" diyor. Farkli adli `escHtml`
gercekten zararsizdi; ama AYNI adli `safeHref` gozden kacmisti.

KANON: paylasilan dosya bir adi ust duzeyde disa aciyorsa, o dosyayi yukleyen
sablon AYNI adi yeniden tanimlayamaz. (Paylasilan dosyalarin cogu zaten IIFE
sarmali -- onlarin ic adlari kapsama girmez, dogru davranis budur.)

OLCUM: ust duzey = GIRINTISIZ bildirim (IIFE icindekiler girintilidir).
Yorumlar ve dizgeler soyulur. Yalnizca sablonun GERCEKTEN yukledigi <script
src=...> dosyalari karsilastirilir -- sayfa yuklemiyorsa cakisma da yoktur.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SRC_RE = re.compile(r'<script[^>]*\bsrc=["\']([^"\']+)["\']', re.I)
INLINE_RE = re.compile(r'<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>', re.S | re.I)
DECL_RE = re.compile(
    r'^(?:function\s+([A-Za-z_$][\w$]*)\s*\(|(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=)', re.M)


def strip_comments(src):
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in '"\'`':
            q = c
            out.append(c)
            i += 1
            while i < n:
                if src[i] == '\\' and i + 1 < n:
                    out.append('  ')
                    i += 2
                    continue
                out.append('\n' if src[i] == '\n' else src[i])
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            while i < n and not (src[i] == '*' and i + 1 < n and src[i + 1] == '/'):
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            out.append('  ')
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def top_level(src):
    clean = strip_comments(src)
    g = {}
    for m in DECL_RE.finditer(clean):
        name = m.group(1) or m.group(2)
        g.setdefault(name, clean[:m.start()].count('\n') + 1)
    return g


def shared_files():
    out = {}
    for p in sorted(glob.glob('static/*.js') + glob.glob('static/js/*.js')):
        out[p] = top_level(open(p, encoding='utf-8').read())
    return out


def scan(templates, shared):
    hits = []
    pages_checked = 0
    for t in templates:
        txt = open(t, encoding='utf-8').read()
        loaded = []
        for m in SRC_RE.finditer(txt):
            u = m.group(1).split('?')[0].lstrip('/')
            if u in shared:
                loaded.append(u)
        if not loaded:
            continue
        pages_checked += 1
        inline = {}
        for m in INLINE_RE.finditer(txt):
            base = txt[:m.start(1)].count('\n') + 1
            for name, ln in top_level(m.group(1)).items():
                inline.setdefault(name, base + ln - 1)
        for u in loaded:
            for name in sorted(set(inline) & set(shared[u])):
                hits.append((t, inline[name], name, u, shared[u][name]))
    return hits, pages_checked


def main():
    shared = shared_files()
    exported = sum(len(v) for v in shared.values())
    templates = sorted(glob.glob('templates/*.html'))
    hits, pages = scan(templates, shared)

    # POZITIF KONTROL — sahte cakisma enjekte edilince yakalaniyor mu?
    probe_name = None
    for p, g in shared.items():
        if g:
            probe_name = (p, sorted(g)[0])
            break
    if probe_name is None:
        print('K-BE OLCULEMEDI: hicbir paylasilan dosya ust duzey ad disa acmiyor.')
        return 2
    ppath, pname = probe_name
    import tempfile
    pos_ok = 0
    with tempfile.TemporaryDirectory() as d:
        fake = os.path.join(d, 'probe.html')
        with open(fake, 'w', encoding='utf-8') as fh:
            fh.write('<script src="/%s?v=1"></script>\n<script>\nfunction %s(x){return x;}\n</script>'
                     % (ppath, pname))
        probe_hits, _ = scan([fake], shared)
        if any(h[2] == pname for h in probe_hits):
            pos_ok = 1
        else:
            print('  ! POZITIF KONTROL DUSTU: enjekte edilen cakisma yakalanamadi')

    # NEGATIF KONTROL — dosya YUKLENMIYORSA cakisma sayilmamali
    neg_ok = 0
    with tempfile.TemporaryDirectory() as d:
        fake = os.path.join(d, 'probe2.html')
        with open(fake, 'w', encoding='utf-8') as fh:
            fh.write('<script>\nfunction %s(x){return x;}\n</script>' % pname)
        if not scan([fake], shared)[0]:
            neg_ok = 1
        else:
            print('  ! NEGATIF KONTROL DUSTU: yuklenmeyen dosya icin cakisma bildirildi')

    print('global-collision-check (K-BE kuresel ad cakismasi)')
    print('  paylasilan dosya: %d · ust duzey disa acilan ad: %d · betik yukleyen sablon: %d'
          % (len(shared), exported, pages))
    print('  pozitif kontrol: %d/1 · negatif kontrol: %d/1' % (pos_ok, neg_ok))

    if not pos_ok or not neg_ok:
        print('K-BE OLCULEMEDI — dedektor kendi kontrolunu gecemedi (sonuc "temiz" DEGIL).')
        return 2

    if hits:
        print('K-BE IHLAL — sablon, yukledigi paylasilan dosyanin adini eziyor (%d):' % len(hits))
        for t, tl, name, u, sl in hits:
            print("  %s:%d  '%s'  <->  %s:%d" % (t, tl, name, u, sl))
        print('  DUZELTME: satir-ici kopyayi SIL (paylasilan dosya kanondur) veya')
        print('            paylasilan adi IIFE icine al / sablondaki adi degistir.')
        return 1

    print('  ✓ hicbir sablon yukledigi paylasilan dosyanin ust duzey adini ezmiyor')
    return 0


if __name__ == '__main__':
    sys.exit(main())
