# Guest checkout (proposed) — flow report

**App:** Example Shop · **Stack:** `nextjs` · **Commit:** `proposal` · **Flow:** `checkout-proposed`

> Same goal, with the forced signup removed, the failure branches modelled, and the promo interstitial moved off the critical path.

## Summary

This flow has 2 findings: 1 of medium priority. The primary path is 7 steps.

| | | |
| --- | ---: | --- |
| 🔴 **High** | 0 | affects users directly |
| 🟠 Medium | 1 | costs conversion |
| 🟡 Low | 1 | polish |
| | | |
| Primary path | 7 steps | places the user passes through |
| Stuck | 0 | ways to end up going nowhere |

## What to do

Ordered by severity, confidence and effort. Working top to bottom gives the fastest improvement, and each row is ready to become a ticket.

| # | what | where | effort | detail |
| ---: | --- | --- | --- | --- |
| 1 | 🟠 The primary path is longer than it needs to be | Guest checkout (proposed)<br>— | L | [UXF-DEEP-2678](#uxf-deep-2678) |
| 2 | 🟡 Part of this map cannot be verified | Guest checkout (proposed)<br>— | S | [UXF-SRC-255A](#uxf-src-255a) |

## The flow

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}, 'theme': 'base'}}%%
flowchart TD
    subgraph lane_user["User"]
    direction TD
    start(["Taps Checkout in cart"])
    done(["Order placed"])
    end
    subgraph lane_ui["App UI"]
    direction TD
    cart["Cart"]
    address["Contact + shipping"]
    shipping_error("Quote unavailable")
    payment["Payment"]
    charge_error("Order could not be created")
    declined["Payment declined"]
    confirm["Order confirmed"]
    end
    subgraph lane_api["Backend"]
    direction TD
    shipping_api[/"POST /api/shipping/quote"/]
    psp[["3-D Secure #40;bank page#41;"]]
    charge[/"POST /api/orders"/]
    orders_db[("orders table")]
    end

    start ==> cart
    cart ==>|"Checkout"| address
    address ==>|"Continue"| shipping_api
    shipping_api ==>|"200"| payment
    shipping_api -.->|"5xx / timeout"| shipping_error
    shipping_error -.->|"Retry"| shipping_api
    shipping_error -.->|"flat rate"| payment
    payment ==>|"Pay"| psp
    payment -.->|"back"| address
    psp ==>|"authorised"| charge
    psp -.->|"rejected"| declined
    declined -.->|"Try another card"| payment
    charge -->|"insert"| orders_db
    charge ==>|"201"| confirm
    charge -.->|"5xx"| charge_error
    charge_error -.->|"Retry"| charge
    confirm ==> done

    classDef happy fill:#E7F5EA,stroke:#2E7D32,color:#14532D,stroke-width:2px;
    classDef error fill:#FDEAEA,stroke:#C62828,color:#7F1D1D,stroke-width:2px;
    classDef edge fill:#FFF6E0,stroke:#B8860B,color:#78350F,stroke-width:2px;
    classDef neutral fill:#F4F4F5,stroke:#71717A,color:#27272A,stroke-width:2px;
    classDef deadend fill:#FCE4EC,stroke:#AD1457,color:#831843,stroke-width:2px;
    classDef orphan fill:#EDE9FE,stroke:#6D28D9,color:#4C1D95,stroke-width:2px;
    classDef unreachable fill:#E0E7FF,stroke:#3730A3,color:#312E81,stroke-width:2px;
    class shipping_error,charge_error,declined error;
    class start,cart,address,shipping_api,payment,psp,charge,confirm,done happy;
    class orders_db neutral;
```

*Editable version: `checkout-proposed.drawio` — open it in [diagrams.net](https://app.diagrams.net). The second tab carries the annotations.*

## Primary path

The longest complete journey a user takes to reach the goal — 7 steps:

- *entry* — Taps Checkout in cart
1. **Cart**  — 1 tap
2. **Contact + shipping**  — 1 tap, 5 required fields
3. **POST /api/shipping/quote**  — waits
4. **Payment**  — 2 taps, 4 required fields
5. **3-D Secure (bank page)**
6. **POST /api/orders**
7. **Order confirmed**
- *goal* — Order placed

## Metrics

| | metric | value | reading |
| :-: | --- | ---: | --- |
| ! | Steps on the primary path | 7 | above six — every extra step costs users |
| ✓ | Screens on the primary path | 4 | reasonable |
| ✓ | Interactions on the primary path | 4 | light interaction load |
| ! | Required form fields (total) | 9 | every required field is a chance to give up — are they all needed? |
| ✓ | Ways to end up stuck | 0 | no point where the user gets trapped |
| ✓ | Error-branch coverage | 100% | every network call has a modelled failure path |
| ✗ | Source-anchor coverage | 0% | a large share of nodes is not grounded in code — read this map with care |

**Size:** 13 nodes · 17 transitions · 5 screens · 2 network calls · 0 decisions · 6 error branches

## Findings (2)

<a id="uxf-deep-2678"></a>

### 🟠 The primary path is longer than it needs to be

`UXF-DEEP-2678` · **node:** Guest checkout (proposed) · **severity:** medium · **confidence:** certain · **effort:** L (needs a design decision)

**What happens**

The primary path is 7 steps (threshold 6).

**What the user experiences**

Every additional step costs users. Long flows complete at measurably lower rates, especially on mobile and on first use.

**What to do**

Look for steps to merge: fields that could share a screen, decisions that could be deferred, confirmations that could be dropped.

<sub>Accept and silence with: `flowlint ignore UXF-DEEP-2678`</sub>

<a id="uxf-src-255a"></a>

### 🟡 Part of this map cannot be verified

`UXF-SRC-255A` · **node:** Guest checkout (proposed) · **severity:** low · **confidence:** certain · **effort:** S (~1 hour)

**What happens**

11 nodes have no `source` anchor: Cart, Contact + shipping, POST /api/shipping/quote, Quote unavailable, Payment, 3-D Secure (bank page) ve 5 tane daha.

**What the user experiences**

There is no way to confirm these nodes came from the code. When a reader cannot tell which parts are real and which are assumed, they trust the whole map less.

**What to do**

Add the `file:line` each node came from. If this flow describes something not built yet — a `-proposed` file, for instance — this finding is expected; accept it with `flowlint ignore` and a reason.

<sub>Accept and silence with: `flowlint ignore UXF-SRC-255A`</sub>

## Notes

Not problems, but worth knowing when reading the flow.

- **3-D Secure (bank page)** — At this step the user leaves the app for an external service. That is not a problem in itself, but the return paths — cancellation and failure — need to be modelled.

## Method

This report was generated from `checkout-proposed.flow.json`, which was in turn extracted by reading the codebase.

- **Scope:** 13 nodes, 17 transitions, at commit `proposal`
- **Traceability:** 0% of nodes carry a `file:line` anchor
- **Findings come only from the graph.** Nothing is invented: every finding follows either from the structure or from a tag grounded in code.
- **Not covered:** what real users do. This extracts the paths the code permits, not the ones people choose. It complements analytics rather than replacing them.
- **Caution:** some nodes could not be traced to code; treat those parts of the map with care.

## Machine-readable summary

<details><summary>JSON</summary>

```json
{
  "flow": "checkout-proposed",
  "title": "Guest checkout (proposed)",
  "ir_hash": "b87d703e6164b5fc",
  "app": {
    "name": "Example Shop",
    "stack": "nextjs",
    "commit": "proposal"
  },
  "metrics": {
    "nodes": 13,
    "edges": 17,
    "screens": 5,
    "api_calls": 2,
    "decisions": 0,
    "primary_path_steps": 7,
    "screens_on_primary_path": 4,
    "total_taps": 5,
    "taps_on_primary_path": 4,
    "required_fields": 9,
    "friction_tags": 0,
    "unreachable_nodes": 0,
    "error_branches": 6,
    "error_branch_coverage": 100,
    "source_coverage": 0,
    "failure_exits": 0
  },
  "primary_path": [
    "start",
    "cart",
    "address",
    "shipping-api",
    "payment",
    "psp",
    "charge",
    "confirm",
    "done"
  ],
  "findings": [
    {
      "id": "UXF-DEEP-2678",
      "code": "flow_too_deep",
      "severity": "medium",
      "confidence": "certain",
      "effort": "L",
      "node": "",
      "label": "Guest checkout (proposed)",
      "evidence": [],
      "fix": "Look for steps to merge: fields that could share a screen, decisions that could be deferred, confirmations that could be dropped."
    },
    {
      "id": "UXF-SRC-255A",
      "code": "missing_source",
      "severity": "low",
      "confidence": "certain",
      "effort": "S",
      "node": "",
      "label": "Guest checkout (proposed)",
      "evidence": [],
      "fix": "Add the `file:line` each node came from. If this flow describes something not built yet — a `-proposed` file, for instance — this finding is expected; accept it with `flowlint ignore` and a reason."
    }
  ],
  "suppressed": []
}
```

</details>

# Flow diff -- Guest checkout (proposed)

`checkout` (before, hash ac3604074e5deec3) → `checkout-proposed` (after, hash b87d703e6164b5fc)

## What changed

| | count |
| --- | ---: |
| Nodes added | 1 |
| Nodes removed | 3 |
| Nodes changed | 6 |
| Nodes unchanged | 6 |

## Metric delta

| metric | before | after | delta |
| --- | ---: | ---: | ---: |
| primary path steps | 8 | 7 | -1 |
| screens on primary path | 4 | 4 | ±0 |
| taps on primary path | 5 | 4 | -1 |
| required fields | 14 | 9 | -5 |
| screens | 7 | 5 | -2 |
| api calls | 2 | 2 | ±0 |
| error branches | 2 | 6 | +4 |
| friction tags | 8 | 0 | -8 |
| high-severity findings | 7 | 0 | -7 |
| medium-severity findings | 5 | 1 | -4 |
| low-severity findings | 0 | 1 | +1 |

## Findings resolved

- `deadend` on `declined`
- `deadend` on `shipping-error`
- `friction:blocking_modal` on `promo-modal`
- `friction:duplicate_input` on `address`
- `friction:forced_signup` on `signup`
- `friction:long_form` on `signup`
- `friction:no_back_affordance` on `declined`
- `friction:no_back_affordance` on `payment`
- `friction:silent_failure` on `shipping-error`
- `friction:unskippable` on `promo-modal`
- `no_error_branch` on `charge`

## Findings introduced

- `missing_source` on `(flow)`

## Added

- **Order could not be created** (`charge-error`)

## Removed

- **Signed in?** (`auth-gate`)
- **Create an account** (`signup`)
- **Newsletter offer** (`promo-modal`)

## Changed

- **Contact + shipping** (`address`) — label, annotations
  - `label`: 'Shipping address' → 'Contact + shipping'
- **POST /api/shipping/quote** (`shipping-api`) — annotations
- **Quote unavailable** (`shipping-error`) — label, annotations
  - `label`: 'Quote failed' → 'Quote unavailable'
- **Payment** (`payment`) — annotations
- **Payment declined** (`declined`) — annotations
- **Order confirmed** (`confirm`) — annotations

