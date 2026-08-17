#!/usr/bin/env python3
"""T2.5 — deterministic inline <style> -> external CSS extractor.

Mechanical, content-preserving. Leaves any <style id="bp-critical-css"> block
untouched (established convention: 21 templates already mark true critical CSS
this way). Everything else non-critical is moved verbatim (same document order)
into an external CSS file; the FIRST removed block's location gets a
<link rel="stylesheet"> in its place, later blocks in the same file are just
removed (content already carried by the same external file).

Usage:
  extract_inline_css.py <template.html> <css_out_relpath> [--fold file2.html file3.html ...] \
      [--dynamic-line "NEEDLE" --root-selector ":root"] [--no-link]

--fold: additional partial templates whose non-critical <style> blocks get
        folded into the SAME css_out_path, blocks fully removed from that
        partial (no <link> inserted there — caller is responsible for linking
        css_out_path from wherever needed, e.g. a shared _head.html include).
--dynamic-line: a Jinja-bearing CSS declaration line (e.g. "--accent: {{ meta.color }};")
        that cannot be moved to a static file. It is stripped from the block
        going to CSS and re-emitted as a tiny inline <style> immediately after
        the new <link> tag, wrapped in --root-selector (default ':root').
--no-link: don't insert any <link> in template_path (used for pure "fold"
        targets like the mobile-nav partial, where the link is added once,
        by hand, in the shared head include).
"""
import argparse
import hashlib
import os
import re
import sys

STYLE_RE = re.compile(r'<style([^>]*)>(.*?)</style>', re.DOTALL)


def find_noncritical_blocks(html):
    blocks = []
    for m in STYLE_RE.finditer(html):
        attrs = m.group(1)
        if 'bp-critical-css' in attrs:
            continue
        blocks.append((m.start(), m.end(), m.group(2)))
    return blocks


def strip_dynamic_line(body, needle):
    """Remove any line containing `needle` from body; return (clean_body, [raw_lines])."""
    kept, dyn = [], []
    for line in body.split('\n'):
        if needle in line:
            dyn.append(line.strip())
        else:
            kept.append(line)
    return '\n'.join(kept), dyn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('template')
    ap.add_argument('css_out')
    ap.add_argument('--fold', nargs='*', default=[])
    ap.add_argument('--dynamic-line', default=None)
    ap.add_argument('--root-selector', default=':root')
    ap.add_argument('--no-link', action='store_true')
    args = ap.parse_args()

    main_html = open(args.template, encoding='utf-8').read()
    main_blocks = find_noncritical_blocks(main_html)
    if not main_blocks:
        print(f'SKIP {args.template}: no non-critical <style> block found', file=sys.stderr)
        sys.exit(1)

    css_parts = [f'/* ==== extracted from {args.template} (T2.5) ==== */']
    dyn_snippet = None

    for (s, e, body) in main_blocks:
        if args.dynamic_line and args.dynamic_line in body:
            body, dyn_raw = strip_dynamic_line(body, args.dynamic_line)
            if dyn_raw:
                decls = []
                for raw in dyn_raw:
                    raw = raw.rstrip(';').strip()
                    decls.append(raw + ';')
                dyn_snippet = f'<style>{args.root_selector}{{{"".join(decls)}}}</style>'
        css_parts.append(body)

    version = hashlib.sha1('\n'.join(css_parts).encode('utf-8')).hexdigest()[:8]

    out = []
    last = 0
    for i, (s, e, body) in enumerate(main_blocks):
        out.append(main_html[last:s])
        if i == 0 and not args.no_link:
            link = f'<link rel="stylesheet" href="/{args.css_out}?v={version}">'
            if dyn_snippet:
                link += dyn_snippet
            out.append(link)
        last = e
    out.append(main_html[last:])
    new_main_html = ''.join(out)

    fold_results = {}
    for p in args.fold:
        phtml = open(p, encoding='utf-8').read()
        pblocks = find_noncritical_blocks(phtml)
        if not pblocks:
            print(f'WARN --fold {p}: no non-critical <style> block found, left untouched', file=sys.stderr)
            continue
        css_parts.append(f'/* ==== extracted from {p} (T2.5) ==== */')
        pout, plast = [], 0
        for (s, e, body) in pblocks:
            pout.append(phtml[plast:s])
            css_parts.append(body)
            plast = e
        pout.append(phtml[plast:])
        fold_results[p] = ''.join(pout)

    # recompute version+link now that fold content is included (content-hash must reflect final file)
    version = hashlib.sha1('\n'.join(css_parts).encode('utf-8')).hexdigest()[:8]
    if not args.no_link and main_blocks:
        # patch the version in the already-built new_main_html (only one occurrence, ours)
        new_main_html = new_main_html.replace(f'?v={version[:0]}', '')  # no-op guard
    if not args.no_link:
        # rebuild link with final version (simpler: redo the substitution pass)
        out = []
        last = 0
        for i, (s, e, body) in enumerate(main_blocks):
            out.append(main_html[last:s])
            if i == 0:
                link = f'<link rel="stylesheet" href="/{args.css_out}?v={version}">'
                if dyn_snippet:
                    link += dyn_snippet
                out.append(link)
            last = e
        out.append(main_html[last:])
        new_main_html = ''.join(out)

    css_out_content = '\n'.join(css_parts) + '\n'
    os.makedirs(os.path.dirname(args.css_out) or '.', exist_ok=True)
    with open(args.css_out, 'w', encoding='utf-8') as f:
        f.write(css_out_content)
    with open(args.template, 'w', encoding='utf-8') as f:
        f.write(new_main_html)
    for p, content in fold_results.items():
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)

    total_lines = sum(b.count('\n') + 1 for _, _, b in main_blocks)
    print(f'OK {args.template} -> {args.css_out} (v={version}, {total_lines} main-block lines'
          + (f', +{len(args.fold)} folded' if args.fold else '')
          + (', dynamic-line preserved inline' if dyn_snippet else '')
          + ')')


if __name__ == '__main__':
    main()
