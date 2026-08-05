"""uxflow test suite -- standard library unittest, no dependencies.

    python3 -m unittest discover -s tests -v
"""

import copy
import json
import os
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from uxflow_lib import analyze, diffing, drawio, ir, layout, mermaid, svg  # noqa: E402

EXAMPLE = os.path.join(ROOT, "examples", "checkout.flow.json")
PROPOSED = os.path.join(ROOT, "examples", "checkout-proposed.flow.json")


def minimal(**over):
    doc = {
        "version": "1.0", "id": "t", "title": "T",
        "nodes": [
            {"id": "a", "type": "start", "label": "A"},
            {"id": "b", "type": "screen", "label": "B"},
            {"id": "c", "type": "end", "label": "C"},
        ],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
    }
    doc.update(over)
    return ir.normalize(doc)


class TestValidation(unittest.TestCase):
    def test_example_is_valid(self):
        doc = ir.load(EXAMPLE)
        self.assertEqual(doc["id"], "checkout")
        self.assertTrue(len(doc["nodes"]) > 10)

    def test_requires_start_node(self):
        doc = {"version": "1.0", "id": "t", "title": "T",
               "nodes": [{"id": "a", "type": "screen", "label": "A"}], "edges": []}
        with self.assertRaises(ir.IRError):
            ir.validate(doc)

    def test_rejects_dangling_edge(self):
        doc = {"version": "1.0", "id": "t", "title": "T",
               "nodes": [{"id": "a", "type": "start", "label": "A"}],
               "edges": [{"from": "a", "to": "ghost"}]}
        with self.assertRaises(ir.IRError):
            ir.validate(doc)

    def test_rejects_duplicate_ids(self):
        doc = {"version": "1.0", "id": "t", "title": "T",
               "nodes": [{"id": "a", "type": "start", "label": "A"},
                         {"id": "a", "type": "end", "label": "A2"}],
               "edges": []}
        with self.assertRaises(ir.IRError):
            ir.validate(doc)

    def test_rejects_unknown_friction_tag(self):
        doc = {"version": "1.0", "id": "t", "title": "T",
               "nodes": [{"id": "a", "type": "start", "label": "A",
                          "annotations": {"friction": ["made_up_tag"]}}],
               "edges": []}
        with self.assertRaises(ir.IRError):
            ir.validate(doc)

    def test_requires_lane_when_lanes_declared(self):
        doc = {"version": "1.0", "id": "t", "title": "T",
               "lanes": [{"id": "ui", "label": "UI"}],
               "nodes": [{"id": "a", "type": "start", "label": "A"}],
               "edges": []}
        with self.assertRaises(ir.IRError):
            ir.validate(doc)


class TestHashing(unittest.TestCase):
    def test_hash_is_stable_across_key_order(self):
        a = ir.load(EXAMPLE)
        with open(EXAMPLE, encoding="utf-8") as fh:
            raw = json.load(fh)
        raw["nodes"] = list(reversed(raw["nodes"]))
        raw["edges"] = list(reversed(raw["edges"]))
        b = ir.normalize(raw)
        self.assertEqual(ir.content_hash(a), ir.content_hash(b))

    def test_hash_changes_with_content(self):
        a = ir.load(EXAMPLE)
        b = copy.deepcopy(a)
        b["nodes"][1]["label"] = "Something else"
        self.assertNotEqual(ir.content_hash(a), ir.content_hash(b))

    def test_render_annotations_do_not_change_hash(self):
        doc = ir.load(EXAMPLE)
        before = ir.content_hash(doc)
        analyze.audit(doc)                     # injects _problem markers
        self.assertEqual(before, ir.content_hash(doc))

    def test_stable_id_is_deterministic(self):
        self.assertEqual(ir.stable_id("/checkout/payment", "PaymentPage"),
                         ir.stable_id("/checkout/payment", "PaymentPage"))
        self.assertTrue(ir.ID_RE.match(ir.stable_id("/a/[very]/long/" + "x" * 90, "Comp")))


class TestLayout(unittest.TestCase):
    def setUp(self):
        self.doc = ir.load(EXAMPLE)
        self.lay = layout.compute(self.doc, annotated=True)

    def test_no_overlapping_nodes(self):
        g = self.lay["nodes"]
        ids = list(g)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = g[ids[i]], g[ids[j]]
                overlap = (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and
                           a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"])
                self.assertFalse(overlap, "%s overlaps %s" % (ids[i], ids[j]))

    def test_every_node_positioned(self):
        self.assertEqual(set(self.lay["nodes"]), {n["id"] for n in self.doc["nodes"]})

    def test_start_is_at_the_top(self):
        ys = {k: v["y"] for k, v in self.lay["nodes"].items()}
        self.assertEqual(min(ys, key=ys.get), "start")

    def test_deterministic(self):
        again = layout.compute(ir.load(EXAMPLE), annotated=True)
        self.assertEqual(self.lay["nodes"], again["nodes"])

    def test_handles_cycles(self):
        doc = minimal(edges=[{"from": "a", "to": "b"}, {"from": "b", "to": "c"},
                             {"from": "c", "to": "b"}])
        lay = layout.compute(doc)
        self.assertEqual(len(lay["nodes"]), 3)

    def test_lanes_produce_boxes(self):
        self.assertEqual(len(self.lay["lanes"]), 3)
        for box in self.lay["lanes"]:
            self.assertGreater(box["w"], 0)
            self.assertGreater(box["h"], 0)

    def test_lr_direction_transposes(self):
        doc = ir.load(EXAMPLE)
        doc["direction"] = "LR"
        lr = layout.compute(doc)
        self.assertGreater(lr["width"], lr["height"])


class TestRenderers(unittest.TestCase):
    def setUp(self):
        self.doc = ir.load(EXAMPLE)
        analyze.audit(self.doc)
        self.lay = layout.compute(self.doc, annotated=True)

    def test_drawio_is_wellformed_xml(self):
        xml = drawio.render(self.doc, self.lay)
        root = ET.fromstring(xml.split("\n", 1)[1] if xml.startswith("<?xml") else xml)
        self.assertEqual(root.tag, "mxfile")

    def test_drawio_contains_every_node_and_edge(self):
        xml = drawio.render(self.doc, self.lay)
        for n in self.doc["nodes"]:
            self.assertIn('"n-%s"' % n["id"], xml)
        self.assertEqual(xml.count('edge="1"'), len(self.doc["edges"]))

    def test_drawio_labels_are_not_double_escaped(self):
        xml = drawio.render(self.doc, self.lay)
        self.assertNotIn("&amp;lt;br&amp;gt;", xml)
        self.assertIn("&lt;br&gt;", xml)

    def test_drawio_carries_source_tooltips(self):
        xml = drawio.render(self.doc, self.lay)
        self.assertIn("src/app/checkout/payment/page.tsx:24", xml)

    def test_svg_is_wellformed(self):
        out = svg.render(self.doc, self.lay)
        root = ET.fromstring(out)
        self.assertTrue(root.tag.endswith("svg"))

    def test_mermaid_comments_use_double_percent(self):
        out = mermaid.render(self.doc)
        for line in out.splitlines():
            if "Generated by uxflow" in line or "->" in line and line.startswith("%"):
                self.assertTrue(line.startswith("%%"), line)

    def test_mermaid_balances_subgraphs(self):
        out = mermaid.render(self.doc)
        opens = sum(1 for l in out.splitlines() if l.strip().startswith("subgraph"))
        closes = sum(1 for l in out.splitlines() if l.strip() == "end")
        self.assertEqual(opens, closes)

    def test_mermaid_escapes_quotes(self):
        doc = minimal()
        doc["nodes"][1]["label"] = 'He said "hi" #1'
        out = mermaid.render(doc)
        self.assertIn("#quot;", out)
        self.assertNotIn('"hi"', out)

    def test_mermaid_avoids_reserved_words(self):
        doc = minimal()
        doc["nodes"][2]["id"] = "end"
        doc["edges"][1]["to"] = "end"
        doc["_index"] = {n["id"]: n for n in doc["nodes"]}
        out = mermaid.render(doc)
        self.assertNotIn("\n    end([", out)

    def test_clean_variant_drops_annotations(self):
        node = self.doc["_index"]["signup"]
        annotated = ir.node_lines(node, annotated=True)
        clean = ir.node_lines(node, annotated=False)
        self.assertGreater(len(annotated), len(clean))
        self.assertEqual(clean, ["Create an account"])


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.doc = ir.load(EXAMPLE)
        self.report = analyze.audit(self.doc)
        self.codes = {f["code"] for f in self.report["findings"]}

    def test_finds_dead_end(self):
        self.assertIn("deadend", self.codes)

    def test_finds_api_without_error_branch(self):
        self.assertIn("no_error_branch", self.codes)
        offender = [f for f in self.report["findings"] if f["code"] == "no_error_branch"][0]
        self.assertEqual(offender["node"], "charge")

    def test_does_not_flag_api_with_error_branch(self):
        offenders = [f["node"] for f in self.report["findings"] if f["code"] == "no_error_branch"]
        self.assertNotIn("shipping-api", offenders)

    def test_modal_with_dismiss_is_not_a_dead_end(self):
        deadends = [f["node"] for f in self.report["findings"] if f["code"] == "deadend"]
        self.assertNotIn("promo-modal", deadends)

    def test_back_edges_excluded_from_depth(self):
        self.assertLess(self.report["metrics"]["primary_path_steps"], len(self.doc["nodes"]))

    def test_finds_unreachable_node(self):
        doc = minimal()
        doc["nodes"].append({"id": "ghost", "type": "screen", "label": "Ghost", "kind": "neutral",
                             "annotations": {}})
        doc["_index"]["ghost"] = doc["nodes"][-1]
        report = analyze.audit(doc)
        self.assertIn("unreachable", {f["code"] for f in report["findings"]})

    def test_markdown_report_renders(self):
        md = analyze.to_markdown(self.doc, self.report)
        self.assertIn("# UX audit", md)
        self.assertIn("Primary path", md)
        self.assertIn("src/app/checkout/declined/page.tsx:9", md)

    def test_findings_carry_source_anchors(self):
        with_source = [f for f in self.report["findings"] if f["node"] and f["label"]]
        self.assertTrue(any(f["source"] for f in with_source))


class TestDiff(unittest.TestCase):
    def setUp(self):
        self.before = ir.load(EXAMPLE)
        self.after = ir.load(PROPOSED)
        self.merged, self.summary = diffing.diff(self.before, self.after)

    def test_classifies_added_removed_changed(self):
        self.assertIn("charge-error", [n["id"] for n in self.summary["added"]])
        self.assertIn("signup", [n["id"] for n in self.summary["removed"]])
        self.assertTrue(self.summary["changed"])

    def test_stable_ids_are_reported_as_changed_not_replaced(self):
        changed = {n["id"] for n, _, _ in self.summary["changed"]}
        self.assertIn("address", changed)
        self.assertNotIn("address", [n["id"] for n in self.summary["added"]])

    def test_merged_graph_renders(self):
        lay = layout.compute(self.merged, annotated=True)
        xml = drawio.render(self.merged, lay, mode="diff")
        ET.fromstring(xml.split("\n", 1)[1])

    def test_markdown_shows_metric_delta(self):
        md = diffing.to_markdown(self.before, self.after, self.summary)
        self.assertIn("Metric delta", md)
        self.assertIn("high-severity findings", md)

    def test_proposal_actually_improves_metrics(self):
        rb = analyze.audit(ir.load(EXAMPLE))
        ra = analyze.audit(ir.load(PROPOSED))
        self.assertLess(ra["metrics"]["required_fields"], rb["metrics"]["required_fields"])
        self.assertGreater(ra["metrics"]["error_branches"], rb["metrics"]["error_branches"])
        self.assertLess(len([f for f in ra["findings"] if f["severity"] == "high"]),
                        len([f for f in rb["findings"] if f["severity"] == "high"]))


class TestCLI(unittest.TestCase):
    def test_end_to_end(self):
        import shutil
        import tempfile
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import uxflow as cli

        tmp = tempfile.mkdtemp()
        try:
            self.assertEqual(cli.main(["validate", EXAMPLE]), 0)
            self.assertEqual(cli.main(["render", EXAMPLE, "-o", tmp]), 0)
            for suffix in (".annotated.drawio", ".clean.drawio", ".annotated.mmd",
                           ".annotated.svg", ".findings.md"):
                self.assertTrue(os.path.exists(os.path.join(tmp, "checkout" + suffix)), suffix)
            self.assertEqual(cli.main(["check", EXAMPLE, "-o", tmp]), 0)
            self.assertEqual(cli.main(["diff", EXAMPLE, PROPOSED, "-o", tmp]), 0)

            # tamper with the IR -> check must fail
            tampered = os.path.join(tmp, "tampered.flow.json")
            doc = ir.load(EXAMPLE)
            doc["nodes"][1]["label"] = "Changed"
            ir.dump(doc, tampered)
            self.assertEqual(cli.main(["check", tampered, "-o", tmp]), 1)

            self.assertEqual(cli.main(["init", "onboarding", "-o", tmp]), 0)
            self.assertEqual(cli.main(["validate", os.path.join(tmp, "onboarding.flow.json")]), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
