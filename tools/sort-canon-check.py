#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-AV — SIRALAMA KONTROLU DURUM KANONU  (pre-deploy kapisi)

Neden var (21.09 canli olcum, /tarama):
  (1) YON YALANI. Teknik sekmesinin acilir menusunde option metinleri yonu
      IDDIA ediyordu ("Trend Gucu / ADX (Guclu -> Zayif)") ama yonu sutun
      basligi da degistirebiliyordu (sortBy toggle). Ikinci tiklamadan sonra
      canli olcum: aria-sort="ascending", liste Zayif->Guclu, URL sort_dir=asc
      -- ekrandaki TEK metinsel siralama ifadesi hala "Guclu -> Zayif" diyordu.
  (2) ISARETSIZ SIRALI SUTUN. Temel sekmesinde siralama yalniz acilir menuyle
      yapiliyordu; tablonun 10/10 basliginda aria-sort YOKTU ve sirali sutun
      hicbir sekilde isaretlenmiyordu (canli olcum: sort=karlilik iken
      thAria = 10x null). Ayni sayfada Teknik sekmesi basliga tiklatip ok +
      aria-sort gosteriyordu -- ayni is, iki farkli etkilesim dili.
      (Backend /api/tarama/temel `sort_dir`i zaten destekliyordu, frontend
      sabit 'desc' yolluyordu -- yetenek kullanilmiyordu.)

Kanon:
  A) Yon ibaresi tasiyan option METNI sabit yazilamaz; option `data-label` +
     `data-desc` + `data-asc` tasir ve gorunen metin calisma aninda gercek
     yonden turer (_syncSortSelLabel / _syncSortSelLabelTemel).
  B) Siralanabilir baslik `th.th-sortable` + `aria-sort` + icinde
     `button.th-sort-btn` kalibini izler (klavye + durum bildirimi).
  C) GRUPLU SIRALAMA BEYANI (K-DF, 22.09). Bir siralama anahtari backend'de
     once YON BUCKET'ina (AL=0 / BEKLE=1 / SAT=2, CPO-1581) sokuluyorsa,
     sutun bastan sona monoton DEGILDIR. Canli olcum 22.09: menu "Yuksek ->
     Dusuk" derken sutun 72,62,61,57,49,44,43 -> 137 satir "—" -> 71,70,68...
     gidiyordu, yani tablonun EN YUKSEK skoru (71) 145. siradaydi. Boyle bir
     anahtar icin (1) option'un data-desc/data-asc metni gruplamayi SOYLEMELI
     ve (2) istemci o sutuna `aria-sort="other"` yazmali (WAI-ARIA: "asc/desc
     disinda bir algoritmaya gore sirali"). `descending` demek ekran okuyucuya
     olmayan bir duzen vaat etmektir.

Cikis: 0 temiz · 1 sapma · 2 kapsam tabani altinda (dedektor korlesmis).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL  = os.path.join(ROOT, 'templates')

# yon iddiasi iceren parantezli ibare: "(Yuksek -> Dusuk)", "(Guclu -> Zayif)", "(Yeni -> Eski)"
DIR_CLAIM = re.compile(r'\([^()]*(?:→|->)[^()]*\)')
OPTION_RE = re.compile(r'<option\b[^>]*>.*?</option>', re.S)
TH_SORTABLE_RE = re.compile(r'<th\b[^>]*class="[^"]*\bth-sortable\b[^"]*"[^>]*>.*?</th>', re.S)

# kapsam tabanlari — dedektor bunlarin altina duserse sessizce korlesmis demektir
# C-34 (24.09): tabanlarin tamami eski /tarama'nin iki sekmesinden geliyordu (12 yonlu option,
# 12 th-sortable). v2'de siralama basliklari static/js/bp-tarama.js thHTML()'de uretilir
# (siralanan sutunda aria-sort + ok; yon iddiali <option> yok). Sablonlarda olculecek yuzey kalmadi.
MIN_OPTIONS = 0
MIN_THS     = 0

# C) yon bucket'li siralama anahtarlari — app.py `_tarama_sort_key` ile ayni
# kume. Backend bir anahtari daha bucket'larsa buraya EKLENMELI (yoksa kapi
# o anahtar icin kor kalir; envanter bayatligi da bir kusurdur).
BUCKETED_SORTS = ('signal_strength',)
# gruplamayi soyleyen ibare (etiket metninde aranir)
GROUP_CLAIM = re.compile(r'(?:once|önce)', re.I)


def scan_text(html):
    """(yon iddiasi tasiyan option'lar, th-sortable bloklari) -> sapma listesi."""
    devs = []
    n_opt = 0
    n_th  = 0
    for m in OPTION_RE.finditer(html):
        blk = m.group(0)
        # option'un GORUNEN metni (etiketler arasi)
        inner = re.sub(r'<[^>]+>', '', blk)
        if not DIR_CLAIM.search(inner):
            continue
        n_opt += 1
        missing = [a for a in ('data-label', 'data-desc', 'data-asc') if a not in blk]
        if missing:
            devs.append(('option', inner.strip()[:60], 'eksik: ' + ', '.join(missing)))
        # C) gruplu anahtarin etiketi gruplamayi soylemeli
        mval = re.search(r'value="([^"]+)"', blk)
        if mval and mval.group(1) in BUCKETED_SORTS:
            for attr in ('data-desc', 'data-asc'):
                mattr = re.search(attr + r'="([^"]*)"', blk)
                if not mattr or not GROUP_CLAIM.search(mattr.group(1)):
                    devs.append(('option', inner.strip()[:60],
                                 'yon bucket\'li anahtar (%s) ama %s gruplamayi '
                                 'soylemiyor -- sutun monoton degil'
                                 % (mval.group(1), attr)))
    for m in TH_SORTABLE_RE.finditer(html):
        blk = m.group(0)
        n_th += 1
        if 'aria-sort' not in blk:
            devs.append(('th', re.sub(r'<[^>]+>', '', blk).strip()[:40], 'aria-sort yok'))
        if not re.search(r'<button\b[^>]*class="[^"]*\bth-sort-btn\b', blk):
            devs.append(('th', re.sub(r'<[^>]+>', '', blk).strip()[:40], 'button.th-sort-btn yok'))
    return devs, n_opt, n_th


def scan_aria_other(html):
    """C) gruplu anahtar icin `aria-sort` 'other' dalina sahip mi.

    Kapi hatanin YAZIMINI degil kendisini arar: yalnizca "other" kelimesinin
    dosyada gecmesi yetmez, ayni ifadede bucket'li anahtarin adi da gecmeli.
    """
    if not any(("'%s'" % k) in html or ('"%s"' % k) in html for k in BUCKETED_SORTS):
        return []
    if "aria-sort" not in html:
        return []
    for m in re.finditer(r"setAttribute\(\s*'aria-sort'\s*,(.{0,240})", html, re.S):
        expr = m.group(1)
        if "'other'" in expr and any(k in expr for k in BUCKETED_SORTS):
            return []
    return [('js', 'aria-sort', "yon bucket'li anahtar var ama aria-sort hicbir "
             "yerde 'other' dalina girmiyor -- tabloya olmayan bir duzen atfediliyor")]


def positive_control():
    """Taban ne kadar yuksek olursa olsun, mantigin kendisi sentetik sapmalari
    yakalamali (bkz. K-AU dersi: sifir/taban tek basina kanit degildir)."""
    fixtures = [
        ('<option value="x">Fiyat (Yüksek → Düşük)</option>', 1),                 # sabit yon iddiasi
        ('<th class="th-sortable"><button class="th-sort-btn">A</button></th>', 1),  # aria-sort yok
        ('<th class="th-sortable" aria-sort="none">A</th>', 1),                    # buton yok
        ('<option value="x" data-label="Fiyat" data-desc="Yüksek → Düşük" data-asc="Düşük → Yüksek">Fiyat (Yüksek → Düşük)</option>', 0),
        # C) bucket'li anahtar, gruplamayi soylemeyen etiket
        ('<option value="signal_strength" data-label="Skor" data-desc="Yüksek → Düşük" '
         'data-asc="Düşük → Yüksek">Skor (Yüksek → Düşük)</option>', 1),
        # C) bucket'li anahtar, gruplamayi soyleyen etiket
        ('<option value="signal_strength" data-label="Skor" data-desc="Güçlü Trend önce · Yüksek → Düşük" '
         'data-asc="Güçlü Trend önce · Düşük → Yüksek">Skor (Güçlü Trend önce · Yüksek → Düşük)</option>', 0),
    ]
    hits = 0
    for html, expected in fixtures:
        devs, _, _ = scan_text(html)
        if len(devs) >= 1 if expected else len(devs) == 0:
            hits += 1
    return hits, len(fixtures)


def main():
    devs = []
    tot_opt = tot_th = 0
    for fn in sorted(os.listdir(TPL)):
        if not fn.endswith('.html'):
            continue
        with open(os.path.join(TPL, fn), encoding='utf-8') as f:
            html = f.read()
        d, n_o, n_t = scan_text(html)
        d += scan_aria_other(html)
        tot_opt += n_o
        tot_th  += n_t
        devs += [(fn,) + x for x in d]

    pc_hit, pc_tot = positive_control()
    print("sort-canon-check (K-AV siralama kontrolu durum kanonu)")
    print("  yon ibaresi tasiyan option: %d · siralanabilir baslik: %d · pozitif kontrol: %d/%d"
          % (tot_opt, tot_th, pc_hit, pc_tot))

    if pc_hit != pc_tot:
        print("  ✗ POZITIF KONTROL DUSTU — dedektor korlesmis, sayilar guvenilmez")
        return 2
    if tot_opt < MIN_OPTIONS or tot_th < MIN_THS:
        print("  ✗ kapsam tabani altinda (option %d/%d, baslik %d/%d) — dedektor korlesmis"
              % (tot_opt, MIN_OPTIONS, tot_th, MIN_THS))
        return 2
    if devs:
        print("  ✗ %d sapma:" % len(devs))
        for fn, kind, label, why in devs:
            print("      · %-24s %-6s %-42s %s" % (fn, kind, label, why))
        return 1
    print("  ✓ her yon ibaresi gercek yonden turuyor, her siralanabilir baslik durumunu bildiriyor")
    return 0


if __name__ == '__main__':
    sys.exit(main())
