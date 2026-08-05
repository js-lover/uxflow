# UX audit -- Guest checkout

**App:** Example Shop  
**Commit:** `a1b2c3d`  
**Flow id:** `checkout`  
**IR hash:** `ac3604074e5deec3`

## Metrics

| metric | value |
| --- | ---: |
| Steps on the primary path | 9 |
| Screens on the primary path | 4 |
| Taps on the primary path | 5 |
| Required form fields (total) | 14 |
| Screens | 7 |
| API calls | 2 |
| Decision points | 1 |
| Modelled error branches | 2 |
| Friction tags | 9 |
| Unreachable nodes | 0 |
| Nodes | 15 |
| Edges | 17 |

## Primary path

Taps Checkout in cart → Cart → Signed in? → Shipping address → POST /api/shipping/quote → Payment → 3-D Secure (bank page) → POST /api/orders → Order confirmed → Order placed

## Findings (14)

### High (7)

| node | issue | detail | source |
| --- | --- | --- | --- |
| POST /api/orders | `no_error_branch` | Network call with no modelled failure branch. Either the code swallows the error, or the flow is incomplete. | `src/app/api/orders/route.ts:11` |
| Payment declined | `deadend` | Dead end: the user reaches this state and the flow offers no way out at all. | `src/app/checkout/declined/page.tsx:9` |
| Payment declined | `friction:no_back_affordance` | No way back. | `src/app/checkout/declined/page.tsx:9` |
| Payment | `friction:no_back_affordance` | No way back. | `src/app/checkout/payment/page.tsx:24` |
| Quote failed | `deadend` | Dead end: the user reaches this state and the flow offers no way out at all. | `src/app/checkout/address/page.tsx:88` |
| Quote failed | `friction:silent_failure` | Fails silently. | `src/app/checkout/address/page.tsx:88` |
| Create an account | `friction:forced_signup` | Forced signup. | `src/app/signup/page.tsx:12` |

### Medium (2)

| node | issue | detail | source |
| --- | --- | --- | --- |
| Payment declined | `no_back` | Screen offers no back or cancel affordance. | `src/app/checkout/declined/page.tsx:9` |
| done | `flow_too_deep` | The primary path is 9 steps long (threshold 6). Each extra step compounds drop-off. |  |

### Low (5)

| node | issue | detail | source |
| --- | --- | --- | --- |
| Shipping address | `friction:duplicate_input` | Re-asks known data. | `src/app/checkout/address/page.tsx:30` |
| Newsletter offer | `friction:blocking_modal` | Blocking modal. | `src/components/PromoModal.tsx:20` |
| Newsletter offer | `friction:unskippable` | Cannot be skipped. | `src/components/PromoModal.tsx:20` |
| 3-D Secure (bank page) | `friction:external_handoff` | Leaves the app. | `src/lib/psp/redirect.ts:15` |
| Create an account | `friction:long_form` | Long form. | `src/app/signup/page.tsx:12` |

