#!/usr/bin/env python3
"""D-27 / A3 — EOD oneshot CLI sarmalayıcı (app.py'yi BP_ROLE=batch ile import eder).

`background_refresh()` (app.py:4883+) sonsuz while-loop'unun web-worker DIŞI EOD
dallarını (ana tur / chart re-verify / catch-up / resmi kapanış) tek seferlik komut
satırına çevirir — CPO-1834 (18.10 20:3x) onayı: ince sarmalayıcı, app.py'deki
fonksiyonları DOĞRUDAN çağırır, yeniden yazım yok. D-26'nın slow-chart/fundamentals/
MTF thread'leri BU SARMALAYICIYA TAŞINMAZ — kendi EOD-gated thread'lerinde kalır
(background_refresh web worker'larda hâlâ başlar, D-28/A4'e kadar).

Zaman pencereleri app.py'deki ORİJİNAL `_eod_fetch_trigger_ready_after()` /
`_eod_data_ready_after()` / `_catchup_retry_ready_after()` / `_official_pass_window()`
ile birebir aynı — kopyalanmadı, `app` modülünden çağrılıyor. Hang koruması BİLEREK
kod seviyesinde değil: `bp-eod.timer`'ın systemd `TimeoutStartSec`'i process'i keser,
`bp-eod-retry.timer` (16:30 UTC) bir sonraki pencerede yeniden dener (Stabilite > UX,
Maksimum Sadelik — background_refresh'teki ThreadPoolExecutor watchdog'u sürekli web
process'ini korumak için gerekliydi, oneshot CLI'da bu rolü systemd üstlenir).

Kullanım (WorkingDirectory=/root/bist30):
  python3 -m pipeline.eod run                  # ana tur + chart re-verify (zaman kapılı)
  python3 -m pipeline.eod run --only-missing   # yalnız catch-up + resmi kapanış denemesi

Henüz hiçbir systemd unit'e bağlı DEĞİL (D-27 adım 2/7 — Cmt 24.10 11:00 pipeline-fazı
penceresinde kurulacak: adım 3). Geri alma: bu dosyayı kullanmamak/silmek yeterli,
background_refresh() dokunulmadı.
"""
import argparse
import os
import sys
import time

os.environ.setdefault("BP_ROLE", "batch")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402


def _snapshot_path(today_tr):
    return os.path.join(app._SNAPSHOTS_DIR, f"{today_tr.strftime('%Y-%m-%d')}.json")


def _main_pass(today_tr):
    """Ana EOD turu: refresh_data + chart refresh + purge + earnings (18:10 TR+)."""
    app.logger.info("pipeline.eod: ana EOD turu başlıyor (%s)", today_tr.isoformat())
    app.refresh_data()
    for fn in (app.refresh_chart, app.refresh_xu100_chart):
        try:
            fn()
        except Exception:
            app.logger.error("pipeline.eod: %s hatası", fn.__name__, exc_info=True)
        time.sleep(5)
    try:
        app._purge_stale_chart_caches()
    except Exception:
        app.logger.error("pipeline.eod: purge hatası", exc_info=True)
    try:
        app._do_earnings_refresh()
    except Exception:
        app.logger.error("pipeline.eod: earnings hatası", exc_info=True)


def _chart_reverify_pass(today_tr, flag_path):
    """Yahoo settle payı doğrulaması: aynı chart fonksiyonları, 18:30 TR+ bir kez."""
    app.logger.info("pipeline.eod: chart re-verify turu (%s)", today_tr.isoformat())
    for fn in (app.refresh_chart, app.refresh_xu100_chart):
        try:
            fn()
        except Exception:
            app.logger.error("pipeline.eod: %s re-verify hatası", fn.__name__, exc_info=True)
        time.sleep(5)
    try:
        with open(flag_path, "w", encoding="utf-8") as f:
            f.write(app.datetime.now(app._TZ_TR).strftime("%d.%m.%Y %H:%M:%S"))
    except OSError as e:
        app.logger.warning("pipeline.eod: chart reverify marker yazılamadı: %s", e)


def run(only_missing=False):
    today_tr = app.datetime.now(app._TZ_TR).date()
    if not app.is_trading_day(today_tr):
        app.logger.info("pipeline.eod: işlem günü değil, no-op (%s)", today_tr.isoformat())
        return

    snapshot_path = _snapshot_path(today_tr)
    already_done = os.path.exists(snapshot_path)

    if only_missing:
        if not already_done:
            app.logger.info("pipeline.eod: --only-missing ama ana tur henüz koşmadı, no-op")
            return
        official_flag = os.path.join(
            app._SNAPSHOTS_DIR, f"{today_tr.strftime('%Y-%m-%d')}_official_close.flag")
        if app._official_pass_window() and not os.path.exists(official_flag):
            if app._run_official_close_pass(today_tr):
                try:
                    with open(official_flag, "w", encoding="utf-8") as f:
                        f.write(app.datetime.now(app._TZ_TR).strftime("%d.%m.%Y %H:%M:%S"))
                except OSError as e:
                    app.logger.warning("pipeline.eod: official_close flag yazılamadı: %s", e)
        catchup_path = os.path.join(
            app._SNAPSHOTS_DIR, f"{today_tr.strftime('%Y-%m-%d')}_catchup.flag")
        if not os.path.exists(catchup_path) and app._catchup_retry_ready_after():
            app._run_catchup_retry_pass(catchup_path)
        return

    if not already_done and app._eod_fetch_trigger_ready_after():
        _main_pass(today_tr)
        already_done = os.path.exists(snapshot_path)

    reverify_path = os.path.join(
        app._SNAPSHOTS_DIR, f"{today_tr.strftime('%Y-%m-%d')}_chart_reverify.flag")
    if already_done and app._eod_data_ready_after() and not os.path.exists(reverify_path):
        _chart_reverify_pass(today_tr, reverify_path)


def main():
    parser = argparse.ArgumentParser(description="D-27 EOD oneshot CLI sarmalayıcı")
    sub = parser.add_subparsers(dest="action", required=True)
    run_p = sub.add_parser("run", help="EOD turu (zaman kapılı, uygun değilse no-op)")
    run_p.add_argument("--only-missing", action="store_true",
                        help="yalnız catch-up + resmi kapanış denemesi (ana tur zaten koşmuşsa)")
    args = parser.parse_args()
    if args.action == "run":
        run(only_missing=args.only_missing)


if __name__ == "__main__":
    main()
