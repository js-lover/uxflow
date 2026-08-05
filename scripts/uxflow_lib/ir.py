"""Load, validate and normalise the UXFlow IR. Standard library only."""

import hashlib
import json
import os
import re
import textwrap

from . import theme

VERSION = "1.0"

NODE_TYPES = {"start", "end", "screen", "modal", "action", "decision",
              "api", "data", "state", "external", "note"}
NODE_KINDS = {"happy", "error", "edge", "neutral"}
EDGE_KINDS = {"happy", "error", "edge", "back", "neutral"}
FRICTION = set(theme.FRICTION_LABELS)

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class IRError(Exception):
    """Raised with a list of human-readable problems."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__("\n".join("  - " + p for p in problems))


# --------------------------------------------------------------------------- io
def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        try:
            doc = json.load(fh)
        except json.JSONDecodeError as exc:
            raise IRError(["%s is not valid JSON: %s" % (path, exc)])
    validate(doc, origin=os.path.basename(path))
    return normalize(doc)


def dump(doc, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(strip_internal(doc), fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")


def strip_internal(doc):
    """Remove keys the renderer added (prefixed with _) so the IR stays clean on disk."""
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items() if not k.startswith("_")}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return obj
    return clean(doc)


# --------------------------------------------------------------------- validation
def validate(doc, origin="flow.json"):
    p = []
    if not isinstance(doc, dict):
        raise IRError(["%s: top level must be an object" % origin])

    if doc.get("version") != VERSION:
        p.append("version must be %r (got %r)" % (VERSION, doc.get("version")))
    if not SLUG_RE.match(str(doc.get("id", ""))):
        p.append("id must be a lowercase slug, got %r" % doc.get("id"))
    if not str(doc.get("title", "")).strip():
        p.append("title is required")

    nodes = doc.get("nodes")
    edges = doc.get("edges", [])
    if not isinstance(nodes, list) or not nodes:
        raise IRError(p + ["nodes must be a non-empty array"])
    if not isinstance(edges, list):
        raise IRError(p + ["edges must be an array"])

    lane_ids = {l.get("id") for l in doc.get("lanes", []) or []}
    for lane in doc.get("lanes", []) or []:
        if not SLUG_RE.match(str(lane.get("id", ""))):
            p.append("lane id %r is not a slug" % lane.get("id"))
        if not lane.get("label"):
            p.append("lane %r has no label" % lane.get("id"))

    seen = set()
    for i, n in enumerate(nodes):
        where = "nodes[%d]" % i
        nid = n.get("id")
        if not isinstance(nid, str) or not ID_RE.match(nid):
            p.append("%s: id %r must match [a-z0-9][a-z0-9_.-]*" % (where, nid))
        elif nid in seen:
            p.append("%s: duplicate node id %r" % (where, nid))
        else:
            seen.add(nid)
        if n.get("type") not in NODE_TYPES:
            p.append("%s (%s): type %r not in %s" % (where, nid, n.get("type"), sorted(NODE_TYPES)))
        if not str(n.get("label", "")).strip():
            p.append("%s (%s): label is required" % (where, nid))
        if n.get("kind") and n["kind"] not in NODE_KINDS:
            p.append("%s (%s): kind %r invalid" % (where, nid, n["kind"]))
        if lane_ids and n.get("type") != "note":
            if not n.get("lane"):
                p.append("%s (%s): lane is required because lanes are declared" % (where, nid))
            elif n["lane"] not in lane_ids:
                p.append("%s (%s): unknown lane %r" % (where, nid, n["lane"]))
        ann = n.get("annotations") or {}
        for f in ann.get("friction", []) or []:
            if f not in FRICTION:
                p.append("%s (%s): unknown friction tag %r" % (where, nid, f))
        for key in ("taps", "required_fields", "optional_fields"):
            if key in ann and (not isinstance(ann[key], int) or ann[key] < 0):
                p.append("%s (%s): annotations.%s must be a non-negative integer" % (where, nid, key))

    for i, e in enumerate(edges):
        where = "edges[%d]" % i
        if e.get("from") not in seen:
            p.append("%s: from %r is not a known node" % (where, e.get("from")))
        if e.get("to") not in seen:
            p.append("%s: to %r is not a known node" % (where, e.get("to")))
        if e.get("kind") and e["kind"] not in EDGE_KINDS:
            p.append("%s: kind %r invalid" % (where, e["kind"]))

    if not any(n.get("type") == "start" for n in nodes):
        p.append("at least one node of type 'start' is required (the flow entry point)")

    if p:
        raise IRError(["%s:" % origin] + p if False else p)
    return True


# -------------------------------------------------------------------- normalise
def normalize(doc):
    doc.setdefault("direction", "TD")
    doc.setdefault("edges", [])
    doc.setdefault("lanes", [])
    doc.setdefault("app", {})
    for n in doc["nodes"]:
        n.setdefault("kind", "neutral")
        n.setdefault("annotations", {})
    for e in doc["edges"]:
        e.setdefault("kind", "neutral")
    doc["_index"] = {n["id"]: n for n in doc["nodes"]}
    return doc


def index(doc):
    return doc.get("_index") or {n["id"]: n for n in doc["nodes"]}


# ------------------------------------------------------------------------ hashing
def content_hash(doc):
    """Stable hash over the semantic content only -- used by `uxflow check`."""
    clean = strip_internal(doc)
    payload = {
        "id": clean.get("id"),
        "direction": clean.get("direction"),
        "lanes": clean.get("lanes"),
        "nodes": sorted(clean["nodes"], key=lambda n: n["id"]),
        "edges": sorted(clean.get("edges", []),
                        key=lambda e: (e["from"], e["to"], e.get("label", ""))),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def stable_id(*parts):
    """Helper agents can call to mint deterministic node ids from route + component."""
    raw = "/".join(str(p) for p in parts if p)
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if ID_RE.match(slug) and len(slug) <= 48:
        return slug
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return (slug[:39].rstrip("-") or "n") + "-" + digest


# ------------------------------------------------------------------------- labels
def wrap(text, width):
    out = []
    for para in str(text).split("\n"):
        out.extend(textwrap.wrap(para, width) or [""])
    return out


def node_lines(node, annotated=True, width=26):
    """Return the list of display lines for a node. Renderer-agnostic."""
    lines = list(wrap(node["label"], width))
    if not annotated:
        return lines

    ann = node.get("annotations") or {}
    meta = []
    if node.get("route"):
        meta.append(node["route"])
    if ann.get("taps"):
        meta.append("%d tap" % ann["taps"] if ann["taps"] == 1 else "%d taps" % ann["taps"])
    fields = []
    if ann.get("required_fields"):
        fields.append("%d required" % ann["required_fields"])
    if ann.get("optional_fields"):
        fields.append("%d optional" % ann["optional_fields"])
    if fields:
        meta.append(" / ".join(fields) + " fields")
    if ann.get("wait"):
        meta.append("wait: " + ann["wait"])

    for m in meta:
        lines.extend(wrap(m, width + 4))
    if ann.get("note"):
        lines.extend(wrap(ann["note"], width + 4))
    for f in ann.get("friction", []) or []:
        lines.extend(wrap("! " + theme.FRICTION_LABELS.get(f, f), width + 4))
    if node.get("_problem"):
        lines.append("!! " + node["_problem"].upper())
    return lines


def node_size(node, annotated=True):
    shape = theme.SHAPES.get(node["type"], theme.SHAPES["screen"])
    lines = node_lines(node, annotated=annotated)
    longest = max((len(l) for l in lines), default=0)
    w = max(shape["min_w"], min(300, 22 + longest * 7))
    h = max(shape["min_h"], 24 + len(lines) * 16)
    if node["type"] == "decision":
        w = max(w, 200)
        h = max(h, 90)
    return int(w), int(h)
