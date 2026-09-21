#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/tr-decimal-input-check.py — K-BA: TÜRKÇE ONDALIK GİRDİ KANONU

KUSUR (canlıda uçtan uca ölçüldü, /tarama, 21.09):
  Fiyat filtreleri `type="number"`di. Türkçe konuşan kullanıcı **"12,50"**
  yazınca tarayıcı virgülü SESSİZCE atıyor ve `input.value` **"1250"** oluyor.
  `validity.valid` hâlâ **true**, `validity.badInput` **false** — yani ne
  tarayıcı ne de sayfa hata üretiyor. Sonuç: 216 hisse **5**'e düşüyor ve
  filtre çipi güvenle **"Min 1250 ₺"** yazıyor. 100 kat sapma, sıfır uyarı.

  ⛔ Bu hata DAHA ÖNCE bir kez bulunup düzeltilmişti (portfolio.html "Alış ₺",
  r161-bughunt) ama YALNIZCA orada. /tarama'nın dört fiyat alanı fix'i miras
  almadı. Kapının varlık sebebi tam olarak budur: düzeltilen bir sınıfın
  ÜÇÜNCÜ kopyası sessizce geri gelmesin.

MEKANİK KURAL (tek, istisnasız):
  Bir `<input>` ONDALIK bir miktar kabul ediyorsa `type="number"` OLAMAZ.
  "Ondalık kabul ediyor" iki gözlemlenebilir işaretten biriyle saptanır:
      · `inputmode="decimal"`           (yazar ondalık beklediğini SÖYLÜYOR)
      · `step` tam sayı DEĞİL           (ör. step="0.01" / step="any")
  Doğru biçim: `type="text"` + `inputmode="decimal"`, değer
  `bpParseTrNumber()` (static/bp-format.js) ile ayrıştırılır.

KAPSAM DIŞI DEĞİL, AYRI: tam sayı alanları (`step="1"`, `step="5"`,
  `inputmode="numeric"`) `type="number"` KALABİLİR — ondalık ayracı hiç
  devreye girmez. Bunlar sayılır ve raporlanır ki "kapsam dışı" kovası
  ölçmediğini saklamasın.
  ⛔ Muafiyet ADA göre verilmez (id/sınıf), yalnızca yukarıdaki iki
  GÖZLEMLENEBİLİR işarete göre.

POZİTİF KONTROL (--kill-fix): her şablona geçici olarak bozuk bir alan
  enjekte eder; kapı hepsini yakalamazsa kapı kördür ve BAŞARISIZ olur.

Kullanım: python3 tools/tr-decimal-input-check.py [--kill-fix] [--verbose]
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL  = os.path.join(ROOT, 'templates')

INPUT_RE = re.compile(r'<input\b[^>]*>', re.I)
ATTR_RE  = re.compile(r'([a-zA-Z-]+)\s*=\s*"([^"]*)"')


def attrs_of(tag):
    return {k.lower(): v for k, v in ATTR_RE.findall(tag)}


def is_integer_step(step):
    """step tam sayı mı? 'any' ve ondalıklı değerler tam sayı DEĞİLDİR."""
    s = (step or '').strip().lower()
    if not s:
        return None          # step yok -> bilgi yok
    if s == 'any':
        return False
    try:
        return float(s) == int(float(s))
    except ValueError:
        return None


def scan_text(text, path, findings, integer_fields):
    for tag in INPUT_RE.findall(text):
        a = attrs_of(tag)
        if a.get('type', '').lower() != 'number':
            continue
        step_int = is_integer_step(a.get('step'))
        decimal_signals = []
        if a.get('inputmode', '').lower() == 'decimal':
            decimal_signals.append('inputmode="decimal"')
        if step_int is False:
            decimal_signals.append('step="%s"' % a.get('step'))
        ident = a.get('id') or a.get('name') or a.get('aria-label') or '(adsız)'
        if decimal_signals:
            findings.append({
                'file': path, 'id': ident,
                'why': ' + '.join(decimal_signals),
                'tag': tag[:160],
            })
        else:
            integer_fields.append((path, ident, a.get('step') or '(step yok)'))


def run(kill_fix=False, verbose=False):
    findings, integer_fields = [], []
    files = sorted(f for f in os.listdir(TPL) if f.endswith('.html'))
    injected = 0
    for fn in files:
        path = os.path.join(TPL, fn)
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        if kill_fix and '<input' in text:
            # pozitif kontrol: bilerek bozuk bir alan enjekte et
            text += '\n<input type="number" id="__killfix__" step="0.01" inputmode="decimal">\n'
            injected += 1
        scan_text(text, fn, findings, integer_fields)

    if kill_fix:
        caught = sum(1 for f in findings if f['id'] == '__killfix__')
        print('POZİTİF KONTROL: %d enjekte, %d yakalandı' % (injected, caught))
        if injected == 0 or caught != injected:
            print('KAPI KÖR — enjekte edilen bozuk alanları görmedi.')
            return 1
        print('Kapı enjekte edilenlerin HEPSİNİ gördü.')
        return 0

    print('Tam sayı alanları (kanon gereği type="number" KALIR): %d' % len(integer_fields))
    if verbose:
        for p, i, st in integer_fields:
            print('   · %-22s %-16s step=%s' % (p, i, st))

    if findings:
        print('\nK-BA İHLALİ — ondalık kabul eden alan type="number" (TR virgülü')
        print('sessizce siliniyor, validity.valid hâlâ true):')
        for f in findings:
            print('  ✗ %s  #%s  [%s]' % (f['file'], f['id'], f['why']))
            print('      %s' % f['tag'])
        print('\nDoğrusu: type="text" inputmode="decimal" + bpParseTrNumber()')
        print('K-BA ihlali: %d' % len(findings))
        return 1

    print('K-BA: ondalık kabul eden type="number" alan YOK (0 ihlal).')
    return 0


if __name__ == '__main__':
    sys.exit(run('--kill-fix' in sys.argv, '--verbose' in sys.argv))
