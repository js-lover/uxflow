# Contributing to uxflow

Thanks for helping out. This project has two hard rules and a short setup.

## The two rules

1. **Zero runtime dependencies.** Python 3.8+ standard library only. If a change needs a
   package, it belongs in a separate optional tool, not in `scripts/uxflow_lib/`.
2. **Rendering is deterministic.** The same IR must always produce byte-identical output.
   Never introduce randomness, wall-clock timestamps, set iteration order, or anything derived
   from the filesystem into the layout or the renderers. There is a test for this; keep it green.

## Setup

There is no build step and nothing to install.

```bash
git clone https://github.com/<you>/uxflow.git
cd uxflow
python3 -m unittest discover -s tests -v
```

## Before you open a PR

```bash
python3 -m unittest discover -s tests            # all tests pass
python3 scripts/uxflow.py validate examples/*.flow.json
python3 scripts/uxflow.py render   examples/*.flow.json -o examples/output
git diff --stat examples/output                  # should be empty unless you meant to change output
```

That last line is the important one. If a change to the layout or a renderer alters the example
output, **commit the regenerated files in the same PR** and explain the visual change in the
description. A silent diff in generated artefacts is how this project would rot.

## Adding support for a new stack

This is the most useful contribution and it does not touch the renderer at all.

1. Add `references/discovery-<stack>.md`. Follow the shape of the existing ones:
   - how to detect the stack (concrete files, concrete `package.json` / manifest keys)
   - how to enumerate routes and screens
   - how to find transitions, guards, network calls, per-screen states
   - **grep-able commands**, not prose — the agent runs these
   - a "mapping to IR" table at the end
2. Add the stack to the enum in `schema/flow.schema.json` (`app.stack`).
3. Add a row to the detection table in `SKILL.md` and the list in `AGENTS.md` and `README.md`.

Ground every friction tag in evidence a reader can grep for. A playbook that tells an agent to
guess is worse than no playbook.

## Adding a friction tag

1. `theme.FRICTION_LABELS` — the short label shown inside a diagram node.
2. `catalog.CATALOG["friction:<tag>"]` — **required**: title, severity, confidence, effort,
   and the three texts (`what` / `impact` / `fix`). A finding without a `fix` is noise; the
   test suite enforces this.
3. `schema/flow.schema.json` — the enum.
4. `references/ir-authoring.md` — the "evidence you must have found" row. **Required.** A tag
   with no stated evidence rule will get applied loosely and devalue the whole audit.
5. `references/findings-guide.md` — a row in the rules table.
6. A test in `tests/test_uxflow.py`.

If the tag describes normal behaviour rather than a defect (like `external_handoff`), add it
to `catalog.INFORMATIONAL` instead. Listing non-problems as findings buries the real ones.

## Adding an audit rule

Rules live in `analyze.py` and their prose lives in `catalog.py`. Two things to get right:

- **No false positives.** A rule that cries wolf costs more trust than it earns. Prefer a
  narrow rule that misses cases over a broad one that misfires. `_loop_is_risky` is the model
  here: it ignores cycles containing an action or a form, because those are legitimate retries.
- **Say what to do.** If you cannot write a useful `fix`, the rule is not ready.

## Writing findings text

Write for someone who has not opened the code. `what` is mechanical and verifiable. `impact`
describes a person's experience, concretely — "kullanıcı boş bir ekranda kalır ve aynı butona
tekrar basar", not "kötü kullanıcı deneyimi". `fix` names the change, and mentions the
framework idiom when there is an obvious one.

## Changing the layout

`scripts/uxflow_lib/layout.py` is a layered (Sugiyama-style) pipeline: break cycles → layer →
barycenter ordering → coordinates. If you improve crossing reduction or spacing:

- keep it deterministic and bounded (the barycenter sweep count is fixed on purpose)
- keep `test_no_overlapping_nodes` and `test_deterministic` green
- regenerate `examples/output` and the preview PNGs in the same PR

## Changing the IR schema

The IR is a public contract — people have `.flow.json` files in their repos.

- Additive changes (new optional field, new enum member) are fine within `version: "1.0"`.
- Anything that would invalidate an existing valid file needs a version bump and a migration
  note in the README.

## Reporting a bug

Please include the `.flow.json` that reproduces it (redacted is fine — replace labels and
sources, keep the graph shape), your Python version, and the command you ran.

## Licence

By contributing you agree your work is released under the MIT licence.
