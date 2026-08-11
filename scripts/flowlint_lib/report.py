"""The report: one Markdown file per flow, and the only file most readers open.

Two audiences, one document. A person skims the summary and the action list and
stops there, so those come first and are written in plain language. An agent needs
structured facts, so the document ends with a compact machine block instead of
forcing anything to parse prose.

Everything in between is ordered by how likely it is to be read: what to do, the
diagram for context, the numbers, then the detail behind each finding.
"""

import json

from . import benchmarks, catalog, ir, mermaid

BADGE = {"good": "✓", "warn": "!", "bad": "✗", "info": "·"}
SEV_BADGE = {"high": "🔴", "medium": "🟠", "low": "🟡"}


def render(doc, report, embed_diagram=True):
    o = []
    _header(o, doc, report)
    _summary(o, report)
    _actions(o, report)
    if embed_diagram:
        _diagram(o, doc)
    _entry_points(o, doc)
    _journey(o, doc, report)
    _metrics(o, report)
    _findings(o, report)
    _informational(o, report)
    _suppressed(o, report)
    _method(o, doc, report)
    _machine(o, doc, report)
    return "\n".join(o).rstrip() + "\n"


# ------------------------------------------------------------------- sections
def _header(o, doc, report):
    o.append("# %s — flow report" % doc["title"])
    o.append("")
    app = doc.get("app") or {}
    bits = []
    if app.get("name"):
        bits.append("**App:** %s" % app["name"])
    if app.get("stack"):
        bits.append("**Stack:** `%s`" % app["stack"])
    if app.get("commit"):
        bits.append("**Commit:** `%s`" % app["commit"])
    bits.append("**Flow:** `%s`" % doc["id"])
    o.append(" · ".join(bits))
    if doc.get("description"):
        o.append("")
        o.append("> %s" % doc["description"])
    o.append("")


def _summary(o, report):
    m, findings = report["metrics"], report["findings"]
    o.append("## Summary")
    o.append("")
    o.append(report["headline"])
    o.append("")

    counts = {s: len([f for f in findings if f["severity"] == s])
              for s in ("high", "medium", "low")}
    o.append("| | | |")
    o.append("| --- | ---: | --- |")
    o.append("| %s **High** | %d | affects users directly |" % (SEV_BADGE["high"], counts["high"]))
    o.append("| %s Medium | %d | costs conversion |" % (SEV_BADGE["medium"], counts["medium"]))
    o.append("| %s Low | %d | polish |" % (SEV_BADGE["low"], counts["low"]))
    o.append("| | | |")
    o.append("| Primary path | %d steps | places the user passes through |"
             % m["primary_path_steps"])
    o.append("| Stuck | %d | ways to end up going nowhere |" % m["failure_exits"])
    o.append("")


def _actions(o, report):
    findings = report["findings"]
    o.append("## What to do")
    o.append("")
    if not findings:
        o.append("Nothing to act on. No screen traps the user, no network call is "
                 "missing its failure branch, no screen is unreachable.")
        o.append("")
        return
    o.append("Ordered by severity, confidence and effort. Working top to bottom gives "
             "the fastest improvement, and each row is ready to become a ticket.")
    o.append("")
    o.append("| # | what | where | effort | detail |")
    o.append("| ---: | --- | --- | --- | --- |")
    for i, f in enumerate(findings, 1):
        where = f["label"] or f["node"] or "whole flow"
        src = "`%s`" % f["evidence"][0] if f["evidence"] else "—"
        o.append("| %d | %s %s | %s<br>%s | %s | [%s](#%s) |"
                 % (i, SEV_BADGE[f["severity"]], f["title"], _esc(where), src,
                    f["effort"], f["id"], _anchor(f["id"])))
    o.append("")


def _diagram(o, doc):
    o.append("## The flow")
    o.append("")
    o.append("```mermaid")
    o.append(mermaid.render(doc, annotated=False, with_source=False, header=False).rstrip())
    o.append("```")
    o.append("")
    o.append("*Editable version: `%s.drawio` — open it in "
             "[diagrams.net](https://app.diagrams.net). The second tab carries the "
             "annotations.*" % doc["id"])
    o.append("")


def _entry_points(o, doc):
    starts = [n for n in doc["nodes"] if n["type"] == "start"]
    if len(starts) < 2:
        return
    o.append("## Entry points")
    o.append("")
    o.append("This flow is entered from %d separate places. The primary path below "
             "follows only one of them; the others appear in the diagram." % len(starts))
    o.append("")
    for n in starts:
        src = "  `%s`" % n["source"] if n.get("source") else ""
        o.append("- **%s**%s" % (n["label"], src))
    o.append("")


def _journey(o, doc, report):
    path = report["primary_path"]
    if not path:
        return
    idx = ir.index(doc)
    o.append("## Primary path")
    o.append("")
    o.append("The longest complete journey a user takes to reach the goal — %d steps:"
             % report["metrics"]["primary_path_steps"])
    o.append("")
    step = 0
    for nid in path:
        node = idx.get(nid)
        if not node:
            continue
        if node["type"] in ("start", "end"):
            o.append("- *%s* — %s" % (
                "entry" if node["type"] == "start" else "goal", node["label"]))
            continue
        step += 1
        ann = node.get("annotations") or {}
        extra = []
        if ann.get("taps"):
            extra.append("%d tap%s" % (ann["taps"], "" if ann["taps"] == 1 else "s"))
        if ann.get("required_fields"):
            extra.append("%d required field%s" % (
                ann["required_fields"], "" if ann["required_fields"] == 1 else "s"))
        if ann.get("wait"):
            extra.append("waits")
        suffix = "  — %s" % ", ".join(extra) if extra else ""
        o.append("%d. **%s**%s" % (step, node["label"], suffix))
    o.append("")


def _metrics(o, report):
    o.append("## Metrics")
    o.append("")
    o.append("| | metric | value | reading |")
    o.append("| :-: | --- | ---: | --- |")
    for b in report["benchmarks"]:
        if b["verdict"] == "info":
            continue
        o.append("| %s | %s | %s%s | %s |"
                 % (BADGE[b["verdict"]], b["label"], b["value"], b["unit"], b["note"]))
    o.append("")
    size = {b["key"]: b["value"] for b in report["benchmarks"] if b["verdict"] == "info"}
    if size:
        o.append("**Size:** " + " · ".join(
            "%d %s" % (size[k], label) for k, label in (
                ("nodes", "nodes"), ("edges", "transitions"), ("screens", "screens"),
                ("api_calls", "network calls"), ("decisions", "decisions"),
                ("error_branches", "error branches")) if k in size))
        o.append("")


def _findings(o, report):
    findings = report["findings"]
    o.append("## Findings (%d)" % len(findings))
    o.append("")
    if not findings:
        o.append("No structural problems found.")
        o.append("")
        return

    for f in findings:
        o.append('<a id="%s"></a>' % _anchor(f["id"]))
        o.append("")
        o.append("### %s %s" % (SEV_BADGE[f["severity"]], f["title"]))
        o.append("")
        meta = ["`%s`" % f["id"],
                "**severity:** %s" % catalog.SEVERITY_LABEL[f["severity"]].lower(),
                "**confidence:** %s" % catalog.CONFIDENCE_LABEL.get(f["confidence"],
                                                                   f["confidence"]),
                "**effort:** %s" % catalog.EFFORT_LABEL[f["effort"]]]
        if f["label"]:
            meta.insert(1, "**node:** %s" % f["label"])
        if f["route"]:
            meta.append("**route:** `%s`" % f["route"])
        o.append(" · ".join(meta))
        o.append("")
        for heading, key in (("What happens", "what"),
                             ("What the user experiences", "impact"),
                             ("What to do", "fix")):
            if f[key]:
                o.append("**%s**" % heading)
                o.append("")
                o.append(f[key])
                o.append("")
        if f["evidence"]:
            o.append("**Evidence:** " + " · ".join("`%s`" % e for e in f["evidence"]))
            o.append("")
        o.append("<sub>Accept and silence with: `flowlint ignore %s`</sub>" % f["id"])
        o.append("")


def _informational(o, report):
    info = report.get("info") or []
    if not info:
        return
    o.append("## Notes")
    o.append("")
    o.append("Not problems, but worth knowing when reading the flow.")
    o.append("")
    for i in info:
        o.append("- **%s** — %s%s" % (
            i["label"], i["text"], "  `%s`" % i["source"] if i["source"] else ""))
    o.append("")


def _suppressed(o, report):
    muted = report.get("suppressed") or []
    if not muted:
        return
    o.append("## Accepted (%d)" % len(muted))
    o.append("")
    o.append("Findings silenced in `.flowlintignore`. They pass the audit but do not "
             "disappear — the decision to accept them stays on the record.")
    o.append("")
    o.append("| id | finding | node |")
    o.append("| --- | --- | --- |")
    for f in muted:
        o.append("| `%s` | %s | %s |" % (f["id"], f["title"], _esc(f["label"] or f["node"])))
    o.append("")


def _method(o, doc, report):
    m = report["metrics"]
    app = doc.get("app") or {}
    o.append("## Method")
    o.append("")
    o.append("This report was generated from `%s.flow.json`, which was in turn "
             "extracted by reading the codebase." % doc["id"])
    o.append("")
    o.append("- **Scope:** %d nodes, %d transitions%s"
             % (m["nodes"], m["edges"],
                ", at commit `%s`" % app["commit"] if app.get("commit") else ""))
    o.append("- **Traceability:** %d%% of nodes carry a `file:line` anchor"
             % m["source_coverage"])
    o.append("- **Findings come only from the graph.** Nothing is invented: every "
             "finding follows either from the structure or from a tag grounded in code.")
    o.append("- **Not covered:** what real users do. This extracts the paths the code "
             "permits, not the ones people choose. It complements analytics rather than "
             "replacing them.")
    if m["source_coverage"] < 100:
        o.append("- **Caution:** some nodes could not be traced to code; treat those "
                 "parts of the map with care.")
    o.append("")


def _machine(o, doc, report):
    """Structured facts, so an agent does not have to parse the prose above."""
    payload = {
        "flow": doc["id"],
        "title": doc["title"],
        "ir_hash": ir.content_hash(doc),
        "app": {k: v for k, v in (doc.get("app") or {}).items() if v},
        "metrics": report["metrics"],
        "primary_path": report["primary_path"],
        "findings": [
            {"id": f["id"], "code": f["code"], "severity": f["severity"],
             "confidence": f["confidence"], "effort": f["effort"],
             "node": f["node"], "label": f["label"], "evidence": f["evidence"],
             "fix": f["fix"]}
            for f in report["findings"]
        ],
        "suppressed": [f["id"] for f in report.get("suppressed") or []],
    }
    o.append("## Machine-readable summary")
    o.append("")
    o.append("<details><summary>JSON</summary>")
    o.append("")
    o.append("```json")
    o.append(json.dumps(payload, ensure_ascii=False, indent=2))
    o.append("```")
    o.append("")
    o.append("</details>")
    o.append("")


# --------------------------------------------------------------------- helpers
def _esc(text):
    """Table cells: a pipe in a label would split the row."""
    return str(text).replace("|", "\\|")


def _anchor(finding_id):
    return finding_id.lower()
