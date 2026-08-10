#!/usr/bin/env python3
"""FAZ8 makro seridi duraklatma dugmesi migrasyonu — WCAG 2.2.2 (Pause/Stop/Hide) acigini
kapatir: macroScroll 40s infinite animasyonu bugun yalniz `:hover` ile duruyor, dokunmatik
cihazda hicbir kullanici seridi durduramiyor. Bu script 16 sablonun HER BIRINE ayni dugmeyi
+ CSS'i + inline onclick JS'i (kodda zaten var olan onclick=event.stopPropagation() gibi
inline-handler konvansiyonuyla tutarli, ayri bir script.js gerektirmiyor) ekler.

Kapsam: yalniz macroScroll iceren 16 sablon (glob ile degil, sabit liste — surpriz dosya
almasin). Iki bagimsiz anchor:
  1) `<div class="macro-bar">` veya `<div class="macro-bar" id="macroBar">` -> ilk cocuk
     olarak <button> eklenir.
  2) `@keyframes macroScroll ... }` bloğunun hemen ardindan gelen `.macro-item` selektorunden
     once CSS eklenir (16 sablonun 16'sinda da bu bitisiklik elle grep ile dogrulandi).
Her iki anchor da tam 1 kez eslesmezse dosya ATLANIR ve uyari basilir (sessiz atlama yok).
"""
import re, sys

FILES = [
    'templates/ozet.html', 'templates/blog_article.html', 'templates/sektor_harita.html',
    'templates/index.html', 'templates/tarama.html', 'templates/blog.html',
    'templates/gundem.html', 'templates/kategori.html', 'templates/bilanco_takvimi.html',
    'templates/metodoloji.html', 'templates/karsilastir.html', 'templates/portfolio.html',
    'templates/hisse.html', 'templates/gucu_yuksek.html', 'templates/varlik.html',
    'templates/sinyal_performans.html',
]

BAR_RE = re.compile(r'<div class="macro-bar"( id="macroBar")?>')

BUTTON_HTML = (
    '<button type="button" class="macro-pause-btn" id="macroPauseBtn" '
    'aria-pressed="false" aria-label="Haber şeridini duraklat" '
    "onclick=\"(function(b){var bar=b.closest('.macro-bar');"
    "var p=bar.getAttribute('data-paused')==='true';"
    "bar.setAttribute('data-paused',String(!p));"
    "b.setAttribute('aria-pressed',String(!p));"
    "b.textContent=!p?'▶':'⏸';"
    "b.setAttribute('aria-label',!p?'Haber şeridini devam ettir':'Haber şeridini duraklat');"
    '})(this)">⏸</button>'
)

CSS_BLOCK = (
    '  .macro-bar { position: relative; }\n'
    '  .macro-pause-btn { position: absolute; right: 2px; top: 50%; transform: translateY(-50%); '
    'z-index: 3; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; '
    'background: transparent; border: none; color: inherit; opacity: .55; font-size: 12px; line-height: 1; '
    'cursor: pointer; padding: 0; }\n'
    '  .macro-pause-btn:hover, .macro-pause-btn:focus-visible { opacity: 1; }\n'
    '  .macro-bar[data-paused="true"] .macro-track { animation-play-state: paused !important; }\n  '
)

KEYFRAMES_ANCHOR = '@keyframes macroScroll'
ITEM_ANCHOR = '.macro-item'
MAX_GAP = 400  # keyframes blogu her zaman kisa; daha uzunsa bir seyler beklenmedik demektir


def migrate(path, dry_run):
    with open(path, encoding='utf-8') as f:
        text = f.read()

    bar_matches = list(BAR_RE.finditer(text))
    if len(bar_matches) != 1:
        print(f'{path}: ATLANDI — macro-bar acilis etiketi {len(bar_matches)} kez eslesti (1 bekleniyordu)')
        return False
    m = bar_matches[0]
    text2 = text[:m.end()] + BUTTON_HTML + text[m.end():]

    kf_idx = text2.find(KEYFRAMES_ANCHOR)
    if kf_idx == -1:
        print(f'{path}: ATLANDI — @keyframes macroScroll bulunamadi')
        return False
    item_idx = text2.find(ITEM_ANCHOR, kf_idx)
    if item_idx == -1:
        print(f'{path}: ATLANDI — keyframes sonrasi .macro-item bulunamadi')
        return False
    gap = text2[kf_idx:item_idx]
    if len(gap) > MAX_GAP or gap.count('.macro-item') > 0:
        print(f'{path}: ATLANDI — keyframes/.macro-item arasi beklenmedik ({len(gap)} char), elle kontrol gerekiyor')
        return False

    text3 = text2[:item_idx] + CSS_BLOCK + text2[item_idx:]

    print(f'{path}: buton + CSS eklendi ({"DRY-RUN" if dry_run else "YAZILDI"})')
    if not dry_run:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text3)
    return True


def main():
    dry_run = '--apply' not in sys.argv
    changed = 0
    for path in FILES:
        if migrate(path, dry_run):
            changed += 1
    print('---')
    print(f'{changed}/{len(FILES)} dosya' + (' degisecek (DRY-RUN)' if dry_run else ' degisti (YAZILDI)'))
    if changed != len(FILES):
        print('UYARI: beklenen 16, degisen', changed, '— eksik dosyalari yukarida incele')


if __name__ == '__main__':
    main()
