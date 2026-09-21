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
MIN_OPTIONS = 10
MIN_THS     = 10


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
    for m in TH_SORTABLE_RE.finditer(html):
        blk = m.group(0)
        n_th += 1
        if 'aria-sort' not in blk:
            devs.append(('th', re.sub(r'<[^>]+>', '', blk).strip()[:40], 'aria-sort yok'))
        if not re.search(r'<button\b[^>]*class="[^"]*\bth-sort-btn\b', blk):
            devs.append(('th', re.sub(r'<[^>]+>', '', blk).strip()[:40], 'button.th-sort-btn yok'))
    return devs, n_opt, n_th


def positive_control():
    """Taban ne kadar yuksek olursa olsun, mantigin kendisi sentetik sapmalari
    yakalamali (bkz. K-AU dersi: sifir/taban tek basina kanit degildir)."""
    fixtures = [
        ('<option value="x">Fiyat (Yüksek → Düşük)</option>', 1),                 # sabit yon iddiasi
        ('<th class="th-sortable"><button class="th-sort-btn">A</button></th>', 1),  # aria-sort yok
        ('<th class="th-sortable" aria-sort="none">A</th>', 1),                    # buton yok
        ('<option value="x" data-label="Fiyat" data-desc="Yüksek → Düşük" data-asc="Düşük → Yüksek">Fiyat (Yüksek → Düşük)</option>', 0),
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
