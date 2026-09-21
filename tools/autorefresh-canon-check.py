#!/usr/bin/env python3
"""K-AX kapisi — PERIYODIK YENILEME ODAK KANONU (CPO 21.09.2026)

KANON (baglayici):
  Sayfayi periyodik olarak yenileyen bir `setInterval(handler, >=1000)`, eger o
  handler sayfanin icerigini `innerHTML` ile YENIDEN YAZIYORSA, `bpPreserveFocus`
  uzerinden gecmek ZORUNDADIR.

NEDEN (K-AX, olculdu):
  /portfolio 60 saniyede bir `tbody.innerHTML = ...` ile tum satirlari basdan
  yaziyordu. Satirlarin icinde "✎ duzenle" ve "✕ kaldir" dugmeleri var. Klavye
  kullanicisi bir dugmeye gelip duraksarsa dugme yok ediliyor, odak <body>'ye
  dusuyor: Enter hicbir sey yapmiyor, Tab belgenin EN BASINDAN basliyor -- ve
  bu 60 saniyede bir tekrarliyordu. Canli olcum (tools/autorefresh-focus-check.js):
  5 sayfa / 6 zamanlayici / 529 oge risk altinda; bilanco takvimi 190 oge,
  sektor haritasi 164 oge (2 DAKIKADA bir). WCAG 2.2.2 (A) + 2.4.3 (A).

  Ekranda gorsel fark yok, konsolda hata yok, fare kullanicisi fark etmiyor --
  bu yuzden 20 tur denetimden gecti. Statik kapi olmadan tekrar gelir.

⛔ GECISKENLIK DERINLIGI = 1, BILEREK:
  Handler'in KENDISI + ayni sablonda DOGRUDAN cagirdigi fonksiyonlar taranir.
  (`fetchLive` innerHTML yazmaz, cagirdigi `render()` yazar -- tek kat tarama
  bunu KACIRIRDI.) Serbest derinlik ise ters yone patlar: gecmis bir turda
  sinirsiz gecisenlik 17 sahte bulgu uretmisti. Derinlik 1'in DOGRU esik
  oldugu, kapinin ciktisi canli olcumle karsilastirilarak dogrulandi:
  ikisi de ayni 5 sablon / 6 zamanlayiciyi isaret ediyor.

⛔ MUAFIYET YOK -- PAYLASILAN HANDLER AYRICA OLCULUR:
  Sablonda tanimlanmayan handler (ornegin `window.bpLoadMacroBar`, 17 sablonda
  180 sn) sessizce kapsam disi BIRAKILMAZ. Onun yerine kaynagi dogrudan
  sinanir: makro serit yalnizca <span> uretiyorsa odaklanabilir oge yok
  edemez, dolayisiyla sarmalanmasi gerekmez. Serit bir gun <a>/<button>
  uretmeye baslarsa bu kapi DUSER. ("Kapinin bilerek kapsam disi maddesi,
  kapinin en buyuk riskidir" -- K-AW dersi.)

TABAN: SIFIR.
Kullanim: python3 tools/autorefresh-canon-check.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, 'templates')
SEARCH_JS = os.path.join(ROOT, 'static', 'bp-search.js')

# setInterval(<ad>, <gecikme>) -- ilk argumani CIPLAK BIR AD olan cagrilar.
# (Satir ici arrow/function ifadeleri zaten sarmalanamaz bir handler degildir;
#  onlari asagida ayrica sayiyoruz ki sessizce dusmesinler.)
RE_INTERVAL_NAMED = re.compile(r'setInterval\(\s*([A-Za-z_$][\w$.]*)\s*,\s*([^,)]+)\)')
RE_INTERVAL_ANY = re.compile(r'setInterval\(')
RE_FUNCDEF = re.compile(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(')


def strip_comments(src):
    """JS yorumlarini bosluga cevirir (uzunluk korunur, satir numaralari kaymaz).

    ⛔ NEDEN ZORUNLU: ilk yazimda kapi sektor_harita.html'de bir SAPMA bildirdi;
    kaynak satir su YORUMDU:
        /* retry-zinciri (setTimeout) ile setInterval(load,120000) cakismasin */
    Yani kapi, kodun degil ANLATIMIN icinde arama yapiyordu -- klasik sahte
    pozitif. Yorumlari soymak ayrica suslu-parantez dengelemesini de saglamlastirir
    (yorum icindeki tek basina bir { veya } govde cikarimini kaydirirdi).

    `//` icin protokol korumasi var: "https://..." bir yorum degildir.
    """
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
        elif c == '/' and i + 1 < n and src[i + 1] == '/' and not (i and src[i - 1] == ':'):
            j = src.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        else:
            i += 1
    return ''.join(out)


def delay_ms(expr):
    """'60000' / '5 * 60 * 1000' / '1800000' -> int ms; cozulemezse None."""
    expr = expr.strip()
    if not re.fullmatch(r'[\d\s*+]+', expr):
        return None
    try:
        return int(eval(expr, {'__builtins__': {}}, {}))  # yalniz rakam/*/+ iceren ifade
    except Exception:
        return None


def function_bodies(src):
    """Sablondaki her ust duzey `function ad(` govdesini kaba suslu-parantez
    dengelemesiyle cikarir. Jinja/HTML gurultusu icinde tam bir JS ayristiricisi
    gerekmiyor: yalniz `.innerHTML` ve cagri adlari araniyor."""
    out = {}
    for m in RE_FUNCDEF.finditer(src):
        name = m.group(1)
        i = src.find('{', m.end() - 1)
        if i < 0:
            continue
        depth, j, n = 0, i, len(src)
        while j < n:
            c = src[j]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.setdefault(name, src[i:j + 1])
    return out


def alias_defs(src):
    """`const AD = <ifade>;` seklindeki handler takma adlarini cikarir.

    ⛔ BU FONKSIYON BIR POZITIF KONTROL BASARISIZLIGININ URUNU: ilk yazimda
    kapi, sablonda `function AD(` olarak TANIMLANMAYAN her handler'i sessizce
    "paylasilan handler" kovasina atiyordu. Sarmalamayi sokup kapiyi kostugumda
    kapi yine PASS dedi -- cunku `_pfLiveTick` bir ok-fonksiyonuydu ve o kovaya
    dusuyordu. Yani kapinin en kalabalik kovasi, olcmedigi seyleri saklayan bir
    delikti. Artik takma adlar cozuluyor ve cozulemeyen handler SESSIZCE
    GECMIYOR, bulgu olarak bildiriliyor.
    """
    out = {}
    for m in re.finditer(r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]+)', src):
        out.setdefault(m.group(1), m.group(2))
    return out


def writes_innerhtml(name, bodies, seen=None, depth=0):
    """Handler'in kendisi (derinlik 0) veya DOGRUDAN cagirdigi bir fonksiyon
    (derinlik 1) innerHTML yaziyor mu?"""
    if depth > 1 or name not in bodies:
        return False
    body = bodies[name]
    if '.innerHTML' in body:
        return True
    if depth == 1:
        return False
    for callee in set(re.findall(r'\b([A-Za-z_$][\w$]*)\s*\(', body)):
        if callee != name and callee in bodies:
            if writes_innerhtml(callee, bodies, depth=depth + 1):
                return True
    return False


def check_shared_macro():
    """Paylasilan makro serit yenileyicisi odaklanabilir oge uretiyor mu?
    Uretmiyorsa sarmalanmasi gerekmez; uretmeye baslarsa bu kapi duser."""
    src = strip_comments(open(SEARCH_JS, encoding='utf-8').read())
    i = src.find('window.bpLoadMacroBar')
    if i < 0:
        return ['bp-search.js icinde bpLoadMacroBar bulunamadi (kapi kor kaldi)']
    j = src.find('window.bpStartMacroTicker', i)
    body = src[i:j if j > i else len(src)]
    # Serit ic HTML'i: yalniz <span> beklenir.
    bad = re.findall(r"<(a|button|input|select|textarea)\b", body) + \
          re.findall(r"tabindex\s*[=:]", body)
    if bad:
        return ['makro serit artik odaklanabilir oge uretiyor (%s) — '
                'bpLoadMacroBar bpPreserveFocus ile sarmalanmali' % ', '.join(sorted(set(bad)))]
    return []


def main():
    findings = []
    measured = {'timers': 0, 'wrapped': 0, 'no_write': 0, 'shared': 0, 'inline': 0}

    for fn in sorted(os.listdir(TPL)):
        if not fn.endswith('.html'):
            continue
        path = os.path.join(TPL, fn)
        src = strip_comments(open(path, encoding='utf-8').read())
        if 'setInterval(' not in src:
            continue
        bodies = function_bodies(src)
        aliases = alias_defs(src)

        named = RE_INTERVAL_NAMED.findall(src)
        measured['inline'] += len(RE_INTERVAL_ANY.findall(src)) - len(named)

        for name, dexpr in named:
            ms = delay_ms(dexpr)
            if ms is None or ms < 1000:
                continue          # <1sn = animasyon/sayac, kapsam disi
            measured['timers'] += 1
            base = name.split('.')[-1]

            # Dogrudan sarmalanmis.
            if 'bpPreserveFocus' in name:
                measured['wrapped'] += 1
                continue

            # Takma ad (`const _pfLiveTick = () => ...`) ise ONU coz.
            target = base
            if base not in bodies and base in aliases:
                expr = aliases[base]
                if 'bpPreserveFocus' in expr:
                    measured['wrapped'] += 1
                    continue
                # Sarmalanmamis takma ad: ardindaki gercek handler'i bul.
                # Takma adin govdesinde gecen HER tanimli ad aday: `(... ? w(fetchLive)
                # : fetchLive)()` yaziminda `fetchLive` ardindan '(' GELMEZ, bu
                # yuzden "ad + parantez" desenlemesi onu kaciriyordu.
                inner = [c for c in re.findall(r'\b([A-Za-z_$][\w$]*)\b', expr) if c in bodies]
                if not inner:
                    findings.append(
                        '%s: setInterval(%s, %d ms) — takma ad COZULEMEDI (%s); '
                        'sarmalanmis mi bilinmiyor' % (fn, name, ms, expr.strip()[:60]))
                    continue
                target = inner[0]

            if target not in bodies:
                # Paylasilan handler. SESSIZCE gecmez: yalnizca ayrica olculen
                # bpLoadMacroBar kabul edilir, digeri bulgudur.
                if base == 'bpLoadMacroBar':
                    measured['shared'] += 1
                else:
                    findings.append(
                        '%s: setInterval(%s, %d ms) — handler bu sablonda tanimli '
                        'DEGIL ve olculen paylasilan handler listesinde de yok; '
                        'kapi bunu dogrulayamiyor' % (fn, name, ms))
                continue

            if writes_innerhtml(target, bodies):
                findings.append(
                    '%s: setInterval(%s, %d ms) — handler (%s) icerigi innerHTML '
                    'ile yeniden yaziyor ama bpPreserveFocus ile SARMALANMAMIS '
                    '(odaktaki oge yok edilir, odak <body>ye duser)' % (fn, name, ms, target))
            else:
                measured['no_write'] += 1

    findings += check_shared_macro()

    print('OLCULDU: periyodik-zamanlayici=%d  sarmalanmis=%d  icerik-yazmayan=%d  '
          'paylasilan-handler=%d  satir-ici-handler=%d'
          % (measured['timers'], measured['wrapped'], measured['no_write'],
             measured['shared'], measured['inline']))
    if findings:
        print('\nK-AX SAPMA (%d):' % len(findings))
        for f in findings:
            print('  X ' + f)
        return 1
    print('K-AX PASS — sarmalanmamis icerik yenileyici yok.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
