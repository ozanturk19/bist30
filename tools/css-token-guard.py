#!/usr/bin/env python3
"""CSS token guard — T1.7 format-lint v2'nin ilk parcasi.

NEDEN VAR (08.08.2026, DEV-2):
tokens.css'teki bir YORUM, govdesinde kaza eseri bir yorum-kapatma dizisi
(yildiz + egik-cizgi) tasiyordu. Yorum orada kapandi; kalan Turkce aciklama
metni ust duzeyde CSS oldu ve hemen ardindaki ":root {" ile birlesip
gecersiz bir selektor olusturdu. Ayristirici o blogun TAMAMINI atti:
ikinci :root blogunun 10/10 olcek token'i canlida TANIMSIZ kaldi.

Fark edilmedi cunku her yuzeysel olcut YESILDI:
  - dosya HTTP 200 donuyordu
  - boyutu dogruydu
  - grep token adlarini dosyanin icinde buluyordu
Tek kirmizi olcut tarayicidaki getComputedStyle idi.

Ayni hata, hatayi ACIKLAYAN yorumun icine dizeyi birebir kopyalayarak
BIR KEZ DAHA uretildi. Bu yuzden guard var.

OLCUT: yorumlar soyulduktan sonra, blok DISINDA kalan metin yalnizca
selektor/at-kural karakterlerinden olusmali. Turkce dux metin (i, s, g,
u, o, c ya da cumle noktalamasi) orada goruldugu an dosya kiriktir.

Kullanim:  python3 tools/css-token-guard.py static/css/tokens.css [...]
Cikis:     0 = temiz, 1 = kirik (deploy engellenmeli)
"""
import re
import sys
import pathlib

# Selektorlerde ve at-kural basliklarinda gorulebilecek karakterler.
SELEKTOR_IZINLI = re.compile(r'^[\sA-Za-z0-9_.#:\[\]()"\'=,>+~*%/^$|@!-]*$')


def yorumlari_soy(s):
    """CSS yorumlarini soyar. CSS yorumlari IC ICE GECMEZ — /* ilk */ ile kapanir."""
    out, i, depth = [], 0, 0
    while i < len(s):
        if depth == 0 and s[i:i + 2] == '/*':
            depth = 1
            i += 2
            continue
        if depth == 1 and s[i:i + 2] == '*/':
            depth = 0
            i += 2
            continue
        if depth == 0:
            out.append(s[i])
        i += 1
    return ''.join(out), depth


def blok_disi_parcalar(kod):
    """Suslu parantez derinligi 0 olan metin parcalarini dondurur."""
    parcalar, cur, derinlik = [], '', 0
    satir = 1
    baslangic = 1
    for ch in kod:
        if ch == '\n':
            satir += 1
        if ch == '{':
            if derinlik == 0:
                parcalar.append((baslangic, cur))
                cur = ''
            derinlik += 1
        elif ch == '}':
            derinlik -= 1
            if derinlik == 0:
                baslangic = satir
                cur = ''
        elif derinlik == 0:
            cur += ch
    if cur.strip():
        parcalar.append((baslangic, cur))
    return parcalar, derinlik


def kontrol(yol):
    src = pathlib.Path(yol).read_text(encoding='utf-8')
    hatalar = []

    kod, acik = yorumlari_soy(src)
    if acik:
        hatalar.append('kapanmamis yorum blogu (dosya sonunda /* acik kaldi)')

    parcalar, derinlik = blok_disi_parcalar(kod)
    if derinlik != 0:
        hatalar.append('dengesiz suslu parantez (derinlik %d)' % derinlik)

    for satir, metin in parcalar:
        duz = metin.strip()
        if not duz:
            continue
        if not SELEKTOR_IZINLI.match(duz):
            kotu = sorted({c for c in duz if not SELEKTOR_IZINLI.match(c)})
            hatalar.append(
                'satir ~%d: blok disinda selektor olamayacak metin var — '
                'buyuk ihtimalle bir yorum erken kapandi. '
                'gecersiz karakterler: %r  parca: %r'
                % (satir, ''.join(kotu)[:20], duz[:120].replace('\n', ' '))
            )

    toks = re.findall(r'(--[A-Za-z0-9_-]+)\s*:', kod)
    return hatalar, len(toks), sorted(set(toks))


def main(argv):
    if not argv:
        print('kullanim: css-token-guard.py <dosya.css> [...]')
        return 2
    kod_cikis = 0
    for yol in argv:
        try:
            hatalar, n, _ = kontrol(yol)
        except OSError as e:
            print('OKUNAMADI  %s  (%s)' % (yol, e))
            kod_cikis = 1
            continue
        if hatalar:
            kod_cikis = 1
            print('KIRIK  %s  (%d token gorunuyor ama blok dusebilir)' % (yol, n))
            for h in hatalar:
                print('        - %s' % h)
        else:
            print('TEMIZ  %s  (%d token)' % (yol, n))
    return kod_cikis


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
