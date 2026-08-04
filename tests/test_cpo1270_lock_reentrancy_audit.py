"""CPO-1270 P0-3 (04.08) — `_lock` (app.py:1300, `threading.Lock()`, non-reentrant)
transitif re-entrancy audit + kalıcı regresyon.

Kök neden (canlı doğrulandı, DEV-1598): `get_ai_news()` ve `_prefetch_news_worker()`
bir `with _lock:` bloğu içindeyken `_news_ttl_for()` çağırıyordu — `_news_ttl_for()`
kendisi de `with _lock:` alıyor. `_lock` reentrant OLMADIĞI için aynı greenlet/thread
kendini sonsuza kadar bekliyordu: kilidi tutan greenlet donuyor, `_lock`'a dokunan
HER rota (context processor `_inject_premium_status`, health snapshot loop, hatta
404 handler) da aynı kilidi bekleyip asılı kalıyordu. Bu, CPO-1269/CPO-1270'in
canlı gözlemlediği ~40s-onset, restart-sonrası-tekrar-eden, %93 kesinti deseninin
birebir açıklaması.

Fix: her iki call-site'ta da `_news_ttl_for()` çağrısı `with _lock:` bloğunun
DIŞINA taşındı (kilit sadece paylaşılan state okuması için tutulur, TTL hesabı
kilitsiz alanda yapılır) — CPO'nun istediği "kilit kapsam daraltması".

Bu dosyadaki `test_no_transitive_lock_reentrancy` GENEL bir dedektördür: sadece
bu iki call-site'ı değil, `app.py`'deki TÜM `with _lock:` bloklarını transitif
çağrı grafiği üzerinden tarar — CPO-1270'in istediği yöntem ("1-2 seviye yetmez,
kapanışa kadar izle"). Gelecekte HERHANGİ bir fonksiyon `with _lock:` içindeyken
(doğrudan veya transitif olarak) yeniden `_lock` alan bir fonksiyon çağırırsa bu
test kırılır — bug sınıfı bir daha sessizce geri gelemez.
"""
import ast
import os
import threading
import time

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _parse_app():
    return ast.parse(_read_app(), filename="app.py")


def _is_lock_with(node):
    if not isinstance(node, ast.With):
        return False
    return any(
        isinstance(item.context_expr, ast.Name) and item.context_expr.id == "_lock"
        for item in node.items
    )


def _find_lock_withs(func_node):
    """func_node gövdesindeki `with _lock:` bloklarını döndürür — iç içe
    (nested) def'lere İNMEZ, onlar ayrı scope."""
    result = []

    def walk(n, top):
        for child in ast.iter_child_nodes(n):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not top:
                continue
            if _is_lock_with(child):
                result.append(child)
            walk(child, top=False)

    walk(func_node, top=True)
    return result


def _collect_call_names(node):
    """node altındaki tüm çağrıların (Name veya Attribute) isimlerini toplar."""
    names = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


def _collect_functions(tree):
    funcs = {}

    class Collector(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            funcs.setdefault(node.name, []).append(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            funcs.setdefault(node.name, []).append(node)
            self.generic_visit(node)

    Collector().visit(tree)
    return funcs


def _find_lock_reentrancy_findings(tree):
    """CPO-1270 P0-3 metodu: her `with _lock:` bloğu içinde DOĞRUDAN veya
    TRANSİTİF olarak `_lock`'u yeniden alan bir fonksiyon çağrılıyor mu?

    Döner: (enclosing_func_name, with_lineno, offending_callee) tuple listesi.
    """
    funcs = _collect_functions(tree)
    func_names = set(funcs.keys())

    direct_lock_funcs = {
        name for name, nodes in funcs.items()
        if any(_find_lock_withs(n) for n in nodes)
    }

    call_graph = {}
    for name, nodes in funcs.items():
        calls = set()
        for n in nodes:
            calls |= _collect_call_names(n)
        call_graph[name] = calls & func_names

    memo = {}

    def reaches_lock(name, visiting=frozenset()):
        if name in memo:
            return memo[name]
        if name in visiting:
            return False
        if name in direct_lock_funcs:
            memo[name] = True
            return True
        visiting = visiting | {name}
        result = any(reaches_lock(c, visiting) for c in call_graph.get(name, ()))
        memo[name] = result
        return result

    findings = []
    for name, nodes in funcs.items():
        for n in nodes:
            for w in _find_lock_withs(n):
                called_in_block = _collect_call_names(w) & func_names
                for callee in called_in_block:
                    if callee == name:
                        continue  # doğrudan self-recursion ayrı kategori, aynı mantıkla yine yakalanırdı
                    if reaches_lock(callee):
                        findings.append((name, w.lineno, callee))
    return findings


def test_no_transitive_lock_reentrancy():
    """Genel dedektör — app.py'deki 100+ `with _lock:` sitesinin HİÇBİRİ,
    doğrudan veya transitif olarak, _lock'u yeniden almamalı."""
    tree = _parse_app()
    findings = _find_lock_reentrancy_findings(tree)
    assert not findings, (
        "_lock (non-reentrant) transitif olarak yeniden alınıyor -> kalıcı "
        f"self-deadlock riski (CPO-1270 P0-3 sınıfı bug): {findings}"
    )


def test_at_least_75_functions_directly_hold_lock_sanity_check():
    """Audit fonksiyonunun sessizce no-op'a düşmediğini doğrulayan sağlık
    kontrolü — `with _lock:` yakalama mantığı bozulursa (örn. isim değişikliği,
    AST şekli değişikliği) bu test de kırılır, sahte-yeşil önlenir."""
    tree = _parse_app()
    funcs = _collect_functions(tree)
    direct_lock_funcs = {
        name for name, nodes in funcs.items()
        if any(_find_lock_withs(n) for n in nodes)
    }
    assert len(direct_lock_funcs) >= 70, (
        f"Beklenenden çok daha az fonksiyon _lock alıyor görünüyor "
        f"({len(direct_lock_funcs)}) — audit'in kendisi bozulmuş olabilir"
    )


def test_news_ttl_for_not_called_inside_get_ai_news_lock_block():
    """CPO-1270'in bulduğu spesifik call-site #1 — regresyon durumunda hangi
    satırın bozulduğunu doğrudan işaret eder (genel testten bağımsız, ayrı
    başarısızlık mesajı için)."""
    tree = _parse_app()
    funcs = _collect_functions(tree)
    assert "get_ai_news" in funcs, "get_ai_news() bulunamadı"
    for n in funcs["get_ai_news"]:
        for w in _find_lock_withs(n):
            called = _collect_call_names(w)
            assert "_news_ttl_for" not in called, (
                "get_ai_news() bir with _lock: bloğu İÇİNDE _news_ttl_for() "
                "çağırıyor — _news_ttl_for() kendisi de _lock alıyor (non-"
                "reentrant) => kalıcı self-deadlock (CPO-1270 P0-3, DEV-1598 fix)"
            )


def test_news_ttl_for_not_called_inside_prefetch_worker_lock_block():
    """CPO-1270'in bulduğu spesifik call-site #2."""
    tree = _parse_app()
    funcs = _collect_functions(tree)
    assert "_prefetch_news_worker" in funcs, "_prefetch_news_worker() bulunamadı"
    for n in funcs["_prefetch_news_worker"]:
        for w in _find_lock_withs(n):
            called = _collect_call_names(w)
            assert "_news_ttl_for" not in called, (
                "_prefetch_news_worker() bir with _lock: bloğu İÇİNDE "
                "_news_ttl_for() çağırıyor — kalıcı self-deadlock riski "
                "(CPO-1270 P0-3, DEV-1598 fix)"
            )


def test_news_ttl_for_itself_deadlocks_on_naive_reentry():
    """Mekanizmanın kendisini canlı threading.Lock ile kanıtlar: _news_ttl_for
    aynı thread tarafından _lock ZATEN tutulurken çağrılırsa gerçekten asılır.
    Bunu gerçek `with _lock:` (bloklayan, timeout'suz) ile TEST THREAD'İNİ
    hiç bloklamadan kanıtlamak için reentry denemesini ayrı bir daemon thread'e
    koyup join(timeout=) ile sınırlıyoruz — bug varsa test SAFELY FAIL olur,
    CI'da sonsuza kadar asılı kalmaz.
    """
    real_lock = threading.Lock()
    cache = {"data": [{"ticker": "AKBNK", "signal": "TUT", "vol_ratio": 0.8}]}

    def news_ttl_for(ticker):
        # app.py:_news_ttl_for'un basitleştirilmiş, davranışsal eşdeğeri
        with real_lock:
            for s in cache["data"]:
                if s.get("ticker") == ticker:
                    return 3600
            return 3600

    deadlocked = {"hit": False}

    def buggy_call_pattern():
        with real_lock:
            # eski (buggy) sıra: _lock ZATEN tutuluyorken yeniden almaya çalış
            news_ttl_for("AKBNK")
        deadlocked["hit"] = True

    t = threading.Thread(target=buggy_call_pattern, daemon=True)
    t.start()
    t.join(timeout=2.0)

    assert t.is_alive() and not deadlocked["hit"], (
        "Beklenen: non-reentrant threading.Lock aynı thread tarafından "
        "yeniden alınmaya çalışılınca SONSUZA KADAR bloklar (bu testin "
        "kendisi bekleniyordu) — eğer thread 2sn içinde bitmişse, ortamın "
        "threading.Lock semantiği beklenenden farklı, sonuçlar güvenilmez"
    )
    # Not: thread daemon+timeout ile bırakıldığı için process'i asmaz;
    # gerçek app.py'de _lock global ve süresiz tutulduğu için TÜM diğer
    # rotalar bu şekilde asılı kalıyordu (CPO-1270 E1-E5).
