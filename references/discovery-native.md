# Discovery — Native iOS (SwiftUI / UIKit) and Android (Jetpack Compose)

## Detect

```bash
ls *.xcodeproj *.xcworkspace Package.swift 2>/dev/null
rg -l 'import SwiftUI' | head
rg -l 'androidx.compose' --glob '*.kt' | head
ls app/src/main/AndroidManifest.xml 2>/dev/null
```

---

## SwiftUI

### Routes and transitions

```bash
rg -n 'NavigationStack|NavigationSplitView|NavigationView' -A 4
rg -n 'navigationDestination\(|NavigationLink\(' -A 3
rg -n '@State.*path|NavigationPath\(|\.append\(|\.removeLast\('
rg -n 'TabView' -A 6                # each tab is an entry point
rg -n '\.sheet\(|\.fullScreenCover\(|\.alert\(|\.confirmationDialog\(' -A 3
rg -n '\.onOpenURL|onContinueUserActivity'   # deep links -> start nodes
```

A `NavigationPath`-driven stack means routes are values — enumerate the destination enum/type
to get the full screen list.

`.fullScreenCover` with no dismiss binding exposed, or `.interactiveDismissDisabled()` →
`blocking_modal` / `unskippable`.

### Async state

```bash
rg -n '\.task\s*\{|Task\s*\{' -A 6
rg -n 'do\s*\{' -A 8 | rg -n 'catch'
rg -n 'ProgressView\(|redacted\(reason:'
rg -n 'ContentUnavailableView|isEmpty'
```

- `catch { print(...) }` or `catch { }` → `silent_failure`
- awaited call with no `ProgressView`/redaction → `no_loading_state`
- list with no `isEmpty` branch and no `ContentUnavailableView` → `no_empty_state`

### Guards and permissions

```bash
rg -n 'if .*isAuthenticated|@AppStorage\("(hasOnboarded|token)"'
rg -n 'requestAuthorization|AVCaptureDevice\.requestAccess|ATTrackingManager|requestWhenInUseAuthorization'
rg -n 'StoreKit|Product\.purchase|paywall'
```

---

## UIKit

```bash
rg -n 'performSegue\(withIdentifier|prepare\(for segue'
rg -n 'navigationController\?\.(pushViewController|popViewController|setViewControllers)'
rg -n 'present\(.*animated|dismiss\(animated'
rg -n 'instantiateViewController\(withIdentifier'
rg -n 'UIStoryboardSegue|storyboard'
```

Storyboards carry the flow explicitly — read the `.storyboard` XML for `<segue>` elements:

```bash
rg -n '<segue ' --glob '*.storyboard'
```

`setViewControllers(_:animated:)` replaces the stack → `no_back_affordance`.
`isModalInPresentation = true` → `blocking_modal`.

---

## Jetpack Compose

### Routes and transitions

```bash
rg -n 'NavHost\(|composable\(|navigation\(' --glob '*.kt' -A 3
rg -n 'navController\.(navigate|popBackStack|navigateUp)\(' --glob '*.kt'
rg -n 'popUpTo\(|inclusive\s*=\s*true|launchSingleTop' --glob '*.kt'
rg -n '@Serializable\s+(data\s+)?object|sealed (class|interface).*Route' --glob '*.kt'
```

`popUpTo(..., inclusive = true)` clears the back stack → `no_back_affordance` evidence.

### Async state

```bash
rg -n 'collectAsStateWithLifecycle|collectAsState\(' --glob '*.kt'
rg -n 'sealed (interface|class) .*UiState' -A 6 --glob '*.kt'
rg -n 'runCatching|try\s*\{' -A 6 --glob '*.kt'
rg -n 'CircularProgressIndicator|Shimmer' --glob '*.kt'
```

A `UiState` sealed hierarchy with no `Error` member, or an `Error` member the UI never renders,
is `no_error_state`. Check the `when (state)` block actually handles every branch.

### Entry points and permissions

```bash
grep -A 25 'intent-filter' app/src/main/AndroidManifest.xml
rg -n 'rememberLauncherForActivityResult|RequestPermission|shouldShowRequestPermissionRationale' --glob '*.kt'
rg -n 'FirebaseMessagingService|onMessageReceived' --glob '*.kt'
rg -n 'BackHandler\(' --glob '*.kt'      # BackHandler { } that no-ops blocks the back button
```

`BackHandler(enabled = true) { /* nothing */ }` swallows the system back button — a strong
`no_back_affordance` finding, and one users complain about loudly.

---

## Mapping to IR (both platforms)

| Found | Node |
| --- | --- |
| `navigationDestination` / `composable(...)` / view controller / segue target | `screen` |
| `.sheet`, `.fullScreenCover`, `Dialog`, `ModalBottomSheet`, `present(_:)` | `modal` |
| auth check, onboarding flag, paywall gate | `decision` |
| permission request | `decision` + `permission_prompt`; model the denied branch |
| repository / URLSession / Retrofit / Ktor call | `api` |
| CoreData, SwiftData, Room, DataStore, Keychain write | `data` |
| Safari VC, Custom Tab, StoreKit sheet, OS share | `external` |
| `UiState.Error`, `.failure`, error alert | `state`, `kind: "error"` |

Suggested lanes: `user` → `app` → `api` → `device`.

## A note on native codebases

Navigation is frequently imperative and scattered, so the route table is not a single file.
Budget more time for Phase 1, and when you cannot prove a transition exists, do not draw it.
An incomplete diagram with honest gaps is worth far more than a complete-looking invented one —
put the gap in `annotations.note` and tell the user which files you could not resolve.
