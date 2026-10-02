# -*- coding: utf-8 -*-
"""app.py'den route -> template eslemesini cok-satirli render_template GUVENLI cikar."""
import re
s = open('app.py', encoding='utf-8').read()
lines = s.splitlines()
route_re = re.compile(r"@app\.route\(\s*['\"]([^'\"]+)['\"]")
rt_re = re.compile(r"render_template\(\s*['\"]([a-z0-9_]+\.html)", re.S)

# her fonksiyon blogunu tara: @app.route(...) ... def f(): ... render_template('x.html'
out = {}
i = 0
while i < len(lines):
    m = route_re.search(lines[i])
    if m:
        path = m.group(1)
        # ayni fonksiyona ait ek route dekoratorlerini topla
        paths = [path]
        j = i + 1
        while j < len(lines) and route_re.search(lines[j]):
            paths.append(route_re.search(lines[j]).group(1)); j += 1
        # bir sonraki @app.route'a kadar olan govdeyi al
        k = j
        while k < len(lines) and not route_re.search(lines[k]):
            k += 1
        body = "\n".join(lines[j:k])
        for t in rt_re.findall(body):
            out.setdefault(t, []).extend(paths)
        i = j
    else:
        i += 1

for t in sorted(out):
    print("%-26s %s" % (t, " | ".join(dict.fromkeys(out[t]))))
