"""C-25b: sablondan static/js'e tasinan satir-ici JS kapilarin gozunde sablonun parcasi kalir.

Sablon metni okunduktan sonra with_page_js(ad, metin) sayfanin kendi JS dosyasini
<script> blogu olarak sona ekler; satir numaralari ve muafiyet anahtarlari degismez."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_JS = {'hisse.html': 'static/js/hisse.js'}


def with_page_js(name, text, root=ROOT, read=None):
    rel = PAGE_JS.get(os.path.basename(str(name)))
    if not rel:
        return text
    if read:
        js = read(rel)
    else:
        p = os.path.join(root, rel)
        js = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
    return text + '\n<script>\n' + js + '\n</script>\n'
