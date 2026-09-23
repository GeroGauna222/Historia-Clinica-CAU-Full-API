# Visual Foundation & Identity — Design

- **Date:** 2026-09-23
- **Status:** Approved in brainstorming, pending written-spec review
- **Scope:** Spec 1 of 2. Spec 2 (appointment events in the Agenda / Group Agenda FullCalendar views) is out of scope here and builds on the tokens defined below.

## 1. Problem

The frontend has no single source of truth for color, which causes visible light/dark inconsistencies:

1. **Two competing color systems.** PrimeVue runs the stock Aura preset (no `definePreset`), while `tailwind.config.js` redefines `primary`, `surface`, and `textcolor` with static hex values. In Tailwind v3 the user config overrides the `tailwindcss-primeui` plugin keys, so:
   - `bg-primary-*` renders a fixed `#009688`-family teal while PrimeVue components render Aura's emerald.
   - The `surface` scale is half static (`0`, `50`, `100`, `900`, `950`) and half dynamic (`200`–`800` from the plugin), so it breaks in dark mode.
2. **Dark mode is not persisted inside the app.** `layout.js#toggleDarkMode` never writes `localStorage`. Only `FloatingConfigurator.vue` (Login and Recover Password) does, so reloading an in-app page reverts to light.
3. **`src/assets/theme-dark.css`** (~216 lines) is a patch sheet full of `!important`. Its `html.dark` selectors are dead code because the app only ever sets `.app-dark`. The same dead selectors appear in `calendar-medical.css`.
4. **`AppConfigurator.vue`** lets any user change the preset, primary, and surface at runtime, which guarantees inconsistency with Tailwind utilities.
5. About 19 of 49 `.vue` files have no dark-mode handling at all.

## 2. Goals / Non-goals

**Goals**
- One token source (PrimeVue preset) consumed by both PrimeVue components and Tailwind utilities.
- New visual identity, direction "A: Clinical calm": a deeper accessible teal, slate neutrals, soft shadows in light and none in dark, 10px content radius, comfortable density.
- Three-state color scheme (System / Light / Dark), defaulting to System, persisted per browser, with no flash on load.
- Hand-polished layouts for: Login, Dashboard, Patient History & Evolutions, Patient List/Search.
- Every other screen inherits the new look and correct dark mode through tokens, without a layout redesign.
- A guard that prevents hardcoded colors from coming back.

**Non-goals**
- Agenda / Group Agenda / FullCalendar event styling (Spec 2). `calendar-medical.css` and the JS status-color blocks in `Turnos.vue` / `ModuloRehabilitacion.vue` stay untouched except where they break the build.
- Layout redesign of Groups management, Availability, Absences, Users, and Blockchain views.
- Backend or API changes.

## 3. Design

### 3.1 Token foundation

**New file `src/theme/cauPreset.js`**: `definePreset(Aura, { ... })` exporting `CauPreset`.

- `primitive.cau`: a teal scale 50–950 anchored on `#0F766E` (600) with `#2DD4BF` (400) as the dark-mode primary.
- `semantic.primary`: maps to `{cau.50}` … `{cau.950}`.
- `semantic.colorScheme.light`:
  - `primary.color = {cau.700}` (`#0F766E`), `contrastColor = #FFFFFF`, hover/active one step darker.
  - `surface`: slate scale (`0: #FFFFFF`, `50: #F8FAFC`, `100: #F1F5F9`, `200: #E2E8F0`, … `950: #020617`).
  - `highlight`: `{cau.50}` background with `{cau.800}` text.
  - Text: `#0F172A`, muted `#64748B`.
- `semantic.colorScheme.dark`:
  - `primary.color = {cau.400}` (`#2DD4BF`), `contrastColor = #042F2E`.
  - `surface`: dark slate scale anchored on `0: #FFFFFF` … `800: #131C2E` (card), `900: #0F172A` (chrome), `950: #0B1220` (app background).
  - `highlight`: `rgba(45,212,191,.12)` background with `#5EEAD4` text.
  - Text: `#E2E8F0`, muted `#94A3B8`.
- Shape: content border radius `10px`, form-field radius `8px`.
- Focus ring: 2px `{primary.color}` with offset, identical in both modes.

**Appointment status tokens** are emitted as CSS custom properties under `:root` and `.app-dark` in `src/theme/status.css`, using the DB enum `turnos.estado_asistencia`:

| Token | Meaning | Light fg / bg | Dark fg / bg |
|---|---|---|---|
| `--cau-status-programado-*` | Scheduled | `#334155` / `#F1F5F9` | `#CBD5E1` / `rgba(148,163,184,.14)` |
| `--cau-status-presente-*` | Present | `#15803D` / `#DCFCE7` | `#4ADE80` / `rgba(74,222,128,.12)` |
| `--cau-status-con-aviso-*` | Absent, notified | `#B45309` / `#FEF3C7` | `#FBBF24` / `rgba(251,191,36,.12)` |
| `--cau-status-sin-aviso-*` | Absent, no notice | `#B91C1C` / `#FEE2E2` | `#F87171` / `rgba(248,113,113,.12)` |

Each status exposes `-fg`, `-bg`, and `-border`. Spec 2 consumes these; it may add further states.

**Wiring**
- `main.js`: `theme: { preset: CauPreset, options: { darkModeSelector: '.app-dark', cssLayer: false } }`.
- `tailwind.config.js`: remove `colors.primary`, `colors.surface`, and `colors.textcolor` so the `tailwindcss-primeui` plugin mappings take effect. Keep `darkMode` and `screens`.
- Fonts: body `Inter`, headings `Figtree`, both loaded once from `index.html`. Remove `Noto Sans`.
- Views use semantic utilities: `bg-surface-0`, `bg-surface-50`, `text-color`, `text-muted-color`, `border-surface`, `bg-emphasis`, `bg-highlight`, `bg-primary`, `text-primary`. `dark:` variants are no longer needed for colors.

**Removed**
- `src/assets/theme-dark.css` and its import in `styles.scss`.
- `src/layout/AppConfigurator.vue` and any trigger for it in `AppTopbar.vue`.
- Preset, primary, and surface state in `layout.js`.

### 3.2 Color scheme (dark mode)

**New composable `src/theme/useColorScheme.js`** (module-level singleton state):

- `mode: Ref<'system' | 'light' | 'dark'>`, persisted in `localStorage['cau-color-scheme']`, default `'system'`.
- `isDark: ComputedRef<boolean>`, which resolves `system` through `matchMedia('(prefers-color-scheme: dark)')` and updates live on OS changes while in `system` mode.
- `setMode(mode)`: persists and applies.
- `apply()`: toggles `.app-dark` on `document.documentElement` and sets `style.colorScheme`. This is the ONLY code path that touches `.app-dark`.
- Legacy migration: if `localStorage['theme']` (`'dark'` / `'light'`) exists and the new key does not, adopt it once and remove the old key.
- Every `localStorage` access is wrapped in try/catch. If storage fails, the app falls back to `system` and still renders.

**No flash on load:** an inline `<script>` in `index.html` `<head>` reads the same key (including the legacy key), resolves `system`, and applies `.app-dark` before the bundle loads. It is kept at ~10 lines and mirrors the composable's resolution rules.

**Init:** `main.js` calls `useColorScheme().init()` before `app.mount`.

**UI:** `src/components/ui/ColorSchemeSwitcher.vue` is an icon button (sun / moon / desktop for the current mode) that opens a PrimeVue `Menu` with the three options, marking the active one and giving each an `aria-label`. It is used in `AppTopbar.vue` and in the slimmed-down `FloatingConfigurator.vue` (Login, Recover Password).

### 3.3 App shell

- **Topbar:** `bg-surface-0` with a bottom `border-surface` and no shadow. Logo in `text-primary` Figtree 600. The user menu and `ColorSchemeSwitcher` sit on the right.
- **Sidebar:** `bg-surface-0` with a right border. The active item uses `bg-highlight` with a semibold weight; hover uses `bg-emphasis`. 8px item radius.
- **Main area:** `bg-surface-50` in light and `surface-950` in dark, via the preset. Cards use `bg-surface-0` in light and `surface-800` in dark, with a `border-surface`, a 10px radius, and a soft shadow in light only.
- **Footer:** no hex, `text-muted-color`.
- Sakai SCSS files (`_topbar.scss`, `_menu.scss`, `_main.scss`, `_footer.scss`, `variables/_light.scss`, `variables/_dark.scss`) are updated to reference `--p-*` variables instead of literal colors.

### 3.4 Shared UI pieces (`src/components/ui/`)

| Component | Purpose | Props / slots |
|---|---|---|
| `PageHeader.vue` | Consistent page title block | `title`, `subtitle?`; slots `breadcrumb`, `actions` |
| `StatTile.vue` | KPI on Dashboard | `label`, `value`, `icon?`, `hint?` |
| `EmptyState.vue` | Empty / no-results lists | `icon`, `title`, `message?`; slot `action` |
| `StatusTag.vue` | Appointment or signature status | `status` (enum key), `size?`; reads `--cau-status-*` |
| `ColorSchemeSwitcher.vue` | See 3.2 | none |

Components use only semantic utilities and tokens, with no hex values and no `dark:`.

### 3.5 Screen polish (in scope)

Each screen gets a companion mockup (light and dark) approved during planning, before implementation.

- **Login** (`views/pages/auth/Login.vue`): a centered card on `surface-50` with a subtle brand accent, the logo and app name in Figtree, full-width primary button, `ColorSchemeSwitcher` in the corner, and AA contrast in both modes.
- **Dashboard** (`views/Dashboard.vue` + `components/dashboard/*`): `PageHeader` with a greeting and date, a row of `StatTile`s, and `ProximoTurnoWidget` using `StatusTag`. Hardcoded hex and `bg-white` usages are removed.
- **Patient History & Evolutions** (`views/pages/historias/HistoriaPaciente.vue` and evolution views): a sticky patient header (name, DNI, age, key data), evolutions as a readable vertical timeline (date, professional, body, attachments), and the blockchain seal and signature status as quiet metadata (`StatusTag` for `estado_firma`).
- **Patient List / Search** (`views/pages/historias/Pacientes.vue` and `views/pages/historias/BuscarHistorias.vue`): a prominent search field, a DataTable with comfortable density and consistent row actions, and `EmptyState` for no results.

### 3.6 Everything else

All remaining views inherit the preset. Mechanical pass: replace `bg-white`, `text-gray-*`, `bg-gray-*`, `border-gray-*`, and paired `dark:` color classes with semantic utilities; replace hex values in templates and styles with tokens. Views with zero dark coverage today (`BlockchainVerificar.vue`, `BuscarHistorias.vue`, `Logout.vue`, `AppTopbar.vue`, `ProximoTurnoWidget.vue`) are included. Calendar files in Spec 2's scope are excluded.

## 4. Verification

1. **Vitest** (new devDependency, plus `jsdom`), with `npm run test`. It covers `useColorScheme`:
   - Default is `system` and follows a mocked `matchMedia`, including live changes.
   - `setMode` persists and toggles `.app-dark`.
   - Legacy `theme` key migration.
   - Storage throwing falls back to `system` without crashing.
2. **Token guard** `npm run check:tokens` (a Node script in `scripts/check-tokens.mjs`) fails on hex colors, `bg-white`, `text-gray-*`, `bg-gray-*`, `border-gray-*`, or `dark:` color utilities under `src/views`, `src/layout`, and `src/components`. It has an explicit allowlist for the Spec 2 calendar files until Spec 2 lands.
3. **Build and lint**: `npm run build` and `npm run lint` stay clean.
4. **Visual check**: Playwright screenshots of the four polished screens plus one inherited screen, in light and dark, reviewed before closing.

## 5. Risks

- **PrimeVue token names:** the exact `definePreset` keys must be checked against the installed `@primeuix/themes` version during implementation.
- **Removing Tailwind `primary.DEFAULT`:** any `bg-primary` that relied on `#00BFA5` changes hue. This is intended, but verify on the polished screens.
- **Sakai SCSS literal colors** may be spread widely. They are handled in the shell pass, and the guard catches regressions only in `.vue` files, not in SCSS.
- **Large diff:** likely over 400 changed lines. Plan to split into chained work units: (1) tokens + color scheme + shell, (2) shared UI pieces + mechanical pass, (3) screen polish, one screen per unit.
