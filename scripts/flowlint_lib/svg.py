"""Standalone SVG renderer -- for README embeds and PR previews. No dependencies,
no headless browser, uses the same layout as the draw.io output."""

from xml.sax.saxutils import escape

from . import ir, theme

FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif"
LINE_H = 16


def render(doc, lay, annotated=True, mode="normal"):
    w, h = lay["width"] + 40, lay["height"] + 60
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'font-family="%s">' % (w, h, w, h, FONT)]
    o.append('<rect width="100%" height="100%" fill="#FFFFFF"/>')
    o.append('<defs>')
    for name, c in list(theme.KIND_COLORS.items()) + list(theme.DIFF_COLORS.items()):
        o.append('<marker id="arrow-%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                 'markerHeight="7" orient="auto-start-reverse">'
                 '<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker>' % (name, c["stroke"]))
    o.append('<marker id="arrow-back" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
             'markerHeight="7" orient="auto-start-reverse">'
             '<path d="M 0 0 L 10 5 L 0 10 z" fill="#71717A"/></marker>')
    o.append('</defs>')
    o.append('<text x="20" y="30" font-size="18" font-weight="700" fill="#18181B">%s</text>'
             % escape(doc["title"]))

    off_y = 34
    for box in lay["lanes"]:
        color = box.get("color") or theme.LANE_DEFAULT_COLORS[box["i"] % len(theme.LANE_DEFAULT_COLORS)]
        o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="#CBD5E1" rx="4"/>'
                 % (box["x"], box["y"] + off_y, box["w"], box["h"], color))
        o.append('<text x="%d" y="%d" font-size="13" font-weight="600" fill="#334155">%s</text>'
                 % (box["x"] + 12, box["y"] + off_y + 22, escape(box["label"])))

    idx = ir.index(doc)
    # Occupied rectangles: node boxes first, then each label we place. Labels are
    # nudged until they land somewhere free, so nothing overlaps by accident.
    occupied = [(g["x"], g["y"] + off_y, g["x"] + g["w"], g["y"] + g["h"] + off_y)
                for g in lay["nodes"].values()]
    corridors = {}
    for i, e in enumerate(doc["edges"]):
        o.append(_edge(e, lay, idx, off_y, annotated, mode, i, occupied, corridors))
    for n in doc["nodes"]:
        o.append(_node(n, lay["nodes"][n["id"]], off_y, annotated, mode))

    o.append("</svg>")
    return "\n".join(o) + "\n"


def _node(node, g, off_y, annotated, mode):
    c = theme.colors_for(node, mode)
    x, y, w, h = g["x"], g["y"] + off_y, g["w"], g["h"]
    t = node["type"]
    sw = 3 if node.get("_problem") else 2
    dash = ' stroke-dasharray="7 4"' if t in ("modal", "state") else ""

    if t in ("start", "end"):
        shape = ('<ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="%s" stroke="%s" stroke-width="%d"/>'
                 % (x + w / 2, y + h / 2, w / 2, h / 2, c["fill"], c["stroke"], sw))
    elif t == "decision":
        pts = "%g,%g %g,%g %g,%g %g,%g" % (x + w / 2, y, x + w, y + h / 2, x + w / 2, y + h, x, y + h / 2)
        shape = '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%d"/>' % (pts, c["fill"], c["stroke"], sw)
    elif t == "api":
        k = 16
        pts = "%g,%g %g,%g %g,%g %g,%g" % (x + k, y, x + w, y, x + w - k, y + h, x, y + h)
        shape = '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%d"/>' % (pts, c["fill"], c["stroke"], sw)
    elif t == "data":
        ry = 9
        shape = ('<path d="M %g %g a %g %g 0 0 0 %g 0 l 0 %g a %g %g 0 0 1 -%g 0 z" fill="%s" stroke="%s" stroke-width="%d"/>'
                 '<path d="M %g %g a %g %g 0 0 0 %g 0" fill="none" stroke="%s" stroke-width="%d"/>'
                 % (x, y + ry, w / 2, ry, w, h - 2 * ry, w / 2, ry, w, c["fill"], c["stroke"], sw,
                    x, y + ry, w / 2, ry, w, c["stroke"], sw))
    elif t == "external":
        pts = "%g,%g %g,%g %g,%g %g,%g %g,%g" % (x, y, x + w, y, x + w, y + h - 14,
                                                 x + w / 2, y + h, x, y + h - 14)
        shape = '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%d"/>' % (pts, c["fill"], c["stroke"], sw)
    else:
        rx = 20 if t == "state" else (0 if t == "action" else 8)
        shape = ('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" stroke="%s" stroke-width="%d"%s/>'
                 % (x, y, w, h, rx, c["fill"], c["stroke"], sw, dash))

    lines = ir.node_lines(node, annotated=annotated)
    total = len(lines) * LINE_H
    ty = y + h / 2 - total / 2 + 12
    text = []
    for i, l in enumerate(lines):
        weight = "600" if i == 0 else "400"
        size = 12 if i == 0 else 10.5
        fill = c["text"] if i == 0 else "#52525B"
        if l.startswith("!"):
            fill = "#B91C1C"
        text.append('<text x="%g" y="%g" font-size="%s" font-weight="%s" fill="%s" text-anchor="middle">%s</text>'
                    % (x + w / 2, ty + i * LINE_H, size, weight, fill, escape(l)))
    title = '<title>%s</title>' % escape(node.get("source") or node.get("route") or node["id"])
    return "<g>" + title + shape + "".join(text) + "</g>"


def _overlaps(rect, occupied):
    x1, y1, x2, y2 = rect
    for ox1, oy1, ox2, oy2 in occupied:
        if x1 < ox2 and ox1 < x2 and y1 < oy2 and oy1 < y2:
            return True
    return False


def _place_label(cx, cy, w, h, occupied):
    """Find a free spot near (cx, cy) by stepping away vertically."""
    for step in range(0, 9):
        for direction in ((1, -1) if step else (1,)):
            oy = cy + direction * step * (h + 3)
            rect = (cx - w / 2, oy - h + 3, cx + w / 2, oy + 3)
            if not _overlaps(rect, occupied):
                occupied.append(rect)
                return oy
    return cy


def _edge(e, lay, idx, off_y, annotated, mode, idx_hint=0, occupied=None, corridors=None):
    occupied = occupied if occupied is not None else []
    corridors = corridors if corridors is not None else {}
    a, b = lay["nodes"][e["from"]], lay["nodes"][e["to"]]
    kind = e.get("kind", "neutral")
    stroke = {"happy": "#2E7D32", "error": "#C62828", "edge": "#B8860B",
              "back": "#71717A"}.get(kind, "#52525B")
    dash = ' stroke-dasharray="6 4"' if kind in ("error", "edge", "back") else ""
    width = 2 if kind == "happy" else 1.5

    x1, y1 = a["x"] + a["w"] / 2, a["y"] + a["h"] + off_y
    x2, y2 = b["x"] + b["w"] / 2, b["y"] + off_y
    label_at = None
    if b["y"] < a["y"]:                      # upward (back) edge: leave from the side
        x1, y1 = a["x"] + a["w"], a["y"] + a["h"] / 2 + off_y
        x2, y2 = b["x"] + b["w"], b["y"] + b["h"] / 2 + off_y
        mid = max(x1, x2) + 40
        d = "M %g %g H %g V %g H %g" % (x1, y1, mid, y2, x2)
        label_at = (mid, (y1 + y2) / 2)
    elif abs(x1 - x2) < 4:
        d = "M %g %g L %g %g" % (x1, y1, x2, y2)
    else:
        # Horizontal runs between the same pair of ranks would sit on top of each
        # other; give each one its own corridor a few pixels apart.
        key = (round(y1), round(y2))
        slot = corridors.setdefault(key, 0)
        corridors[key] = slot + 1
        my = (y1 + y2) / 2 + (slot - 1) * 11
        my = min(max(my, y1 + 12), y2 - 12) if y2 - y1 > 26 else (y1 + y2) / 2
        d = "M %g %g V %g H %g V %g" % (x1, y1, my, x2, y2)
        label_at = ((x1 + x2) / 2, my)

    marker = "arrow-back" if kind == "back" else "arrow-%s" % (
        kind if kind in theme.KIND_COLORS else "neutral")
    out = ['<path d="%s" fill="none" stroke="%s" stroke-width="%g"%s marker-end="url(#%s)"/>'
           % (d, stroke, width, dash, marker)]

    label = e.get("label", "")
    if annotated and e.get("condition"):
        label = (label + " [" + e["condition"] + "]").strip()
    if label:
        lx, ly = label_at or ((x1 + x2) / 2, (y1 + y2) / 2)
        lw, lh = len(label) * 6.0, 15
        ly = _place_label(lx, ly, lw, lh, occupied)
        out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#FFFFFF" opacity="0.92" rx="2"/>'
                   % (lx - lw / 2, ly - 11, lw, lh))
        out.append('<text x="%g" y="%g" font-size="10.5" fill="#3F3F46" text-anchor="middle">%s</text>'
                   % (lx, ly, escape(label)))
    return "".join(out)
