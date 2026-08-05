# Discovery — React Native / Expo

## 1. Identify the navigation library

```bash
rg -n '"(@react-navigation/[a-z-]+|expo-router|react-native-navigation)"' package.json
ls -d app src/app 2>/dev/null          # expo-router uses a filesystem router
```

| Evidence | Router |
| --- | --- |
| `app/` with `_layout.tsx` | Expo Router (filesystem) |
| `@react-navigation/native` | React Navigation (declarative) |
| `react-native-navigation` | Wix RNN (native stacks) |

## 2a. Expo Router — filesystem routes

```bash
find app -name '*.tsx' -o -name '*.jsx' | sort
```

Conventions that change the flow shape:

- `app/(tabs)/_layout.tsx` → tab navigator; each child is a tab root and therefore an **entry point**
- `app/(auth)/_layout.tsx` → typically the auth gate; read its redirect logic
- `app/+not-found.tsx` → the 404 screen
- `app/[id].tsx` → dynamic route
- `_layout.tsx` with `<Stack.Screen options={{ presentation: 'modal' }} />` → that child is a `modal`
- `<Redirect href="/login" />` inside a layout → a `decision` node

## 2b. React Navigation — declarative routes

```bash
rg -n 'createNativeStackNavigator|createBottomTabNavigator|createDrawerNavigator|createMaterialTopTabNavigator'
rg -n '<Stack\.Screen|<Tab\.Screen|<Drawer\.Screen' -A 2
```

Each `<Stack.Screen name="Payment" component={PaymentScreen} />` is a node; `name` is the
route, the component file is the `source`.

`options={{ headerLeft: () => null }}`, `gestureEnabled: false`, or
`headerBackVisible: false` → **`no_back_affordance`**. This is the single most common finding
in React Native apps and it is trivial to grep for:

```bash
rg -n 'headerLeft:\s*\(\)\s*=>\s*null|gestureEnabled:\s*false|headerBackVisible:\s*false'
```

## 3. Transitions

```bash
rg -n 'navigation\.(navigate|push|replace|goBack|popToTop|reset)\('
rg -n 'router\.(push|replace|back|navigate)\('        # expo-router
rg -n 'useNavigation\(|useRouter\(|<Link href='
rg -n 'Linking\.openURL|openBrowserAsync|WebBrowser\.'   # -> external nodes
```

`navigation.reset(...)` and `router.replace(...)` destroy the back stack — record it.

## 4. Deep links and entry points

```bash
cat app.json app.config.* 2>/dev/null | grep -A 20 -E '"scheme"|"associatedDomains"|intentFilters'
rg -n 'linking\s*=|prefixes:|getInitialURL|addEventListener\([\x27"]url'
rg -n 'Notifications\.addNotificationResponseReceivedListener|onNotification'
```

Every deep-link target and every notification tap target is a `start` node in some flow — and
those flows are usually the least designed ones in the product.

## 5. Network calls, states, permissions

```bash
rg -n 'fetch\(|axios\.|useQuery\(|useMutation\('
rg -n 'ActivityIndicator|isLoading|isPending|Skeleton'
rg -n 'ListEmptyComponent|data\.length === 0|EmptyState'
rg -n 'catch\s*\(' -A 3
rg -n 'requestPermissionsAsync|PermissionsAndroid|requestTrackingPermissions'
```

- `<FlatList>` without `ListEmptyComponent` → `no_empty_state`
- `catch` that only logs → `silent_failure`
- any `requestPermissionsAsync` on the critical path → a `decision` node plus the
  `permission_prompt` friction tag; model the **denied** branch, it is nearly always missing

## 6. Offline and connectivity

```bash
rg -n 'NetInfo|useNetInfo|onlineManager|isConnected'
```

Mobile apps go offline. If the flow has no offline branch, that is a real finding — model the
absence in `annotations.note` rather than inventing a branch that does not exist.

## 7. Modals and sheets

```bash
rg -n '<Modal|BottomSheet|presentation:\s*[\x27"]modal|@gorhom/bottom-sheet'
rg -n 'onRequestClose|enablePanDownToClose|backdropPressBehavior'
```

`<Modal>` without `onRequestClose` traps the Android back button → `blocking_modal`.

## Mapping to IR

| Found | Node |
| --- | --- |
| `Stack.Screen` / `app/*.tsx` route | `screen` |
| `presentation: 'modal'`, `<Modal>`, bottom sheet | `modal` |
| tab root | `screen`, and also a `start` node for its own flow |
| `<Redirect>`, auth layout guard, `if (!user)` | `decision` |
| permission request | `decision` + `permission_prompt` |
| `fetch` / `useMutation` | `api` |
| AsyncStorage / MMKV / SecureStore / SQLite write | `data` |
| `Linking.openURL`, in-app browser, native share | `external` |
| `ActivityIndicator` blocking the screen | `annotations.wait`, not a node |

Suggested lanes for mobile: `user` → `app` → `api` → `device` (permissions, storage, OS).
