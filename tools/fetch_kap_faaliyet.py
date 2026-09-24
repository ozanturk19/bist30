#!/usr/bin/env python3
"""D-46b: kap_sirket_bilgileri.json'da faaliyet_konusu bos olan hisselerin KAP genel
sayfasindan 'Sirketin Faaliyet Konusu' alanini tamamlar. >=5 sn arayla, ilk 429'da durur.
Kullanim: python3 tools/fetch_kap_faaliyet.py [dosya]   (varsayilan repo kokundeki json)"""
import html, json, os, re, sys, time, urllib.request, urllib.error

PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kap_sirket_bilgileri.json")
MAX_LEN = 400
_RE = re.compile(r'"itemKey":"kpy41_acc2_faaliyet_konu","value":"(.*?)","disclosureIndex":\d+,"creationDate":"([^"]*)"')


def _clean(raw):
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
    s = re.sub(r"<[^>]+>", " ", s.replace('\\"', '"'))
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _trim(text):
    if len(text) <= MAX_LEN:
        return text, None
    cut = max(text.rfind(c, 0, MAX_LEN - 5) for c in ".;")
    cut = cut if cut > 120 else text.rfind(" ", 0, MAX_LEN - 5)
    return text[:cut + 1].rstrip(" ;,") + "…", "kısaltıldı"


def _is_sector_chain(text):
    # KAP bazi sirketlerde faaliyet alanina sektor zincirini yazar (buyuk harf + ' / ')
    return " / " in text and text == text.upper()


def main():
    data = json.load(open(PATH, encoding="utf-8"))
    todo = [t for t, k in data.items() if not k.get("faaliyet_konusu") and k.get("oid")
            and str(k.get("faaliyet_notu", "")).startswith("KAP genel")]
    print(len(todo), "hisse cekilecek")
    for t in todo:
        url = "https://www.kap.org.tr/tr/sirket-bilgileri/genel/" + data[t]["oid"]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            print(t, "HTTP", e.code)
            if e.code == 429:
                break
            time.sleep(5)
            continue
        except Exception as e:
            print(t, "hata", e)
            time.sleep(5)
            continue
        m = _RE.search(page.replace('\\"', '"'))
        if not m:
            data[t]["faaliyet_notu"] = "KAP sayfasında faaliyet konusu alanı bulunamadı"
            print(t, "alan yok")
        else:
            text = _clean(m.group(1))
            if re.fullmatch(r"\$[0-9a-f]{1,3}", text):
                data[t]["faaliyet_notu"] = "KAP metni akış referansı ($xx) — sonraki turda çözülecek"
                print(t, "referans", text)
            elif not text or _is_sector_chain(text):
                data[t]["faaliyet_notu"] = "KAP'ta anlamlı metin yok (yalnız sektör zinciri)"
                print(t, "sektor zinciri:", text[:60])
            else:
                text, note = _trim(text)
                data[t]["faaliyet_konusu"] = text
                data[t]["faaliyet_tarihi"] = m.group(2)[:10]
                data[t].pop("faaliyet_notu", None)
                if note:
                    data[t]["faaliyet_notu"] = note
                print(t, "OK", len(text))
        time.sleep(5)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
