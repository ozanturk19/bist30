"""D-19: static_v() içerik özeti + bp_rules bağlamı + eşik tablolarının eski davranışla eşitliği."""
import hashlib
import os
import re

import business_rules as br


def _old_adx(a):
    if a >= 40:
        return "Çok Güçlü"
    if a >= 25:
        return "Güçlü"
    if a >= 18:
        return "Orta"
    return "Zayıf"


def _old_rsi(r, signal=None):
    if r < 30:
        return "Aşırı Satım"
    if r < 45:
        return "Dip Toparlanması"
    if r < 60:
        return "Sağlıklı Momentum" if signal == "AL" else "Nötr Bölge"
    if r < 70:
        return "Trend Güçleniyor"
    if r < 80:
        return "Dikkatli"
    return "Aşırı Alım"


def test_tablo_esikleri_eski_davranisla_ayni():
    for i in range(-5, 1200):
        v = i / 10.0
        assert br.derive_adx_label(v) == _old_adx(v)
        for sig in (None, "AL", "SAT", "BEKLE"):
            assert br.derive_rsi_zone(v, sig) == _old_rsi(v, sig)
    assert br.derive_adx_label(None) == "Zayıf"
    assert br.derive_rsi_zone("x") is None


def test_tablolar_fonksiyonlarla_ayni():
    for esik, etiket in br.ADX_LABEL_BANDS:
        assert br.derive_adx_label(esik) == etiket
        assert br.derive_adx_label(esik - 0.01) != etiket
    for ust, etiket in br.RSI_ZONE_BANDS:
        assert br.derive_rsi_zone(ust - 0.01, "AL") == etiket
        assert br.derive_rsi_zone(ust, "AL") != etiket


def test_bp_rules_tablolardan_turer():
    r = br.BP_RULES
    assert r["adx_min"] == br.TREND_ADX_MIN == 25
    assert r["adx_bands"] == [[40, "Çok Güçlü"], [25, "Güçlü"], [18, "Orta"]]
    assert r["rsi_bands"][0] == [30, "Aşırı Satım"]
    assert r["ema_deadband_pct"] == br.EMA_DEADBAND_THRESHOLD_PCT
    assert r["signal_labels"] == br.SIGNAL_LABELS
    assert not br.TRADE_LANG_RE.search(repr(r))


def test_static_v_ozet_ve_guvenlik():
    import app as appmod
    got = appmod.static_v("css/tokens.css")
    m = re.fullmatch(r"/static/css/tokens\.css\?v=([0-9a-f]{8})", got)
    assert m
    with open(os.path.join(appmod.app.static_folder, "css/tokens.css"), "rb") as fh:
        assert m.group(1) == hashlib.md5(fh.read()).hexdigest()[:8]
    assert appmod.static_v("/static/css/tokens.css") == got
    assert appmod.static_v("yok/olmayan.js") == "/static/yok/olmayan.js"
    assert "?v=" not in appmod.static_v("../app.py")


def test_jinja_global_ve_baglam():
    import app as appmod
    with appmod.app.test_request_context("/"):
        out = appmod.app.jinja_env.from_string(
            "{{ static_v('bp-vocab.js') }}|{{ bp_rules.adx_min }}"
        )
        ctx = {}
        appmod.app.update_template_context(ctx)
        assert out.render(**ctx).endswith("|25")
        assert ctx["bp_rules"]["adx_min"] == 25
