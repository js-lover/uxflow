"""flowlint test suite -- standard library unittest, no dependencies.

    python3 -m unittest discover -s tests -v
"""

import copy
import json
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from flowlint_lib import (analyze, benchmarks, catalog, diffing, drawio, ir,  # noqa: E402
                        layout, mermaid, report, svg)

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

    def _assert_no_overlap(self, lay, where):
        g = lay["nodes"]
        ids = list(g)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = g[ids[i]], g[ids[j]]
                overlap = (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and
                           a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"])
                self.assertFalse(overlap, "%s overlaps %s (%s)" % (ids[i], ids[j], where))

    def test_no_overlapping_nodes(self):
        self._assert_no_overlap(self.lay, "TD")

    def test_no_overlapping_nodes_lr(self):
        """LR laid out with untransposed box sizes used to overlap: the packer
        spaced siblings by their height while they were still full width."""
        doc = ir.load(EXAMPLE)
        doc["direction"] = "LR"
        self._assert_no_overlap(layout.compute(doc, annotated=True), "LR")

    def test_box_sizes_are_direction_independent(self):
        doc = ir.load(EXAMPLE)
        doc["direction"] = "LR"
        lr = layout.compute(doc, annotated=True)
        for node in doc["nodes"]:
            w, h = ir.node_size(node, True)
            geom = lr["nodes"][node["id"]]
            self.assertEqual((geom["w"], geom["h"]), (w, h), node["id"])

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
            if "Generated by flowlint" in line or "->" in line and line.startswith("%"):
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

    def test_mermaid_escapes_shape_terminators(self):
        """A single raw "(" in a label aborts the whole diagram with a parse error.

        Real labels look like "Silinemedi (Alert)" and "Bitiş < başlangıç", which
        is exactly how this was found.
        """
        doc = minimal()
        doc["nodes"][1]["label"] = "Silinemedi (Alert) [x] {y} a<b>c c|d"
        doc["edges"][1]["label"] = "iptal (kalmaya devam)"
        out = mermaid.render(doc)
        for raw, code in (("(", "#40;"), (")", "#41;"), ("[", "#91;"), ("]", "#93;"),
                          ("{", "#123;"), ("}", "#125;"), ("<", "#60;"), (">", "#62;")):
            self.assertIn(code, out, raw)
        for line in out.splitlines():
            body = line.strip()
            if body.startswith("%%") or body.startswith("class") or "subgraph" in body:
                continue
            for chunk in re.findall(r'"([^"]*)"', body):
                # <br/> is the one piece of markup Mermaid wants inside a label
                self.assertNotRegex(chunk.replace("<br/>", ""), r"[()\[\]{}|<>]", body)

    def test_mermaid_quotes_every_node_label(self):
        """An unquoted label is one stray character away from a parse error."""
        doc = ir.load(EXAMPLE)
        out = mermaid.render(doc, annotated=False)
        idx = ir.index(doc)
        for node in doc["nodes"]:
            mid = mermaid._mid(node["id"])
            for line in out.splitlines():
                if line.strip().startswith(mid + "(") or line.strip().startswith(mid + "["):
                    self.assertIn('"', line, line)
                    break

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
        md = report.render(self.doc, self.report)
        self.assertIn("flow report", md)
        self.assertIn("## Primary path", md)
        self.assertIn("## What to do", md)
        self.assertIn("src/app/checkout/declined/page.tsx:9", md)

    def test_report_ends_with_a_machine_readable_block(self):
        """An agent should not have to parse prose to get the facts."""
        md = report.render(self.doc, self.report)
        self.assertIn("## Machine-readable summary", md)
        blob = md.split("```json", 1)[1].split("```", 1)[0]
        payload = json.loads(blob)
        self.assertEqual(payload["flow"], self.doc["id"])
        self.assertEqual(len(payload["findings"]), len(self.report["findings"]))
        self.assertIn("failure_exits", payload["metrics"])

    def test_metrics_and_findings_do_not_contradict(self):
        """A report claiming no problems while counting dead ends is incoherent.

        `failure_exits` used to count any node without a forward edge, which
        flagged every error toast whose single edge back to the form is the
        correct design.
        """
        for path in (EXAMPLE, PROPOSED):
            rep = analyze.audit(ir.load(path))
            stuck = {f["code"] for f in rep["findings"]} & {"deadend", "only_exit_is_back"}
            if not stuck:
                self.assertEqual(rep["metrics"]["failure_exits"], 0, path)

    def test_report_embeds_the_diagram(self):
        md = report.render(self.doc, self.report, embed_diagram=True)
        self.assertIn("```mermaid", md)
        self.assertIn("flowchart TD", md)

    def test_findings_carry_source_anchors(self):
        anchored = [f for f in self.report["findings"] if f["node"] and f["label"]]
        self.assertTrue(any(f["evidence"] for f in anchored))

    def test_findings_are_actionable(self):
        """Every finding must say what to do; a finding without a fix is noise."""
        for f in self.report["findings"]:
            self.assertTrue(f["title"], f["code"])
            self.assertTrue(f["what"], f["code"])
            self.assertTrue(f["impact"], f["code"])
            self.assertTrue(f["fix"], f["code"])
            self.assertIn(f["severity"], ("high", "medium", "low"))
            self.assertIn(f["effort"], ("S", "M", "L"))

    def test_finding_ids_are_stable(self):
        again = analyze.audit(ir.load(EXAMPLE))
        self.assertEqual([f["id"] for f in self.report["findings"]],
                         [f["id"] for f in again["findings"]])

    def test_suppression_moves_findings_aside(self):
        target = self.report["findings"][0]["id"]
        muted = analyze.audit(ir.load(EXAMPLE), suppressed={target})
        self.assertNotIn(target, [f["id"] for f in muted["findings"]])
        self.assertIn(target, [f["id"] for f in muted["suppressed"]])

    def test_informational_tags_are_not_findings(self):
        codes = {f["code"] for f in self.report["findings"]}
        self.assertNotIn("friction:external_handoff", codes)
        self.assertTrue(any(i["tag"] == "external_handoff" for i in self.report["info"]))

    def test_terminals_do_not_count_as_steps(self):
        path = self.report["primary_path"]
        idx = ir.index(self.doc)
        terminals = sum(1 for n in path if idx[n]["type"] in ("start", "end"))
        self.assertEqual(self.report["metrics"]["primary_path_steps"],
                         len(path) - terminals)

    def test_primary_path_is_exact_on_a_branchy_graph(self):
        """A wide subgraph explored first must not hide a deeper branch.

        The earlier path search enumerated simple paths under a fixed visit
        budget; a fan-out big enough to exhaust it made the search return a
        truncated depth without saying so. The layered search is exact.
        """
        doc = minimal()
        doc["nodes"] = [n for n in doc["nodes"] if n["type"] == "start"]
        doc["edges"] = []
        start = doc["nodes"][0]["id"]

        def screen(nid):
            n = {"id": nid, "type": "screen", "label": nid, "lane": "ui",
                 "kind": "happy", "source": "src/x.tsx:1", "annotations": {}}
            doc["nodes"].append(n)
            return nid

        # wide branch: 18-node complete forward DAG, ~65k simple paths, depth 18
        wide = [screen("w%02d" % i) for i in range(18)]
        doc["edges"].append({"from": start, "to": wide[0], "kind": "happy"})
        for i in range(len(wide)):
            for j in range(i + 1, len(wide)):
                doc["edges"].append({"from": wide[i], "to": wide[j], "kind": "happy"})
        # deep branch: a plain 40-step chain, declared second
        deep = [screen("d%02d" % i) for i in range(40)]
        doc["edges"].append({"from": start, "to": deep[0], "kind": "happy"})
        for i in range(len(deep) - 1):
            doc["edges"].append({"from": deep[i], "to": deep[i + 1], "kind": "happy"})
        doc["_index"] = {n["id"]: n for n in doc["nodes"]}

        report = analyze.audit(doc)
        self.assertEqual(report["metrics"]["primary_path_steps"], len(deep))
        self.assertEqual(report["primary_path"][-1], deep[-1])

    def test_primary_path_prefers_happy_edges(self):
        doc = minimal()
        doc["_index"] = {n["id"]: n for n in doc["nodes"]}
        report = analyze.audit(doc)
        kinds = {(e["from"], e["to"]): e.get("kind") for e in doc["edges"]}
        path = report["primary_path"]
        walked = [kinds.get((a, b)) for a, b in zip(path, path[1:])]
        self.assertNotIn("back", walked)


class TestNoFalsePositives(unittest.TestCase):
    """Adversarial graphs, every one of which made a rule misfire at least once.

    A rule that cries wolf costs more trust than it earns, so each of these is a
    healthy flow that must come back clean -- paired with the minimal broken
    variant that must still be caught.
    """

    @staticmethod
    def _n(nid, typ, label, **kw):
        node = {"id": nid, "type": typ, "label": label, "source": "src/x.tsx:1"}
        node.update(kw)
        return node

    def _codes(self, nodes, edges):
        doc = ir.normalize({"version": "1.0", "id": "t", "title": "T",
                            "nodes": nodes, "edges": edges})
        return {f["code"] for f in analyze.audit(doc)["findings"]}

    def test_clipboard_state_is_not_an_unanswered_wait(self):
        """'Bağlantı kopyalandı' mentions a link, but nothing was sent."""
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("btn", "action", "Kopyala"),
             self._n("copied", "state", "Baglanti kopyalandi"), self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "btn", "kind": "happy"},
             {"from": "btn", "to": "copied", "kind": "happy"},
             {"from": "copied", "to": "e", "kind": "happy"}])
        self.assertNotIn("waiting_no_resend", codes)

    def test_wait_hint_does_not_match_inside_other_words(self):
        """`lien` once matched inside "client-side" and flagged a plain redirect."""
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("api", "api", "POST /auth"),
             self._n("redir", "state", "/login?error=auth",
                     annotations={"note": "the only visible error comes from "
                                          "client-side auth calls"}),
             self._n("login", "screen", "Login"), self._n("e", "end", "Done")],
            [{"from": "s", "to": "api", "kind": "happy"},
             {"from": "api", "to": "redir", "kind": "error"},
             {"from": "api", "to": "e", "kind": "happy"},
             {"from": "redir", "to": "login", "kind": "neutral"},
             {"from": "login", "to": "api", "kind": "happy"}])
        self.assertNotIn("waiting_no_resend", codes)

    def test_magic_link_without_resend_is_caught(self):
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("send", "api", "POST /otp"),
             self._n("sent", "state", "Giris baglantisi gonderildi"),
             self._n("cb", "api", "GET /cb"), self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "send", "kind": "happy"},
             {"from": "send", "to": "sent", "kind": "happy"},
             {"from": "send", "to": "sent", "kind": "error"},
             {"from": "sent", "to": "cb", "kind": "happy"},
             {"from": "cb", "to": "e", "kind": "happy"},
             {"from": "cb", "to": "e", "kind": "error"}])
        self.assertIn("waiting_no_resend", codes)

    def test_magic_link_with_resend_is_clean(self):
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("send", "api", "POST /otp"),
             self._n("sent", "state", "Giris baglantisi gonderildi"),
             self._n("cb", "api", "GET /cb"), self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "send", "kind": "happy"},
             {"from": "send", "to": "sent", "kind": "happy"},
             {"from": "send", "to": "sent", "kind": "error"},
             {"from": "sent", "to": "send", "label": "tekrar gonder", "kind": "edge"},
             {"from": "sent", "to": "cb", "kind": "happy"},
             {"from": "cb", "to": "e", "kind": "happy"},
             {"from": "cb", "to": "e", "kind": "error"}])
        self.assertEqual(codes, set())

    def test_cycle_with_an_exit_is_not_a_trap(self):
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("a", "screen", "A"),
             self._n("b", "screen", "B2"), self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "a", "kind": "happy"},
             {"from": "a", "to": "b", "kind": "happy"},
             {"from": "b", "to": "a", "kind": "neutral"},
             {"from": "b", "to": "e", "kind": "happy"}])
        self.assertNotIn("redirect_loop", codes)

    def test_cycle_without_an_exit_is_caught(self):
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("a", "screen", "A"),
             self._n("b", "screen", "B2"), self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "a", "kind": "happy"},
             {"from": "a", "to": "b", "kind": "happy"},
             {"from": "b", "to": "a", "kind": "neutral"},
             {"from": "s", "to": "e", "kind": "happy"}])
        self.assertIn("redirect_loop", codes)

    def test_external_with_cancel_branch_is_clean(self):
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("x", "external", "3DS"),
             self._n("ok", "screen", "Onay"), self._n("no", "state", "Iptal edildi"),
             self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "x", "kind": "happy"},
             {"from": "x", "to": "ok", "kind": "happy"},
             {"from": "x", "to": "no", "kind": "error"},
             {"from": "ok", "to": "e", "kind": "happy"},
             {"from": "no", "to": "s", "kind": "back"}])
        self.assertEqual(codes, set())

    def test_external_without_cancel_branch_is_caught(self):
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("x", "external", "3DS"),
             self._n("ok", "screen", "Onay"), self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "x", "kind": "happy"},
             {"from": "x", "to": "ok", "kind": "happy"},
             {"from": "ok", "to": "e", "kind": "happy"}])
        self.assertIn("external_no_return", codes)

    def test_terminal_external_is_not_flagged(self):
        """Leaving for the app store and never coming back is not a missing branch."""
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("x", "external", "App Store"),
             self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "x", "kind": "happy"},
             {"from": "s", "to": "e", "kind": "happy"}])
        self.assertNotIn("external_no_return", codes)

    def test_dismissable_modal_is_not_a_dead_end(self):
        codes = self._codes(
            [self._n("s", "start", "B"), self._n("scr", "screen", "Ekran"),
             self._n("m", "modal", "Bilgi"), self._n("e", "end", "Bitti")],
            [{"from": "s", "to": "scr", "kind": "happy"},
             {"from": "scr", "to": "m", "kind": "edge"},
             {"from": "m", "to": "scr", "kind": "back"},
             {"from": "scr", "to": "e", "kind": "happy"}])
        self.assertEqual(codes, set())


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


class TestPackaging(unittest.TestCase):
    """The same code has to serve two entry points: the installed console script
    (`flowlint` -> flowlint.cli:main) and a vendored checkout run with no install."""

    def test_cli_module_lives_inside_the_package(self):
        from flowlint_lib import cli
        self.assertTrue(callable(cli.main))

    def test_package_modules_use_relative_imports(self):
        """An absolute `import flowlint_lib` would break once installed as `flowlint`."""
        pkg = os.path.join(ROOT, "scripts", "flowlint_lib")
        for name in os.listdir(pkg):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(pkg, name), encoding="utf-8") as fh:
                body = fh.read()
            self.assertNotIn("from flowlint_lib import", body, name)
            self.assertNotIn("import flowlint_lib", body, name)

    def test_version_matches_pyproject(self):
        from flowlint_lib import __version__
        with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("version = "):
                    self.assertEqual(line.split('"')[1], __version__)
                    return
        self.fail("pyproject.toml has no version")

    def test_user_facing_text_is_english(self):
        """The report is what a stranger reads first, so it is part of the public
        interface. This project was written in Turkish before it was published; the
        guard exists so that does not creep back one string at a time.

        `analyze._WAIT_HINT` is exempt: it matches labels users write in their own
        language, and narrowing it to English would miss locked-out users.
        """
        turkish = re.compile(r"[çğıİöşüÇĞÖŞÜ]")
        for name in ("catalog.py", "benchmarks.py", "report.py", "cli.py"):
            path = os.path.join(ROOT, "scripts", "flowlint_lib", name)
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    self.assertIsNone(turkish.search(line),
                                      "%s:%d is not English: %s" % (name, lineno, line.strip()))

    def test_every_catalog_entry_is_complete(self):
        """A finding with no fix is noise, and a missing key would render as blank."""
        for code, entry in catalog.CATALOG.items():
            for key in ("title", "severity", "confidence", "effort", "what", "impact", "fix"):
                self.assertIn(key, entry, code)
                self.assertTrue(str(entry[key]).strip(), "%s.%s is empty" % (code, key))
            self.assertIn(entry["severity"], ("high", "medium", "low"), code)
            self.assertIn(entry["effort"], ("S", "M", "L"), code)
            self.assertIn(entry["confidence"], ("certain", "likely"), code)

    def test_documented_commands_all_exist(self):
        """Every subcommand named in a workflow or a doc must be a real one.

        Renaming `check` to `stale` left the CI workflow calling a command that
        had quietly changed meaning; the step passed a tampered IR and the build
        broke. Grep the tree for invocations and check them against the parser.
        """
        from flowlint_lib import cli
        parser = cli.build_parser()
        known = set()
        for action in parser._subparsers._group_actions:
            known |= set(action.choices)

        # Only real invocations. Prose like "the flowlint repository" must not
        # be mistaken for a command, so the bare form has to sit at the start of
        # a line or right after a backtick -- where a command actually appears.
        invocation = re.compile(r"\bflowlint(?:\.py)? ([a-z][a-z-]*)")
        skip = {"install"}                                 # `pip install flowlint`
        roots = [os.path.join(ROOT, p) for p in
                 (".github/workflows", "examples/ci", "README.md", "SKILL.md",
                  "AGENTS.md", "CONTRIBUTING.md", "references")]
        seen = set()
        for root in roots:
            paths = [root]
            if os.path.isdir(root):
                paths = [os.path.join(root, f) for f in sorted(os.listdir(root))]
            for path in paths:
                if not os.path.isfile(path):
                    continue
                with open(path, encoding="utf-8") as fh:
                    body = fh.read()
                for line in self._command_lines(path, body):
                    for word in invocation.findall(line):
                        if word in skip:
                            continue
                        seen.add(word)
                        self.assertIn(word, known,
                                      "%s calls `flowlint %s`, which is not a command"
                                      % (os.path.relpath(path, ROOT), word))
        self.assertIn("check", seen)      # the docs must actually show the main command
        self.assertIn("stale", seen)

    @staticmethod
    def _command_lines(path, body):
        """Only places a command can actually live.

        Scanning whole files means matching prose -- "flowlint reads an existing
        codebase" is not an invocation of `flowlint reads`. So: fenced code blocks
        and inline backticks in Markdown, and `flowlint.py` lines in YAML.
        """
        if path.endswith((".yml", ".yaml")):
            return [l for l in body.splitlines() if "flowlint.py" in l]

        lines, fenced = [], False
        for line in body.splitlines():
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                lines.append(line)
            else:
                lines.extend(re.findall(r"`([^`]*)`", line))
        return lines

    def test_shim_stays_thin(self):
        """Logic in the shim would only run for vendored users, not installed ones."""
        with open(os.path.join(ROOT, "scripts", "flowlint.py"), encoding="utf-8") as fh:
            code = [l for l in fh if l.strip() and not l.strip().startswith("#")]
        self.assertLess(len(code), 30)


class TestCLI(unittest.TestCase):
    def test_end_to_end(self):
        import shutil
        import tempfile
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import flowlint as cli

        tmp = tempfile.mkdtemp()
        try:
            self.assertEqual(cli.main(["validate", EXAMPLE]), 0)
            self.assertEqual(cli.main(["render", EXAMPLE, "-o", tmp]), 0)
            for suffix in (".drawio", ".md"):
                self.assertTrue(os.path.exists(os.path.join(tmp, "checkout" + suffix)), suffix)
            self.assertEqual(cli.main(["stale", EXAMPLE, "-o", tmp]), 0)
            self.assertEqual(cli.main(["diff", EXAMPLE, PROPOSED, "-o", tmp]), 0)

            # `check` is the headline command: it lints, and only --fail-on-high
            # turns findings into a non-zero exit.
            self.assertEqual(cli.main(["check", EXAMPLE]), 0)
            self.assertEqual(cli.main(["check", EXAMPLE, "--fail-on-high"]), 1)
            self.assertEqual(cli.main(["audit", EXAMPLE]), 0)      # kept as an alias

            # tamper with the IR -> check must fail
            tampered = os.path.join(tmp, "tampered.flow.json")
            doc = ir.load(EXAMPLE)
            doc["nodes"][1]["label"] = "Changed"
            ir.dump(doc, tampered)
            self.assertEqual(cli.main(["stale", tampered, "-o", tmp]), 1)

            self.assertEqual(cli.main(["init", "onboarding", "-o", tmp]), 0)
            self.assertEqual(cli.main(["validate", os.path.join(tmp, "onboarding.flow.json")]), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
