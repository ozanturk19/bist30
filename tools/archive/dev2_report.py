#!/usr/bin/env python3
import json
import sys

rows = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dev2base/audit.json"))
hdr = ("sablon", "HTTP", "skipA", "css", "focus", "hedef", "ilk", "nav", "sheet", "main")
print("%-26s %-5s %-5s %-4s %-5s %-5s %-4s %-4s %-5s %-4s %s" % (*hdr, "dup_ids(ilk3)"))
for r in rows:
    print("%-26s %-5s %-5s %-4s %-5s %-5s %-4s %-4s %-5s %-4s %s" % (
        r["tpl"], r["http"], r["skip_a"], str(r["skip_css"])[0],
        str(r["skip_focus_css"])[0], str(r["skip_target_ids"]),
        str(r["skip_is_first_focusable"])[0], r["mbnav_dom"], r["mbnSheet"],
        r["main"], list(r["dup_ids"].items())[:3]))

n = len(rows)
print("\nPAYDA = %d" % n)


def c(f):
    return sum(1 for r in rows if f(r))


print("HTTP 200                  : %d/%d" % (c(lambda r: r["http"] == "200"), n))
print("skip-link ANCHOR (DOM)    : %d/%d" % (c(lambda r: r["skip_a"] > 0), n))
print("skip-link CSS kurali      : %d/%d" % (c(lambda r: r["skip_css"]), n))
print("skip-link :focus kurali   : %d/%d" % (c(lambda r: r["skip_focus_css"]), n))
print("hedef id GERCEKTEN var    : %d/%d" % (c(lambda r: r["skip_target_ids"] == 1), n))
print("skip-link ILK odaklanabilir: %d/%d" % (c(lambda r: r["skip_is_first_focusable"]), n))
print("<main> etiketi var        : %d/%d" % (c(lambda r: r["main"] > 0), n))
print()
print("ANCHOR var ama CSS YOK    :", [r["tpl"] for r in rows if r["skip_a"] > 0 and not r["skip_css"]])
print("ANCHOR var HEDEF YOK      :", [(r["tpl"], r["skip_href"], r["skip_target_ids"])
                                      for r in rows if r["skip_a"] > 0 and r["skip_target_ids"] != 1])
print("skip href dagilimi        :", sorted({r["skip_href"] for r in rows if r["skip_a"]}))
print()
print("mbnav DOM >1 (CIFT BAR)   :", [(r["tpl"], r["mbnav_dom"]) for r in rows if r["mbnav_dom"] > 1])
print("mbnav DOM ==0 (BAR YOK)   :", [r["tpl"] for r in rows if r["mbnav_dom"] == 0])
print("mbnSheet id >1 (CIFT ID)  :", [(r["tpl"], r["mbnSheet"]) for r in rows if r["mbnSheet"] > 1])
print("mbnSheet id ==0           :", [r["tpl"] for r in rows if r["mbnSheet"] == 0])
print("HERHANGI dup id tasiyan   : %d/%d" % (c(lambda r: r["dup_ids"]), n))
