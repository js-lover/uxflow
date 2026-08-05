"""Static UX audit over the IR.

Everything here is derived from the graph -- no guessing, no invented numbers.
Findings are annotated back onto the nodes (as `_problem`) so the renderers can
colour them, and returned as a structured report.
"""

from . import ir, theme

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def audit(doc, max_depth=6):
    out, inc = {}, {}
    for n in doc["nodes"]:
        out[n["id"]] = []
        inc[n["id"]] = []
    for e in doc["edges"]:
        out[e["from"]].append(e)
        inc[e["to"]].append(e)

    starts = [n["id"] for n in doc["nodes"] if n["type"] == "start"]
    ends = {n["id"] for n in doc["nodes"] if n["type"] == "end"}
    findings = []

    # ---------------------------------------------------------------- reachability
    seen = set()
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(e["to"] for e in out[cur])

    for n in doc["nodes"]:
        nid = n["id"]
        if n["type"] == "note":
            continue

        if nid not in seen:
            n["_problem"] = "unreachable"
            findings.append(_f("unreachable", "high", nid, n,
                               "No path from any start node reaches this screen. "
                               "Either it is dead code or the entry point is missing from the flow."))
        elif not inc[nid] and n["type"] != "start":
            n["_problem"] = "orphan"
            findings.append(_f("orphan", "medium", nid, n,
                               "Nothing links to this node. Users can only arrive by deep link or by accident."))

        terminal_ok = n["type"] in ("end", "external", "note", "data")
        forward = [e for e in out[nid] if e.get("kind") != "back"]
        back = [e for e in out[nid] if e.get("kind") == "back"]
        if not forward and not back and nid not in ends and not terminal_ok:
            n["_problem"] = "deadend"
            findings.append(_f("deadend", "high", nid, n,
                               "Dead end: the user reaches this state and the flow offers no way out at all."))
        elif not forward and back and not terminal_ok and n["type"] != "modal":
            # a modal whose only exit is dismiss is fine; a screen is not
            n["_problem"] = "deadend"
            findings.append(_f("only_exit_is_back", "high", nid, n,
                               "The only way out of this screen is backwards. The user cannot make progress from here."))

    # ---------------------------------------------------------- missing error paths
    for n in doc["nodes"]:
        if n["type"] != "api":
            continue
        kinds = {e.get("kind") for e in out[n["id"]]}
        if "error" not in kinds:
            findings.append(_f("no_error_branch", "high", n["id"], n,
                               "Network call with no modelled failure branch. "
                               "Either the code swallows the error, or the flow is incomplete."))

    # ------------------------------------------------------------ decision coverage
    for n in doc["nodes"]:
        if n["type"] != "decision":
            continue
        if len([e for e in out[n["id"]] if e.get("kind") != "back"]) < 2:
            findings.append(_f("decision_single_branch", "medium", n["id"], n,
                               "Decision node with fewer than two outgoing branches -- "
                               "the alternative path is missing from the model or from the code."))

    # ------------------------------------------------------------- no way back
    for n in doc["nodes"]:
        if n["type"] not in ("screen", "modal"):
            continue
        has_back = any(e.get("kind") == "back" for e in out[n["id"]])
        tagged = "no_back_affordance" in ((n.get("annotations") or {}).get("friction") or [])
        if tagged and not has_back:
            findings.append(_f("no_back", "medium", n["id"], n,
                               "Screen offers no back or cancel affordance."))

    # --------------------------------------------------------------- friction tags
    for n in doc["nodes"]:
        for tag in (n.get("annotations") or {}).get("friction", []) or []:
            sev = "high" if tag in theme.SEVERE_FRICTION else "low"
            findings.append(_f("friction:" + tag, sev, n["id"], n,
                               theme.FRICTION_LABELS.get(tag, tag).capitalize() + "."))

    # ------------------------------------------------------------------- depth
    depth, path = _longest_happy_path(starts, out, ends)
    if depth > max_depth:
        findings.append(_f("flow_too_deep", "medium", path[-1] if path else "", None,
                           "The primary path is %d steps long (threshold %d). "
                           "Each extra step compounds drop-off." % (depth, max_depth)))

    metrics = _metrics(doc, depth, path, seen)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["node"]))
    return {"findings": findings, "metrics": metrics, "primary_path": path}


def _f(code, severity, node_id, node, message):
    return {
        "code": code, "severity": severity, "node": node_id,
        "label": (node or {}).get("label", ""),
        "source": (node or {}).get("source", ""),
        "message": message,
    }


def _longest_happy_path(starts, out, ends=None):
    """Longest forward path from a start node, preferring happy edges.

    Two reductions make this exact and linear instead of an exponential walk over
    every simple path:

      1. per-node happy preference -- a node with at least one `happy` successor
         keeps only those. That is what makes the result *the primary path*
         rather than merely the longest one;
      2. back edges (explicit `kind: back`, plus whatever cycles survive step 1)
         are removed, leaving a DAG on which longest-path is a single pass in
         topological order.

    The previous implementation enumerated simple paths under a fixed visit
    budget, so a branchy flow would exhaust the budget and silently return a
    truncated depth. Results are unchanged for graphs small enough that the old
    search completed.
    """
    adj = {}
    for nid, edges in out.items():
        forward = [e for e in edges if e.get("kind") != "back"]
        happy = [e for e in forward if e.get("kind") == "happy"]
        adj[nid] = sorted({e["to"] for e in (happy or forward)})

    back = ir.back_edges(adj, starts)
    dag = {k: [v for v in vs if (k, v) not in back] for k, vs in adj.items()}

    reachable = {s: 0 for s in starts if s in dag}
    if not reachable:
        return 0, []

    prev = {}
    for node in ir.topo_order(dag):
        if node not in reachable:
            continue
        for nxt in dag.get(node, []):
            if reachable[node] + 1 > reachable.get(nxt, -1):
                reachable[nxt] = reachable[node] + 1
                prev[nxt] = node

    end = max(sorted(reachable), key=lambda n: reachable[n])
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    return len(path) - 1, path


def _metrics(doc, depth, path, reachable):
    nodes = doc["nodes"]
    ann = [n.get("annotations") or {} for n in nodes]
    on_path = set(path)
    return {
        "nodes": len(nodes),
        "edges": len(doc["edges"]),
        "screens": sum(1 for n in nodes if n["type"] in ("screen", "modal")),
        "api_calls": sum(1 for n in nodes if n["type"] == "api"),
        "decisions": sum(1 for n in nodes if n["type"] == "decision"),
        "primary_path_steps": depth,
        "screens_on_primary_path": sum(
            1 for n in nodes if n["id"] in on_path and n["type"] in ("screen", "modal")),
        "total_taps": sum(a.get("taps", 0) for a in ann),
        "taps_on_primary_path": sum(
            (n.get("annotations") or {}).get("taps", 0) for n in nodes if n["id"] in on_path),
        "required_fields": sum(a.get("required_fields", 0) for a in ann),
        "friction_tags": sum(len(a.get("friction", []) or []) for a in ann),
        "unreachable_nodes": sum(1 for n in nodes if n["id"] not in reachable and n["type"] != "note"),
        "error_branches": sum(1 for e in doc["edges"] if e.get("kind") == "error"),
    }


# ------------------------------------------------------------------- reporting
def to_markdown(doc, report):
    m = report["metrics"]
    out = ["# UX audit -- %s" % doc["title"], ""]
    if doc.get("app", {}).get("name"):
        out.append("**App:** %s  " % doc["app"]["name"])
    if doc.get("app", {}).get("commit"):
        out.append("**Commit:** `%s`  " % doc["app"]["commit"])
    out.append("**Flow id:** `%s`  " % doc["id"])
    out.append("**IR hash:** `%s`" % ir.content_hash(doc))
    out.append("")

    out.append("## Metrics")
    out.append("")
    out.append("| metric | value |")
    out.append("| --- | ---: |")
    pretty = {
        "primary_path_steps": "Steps on the primary path",
        "screens_on_primary_path": "Screens on the primary path",
        "taps_on_primary_path": "Taps on the primary path",
        "required_fields": "Required form fields (total)",
        "screens": "Screens", "api_calls": "API calls", "decisions": "Decision points",
        "error_branches": "Modelled error branches", "friction_tags": "Friction tags",
        "unreachable_nodes": "Unreachable nodes", "nodes": "Nodes", "edges": "Edges",
        "total_taps": "Taps (total)",
    }
    for key in ["primary_path_steps", "screens_on_primary_path", "taps_on_primary_path",
                "required_fields", "screens", "api_calls", "decisions", "error_branches",
                "friction_tags", "unreachable_nodes", "nodes", "edges"]:
        out.append("| %s | %s |" % (pretty[key], m[key]))
    out.append("")

    if report["primary_path"]:
        idx = ir.index(doc)
        out.append("## Primary path")
        out.append("")
        out.append(" → ".join(idx[n]["label"] for n in report["primary_path"] if n in idx))
        out.append("")

    findings = report["findings"]
    out.append("## Findings (%d)" % len(findings))
    out.append("")
    if not findings:
        out.append("No structural problems found.")
        return "\n".join(out) + "\n"

    for sev in ("high", "medium", "low"):
        group = [f for f in findings if f["severity"] == sev]
        if not group:
            continue
        out.append("### %s (%d)" % (sev.capitalize(), len(group)))
        out.append("")
        out.append("| node | issue | detail | source |")
        out.append("| --- | --- | --- | --- |")
        for f in group:
            out.append("| %s | `%s` | %s | %s |" % (
                f["label"] or f["node"], f["code"], f["message"].replace("|", "\\|"),
                "`%s`" % f["source"] if f["source"] else ""))
        out.append("")
    return "\n".join(out) + "\n"
