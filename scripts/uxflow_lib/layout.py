"""Deterministic layered (Sugiyama-lite) layout. Standard library only.

Why we do layout ourselves instead of letting draw.io / mermaid auto-arrange:
  * the same IR must produce byte-identical geometry on every machine, so that
    regenerated diagrams create minimal git diffs;
  * swimlane placement needs to be exact, and neither tool guarantees it.

Pipeline: break cycles -> layer -> order (barycenter) -> assign coordinates.
"""

from . import ir

H_GAP = 46          # horizontal gap between sibling nodes
V_GAP = 62          # vertical gap between ranks
LANE_PAD = 28       # padding inside a lane
LANE_HEADER = 34    # lane title bar height
MARGIN = 40


# ------------------------------------------------------------------ graph prep
def _adjacency(doc):
    out, inc = {}, {}
    for n in doc["nodes"]:
        out[n["id"]] = []
        inc[n["id"]] = []
    for e in doc["edges"]:
        if e.get("kind") == "back":
            continue                      # back edges never influence layering
        out[e["from"]].append(e["to"])
        inc[e["to"]].append(e["from"])
    return out, inc


def _back_edges(out, starts, node_ids):
    """Iterative DFS colouring; returns the set of edges that close a cycle."""
    color = dict.fromkeys(node_ids, 0)     # 0 white, 1 grey, 2 black
    found = set()
    roots = list(starts) + [n for n in node_ids if n not in starts]
    for root in roots:
        if color[root]:
            continue
        color[root] = 1
        stack = [(root, iter(out[root]))]
        while stack:
            node, it = stack[-1]
            pushed = False
            for nxt in it:
                c = color.get(nxt, 0)
                if c == 1:
                    found.add((node, nxt))
                elif c == 0:
                    color[nxt] = 1
                    stack.append((nxt, iter(out[nxt])))
                    pushed = True
                    break
            if not pushed:
                color[node] = 2
                stack.pop()
    return found


def _rank(doc, out, inc, starts):
    """Longest-path layering on the DAG obtained after removing back edges."""
    ids = [n["id"] for n in doc["nodes"]]
    back = _back_edges(out, starts, ids)
    dag_out = {k: [v for v in vs if (k, v) not in back] for k, vs in out.items()}
    dag_in = {k: [] for k in ids}
    for a, vs in dag_out.items():
        for b in vs:
            dag_in[b].append(a)

    rank = {}
    indeg = {k: len(v) for k, v in dag_in.items()}
    queue = [k for k in ids if indeg[k] == 0]
    queue.sort()
    # prefer explicit start nodes at rank 0
    for s in starts:
        if s in queue:
            queue.remove(s)
            queue.insert(0, s)
    for k in queue:
        rank[k] = 0
    processed = 0
    while queue:
        node = queue.pop(0)
        processed += 1
        for nxt in dag_out[node]:
            rank[nxt] = max(rank.get(nxt, 0), rank[node] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    for k in ids:                          # safety net for pathological graphs
        rank.setdefault(k, 0)
    return rank, back


# -------------------------------------------------------------------- ordering
def _order(doc, rank, out, inc):
    """Barycenter sweeps to reduce edge crossings. Deterministic and bounded."""
    by_rank = {}
    for n in doc["nodes"]:
        by_rank.setdefault(rank[n["id"]], []).append(n["id"])
    for r in by_rank:
        by_rank[r].sort()                  # deterministic seed

    pos = {}
    for r, ids in by_rank.items():
        for i, nid in enumerate(ids):
            pos[nid] = float(i)

    for sweep in range(6):
        ranks = sorted(by_rank)
        if sweep % 2:
            ranks = list(reversed(ranks))
        for r in ranks:
            neighbours = inc if sweep % 2 == 0 else out
            scored = []
            for i, nid in enumerate(by_rank[r]):
                ns = [pos[x] for x in neighbours.get(nid, []) if rank.get(x) != r]
                bary = sum(ns) / len(ns) if ns else pos[nid]
                scored.append((bary, pos[nid], nid))
            scored.sort()
            by_rank[r] = [nid for _, _, nid in scored]
            for i, nid in enumerate(by_rank[r]):
                pos[nid] = float(i)
    return by_rank


# ----------------------------------------------------------------- coordinates
def compute(doc, annotated=True):
    """Return {'nodes': {id: {x,y,w,h}}, 'lanes': [...], 'width':, 'height':,
    'rank': {...}, 'back_edges': set}."""
    out, inc = _adjacency(doc)
    starts = [n["id"] for n in doc["nodes"] if n["type"] == "start"]
    rank, back = _rank(doc, out, inc, starts)
    by_rank = _order(doc, rank, out, inc)

    idx = ir.index(doc)
    size = {n["id"]: ir.node_size(n, annotated) for n in doc["nodes"]}

    lanes = doc.get("lanes") or []
    horizontal = doc.get("direction", "TD") == "LR"

    if lanes:
        geom, lane_boxes, w, h = _lane_layout(doc, by_rank, rank, size, idx, lanes)
    else:
        geom, w, h = _plain_layout(by_rank, size)
        lane_boxes = []

    if horizontal:
        geom, lane_boxes, w, h = _transpose(geom, lane_boxes, w, h)

    return {"nodes": geom, "lanes": lane_boxes, "width": w, "height": h,
            "rank": rank, "back_edges": back, "by_rank": by_rank}


def _plain_layout(by_rank, size):
    rows = []
    for r in sorted(by_rank):
        ids = by_rank[r]
        row_w = sum(size[i][0] for i in ids) + H_GAP * (len(ids) - 1)
        rows.append((r, ids, row_w))
    total_w = max((rw for _, _, rw in rows), default=200)

    geom = {}
    y = MARGIN
    for r, ids, row_w in rows:
        x = MARGIN + (total_w - row_w) / 2.0
        row_h = max(size[i][1] for i in ids)
        for nid in ids:
            w, h = size[nid]
            geom[nid] = {"x": round(x), "y": round(y + (row_h - h) / 2.0), "w": w, "h": h}
            x += w + H_GAP
        y += row_h + V_GAP
    return geom, int(total_w + MARGIN * 2), int(y - V_GAP + MARGIN)


def _lane_layout(doc, by_rank, rank, size, idx, lanes):
    lane_ids = [l["id"] for l in lanes]
    lane_of = {}
    for n in doc["nodes"]:
        lane_of[n["id"]] = n.get("lane") or lane_ids[0]

    # width each lane needs = widest (lane, rank) cell
    lane_w = {}
    for lid in lane_ids:
        widest = 0
        for r, ids in by_rank.items():
            cell = [i for i in ids if lane_of[i] == lid]
            if not cell:
                continue
            widest = max(widest, sum(size[i][0] for i in cell) + H_GAP * (len(cell) - 1))
        lane_w[lid] = max(200, widest) + LANE_PAD * 2

    lane_x, x = {}, MARGIN
    for lid in lane_ids:
        lane_x[lid] = x
        x += lane_w[lid]
    total_w = x - MARGIN

    geom = {}
    y = MARGIN + LANE_HEADER
    for r in sorted(by_rank):
        ids = by_rank[r]
        row_h = max(size[i][1] for i in ids)
        for lid in lane_ids:
            cell = [i for i in ids if lane_of[i] == lid]
            if not cell:
                continue
            cell_w = sum(size[i][0] for i in cell) + H_GAP * (len(cell) - 1)
            cx = lane_x[lid] + (lane_w[lid] - cell_w) / 2.0
            for nid in cell:
                w, h = size[nid]
                geom[nid] = {"x": round(cx), "y": round(y + (row_h - h) / 2.0), "w": w, "h": h}
                cx += w + H_GAP
        y += row_h + V_GAP
    content_h = y - V_GAP + LANE_PAD

    lane_boxes = []
    for i, l in enumerate(lanes):
        lane_boxes.append({
            "id": l["id"], "label": l["label"],
            "x": lane_x[l["id"]], "y": MARGIN,
            "w": lane_w[l["id"]], "h": content_h - MARGIN,
            "color": l.get("color"), "i": i,
        })
    return geom, lane_boxes, int(total_w + MARGIN * 2), int(content_h + MARGIN)


def _transpose(geom, lane_boxes, w, h):
    ng = {k: {"x": v["y"], "y": v["x"], "w": v["w"], "h": v["h"]} for k, v in geom.items()}
    nl = [dict(b, x=b["y"], y=b["x"], w=b["h"], h=b["w"]) for b in lane_boxes]
    return ng, nl, h, w
