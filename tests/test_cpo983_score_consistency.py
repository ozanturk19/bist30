"""CPO-983 — Puanlama tutarlılık fix (Güçlü Trend listesi vs hisse detay).

Root cause (3 Tem 2026): gucu_yuksek() route her istekte compose_score()'u
canlı yeniden hesaplıyordu ve analyze()'daki F5 AI Sentiment ±5 ayarını
atlıyordu. hisse detay sayfası ise cache'teki signal_strength'i (sentiment
dahil) gösteriyordu — aynı hisse için iki farklı sayı (Ozan 3. kez rapor,
Site Contract §20/§24).

Fix: gucu_yuksek() artık compose_score()'u tekrar çağırmıyor, doğrudan
cache'teki signal_strength alanını okuyor — tek kaynak, iki sayfa da aynı
sayıyı gösterir.

Bu testler kod tabanını statik olarak inceler (regex/AST), sunucu ayağa
kaldırmadan regresyonu yakalar.
"""
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


def test_gucu_yuksek_reads_cached_signal_strength():
    """gucu_yuksek() _mscore'u cache'teki signal_strength'ten almalı."""
    src = _read_app()
    body = _extract_function_body(src, "gucu_yuksek")
    assert body, "gucu_yuksek() bulunamadı"
    reads_cached = (
        's["_mscore"] = s.get("signal_strength")' in body or
        "s['_mscore'] = s.get('signal_strength')" in body
    )
    assert reads_cached, (
        "gucu_yuksek() _mscore'u cache'teki signal_strength alanından okumuyor — "
        "puanlama tutarlılık regresyonu (CPO-983)"
    )


def test_gucu_yuksek_does_not_recompute_compose_score():
    """gucu_yuksek() compose_score()'u canlı yeniden çağırmamalı (tek kaynak: analyze())."""
    src = _read_app()
    body = _extract_function_body(src, "gucu_yuksek")
    assert body, "gucu_yuksek() bulunamadı"
    assert "compose_score(" not in body, (
        "gucu_yuksek() compose_score()'u tekrar çağırıyor — bu, analyze()'daki "
        "F5 AI Sentiment ayarını atlayarak hisse detay sayfasından farklı bir "
        "sayı üretir (CPO-983 regresyonu)"
    )


def test_compose_score_called_only_in_analyze():
    """compose_score() tanımı hariç sadece analyze() içinde çağrılmalı (tek kanonik yazım noktası)."""
    src = _read_app()
    # Tüm 'compose_score(' çağrılarını (tanım hariç) bul, hangi fonksiyon
    # içinde olduklarını kabaca eşleştir.
    def_pos = src.find("def compose_score(")
    assert def_pos != -1, "compose_score() tanımı bulunamadı"

    call_positions = [m.start() for m in re.finditer(r"(?<!def )compose_score\(", src)]
    assert call_positions, "compose_score() hiç çağrılmıyor"

    func_starts = [(m.start(), m.group(1)) for m in re.finditer(r"\ndef (\w+)\(", src)]
    func_starts.sort()

    def _enclosing_func(pos):
        current = None
        for start, name in func_starts:
            if start < pos:
                current = name
            else:
                break
        return current

    callers = {_enclosing_func(pos) for pos in call_positions}
    assert callers == {"analyze"}, (
        f"compose_score() beklenmedik fonksiyon(lar)dan çağrılıyor: {callers - {'analyze'}} — "
        "sadece analyze() çağırmalı, diğer sayfalar cache'teki signal_strength'i okumalı "
        "(CPO-983 kanonik skor kuralı, Site Contract §24)"
    )


def test_signal_strength_includes_sentiment_adjustment():
    """analyze() içinde signal_strength F5 AI Sentiment ayarını içermeli."""
    src = _read_app()
    body = _extract_function_body(src, "analyze")
    assert body, "analyze() bulunamadı"
    assert "signal_strength = min(signal_strength + 5, 100)" in body, (
        "F5 AI Sentiment pozitif ayarı signal_strength hesaplamasından kayboldu"
    )
    assert "signal_strength = max(signal_strength - 5, 0)" in body, (
        "F5 AI Sentiment negatif ayarı signal_strength hesaplamasından kayboldu"
    )


if __name__ == "__main__":
    tests = [
        test_gucu_yuksek_reads_cached_signal_strength,
        test_gucu_yuksek_does_not_recompute_compose_score,
        test_compose_score_called_only_in_analyze,
        test_signal_strength_includes_sentiment_adjustment,
    ]
    passed = 0
    fail_names = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✓ {t.__name__}")
        except Exception as e:
            fail_names.append(t.__name__)
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{'='*65}")
    print(f"Result: {passed}/{len(tests)} passed")
    if fail_names:
        print(f"FAILED: {', '.join(fail_names)}")
        raise SystemExit(1)
    print("ALL TESTS PASSED")
