#!/usr/bin/env python3
# tools/node-syntax-check.py
# DEV2-T-MOBOVF-1 / CPO-DEV2-011 onerisi — T7.4'te (8a00386) yasanan sinif hata
# (hisse.html'de tek-tirnak template-literal JS string'i erken kapatti, TUM
# inline <script> bloklarini kirdi - SyntaxError; ama Jinja parse / python
# compile / format-lint / CSS token guard / style-guard / lint_scope 7
# katinin HICBIRI bunu yakalamadi, cunku hepsi Jinja/Python katmanina bakiyor,
# saf JS sozdizimine degil). Deploy-sonrasi canli konsolda yakalanip
# duzeltilmisti (8a00386) - bu script AYNI SINIF hatayi deploy-ONCESI
# yakalamak icin var.
#
# Yontem: her templates/*.html icindeki src= OLMAYAN, application/ld+json
# OLMAYAN <script> bloklarini cikarir, Jinja'yi (statement/ifade sinirlarinda
# temiz kesildigi dogrulanmis - {{ }} -> '0' placeholder, {% %} -> silinir)
# soyar, `node --check` ile sozdizimini dogrular. Jinja soyma yontemi TUM
# mevcut sablonlarda 0 yanlis-pozitif verecek sekilde test edilmistir.
#
# DEV2-340 (23.08, r105 hotfix sonrasi): kapsam static/**/*.js dosyalarini
# KAPSAMIYORDU (yalnizca sablon-ici inline <script>) — bp-vocab.js'e yapilan
# bozuk bir ekleme (cat >> shell tirnak-kacis hatasi) bu bosluktan gecip
# canliya SyntaxError olarak deploy oldu (~7dk kisa prod olayi, dc287d4).
# Jinja soyma gerekmiyor (bu dosyalar duz JS), dogrudan `node --check <path>`.
import re
import subprocess
import sys
import glob

SCRIPT_RE = re.compile(
    r'<script(?![^>]*\bsrc=)(?![^>]*type=["\']application/(?:ld\+json|json)["\'])[^>]*>(.*?)</script>',
    re.S | re.I,
)
JINJA_VAR_RE = re.compile(r'\{\{.*?\}\}', re.S)
JINJA_TAG_RE = re.compile(r'\{%.*?%\}', re.S)


def strip_jinja(body):
    body = JINJA_VAR_RE.sub('0', body)
    body = JINJA_TAG_RE.sub('', body)
    return body


def check_file(path):
    content = open(path, encoding='utf-8').read()
    errors = []
    for i, m in enumerate(SCRIPT_RE.finditer(content)):
        body = m.group(1)
        if not body.strip():
            continue
        js = strip_jinja(body)
        proc = subprocess.run(
            ['node', '--check'],
            input=js, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            line_no = content[:m.start()].count('\n') + 1
            errors.append((line_no, i, proc.stderr.strip().splitlines()[0] if proc.stderr else 'bilinmeyen hata'))
    return errors


def check_js_file(path):
    proc = subprocess.run(
        ['node', '--check', path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return proc.stderr.strip().splitlines()[0] if proc.stderr else 'bilinmeyen hata'
    return None


def main():
    files = sorted(glob.glob('templates/*.html'))
    fail = 0
    for f in files:
        errs = check_file(f)
        if errs:
            fail += 1
            for line_no, idx, msg in errs:
                print(f'  ✗ {f}:~{line_no} (script #{idx}) — {msg}')

    js_files = sorted(glob.glob('static/**/*.js', recursive=True))
    js_fail = 0
    for jf in js_files:
        err = check_js_file(jf)
        if err:
            js_fail += 1
            print(f'  ✗ {jf} — {err}')

    if fail == 0 and js_fail == 0:
        print(f'  ✓ node-syntax-check PASS ({len(files)} sablon + {len(js_files)} static JS dosyasi tarandi)')
        return 0
    else:
        print(f'  ✗ node-syntax-check FAIL — {fail} sablonda + {js_fail} static JS dosyasinda sozdizimi hatasi')
        return 1


if __name__ == '__main__':
    sys.exit(main())
