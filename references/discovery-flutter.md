# Discovery — Flutter

## 1. Identify the router

```bash
grep -E 'go_router|auto_route|beamer|routemaster|flutter_modular' pubspec.yaml
rg -n 'MaterialApp\(|MaterialApp\.router\(|CupertinoApp'
```

| Evidence | Router |
| --- | --- |
| `go_router` + `GoRouter(routes: [...])` | GoRouter (most common) |
| `auto_route` + `*.gr.dart` | AutoRoute (codegen) |
| `MaterialApp(routes: {...})` | named routes |
| bare `Navigator.push(MaterialPageRoute(...))` | imperative only |

## 2. Build the route table

**GoRouter:**

```bash
rg -n 'GoRoute\(' -A 6
rg -n 'path:\s*[\x27"]|name:\s*[\x27"]|ShellRoute\(|StatefulShellRoute'
rg -n 'redirect:' -A 8          # <- the auth gate lives here
```

`GoRouter`'s top-level `redirect` callback is usually the single place all guards are
expressed. Read it fully and turn each `if` into a `decision` node with the Dart condition as
`condition`.

**AutoRoute:**

```bash
rg -n '@AutoRouterConfig|AutoRoute\(' -A 3
rg -n 'AutoRouteGuard|onNavigation\('
```

**Named routes:**

```bash
rg -n 'routes:\s*\{' -A 20
rg -n 'onGenerateRoute|onUnknownRoute'
```

## 3. Transitions

```bash
rg -n 'context\.(go|push|pushNamed|replace|pop)\('        # go_router
rg -n 'Navigator\.(of\(context\)\.)?(push|pushNamed|pushReplacement|pushAndRemoveUntil|pop)'
rg -n 'AutoRouter\.of\(context\)\.(push|replace|navigate)'
rg -n 'showModalBottomSheet|showDialog|showGeneralDialog'
rg -n 'url_launcher|launchUrl\('                          # -> external nodes
```

`pushReplacement` and `pushAndRemoveUntil` clear the back stack → `no_back_affordance`
evidence.

## 4. Modals and dismissibility

```bash
rg -n 'showDialog\(' -A 4 | rg -n 'barrierDismissible'
rg -n 'isDismissible:\s*false|enableDrag:\s*false|WillPopScope|PopScope'
```

`barrierDismissible: false` or `PopScope(canPop: false)` → `blocking_modal` / `unskippable`.

## 5. Async state and error handling

Flutter's async UI is where friction hides. Three patterns to grep:

```bash
rg -n 'FutureBuilder|StreamBuilder' -A 8        # does it handle hasError and !hasData?
rg -n '\.when\(' -A 4                           # riverpod AsyncValue: data/loading/error
rg -n 'BlocBuilder|BlocConsumer|state is .*Error' -A 4
rg -n 'try\s*\{' -A 8 | rg -n 'catch'
```

- `FutureBuilder` without a `snapshot.hasError` branch → `no_error_state`
- `AsyncValue.when` with `error: (_, __) => const SizedBox()` → `silent_failure`
- a `catch` that only `debugPrint`s → `silent_failure`
- no `CircularProgressIndicator` / shimmer on an awaited call → `no_loading_state`

## 6. Empty states

```bash
rg -n 'ListView\.builder' -A 4
rg -n 'itemCount:\s*0|isEmpty|EmptyState|NoResults'
```

`ListView.builder` with no `isEmpty` branch → `no_empty_state`.

## 7. Forms

```bash
rg -n 'TextFormField' -A 4 | rg -n 'validator:'
rg -n 'GlobalKey<FormState>|_formKey\.currentState!\.validate'
```

Count `required_fields` from the `validator:` callbacks that reject empty input. More than five
on one screen → `long_form`.

## 8. Entry points, permissions, platform channels

```bash
grep -A 25 'intent-filter' android/app/src/main/AndroidManifest.xml 2>/dev/null
grep -A 10 'CFBundleURLTypes\|associated-domains' ios/Runner/Info.plist 2>/dev/null
rg -n 'uni_links|app_links|getInitialLink|firebase_dynamic_links'
rg -n 'Permission\.[a-z]+\.request\(|permission_handler'
rg -n 'FirebaseMessaging\.onMessageOpenedApp|getInitialMessage'
```

Each deep link, dynamic link and notification target is a `start` node.
Each permission request is a `decision` — model the **denied** branch.

## Mapping to IR

| Found | Node |
| --- | --- |
| `GoRoute` / `AutoRoute` / named route | `screen`, `route` = path |
| `showDialog` / `showModalBottomSheet` | `modal` |
| `redirect:` / `AutoRouteGuard` / `if (user == null)` | `decision` |
| `http`/`dio` call, repository method | `api` |
| Hive / SharedPreferences / Isar / Drift write | `data` |
| `launchUrl`, in-app purchase sheet, OAuth webview | `external` |
| Bloc/Riverpod error or empty state | `state` with `kind: "error"` |
| `CircularProgressIndicator` blocking the screen | `annotations.wait` |

Suggested lanes: `user` → `app` → `api` → `device`.
