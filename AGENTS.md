# flowlint — instructions for coding agents

> This file is the agent-agnostic entry point. Cursor, Codex, Copilot, Gemini, Cline, Aider and
> any other agent that reads `AGENTS.md` should follow it. Claude Code / Claude Cowork users get
> the same content through `SKILL.md`, which is loaded automatically.

## What you are being asked to do

Read an application's codebase, extract its real user flows, and emit an **editable diagram**
plus an **actionable UX audit**.

The point is not the diagram. Every app has two flows — the one the designer drew and the one
the code implements — and only the first is written down anywhere. Error states, cancel paths,
permission denials and empty states get improvised while coding or left out. Your job is to
surface the second flow, especially its unlit branches.

## The one architectural rule

You write **JSON**, not diagrams.

```
you (agent)                       scripts/flowlint.py (deterministic)
────────────                      ─────────────────────────────────
read the code   ──►  flow.json  ──►  <id>.drawio   <id>.md
```

Three files per flow: the IR you wrote, a multi-page `.drawio` (clean / annotated / diff),
and a report with the diagram embedded as Mermaid.

Never hand-write mxGraph XML. Never compute coordinates. The renderer guarantees that the same
IR produces byte-identical output on every machine — that is what keeps the diagrams
version-controllable.

## Hard constraints

1. Every node derived from code carries `"source": "path/to/File.ext:LINE"`.
2. Never invent numbers. `taps`, `required_fields` and friction tags must be countable in code.
3. Model the code as it is. Proposed improvements go in a separate `-proposed.flow.json`.
4. Ask the user which flows to map before producing anything.
5. Node ids are stable and semantic (`checkout-payment`, never `node-7`).

## Procedure

1. **Detect the stack** and read the one matching playbook:
   - `references/discovery-web.md` — Next.js, React, React Router, Remix, TanStack
   - `references/discovery-react-native.md` — React Native, Expo
   - `references/discovery-flutter.md` — Flutter
   - `references/discovery-native.md` — SwiftUI, UIKit, Jetpack Compose
   - `references/findings-guide.md` — read before explaining the report to the user
2. **Inventory** routes, entry points, guards, transitions, network calls, per-screen states.
3. **Ask the user** which flows to map, which variant (annotated / clean / both), and the
   output directory.
4. **Trace** each chosen flow from entry point to goal, following error branches as seriously
   as the happy path. Four things are almost always missing and produce the most valuable
   findings: what happens when the user **cancels** an external hand-off (OAuth, 3-D Secure);
   what happens when an out-of-band message (magic link, OTP) **never arrives**; whether an
   error carried by a redirect (`?error=...`) is actually **read** at the destination; and
   whether a permission **denial** has a modelled path.
5. **Write the IR** — one `docs/ux-flows/<id>.flow.json` per flow.
   Field guide: `references/ir-authoring.md`. Contract: `schema/flow.schema.json`.
6. **Validate, then render:**

   ```bash
   python3 scripts/flowlint.py validate docs/ux-flows/*.flow.json
   python3 scripts/flowlint.py render   docs/ux-flows/*.flow.json -o docs/ux-flows
   ```

7. **Report** the findings with their file:line anchors, and offer a `-proposed` flow plus a
   `diff` run.

## CLI reference

```
flowlint.py validate <flow.json>...                       schema + integrity check
flowlint.py render   <flow.json>... [-o DIR]              .drawio + report
                   [--formats drawio,md,svg,mermaid]    default: drawio,md
                   [--fail-on-high]
flowlint.py check    <flow.json>... [-o DIR]              report only
flowlint.py diff     <before.json> <after.json> [-o DIR]  before/after + metric delta
flowlint.py check    <flow.json>... [-o DIR]              CI: fail if diagrams are stale
flowlint.py ignore   <FINDING-ID>... [--reason TEXT]      accept a finding, keep it visible
flowlint.py init     <flow-id> [-o DIR]                   scaffold an IR file
flowlint.py id       <route> [component]                  mint a stable node id
```

Requires Python 3.8+. No third-party packages, no network access, no build step.

If `flowlint` is on PATH (`pip install flowlint`), use it directly; otherwise call the
vendored shim, `python3 flowlint/scripts/flowlint.py`. Same code either way.

## If you are a human

Everything above works without an agent. Write the JSON yourself and run the CLI.
See `README.md`.
