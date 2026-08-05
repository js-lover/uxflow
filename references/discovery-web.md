# Discovery — Next.js / React / React Router

## 1. Identify the router

```bash
cat package.json | grep -E '"(next|react-router-dom|@tanstack/react-router|@remix-run)"'
ls next.config.* 2>/dev/null
ls -d app src/app pages src/pages 2>/dev/null
```

| Evidence | Router |
| --- | --- |
| `app/` with `page.tsx` | Next.js App Router |
| `pages/` with default exports | Next.js Pages Router |
| `createBrowserRouter` / `<Routes>` | React Router |
| `routeTree.gen.ts` | TanStack Router |
| `app/routes/` + `@remix-run` | Remix / React Router 7 |

## 2. Build the route table

**Next.js App Router** — the filesystem *is* the route table:

```bash
find app src/app -name 'page.tsx' -o -name 'page.jsx' -o -name 'page.js' 2>/dev/null
find app src/app -name 'layout.tsx' -o -name 'template.tsx' -o -name 'loading.tsx' \
                 -o -name 'error.tsx' -o -name 'not-found.tsx' 2>/dev/null
```

`app/checkout/payment/page.tsx` → `/checkout/payment`. `(group)` segments do not appear in the
URL. `[param]` and `[...slug]` are dynamic. **`loading.tsx` present = there is a loading state;
absent = there may not be. `error.tsx` present = there is an error boundary.** Record both —
their absence is exactly the `no_loading_state` / `no_error_state` evidence you need.

**Next.js Pages Router** — `pages/checkout/payment.tsx` → `/checkout/payment`;
`pages/_app.tsx` wraps everything; `pages/api/**` are endpoints, not screens.

**React Router / TanStack** — grep the route config:

```bash
rg -n 'createBrowserRouter|<Route |path:\s*[\x27"]|createRoute\(' --glob '*.{ts,tsx,js,jsx}'
```

## 3. Find the transitions

```bash
rg -n 'router\.(push|replace|back|forward)\(|redirect\(|permanentRedirect\(' --glob '*.{ts,tsx}'
rg -n '<Link\s+href=|navigate\(|useNavigate\(' --glob '*.{ts,tsx}'
rg -n 'window\.location\.(href|assign|replace)' --glob '*.{ts,tsx}'
```

`router.replace` matters: it removes the previous entry, so **the user cannot go back** — good
evidence for `no_back_affordance`.

## 4. Find the guards

```bash
cat middleware.ts src/middleware.ts 2>/dev/null
rg -n 'getServerSession|auth\(\)|requireUser|withAuth|redirect\([\x27"]/(login|signin)' --glob '*.{ts,tsx}'
rg -n 'useFlag|featureFlag|isEnabled\(|posthog\.isFeatureEnabled|launchdarkly' --glob '*.{ts,tsx}'
```

`middleware.ts` `matcher` config tells you exactly which routes are gated — that becomes a
`decision` node with the matcher expression as its `condition`.

## 5. Find the network calls and their error handling

```bash
rg -n 'fetch\(|axios\.|useQuery\(|useMutation\(|useSWR\(|createServerAction' --glob '*.{ts,tsx}'
rg -n 'catch\s*\(' -A 3 --glob '*.{ts,tsx}'
```

For each call, answer three questions and record the answer as an edge or a friction tag:

1. Is there a pending UI? (`isPending`, `isLoading`, `loading.tsx`, a Suspense boundary)
   No → `no_loading_state`.
2. Is there a rejection UI? (`isError`, `error.tsx`, an error toast, a rendered message)
   No → `no_error_state`.
3. Does the `catch` only `console.*` / swallow? → `silent_failure`.

API route handlers live in `app/api/**/route.ts` or `pages/api/**` — read them to name the
endpoint and its status codes accurately.

## 6. States per screen

```bash
rg -n 'isLoading|isPending|isFetching|isError|\.length === 0|EmptyState|Skeleton' --glob '*.{ts,tsx}'
```

A list component with no `length === 0` branch and no `EmptyState` → `no_empty_state`.

## 7. Modals and interstitials

```bash
rg -n 'Dialog|Modal|Drawer|Sheet|createPortal|showModal' --glob '*.{ts,tsx}'
rg -n 'onOpenChange|closeOnEscape|dismissible|onDismiss' --glob '*.{ts,tsx}'
```

A modal with `dismissible={false}`, no `onOpenChange`, or no escape handler →
`blocking_modal`, and `unskippable` if it is on the critical path.

## 8. Forms

```bash
rg -n 'zodResolver|yupResolver|useForm\(|z\.object\(|\.required\(' --glob '*.{ts,tsx}'
```

Count `required_fields` from the **validation schema**, not the JSX — the schema is the truth.
More than five on one screen → `long_form`.

## 9. Entry points

- `sitemap.ts` / `robots.ts` — publicly reachable routes
- `app/layout.tsx` nav components — what is reachable from the chrome
- deep links from email templates or marketing code
- OAuth callback routes (`/api/auth/callback/*`)

## Mapping to IR

| Found | Node |
| --- | --- |
| `page.tsx` route | `screen`, `route` = URL, `source` = file:1 |
| `error.tsx` / rendered error | `state`, `kind: "error"` |
| `loading.tsx` / skeleton | usually not a node — put it in `annotations.wait` |
| Dialog / Sheet | `modal` |
| middleware guard, `if (!session)` | `decision` with the guard as `condition` |
| `fetch` / `useMutation` | `api`, label = `METHOD /path` |
| Prisma/Drizzle model written to | `data` |
| OAuth provider, Stripe Checkout, 3DS | `external` |
