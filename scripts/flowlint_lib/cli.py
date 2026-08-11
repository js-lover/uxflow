"""flowlint -- a linter for your app's user flows.

Reads a flow description extracted from the codebase, reports what is wrong with
it, and renders editable diagrams as the evidence.

Commands
  flowlint check    <flow.json>... [-o DIR] [--fail-on-high] [--format full]
                    lint the flows -- the point of the tool
  flowlint render   <flow.json>... [-o DIR] [--formats drawio,md,svg,mermaid]
                    write the diagram and the full report
  flowlint diff     <before.json> <after.json> [-o DIR]
                    before/after comparison with a metric delta
  flowlint stale    <flow.json>... [-o DIR]
                    CI guard: fail if an IR changed but diagrams were not regenerated
  flowlint validate <flow.json>...            schema and integrity check
  flowlint ignore   <FINDING-ID>... [--reason TEXT]   accept a finding
  flowlint init     <flow-id> [-o DIR]        scaffold an IR file
  flowlint id       <route> [component]       mint a stable node id

Default output per flow (3 files)
  <id>.flow.json   the IR you edit
  <id>.drawio      multi-page: [Flow] [Flow + notes] (+ [Changes] after a diff)
  <id>.md          the report, with the diagram embedded as Mermaid

No third-party packages. Python 3.8+.
"""

import argparse
import copy
import json
import os
import sys

from . import analyze, diffing, drawio, ir, layout, mermaid, report, svg

LOCK = ".flowlint.lock.json"
IGNORE = ".flowlintignore"
ALL_FORMATS = ["drawio", "md", "svg", "mermaid"]
DEFAULT_FORMATS = "drawio,md"


# --------------------------------------------------------------------- helpers
def _ensure(d):
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    return d


def _write(path, text, quiet=False):
    _ensure(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if not quiet:
        print("  %s" % os.path.relpath(path))
    return path


def _load(paths):
    docs = []
    for p in paths:
        try:
            docs.append((p, ir.load(p)))
        except ir.IRError as exc:
            print("FAIL %s" % p, file=sys.stderr)
            print(exc, file=sys.stderr)
            raise SystemExit(2)
    return docs


def _lock_path(outdir):
    return os.path.join(outdir or ".", LOCK)


def _read_lock(outdir):
    p = _lock_path(outdir)
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError:
            return {}


def _write_lock(outdir, data):
    with open(_lock_path(outdir), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


# ------------------------------------------------------------------ suppression
def _ignore_file(start="."):
    """Walk up from `start` looking for .flowlintignore, like .gitignore."""
    cur = os.path.abspath(start)
    while True:
        cand = os.path.join(cur, IGNORE)
        if os.path.exists(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.join(os.path.abspath(start), IGNORE)
        cur = parent


def _read_ignore(start="."):
    path = _ignore_file(start)
    ids = set()
    if not os.path.exists(path):
        return ids
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                ids.add(line.split()[0])
    return ids


def cmd_ignore(args):
    path = _ignore_file(".")
    existing = _read_ignore(".")
    new = [i for i in args.ids if i not in existing]
    if not new:
        print("Already accepted: %s" % ", ".join(args.ids))
        return 0
    fresh = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as fh:
        if fresh:
            fh.write("# flowlint -- accepted findings.\n"
                     "# One finding id per line. Put the reason beside it; it shows in\n"
                     "# the report.\n\n")
        for i in new:
            fh.write("%s%s\n" % (i, ("  # " + args.reason) if args.reason else ""))
    print("Added to %s: %s" % (os.path.relpath(path), ", ".join(new)))
    return 0


# -------------------------------------------------------------------- commands
def cmd_validate(args):
    for path, doc in _load(args.flows):
        print("OK   %s  (%d nodes, %d transitions, hash %s)"
              % (path, len(doc["nodes"]), len(doc["edges"]), ir.content_hash(doc)))
    return 0


def _pages_for(doc):
    """Clean page first -- it is the one people show to other people."""
    clean_lay = layout.compute(doc, annotated=False)
    annot_lay = layout.compute(doc, annotated=True)
    return [
        {"name": "Flow", "doc": doc, "layout": clean_lay,
         "annotated": False, "mode": "normal", "legend": True},
        {"name": "Flow + notes", "doc": doc, "layout": annot_lay,
         "annotated": True, "mode": "normal", "legend": True},
    ]


def cmd_render(args):
    outdir = _ensure(args.out or "docs/ux-flows")
    formats = [f.strip() for f in (args.formats or DEFAULT_FORMATS).split(",") if f.strip()]
    bad = [f for f in formats if f not in ALL_FORMATS]
    if bad:
        print("unknown format: %s" % ", ".join(bad), file=sys.stderr)
        return 2
    if getattr(args, "variant", None):
        print("warning: --variant was removed. Both views are now tabs inside the "
              ".drawio file. The flag was ignored.", file=sys.stderr)

    suppressed = _read_ignore(outdir)
    lock = _read_lock(outdir)
    exit_code = 0

    for path, doc in _load(args.flows):
        print("%s" % path)
        rep = analyze.audit(doc, suppressed=suppressed)
        base = os.path.join(outdir, doc["id"])

        if "drawio" in formats:
            _write(base + ".drawio", drawio.render_pages(_pages_for(doc)))
        if "md" in formats:
            _write(base + ".md", report.render(doc, rep,
                                               embed_diagram="mermaid" not in formats or True))
        if "mermaid" in formats:
            _write(base + ".mmd", mermaid.render(doc, annotated=True))
        if "svg" in formats:
            lay = layout.compute(doc, annotated=True)
            _write(base + ".svg", svg.render(doc, lay, annotated=True))

        highs = [f for f in rep["findings"] if f["severity"] == "high"]
        print("  -> %d findings (%d high), primary path %d steps, %d dead ends"
              % (len(rep["findings"]), len(highs),
                 rep["metrics"]["primary_path_steps"], rep["metrics"]["failure_exits"]))
        if rep["suppressed"]:
            print("  -> %d findings accepted (.flowlintignore)" % len(rep["suppressed"]))
        if args.fail_on_high and highs:
            exit_code = 1

        lock[doc["id"]] = {"hash": ir.content_hash(doc), "source": os.path.relpath(path)}

    _write_lock(outdir, lock)
    return exit_code


def cmd_check(args):
    """Lint the flows. The headline command -- what the tool is named after.

    Prints a compact result line per flow by default, because that is what a CI
    log should contain. `-o DIR` writes the full report instead.
    """
    outdir = args.out
    suppressed = _read_ignore(outdir or ".")
    worst = 0
    total = 0
    for path, doc in _load(args.flows):
        rep = analyze.audit(doc, suppressed=suppressed)
        findings = rep["findings"]
        highs = [f for f in findings if f["severity"] == "high"]
        total += len(findings)

        if outdir:
            _write(os.path.join(_ensure(outdir), doc["id"] + ".md"),
                   report.render(doc, rep, embed_diagram=False))
        elif args.format == "full":
            print(report.render(doc, rep, embed_diagram=False))
        else:
            mark = "✗" if highs else ("!" if findings else "✓")
            print("%s %-24s %d findings (%d high) · primary path %d steps · %d dead ends"
                  % (mark, doc["id"], len(findings), len(highs),
                     rep["metrics"]["primary_path_steps"], rep["metrics"]["failure_exits"]))
            for f in findings:
                where = f["evidence"][0] if f["evidence"] else (f["label"] or doc["id"])
                print("    %s  %s — %s  [%s]"
                      % (SEVERITY_MARK[f["severity"]], f["title"],
                         f["label"] or "whole flow", where))
            if rep["suppressed"]:
                print("    %d findings accepted (.flowlintignore)" % len(rep["suppressed"]))

        if highs:
            worst = 1
    if not args.out and args.format != "full" and total == 0:
        print("No problems found.")
    return worst if args.fail_on_high else 0


SEVERITY_MARK = {"high": "high  ", "medium": "medium", "low": "low   "}


def cmd_diff(args):
    outdir = _ensure(args.out or "docs/ux-flows")
    (_, before), (_, after) = _load([args.before, args.after])
    merged, summary = diffing.diff(before, after)

    pages = _pages_for(after)
    pages.append({"name": "Changes", "doc": merged,
                  "layout": layout.compute(merged, annotated=True),
                  "annotated": True, "mode": "diff", "legend": True})
    base = os.path.join(outdir, after["id"])
    print("%s → %s" % (before["id"], after["id"]))
    _write(base + ".drawio", drawio.render_pages(pages))

    rep = analyze.audit(after, suppressed=_read_ignore(outdir))
    body = report.render(after, rep)
    body += "\n" + diffing.to_markdown(before, after, summary)
    _write(base + ".md", body)

    print("  -> +%d / -%d / ~%d nodes"
          % (len(summary["added"]), len(summary["removed"]), len(summary["changed"])))
    return 0


def cmd_stale(args):
    """CI guard: did someone edit an IR without regenerating the diagrams?"""
    outdir = args.out or "docs/ux-flows"
    lock = _read_lock(outdir)
    stale, legacy = [], []
    for path, doc in _load(args.flows):
        recorded = (lock.get(doc["id"]) or {}).get("hash")
        current = ir.content_hash(doc)
        if recorded is None:
            legacy.append(doc["id"])
        elif recorded != current:
            stale.append((doc["id"], recorded, current))

    if legacy:
        print("No lock entry for these flows (first run, or upgraded from an older "
              "version): %s"
              % ", ".join(legacy), file=sys.stderr)
        print("Run `flowlint render` and commit the result.", file=sys.stderr)
        return 1
    if stale:
        print("Diagrams are out of date. Run `flowlint render` and commit:", file=sys.stderr)
        for fid, rec, cur in stale:
            print("  %-24s locked=%s current=%s" % (fid, rec, cur), file=sys.stderr)
        return 1
    print("All diagrams are up to date.")
    return 0


TEMPLATE = {
    "version": "1.0",
    "id": "REPLACE-ME",
    "title": "Replace me",
    "description": "One sentence: what the user is trying to accomplish.",
    "app": {"name": "", "stack": "other", "commit": ""},
    "direction": "TD",
    "lanes": [
        {"id": "user", "label": "User"},
        {"id": "ui", "label": "UI"},
        {"id": "api", "label": "Backend"},
    ],
    "nodes": [
        {"id": "entry", "type": "start", "label": "Entry point", "lane": "user", "kind": "happy"},
        {"id": "home", "type": "screen", "label": "Home", "lane": "ui", "kind": "happy",
         "route": "/", "source": "src/app/page.tsx:1",
         "annotations": {"taps": 1, "friction": []}},
        {"id": "done", "type": "end", "label": "Goal reached", "lane": "user", "kind": "happy"},
    ],
    "edges": [
        {"from": "entry", "to": "home", "kind": "happy"},
        {"from": "home", "to": "done", "label": "completes", "kind": "happy"},
    ],
}


def cmd_init(args):
    outdir = _ensure(args.out or "docs/ux-flows")
    doc = copy.deepcopy(TEMPLATE)
    doc["id"] = args.flow_id
    doc["title"] = args.flow_id.replace("-", " ").replace("_", " ").title()
    path = os.path.join(outdir, args.flow_id + ".flow.json")
    if os.path.exists(path) and not args.force:
        print("%s already exists (use --force to overwrite)" % path, file=sys.stderr)
        return 1
    _write(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_id(args):
    print(ir.stable_id(args.route, args.component))
    return 0


# ------------------------------------------------------------------------ main
def build_parser():
    p = argparse.ArgumentParser(prog="flowlint", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="check a flow file for schema and integrity errors")
    v.add_argument("flows", nargs="+")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("render", help="write the diagram and the full report")
    r.add_argument("flows", nargs="+")
    r.add_argument("-o", "--out", help="output directory (default docs/ux-flows)")
    r.add_argument("--formats", default=DEFAULT_FORMATS,
                   help="drawio,md,svg,mermaid (default: %s)" % DEFAULT_FORMATS)
    r.add_argument("--fail-on-high", action="store_true",
                   help="exit 1 when a high-severity finding exists")
    r.add_argument("--variant", help=argparse.SUPPRESS)
    r.set_defaults(func=cmd_render)

    # `check` is the headline command: the tool is a linter, so linting is what
    # its plainest verb has to do. The staleness guard moved to `stale`.
    for name, hidden in (("check", False), ("audit", True)):
        a = sub.add_parser(name, help=argparse.SUPPRESS if hidden
                           else "lint the flows -- the main command")
        a.add_argument("flows", nargs="+")
        a.add_argument("-o", "--out", help="write the report here (default: print a summary)")
        a.add_argument("--format", choices=["summary", "full"], default="summary",
                       help="summary = a short list for CI, full = the whole report")
        a.add_argument("--fail-on-high", action="store_true",
                       help="exit 1 when a high-severity finding exists")
        a.set_defaults(func=cmd_check)

    d = sub.add_parser("diff", help="before/after comparison")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("-o", "--out")
    d.set_defaults(func=cmd_diff)

    s = sub.add_parser("stale", help="CI: are the diagrams in sync with their source")
    s.add_argument("flows", nargs="+")
    s.add_argument("-o", "--out")
    s.set_defaults(func=cmd_stale)

    g = sub.add_parser("ignore", help="accept a finding and stop reporting it")
    g.add_argument("ids", nargs="+", metavar="FINDING-ID")
    g.add_argument("--reason", help="reason, written into the file as a comment")
    g.set_defaults(func=cmd_ignore)

    i = sub.add_parser("init", help="scaffold a new flow file")
    i.add_argument("flow_id")
    i.add_argument("-o", "--out")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    n = sub.add_parser("id", help="mint a stable node id from a route")
    n.add_argument("route")
    n.add_argument("component", nargs="?", default="")
    n.set_defaults(func=cmd_id)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)

