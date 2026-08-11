# flowlint

<!-- banner: docs/banner.png -->

[![CI](https://github.com/js-lover/flowlint/actions/workflows/flowlint.yml/badge.svg)](https://github.com/js-lover/flowlint/actions/workflows/flowlint.yml)
[![PyPI](https://img.shields.io/pypi/v/flowlint.svg)](https://pypi.org/project/flowlint/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A linter for your app's user flows.**

Your linter checks syntax. Your type checker checks types. Nothing checks whether a
user can get *out* of the screen they just landed on.

flowlint reads an existing codebase, maps the flow the code actually implements, and
reports what is wrong with it — dead ends, network calls with no error branch, OAuth
screens with no cancel path. Every finding names a `file:line`.

```bash
pip install flowlint
flowlint check docs/ux-flows/*.flow.json --fail-on-high
```

```
✗ auth-login    4 findings (3 high) · primary path 7 steps · 0 dead ends
    high   Error never shown to the user — /login?error=auth   app/auth/callback/route.ts:17
    high   Waiting on an email with no resend — Sign-in link sent   app/login/page.tsx:68
    high   External hand-off with no cancel path — Google OAuth   app/login/page.tsx:20
```

---

## Why

Every application has two flows: the one the designer drew, and the one the code
implements. The second is written down nowhere. Error states, empty states, cancel
paths, permission denials — rarely designed, usually improvised while coding.

Here is a real finding from the first run against a real app:

> `/auth/callback` redirects to `/login?error=auth` when OAuth fails — but the login
> page never reads that query parameter. A user whose sign-in fails lands on an empty
> login screen with no message, taps the same button, and gets the same result.

Nobody designed that. It is what the code does.

---

## How it works

You (or your agent) describe the flow once as JSON. flowlint does everything else,
deterministically.

```
   you / your agent                 flowlint
   ────────────────                 ────────
   read the code   ──►  flow.json  ──►  <id>.drawio      <id>.md
                        (in git)        (regenerated, never hand-edited)
```

The JSON is the source of truth: it lives next to the code, reviews like code, diffs
like code. The diagrams are build artefacts, and `flowlint stale` fails the PR when
they drift apart. That is what stops flow diagrams from rotting.

Three files per flow:

| File | What it is |
| --- | --- |
| `<flow>.flow.json` | the description you edit |
| `<flow>.drawio` | editable diagram — real shapes on a real canvas, one tab per view |
| `<flow>.md` | the report: summary, action list, diagram inline, metrics, findings |

---

## Quick start

**With an agent** — install as a skill (see [Installing](#installing)), then ask:

> Map the checkout and signup flows in this app and show me where the friction is.

It reads `SKILL.md` (Claude) or `AGENTS.md` (Cursor, Codex, Copilot, Cline, Aider,
Gemini…), inventories your routes, **asks which flows to map**, traces them, and
renders.

**By hand**

```bash
flowlint init checkout -o docs/ux-flows
# describe the flow in docs/ux-flows/checkout.flow.json
flowlint validate docs/ux-flows/checkout.flow.json
flowlint render   docs/ux-flows/checkout.flow.json -o docs/ux-flows
```

**Try it on the bundled examples**

```bash
flowlint check  examples/*.flow.json
flowlint render examples/checkout.flow.json -o /tmp/demo
```

---

## What it catches

Straight from the graph — no heuristics, no guessing.

**Can the user get stuck?** dead ends · screens whose only exit is backwards ·
unreachable nodes · orphans · redirect loops with no way to change the outcome

**What happens when it fails?** network calls with no error branch · external
hand-offs (OAuth, 3-D Secure, payment) with no cancel path · out-of-band waits
(magic link, OTP) with no resend · decisions with one branch

**Is it longer than it needs to be?** step count · taps · required fields · friction
tags, severity-ranked

Plus a model-quality check: nodes with no `source` anchor are flagged, because a claim
you cannot verify weakens the whole map.

### Findings are written to be acted on

Not `no_error_state · "No error state."` Each finding says what the code does, what the
user experiences, what to change, and where — enough to paste into a tracker unchanged.
Each carries a stable id, so a team can accept one without it disappearing:

```bash
flowlint ignore UXF-NOERR-0A7D --reason "scheduled for Q3"
```

It moves to an "accepted" section and stops failing CI. That is what makes
`--fail-on-high` adoptable on a codebase that already exists.

See [`references/findings-guide.md`](references/findings-guide.md) for every rule and
what makes it fire.

---

## Before / after

Model the flow as it is, copy it, fix it, render the delta:

```bash
flowlint diff checkout.flow.json checkout-proposed.flow.json -o docs/ux-flows
```

From `examples/`:

| metric | before | after |
| --- | ---: | ---: |
| steps on the primary path | 9 | 8 |
| required form fields | 14 | 9 |
| modelled error branches | 2 | 6 |
| high-severity findings | 7 | 0 |

A design argument you can take to a stakeholder, with a colour-coded diff diagram to
go with it.

---

## In CI

Copy [`examples/ci/flowlint.yml`](examples/ci/flowlint.yml) into your app. The two
lines that matter:

```yaml
- run: flowlint stale docs/ux-flows/*.flow.json -o docs/ux-flows
- run: flowlint check docs/ux-flows/*.flow.json --fail-on-high
```

`stale` fails when someone edited a flow without regenerating its diagram.
`--fail-on-high` blocks merges that introduce a dead end or an unhandled failure.

---

## Supported stacks

| Stack | Playbook |
| --- | --- |
| Next.js (App + Pages Router), React, React Router, Remix, TanStack | [`discovery-web.md`](references/discovery-web.md) |
| React Native, Expo (Expo Router + React Navigation) | [`discovery-react-native.md`](references/discovery-react-native.md) |
| Flutter (GoRouter, AutoRoute, named routes) | [`discovery-flutter.md`](references/discovery-flutter.md) |
| SwiftUI, UIKit, Jetpack Compose | [`discovery-native.md`](references/discovery-native.md) |

The description format is stack-agnostic — anything you can read, you can model.
Adding a stack means adding one Markdown file; the renderer does not change.

---

## CLI

```
flowlint check    <flow.json>...  lint the flows           [-o DIR] [--fail-on-high]
flowlint render   <flow.json>...  diagram + full report    [-o DIR] [--formats …]
flowlint diff     <before> <after>  before/after + metric delta
flowlint stale    <flow.json>...  CI: diagrams out of sync with their source
flowlint validate <flow.json>...  schema and integrity check
flowlint ignore   <FINDING-ID>    accept a finding         [--reason TEXT]
flowlint init     <flow-id>       scaffold a flow file
flowlint id       <route>         mint a stable node id
```

---

## Installing

**CLI**

```bash
pip install flowlint
```

**Skill in Claude Code** — a skill is a directory with a `SKILL.md`, and the directory
may be a symlink, so the checkout stays current with every `git pull`:

```bash
git clone https://github.com/js-lover/flowlint.git ~/src/flowlint
mkdir -p ~/.claude/skills && ln -s ~/src/flowlint ~/.claude/skills/flowlint
```

Use a project's `.claude/skills/` instead to scope it to one repo.

**Skill in Claude Cowork** — download `flowlint.skill` from
[Releases](https://github.com/js-lover/flowlint/releases) and open it.

**Vendored** — works with any agent, and with none:

```bash
git clone --depth 1 https://github.com/js-lover/flowlint.git && rm -rf flowlint/.git
python3 flowlint/scripts/flowlint.py --help
```

All four run the same code. Zero dependencies is deliberate: the tool has to run
inside whatever environment an agent finds itself in, with no resolver step.

---

## Why it is built this way

**Layout is ours, not draw.io's.** The same input must produce identical geometry
everywhere, or every regeneration is a 400-line diff. flowlint implements a layered
(Sugiyama-style) layout: break cycles → layer → barycenter ordering → coordinates.

**Node ids are stable and semantic.** That is how `diff` tells "this screen changed"
from "this screen was deleted and another added".

**Every node carries a `source` anchor.** A diagram nobody can verify is a diagram
nobody trusts. Hover a box in draw.io and you get `src/app/checkout/payment/page.tsx:24`.

**The primary path is exact, not sampled.** Two earlier versions were wrong in
instructive ways. Following happy edges greedily meant a guard like *"already signed
in? → home"* ended the search after two hops, and every metric described a path no real
user walks. Enumerating paths under a visit budget was worse: a wide fan-out exhausts
the budget and returns a truncated answer *without saying so*. Removing cycle-closing
edges gives a DAG, where longest path is linear and exact. Silently wrong metrics are
the worst kind of bug in a tool people are supposed to trust.

---

## Contributing

```bash
python3 -m unittest discover -s tests -v
```

69 tests, no dependencies. See [CONTRIBUTING.md](CONTRIBUTING.md) — adding a stack is
one Markdown file, and every audit rule has to state precisely when it is right.

## Licence

MIT — see [LICENSE](LICENSE).
