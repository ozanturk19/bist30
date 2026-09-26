#!/usr/bin/env python3
"""D-16: güvenli shadow karşılaştırma (backend-mimari.md §5.1). Yalnız GET, yalnız localhost.

  shadow_compare.py --a http://127.0.0.1:8003 --b http://127.0.0.1:8013 [--tickers 20|all]
  shadow_compare.py --spawn /root/bist30 --a http://127.0.0.1:8003 --port 8013   # b'yi kendisi açar

--spawn: <dizin>'de `BP_ROLE=shadow` tek-worker gunicorn açar; bitince kabul denetimlerini koşar
(shadow PID'i /tmp/bp_*.lock'ta yok, işaret dosyasından sonra data/'da değişiklik yok) ve kapatır.
Fark varsa uç + JSON-yolu listesi basar, çıkış kodu 1. Yalnız kod-özdeşliği için; canlı ortamda
`--spawn` YALNIZ BP_ROLE=shadow'u tanıyan kodla kullanılır (eski kod thread başlatıp kilit kapar)."""
import argparse, glob, json, os, re, subprocess, sys, time, urllib.error, urllib.request

DROP = {"stocks_age_s", "age_s", "ts", "cached", "uptime_sec", "generated_at",
        "fetched_at", "server_time", "updated_at", "stocks_updated_at"}  # son ikisi: diskten yüklemede dosya saati
DROP_SUFFIX = ("_age_seconds", "_age_s")
API = ["/api/data", "/api/data-lite", "/api/tarama", "/api/tarama/temel", "/api/gundem",
       "/api/sector-heatmap", "/api/sektor-summary", "/api/bilanco-takvimi",
       "/api/temettu-takvimi", "/api/macro", "/api/stocks/list", "/api/backtest"]
# Yalnız bellekte (yfinance/lider iş parçacığı) hesaplanır, shadow'da soğuk → yalnız HTTP durumu karşılaştırılır
COLD = {"/api/bilanco-takvimi", "/api/backtest"}
PER_TICKER = ["lite", "chart", "fundamentals", "health-score", "mtf", "signal-story"]
PAGES = ["/", "/tarama", "/sektor-harita"]
SAMPLE = ["THYAO", "GARAN", "ASELS", "BIMAS", "EREGL", "KCHOL", "ANHYT", "ULKER", "ENKAI", "AEFES"]


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # bağlantı/zaman aşımı → fark olarak görünür
        return -1, repr(e)


def norm(o):
    if isinstance(o, dict):
        return {k: norm(v) for k, v in o.items() if k not in DROP and not k.endswith(DROP_SUFFIX)}
    return [norm(v) for v in o] if isinstance(o, list) else o


def diff(a, b, path="$"):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        out = [f"{path}.{k}" for k in a.keys() ^ b.keys()]
        for k in a.keys() & b.keys():
            out += diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}[len {len(a)}!={len(b)}]"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [path]


def html_view(t):  # görünür metin + data-* öznitelikleri (script/style/nonce hariç)
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", t)
    data = sorted(re.findall(r'\sdata-[\w-]+="[^"]*"', t))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip(), data


def compare(a, b, path):
    (sa, ta), (sb, tb) = get(a, path), get(b, path)
    if sa != sb:
        return [f"{path} status {sa}!={sb}"]
    if sa != 200 or path in COLD:
        return []
    if path.startswith("/api/"):
        try:
            return [f"{path} {d}" for d in diff(norm(json.loads(ta)), norm(json.loads(tb)))]
        except ValueError:
            return [f"{path} json-değil"] if ta != tb else []
    return [] if html_view(ta) == html_view(tb) else [f"{path} html metin/data-* farkı"]


def spawn(root, port):
    marker = f"/tmp/shadow_marker_{os.getpid()}"
    open(marker, "w").close()
    time.sleep(1.1)
    env = dict(os.environ, BP_ROLE="shadow")
    for l in open(os.path.join(root, ".env")) if os.path.exists(os.path.join(root, ".env")) else []:
        if "=" in l and not l.lstrip().startswith("#"):
            k, v = l.strip().split("=", 1)
            env.setdefault(k, v.strip("'\""))
    p = subprocess.Popen([os.path.join(root, "venv/bin/gunicorn"), "-w", "1", "-k",
                          "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "--bind",
                          f"127.0.0.1:{port}", "--timeout", "120", "app:app"], cwd=root, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(90):
        if get(f"http://127.0.0.1:{port}", "/api/stocks/list")[0] == 200:
            return p, marker
        time.sleep(1)
    p.terminate()
    sys.exit("shadow açılmadı")


def checks(p, root, marker):
    fails = []
    pids = {str(p.pid)} | set(subprocess.run(["pgrep", "-P", str(p.pid)], capture_output=True,
                                             text=True).stdout.split())
    for lk in glob.glob("/tmp/bp_*.lock"):
        held = subprocess.run(["lsof", "-t", lk], capture_output=True, text=True).stdout.split()
        if pids & set(held):
            fails.append(f"shadow PID {lk} kilidinde")
    new = subprocess.run(["find", os.path.join(root, "data"), "-newer", marker, "-type", "f"],
                         capture_output=True, text=True).stdout.split()
    return fails + [f"data yazımı: {f}" for f in new]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="http://127.0.0.1:8003")
    ap.add_argument("--b", default="http://127.0.0.1:8013")
    ap.add_argument("--tickers", default="20")
    ap.add_argument("--spawn")
    ap.add_argument("--port", type=int, default=8013)
    o = ap.parse_args()
    proc = None
    if o.spawn:
        proc, marker = spawn(o.spawn, o.port)
        o.b = f"http://127.0.0.1:{o.port}"
    try:
        lst = json.loads(get(o.a, "/api/stocks/list")[1] or "{}").get("stocks", [])
        tk = [s["ticker"] for s in lst]
        tk = tk if o.tickers == "all" else tk[:int(o.tickers)]
        paths = API + PAGES + [f"/hisse/{t}" for t in SAMPLE if t in tk or o.tickers != "all"] + \
            [f"/api/hisse/{t}/{e}" for t in tk for e in PER_TICKER]
        fails = [f for p in paths for f in compare(o.a, o.b, p)]
        if proc:
            fails += checks(proc, o.spawn, marker)
    finally:
        if proc:
            proc.terminate()
    print(f"{len(paths)} uç karşılaştırıldı, fark: {len(fails)}")
    print("\n".join(fails[:200]))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
