# Authoring the flow IR

The IR is the only thing you write by hand. Get it right and every output format follows.
Contract: `schema/flow.schema.json`. Worked example: `examples/checkout.flow.json`.

## Skeleton

```json
{
  "version": "1.0",
  "id": "checkout",
  "title": "Guest checkout",
  "description": "From cart to order confirmation for a user who is not signed in.",
  "app": { "name": "Example Shop", "stack": "nextjs", "commit": "a1b2c3d" },
  "direction": "TD",
  "lanes": [
    { "id": "user", "label": "User" },
    { "id": "ui",   "label": "App UI" },
    { "id": "api",  "label": "Backend" }
  ],
  "nodes": [ ... ],
  "edges": [ ... ]
}
```

`direction`: `TD` for tall flows (default, reads like a funnel), `LR` for wide ones.

## Choosing a node type

| Type | Use it for | Shape |
| --- | --- | --- |
| `start` | the trigger: a tap, a deep link, a push notification, app launch | ellipse |
| `end` | goal reached, or the user abandons | ellipse |
| `screen` | a full route/page the user lands on | rounded box |
| `modal` | overlay, bottom sheet, dialog — anything that traps focus | dashed rounded box |
| `action` | a discrete interaction that is not itself a screen (submit, swipe) | square box |
| `decision` | a branch point: guard, validation, feature flag, A/B split | diamond |
| `api` | a network call | parallelogram |
| `data` | persistence: DB table, cache, secure storage | cylinder |
| `state` | an app/UI state that is not a route (error banner, offline, empty) | pill |
| `external` | control leaves the app: 3DS page, OAuth, OS share sheet, app store | off-page |
| `note` | commentary only; excluded from all metrics and audit checks | note |

Rule of thumb: if the URL changes, it is a `screen`. If only the UI changes, it is a `state`.

## `kind` — the colour semantics

- `happy` — the primary success path. Exactly one continuous chain from `start` to `end`.
- `error` — failure handling: 4xx/5xx, validation errors, timeouts, declines.
- `edge` — rare but legitimate: first-run variant, feature-flagged branch, forced signup.
- `neutral` — infrastructure the user never perceives (a `data` node, an internal redirect).

If everything is `neutral` the diagram is grey and useless. Colour it.

## Node ids

Semantic, stable, lowercase: `checkout-payment`, `auth-otp-verify`, `settings-delete-account`.

Derive from route + component, never from position. If a route is long or has params:

```bash
python3 scripts/uxflow.py id "/checkout/[step]/payment" PaymentPage
```

**Renaming an id is a breaking change**: it churns the git diff and it makes `uxflow diff`
report a delete + an add instead of a modification. Rename only when the screen really is
a different screen.

## `source` — the traceability anchor

```json
"source": "src/app/checkout/payment/page.tsx:24"
```

Relative to the repo root, with a line number. This is required for every node you derived
from code, and it lands in the draw.io tooltip and the SVG `<title>`, so a reader can hover a
box and see where it lives. Extra corroborating locations go in `annotations.evidence`.

## Annotations — only what you can count

```json
"annotations": {
  "taps": 2,
  "required_fields": 6,
  "optional_fields": 2,
  "wait": "full-screen spinner until /api/shipping/quote resolves",
  "note": "Re-asks name and phone already collected at signup.",
  "friction": ["duplicate_input", "long_form"],
  "evidence": ["src/components/AddressForm.tsx:44"]
}
```

- `taps` — interactions needed to *leave* this node on the happy path. A form with one submit
  button after filling fields is 1 tap; a three-step accordion is 3.
- `required_fields` — count the actual validators, do not eyeball the JSX.
- `wait` — describe the blocking wait. Include a measured latency only if you measured it.
- `note` — one sentence, factual, in the user's language.

### Friction tags

| Tag | Evidence you must have found |
| --- | --- |
| `blocking_modal` | a modal rendered over the flow with no non-modal path around it |
| `no_loading_state` | an async call with no pending UI |
| `no_error_state` | an async call whose rejection renders nothing |
| `no_empty_state` | a list that renders nothing when the array is empty |
| `no_back_affordance` | no back button, no `router.back`, no swipe-back, header hidden |
| `hidden_cta` | the primary action sits below the fold / behind a scroll |
| `long_form` | more than 5 required fields on one screen |
| `forced_signup` | an auth guard on a screen that the API could serve to a guest |
| `unskippable` | interstitial with no dismiss/skip path |
| `destructive_no_confirm` | delete/cancel/irreversible action with no confirmation step |
| `silent_failure` | a `catch` that only logs, and the UI does not change |
| `duplicate_input` | asks for data the app already holds |
| `external_handoff` | control leaves the app mid-flow |
| `permission_prompt` | an OS permission dialog interrupts the flow |

Severe ones (`no_error_state`, `silent_failure`, `destructive_no_confirm`,
`no_back_affordance`, `forced_signup`) surface as **high** severity in the audit. Do not use
them loosely.

## Edges

```json
{ "from": "auth-gate", "to": "signup", "label": "no", "kind": "edge",
  "condition": "session == null", "source": "src/middleware.ts:42" }
```

- `label` — what the user sees or does: the button text, `"Continue"`, `"201"`, `"timeout"`.
- `condition` — the guard **as it appears in code**. Renders only in the annotated variant.
- `kind: "back"` — return/cancel transitions. These are excluded from layering and from the
  depth metric, so a back edge never distorts the funnel. Use it, or your diagram will look
  like spaghetti.

Every `api` node should have at least one `kind: "error"` edge leaving it. If it does not, the
audit flags it — and that flag is usually a real bug, not a modelling gap.

## Common mistakes

| Mistake | Why it hurts |
| --- | --- |
| One giant flow for the whole app | Unreadable. One flow = one user goal. 10–30 nodes is the sweet spot. |
| Modelling components instead of user-visible steps | The reader is thinking about the user, not the render tree. |
| Omitting error branches | The audit's most valuable output disappears. |
| `kind` left `neutral` everywhere | No visual signal. |
| Positional ids (`node-1`) | Diffs churn; before/after comparison breaks. |
| Friction tags without evidence | Destroys trust in the whole document. |

## Splitting a flow that got too big

Above ~35 nodes, split at a natural boundary and connect with `external` nodes that name the
other flow (`"Continues in: onboarding"`). Keep one goal per file.
