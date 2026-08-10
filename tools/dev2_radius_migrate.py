#!/usr/bin/env python3
"""FAZ8 border-radius token migrasyonu — yalniz TAM eslesen tek-deger olceklerini
var(--bp-radius-*) e baglar. Kapsam: templates/*.html (<script> bloklari HARIC) +
static/css/*.css. JS dosyalari (toast.js, page-info-panel.js) elle duzenlendi, script
onlara dokunmuyor. Coklu-deger shorthand (orn '10px 10px 0 0') KASITLI disarida --
terminator sadece ; " ' } olabilir, bosluk degil.
"""
import re, sys, glob

VALUE_TO_TOKEN = {
    '6px': 'var(--bp-radius)',
    '8px': 'var(--bp-radius-md)',
    '10px': 'var(--bp-radius-lg)',
    '12px': 'var(--bp-radius-xl)',
    '3px': 'var(--bp-radius-sm)',
    '2px': 'var(--bp-radius-xs)',
    '999px': 'var(--bp-radius-pill)',
}
# uzunluk azalan sirada dene (999px 12px'ten once denenmeli yoksa yanlis eslesir gibi
# gorunse de \b + deger tam string oldugu icin sorun yok, ama garanti olsun)
VALUES_SORTED = sorted(VALUE_TO_TOKEN.keys(), key=len, reverse=True)
VALUE_ALT = '|'.join(re.escape(v) for v in VALUES_SORTED)
PATTERN = re.compile(r'border-radius\s*:\s*(' + VALUE_ALT + r')(?=[;"\'}])')

SCRIPT_BLOCK = re.compile(r'<script\b[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)

def migrate_text(text, mask_scripts):
    """mask_scripts=True icin script bloklarini gecici placeholder ile koru."""
    if not mask_scripts:
        counts = {}
        def repl(m):
            val = m.group(1)
            counts[val] = counts.get(val, 0) + 1
            return 'border-radius:' + VALUE_TO_TOKEN[val]
        new_text = PATTERN.sub(repl, text)
        return new_text, counts

    placeholders = []
    def stash(m):
        placeholders.append(m.group(0))
        return f'@@SCRIPTBLOCK{len(placeholders)-1}@@'
    masked = SCRIPT_BLOCK.sub(stash, text)

    counts = {}
    def repl(m):
        val = m.group(1)
        counts[val] = counts.get(val, 0) + 1
        return 'border-radius:' + VALUE_TO_TOKEN[val]
    migrated = PATTERN.sub(repl, masked)

    def restore(m):
        idx = int(m.group(1))
        return placeholders[idx]
    final = re.sub(r'@@SCRIPTBLOCK(\d+)@@', restore, migrated)
    return final, counts

def main():
    dry_run = '--apply' not in sys.argv
    targets = sorted(glob.glob('templates/*.html')) + sorted(glob.glob('static/css/*.css'))
    total_counts = {}
    files_changed = 0
    for path in targets:
        with open(path, encoding='utf-8') as f:
            text = f.read()
        mask = path.endswith('.html')
        new_text, counts = migrate_text(text, mask_scripts=mask)
        if counts:
            files_changed += 1
            summary = ', '.join(f'{k}x{v}' for k, v in sorted(counts.items()))
            print(f'{path}: {summary}')
            for k, v in counts.items():
                total_counts[k] = total_counts.get(k, 0) + v
            if not dry_run:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_text)
    print('---')
    print('TOPLAM:', ', '.join(f'{k}x{v}' for k, v in sorted(total_counts.items())),
          '=', sum(total_counts.values()))
    print(f'{files_changed} dosya degisti' + (' (DRY-RUN, yazilmadi)' if dry_run else ' (YAZILDI)'))

if __name__ == '__main__':
    main()
