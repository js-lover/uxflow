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
| primary path steps | 9 | 8 | -1 |
| screens on primary path | 4 | 4 | ±0 |
| taps on primary path | 5 | 4 | -1 |
| required fields | 14 | 9 | -5 |
| screens | 7 | 5 | -2 |
| api calls | 2 | 2 | ±0 |
| error branches | 2 | 6 | +4 |
| friction tags | 9 | 1 | -8 |

| high-severity findings | 7 | 0 | -7 |

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

