"""D-P1-2210-7 kalan: `_load_macro_from_disk()` her 90s'de bir (web worker başına,
non-leader worker'lar dahil) logger.info basıyordu → journald'de günde ~21 bin
INFO satırı (gerçek uyarıyı gömen gürültünün büyük kısmı). Davranış değişmiyor,
yalnız log seviyesi INFO→DEBUG (kök logger INFO'da kurulu, DEBUG basılmaz)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_load_macro_from_disk_logs_at_debug_not_info():
    with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
        src = f.read()
    start = src.index("def _load_macro_from_disk():")
    end = src.index("\ndef ", start + 1)
    body = src[start:end]
    assert 'logger.info("_load_macro_from_disk' not in body
    assert 'logger.debug("_load_macro_from_disk' in body
