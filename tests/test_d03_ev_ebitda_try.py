"""D-03: yabanci para raporlayan hissede FD/FAVOK TRY'ye cevrilerek hesaplanir."""
import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import _ev_to_ebitda_try
from yf_fundamentals_fetch import _merge_cross_statement_ratios


def test_thyao_benzeri_usd_raporlayan():
    # mcap 400 mlr TRY, kur 40, FAVOK 6 mlr USD, net borc 0,9 mlr USD
    # EV = 400 + 0,9*40 = 436 mlr TRY; FAVOK = 240 mlr TRY -> 1,82x
    assert _ev_to_ebitda_try(400e9, 40.0, 6e9, 0.9e9) == 1.82


def test_net_nakit_pozisyonu_evi_dusurur():
    assert _ev_to_ebitda_try(400e9, 40.0, 6e9, -1e9) == round((400e9 - 40e9) / 240e9, 2)


def test_eksik_ya_da_negatif_girdide_none():
    assert _ev_to_ebitda_try(400e9, None, 6e9, 1e9) is None
    assert _ev_to_ebitda_try(400e9, 40.0, None, 1e9) is None
    assert _ev_to_ebitda_try(400e9, 40.0, -1e9, 1e9) is None
    assert _ev_to_ebitda_try(400e9, 40.0, 6e9, None) is None


def test_fetcher_ham_tutarlari_tasir():
    r = _merge_cross_statement_ratios({"enterpriseValue": 1.0}, {"total_revenue": 10.0, "ebitda": 4.0},
                                      {"net_debt": 2.0}, {})
    assert r["ebitda_abs"] == 4.0 and r["net_debt_abs"] == 2.0
    assert r["net_debt_to_ebitda"] == 0.5


def _bilanco(satirlar):
    import pandas as pd
    return type("T", (), {"balance_sheet": pd.DataFrame({"2025": satirlar})})()


def test_net_borc_satiri_yoksa_toplam_borc_eksi_nakitten_turer():
    from yf_fundamentals_fetch import _fetch_balance_sheet_trend
    out = _fetch_balance_sheet_trend(_bilanco({
        "Total Debt": 160.0,
        "Cash Cash Equivalents And Short Term Investments": 5120.0,
    }))
    assert out["net_debt"] == 160.0 - 5120.0


def test_net_borc_satiri_varsa_ona_dokunulmaz():
    from yf_fundamentals_fetch import _fetch_balance_sheet_trend
    out = _fetch_balance_sheet_trend(_bilanco({"Net Debt": 42.0, "Total Debt": 100.0,
                                            "Cash And Cash Equivalents": 10.0}))
    assert out["net_debt"] == 42.0
