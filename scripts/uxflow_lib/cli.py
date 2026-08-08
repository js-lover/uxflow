"""uxflow command line interface.

uxflow -- deterministic UX flow diagram generator and static UX audit.

Usage
  uxflow.py validate <flow.json>...
  uxflow.py render   <flow.json>... [-o DIR] [--formats drawio,md,svg,mermaid]
                                    [--fail-on-high]
  uxflow.py audit    <flow.json>... [-o DIR] [--fail-on-high]
  uxflow.py diff     <before.json> <after.json> [-o DIR]
  uxflow.py check    <flow.json>... [-o DIR]
  uxflow.py ignore   <FINDING-ID>... [--reason TEXT]
  uxflow.py init     <flow-id> [-o DIR]
  uxflow.py id       <route> [component]

Default output per flow (3 files):
  <id>.flow.json   the IR you edit
  <id>.drawio      multi-page: [Akış] [Akış + notlar] (+ [Değişim] after a diff)
  <id>.md          the report, with the diagram embedded as Mermaid

No third-party packages. Python 3.8+.
"""

import argparse
import copy
import json
import os
import sys

from . import analyze, diffing, drawio, ir, layout, mermaid, report, svg

LOCK = ".uxflow.lock.json"
IGNORE = ".uxflowignore"
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
    """Walk up from `start` looking for .uxflowignore, like .gitignore."""
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
        print("Zaten bastırılmış: %s" % ", ".join(args.ids))
        return 0
    fresh = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as fh:
        if fresh:
            fh.write("# uxflow -- kabul edilmiş bulgular.\n"
                     "# Her satır bir bulgu id'si. Gerekçeyi yanına yaz; rapora yansır.\n\n")
        for i in new:
            fh.write("%s%s\n" % (i, ("  # " + args.reason) if args.reason else ""))
    print("%s dosyasına eklendi: %s" % (os.path.relpath(path), ", ".join(new)))
    return 0


# -------------------------------------------------------------------- commands
def cmd_validate(args):
    for path, doc in _load(args.flows):
        print("OK   %s  (%d düğüm, %d geçiş, hash %s)"
              % (path, len(doc["nodes"]), len(doc["edges"]), ir.content_hash(doc)))
    return 0


def _pages_for(doc):
    """Clean page first -- it is the one people show to other people."""
    clean_lay = layout.compute(doc, annotated=False)
    annot_lay = layout.compute(doc, annotated=True)
    return [
        {"name": "Akış", "doc": doc, "layout": clean_lay,
         "annotated": False, "mode": "normal", "legend": True},
        {"name": "Akış + notlar", "doc": doc, "layout": annot_lay,
         "annotated": True, "mode": "normal", "legend": True},
    ]


def cmd_render(args):
    outdir = _ensure(args.out or "docs/ux-flows")
    formats = [f.strip() for f in (args.formats or DEFAULT_FORMATS).split(",") if f.strip()]
    bad = [f for f in formats if f not in ALL_FORMATS]
    if bad:
        print("bilinmeyen format: %s" % ", ".join(bad), file=sys.stderr)
        return 2
    if getattr(args, "variant", None):
        print("uyarı: --variant kaldırıldı. Her iki görünüm artık .drawio dosyasının "
              "sekmelerinde. Bayrak yok sayıldı.", file=sys.stderr)

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
        print("  → %d bulgu (%d yüksek), ana yol %d adım, %d çıkmaz"
              % (len(rep["findings"]), len(highs),
                 rep["metrics"]["primary_path_steps"], rep["metrics"]["failure_exits"]))
        if rep["suppressed"]:
            print("  → %d bulgu bastırılmış (.uxflowignore)" % len(rep["suppressed"]))
        if args.fail_on_high and highs:
            exit_code = 1

        lock[doc["id"]] = {"hash": ir.content_hash(doc), "source": os.path.relpath(path)}

    _write_lock(outdir, lock)
    return exit_code


def cmd_audit(args):
    outdir = args.out
    suppressed = _read_ignore(outdir or ".")
    worst = 0
    for path, doc in _load(args.flows):
        rep = analyze.audit(doc, suppressed=suppressed)
        md = report.render(doc, rep, embed_diagram=False)
        if outdir:
            _write(os.path.join(_ensure(outdir), doc["id"] + ".md"), md)
        else:
            print(md)
        if any(f["severity"] == "high" for f in rep["findings"]):
            worst = 1
    return worst if args.fail_on_high else 0


def cmd_diff(args):
    outdir = _ensure(args.out or "docs/ux-flows")
    (_, before), (_, after) = _load([args.before, args.after])
    merged, summary = diffing.diff(before, after)

    pages = _pages_for(after)
    pages.append({"name": "Değişim", "doc": merged,
                  "layout": layout.compute(merged, annotated=True),
                  "annotated": True, "mode": "diff", "legend": True})
    base = os.path.join(outdir, after["id"])
    print("%s → %s" % (before["id"], after["id"]))
    _write(base + ".drawio", drawio.render_pages(pages))

    rep = analyze.audit(after, suppressed=_read_ignore(outdir))
    body = report.render(after, rep)
    body += "\n" + diffing.to_markdown(before, after, summary)
    _write(base + ".md", body)

    print("  → +%d / -%d / ~%d düğüm"
          % (len(summary["added"]), len(summary["removed"]), len(summary["changed"])))
    return 0


def cmd_check(args):
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
        print("Bu akışlar için kayıt yok (ilk çalıştırma ya da eski sürümden geçiş): %s"
              % ", ".join(legacy), file=sys.stderr)
        print("`uxflow render` çalıştırıp sonucu commit et.", file=sys.stderr)
        return 1
    if stale:
        print("Diyagramlar güncel değil. `uxflow render` çalıştırıp commit et:", file=sys.stderr)
        for fid, rec, cur in stale:
            print("  %-24s kayıtlı=%s güncel=%s" % (fid, rec, cur), file=sys.stderr)
        return 1
    print("Tüm diyagramlar güncel.")
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
        print("%s zaten var (--force ile üzerine yaz)" % path, file=sys.stderr)
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

    v = sub.add_parser("validate", help="IR dosyalarını doğrula")
    v.add_argument("flows", nargs="+")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("render", help=".drawio + rapor üret")
    r.add_argument("flows", nargs="+")
    r.add_argument("-o", "--out", help="çıktı klasörü (varsayılan docs/ux-flows)")
    r.add_argument("--formats", default=DEFAULT_FORMATS,
                   help="drawio,md,svg,mermaid (varsayılan: %s)" % DEFAULT_FORMATS)
    r.add_argument("--fail-on-high", action="store_true",
                   help="yüksek önemli bulgu varsa 1 ile çık")
    r.add_argument("--variant", help=argparse.SUPPRESS)
    r.set_defaults(func=cmd_render)

    a = sub.add_parser("audit", help="yalnızca rapor")
    a.add_argument("flows", nargs="+")
    a.add_argument("-o", "--out")
    a.add_argument("--fail-on-high", action="store_true")
    a.set_defaults(func=cmd_audit)

    d = sub.add_parser("diff", help="öncesi/sonrası karşılaştırma")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("-o", "--out")
    d.set_defaults(func=cmd_diff)

    c = sub.add_parser("check", help="CI: diyagramlar IR ile senkron mu")
    c.add_argument("flows", nargs="+")
    c.add_argument("-o", "--out")
    c.set_defaults(func=cmd_check)

    g = sub.add_parser("ignore", help="bulguyu kabul et ve sustur")
    g.add_argument("ids", nargs="+", metavar="FINDING-ID")
    g.add_argument("--reason", help="gerekçe (dosyaya yorum olarak yazılır)")
    g.set_defaults(func=cmd_ignore)

    i = sub.add_parser("init", help="yeni IR dosyası oluştur")
    i.add_argument("flow_id")
    i.add_argument("-o", "--out")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    n = sub.add_parser("id", help="route'tan stabil düğüm id'si üret")
    n.add_argument("route")
    n.add_argument("component", nargs="?", default="")
    n.set_defaults(func=cmd_id)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)

