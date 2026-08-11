"""Colors, shapes and label rules. Single source of truth for every renderer."""

# --- semantic colors -------------------------------------------------------
KIND_COLORS = {
    "happy":   {"fill": "#E7F5EA", "stroke": "#2E7D32", "text": "#14532D"},
    "error":   {"fill": "#FDEAEA", "stroke": "#C62828", "text": "#7F1D1D"},
    "edge":    {"fill": "#FFF6E0", "stroke": "#B8860B", "text": "#78350F"},
    "neutral": {"fill": "#F4F4F5", "stroke": "#71717A", "text": "#27272A"},
}

# problems injected by analyze.py
PROBLEM_COLORS = {
    "deadend":     {"fill": "#FCE4EC", "stroke": "#AD1457", "text": "#831843"},
    "orphan":      {"fill": "#EDE9FE", "stroke": "#6D28D9", "text": "#4C1D95"},
    "unreachable": {"fill": "#E0E7FF", "stroke": "#3730A3", "text": "#312E81"},
}

DIFF_COLORS = {
    "added":     {"fill": "#DCFCE7", "stroke": "#15803D", "text": "#14532D"},
    "removed":   {"fill": "#FEE2E2", "stroke": "#B91C1C", "text": "#7F1D1D"},
    "changed":   {"fill": "#FEF3C7", "stroke": "#B45309", "text": "#78350F"},
    "unchanged": {"fill": "#F4F4F5", "stroke": "#A1A1AA", "text": "#52525B"},
}

LANE_DEFAULT_COLORS = ["#F8FAFC", "#F1F5F9", "#F8FAFC", "#F1F5F9", "#F8FAFC"]

# --- shapes ----------------------------------------------------------------
# drawio: extra style fragments appended after the color block
# mermaid: (open, close) delimiters around the quoted label
SHAPES = {
    "start":    {"drawio": "ellipse;whiteSpace=wrap;html=1;",
                 "mermaid": ('(["', '"])'), "min_w": 140, "min_h": 50},
    "end":      {"drawio": "ellipse;whiteSpace=wrap;html=1;",
                 "mermaid": ('(["', '"])'), "min_w": 140, "min_h": 50},
    "screen":   {"drawio": "rounded=1;arcSize=8;whiteSpace=wrap;html=1;",
                 "mermaid": ('["', '"]'), "min_w": 190, "min_h": 60},
    "modal":    {"drawio": "rounded=1;arcSize=8;dashed=1;dashPattern=8 4;whiteSpace=wrap;html=1;",
                 "mermaid": ('["', '"]'), "min_w": 190, "min_h": 60},
    "action":   {"drawio": "rounded=0;whiteSpace=wrap;html=1;",
                 "mermaid": ('["', '"]'), "min_w": 170, "min_h": 50},
    "decision": {"drawio": "rhombus;whiteSpace=wrap;html=1;",
                 "mermaid": ('{"', '"}'), "min_w": 190, "min_h": 90},
    "api":      {"drawio": "shape=parallelogram;perimeter=parallelogramPerimeter;fixedSize=1;size=18;whiteSpace=wrap;html=1;",
                 "mermaid": ('[/"', '"/]'), "min_w": 200, "min_h": 55},
    "data":     {"drawio": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=12;whiteSpace=wrap;html=1;",
                 "mermaid": ('[("', '")]'), "min_w": 170, "min_h": 70},
    "state":    {"drawio": "rounded=1;arcSize=40;dashed=1;whiteSpace=wrap;html=1;",
                 "mermaid": ('("', '")'), "min_w": 170, "min_h": 50},
    "external": {"drawio": "shape=offPageConnector;whiteSpace=wrap;html=1;",
                 "mermaid": ('[["', '"]]'), "min_w": 170, "min_h": 60},
    "note":     {"drawio": "shape=note;whiteSpace=wrap;html=1;size=14;",
                 "mermaid": ('["', '"]'), "min_w": 170, "min_h": 55},
}

EDGE_STYLES = {
    "happy":   "strokeColor=#2E7D32;strokeWidth=2;",
    "error":   "strokeColor=#C62828;dashed=1;dashPattern=6 4;",
    "edge":    "strokeColor=#B8860B;dashed=1;dashPattern=2 3;",
    "back":    "strokeColor=#71717A;dashed=1;dashPattern=1 3;endArrow=open;",
    "neutral": "strokeColor=#52525B;",
}

FRICTION_LABELS = {
    "blocking_modal":         "blocking modal",
    "no_loading_state":       "no loading state",
    "no_error_state":         "no error state",
    "no_empty_state":         "no empty state",
    "no_back_affordance":     "no way back",
    "hidden_cta":             "CTA below the fold",
    "long_form":              "long form",
    "forced_signup":          "forced signup",
    "unskippable":            "cannot be skipped",
    "destructive_no_confirm": "destructive, no confirm",
    "silent_failure":         "fails silently",
    "duplicate_input":        "re-asks known data",
    "external_handoff":       "leaves the app",
    "permission_prompt":      "OS permission prompt",
}

# friction items that are severe enough to flag in findings
SEVERE_FRICTION = {
    "no_error_state", "silent_failure", "destructive_no_confirm",
    "no_back_affordance", "forced_signup",
}


def colors_for(node, mode="normal"):
    """Resolve the fill/stroke/text triple for a node."""
    if mode == "diff":
        return DIFF_COLORS.get(node.get("_diff", "unchanged"), DIFF_COLORS["unchanged"])
    problem = node.get("_problem")
    if problem and problem in PROBLEM_COLORS:
        return PROBLEM_COLORS[problem]
    return KIND_COLORS.get(node.get("kind", "neutral"), KIND_COLORS["neutral"])
