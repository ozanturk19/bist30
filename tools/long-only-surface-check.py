#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K-DE (22.09.2026) — "LONG-ONLY" KURALI HER KANALDA UYGULANIYOR MU?

Urunun kendi metodoloji sayfasi kurali kendi kelimeleriyle yaziyor:

    «BorsaPusula long-only bir urundur: "ideal giris" ancak yonu yukari
     gosteren bir sinyalin yaninda bir sey vaat eder.»
    «Trend Bozuldu sinyallerinde hedef/stop yapisi ve R/R gosterilmez —
     BIST'te bireysel yatirimci genellikle aciga satamaz.»

Kural /hisse'de (CPO-DEV2-052 #1, Ozan karari) ve /karsilastir'da
(_naForSat) uygulaniyordu. CANLI OLCUM 22.09 — /tarama ve /gundem kurali
HIC gormemisti:

  * borsapusula.com/tarama, Sinyal filtresi "Trend Bozuldu": 72 satirin
    **35'i** "Ideal"/"Iyi" giris kalitesi rozetini tasiyordu ve rozetin
    rengi `rgb(0, 226, 144)` = `--bp-al`, yani urunun ALIM yesili.
    Mobil kartlarda da 35. (Olcum: canli DOM, getComputedStyle.)
  * Ayni hissenin kendi sayfasi ayni anda soyle diyordu:
    «Trend asagi yonlu — somut giris/hedef seviyesi bu sinyal tipinde
     gosterilmez.» Tek urun, ayni soru ("su an alsam olur mu?"), iki cevap.
  * CSV disa aktarimi da ekranin dedigini degil ham alani yaziyordu.
  * /gundem kart makrosu SAT kartinda "Kalite: Ideal" + "R/R 1:7,4"
    basabiliyordu (yeni SAT sinyali olan gunlerde; 22.09 evreninde SAT
    hisselerin 51'inde rr_signal > 0, en yuksegi 7,43).

139. dersin ikizi: KURALIN KENDI KELIMELERIYLE YAZILI OLMASI, UYGULANDIGI
ANLAMINA GELMEZ — kac kanal var, kaci uyguluyor diye SAY.

OLCUT (taban SIFIR):

  R1  ENVANTER TAM — yon kapisina tabi alanlari (entry_quality /
      optimal_entry / rr_signal / tp1 / tp2) okuyan her sablon/JS dosyasi
      tools/long_only_surfaces.json'da BILDIRILMIS olmali.
  R2  ENVANTER TAZE — bildirilen dosya o alani artik hic okumuyorsa girdi
      BAYAT demektir (kapi korlesir), FAIL.
  R3  ALAN KUMESI TAM — bildirilen dosyada bildirilmemis yeni bir gated
      alan belirirse FAIL (kanal biliniyordu, yeni vaat sessizce eklendi).
  R4  HER LEHCE AYRI KAPILANIR — dosya hem SSR (Jinja) hem istemci (JS)
      render ediyorsa, kapi IKISINDE DE bulunmali. Urunde uc kez "JS'i
      duzeltip SSR'i unutma" oldu (ders 36/136).
  R5  EKRANA BASAN HER OKUMA BIR KAPININ ALTINDA — yayin yapan her okuma
      icin yon kapisi ya AYNI IFADEDE ya da OKUMAYI CEVRELEYEN BLOK'ta
      olmali: eqApplies(...) / signal === 'AL' / signal === 'SAT' /
      _naForSat(...). KOMSU satirdaki bir yon kontrolu kapi SAYILMAZ --
      kusurun kendisi tam da buydu: /gundem kartinda `const isAl =
      s.signal === 'AL'` satiri rozeti boyuyordu, "Kalite" hucresini
      degil; komsuluk olcen bir kapi bu turu ORTERDI (140. ders).
      Yorumlar soyulur (137. ders): "SAT'ta gosterilmez" diye yazmak kapi
      degildir. Yerel degiskene alinan alan TAKMA AD olarak izlenir.
  R6  MUAFIYET GEREKCELIDIR — status "exempt" ise `reason` bos olamaz.

Kullanim:
  python3 tools/long-only-surface-check.py              # calisan agac
  python3 tools/long-only-surface-check.py --ref SHA    # o commit'in agaci
  python3 tools/long-only-surface-check.py --self-test  # sahte-pozitif/negatif
"""
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

INVENTORY = os.path.join('tools', 'long_only_surfaces.json')
SCAN = (('templates', ('.html',)), ('static', ('.js',)))
WINDOW = 45           # R5 blok penceresi (satir)

# Kapi yazimlari — bosluklar normalize edildikten SONRA aranir.
GUARD_JS = (
    "eqApplies(",
    "signal==='AL'", "signal=='AL'",
    "signal==='SAT'", "signal=='SAT'",
    "_naForSat(",
)
GUARD_JINJA = (
    "signal=='AL'", "signal=='SAT'",
    "signal!='SAT'",
)


def _blank(t):
    return ''.join('\n' if ch == '\n' else ' ' for ch in t)


def strip_comments(s):
    """Yorumlari SIL (137. ders: kapi kendi belgelendirmesiyle korlesmesin)."""
    s = re.sub(r'/\*.*?\*/', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'\{#.*?#\}', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: _blank(m.group(0)), s, flags=re.S)
    s = re.sub(r"(?<![:'\"\\])//[^\n]*", lambda m: _blank(m.group(0)), s)
    return s


def _norm(s):
    return re.sub(r'\s+', '', s)


def field_re(fields):
    """Yalniz ALAN OKUMASI sayilir: `x.alan` ya da tirnakli `'alan'` (case/key).

    Ciplak yerel degisken (`const tp1 = signalData.tp1; ... fmt(tp1)`) alan
    okumasi DEGILDIR — kaynak okuma zaten kapinin altinda yakalanir, ikinci
    kez saymak sahte-pozitif uretir (K-BX: mutlak yazim esigi esik degildir).
    """
    alt = '|'.join(re.escape(f) for f in fields)
    return re.compile(r"(?:\.|['\"])(" + alt + r")\b")


# Kolon TANIMI bir render degildir: `{ key: 'tp1', label: 'Hedef 1' }` satiri
# alani ADLANDIRIR, degerini basmaz -- basan yer switch/case'tir ve kapi
# ORADA aranir. (Tanim satirini kapi saymak, kapiyi kendi envanterine
# karsi korlestirirdi.)
DECL_LINE = re.compile(r"\bkey\s*:\s*['\"]")


def dialect_of(line):
    """Satirin hangi lehcede render ettigi — Jinja ifadesi mi, JS mi."""
    return 'jinja' if ('{{' in line or '{%' in line) else 'js'


# EKRANA BASAN ifade isaretleri — alan okumasi bunlardan birinin icindeyse
# "yayin" sayilir. (Yerel degiskene alma, siniflandirma, filtre: yayin degil.)
EMIT_JS = re.compile(r'`[^`]*<|innerHTML|\.push\(|csvSafe\(|document\.write|return\s'
                     # cok satirli sablon dizesinin ORTA satirlari: isaretleme + ${...}
                     r'|\$\{[^}]*\}[^\n]*<|<[^\n]*\$\{')


# TAKMA AD IZLEME — `const tp1 = signalData.tp1;` satiri yayin DEGILDIR ama
# `tp1` artik o alanin ta kendisidir; asagida `${fmt(tp1)}` diye BASILIR.
# Alias'i saymazsak kapi "alani yerel degiskene al, sonra bas" deseniyle
# tamamen atlatilabilirdi (36. ders: ayni isin degiskene atanmis hali ayri
# bir yazimdir).
ALIAS_ASSIGN = None  # scan_file icinde alanlara gore kurulur


def alias_map(src, fields):
    out = {}
    rx = re.compile(r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*[A-Za-z_$][\w$]*\.('
                    + '|'.join(re.escape(f) for f in fields) + r')\b')
    for m in rx.finditer(src):
        out[m.group(1)] = m.group(2)
    return out

def emits(stmt, dia):
    if dia == 'jinja':
        return '{{' in stmt
    return bool(EMIT_JS.search(stmt))

def js_block_openers(lines, idx, levels=6):
    """JS icin BLOK BAGLAMI: okumayi cevreleyen `{` acilis satirlari.

    Pencere yerine gercek kapsam aranir (140. ders: kapi hatanin yazimini
    degil KENDISINI arar; "45 satir yukarida bir yerde kapi vardi" bir
    kapsam iddiasi degildir). `} else {` acilisinda esleyen `if` satiri da
    baglama katilir -- kapi genelde orada yazar.
    """
    text = '\n'.join(lines[:idx + 1])
    out = []
    depth = 0
    j = len(text) - 1
    while j >= 0 and len(out) < levels:
        ch = text[j]
        if ch == '}':
            depth += 1
        elif ch == '{':
            if depth == 0:
                ln = text[:j].count('\n')
                blk = '\n'.join(lines[max(0, ln - 3):ln + 1])
                out.append(blk)
                if re.search(r'\belse\b', lines[ln]):
                    # esleyen `if` blogunu bul: `}` den geriye dengeli tarama
                    k = text.rfind('}', 0, j)
                    d2 = 0
                    while k >= 0:
                        if text[k] == '}':
                            d2 += 1
                        elif text[k] == '{':
                            d2 -= 1
                            if d2 == 0:
                                ln2 = text[:k].count('\n')
                                out.append('\n'.join(lines[max(0, ln2 - 3):ln2 + 1]))
                                break
                        k -= 1
            else:
                depth -= 1
        j -= 1
    return '\n'.join(out)

def scan_file(src, fields):
    """-> {alan: [(satir_no, lehce, kapi_var_mi)]} — yalniz EKRANA BASAN okumalar.

    Bir alani yerel degiskene almak ihlal degildir; ihlal o degerin KULLANICIYA
    BASILMASIDIR. Bu yuzden her okuma once "yayin yapiyor mu" diye suzulur
    (EMIT_JS / Jinja `{{`), sonra kapi ARANIR ve kapi ayni IFADEDE (JS'te
    ifadeyi olusturan 3 satirlik grup, Jinja'da ayni satir) ya da JS'te
    OKUMAYI CEVRELEYEN BLOK'ta olmak zorundadir.

    Neden komsuluk degil: `const isAl = s.signal === 'AL';` satiri kartin
    BASKA bir hucresini boyuyordu ve 45 satirlik komsuluk olcumunde kapi
    saniliyordu -- tam da bu turda duzeltilen kusuru ORTUYORDU (140. ders:
    kapi hatanin yazimini degil kendisini arar).
    """
    lines = src.split('\n')
    rx = field_re(fields)
    aliases = alias_map(src, fields)
    arx = (re.compile(r'\b(' + '|'.join(re.escape(a) for a in aliases) + r')\b')
           if aliases else None)
    out = {}
    for i, line in enumerate(lines):
        if DECL_LINE.search(line):
            continue
        found = [(m.start(), m.group(1)) for m in rx.finditer(line)]
        if arx:
            found += [(m.start(), aliases[m.group(1)]) for m in arx.finditer(line)
                      if not re.match(r'\s*(?:const|let|var)\s', line)]
        for _pos, f in found:
            dia = dialect_of(line)
            if dia == 'jinja':
                stmt = line
            else:
                stmt = '\n'.join(lines[i:i + 3])
            if not emits(stmt, dia):
                continue
            guards = GUARD_JINJA if dia == 'jinja' else GUARD_JS
            ctx = _norm(stmt)
            if dia == 'js':
                ctx += _norm(js_block_openers(lines, i))
            ok = any(g.replace(' ', '') in ctx for g in guards)
            out.setdefault(f, []).append((i + 1, dia, ok))
    return out


def scan_tree(root, inventory):
    fields = inventory['fields']
    declared = inventory['surfaces']
    bad = []
    seen = {}

    for sub, exts in SCAN:
        base = os.path.join(root, sub)
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if not fn.endswith(exts):
                    continue
                path = os.path.join(dp, fn)
                rel = os.path.relpath(path, root).replace(os.sep, '/')
                src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
                hits = scan_file(src, fields)
                if hits:
                    seen[rel] = hits

    # R1 — bildirilmemis kanal
    for rel, hits in sorted(seen.items()):
        if rel not in declared:
            ln = min(v[0][0] for v in hits.values())
            bad.append((rel, ln, 'R1',
                        "yon kapisina tabi alan(lar) okunuyor (%s) ama kanal "
                        "tools/long_only_surfaces.json'da BILDIRILMEMIS."
                        % ', '.join(sorted(hits))))

    for rel, meta in sorted(declared.items()):
        hits = seen.get(rel, {})
        # R2 — bayat girdi
        if not hits:
            bad.append((rel, 0, 'R2',
                        "envanterde bildirilmis ama dosyada gated alan YOK — "
                        "girdi bayat, kapi bu dosyada korlesmis olur."))
            continue
        # R3 — alan kumesi
        extra = sorted(set(hits) - set(meta.get('fields', [])))
        if extra:
            ln = min(hits[f][0][0] for f in extra)
            bad.append((rel, ln, 'R3',
                        "bildirilmemis yeni gated alan: %s (envanterdeki kume: %s)"
                        % (', '.join(extra), ', '.join(meta.get('fields', [])) or '-')))
        missing = sorted(set(meta.get('fields', [])) - set(hits))
        if missing:
            bad.append((rel, 0, 'R3',
                        "envanterde yazan ama artik okunmayan alan: %s — girdi bayat."
                        % ', '.join(missing)))

        if meta.get('status') == 'exempt':
            # R6 — gerekce
            if not (meta.get('reason') or '').strip():
                bad.append((rel, 0, 'R6', "status=exempt ama `reason` bos."))
            continue

        # R4 — her lehce ayri kapilanir
        dialects_seen = {d for occ in hits.values() for (_, d, _) in occ}
        for dia in sorted(dialects_seen):
            declared_d = meta.get('dialects', [])
            if dia not in declared_d:
                ln = min(l for occ in hits.values() for (l, d, _) in occ if d == dia)
                bad.append((rel, ln, 'R4',
                            "`%s` lehcesinde render var ama envanterde bildirilen "
                            "lehceler: %s" % (dia, ', '.join(declared_d) or '-')))
        # R5 — kapisiz okuma
        for f, occ in sorted(hits.items()):
            for (ln, dia, ok) in occ:
                if not ok:
                    bad.append((rel, ln, 'R5',
                                "`%s` (%s) EKRANA BASILIYOR ama ne ayni ifadede ne de "
                                "cevreleyen blokta yon kapisi var (eqApplies / "
                                "signal=='AL' / signal=='SAT' / _naForSat). Komsu "
                                "satirdaki bir yon kontrolu kapi SAYILMAZ." % (f, dia)))
    return bad


# ── sahte-pozitif / sahte-negatif vakalari ───────────────────────────────────
CASES = [
    # (ad, kaynak, lehce, kapi_beklenen)  -- None: "yayin degil, hic sayilmamali"
    ("js: kapisiz yayin",
     "const h = s.entry_quality ? `<span>${eqLabel(s.entry_quality)}</span>` : '-';", 'js', False),
    ("js: eqApplies kapisi",
     "const h = (eqApplies(s.signal) && s.entry_quality) ? `<span>x</span>` : '-';", 'js', True),
    ("js: signal === 'SAT' ucluisi",
     "case 'tp1': return (s.signal === 'SAT') ? _naForSat('x') : fmt(v);", 'js', True),
    ("js: kapi cevreleyen blokta",
     "if (s.signal === 'SAT') {\n  n();\n} else {\n  el.innerHTML = fmt(signalData.optimal_entry);\n}", 'js', True),
    ("js: KOMSU satirdaki isAl kapi DEGIL",
     "const isAl = s.signal === 'AL';\nconst badge = isAl ? 'al' : 'sat';\nif (s.entry_quality) metrics.push(`<div>x</div>`);", 'js', False),
    ("jinja: kapisiz yayin",
     "<td>{{ _eq.get(s.entry_quality, '-') }}</td>", 'jinja', False),
    ("jinja: signal == 'AL' kapisi",
     "{% if s.entry_quality and s.signal == 'AL' %}{{ s.entry_quality }}{% endif %}", 'jinja', True),
    ("jinja: bosluksuz yazim",
     "{% if s.signal=='AL' %}{{ s.rr_signal }}{% endif %}", 'jinja', True),
    ("jinja: UST SATIRDAKI rozet kapi DEGIL",
     "<span>{{ '+' if s.signal=='AL' else '-' }}</span>\n<div>{{ s.entry_quality }}</div>", 'jinja', False),
    ("yorum kapi SAYILMAZ (137. ders)",
     "/* SAT'ta gosterilmez: s.signal === 'SAT' */\nel.innerHTML = `<b>${s.entry_quality}</b>`;", 'js', False),
    ("kolon TANIMI render degildir",
     "{ key: 'entry_quality', label: 'Giris Kalitesi' },\ncase 'entry_quality': return (s.signal === 'SAT') ? na() : q(v);", 'js', True),
    ("yerel degiskene alma yayin degildir",
     "const tp1 = signalData.tp1;", 'js', None),
    ("siniflandirma yayin degildir",
     "const eqSafe = s.entry_quality === 'IDEAL' || s.entry_quality === 'IYI';", 'js', None),
]


def self_test():
    fields = ["entry_quality", "optimal_entry", "rr_signal", "tp1", "tp2"]
    ok = 0
    for name, src, dia, expect in CASES:
        hits = scan_file(strip_comments(src), fields)
        occs = [o for v in hits.values() for o in v]
        if expect is None:                      # yayin degil -> hic sayilmamali
            passed = (occs == [])
            got = "sayildi: %s" % occs
        else:
            got_guard = all(o[2] for o in occs) if occs else None
            got_dia = {o[1] for o in occs}
            passed = bool(occs) and (got_guard is expect) and (dia in got_dia)
            got = "kapi=%s, lehce=%s" % (got_guard, got_dia)
        ok += 1 if passed else 0
        print("  %-42s %s" % (name, "PASS" if passed else "FAIL (%s)" % got))
    inv = json.load(open(INVENTORY, encoding='utf-8'))
    sem = isinstance(inv.get('fields'), list) and isinstance(inv.get('surfaces'), dict)
    print("  %-42s %s" % ("envanter semasi", "PASS" if sem else "FAIL"))
    ok += 1 if sem else 0
    total = len(CASES) + 1
    print("self-test %d/%d" % (ok, total))
    return 0 if ok == total else 1


def tree_at_ref(ref):
    d = tempfile.mkdtemp(prefix='longonly-')
    blob = subprocess.check_output(['git', 'archive', ref])
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    return d


def main():
    if '--self-test' in sys.argv:
        return self_test()
    ref = None
    if '--ref' in sys.argv:
        ref = sys.argv[sys.argv.index('--ref') + 1]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = tree_at_ref(ref) if ref else repo
    inv_path = os.path.join(root, INVENTORY)
    if not os.path.exists(inv_path):          # eski agac: envanter yok
        inv_path = os.path.join(repo, INVENTORY)
    inventory = json.load(open(inv_path, encoding='utf-8'))
    bad = scan_tree(root, inventory)
    tag = " (ref %s)" % ref if ref else ""
    if not bad:
        print("K-DE OK — long-only sunum kurali bildirilen %d kanalin hepsinde "
              "kapili%s." % (len(inventory['surfaces']), tag))
        return 0
    print("K-DE KIRIK — %d ihlal%s:" % (len(bad), tag))
    for rel, ln, kind, msg in sorted(bad):
        print("  [%s] %s:%s  %s" % (kind, rel, ln or '-', msg))
    print("\n  Kanon (/metodoloji): Trend Bozuldu sinyalinde giris kalitesi,")
    print("  hedef/stop yapisi ve R/R GOSTERILMEZ — BIST'te bireysel yatirimci")
    print("  aciga satamaz. Karar noktasi tek yerde: bp-vocab.js eqApplies().")
    return 1


if __name__ == '__main__':
    sys.exit(main())
