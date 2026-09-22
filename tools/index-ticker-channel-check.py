#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAPI 73 — K-DC (22.09.2026): "ENDEKS BIR HISSE DEGIL" KURALI KANAL KANAL.

app.py:11235 kuralı açıkça yazıyor:
    # CPO-1107 Faz0#6: XU030 bir endeks, hisse değil — evren sayısı/liste tek kaynak
Ama bu kural ürünün her kanalında ELLE tekrar ediliyor (22.09 sayımı: 9 ayrı
yazım), ve üç kanal kuralı hiç uygulamıyordu:

  1) templates/404.html — "Bunu mu demek istediniz?" kutusu `/api/data`'dan
     (217 kayıt) ham ticker listesi kuruyordu: kullanıcı "XU" yazınca ürün
     ENDEKSİ hisse diye öneriyordu. Aynı fonksiyon iki evren döndürüyordu:
     oturum önbelleği yolu 216 (bp-search kanonu), fetch yolu 217.  -> K-DC'de
     `/api/stocks/list` kanonuna geçirildi, bu kapı regresyonu bekliyor.
  2) app.py `stock_page` — `/hisse/XU030` 200 dönüyor (DEV1, CPO-1783).
  3) app.py `karsilastir` — `?tickers=...,XU030` kabul ediliyor (DEV1).

⛔ 135. dersin uygulaması: kural "kaç kanalda geçerli, kapı kaçını görüyor?"

KURALLAR
  R1  `/api/data`'yı fetch eden HER frontend dosyası
      tools/api_data_consumers.json'da sınıflandırılmış olmalı.
        · bildirilmemiş dosya            -> IHLAL (yeni kanal = insan kararı)
        · bildirilmiş ama artık fetch etmiyor -> IHLAL (bayat envanter)
  R2  mode="filtered" dosyada endeks ticker elemesi GERÇEKTEN olmalı.
  R3  mode="keyed" dosya ticker EVRENİ üretmemeli: `stocks…map(… .ticker …)`
      deseni (tam da 404.html'in kusuru) yasak.
  R4  Sayfa üreten route'lar (`stock_page`, `karsilastir`) endeks ticker'ı
      reddetmeli. Muafiyet route_guard_exempt'te; DONDURULMUS, yalnız
      küçülebilir — muaf route guard EKLERSE giriş bayatlar ve FAIL verir.

Kullanım:
  python3 tools/index-ticker-channel-check.py
  python3 tools/index-ticker-channel-check.py --self-test   # 12/12 beklenir
  python3 tools/index-ticker-channel-check.py --ref 4905153  # 1 ihlal beklenir
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join("tools", "api_data_consumers.json")

INDEX_TICKERS = ("XU030", "XU100")

# fetch('/api/data')  —  YORUM icindeki "/api/data" gecislerini ELEMEK icin
# `fetch(` sart. (`/api/data-quality`, `/api/data-lite` AYRI endpointler:
# sinir `['"]` ile kapatiliyor.)
RE_FETCH = re.compile(r"""fetch\(\s*['"]/api/data['"]""")

# stocks -> ticker DIZISI uretimi: `d.stocks.map(function(s){ return s.ticker })`
# `(j.stocks || []).map(s => s.ticker)` gibi yazimlari da yakalar.
RE_UNIVERSE = re.compile(r"stocks\b[^;\n]{0,40}\.map\([^;]{0,200}?\.ticker", re.S)

RE_INDEX_FILTER = re.compile(r"|".join(INDEX_TICKERS))

FRONTEND_DIRS = (("templates", ".html"), ("static", ".js"))


def _frontend_files(base):
    out = []
    for d, ext in FRONTEND_DIRS:
        root = os.path.join(base, d)
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                if fn.endswith(ext):
                    full = os.path.join(dirpath, fn)
                    out.append(os.path.relpath(full, base))
    return sorted(out)


def _strip_js_comments(src):
    """Blok ve satir yorumlarini soyar. ⛔137. ders: kanon kumesi okunurken
    yorumlar soyulmazsa kapi kendi belgelendirmesiyle korlesir — burada tersi
    de gecerli: YORUMDAKI bir `XU030` notu 'filtre var' sanilmamali."""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        elif c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
            out.append(" ")
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _py_func_body(src, name):
    """app.py icinde `def <name>(` ile baslayan fonksiyonun govdesi."""
    m = re.search(r"^def %s\(" % re.escape(name), src, re.M)
    if not m:
        return None
    start = m.start()
    rest = src[m.end():]
    m2 = re.search(r"^(?:@app\.route|def |@app\.errorhandler)", rest, re.M)
    end = m.end() + (m2.start() if m2 else len(rest))
    return src[start:end]


def _admission_region(body):
    """GIRIS KAPISI bolgesi: `def`den ILK `render_template(` cagrisina kadar.

    ⛔ Kapi hatanin YAZIMINI degil KENDISINI aramali (55. ders). Ilk yazimda
    "fonksiyon govdesinde XU030 geciyor mu" diye bakiyordum ve `stock_page`
    YANLISLIKLA korunuyor sayildi: oradaki eleme (app.py:8404) sayfanin KABUL
    kapisi degil, AYNI SEKTOR peer listesiydi -- sayfa yine 200 donuyordu.
    Kabul/red karari (404/410/redirect) daima ilk render'dan ONCE verilir."""
    i = body.find("render_template(")
    return body if i < 0 else body[:i]


def audit(base):
    """(ihlal listesi) dondurur. Her ihlal: (kural, yol, aciklama)."""
    viol = []
    reg_path = os.path.join(base, REGISTRY)
    if not os.path.exists(reg_path):
        return [("R1", REGISTRY, "envanter dosyasi YOK")]
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
    consumers = reg.get("consumers", {})
    exempt = reg.get("route_guard_exempt", {})

    # ── R1/R2/R3 — frontend kanallari ────────────────────────────────────
    actual = {}
    for rel in _frontend_files(base):
        try:
            with open(os.path.join(base, rel), encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError:
            continue
        code = _strip_js_comments(raw)
        if RE_FETCH.search(code):
            actual[rel] = code

    for rel in sorted(actual):
        if rel not in consumers:
            viol.append(("R1", rel,
                         "/api/data fetch ediyor ama envanterde YOK — "
                         "filtered mi keyed mi, siniflandir"))
            continue
        mode = consumers[rel].get("mode")
        code = actual[rel]
        if mode == "filtered":
            if not RE_INDEX_FILTER.search(code):
                viol.append(("R2", rel,
                             "mode=filtered ama kodda endeks ticker elemesi YOK"))
        elif mode == "keyed":
            m = RE_UNIVERSE.search(code)
            if m:
                viol.append(("R3", rel,
                             "mode=keyed ama stocks->ticker DIZISI uretiyor: "
                             + " ".join(m.group(0).split())[:80]))
        else:
            viol.append(("R1", rel, "envanterde gecersiz mode: %r" % (mode,)))

    for rel in sorted(consumers):
        if rel not in actual:
            viol.append(("R1", rel,
                         "envanterde bildirilmis ama artik /api/data fetch "
                         "ETMIYOR — BAYAT girdi, envanterden cikar"))

    # ── R4 — sayfa ureten route'lar ──────────────────────────────────────
    app_path = os.path.join(base, "app.py")
    if os.path.exists(app_path):
        with open(app_path, encoding="utf-8", errors="replace") as fh:
            app_src = fh.read()
        for fn in ("stock_page", "karsilastir"):
            body = _py_func_body(app_src, fn)
            if body is None:
                continue
            guarded = RE_INDEX_FILTER.search(_admission_region(body)) is not None
            if fn in exempt:
                if guarded:
                    viol.append(("R4", "app.py:%s" % fn,
                                 "MUAFIYET BAYAT: route artik endeks ticker'i "
                                 "ayirt ediyor, muafiyeti kaldir (%s)"
                                 % exempt[fn].get("ticket", "?")))
            elif not guarded:
                viol.append(("R4", "app.py:%s" % fn,
                             "sayfa ureten route endeks ticker'i reddetmiyor"))
    return viol


# ── self-test ───────────────────────────────────────────────────────────────
_FIX_REG = {
    "consumers": {
        "templates/a.html": {"mode": "filtered", "reason": "x"},
        "templates/b.html": {"mode": "keyed", "reason": "x"},
    },
    "route_guard_exempt": {},
}


def _mk(base, rel, body):
    p = os.path.join(base, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(body)


def self_test():
    cases = []

    def run(name, files, reg, expect):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "tools"), exist_ok=True)
            with open(os.path.join(td, REGISTRY), "w", encoding="utf-8") as fh:
                json.dump(reg, fh)
            os.makedirs(os.path.join(td, "templates"), exist_ok=True)
            os.makedirs(os.path.join(td, "static"), exist_ok=True)
            for rel, body in files.items():
                _mk(td, rel, body)
            got = sorted(v[0] for v in audit(td))
            ok = got == sorted(expect)
            cases.append((ok, name, got, sorted(expect)))

    FILT = "fetch('/api/data').then(d=>d.stocks.filter(s=>s.ticker!=='XU030'))"
    KEYED = "fetch('/api/data').then(d=>{d.stocks.forEach(s=>m[s.ticker]=s);})"
    UNIV = "fetch('/api/data').then(function(d){var t=d.stocks.map(function(s){return s.ticker;});})"

    run("temiz agac", {"templates/a.html": FILT, "templates/b.html": KEYED},
        _FIX_REG, [])
    run("bildirilmemis kanal",
        {"templates/a.html": FILT, "templates/b.html": KEYED,
         "templates/yeni.html": FILT}, _FIX_REG, ["R1"])
    run("bayat envanter girdisi", {"templates/a.html": FILT}, _FIX_REG, ["R1"])
    run("filtered ama filtre yok",
        {"templates/a.html": "fetch('/api/data')", "templates/b.html": KEYED},
        _FIX_REG, ["R2"])
    run("keyed ama evren uretiyor (404.html kusuru)",
        {"templates/a.html": FILT, "templates/b.html": UNIV}, _FIX_REG, ["R3"])
    run("YORUMDAKI XU030 filtre SAYILMAZ",
        {"templates/a.html": "/* XU030 endekstir */\nfetch('/api/data')",
         "templates/b.html": KEYED}, _FIX_REG, ["R2"])
    run("/api/data-quality fetch'i tuketici DEGIL",
        {"templates/a.html": FILT, "templates/b.html": KEYED,
         "templates/c.html": "fetch('/api/data-quality')"}, _FIX_REG, [])

    BASE = {"templates/a.html": FILT, "templates/b.html": KEYED}
    EXEMPT_REG = dict(_FIX_REG, route_guard_exempt={"stock_page": {"ticket": "T-1"}})
    APP_GUARDED = (
        'def stock_page(ticker):\n'
        '    if ticker in ("XU030",):\n        return render_template("404.html"), 404\n'
        '    return render_template("hisse.html")\n')
    APP_OPEN = (
        'def stock_page(ticker):\n'
        '    return render_template("hisse.html")\n')
    # ⛔ ASIL SAHTE-POZITIF: kural fonksiyonda GECIYOR ama giris kapisinda degil
    APP_LATE = (
        'def stock_page(ticker):\n'
        '    html = render_template("hisse.html")\n'
        '    peers = [t for t in pool if t != "XU030"]\n'
        '    return html\n')
    run("R4 muaf degil + guard YOK", dict(BASE, **{"app.py": APP_OPEN}),
        _FIX_REG, ["R4"])
    run("R4 muaf degil + guard VAR", dict(BASE, **{"app.py": APP_GUARDED}),
        _FIX_REG, [])
    run("R4 XU030 render'DAN SONRA geciyor (peer listesi) -> guard SAYILMAZ",
        dict(BASE, **{"app.py": APP_LATE}), _FIX_REG, ["R4"])
    run("R4 muaf + guard YOK (beklenen durum)", dict(BASE, **{"app.py": APP_OPEN}),
        EXEMPT_REG, [])
    run("R4 muaf + guard EKLENDI -> muafiyet BAYAT",
        dict(BASE, **{"app.py": APP_GUARDED}), EXEMPT_REG, ["R4"])

    for ok, name, got, exp in cases:
        print("  %s %-45s got=%s exp=%s" % ("✓" if ok else "✗", name, got, exp))
    n = sum(1 for c in cases if c[0])
    print("self-test %d/%d" % (n, len(cases)))
    return 0 if n == len(cases) else 1


def at_ref(ref):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git", "worktree", "add", "--detach", td, ref],
                       cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            # Envanter kapinin KENDI kanonudur, test edilen kodun degil:
            # gecmis bir ref'te dosya henuz yoktu. Bugunku envanteri enjekte
            # ederek "o gun kanal envanteri tutarli miydi" sorusu sorulur.
            os.makedirs(os.path.join(td, "tools"), exist_ok=True)
            with open(os.path.join(ROOT, REGISTRY), encoding="utf-8") as fh:
                cur = fh.read()
            with open(os.path.join(td, REGISTRY), "w", encoding="utf-8") as fh:
                fh.write(cur)
            return audit(td)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", td],
                           cwd=ROOT, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)


def main():
    if "--self-test" in sys.argv:
        return self_test()
    if "--ref" in sys.argv:
        ref = sys.argv[sys.argv.index("--ref") + 1]
        viol = at_ref(ref)
        print("ref %s -> %d ihlal" % (ref, len(viol)))
    else:
        viol = audit(ROOT)
    for rule, path, msg in viol:
        print("  ✗ [%s] %s — %s" % (rule, path, msg))
    if not viol:
        print("  ✓ endeks/hisse kanal envanteri tutarli")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
