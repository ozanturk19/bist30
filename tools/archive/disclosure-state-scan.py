#!/usr/bin/env python3
# tools/disclosure-state-scan.py — K-AO: AÇILIR KONTROLÜN DURUM BİLDİRİMİ
# WCAG 2.1 · SC 4.1.2 "Name, Role, Value" (A)
#
# SORU: Bir kontrol bir bölgeyi gösterip gizliyorsa (ya da iki durumlu bir
#   açma/kapama düğmesiyse), ekran okuyucu kullanıcısı durumu YALNIZCA
#   aria-expanded / aria-pressed üzerinden bilir. Görünen ok işareti (▾/▴),
#   metin değişimi ve renk makine tarafından okunabilir DURUM DEĞİLDİR.
#
# NEDEN STATİK: canlı "her tıklanabilire bas" yaklaşımı ölçüldü ve
#   GÜVENİLMEZ çıktı — sayfanın kendi JS'i bölümleri innerHTML ile yeniden
#   basıyor, arama katmanı açılınca geri kalan her şey görünmez oluyor;
#   32 adayın 28'i kayboluyor ve araç bunu "temiz" diye raporluyordu.
#   Şablon kaynağı ise kesindir: görünürlük çeviren her işleyici buradadır.
#   (Canlı teyit için: tools/disclosure-state-check.js)
#
# YÖNTEM:
#   1. şablon/JS içinde GÖRÜNÜRLÜK ÇEVİREN fonksiyonları bul
#      (`.style.display=`, `.hidden=`, classList open/show/expanded/active)
#   2. bu fonksiyonları `onclick="fn()"` ile çağıran KONTROLLERİ bul
#   3. kontrolde aria-expanded VEYA aria-pressed var mı bak
#
# ⛔ KAPSAM DIŞI (bulgu değil, ayrı sayılır):
#   · SEKME değiştiriciler → kanonik öznitelik `aria-selected` (role=tab)
#     [[reference_role_tab_durum_ozniteligi_aria_selected]]
#   · MODAL/DIALOG açıcılar → odak tuzağı + aria-haspopup deseni; bir modal
#     tetikleyicisi aria-expanded taşımaz
#   · <details>/<summary> → tarayıcı durumu `open`'dan kendisi duyurur
#   · saf YÜKLEYİCİ/RENDER fonksiyonları (kullanıcı kontrolü yok)
#
# Kullanım: python3 tools/disclosure-state-scan.py [--json dosya]
import re, sys, glob, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIS = re.compile(r"\.style\.display\s*=|\.hidden\s*=\s*(?:true|false)|classList\.(?:toggle|add|remove)\(\s*['\"](?:open|show|expanded|active|acik|is-open)['\"]")
# sekme / modal / yukleyici desenleri — kapsam disi
TAB   = re.compile(r"aria-selected|role=['\"]tab|SwitchTab|switchTab|applyTab|setFilter|filterCat|SetMode", re.I)
MODAL = re.compile(r"bpTrapFocus|aria-modal|role=['\"]dialog|_modalRelease|Modal", re.I)
LOADER= re.compile(r"^(load|render|apply|build|draw|on[A-Z]|_update|_show[A-Z]|save|submit|reset|clear|remove|dismiss|edit|cancel)", )


def fn_bodies(src):
    """Kaba ama yeterli: fonksiyon adi -> govde."""
    out = {}
    for m in re.finditer(r'(?:window\.)?(\w+)\s*=\s*function\s*\([^)]*\)\s*\{|function\s+(\w+)\s*\([^)]*\)\s*\{', src):
        name = m.group(1) or m.group(2)
        i = src.index('{', m.start()); d = 0; j = i
        while j < len(src):
            if src[j] == '{': d += 1
            elif src[j] == '}':
                d -= 1
                if d == 0: break
            j += 1
        out.setdefault(name, []).append((src[i:j], src[:m.start()].count('\n') + 1))
    return out


def main():
    # POZITIF KONTROL: var olan durum ozniteliklerini BELLEKTE sil; K-AO'da
    # duzeltilen kontroller yeniden BULGU olarak firlamali. Firlamiyorsa
    # tarayici o kontrolu hic gormuyordur (kapsam yalani).
    kill = '--kill-fix' in sys.argv
    findings, scoped_out, checked = [], [], 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'templates', '*.html'))):
        src = open(f, encoding='utf-8').read()
        if kill:
            src = re.sub(r'\s*aria-(?:expanded|pressed)="[^"]*"', '', src)
        bodies = fn_bodies(src)
        togglers = {n for n, bs in bodies.items() if any(VIS.search(b) for b, _ in bs)}
        # ⛔ DOLAYLI CEVIRICILER: `toggleTooltips()` kendisi display'e dokunmaz,
        #   `_applyTooltipVisibility()`yi cagirir. Tek katmanlik tarama bu
        #   kontrolu SESSIZCE eliyordu — olculdu, gercek bulguydu.
        #
        # ⛔ AMA SINIRSIZ GECISKENLIK DE OLCULDU VE FELAKET: 2 kat serbest
        #   gecis `sortBy`, `exportCSV`, `shareSignal`, `addPosition` gibi
        #   HER EYLEMI "acilir kontrol" yapti (17 sahte bulgu) — cunku hepsi
        #   eninde sonunda `showToast()` gibi bir yardimciya ulasiyor.
        #   Bir TOAST/DURUM mesajini gostermek bir BOLGEYI ACMAK DEGILDIR.
        #   Gecis, adi gercekten bir bolge gorunurlugunu anlatan yardimcilarla
        #   SINIRLI (tek kat).
        RELAY = re.compile(r'visibility|expand|collapse|detail|panel|section|sheet|drawer|accordion|acilir', re.I)
        NOISE = re.compile(r'toast|status|warning|error|msg|message|spinner|loading|tooltipPos', re.I)
        relay = {n for n in togglers if RELAY.search(n) and not NOISE.search(n)}
        if relay:
            pat = re.compile(r'\b(' + '|'.join(map(re.escape, relay)) + r')\s*\(')
            for n, bs in bodies.items():
                if n in togglers: continue
                if any(pat.search(b) for b, _ in bs):
                    togglers.add(n)
        if not togglers:
            continue
        # bu fonksiyonlari cagiran KONTROLLER
        for m in re.finditer(r'<(button|a|summary|div|span)\b([^>]*?)onclick\s*=\s*"([^"]*)"([^>]*)>', src, re.S):
            tag, pre, handler, post = m.group(1), m.group(2), m.group(3), m.group(4)
            called = re.findall(r'(\w+)\s*\(', handler)
            hit = [c for c in called if c in togglers]
            if not hit:
                continue
            attrs = pre + post
            ln = src[:m.start()].count('\n') + 1
            rel = os.path.relpath(f, ROOT)
            body_txt = ' '.join(b for c in hit for b, _ in bodies.get(c, []))
            checked += 1
            if tag == 'summary':
                scoped_out.append((rel, ln, hit[0], 'summary (tarayici duyurur)')); continue
            if TAB.search(attrs) or TAB.search(hit[0]) or TAB.search(body_txt):
                scoped_out.append((rel, ln, hit[0], 'sekme -> aria-selected')); continue
            if MODAL.search(attrs) or MODAL.search(body_txt):
                scoped_out.append((rel, ln, hit[0], 'modal -> odak tuzagi/haspopup')); continue
            if re.match(r'^(load|render|apply|build|draw|save|submit|reset|clear|remove|dismiss|forget|cancel|edit)', hit[0]):
                scoped_out.append((rel, ln, hit[0], 'yukleyici/eylem, acilir degil')); continue
            # ⛔ ARKA PERDE bir KONTROL degildir: mbn-sheet-backdrop'un gorevi
            #   disariya tiklaninca kapatmaktir; durumu duyuran oge KENDI
            #   dugmesidir (aria-expanded orada VAR ve guncelleniyor).
            if re.search(r'backdrop|overlay|scrim', attrs, re.I):
                scoped_out.append((rel, ln, hit[0], 'arka perde, kontrol degil')); continue
            # form GONDERIMI acilir bolum degildir
            if re.match(r'^(.*[Ss]ubscribe|.*[Ss]ubmit|.*[Ss]end)', hit[0]):
                scoped_out.append((rel, ln, hit[0], 'form gonderimi')); continue
            has_exp = 'aria-expanded' in attrs
            has_prs = 'aria-pressed' in attrs
            if not has_exp and not has_prs:
                findings.append({'file': rel, 'line': ln, 'fn': hit[0], 'tag': tag,
                                 'kind': 'DURUM_YOK',
                                 'snippet': re.sub(r'\s+', ' ', m.group(0))[:120]})
            elif has_exp and f'{hit[0]}' and 'aria-expanded' in attrs:
                # isleyici gercekten guncelliyor mu?
                if 'aria-expanded' not in body_txt and 'setAttribute' not in body_txt:
                    findings.append({'file': rel, 'line': ln, 'fn': hit[0], 'tag': tag,
                                     'kind': 'SABIT_DURUM',
                                     'snippet': re.sub(r'\s+', ' ', m.group(0))[:120]})

    print(f"K-AO statik tarama — {checked} gorunurluk-ceviren kontrol incelendi\n")
    for r, ln, fn, why in scoped_out:
        print(f"  kapsam disi  {r}:{ln}  {fn}()  — {why}")
    print()
    for x in findings:
        print(f"  BULGU [{x['kind']}]  {x['file']}:{x['line']}  {x['fn']}()")
        print(f"        {x['snippet']}")
    print(f"\nTOPLAM bulgu={len(findings)}  kapsam disi={len(scoped_out)}  incelenen={checked}")
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        json.dump({'findings': findings, 'scoped_out': scoped_out, 'checked': checked}, open(out, 'w'), indent=1)
        print(f"JSON -> {out}")
    sys.exit(1 if findings else 0)


if __name__ == '__main__':
    main()
