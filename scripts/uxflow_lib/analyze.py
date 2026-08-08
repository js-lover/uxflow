"""Static UX audit over the IR.

Everything is derived from the graph -- no guessing, no invented numbers. Findings
are annotated back onto the nodes (as `_problem`) so the renderers can colour them,
and returned as structured records that the report layer turns into prose.

Each finding carries a stable id (`UXF-<CODE>-<node>`) so it can be suppressed.
"""

import hashlib
import re

from . import benchmarks, catalog, ir, theme

MAX_DEPTH = 6

# node -> _problem marker used by the renderers
PROBLEM_FOR = {
    "deadend": "deadend",
    "only_exit_is_back": "deadend",
    "unreachable": "unreachable",
    "orphan": "orphan",
}

# short codes for finding ids
_CODE_ABBR = {
    "deadend": "DEAD", "only_exit_is_back": "BACK", "unreachable": "UNRE",
    "orphan": "ORPH", "no_error_branch": "NOERR", "external_no_return": "EXT",
    "redirect_loop": "LOOP",
    "waiting_no_resend": "RESEND", "decision_single_branch": "BRANCH",
    "flow_too_deep": "DEEP", "missing_source": "SRC",
}


def _finding_id(code, node_id):
    abbr = _CODE_ABBR.get(code)
    if abbr is None:
        abbr = re.sub(r"[^A-Z]", "", code.replace("friction:", "").upper())[:5] or "GEN"
    tail = hashlib.sha1(("%s|%s" % (code, node_id)).encode("utf-8")).hexdigest()[:4]
    return "UXF-%s-%s" % (abbr, tail.upper())


# --------------------------------------------------------------------------- main
def audit(doc, max_depth=MAX_DEPTH, suppressed=()):
    idx = ir.index(doc)
    out, inc = {}, {}
    for n in doc["nodes"]:
        out[n["id"]] = []
        inc[n["id"]] = []
    for e in doc["edges"]:
        out[e["from"]].append(e)
        inc[e["to"]].append(e)

    starts = [n["id"] for n in doc["nodes"] if n["type"] == "start"]
    ends = {n["id"] for n in doc["nodes"] if n["type"] == "end"}
    raw = []

    reachable = _reachable(starts, out)
    _structural(doc, out, inc, ends, reachable, raw)
    _error_paths(doc, out, inc, raw)
    _loops(doc, out, idx, raw)
    _friction(doc, raw)
    _model_quality(doc, raw)

    path, path_edges = primary_path(doc, starts, ends, out)
    real_steps = sum(1 for nid in path
                     if nid in idx and idx[nid]["type"] not in ("start", "end"))
    if real_steps > max_depth and path:
        # A depth problem belongs to the flow, not to whichever node happens to be
        # last on the path -- attributing it to a node sends the reader to the wrong file.
        f = _mk("flow_too_deep", "", None,
                {"steps": real_steps, "threshold": max_depth, "label": doc["title"]})
        f["label"] = doc["title"]
        f["evidence"] = []
        raw.append(f)

    metrics = _metrics(doc, path, reachable, out, ends, starts)

    findings, muted = [], []
    for f in raw:
        (muted if f["id"] in suppressed else findings).append(f)

    for f in findings:
        marker = PROBLEM_FOR.get(f["code"])
        if marker and f["node"] in idx:
            idx[f["node"]]["_problem"] = marker

    findings.sort(key=lambda f: (catalog.SEVERITY_ORDER[f["severity"]],
                                 0 if f["confidence"] == "certain" else 1,
                                 f["node"]))
    return {
        "findings": findings,
        "suppressed": muted,
        "metrics": metrics,
        "primary_path": path,
        "primary_path_edges": path_edges,
        "info": _informational(doc),
        "benchmarks": benchmarks.evaluate(metrics),
        "headline": benchmarks.headline(metrics, findings),
    }


def _mk(code, node_id, node, fmt=None):
    entry = catalog.entry(code) or {}
    fmt = dict(fmt or {})
    fmt.setdefault("label", (node or {}).get("label", node_id))
    def fill(key):
        try:
            return (entry.get(key) or "").format(**fmt)
        except (KeyError, IndexError):
            return entry.get(key) or ""
    return {
        "id": _finding_id(code, node_id),
        "code": code,
        "title": entry.get("title", code),
        "severity": entry.get("severity", "medium"),
        "confidence": entry.get("confidence", "likely"),
        "effort": entry.get("effort", "M"),
        "node": node_id,
        "label": (node or {}).get("label", ""),
        "route": (node or {}).get("route", ""),
        "what": fill("what"),
        "impact": fill("impact"),
        "fix": fill("fix"),
        "evidence": _evidence(node),
    }


def _evidence(node):
    if not node:
        return []
    ev = []
    if node.get("source"):
        ev.append(node["source"])
    for extra in (node.get("annotations") or {}).get("evidence", []) or []:
        if extra not in ev:
            ev.append(extra)
    return ev


# ------------------------------------------------------------------- structural
def _reachable(starts, out):
    seen, stack = set(), list(starts)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(e["to"] for e in out[cur])
    return seen


def _structural(doc, out, inc, ends, reachable, raw):
    for n in doc["nodes"]:
        nid, t = n["id"], n["type"]
        if t == "note":
            continue

        if nid not in reachable:
            raw.append(_mk("unreachable", nid, n))
            continue
        if not inc[nid] and t != "start":
            raw.append(_mk("orphan", nid, n))

        terminal_ok = t in ("end", "external", "note", "data")
        forward = [e for e in out[nid] if e.get("kind") != "back"]
        back = [e for e in out[nid] if e.get("kind") == "back"]

        if not forward and not back and nid not in ends and not terminal_ok:
            raw.append(_mk("deadend", nid, n))
        elif not forward and back and t == "screen":
            # Only a full screen is a problem here. A modal you can only dismiss is
            # normal, and so is a transient state ("cancelled", "error banner") whose
            # only exit is back to where the user came from.
            raw.append(_mk("only_exit_is_back", nid, n))

        if t == "decision" and len(forward) < 2:
            raw.append(_mk("decision_single_branch", nid, n))


# ------------------------------------------------------------------ error paths
_WAIT_HINT = re.compile(
    r"(mail|e-?posta|email|link|bağlant|baglant|sms|kod|code|otp|magic)", re.I)


def _error_paths(doc, out, inc, raw):
    idx = ir.index(doc)
    for n in doc["nodes"]:
        nid, t = n["id"], n["type"]
        forward = [e for e in out[nid] if e.get("kind") != "back"]
        kinds = {e.get("kind") for e in forward}

        # 1. network call with no failure branch
        if t == "api" and "error" not in kinds:
            raw.append(_mk("no_error_branch", nid, n))

        # 2. external hand-off with no cancel/error return
        if t == "external" and forward and "error" not in kinds:
            raw.append(_mk("external_no_return", nid, n))

        # 3. waiting on something out of band with no resend
        #
        # Two guards against false positives, both learned the hard way:
        #   * the state must follow a network call. "Bağlantı kopyalandı" mentions a
        #     link but nothing was sent, so there is nothing to resend.
        #   * a resend means going *back* to whatever produced this state. An edge
        #     that merely continues the journey (the emailed link finally being
        #     opened) is not a resend -- it depends on the thing that never arrived.
        if t == "state" and _WAIT_HINT.search(n.get("label", "") + " " +
                                              ((n.get("annotations") or {}).get("note") or "")):
            producers = {e["from"] for e in inc[nid]}
            sent_by_network = any(idx.get(p, {}).get("type") == "api" for p in producers)
            targets = {e["to"] for e in forward}
            has_resend = bool(targets & producers) or any(
                e.get("kind") == "back" for e in out[nid])
            if sent_by_network and not has_resend:
                raw.append(_mk("waiting_no_resend", nid, n))


# ------------------------------------------------------------------------ loops
def _loops(doc, out, idx, raw):
    """Cycles that contain no state-changing step: the user can circle forever."""
    adj = {n["id"]: [e["to"] for e in out[n["id"]] if e.get("kind") != "back"]
           for n in doc["nodes"]}
    seen_cycles = set()

    colour, stack = {}, []

    def dfs(node):
        colour[node] = 1
        stack.append(node)
        for nxt in adj.get(node, []):
            c = colour.get(nxt, 0)
            if c == 1:
                cycle = stack[stack.index(nxt):]
                key = tuple(sorted(cycle))
                if key not in seen_cycles and _loop_is_risky(cycle, idx, adj):
                    seen_cycles.add(key)
                    labels = " → ".join(idx[c]["label"] for c in cycle if c in idx)
                    raw.append(_mk("redirect_loop", cycle[0], idx.get(cycle[0]),
                                   {"cycle": labels}))
            elif c == 0:
                dfs(nxt)
        stack.pop()
        colour[node] = 2

    for n in doc["nodes"]:
        if colour.get(n["id"], 0) == 0:
            dfs(n["id"])


def _loop_is_risky(cycle, idx, adj):
    """A loop is a trap only if the user cannot get out of it.

    Two escape hatches disqualify a cycle, and both had to be added after the
    rule fired on perfectly healthy graphs:

      * something in the cycle can change the outcome -- an action, a decision,
        a form. That is a retry loop, which is the correct design.
      * some node in the cycle leads somewhere outside it. If there is a door,
        the user is not trapped, no matter how the cycle looks.
    """
    if len(cycle) < 2:
        return False
    members = set(cycle)
    for nid in cycle:
        node = idx.get(nid) or {}
        if node.get("type") in ("action", "decision"):
            return False
        ann = node.get("annotations") or {}
        if ann.get("required_fields") or ann.get("taps"):
            return False
        if any(t not in members for t in adj.get(nid, [])):
            return False
    return True


# --------------------------------------------------------------------- friction
def _friction(doc, raw):
    for n in doc["nodes"]:
        for tag in (n.get("annotations") or {}).get("friction", []) or []:
            if tag in catalog.INFORMATIONAL:
                continue
            raw.append(_mk("friction:" + tag, n["id"], n))


def _informational(doc):
    out = []
    for n in doc["nodes"]:
        for tag in (n.get("annotations") or {}).get("friction", []) or []:
            if tag in catalog.INFORMATIONAL:
                out.append({"node": n["id"], "label": n["label"], "tag": tag,
                            "text": catalog.INFO_TEXT.get(tag, ""),
                            "source": n.get("source", "")})
    return out


def _model_quality(doc, raw):
    for n in doc["nodes"]:
        if n["type"] in ("start", "end", "note"):
            continue
        if not n.get("source"):
            raw.append(_mk("missing_source", n["id"], n))


# ---------------------------------------------------------------- primary path
def primary_path(doc, starts, ends, out):
    """The journey a first-time user actually takes. Exact, not sampled.

    Two earlier attempts were wrong in instructive ways:

    1. Following `happy` edges greedily. A guard like "already signed in? -> home"
       terminated the search after two hops, so every downstream metric described
       a path no real user walks.
    2. Enumerating simple paths under a visit budget. A wide fan-out exhausts the
       budget and the search returns a truncated answer without saying so --
       silently wrong, which is worse than obviously wrong.

    This version removes cycle-closing edges to obtain a DAG, then runs a dynamic
    program over a topological order. Longest path on a DAG is linear time and
    exact, so fan-out no longer matters.

    Scoring is lexicographic: reaching an `end` node beats everything, then the
    number of happy edges, then length. The longest *complete* journey is the one
    worth measuring.
    """
    ids = [n["id"] for n in doc["nodes"]]
    adj = {k: [e for e in out.get(k, []) if e.get("kind") != "back"] for k in ids}
    back = _cycle_edges(adj, starts, ids)
    dag = {k: [e for e in v if (k, e["to"]) not in back] for k, v in adj.items()}

    order = _topo(dag, ids)
    # best[v] = (reaches_end, happy_edges, nodes) achievable from v, plus the edge to take
    best, choice = {}, {}
    for v in reversed(order):
        terminal = (1 if v in ends else 0, 0, 1)
        cur, pick = terminal, None
        # a path may stop at v only if v is an end node or has no way forward
        if dag[v] and v not in ends:
            cur = None
        for e in dag[v]:
            sub = best.get(e["to"])
            if sub is None:
                continue
            cand = (sub[0], sub[1] + (1 if e.get("kind") == "happy" else 0), sub[2] + 1)
            if cur is None or cand > cur:
                cur, pick = cand, e
        best[v] = cur if cur is not None else terminal
        choice[v] = pick

    root = None
    for s in starts or ids:
        if root is None or best.get(s, (0, 0, 0)) > best.get(root, (0, 0, 0)):
            root = s
    if root is None:
        return [], []

    path, edges, node = [root], [], root
    guard = len(ids) + 1
    while choice.get(node) is not None and guard:
        guard -= 1
        e = choice[node]
        edges.append(e)
        node = e["to"]
        path.append(node)
    return path, edges


def _cycle_edges(adj, starts, ids):
    """Edges whose removal makes the forward graph acyclic (DFS back edges)."""
    colour = dict.fromkeys(ids, 0)
    found = set()
    roots = list(starts) + [i for i in ids if i not in starts]
    for root in roots:
        if colour[root]:
            continue
        colour[root] = 1
        stack = [(root, iter(adj[root]))]
        while stack:
            node, it = stack[-1]
            pushed = False
            for e in it:
                nxt = e["to"]
                c = colour.get(nxt, 0)
                if c == 1:
                    found.add((node, nxt))
                elif c == 0:
                    colour[nxt] = 1
                    stack.append((nxt, iter(adj[nxt])))
                    pushed = True
                    break
            if not pushed:
                colour[node] = 2
                stack.pop()
    return found


def _topo(dag, ids):
    indeg = dict.fromkeys(ids, 0)
    for k in ids:
        for e in dag[k]:
            indeg[e["to"]] += 1
    queue = [i for i in ids if indeg[i] == 0]
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for e in dag[n]:
            indeg[e["to"]] -= 1
            if indeg[e["to"]] == 0:
                queue.append(e["to"])
    order += [i for i in ids if i not in set(order)]     # safety net
    return order


def _failure_exits(doc, starts, ends, out):
    """How many distinct ways can a user end up stuck, short of the goal?"""
    terminal_ok = ("end", "external", "data", "note")
    count = 0
    for n in doc["nodes"]:
        nid = n["id"]
        if nid in ends or n["type"] in terminal_ok:
            continue
        forward = [e for e in out[nid] if e.get("kind") != "back"]
        if not forward:
            count += 1
        elif n.get("kind") == "error" and all(e["to"] == nid for e in forward):
            count += 1
    return count


# -------------------------------------------------------------------- metrics
def _metrics(doc, path, reachable, out, ends, starts):
    nodes = doc["nodes"]
    ann = [n.get("annotations") or {} for n in nodes]
    on_path = set(path)
    idx = ir.index(doc)

    api_nodes = [n for n in nodes if n["type"] == "api"]
    api_with_error = [
        n for n in api_nodes
        if any(e.get("kind") == "error" for e in out[n["id"]])]
    traceable = [n for n in nodes if n["type"] not in ("start", "end", "note")]
    with_source = [n for n in traceable if n.get("source")]

    return {
        "nodes": len(nodes),
        "edges": len(doc["edges"]),
        "screens": sum(1 for n in nodes if n["type"] in ("screen", "modal")),
        "api_calls": len(api_nodes),
        "decisions": sum(1 for n in nodes if n["type"] == "decision"),
        # A "step" is a place the user actually passes through. `start` and `end`
        # are bookkeeping markers, not steps, so they are excluded -- otherwise
        # every flow looks two steps longer than it is.
        "primary_path_steps": sum(
            1 for nid in path
            if nid in idx and idx[nid]["type"] not in ("start", "end")),
        "screens_on_primary_path": sum(
            1 for n in nodes if n["id"] in on_path and n["type"] in ("screen", "modal")),
        "total_taps": sum(a.get("taps", 0) for a in ann),
        "taps_on_primary_path": sum(
            (idx[nid].get("annotations") or {}).get("taps", 0)
            for nid in on_path if nid in idx),
        "required_fields": sum(a.get("required_fields", 0) for a in ann),
        "friction_tags": sum(
            len([t for t in (a.get("friction") or []) if t not in catalog.INFORMATIONAL])
            for a in ann),
        "unreachable_nodes": sum(
            1 for n in nodes if n["id"] not in reachable and n["type"] != "note"),
        "error_branches": sum(1 for e in doc["edges"] if e.get("kind") == "error"),
        "error_branch_coverage": int(round(
            100.0 * len(api_with_error) / len(api_nodes))) if api_nodes else 100,
        "source_coverage": int(round(
            100.0 * len(with_source) / len(traceable))) if traceable else 100,
        "failure_exits": _failure_exits(doc, starts, ends, out),
    }
