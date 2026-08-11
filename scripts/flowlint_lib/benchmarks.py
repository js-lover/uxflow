"""Interpretation thresholds for metrics.

A bare number does not help anyone decide anything. "9 steps" means nothing until
you know that six is where flows start losing people. Every metric therefore ships
with a verdict and a one-line reason.

Thresholds are deliberately conservative and stated as rules of thumb, not laws --
they are here to prompt a conversation, not to end one.
"""

GOOD, WARN, BAD, INFO = "good", "warn", "bad", "info"

ICON = {GOOD: "✓", WARN: "!", BAD: "✗", INFO: "·"}
VERDICT_LABEL = {GOOD: "good", WARN: "watch", BAD: "problem", INFO: "info"}


def _band(value, good_max, warn_max):
    if value <= good_max:
        return GOOD
    if value <= warn_max:
        return WARN
    return BAD


RULES = {
    "primary_path_steps": {
        "label": "Steps on the primary path",
        "band": lambda v: _band(v, 6, 9),
        "note": {
            GOOD: "a reasonable length",
            WARN: "above six — every extra step costs users",
            BAD:  "above nine — consider splitting the flow or merging steps",
        },
    },
    "screens_on_primary_path": {
        "label": "Screens on the primary path",
        "band": lambda v: _band(v, 4, 6),
        "note": {
            GOOD: "reasonable",
            WARN: "creeping up — could any of these be combined?",
            BAD:  "too many screen transitions",
        },
    },
    "taps_on_primary_path": {
        "label": "Interactions on the primary path",
        "band": lambda v: _band(v, 8, 14),
        "note": {
            GOOD: "light interaction load",
            WARN: "interaction load is climbing",
            BAD:  "the user is doing a lot of tapping",
        },
    },
    "required_fields": {
        "label": "Required form fields (total)",
        "band": lambda v: _band(v, 6, 12),
        "note": {
            GOOD: "few required fields",
            WARN: "every required field is a chance to give up — are they all needed?",
            BAD:  "heavy form load; split the fields or defer them",
        },
    },
    "failure_exits": {
        "label": "Ways to end up stuck",
        "band": lambda v: _band(v, 0, 2),
        "note": {
            GOOD: "no point where the user gets trapped",
            WARN: "there are places a user stalls short of the goal",
            BAD:  "many dead ends — this flow is not dependable",
        },
    },
    "error_branch_coverage": {
        "label": "Error-branch coverage",
        "band": lambda v: BAD if v < 50 else (WARN if v < 100 else GOOD),
        "unit": "%",
        "note": {
            GOOD: "every network call has a modelled failure path",
            WARN: "some network calls have no failure path",
            BAD:  "most network calls have no failure path",
        },
    },
    "source_coverage": {
        "label": "Source-anchor coverage",
        "band": lambda v: BAD if v < 80 else (WARN if v < 100 else GOOD),
        "unit": "%",
        "note": {
            GOOD: "every node traces back to a line of code",
            WARN: "some nodes cannot be verified",
            BAD:  "a large share of nodes is not grounded in code — read this map with care",
        },
    },
}

# Reported without a verdict: descriptive, not judgeable out of context.
PLAIN = {
    "screens": "Screens",
    "api_calls": "Network calls",
    "decisions": "Decision points",
    "error_branches": "Modelled error branches",
    "nodes": "Nodes",
    "edges": "Transitions",
}


def evaluate(metrics):
    """-> [{key, label, value, unit, verdict, note}] in report order."""
    out = []
    for key, rule in RULES.items():
        if key not in metrics:
            continue
        v = metrics[key]
        verdict = rule["band"](v)
        out.append({
            "key": key, "label": rule["label"], "value": v,
            "unit": rule.get("unit", ""), "verdict": verdict,
            "note": rule["note"][verdict],
        })
    for key, label in PLAIN.items():
        if key in metrics:
            out.append({"key": key, "label": label, "value": metrics[key],
                        "unit": "", "verdict": INFO, "note": ""})
    return out


def headline(metrics, findings):
    """One plain sentence describing the state of the flow."""
    high = [f for f in findings if f["severity"] == "high"]
    med = [f for f in findings if f["severity"] == "medium"]
    steps = metrics.get("primary_path_steps", 0)
    fails = metrics.get("failure_exits", 0)

    if not findings:
        return ("No structural problems found in this flow. The primary path is %d "
                "steps and there is nowhere a user gets stuck." % steps)

    parts = []
    if high:
        parts.append("%d that affect users directly" % len(high))
    if med:
        parts.append("%d of medium priority" % len(med))
    detail = ", ".join(parts) if parts else "all of them low priority"

    sentence = "This flow has %d finding%s: %s." % (
        len(findings), "" if len(findings) == 1 else "s", detail)
    if fails:
        sentence += (" There %s %d distinct way%s to end up stuck short of the goal."
                     % ("is" if fails == 1 else "are", fails, "" if fails == 1 else "s"))
    sentence += " The primary path is %d steps." % steps
    return sentence
