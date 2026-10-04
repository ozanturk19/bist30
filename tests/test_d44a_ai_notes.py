"""D-44a: AI Analist Notu pilotu doğrulayıcı/biçimlendirme birim testleri -- ağ yok.

build_facts() canlı siteye HTTP çeker, bu dosyada test edilmiyor (manuel pilot
koşusuyla doğrulandı: THYAO/GARAN/TUPRS/BIMAS/ASELS, bkz. plans/2026-09-23-denetim/ai-pilot.md).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import ai_notes as an  # noqa: E402

FACTS = [
    {"id": "F1", "t": "Hasılat değişim", "v": "−%21,7"},
    {"id": "F2", "t": "Net kâr değişim", "v": "%23,1"},
    {"id": "F3", "t": "Trend durumu", "v": "Yatay"},
]


def _note(text, facts_used):
    return json.dumps({"note": text, "facts_used": facts_used, "lang": "tr"})


def test_validate_note_accepts_fact_ids_and_renders():
    raw = _note("Hasılat geriledi ({F1}); net kâr arttı ({F2}). Trend durumu {F3}.", ["F1", "F2", "F3"])
    ok, rendered, reason = an.validate_note(raw, FACTS)
    assert ok is True and reason is None
    assert rendered == "Hasılat geriledi (−%21,7); net kâr arttı (%23,1). Trend durumu Yatay."


def test_validate_note_rejects_bare_number():
    raw = _note("Hasılat %21,7 geriledi.", ["F1"])
    ok, rendered, reason = an.validate_note(raw, FACTS)
    assert ok is False and rendered is None and "çıplak rakam" in reason


def test_validate_note_rejects_banned_language():
    raw = _note("Bu hisseyi almalısınız, fırsat ({F1}).", ["F1"])
    ok, _, reason = an.validate_note(raw, FACTS)
    assert ok is False and "yasak dil" in reason


def test_validate_note_rejects_unknown_fact_id():
    raw = _note("Değer {F9} oldu.", ["F9"])
    ok, _, reason = an.validate_note(raw, FACTS)
    assert ok is False and "olgu kümesinin dışında" in reason


def test_validate_note_rejects_facts_used_not_subset():
    raw = _note("Hasılat geriledi ({F1}).", ["F1", "F9"])
    ok, _, reason = an.validate_note(raw, FACTS)
    assert ok is False and "olgu kümesinin dışında" in reason


def test_validate_note_allows_date_digits():
    raw = _note("23 Eylül kapanışında hasılat geriledi ({F1}).", ["F1"])
    ok, rendered, reason = an.validate_note(raw, FACTS)
    assert ok is True and reason is None
    assert "23 Eylül" in rendered


def test_validate_note_rejects_over_length():
    long_note = "Hasılat geriledi ({F1}). " + ("Çok uzun bir açıklama metni burada tekrar ediyor. " * 10)
    raw = _note(long_note.strip(), ["F1"])
    ok, _, reason = an.validate_note(raw, FACTS)
    assert ok is False and "uzunluk" in reason


def test_validate_note_rejects_invalid_json():
    ok, rendered, reason = an.validate_note("bu JSON değil", FACTS)
    assert ok is False and rendered is None and "JSON ayrıştırılamadı" in reason


def test_tr_pct_sign_before_percent():
    assert an._tr_pct(-21.73) == "−%21,7"
    assert an._tr_pct(62.5) == "%62,5"
    assert an._tr_pct(None) is None


def test_tr_num_decimal_comma():
    assert an._tr_num(2.68, 2) == "2,68"
    assert an._tr_num(None) is None


def test_signal_labels_match_app_py_constant():
    # app.py:152 SIGNAL_LABELS ile aynı sabit -- kanon dil (D-47/O29), AL/SAT eski kod burada da üretilmez.
    assert an.SIGNAL_LABELS == {"AL": "Güçlü Trend", "SAT": "Trend Bozuldu", "BEKLE": "Yatay"}


def test_facts_block_is_valid_jsonlines():
    block = an.facts_block(FACTS)
    lines = block.splitlines()
    assert len(lines) == len(FACTS)
    for line, fact in zip(lines, FACTS):
        assert json.loads(line) == fact


# D-44a kalan #1 — bildirim özeti (tarifi §1: 1 cümle, ≤180 karakter). build_bildirim_facts()
# canlı siteye HTTP çeker, bu dosyada test edilmiyor (build_facts ile aynı sözleşme); yalnız
# paylaşılan validate_note()'un max_len parametresi ve bildirim sistem metni test edilir.
BILDIRIM_FACTS = [
    {"id": "F1", "t": "Bildirilen tutar", "v": "1,23 milyar €"},
    {"id": "F2", "t": "Tutarın 2025 hasılatına oranı", "v": "yaklaşık %38"},
]


def test_validate_note_accepts_bildirim_length_under_180():
    raw = _note("Aselsan, Roketsan ile tedarik sözleşmesi imzaladı ({F1}); tutar {F2}.", ["F1", "F2"])
    ok, rendered, reason = an.validate_note(raw, BILDIRIM_FACTS, max_len=180)
    assert ok is True and reason is None
    assert len(rendered) <= 180


def test_validate_note_rejects_bildirim_over_180_but_under_420():
    note = "Aselsan, Roketsan ile imzaladığı sözleşme kapsamında savunma sanayii alanında " \
           "uzun bir tedarik ve teknoloji aktarımı anlaşması yürüteceğini, bu sürecin yıllar " \
           "sürecek kapsamlı bir ortaklığa dönüşeceğini açıkladı ({F1})."
    raw = _note(note, ["F1"])
    ok_420, _, _ = an.validate_note(raw, BILDIRIM_FACTS, max_len=420)
    ok_180, _, reason_180 = an.validate_note(raw, BILDIRIM_FACTS, max_len=180)
    assert ok_420 is True
    assert ok_180 is False and "uzunluk" in reason_180


def test_bildirim_system_prompt_forbids_same_banned_language():
    assert "AL / SAT / BEKLE" in an.SYSTEM_PROMPT_BILDIRIM
    assert "180 karakter" in an.SYSTEM_PROMPT_BILDIRIM
