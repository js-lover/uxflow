# Login (Supabase OAuth + magic link) — flow report

**App:** Example App · **Stack:** `nextjs` · **Commit:** `a31a654` · **Flow:** `auth-login`

> Reaching a protected route, signing in with Google OAuth or an emailed magic link, and returning through the auth callback.

## Summary

This flow has 4 findings: 3 that affect users directly, 1 of medium priority. The primary path is 7 steps.

| | | |
| --- | ---: | --- |
| 🔴 **High** | 3 | affects users directly |
| 🟠 Medium | 1 | costs conversion |
| 🟡 Low | 0 | polish |
| | | |
| Primary path | 7 steps | places the user passes through |
| Stuck | 0 | ways to end up going nowhere |

## What to do

Ordered by severity, confidence and effort. Working top to bottom gives the fastest improvement, and each row is ready to become a ticket.

| # | what | where | effort | detail |
| ---: | --- | --- | --- | --- |
| 1 | 🔴 The error is never shown to the user | /login?error=auth<br>`app/auth/callback/route.ts:17` | S | [UXF-NOERR-0A7D](#uxf-noerr-0a7d) |
| 2 | 🔴 Waiting on something out of band, with no way to resend | Sign-in link sent (waiting for email)<br>`app/login/page.tsx:68` | S | [UXF-RESEND-A1AD](#uxf-resend-a1ad) |
| 3 | 🔴 No cancel or failure path back from an external service | Supabase Google OAuth<br>`app/login/page.tsx:20` | M | [UXF-EXT-E61B](#uxf-ext-e61b) |
| 4 | 🟠 The primary path is longer than it needs to be | Login (Supabase OAuth + magic link)<br>— | L | [UXF-DEEP-2678](#uxf-deep-2678) |

## The flow

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}, 'theme': 'base'}}%%
flowchart TD
    subgraph lane_user["User"]
    direction TD
    auth_start(["Opens a protected route"])
    google_oauth_action["Tap: sign in with Google"]
    magic_link_form["Tap: email me a sign-in<br/>link"]
    auth_end(["App is usable"])
    end
    subgraph lane_ui["App UI"]
    direction TD
    login_screen["Login page"]
    magic_link_sent("Sign-in link sent #40;waiting<br/>for email#41;")
    login_error("Sign-in error shown")
    callback_error_redirect("/login?error=auth")
    app_home["Home"]
    end
    subgraph lane_api["Backend"]
    direction TD
    auth_guard{"Signed in?"}
    supabase_otp[/"Supabase signInWithOtp"/]
    auth_callback[/"GET /auth/callback"/]
    end
    subgraph lane_data["External / data"]
    direction TD
    supabase_google_oauth[["Supabase Google OAuth"]]
    exchange_session[("Supabase session exchange")]
    end

    auth_start ==>|"route render"| auth_guard
    auth_guard -.->|"redirect /login"| login_screen
    auth_guard ==>|"authenticated"| app_home
    login_screen ==>|"tap Google"| google_oauth_action
    google_oauth_action ==>|"signInWithOAuth"| supabase_google_oauth
    supabase_google_oauth ==>|"redirectTo"| auth_callback
    login_screen -.->|"or use email"| magic_link_form
    magic_link_form -.->|"submit"| supabase_otp
    supabase_otp -.->|"ok"| magic_link_sent
    supabase_otp -.->|"error.message"| login_error
    login_error -->|"try again"| login_screen
    magic_link_sent -.->|"link in the email is opened"| auth_callback
    auth_callback ==>|"code"| exchange_session
    exchange_session ==>|"no error"| app_home
    auth_callback -.->|"auth error"| callback_error_redirect
    exchange_session -.->|"exchange error"| callback_error_redirect
    callback_error_redirect -->|"stays on /login"| login_screen
    app_home ==>|"dashboard ready"| auth_end

    classDef happy fill:#E7F5EA,stroke:#2E7D32,color:#14532D,stroke-width:2px;
    classDef error fill:#FDEAEA,stroke:#C62828,color:#7F1D1D,stroke-width:2px;
    classDef edge fill:#FFF6E0,stroke:#B8860B,color:#78350F,stroke-width:2px;
    classDef neutral fill:#F4F4F5,stroke:#71717A,color:#27272A,stroke-width:2px;
    classDef deadend fill:#FCE4EC,stroke:#AD1457,color:#831843,stroke-width:2px;
    classDef orphan fill:#EDE9FE,stroke:#6D28D9,color:#4C1D95,stroke-width:2px;
    classDef unreachable fill:#E0E7FF,stroke:#3730A3,color:#312E81,stroke-width:2px;
    class magic_link_form,supabase_otp,magic_link_sent edge;
    class login_error,callback_error_redirect error;
    class auth_start,auth_guard,login_screen,google_oauth_action,supabase_google_oauth,auth_callback,exchange_session,app_home,auth_end happy;
```

*Editable version: `auth-login.drawio` — open it in [diagrams.net](https://app.diagrams.net). The second tab carries the annotations.*

## Primary path

The longest complete journey a user takes to reach the goal — 7 steps:

- *entry* — Opens a protected route
1. **Signed in?**
2. **Login page**  — 1 tap
3. **Tap: sign in with Google**  — 1 tap
4. **Supabase Google OAuth**  — waits
5. **GET /auth/callback**
6. **Supabase session exchange**
7. **Home**
- *goal* — App is usable

## Metrics

| | metric | value | reading |
| :-: | --- | ---: | --- |
| ! | Steps on the primary path | 7 | above six — every extra step costs users |
| ✓ | Screens on the primary path | 2 | reasonable |
| ✓ | Interactions on the primary path | 2 | light interaction load |
| ✓ | Required form fields (total) | 1 | few required fields |
| ✓ | Ways to end up stuck | 0 | no point where the user gets trapped |
| ✓ | Error-branch coverage | 100% | every network call has a modelled failure path |
| ✓ | Source-anchor coverage | 100% | every node traces back to a line of code |

**Size:** 14 nodes · 18 transitions · 2 screens · 2 network calls · 1 decisions · 3 error branches

## Findings (4)

<a id="uxf-noerr-0a7d"></a>

### 🔴 The error is never shown to the user

`UXF-NOERR-0A7D` · **node:** /login?error=auth · **severity:** high · **confidence:** certain · **effort:** S (~1 hour) · **route:** `/login?error=auth`

**What happens**

There is a failure path for “/login?error=auth”, but nothing in the interface surfaces it.

**What the user experiences**

When something goes wrong the user cannot tell. They are left with a blank or unchanged screen, repeat the same action, and get the same result. This is the most common cause of silent abandonment.

**What to do**

Wire the error state into the UI. When the error travels by redirect (`?error=...`), make sure the destination page actually reads that parameter — this step is skipped surprisingly often.

**Evidence:** `app/auth/callback/route.ts:17` · `app/login/page.tsx:8` · `app/login/page.tsx:104`

<sub>Accept and silence with: `flowlint ignore UXF-NOERR-0A7D`</sub>

<a id="uxf-resend-a1ad"></a>

### 🔴 Waiting on something out of band, with no way to resend

`UXF-RESEND-A1AD` · **node:** Sign-in link sent (waiting for email) · **severity:** high · **confidence:** likely · **effort:** S (~1 hour)

**What happens**

At “Sign-in link sent (waiting for email)” the user is waiting for something delivered outside the app — an emailed link, an SMS code — and this screen offers no way to resend it or switch method.

**What the user experiences**

If the email lands in spam or the SMS never arrives, the user is locked out completely. Their only option is to start over, and most people do not: they leave.

**What to do**

Add a resend action with a cool-down, and offer an alternative method. Show where it was sent, too, so a mistyped address is visible.

**Evidence:** `app/login/page.tsx:68`

<sub>Accept and silence with: `flowlint ignore UXF-RESEND-A1AD`</sub>

<a id="uxf-ext-e61b"></a>

### 🔴 No cancel or failure path back from an external service

`UXF-EXT-E61B` · **node:** Supabase Google OAuth · **severity:** high · **confidence:** likely · **effort:** M (~half a day)

**What happens**

“Supabase Google OAuth” hands the user off to another site, but only the success return is modelled. There is no transition for a cancellation or an error coming back.

**What the user experiences**

If the user presses Cancel on the external screen — an OAuth consent page, 3-D Secure, a payment provider — or hits an error there, where they land is undefined. Typically they arrive back at the start with no explanation and no idea what went wrong.

**What to do**

Read the provider's cancel and error parameters (`error`, `error_description`, `denied`) and route to a state that tells the user what happened. Design the return URL to carry that information.

**Evidence:** `app/login/page.tsx:20`

<sub>Accept and silence with: `flowlint ignore UXF-EXT-E61B`</sub>

<a id="uxf-deep-2678"></a>

### 🟠 The primary path is longer than it needs to be

`UXF-DEEP-2678` · **node:** Login (Supabase OAuth + magic link) · **severity:** medium · **confidence:** certain · **effort:** L (needs a design decision)

**What happens**

The primary path is 7 steps (threshold 6).

**What the user experiences**

Every additional step costs users. Long flows complete at measurably lower rates, especially on mobile and on first use.

**What to do**

Look for steps to merge: fields that could share a screen, decisions that could be deferred, confirmations that could be dropped.

<sub>Accept and silence with: `flowlint ignore UXF-DEEP-2678`</sub>

## Notes

Not problems, but worth knowing when reading the flow.

- **Supabase Google OAuth** — At this step the user leaves the app for an external service. That is not a problem in itself, but the return paths — cancellation and failure — need to be modelled.  `app/login/page.tsx:20`

## Method

This report was generated from `auth-login.flow.json`, which was in turn extracted by reading the codebase.

- **Scope:** 14 nodes, 18 transitions, at commit `a31a654`
- **Traceability:** 100% of nodes carry a `file:line` anchor
- **Findings come only from the graph.** Nothing is invented: every finding follows either from the structure or from a tag grounded in code.
- **Not covered:** what real users do. This extracts the paths the code permits, not the ones people choose. It complements analytics rather than replacing them.

## Machine-readable summary

<details><summary>JSON</summary>

```json
{
  "flow": "auth-login",
  "title": "Login (Supabase OAuth + magic link)",
  "ir_hash": "d8a63d4318a30f23",
  "app": {
    "name": "Example App",
    "stack": "nextjs",
    "commit": "a31a654"
  },
  "metrics": {
    "nodes": 14,
    "edges": 18,
    "screens": 2,
    "api_calls": 2,
    "decisions": 1,
    "primary_path_steps": 7,
    "screens_on_primary_path": 2,
    "total_taps": 3,
    "taps_on_primary_path": 2,
    "required_fields": 1,
    "friction_tags": 1,
    "unreachable_nodes": 0,
    "error_branches": 3,
    "error_branch_coverage": 100,
    "source_coverage": 100,
    "failure_exits": 0
  },
  "primary_path": [
    "auth-start",
    "auth-guard",
    "login-screen",
    "google-oauth-action",
    "supabase-google-oauth",
    "auth-callback",
    "exchange-session",
    "app-home",
    "auth-end"
  ],
  "findings": [
    {
      "id": "UXF-NOERR-0A7D",
      "code": "friction:no_error_state",
      "severity": "high",
      "confidence": "certain",
      "effort": "S",
      "node": "callback-error-redirect",
      "label": "/login?error=auth",
      "evidence": [
        "app/auth/callback/route.ts:17",
        "app/login/page.tsx:8",
        "app/login/page.tsx:104"
      ],
      "fix": "Wire the error state into the UI. When the error travels by redirect (`?error=...`), make sure the destination page actually reads that parameter — this step is skipped surprisingly often."
    },
    {
      "id": "UXF-RESEND-A1AD",
      "code": "waiting_no_resend",
      "severity": "high",
      "confidence": "likely",
      "effort": "S",
      "node": "magic-link-sent",
      "label": "Sign-in link sent (waiting for email)",
      "evidence": [
        "app/login/page.tsx:68"
      ],
      "fix": "Add a resend action with a cool-down, and offer an alternative method. Show where it was sent, too, so a mistyped address is visible."
    },
    {
      "id": "UXF-EXT-E61B",
      "code": "external_no_return",
      "severity": "high",
      "confidence": "likely",
      "effort": "M",
      "node": "supabase-google-oauth",
      "label": "Supabase Google OAuth",
      "evidence": [
        "app/login/page.tsx:20"
      ],
      "fix": "Read the provider's cancel and error parameters (`error`, `error_description`, `denied`) and route to a state that tells the user what happened. Design the return URL to carry that information."
    },
    {
      "id": "UXF-DEEP-2678",
      "code": "flow_too_deep",
      "severity": "medium",
      "confidence": "certain",
      "effort": "L",
      "node": "",
      "label": "Login (Supabase OAuth + magic link)",
      "evidence": [],
      "fix": "Look for steps to merge: fields that could share a screen, decisions that could be deferred, confirmations that could be dropped."
    }
  ],
  "suppressed": []
}
```

</details>
