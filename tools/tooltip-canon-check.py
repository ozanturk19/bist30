#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-AT — TOOLTIP MEKANIZMASI KANONU  (pre-deploy kapisi)

Neden var:
  Sitede iki paralel ipucu mekanizmasi yasiyordu.
    (A) KANONIK: [data-tip] + static/js/bp-tooltip.js
        hover + focus + tap(toggle) + Escape + viewport kirpma + aria-describedby
    (B) tarama.css: `thead th[data-tooltip]:hover::after`
        SADECE :hover / :focus-within. Dokunmatikte hic acilmiyordu; odaklanabilir
        cocugu olmayan iki baslikta (Temel Skor / BorsaPusula Skoru) :focus-within
        de hic tetiklenemiyordu -> skor FORMULU yalnizca fareyle erisilebilirdi
        (WCAG 1.4.13). Ustelik white-space:nowrap + max-width yok: 102px'lik
        basligin altinda 502px, en uzununda ~1000px tek satir.
  (B) K-AT'de silindi. Bu kapi geri gelmesini ve kanonik mekanizmanin klavyeye
  kapali kullanimini engeller.

Olctugu uc eksen:
  1) CSS'te `content: attr(data-*)` tasiyan ipucu kurali — YALNIZ beyaz listedeki
     `.ind-help` mekanizmasi serbest (onun tap-toggle + Escape JS'i var).
  2) [data-tip] tasiyan her oge KLAVYEYLE ODAKLANABILIR olmali: dogal odaklanabilir
     etiket (a[href]/button/input/select/textarea/summary), acik `tabindex`, ya da
     odaklanabilir bir cocugu saran <label> (odak icerden gelir, `focusin` kabarir).
     Odaklanamayan bir ogede ipucu = yalniz-fare icerik (WCAG 1.4.13 + 2.1.1).
     <label> istisnasi KOSULLU: sardigi kontrol CSS'te `display:none` ise sekme
     sirasindan tamamen cikar -> istisna dusut. (Gercek bulgu: portfolio.css
     `#importFileInput{display:none}` yuzunden "İçe Aktar" YALNIZCA fareyle
     calisiyordu, WCAG 2.1.1 A.)
  3) [data-tip] kullanan her sablon bp-tooltip.js'i yuklemeli (yoksa ipucu OLU).

Cikis: 0 temiz · 1 sapma · 2 kapsam tabani altinda (dedektor korlesmis).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL  = os.path.join(ROOT, 'templates')
CSS  = os.path.join(ROOT, 'static', 'css')

# 21.09 (K-AU) — BEYAZ LISTE BOSALTILDI. Tek uyesi `.ind-help` idi; "tap-toggle
# + Escape JS'i var, yani yalniz-fare degil" gerekcesiyle serbest birakilmisti.
# O gerekce EKSIKTI: mekanizmanin klavye/dokunma erisimi vardi ama KONUMLANDIRMASI
# sabit yonluydu (bottom:130% + left:50%), viewport cevirmesi yoktu — canli olcumde
# yapiskan baslik altindaki 4/4 ipucunun gorunur yuksekligi %0, 320px'te 4/4'u saga
# tasiyor ve html{overflow-x:clip} yuzunden kirpiliyordu. `.ind-help` kanonik
# [data-tip]'e gocurdu; artik istisna YOK. Yeni istisna eklenmeden once o
# mekanizmanin hem ERISIMI hem KONUMLANDIRMASI olculmeli.
CSS_ALLOW = set()

NATIVE_FOCUSABLE = {'a', 'button', 'input', 'select', 'textarea', 'summary'}

# kapsam tabanlari — dedektor bunlarin altina duserse sessizce korlesmis demektir
# C-29 (25.09): /sektor-harita sektor kartlari + lejant paneli silindi, onlarla
# [data-tip] kullanimi 47'ye indi (dedektor korlesmedi: pozitif kontrol 3/3) -> taban 50 -> 45.
MIN_TIPS      = 45
# 21.09 (K-AU): gercek sayi artik 0 oldugu icin ">=1" tabani kapiyi surekli
# "korlesmis" (cikis 2) yapardi. Sifir bir kapsam yalani OLMASIN diye taban
# yerine POZITIF KONTROL var: css_attr_tooltips()'in mantigi sentetik bir
# kurala uygulanir, bulmazsa dedektor gercekten korlesmistir.
MIN_CSS_RULES = 0


def scan_css_text(rel, src):
    """Tek bir CSS govdesinde `content: attr(data-…)` kurallarini bul.
       Ayri fonksiyon: ayni mantik hem gercek dosyalara hem POZITIF KONTROL
       fikstürüne uygulansin diye (bkz. positive_control)."""
    out = []
    # yorumlari temizle (yorum icindeki ornek kod sahte pozitif uretir)
    body = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    for m in re.finditer(r'([^{}]+)\{([^{}]*content\s*:\s*attr\(\s*(data-[\w-]+)[^{}]*)\}',
                         body, flags=re.S):
        sel = ' '.join(m.group(1).split())
        out.append((rel, sel, m.group(3)))
    return out


def css_attr_tooltips():
    """CSS'te `content: attr(data-…)` tasiyan kurallar -> (dosya, secici, oznitelik)"""
    out = []
    for dirpath, _, files in os.walk(CSS):
        for fn in sorted(files):
            if not fn.endswith('.css'):
                continue
            path = os.path.join(dirpath, fn)
            rel  = os.path.relpath(path, CSS)
            out.extend(scan_css_text(rel, open(path, encoding='utf-8').read()))
    return out


# 21.09 (K-AU) — gercek sayi 0'a indigi icin ">=1 kural bulmali" tabani artik
# kullanilamaz. Yerine POZITIF KONTROL: dedektorun kendi mantigi, bulmasi
# GEREKEN sentetik bir kurala uygulanir. Sifir ancak bu 3/3 gecerse "temiz"
# demektir; gecmezse dedektor gercekten korlesmistir (cikis 2).
POSCTRL = [
    # (fikstur, beklenen oznitelik) — ucu de ayri yazim yolu
    ('.zzz-fake::after{content:attr(data-tooltip);position:absolute}', 'data-tooltip'),
    ('.zzz-b:hover::before {\n  content : attr( data-hint ) ;\n}',    'data-hint'),
    ('/* content:attr(data-yorum) */\n.zzz-c::after{color:red;content:attr(data-x);}', 'data-x'),
]


def positive_control():
    """Dedektorun gordugunu kanitla. -> (gecen, toplam, hata listesi)"""
    errs = []
    for i, (fixture, expect) in enumerate(POSCTRL, 1):
        hits = scan_css_text('POSCTRL-%d' % i, fixture)
        attrs = [h[2] for h in hits]
        if expect not in attrs:
            errs.append('POSCTRL-%d: `%s` bekleniyordu, bulunan: %s' % (i, expect, attrs or 'YOK'))
    return len(POSCTRL) - len(errs), len(POSCTRL), errs


DISPLAY_NONE_RE = None


def css_display_none_selectors():
    """CSS'te `display:none` atayan secicilerin id/class jetonlari."""
    tokens = set()
    for dirpath, _, files in os.walk(CSS):
        for fn in sorted(files):
            if not fn.endswith('.css'):
                continue
            src = open(os.path.join(dirpath, fn), encoding='utf-8').read()
            body = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
            for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', body):
                if not re.search(r'display\s*:\s*none', m.group(2)):
                    continue
                for t in re.findall(r'[#.][\w-]+', m.group(1)):
                    tokens.add(t)
    return tokens


def tag_of(src, idx):
    """data-tip'in bulundugu konumdan geriye yuruyup acan etiketi ve ozniteliklerini cikar."""
    start = src.rfind('<', 0, idx)
    if start < 0:
        return None, '', ''
    end = src.find('>', idx)
    if end < 0:
        return None, '', ''
    frag = src[start:end + 1]
    m = re.match(r'<\s*([a-zA-Z][\w-]*)', frag)
    if not m:
        return None, '', ''
    tag = m.group(1).lower()
    # <label> istisnasi icin ic icerigi de lazim: kapanis etiketine kadar oku
    inner = ''
    close = src.find('</' + tag, end)
    if close > 0 and close - end < 4000:
        inner = src[end:close]
    return tag, frag, inner


def main():
    problems = []
    hidden_tokens = css_display_none_selectors()

    # ── 1) CSS mekanizmasi ────────────────────────────────────────────────
    css_rules = css_attr_tooltips()
    for rel, sel, attr in css_rules:
        key = next((k for k in CSS_ALLOW if k[0] == rel and k[1] in sel), None)
        if key is None:
            problems.append(
                'CSS %s -> `%s` kurali `content: attr(%s)` ile ikinci bir ipucu '
                'mekanizmasi kuruyor. Kanonik yol: [data-tip] + bp-tooltip.js '
                '(hover+focus+tap+Escape+kirpma). Beyaz listede degil.' % (rel, sel, attr))

    # ── 2/3) sablonlar ────────────────────────────────────────────────────
    tips_total = 0
    for fn in sorted(os.listdir(TPL)):
        if not fn.endswith('.html'):
            continue
        src = open(os.path.join(TPL, fn), encoding='utf-8').read()

        # eski oznitelik geri gelmis mi? (K-AU'dan beri ISTISNASIZ)
        for m in re.finditer(r'data-tooltip\s*=', src):
            tag, frag, _ = tag_of(src, m.start())
            problems.append('templates/%s: `data-tooltip` kanonik disi mekanizma '
                            '(istisna YOK, kanonik yol [data-tip]) -> %s' % (fn, frag[:90]))

        hits = list(re.finditer(r'data-tip\s*=', src))
        tips_total += len(hits)
        if hits and 'bp-tooltip.js' not in src:
            problems.append('templates/%s: %d adet [data-tip] var ama bp-tooltip.js '
                            'yuklenmiyor -> ipuclari OLU.' % (fn, len(hits)))

        for m in hits:
            tag, frag, inner = tag_of(src, m.start())
            if tag is None:
                continue
            focusable = (tag in NATIVE_FOCUSABLE) or ('tabindex=' in frag.replace(' ', ''))
            if tag == 'a' and 'href=' not in frag:
                focusable = False
            if tag == 'label' and not focusable:
                # sardigi kontrol odagi ICERDEN saglar — ama CSS onu
                # display:none ile sekme sirasindan atmis olmamali.
                ctl = re.search(r'<\s*(input|select|textarea|button)([^>]*)>', inner)
                if ctl:
                    ids = re.findall(r'id\s*=\s*"([^"]+)"', ctl.group(2))
                    cls = ' '.join(re.findall(r'class\s*=\s*"([^"]+)"', ctl.group(2))).split()
                    toks = ['#' + i for i in ids] + ['.' + c for c in cls]
                    hidden = [t for t in toks if t in hidden_tokens]
                    if hidden:
                        problems.append(
                            'templates/%s: <label data-tip> sardigi kontrolu CSS %s '
                            'ile display:none -> kontrol SEKME SIRASINDA DEGIL, '
                            'islev yalniz-fare (WCAG 2.1.1 A).' % (fn, ', '.join(hidden)))
                    focusable = True
            if not focusable:
                problems.append('templates/%s: <%s data-tip> klavyeyle ODAKLANAMIYOR '
                                '(dogal odaklanabilir degil, tabindex yok) -> ipucu '
                                'yalniz-fare (WCAG 1.4.13). %s' % (fn, tag, frag[:90]))

    pc_ok, pc_tot, pc_errs = positive_control()

    print('tooltip-canon-check (K-AT ipucu mekanizmasi kanonu + K-AU beyaz liste 1->0)')
    print('  kanonik [data-tip] kullanimi: %d · CSS attr() ipucu kurali: %d (beyaz liste: %d) '
          '· pozitif kontrol: %d/%d'
          % (tips_total, len(css_rules), len(CSS_ALLOW), pc_ok, pc_tot))

    if pc_errs:
        print('  !! POZITIF KONTROL DUSTU — dedektor korlesmis, "0 kural" bir KAPSAM YALANI:')
        for e in pc_errs:
            print('      · ' + e)
        return 2

    if tips_total < MIN_TIPS or len(css_rules) < MIN_CSS_RULES:
        print('  !! KAPSAM TABANI ALTINDA (data-tip %d < %d  ya da  css %d < %d) — '
              'dedektor korlesmis olabilir.' % (tips_total, MIN_TIPS, len(css_rules), MIN_CSS_RULES))
        return 2

    if problems:
        print('  ✗ %d sapma:' % len(problems))
        for p in problems:
            print('      · ' + p)
        return 1

    print('  ✓ tek mekanizma (CSS attr() istisnasi YOK), hepsi klavyeye acik')
    return 0


if __name__ == '__main__':
    sys.exit(main())
