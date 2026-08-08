#!/usr/bin/env python3
"""Pre-deploy Jinja kapisi — templates/ derlenebilir mi VE miras zinciri cozulur mu.

Neden ayri dosya: eskiden bu kontrol pre-deploy-check.sh icinde `python3 -c "..."`
olarak gomuluydu; ic ice tirnak kacislari kirilgandi.

Neden yeniden yazildi (T2.2): sablonlar artik {% extends '_base.html' %} ile
ebeveyne bagli. jinja2 get_template() YALNIZ cocugu derler, ebeveyni RENDER
aninda yukler. Olculdu: _base.html silinmisken eski kapi "GECTI" diyordu,
gercek render ise TemplateNotFound veriyordu -> kapi kordu ve 27 sayfa 500
dondurecek bir deploy'a izin verirdi.

Iki duzeltme:
  (a) payda 5 sabit isim degil, templates/*.html'den TURETILIYOR
  (b) her {% extends %} / {% include %} HEDEFI ayrica cozuluyor

Ozel filtreler Flask tarafindan calisma aninda kayit ediliyor; ciplak ortamda
yoklar ve SAHTE KIRMIZI uretirler. Adlari app.py'den turetiyoruz — elle tasinan
liste bayatlar, bu kendiliginden ogrenir.

Exit 0: hepsi temiz / Exit 1: en az bir sablon derlenemedi veya hedef cozulemedi
"""
import re
import sys
from pathlib import Path

import jinja2
from jinja2 import nodes

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
APP = ROOT / "app.py"

env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TPL)))

names = re.findall(r"@app\.template_filter\(\s*['\"]([A-Za-z0-9_]+)['\"]",
                   APP.read_text(encoding="utf-8"))
for n in names:
    env.filters[n] = lambda v, *a, **k: v
print("  app.py ozel filtresi kayitli: %d (%s)" % (len(names), ",".join(sorted(names))))

ok = True
n_tpl = n_ref = 0
for f in sorted(TPL.glob("*.html")):
    n_tpl += 1
    try:
        ast = env.parse(f.read_text(encoding="utf-8"), filename=f.name)
        env.get_template(f.name)
    except Exception as x:
        print("  HATA %s: %s" % (f.name, x))
        ok = False
        continue
    for node in ast.find_all((nodes.Extends, nodes.Include)):
        tpl = getattr(node, "template", None)
        if isinstance(tpl, nodes.Const) and isinstance(tpl.value, str):
            n_ref += 1
            try:
                env.get_template(tpl.value)
            except Exception as x:
                print("  HATA %s -> %s: %s" % (f.name, tpl.value, x))
                ok = False

print("  %d sablon derlendi, %d extends/include hedefi cozuldu" % (n_tpl, n_ref))
sys.exit(0 if ok else 1)
