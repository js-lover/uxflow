---
name: uxflow
description: >-
  Analyse an existing web or mobile application's codebase and generate editable UX flow
  diagrams (draw.io / .drawio, Mermaid, SVG) plus a static UX audit. Use this skill whenever
  the user asks to map, chart, document, visualise or diagram user flows, user journeys,
  screen flows, navigation graphs or "the checkout/onboarding/signup flow"; whenever they
  ask for a flowchart or flow diagram of an app; whenever they want to find UX friction,
  dead ends or unnecessary steps in an existing product; whenever they mention draw.io,
  diagrams.net, Mermaid flowcharts or "akış diyagramı" in the context of an application;
  and whenever they want a before/after comparison of a proposed UX change. Works with
  Next.js, React, React Native, Expo, Flutter, SwiftUI, UIKit and Jetpack Compose codebases.
license: MIT
---

# uxflow

Turn an application's real navigation and interaction code into **editable, version-controlled
flow diagrams** and a **static UX audit**.

Two-layer design, and it matters:

| Layer | Who produces it | File |
| --- | --- | --- |
| **IR** — what the flow *is* | you, the agent, by reading code | `docs/ux-flows/<id>.flow.json` |
| **Diagrams** — what it *looks like* | `scripts/uxflow.py`, deterministically | `.drawio`, `.mmd`, `.svg`, `.findings.md` |

**Never hand-write `.drawio` XML or lay out coordinates yourself.** You write JSON; the
renderer does geometry. This is what makes output reproducible across machines, agents and
reruns, and what keeps git diffs small.

---

## Non-negotiable rules

1. **Every node you derive from code carries a `source` anchor** (`path/to/File.tsx:120`).
   If you cannot point at a line, you do not know it — mark the node
   `"kind": "edge"` and say so in `annotations.note`, or leave it out.
2. **Never invent metrics.** `taps`, `required_fields` and friction tags must be countable in
   the code. Do not estimate conversion rates, drop-off or timings you have not measured. Real
   analytics numbers, if the user supplies them, go in the top-level `metrics` object.
3. **Model what the code does, not what it should do.** Improvements belong in a separate
   `-proposed` flow file rendered through `uxflow.py diff`.
4. **Ask before you render.** An app has dozens of flows; the user cares about a handful.
   Phase 2 below is mandatory.
5. **Node ids are stable and semantic** (`checkout-payment`, not `node-7`). Regenerating a
   diagram must not reshuffle ids. Use `python3 scripts/uxflow.py id /checkout/payment PaymentPage`
   when in doubt.

---

## Workflow

### Phase 0 — Locate the app and the tool

Confirm the repository root. Then check the runtime:

```bash
python3 --version          # 3.8+ required; no other dependency
python3 scripts/uxflow.py --help
```

If the project already has `docs/ux-flows/*.flow.json`, this is a **re-run**: read the existing
IR first, update it in place, and preserve node ids. Do not start from scratch.

### Phase 1 — Inventory the app (read-only, no output yet)

Detect the stack, then follow the matching playbook:

| Detected | Playbook |
| --- | --- |
| `next.config.*`, `app/` or `pages/` | `references/discovery-web.md` |
| `react-navigation`, `expo-router` in `package.json` | `references/discovery-react-native.md` |
| `pubspec.yaml` | `references/discovery-flutter.md` |
| `*.xcodeproj`, `*.swift`, or `MainActivity.kt` + Compose | `references/discovery-native.md` |

Read only the playbook you need. Each one tells you exactly which files to grep and what the
route/screen declarations look like.

Produce an internal inventory (do not write it to disk yet):

- **routes / screens** — path, component, file:line
- **entry points** — deep links, push notification targets, tab roots, launch screen
- **guards** — auth middleware, feature flags, paywalls, permission gates
- **transitions** — every `router.push`, `navigate(...)`, `Navigator.push`, `NavigationLink`
- **network calls per screen** — which endpoints a screen hits and where errors are handled
- **states per screen** — loading, empty, error, success (note which are *missing*)

### Phase 2 — Ask the user which flows to map  *(mandatory)*

Present the candidate flows you found, grouped and named in the user's language, and ask them
to choose. Offer sensible defaults — the flows that carry the most value in almost every app:

- sign up / sign in (including social and OTP variants)
- onboarding / first run
- the core value action (checkout, booking, publish, transfer — whatever this app is for)
- paywall / subscription
- account deletion or cancellation (almost always the worst flow in the product, and the one
  nobody has ever drawn)
- error and offline recovery

Also confirm, in the same round of questions:

- **variant** — annotated, clean, or both (default: both)
- **swimlanes** — user / UI / backend split, or a single column (default: lanes on, because
  the user chose full depth including API calls)
- **output directory** (default `docs/ux-flows/`)

Do not proceed until the user has answered.

### Phase 3 — Trace each selected flow

For one flow at a time, walk the code from the entry point to the goal. For each step record:

- the screen or state the user is in, and its file:line
- what the user must do to move on (and how many interactions that takes)
- what the app does in response — including the network call and **where the failure is handled**
- every branch: guards, validation failures, empty results, permission denials, timeouts

Follow error paths as seriously as the happy path. The value of this whole exercise is mostly
in the branches nobody drew before.

When you find a `catch` that only logs, a screen with no empty state, a modal with no dismiss,
a destructive action with no confirm — tag it with the matching `friction` value. The tag must
correspond to code you actually read.

### Phase 4 — Write the IR

One file per flow: `docs/ux-flows/<flow-id>.flow.json`.

Read `references/ir-authoring.md` for the field-by-field guide and worked examples, and
`schema/flow.schema.json` for the exact contract. Then validate before rendering:

```bash
python3 scripts/uxflow.py validate docs/ux-flows/checkout.flow.json
```

Fix every reported problem. The validator is strict on purpose.

### Phase 5 — Render

```bash
python3 scripts/uxflow.py render docs/ux-flows/*.flow.json -o docs/ux-flows
```

Useful switches:

| Switch | Effect |
| --- | --- |
| `--variant annotated\|clean\|both` | annotated carries friction + counts; clean is presentation-ready |
| `--formats drawio,mermaid,svg,md` | pick a subset |
| `--fail-on-high` | exit 1 when a high-severity finding exists (CI) |
| `--no-audit` | skip the audit pass |

Outputs per flow: with the default `--variant both` you get `<id>.annotated.drawio`,
`<id>.clean.drawio`, `.mmd`, `.svg` and `<id>.findings.md`. Asking for a single variant drops
the infix — `--variant clean` writes `<id>.drawio`, not `<id>.clean.drawio`. A
`.uxflow.lock.json` records the IR hash for `check`.

`uxflow.py audit <flow>` prints the findings to stdout without writing anything (pass `-o DIR`
to write `findings.md` instead) — useful while you are still iterating on the IR.

`uxflow.py init <flow-id> -o docs/ux-flows` scaffolds a minimal, valid IR file if you would
rather start from a skeleton than a blank page.

### Phase 6 — Report back

Summarise in the user's language:

- how many flows were mapped, and the primary-path step count for each
- the high-severity findings, each with its file:line
- where the files are, and how to open them (`.drawio` → drag into
  [app.diagrams.net](https://app.diagrams.net) or the VS Code *Draw.io Integration* extension;
  `.mmd` renders inline in GitHub Markdown; `.svg` opens in any browser)

Then offer the follow-ups the user probably wants:

- **a proposed flow** — copy the IR to `<id>-proposed.flow.json`, apply the improvements, and
  run `diff` to quantify them
- **CI wiring** — `uxflow.py check` in a workflow so diagrams cannot go stale

---

## Before/after comparison

This is the feature that makes the diagrams a design tool rather than documentation.

```bash
cp docs/ux-flows/checkout.flow.json docs/ux-flows/checkout-proposed.flow.json
# edit the proposed file: give it a new `id`, then
# remove steps, add error branches, merge screens
python3 scripts/uxflow.py diff docs/ux-flows/checkout.flow.json \
                               docs/ux-flows/checkout-proposed.flow.json \
                               -o docs/ux-flows
```

Output is named after the *second* file plus `-diff`, so this writes
`checkout-proposed-diff.drawio/.mmd/.svg`, colour-coded added / removed / changed, plus
`checkout-proposed-diff.md` with the metric delta (steps, screens, taps, required fields,
error branches, findings per severity) and the list of findings the redesign resolves or
introduces.

**Keep node ids identical between the two files for anything that survives the redesign** —
that is how the diff knows a screen was *changed* rather than *replaced*.

---

## Keeping diagrams honest

Add to CI:

```yaml
- run: python3 scripts/uxflow.py check docs/ux-flows/*.flow.json -o docs/ux-flows
```

`check` compares each IR's content hash against `.uxflow.lock.json` and fails when someone
edited the IR without regenerating. Pair it with `render --fail-on-high` to block merges that
introduce a dead end or an unhandled network failure.

---

## What the audit detects

Structural, from the graph alone: unreachable nodes, orphans, dead ends, screens whose only
exit is backwards, API calls with no error branch, decisions with a single branch, and flows
deeper than six steps. Plus every `friction` tag you recorded, severity-ranked.

The audit never invents a problem. If it flags something, it is because the graph says so — and
the node carries a `source` anchor so the user can go look.

---

## Reference files

Read on demand, not upfront:

| File | Read it when |
| --- | --- |
| `references/ir-authoring.md` | writing or editing a `.flow.json` |
| `references/discovery-web.md` | Next.js / React / React Router app |
| `references/discovery-react-native.md` | React Native or Expo app |
| `references/discovery-flutter.md` | Flutter app |
| `references/discovery-native.md` | SwiftUI, UIKit or Jetpack Compose app |
| `schema/flow.schema.json` | you need the exact field contract |
| `examples/checkout.flow.json` | you want a complete, realistic worked example |
