#!/usr/bin/env python3
"""DEV-2 FAZ2 kabuk denetimi — CANLI RENDER edilmis HTML uzerinden.

Kaynak grep'i degil render ciktisini olcer: sablondaki `{% include %}` ve
`{% if %}` dallari kaynak sayimini yaniltir. Ayrica CSS kural sayimi ile
DOM eleman sayimini AYIRIR — `.skip-link` bir kez CSS'te bir kez markup'ta
gecebilir; ikisini toplayan sayac "var" der ama eleman olmayabilir.
"""
import html.parser
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = "http://127.0.0.1:8003"
UA_M = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
OUT = Path("/tmp/dev2base")


class Shell(html.parser.HTMLParser):
    """DOM eksenli olcum: <style> icerigini markup'tan ayirir."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_style = 0
        self.css = []
        self.skip_anchors = []      # (href, classes)
        self.ids = {}               # id -> adet
        self.mbnav = 0              # class'inda mobile-bottom-nav olan ELEMAN
        self.main = 0
        self.bell = []              # zil butonu -> hedef
        self.first_focusable = None
        self.body_started = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "style":
            self.in_style += 1
        if tag == "body":
            self.body_started = True
        if tag == "main":
            self.main += 1
        if "id" in a:
            self.ids[a["id"]] = self.ids.get(a["id"], 0) + 1
        if "mobile-bottom-nav" in cls:
            self.mbnav += 1
        if tag == "a" and "skip-link" in cls:
            self.skip_anchors.append((a.get("href", ""), " ".join(cls)))
        # body'deki ilk odaklanabilir eleman (skip-link ILK olmali)
        if (self.body_started and self.first_focusable is None
                and (tag in ("a", "button", "input", "select", "textarea")
                     or a.get("tabindex", "").lstrip("-").isdigit())):
            self.first_focusable = (tag, a.get("class", ""), a.get("href", ""),
                                    a.get("id", ""), a.get("aria-label", ""))
        # zil / bildirim butonu
        lbl = (a.get("aria-label", "") + " " + a.get("onclick", "")
               + " " + a.get("data-target", ""))
        if "mbn" in lbl.lower() or "bildirim" in lbl.lower() or "🔔" in lbl:
            self.bell.append({"tag": tag, "onclick": a.get("onclick", ""),
                              "aria": a.get("aria-label", ""), "cls": " ".join(cls)})

    def handle_endtag(self, tag):
        if tag == "style" and self.in_style:
            self.in_style -= 1

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)


def fetch(url, mobile=True):
    ua = UA_M if mobile else "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120 Safari/537.36"
    p = subprocess.run(
        ["curl", "-s", "-m", "25", "-w", "\n@@%{http_code}", "-A", ua, BASE + url],
        capture_output=True, text=True)
    body = p.stdout
    code = "000"
    if "\n@@" in body:
        body, code = body.rsplit("\n@@", 1)
    return code.strip(), body


def main():
    OUT.mkdir(exist_ok=True)
    routes = []
    for line in Path("/tmp/dev2base/routes.tsv").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            routes.append(tuple(parts))
    routes.append(("404.html", "<errorhandler>", "/bu-rota-yok-dev2"))

    rows = []
    for tpl, rule, url in routes:
        code, body = fetch(url)
        (OUT / (tpl + ".live")).write_text(body, encoding="utf-8")
        s = Shell()
        try:
            s.feed(body)
        except Exception as e:                              # noqa: BLE001
            print(f"PARSE-FAIL {tpl}: {e}", file=sys.stderr)
        css = "\n".join(s.css)
        # skip-link CSS kurali VAR mi (yalniz secici olarak)
        has_css = bool(re.search(r"\.skip-link\b", css))
        has_focus = bool(re.search(r"\.skip-link[^{}]*:focus", css)) or bool(
            re.search(r"\.skip-link:focus", css))
        anchors = s.skip_anchors
        tgt_ok = None
        if anchors:
            href = anchors[0][0]
            if href.startswith("#"):
                tgt_ok = s.ids.get(href[1:], 0)
        dup_ids = {k: v for k, v in s.ids.items() if v > 1}
        rows.append({
            "tpl": tpl, "url": url, "http": code, "bytes": len(body),
            "skip_a": len(anchors),
            "skip_href": anchors[0][0] if anchors else "",
            "skip_css": has_css, "skip_focus_css": has_focus,
            "skip_target_ids": tgt_ok,
            "skip_is_first_focusable": bool(
                anchors and s.first_focusable
                and "skip-link" in (s.first_focusable[1] or "")),
            "first_focusable": s.first_focusable,
            "mbnav_dom": s.mbnav,
            "mbnSheet": s.ids.get("mbnSheet", 0),
            "main": s.main,
            "dup_ids": dup_ids,
            "bell": s.bell,
        })

    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
