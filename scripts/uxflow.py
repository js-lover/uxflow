#!/usr/bin/env python3
"""uxflow -- deterministic UX flow diagram generator.

Usage
  uxflow.py validate  <flow.json>...
  uxflow.py render    <flow.json>... [-o DIR] [--variant both|annotated|clean]
                                     [--formats drawio,mermaid,svg,md] [--no-audit]
  uxflow.py audit     <flow.json>... [-o DIR]
  uxflow.py diff      <before.json> <after.json> [-o DIR]
  uxflow.py check     <flow.json>... [-o DIR]
  uxflow.py init      <flow-id> [-o DIR]
  uxflow.py id        <route> [component]

No third-party packages. Python 3.8+.
"""

import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uxflow_lib import analyze, diffing, drawio, ir, layout, mermaid, svg  # noqa: E402

LOCK = ".uxflow.lock.json"
ALL_FORMATS = ["drawio", "mermaid", "svg", "md"]


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
        print("  wrote %s" % os.path.relpath(path))
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


# -------------------------------------------------------------------- commands
def cmd_validate(args):
    docs = _load(args.flows)
    for path, doc in docs:
        print("OK   %s  (%d nodes, %d edges, hash %s)"
              % (path, len(doc["nodes"]), len(doc["edges"]), ir.content_hash(doc)))
    return 0


def cmd_render(args):
    outdir = _ensure(args.out or "docs/ux-flows")
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    bad = [f for f in formats if f not in ALL_FORMATS]
    if bad:
        print("unknown format(s): %s" % ", ".join(bad), file=sys.stderr)
        return 2

    variants = {"both": ["annotated", "clean"],
                "annotated": ["annotated"], "clean": ["clean"]}[args.variant]

    lock = _read_lock(outdir)
    exit_code = 0
    for path, doc in _load(args.flows):
        print("%s -> %s" % (path, outdir))
        report = None
        if not args.no_audit:
            report = analyze.audit(copy.deepcopy(doc))
            # re-run on the live doc so `_problem` markers land on the rendered nodes
            analyze.audit(doc)

        for variant in variants:
            annotated = variant == "annotated"
            suffix = "" if len(variants) == 1 and args.variant != "both" else "." + variant
            lay = layout.compute(doc, annotated=annotated)
            base = os.path.join(outdir, doc["id"] + suffix)
            if "drawio" in formats:
                _write(base + ".drawio", drawio.render(doc, lay, annotated=annotated))
            if "mermaid" in formats:
                _write(base + ".mmd", mermaid.render(doc, annotated=annotated))
            if "svg" in formats:
                _write(base + ".svg", svg.render(doc, lay, annotated=annotated))

        if "md" in formats and report:
            _write(os.path.join(outdir, doc["id"] + ".findings.md"),
                   analyze.to_markdown(doc, report))

        if report:
            highs = [f for f in report["findings"] if f["severity"] == "high"]
            print("  %d finding(s), %d high severity, primary path %d steps"
                  % (len(report["findings"]), len(highs), report["metrics"]["primary_path_steps"]))
            if args.fail_on_high and highs:
                exit_code = 1

        lock[doc["id"]] = {"hash": ir.content_hash(doc), "source": os.path.relpath(path)}

    _write_lock(outdir, lock)
    return exit_code


def cmd_audit(args):
    outdir = args.out
    worst = 0
    for path, doc in _load(args.flows):
        report = analyze.audit(doc)
        md = analyze.to_markdown(doc, report)
        if outdir:
            _write(os.path.join(_ensure(outdir), doc["id"] + ".findings.md"), md)
        else:
            print(md)
        if any(f["severity"] == "high" for f in report["findings"]):
            worst = 1
    return worst if args.fail_on_high else 0


def cmd_diff(args):
    outdir = _ensure(args.out or "docs/ux-flows")
    (_, before), (_, after) = _load([args.before, args.after])
    merged, summary = diffing.diff(before, after)
    lay = layout.compute(merged, annotated=True)
    base = os.path.join(outdir, merged["id"])
    _write(base + ".drawio", drawio.render(merged, lay, annotated=True, mode="diff"))
    _write(base + ".mmd", mermaid.render(merged, annotated=True, mode="diff"))
    _write(base + ".svg", svg.render(merged, lay, annotated=True, mode="diff"))
    _write(base + ".md", diffing.to_markdown(before, after, summary))
    print("  +%d / -%d / ~%d nodes"
          % (len(summary["added"]), len(summary["removed"]), len(summary["changed"])))
    return 0


def cmd_check(args):
    outdir = args.out or "docs/ux-flows"
    lock = _read_lock(outdir)
    stale = []
    for path, doc in _load(args.flows):
        recorded = (lock.get(doc["id"]) or {}).get("hash")
        current = ir.content_hash(doc)
        if recorded != current:
            stale.append((doc["id"], recorded, current))
    if stale:
        print("Diagrams are out of date. Run `uxflow render` and commit the result:", file=sys.stderr)
        for fid, rec, cur in stale:
            print("  %-24s locked=%s current=%s" % (fid, rec or "<none>", cur), file=sys.stderr)
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
    p = argparse.ArgumentParser(prog="uxflow", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="check flow IR files against the schema rules")
    v.add_argument("flows", nargs="+")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("render", help="generate .drawio / .mmd / .svg / findings.md")
    r.add_argument("flows", nargs="+")
    r.add_argument("-o", "--out", help="output directory (default docs/ux-flows)")
    r.add_argument("--variant", choices=["both", "annotated", "clean"], default="both")
    r.add_argument("--formats", default="drawio,mermaid,svg,md")
    r.add_argument("--no-audit", action="store_true", help="skip the UX audit pass")
    r.add_argument("--fail-on-high", action="store_true", help="exit 1 if a high-severity finding exists")
    r.set_defaults(func=cmd_render)

    a = sub.add_parser("audit", help="static UX audit; prints or writes findings.md")
    a.add_argument("flows", nargs="+")
    a.add_argument("-o", "--out")
    a.add_argument("--fail-on-high", action="store_true")
    a.set_defaults(func=cmd_audit)

    d = sub.add_parser("diff", help="before/after comparison of two flow IRs")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("-o", "--out")
    d.set_defaults(func=cmd_diff)

    c = sub.add_parser("check", help="CI guard: fail if the IR changed but diagrams were not regenerated")
    c.add_argument("flows", nargs="+")
    c.add_argument("-o", "--out")
    c.set_defaults(func=cmd_check)

    i = sub.add_parser("init", help="scaffold a new flow IR file")
    i.add_argument("flow_id")
    i.add_argument("-o", "--out")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    n = sub.add_parser("id", help="mint a stable node id from a route (+ component)")
    n.add_argument("route")
    n.add_argument("component", nargs="?", default="")
    n.set_defaults(func=cmd_id)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
