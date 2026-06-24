#!/usr/bin/env python3
"""
Pre-deploy visual regression check — CPO-740 Görev 12a.

Playwright ile current screenshot'lar alır, baseline ile pixel diff karşılaştırır.
Exit 0: tüm sayfalar pass (regression yok).
Exit 1: en az 1 sayfada regression tespit edildi.
Exit 2: screenshot capture başarısız (Playwright/server sorunu).

Kullanım:
  python3 tools/pre_deploy_visual_check.py [--base=http://localhost:8003] [--threshold=0.02]

Git pre-push hook entegrasyonu:
  Sunucu çalışmıyorsa WARN + exit 0 (deploy'u BLOKE ETMEZ, sadece uyarır).
  Sunucu çalışıyor + regression var → exit 1 (push bloke edilir).
"""
import sys
import os
import subprocess
import glob
import json
import time
import argparse

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)

BASELINE_DIR = os.path.join(_REPO_ROOT, "tests", "visual", "baseline")
CURRENT_DIR  = os.path.join(_REPO_ROOT, "tests", "visual", "current")
DIFF_DIR     = os.path.join(_REPO_ROOT, "tests", "visual", "diff")
VISUAL_TEST_JS = os.path.join(_TOOLS_DIR, "visual-test.js")

sys.path.insert(0, _REPO_ROOT)


def _server_reachable(base_url: str, timeout: int = 3) -> bool:
    try:
        result = subprocess.run(
            ["curl", "-s", f"--max-time={timeout}", "-o", "/dev/null", "-w", "%{http_code}", f"{base_url}/api/health"],
            capture_output=True, text=True, timeout=timeout + 2,
        )
        return result.stdout.strip() == "200"
    except Exception:
        return False


def _capture_screenshots(base_url: str, timeout: int = 120) -> bool:
    env = {**os.environ, "VTEST_BASE": base_url}
    result = subprocess.run(
        ["node", VISUAL_TEST_JS],
        cwd=_TOOLS_DIR,
        env=env,
        capture_output=True, text=True, timeout=timeout,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        print(f"Screenshot capture FAILED:\n{result.stderr[-400:]}", file=sys.stderr)
        return False
    return True


def _run_diff_checks(threshold: float) -> tuple:
    from playwright_checks import check_visual_diff

    baseline_pngs = sorted(glob.glob(os.path.join(BASELINE_DIR, "*.png")))
    if not baseline_pngs:
        print("WARN: Baseline PNG bulunamadı — visual check atlandı")
        return [], []

    os.makedirs(DIFF_DIR, exist_ok=True)
    passes, fails = [], []

    for baseline_path in baseline_pngs:
        name = os.path.basename(baseline_path)
        current_path = os.path.join(CURRENT_DIR, name)
        diff_path = os.path.join(DIFF_DIR, name)

        if not os.path.exists(current_path):
            fails.append({"name": name, "flag": "MISSING_CURRENT"})
            print(f"  ✗ {name}: current screenshot eksik")
            continue

        res = check_visual_diff(baseline_path, current_path,
                                threshold=threshold, diff_path=diff_path)
        if res["ok"]:
            passes.append(name)
            print(f"  ✓ {name} ({res.get('diff_ratio', 0):.4f})")
        else:
            fails.append({"name": name, **res})
            dr = res.get("diff_ratio", "?")
            print(f"  ✗ {name}: diff={dr} > threshold={threshold} {res.get('flag', '')}")

    return passes, fails


def main():
    parser = argparse.ArgumentParser(description="Pre-deploy visual regression check")
    parser.add_argument("--base", default="http://localhost:8003", help="Dev server base URL")
    parser.add_argument("--threshold", type=float, default=0.02, help="Max diff ratio (default 2%%)")
    parser.add_argument("--skip-capture", action="store_true", help="Kullan mevcut current/ screenshots")
    parser.add_argument("--warn-only", action="store_true", help="Regression varsa exit 1 yerine exit 0 + warn")
    args = parser.parse_args()

    t0 = time.monotonic()
    print(f"\n=== Pre-Deploy Visual Check ===")
    print(f"Base: {args.base} | Threshold: {args.threshold * 100:.1f}%")

    # 1. Sunucu erişilebilir mi?
    if not args.skip_capture:
        if not _server_reachable(args.base):
            print(f"WARN: Sunucu {args.base} erişilemiyor — visual check atlandı (deploy devam eder)")
            sys.exit(0)

        # 2. Current screenshots yakala
        print("\nScreenshots yakalanıyor...")
        if not _capture_screenshots(args.base):
            print("ERROR: Screenshot capture başarısız", file=sys.stderr)
            sys.exit(2)
    else:
        print("(mevcut current/ screenshots kullanılıyor)")

    # 3. Diff karşılaştır
    print("\nBaseline diff kontrol:")
    passes, fails = _run_diff_checks(args.threshold)

    elapsed = time.monotonic() - t0
    total = len(passes) + len(fails)
    print(f"\n{'='*40}")
    print(f"Sonuç: {len(passes)}/{total} PASS | {len(fails)} FAIL | {elapsed:.1f}s")

    if fails:
        print(f"\nRegression tespit edildi ({len(fails)} sayfa):")
        for f in fails:
            diff_ratio = f.get("diff_ratio", "?")
            print(f"  - {f['name']}: {f.get('flag', 'UNKNOWN')} diff={diff_ratio}")
        if not args.warn_only:
            print("\n❌ Pre-deploy visual check BAŞARISIZ — deploy iptal")
            sys.exit(1)
        else:
            print("\n⚠️  Visual regression var (--warn-only: deploy devam eder)")
            sys.exit(0)

    print("\n✅ Pre-deploy visual check BAŞARILI")
    sys.exit(0)


if __name__ == "__main__":
    main()
