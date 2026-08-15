#!/usr/bin/env python3
"""FAZ8 z-index token migrasyonu - YALNIZ tokens.css'te (DEV2-042'de) zaten tanimli
7 seviyeye TAM esit degerleri var(--bp-z-*)'e baglar. Off-scale degerler (3, 999, 500,
9998, 400, 998, 997, 9000, 90, 450, 30, 260, 250, 20, 1100, 10001 - 36 occurrence)
KASITLI disarida - bunlarin her biri hangi UI katmanini temsil ettigi siniflandirilmadan
mekanik tasima yigin sirasi (stacking order) regresyonu riski tasir, ayri bir tur ister.

border-radius migrasyonuyla (tools/dev2_radius_migrate.py) AYNI disiplin: terminator
sadece ; " ' } olabilir, bosluk degil; <script> bloklari HTML'de maskelenir.
"""
import re, sys, glob

VALUE_TO_TOKEN = {
    '100': 'var(--bp-z-dropdown)',
    '9999': 'var(--bp-z-toast)',
    '300': 'var(--bp-z-overlay)',
    '200': 'var(--bp-z-sticky)',
    '1000': 'var(--bp-z-modal)',
    '2': 'var(--bp-z-raised)',
}
VALUES_SORTED = sorted(VALUE_TO_TOKEN.keys(), key=len, reverse=True)
VALUE_ALT = '|'.join(re.escape(v) for v in VALUES_SORTED)
PATTERN = re.compile(r'z-index\s*:\s*(' + VALUE_ALT + r')(?=[;"\'}])')

SCRIPT_BLOCK = re.compile(r'<script\b[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)

def migrate_text(text, mask_scripts):
    if not mask_scripts:
        counts = {}
        def repl(m):
            val = m.group(1)
            counts[val] = counts.get(val, 0) + 1
            return 'z-index:' + VALUE_TO_TOKEN[val]
        return PATTERN.sub(repl, text), counts

    placeholders = []
    def stash(m):
        placeholders.append(m.group(0))
        return f'@@SCRIPTBLOCK{len(placeholders)-1}@@'
    masked = SCRIPT_BLOCK.sub(stash, text)

    counts = {}
    def repl(m):
        val = m.group(1)
        counts[val] = counts.get(val, 0) + 1
        return 'z-index:' + VALUE_TO_TOKEN[val]
    migrated = PATTERN.sub(repl, masked)

    def restore(m):
        return placeholders[int(m.group(1))]
    return re.sub(r'@@SCRIPTBLOCK(\d+)@@', restore, migrated), counts

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
