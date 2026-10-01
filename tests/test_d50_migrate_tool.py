"""D-50 göç aracı (tools/migrate_accounts.py) — sentetik abone dosyasıyla, py3.9 yerel."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)

import migrate_accounts as M  # noqa: E402

SUBS = {
    "u1@ornek.com": {"token": "a" * 48, "tickers": [], "follow": ["THYAO"], "active": True, "mail_pref": "daily"},
    "u2@ornek.com": {"token": "b" * 48, "tickers": ["ASELS"], "active": True, "mail_pref": "instant"},
    "u3@ornek.com": {"token": "c" * 48, "tickers": [], "alerts": {"SASA": {"signal_change": True}}, "active": False},
    "u4@ornek.com": {"token": "d" * 48, "active": True},
}


def test_dry_run_apply_restore(tmp_path, capsys):
    p = tmp_path / "subscribers.json"
    p.write_text(json.dumps(SUBS), encoding="utf-8")
    before = p.read_bytes()
    assert M.main(["--file", str(p)]) == 0
    out = capsys.readouterr().out
    assert "KURU KOŞU" in out and '"migrated": 4' in out and "@" not in out
    assert p.read_bytes() == before                       # kuru koşu dosyaya dokunmaz

    assert M.main(["--file", str(p), "--apply"]) == 0
    out = capsys.readouterr().out
    assert "doğrulama: TAMAM (4 kayıt)" in out and "@" not in out
    baks = [f for f in os.listdir(tmp_path) if ".bak.d50-" in f]
    assert len(baks) == 1 and (tmp_path / baks[0]).read_bytes() == before
    assert oct(os.stat(p).st_mode & 0o777) == "0o600"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert all(r["account_v"] == 1 for r in data.values())
    assert data["u1@ornek.com"]["watchlist"] == ["THYAO"] and "follow" not in data["u1@ornek.com"]
    assert data["u2@ornek.com"]["notify"] == {"trend": True, "bulten": False}

    assert M.main(["--file", str(p), "--apply"]) == 0     # ikinci koşu: değişiklik yok
    assert "değişiklik yok" in capsys.readouterr().out

    assert M.main(["--file", str(p), "--restore", str(tmp_path / baks[0])]) == 0
    assert json.loads(p.read_text(encoding="utf-8")) == SUBS
