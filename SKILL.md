---
name: flowlint
description: >-
  Analyse an existing web or mobile application's codebase and generate editable UX flow
  diagrams (draw.io / .drawio, Mermaid) plus an actionable UX audit. Use this skill whenever
  the user asks to map, chart, document, visualise or diagram user flows, user journeys,
  screen flows, navigation graphs or "the checkout/onboarding/signup/login flow"; whenever
  they ask for a flowchart or flow diagram of an app; whenever they want to find UX friction,
  dead ends, unhandled errors or unnecessary steps in an existing product; whenever they ask
  "how does this flow actually work" about a codebase they inherited; whenever they mention
  draw.io, diagrams.net, Mermaid flowcharts or "akış diyagramı" in the context of an
  application; and whenever they want a before/after comparison of a proposed UX change.
  Works with Next.js, React, React Router, React Native, Expo, Flutter, SwiftUI, UIKit and
  Jetpack Compose codebases.
license: MIT
---

# flowlint

## What this is for

Every application has two flows: the one the designer drew, and the one the code
actually implements. The second one is written down nowhere. Error states, empty
states, cancel paths, permission denials — these are rarely designed. They get
improvised while coding, or left out entirely.

**flowlint extracts the second flow from the code itself.** The value is not a pretty
diagram; it is light on the branches nobody looked at.

Reach for it when the user is:

| Situation | What they get |
| --- | --- |
| Inheriting a codebase | "How does login actually work?" answered in 20 minutes, with file:line anchors |
| Onboarding a developer | A verifiable map instead of tribal knowledge |
| Planning a redesign | You cannot improve what you have not mapped. Current + proposed + measured delta |
| Reviewing a PR | "Does this add a step to checkout?" — answerable automatically |
| Chasing a conversion drop | Analytics says *where* users leave; the flow map shows *why* they can |
| Writing QA cases | Every branch in the diagram is a test case |
| Producing audit documentation | Source-anchored, dated, kept in sync with the code by CI |

**Say so when it does not fit.** flowlint reads existing code, so it cannot design a
flow that has not been written yet, it says nothing about visual design, and it does
not know what real users do — only what the code permits. It complements analytics,
it does not replace them. Where routing is generated dynamically at runtime, the map
will be incomplete, and the report must say so rather than guess.

---

## How it works

| Layer | Who produces it | File |
| --- | --- | --- |
| **IR** — what the flow *is* | you, the agent, by reading code | `docs/ux-flows/<id>.flow.json` |
| **Diagram + report** | `scripts/flowlint.py`, deterministically | `<id>.drawio`, `<id>.md` |

**Never hand-write `.drawio` XML or lay out coordinates.** You write JSON; the renderer
does geometry. That is what makes output reproducible across machines, agents and
reruns, and what keeps git diffs small.

Three files per flow, no more:

```
auth-login.flow.json   the IR you edit
auth-login.drawio      multi-page: [Akış] [Akış + notlar] (+ [Değişim] after a diff)
auth-login.md          the report, with the diagram embedded as Mermaid
```

---

## Non-negotiable rules

1. **Every node derived from code carries a `source` anchor** (`path/to/File.tsx:120`).
   If you cannot point at a line, you do not know it — leave it out, or mark it in
   `annotations.note` as unverified.
2. **Never invent metrics.** `taps`, `required_fields` and friction tags must be
   countable in the code. Do not estimate conversion or timings you have not measured.
3. **Model what the code does, not what it should do.** Improvements belong in a
   separate `-proposed` flow rendered through `flowlint diff`.
4. **Ask before you render.** An app has dozens of flows; the user cares about a few.
5. **Node ids are stable and semantic** (`checkout-payment`, not `node-7`).

---

## Workflow

### Phase 0 — Locate the app and the tool

The renderer can be in three places depending on how flowlint was installed. Find it
once, then use that form for every command in this document. Try in order:

```bash
python3 --version                              # 3.8+ required; no other dependency

flowlint --help                                       # 1. pip install flowlint
python3 "$SKILL_DIR/scripts/flowlint.py" --help       # 2. bundled with this skill
python3 flowlint/scripts/flowlint.py --help           # 3. vendored in the user's repo
```

**Option 2 is the one to remember.** `scripts/flowlint.py` sits next to the `SKILL.md`
you are reading right now. When flowlint is installed as a skill and is not on PATH,
run it from that directory — the working directory is the user's project, not the
skill, so a relative path will not find it. Resolve the absolute path once and reuse it.

Below, `flowlint` stands for whichever form worked.

If `docs/ux-flows/*.flow.json` already exists, this is a **re-run**: read the existing
IR, update it in place, preserve node ids.

### Phase 1 — Inventory the app (read-only)

Detect the stack, then read *only* the matching playbook:

| Detected | Playbook |
| --- | --- |
| `next.config.*`, `app/` or `pages/` | `references/discovery-web.md` |
| `react-navigation`, `expo-router` in `package.json` | `references/discovery-react-native.md` |
| `pubspec.yaml` | `references/discovery-flutter.md` |
| `*.xcodeproj`, `*.swift`, Compose | `references/discovery-native.md` |

Collect: routes/screens, entry points (deep links, notifications, tab roots), guards
(auth, flags, paywalls), transitions, network calls per screen, and per-screen states —
noting especially which states are **missing**.

### Phase 2 — Ask the user which flows to map  *(mandatory)*

Present the candidates you found, named in the user's language. Default suggestions:
sign up / sign in, onboarding, the core value action, paywall, cancellation or account
deletion (almost always the worst flow in the product), error and offline recovery.

Confirm in the same round: output directory (default `docs/ux-flows/`), and whether
they want extra formats (`svg` for README embeds, `mermaid` as a standalone file).

Do not proceed until they answer.

### Phase 3 — Trace each selected flow

Walk from entry point to goal. For each step record the screen/state and its file:line,
what the user must do to move on, what the app does in response, **where failure is
handled**, and every branch: guards, validation, empty results, permission denials,
timeouts, cancellations.

Follow error paths as seriously as the happy path. Most of the value is in the branches
nobody drew before.

Pay attention to four things that are almost always missing, because they produce the
highest-value findings:

- what happens when the user **cancels** an external hand-off (OAuth, 3-D Secure, payment)
- what happens when an out-of-band message (magic link, OTP) **never arrives**
- whether an error carried by a redirect (`?error=...`) is actually **read** at the destination
- whether a permission **denial** has a modelled path

### Phase 4 — Write the IR

One file per flow. Read `references/ir-authoring.md` for the field guide and
`schema/flow.schema.json` for the contract. Then:

```bash
flowlint validate docs/ux-flows/auth-login.flow.json
```

Fix everything it reports. The validator is strict on purpose.

### Phase 5 — Render

```bash
flowlint render docs/ux-flows/*.flow.json -o docs/ux-flows
```

| Switch | Effect |
| --- | --- |
| `--formats drawio,md,svg,mermaid` | default is `drawio,md` |
| `--fail-on-high` | exit 1 when a high-severity finding exists (CI) |

### Phase 6 — Report back

Read `<id>.md` and summarise it for the user in their language:

- the **headline** and the **priority list** — these are the point
- each high-severity finding with its file:line
- where the files are: `.drawio` → drag into [app.diagrams.net](https://app.diagrams.net)
  (second tab has the annotated view); `.md` renders with the diagram inline on GitHub

Then offer the follow-ups: a `-proposed` flow with a measured diff, and CI wiring.

---

## Reading the findings

The diagram shows what *is*. The findings say what is *wrong*, and each one is written
so it can be pasted into an issue tracker unchanged: what the code does, what the user
experiences, what to change, and the evidence.

Each finding has a stable id (`UXF-NOERR-0A7D`). If the team accepts one:

```bash
flowlint ignore UXF-NOERR-0A7D --reason "3. çeyrekte ele alınacak"
```

It moves to an "accepted" section of the report and stops failing CI, but stays visible.
This is what makes `--fail-on-high` adoptable on an existing codebase.

Full guide: `references/findings-guide.md`.

---

## Before/after comparison

```bash
cp docs/ux-flows/checkout.flow.json docs/ux-flows/checkout-proposed.flow.json
# edit the proposed file: remove steps, add error branches, merge screens
flowlint diff docs/ux-flows/checkout.flow.json \
                                      docs/ux-flows/checkout-proposed.flow.json \
                                      -o docs/ux-flows
```

Adds a **Değişim** page to the `.drawio` and a metric-delta table to the report.
**Keep node ids identical for anything that survives the redesign** — that is how the
diff knows a screen was *changed* rather than *replaced*.

---

## Keeping diagrams honest

```yaml
- run: flowlint stale docs/ux-flows/*.flow.json -o docs/ux-flows
- run: flowlint check docs/ux-flows/*.flow.json --fail-on-high
```

`stale` compares each IR's content hash against `.flowlint.lock.json` and fails when
someone edited the IR without regenerating. Copy-ready workflow: `examples/ci/flowlint.yml`.

---

## Reference files

Read on demand, not upfront:

| File | Read it when |
| --- | --- |
| `references/ir-authoring.md` | writing or editing a `.flow.json` |
| `references/findings-guide.md` | explaining the report to the user |
| `references/discovery-web.md` | Next.js / React / React Router app |
| `references/discovery-react-native.md` | React Native or Expo app |
| `references/discovery-flutter.md` | Flutter app |
| `references/discovery-native.md` | SwiftUI, UIKit or Jetpack Compose app |
| `schema/flow.schema.json` | you need the exact field contract |
| `examples/checkout.flow.json` | you want a complete worked example |
