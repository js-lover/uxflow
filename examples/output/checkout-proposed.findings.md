# UX audit -- Guest checkout (proposed)

**App:** Example Shop  
**Commit:** `proposal`  
**Flow id:** `checkout-proposed`  
**IR hash:** `b87d703e6164b5fc`

## Metrics

| metric | value |
| --- | ---: |
| Steps on the primary path | 8 |
| Screens on the primary path | 4 |
| Taps on the primary path | 4 |
| Required form fields (total) | 9 |
| Screens | 5 |
| API calls | 2 |
| Decision points | 0 |
| Modelled error branches | 6 |
| Friction tags | 1 |
| Unreachable nodes | 0 |
| Nodes | 13 |
| Edges | 17 |

## Primary path

Taps Checkout in cart → Cart → Contact + shipping → POST /api/shipping/quote → Payment → 3-D Secure (bank page) → POST /api/orders → Order confirmed → Order placed

## Findings (2)

### Medium (1)

| node | issue | detail | source |
| --- | --- | --- | --- |
| done | `flow_too_deep` | The primary path is 8 steps long (threshold 6). Each extra step compounds drop-off. |  |

### Low (1)

| node | issue | detail | source |
| --- | --- | --- | --- |
| 3-D Secure (bank page) | `friction:external_handoff` | Leaves the app. |  |

