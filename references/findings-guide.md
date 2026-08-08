# Reading the findings

The diagram shows what the flow *is*. The findings say what is *wrong* with it. This
file explains what each rule means, why it fires, and how to talk about it with the user.

## What a finding is trying to answer

Every rule exists to answer one of three questions:

1. **Can the user get stuck here?** — dead ends, back-only screens, redirect loops
2. **What does the user see when something fails?** — missing error/empty/cancel handling
3. **Is this journey longer than it needs to be?** — steps, taps, required fields

If a proposed new rule does not answer one of those, it probably belongs in the notes
rather than the findings list.

## Anatomy

```
### UXF-NOERR-0A7D · Hata kullanıcıya gösterilmiyor
**Önem:** yüksek · **Güven:** kesin · **Efor:** S (~1 saat)

**Ne oluyor**       what the code does — mechanical, verifiable
**Kullanıcı ne yaşıyor**  the human consequence — concrete, not abstract
**Ne yapmalı**      the change to make
**Kanıt**           file:line anchors
```

- **Önem (severity)** — `high` means a user can get stuck or be left uninformed.
  `medium` costs conversion. `low` is polish.
- **Güven (confidence)** — `kesin` means the graph proves it. `güçlü ihtimal` means the
  signal is strong but worth a glance at the code before acting.
- **Efor** — S under an hour, M about half a day, L needs a design decision.
- **Id** — stable across runs for the same rule and node, so it can be suppressed and
  referenced in a ticket.

## The rules

### Structural — can the user get stuck?

| Code | Fires when | Why it matters |
| --- | --- | --- |
| `deadend` | A node has no outgoing transition at all and is not an `end` | The session ends here. The user's only option is to close the app. |
| `only_exit_is_back` | A **screen**'s only way out is a back/cancel edge | The user arrived somewhere they cannot complete anything from. Modals and transient states are exempt: dismissing them is normal. |
| `unreachable` | No path from any entry point reaches the node | Dead code, or a transition was deleted and a feature is now unreachable. |
| `orphan` | Nothing links to the node | Reachable only by deep link or accident. |
| `redirect_loop` | A cycle contains no action, decision or form **and** no node in it leads outside the cycle | The user can circle forever. This is what "the app froze" usually means. |

`redirect_loop` has two escape hatches, both added after the rule fired on healthy
graphs. A cycle passing through an action or a form is a legitimate retry loop — the
user can type something different. And if any node in the cycle leads somewhere outside
it, there is a door, so the user is not trapped no matter how the cycle looks.

### Error paths — what happens when it fails?

| Code | Fires when | Why it matters |
| --- | --- | --- |
| `no_error_branch` | An `api` node has no `error` edge | Usually a genuinely swallowed exception, not a modelling gap. |
| `external_no_return` | An `external` node has outgoing edges but none of kind `error` | The cancel path from OAuth / 3-D Secure / payment is unhandled. Extremely common. |
| `waiting_no_resend` | A state that waits on an out-of-band message (mail, SMS, OTP, link) has no edge back to whatever sent it | If the message never arrives, the user is locked out. |
| `decision_single_branch` | A `decision` has fewer than two forward edges | The else branch is missing from the code or from the model. |

`waiting_no_resend` has two guards. The state must follow a network call — "Bağlantı
kopyalandı" mentions a link but nothing was sent, so there is nothing to resend. And the
resend must be an edge back to the *producer*: an edge that merely continues the journey,
like the emailed link finally being opened, is not a resend, because it depends on the
very thing that did not arrive.

### A rule that was removed

`error_state_no_recovery` shipped in a draft of v1.1 and was cut before release. Its only
reachable condition turned out to be a self-loop, which `deadend` and `redirect_loop`
already cover — so it either never fired or fired on legitimate retry paths. If you cannot
state precisely when a rule is right, it does not belong in the audit.

### Friction — is this harder than it needs to be?

These come from the tags you recorded in the IR, so they are only as good as your
evidence. Severe ones (`no_error_state`, `silent_failure`, `destructive_no_confirm`,
`no_back_affordance`, `forced_signup`) are reported as `high`. See
`references/ir-authoring.md` for the evidence each tag requires.

`external_handoff` is **not** a finding. Leaving the app for OAuth is normal behaviour;
listing it as a problem buries the real ones. It appears under "Bilgi notları" instead.

### Model quality

| Code | Fires when | Why it matters |
| --- | --- | --- |
| `missing_source` | A node has no `source` anchor | That node's claim cannot be verified, which weakens trust in the whole map. |
| `flow_too_deep` | More than six real steps on the primary path | Each extra step compounds drop-off. Attached to the flow, not to a node. |

## Metrics

Bare numbers do not help anyone decide anything, so each one carries a verdict:

| Metric | Meaning |
| --- | --- |
| **Ana yol adım sayısı** | Nodes the user passes through, excluding `start`/`end` — they are bookkeeping, not steps |
| **Başarısızlıkla biten yol sayısı** | How many distinct ways a user can end up stuck short of the goal. The single best indicator of flow health. |
| **Hata dalı kapsamı** | Share of network calls that have a modelled failure branch |
| **Kaynak çapası kapsamı** | Share of nodes traceable to `file:line`. Below 100% means read the map with care. |

The primary path is computed exactly: cycle-closing edges are removed to obtain a DAG,
then a dynamic program over topological order picks the highest-scoring path (reaching
an `end` beats everything, then happy edges, then length). It is not a sampled search,
so a wide fan-out cannot hide a deeper branch.

## Suppression

```bash
python3 scripts/uxflow.py ignore UXF-NOERR-0A7D --reason "Q3'te ele alınacak"
```

Writes to `.uxflowignore` (walked up from the output directory, like `.gitignore`).
Suppressed findings move to an "accepted" section — they stop failing CI but stay
visible, with the reason recorded. Without this, `--fail-on-high` is unadoptable on an
existing codebase, and a check nobody can turn on is a check nobody runs.

## Talking to the user about findings

- Lead with the **headline** and the **priority list**. Most people read nothing else.
- Give the file:line for anything high severity — it is what turns a report into work.
- Be honest about `güçlü ihtimal` findings: say the signal is strong and the code is
  worth a look, rather than asserting a defect.
- If the audit found nothing, say so plainly. A clean flow is a real result, not a
  failure to try hard enough — do not manufacture findings to fill the page.
