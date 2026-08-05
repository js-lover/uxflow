"""Before/after comparison of two flows.

This is the feature that turns the diagrams from documentation into a design
tool: model the flow as it is today, model the flow you propose, and render the
delta. Requires stable node ids -- see ir.stable_id().
"""

import copy

from . import analyze, ir

COMPARED_FIELDS = ("label", "type", "lane", "route", "kind")


def diff(before, after):
    """Return a merged IR where every node/edge carries `_diff`, plus a summary."""
    b_idx, a_idx = ir.index(before), ir.index(after)
    merged = copy.deepcopy(after)
    merged["title"] = "%s -- before / after" % after["title"]
    merged["id"] = after["id"] + "-diff"

    summary = {"added": [], "removed": [], "changed": [], "unchanged": []}

    for n in merged["nodes"]:
        old = b_idx.get(n["id"])
        if old is None:
            n["_diff"] = "added"
            summary["added"].append(n)
            continue
        changes = [f for f in COMPARED_FIELDS if old.get(f) != n.get(f)]
        if (old.get("annotations") or {}) != (n.get("annotations") or {}):
            changes.append("annotations")
        if changes:
            n["_diff"] = "changed"
            n["_changes"] = changes
            summary["changed"].append((n, old, changes))
        else:
            n["_diff"] = "unchanged"
            summary["unchanged"].append(n)

    # removed nodes are carried over so the reader sees what disappears
    for n in before["nodes"]:
        if n["id"] not in a_idx:
            ghost = copy.deepcopy(n)
            ghost["_diff"] = "removed"
            ghost["label"] = n["label"]
            merged["nodes"].append(ghost)
            summary["removed"].append(ghost)

    merged["_index"] = {n["id"]: n for n in merged["nodes"]}

    def ekey(e):
        return (e["from"], e["to"], e.get("label", ""))

    b_edges = {ekey(e): e for e in before["edges"]}
    a_edges = {ekey(e): e for e in after["edges"]}
    for e in merged["edges"]:
        e["_diff"] = "unchanged" if ekey(e) in b_edges else "added"
    present = set(n["id"] for n in merged["nodes"])
    for k, e in b_edges.items():
        if k not in a_edges and e["from"] in present and e["to"] in present:
            ghost = copy.deepcopy(e)
            ghost["_diff"] = "removed"
            merged["edges"].append(ghost)

    return merged, summary


def to_markdown(before, after, summary):
    rb = analyze.audit(copy.deepcopy(before))
    ra = analyze.audit(copy.deepcopy(after))
    mb, ma = rb["metrics"], ra["metrics"]

    out = ["# Flow diff -- %s" % after["title"], "",
           "`%s` (before, hash %s) → `%s` (after, hash %s)"
           % (before["id"], ir.content_hash(before), after["id"], ir.content_hash(after)), ""]

    out += ["## What changed", "",
            "| | count |", "| --- | ---: |",
            "| Nodes added | %d |" % len(summary["added"]),
            "| Nodes removed | %d |" % len(summary["removed"]),
            "| Nodes changed | %d |" % len(summary["changed"]),
            "| Nodes unchanged | %d |" % len(summary["unchanged"]), ""]

    out += ["## Metric delta", "", "| metric | before | after | delta |", "| --- | ---: | ---: | ---: |"]
    keys = ["primary_path_steps", "screens_on_primary_path", "taps_on_primary_path",
            "required_fields", "screens", "api_calls", "error_branches", "friction_tags"]
    for k in keys:
        d = ma[k] - mb[k]
        arrow = "±0" if d == 0 else ("%+d" % d)
        out.append("| %s | %s | %s | %s |" % (k.replace("_", " "), mb[k], ma[k], arrow))
    out.append("")

    hb = len([f for f in rb["findings"] if f["severity"] == "high"])
    ha = len([f for f in ra["findings"] if f["severity"] == "high"])
    out += ["| high-severity findings | %d | %d | %s |" % (hb, ha, "±0" if ha == hb else "%+d" % (ha - hb)), ""]

    if summary["added"]:
        out += ["## Added", ""] + ["- **%s** (`%s`)" % (n["label"], n["id"]) for n in summary["added"]] + [""]
    if summary["removed"]:
        out += ["## Removed", ""] + ["- **%s** (`%s`)" % (n["label"], n["id"]) for n in summary["removed"]] + [""]
    if summary["changed"]:
        out += ["## Changed", ""]
        for n, old, changes in summary["changed"]:
            out.append("- **%s** (`%s`) — %s" % (n["label"], n["id"], ", ".join(changes)))
            for f in changes:
                if f == "annotations":
                    continue
                out.append("  - `%s`: %r → %r" % (f, old.get(f), n.get(f)))
        out.append("")
    return "\n".join(out) + "\n"
