"""D-65: robots.txt — parametre tuzağı kapanır, AI arama ajanlarına Crawl-delay'siz açık grup.

Yerel (py3.9): gövde app.py kaynağından (kapı 55 ile aynı ayıklama) okunur; gruplar RFC 9309'a
göre ayrılır, eşleşme Google kuralıyla (en uzun kural kazanır, eşitlikte Allow; `*` joker, `$` son)
denenir. VPS (py3.10+): /robots.txt ucu aynı metni döner.
"""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")

PARAM = ["/haberler/bildirimler?*hisse=", "/haberler?*hisse=", "/*?*tarih=", "/*?*rutin=",
         "/tarama?", "/sektor-harita?"]
AI_ARAMA = ["OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "Perplexity-User"]


def _body():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    m = re.search(r'def robots\(\):\n    body = """(.*?)"""\n    return Response', src, re.S)
    assert m
    return m.group(1)


def _groups(body):
    groups, cur = [], None
    for ln in body.splitlines():
        s = ln.split("#", 1)[0].strip()
        if not s or ":" not in s:
            continue
        k, v = (x.strip() for x in s.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if cur is None or cur["rules"]:
                cur = {"agents": [], "rules": []}
                groups.append(cur)
            cur["agents"].append(v)
        elif k != "sitemap" and cur is not None:
            cur["rules"].append((k, v))
    return groups


def _group_for(groups, agent):
    for g in groups:
        if any(a.lower() == agent.lower() for a in g["agents"]):
            return g
    return next(g for g in groups if "*" in g["agents"])


def _match(pat, path):
    rx = "^" + "".join(".*" if c == "*" else ("$" if c == "$" and i == len(pat) - 1 else re.escape(c))
                       for i, c in enumerate(pat))
    return re.match(rx, path) is not None


def _allowed(group, path):
    best = None
    for k, v in group["rules"]:
        if k in ("allow", "disallow") and v and _match(v, path):
            cand = (len(v), k == "allow")
            if best is None or cand > best:
                best = cand
    return best is None or best[1]


def test_her_grupta_parametre_kurallari_ve_admin():
    groups = _groups(_body())
    acik = [g for g in groups if ("disallow", "/") not in g["rules"]]
    assert len(acik) == 3
    for g in acik:
        dis = {v for k, v in g["rules"] if k == "disallow"}
        assert set(PARAM) <= dis, g["agents"]
        assert "/admin/" in dis, g["agents"]


def test_ai_arama_ajanlari_crawl_delaysiz_acik_grupta():
    groups = _groups(_body())
    for a in AI_ARAMA + ["Googlebot", "Bingbot", "GPTBot", "ClaudeBot", "PerplexityBot"]:
        g = _group_for(groups, a)
        assert a in g["agents"], a                                    # `*` grubuna düşmez
        assert not any(k == "crawl-delay" for k, _ in g["rules"]), a
        assert _allowed(g, "/hisse/THYAO") and not _allowed(g, "/api/data")
    star = _group_for(groups, "BilinmeyenBot")
    assert ("crawl-delay", "5") in star["rules"]
    for kapali in ("SemrushBot", "AhrefsBot", "MJ12bot", "DotBot"):
        assert not _allowed(_group_for(groups, kapali), "/")


@pytest.mark.parametrize("agent", ["Googlebot", "OAI-SearchBot", "Twitterbot", "BilinmeyenBot"])
def test_parametreli_adresler_kapali_kanonik_adresler_acik(agent):
    g = _group_for(_groups(_body()), agent)
    for path in ("/haberler/bildirimler?hisse=THYAO", "/haberler/bildirimler?tur=temettu&hisse=THYAO",
                 "/haberler/bildirimler?tarih=2026-10-01&rutin=1", "/haberler/bildirimler?rutin=1",
                 "/haberler?hisse=THYAO", "/haberler?sayfa=2&hisse=THYAO", "/tarama?signal=AL&sort=adx",
                 "/tarama?", "/sektor-harita?renk=bp", "/bulten/arsiv?tarih=2026-10-01"):
        assert not _allowed(g, path), (agent, path)
    for path in ("/", "/haberler", "/haberler/bildirimler", "/haberler/bildirimler?tur=temettu",
                 "/haberler/bildirimler?sayfa=2", "/tarama", "/sektor-harita", "/hisse/THYAO",
                 "/hisse/THYAO/bilanco", "/hisse/THYAO/bildirim/1666965", "/bulten/2026-10-14",
                 "/sitemap.xml", "/sitemap-hisseler.xml", "/llms.txt"):
        assert _allowed(g, path), (agent, path)


@PY310
def test_robots_ucu():
    import app
    r = app.app.test_client().get("/robots.txt")
    assert r.status_code == 200 and r.mimetype == "text/plain"
    assert r.get_data(as_text=True) == _body()
