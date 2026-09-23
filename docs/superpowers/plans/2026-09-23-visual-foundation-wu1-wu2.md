# Visual Foundation (WU1 + WU2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the PrimeVue preset the single color source for PrimeVue and Tailwind. Add a persisted three-state color scheme with no flash on load, restyle the app shell, add shared UI pieces, and migrate every non-calendar view to semantic tokens. A guard keeps hardcoded colors from coming back.

**Architecture:**
- `definePreset(Aura, …)` (`src/theme/cauPreset.js`) emits `--p-*` CSS variables. Tailwind consumes them through two sources: the `tailwindcss-primeui` plugin, and a few extra colors (`card`, `ground`, `subtle`, `line`, `status-*`) built from those variables.
- A module-singleton composable (`src/theme/useColorScheme.js`) is the only runtime code that toggles `.app-dark`. An inline `<head>` script mirrors its resolution rules so nothing flashes on load.
- The view migration uses a tested one-shot codemod (`scripts/migrate-tokens.mjs`). A tested guard (`scripts/check-tokens.mjs`) enforces the result.

**Tech Stack:**
- Frontend: Vue 3.4, Vite 7, PrimeVue 4.3 with `@primeuix/themes` 1.2 (Aura base), Tailwind CSS 3.4 with `tailwindcss-primeui` 0.5, Sass.
- New dev dependencies: Vitest 3, jsdom, `@vue/test-utils` 2.

**Spec:** `docs/superpowers/specs/2026-09-23-visual-foundation-design.md` (this plan covers §3.1, §3.2, §3.3, §3.4, §3.6 and §4; §3.5 screen polish is WU3 and out of scope).

## Global Constraints

- **Branch:** work on `feat/visual-foundation`. Do not switch branches.
- **Language:**
  - All code, comments and identifiers are in English.
  - Keep existing Spanish UI strings unchanged.
  - New UI labels are Spanish: "Sistema", "Claro", "Oscuro", "Tema".
- **Commits:** conventional commits (`feat(frontend): …`, `refactor(frontend): …`, `test(frontend): …`, `chore(frontend): …`). NO `Co-Authored-By` or AI attribution lines.
- **Frontend only:**
  - Services pattern unchanged: components never call axios directly.
  - No backend, API, or `db/init.sql` changes.
- **No hardcoded colors:** no `dark:` color utilities and no hex literals in new or modified `.vue` files. The only exception is the allowlist:
  - `src/views/pages/historias/Turnos.vue`
  - `src/views/pages/turnos/CalendarioGrupo.vue`
  - `src/views/pages/turnos/ModuloRehabilitacion.vue`
- **Storage:** every `localStorage` access is wrapped in `try/catch`. An empty `catch` must contain a comment (ESLint `no-empty`).
- **`.app-dark`:** only `useColorScheme().apply()` and the inline anti-flash script in `index.html` may toggle `.app-dark`.
- **Out of scope (Spec 2):** do not edit the three allowlisted calendar views, `src/assets/calendar-medical.css`, or the JS status-color blocks inside them.
- **Commands:** run every command from `frontend/`:
  - `npm run test`
  - `npm run build`
  - `npm run lint`
  - `npm run check:tokens` (exists from Task 5 on)
- **Surfaces in dark mode:** PrimeVue keeps `--p-surface-0` = `#ffffff` in dark mode, so `bg-surface-0` and `bg-surface-50` stay light there. Never use them for surfaces. Use:
  - `bg-card` (content background)
  - `bg-ground` (app background)
  - `bg-subtle` (subtle panel)
  - `border-surface`
  - `divide-line`
  - `ring-line`
  - `bg-emphasis`
  - `bg-highlight`
- **Status colors:** `text-status-<s>-fg`, `bg-status-<s>-bg` and `border-status-<s>-border`, where `<s>` is one of `programado`, `presente`, `con-aviso` or `sin-aviso`.

---

## File Map

| File | Responsibility | Task |
|---|---|---|
| `frontend/vite.config.mjs` | Add the Vitest `test` block | 1 |
| `frontend/package.json` | `test` and `check:tokens` scripts, dev dependencies | 1, 5 |
| `frontend/src/theme/useColorScheme.js` (+ `.test.js`) | Color-scheme state, persistence, `.app-dark` application | 1 |
| `frontend/src/theme/cauPreset.js` (+ `.test.js`) | PrimeVue preset (single token source) | 2 |
| `frontend/src/theme/status.css` | `--cau-status-*` custom properties | 2 |
| `frontend/tailwind.config.js` | Drop static palettes; add token-backed colors | 2 |
| `frontend/index.html` | Fonts plus the anti-flash script | 2 |
| `frontend/src/main.js` | Preset wiring, status.css import, `init()` | 2 |
| `frontend/src/assets/styles.scss` | Drop the theme-dark import; Inter body font | 2 |
| `frontend/src/components/ui/ColorSchemeSwitcher.vue` (+ test) | Mode switcher UI | 3 |
| `frontend/src/components/FloatingConfigurator.vue` | Slimmed to the switcher only | 3 |
| `frontend/src/layout/AppTopbar.vue`, `frontend/src/layout/composables/layout.js` | Remove the configurator and dark toggle | 3 |
| `frontend/src/assets/theme-dark.css`, `frontend/src/layout/AppConfigurator.vue` | Deleted | 3 |
| `frontend/src/assets/layout/**/*.scss`, `frontend/src/layout/AppFooter.vue` | Shell uses `--p-*` variables | 4 |
| `frontend/scripts/check-tokens.mjs` (+ test) | Token guard | 5 |
| `frontend/scripts/migrate-tokens.mjs` (+ test) | Codemod for the mechanical pass | 6 |
| `frontend/src/components/ui/{PageHeader,StatTile,EmptyState,StatusTag}.vue` (+ tests) | Shared UI | 7 |
| Views and components (Tasks 8–11) | Mechanical migration | 8–11 |

**Excluded from the mechanical pass (Spec 2):**
- `src/views/pages/historias/Turnos.vue`
- `src/views/pages/turnos/CalendarioGrupo.vue`
- `src/views/pages/turnos/ModuloRehabilitacion.vue`
- `src/assets/calendar-medical.css`

---

### Task 1: Vitest setup and `useColorScheme`

**Files:**
- Modify: `frontend/package.json` (scripts, devDependencies)
- Modify: `frontend/vite.config.mjs` (add `test` block)
- Create: `frontend/src/theme/useColorScheme.js`
- Test: `frontend/src/theme/useColorScheme.test.js`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `useColorScheme()` returns `{ mode: Readonly<Ref<'system'|'light'|'dark'>>, isDark: ComputedRef<boolean>, setMode(next: string): void, init(): void, apply(): void }`.
  - Named exports `STORAGE_KEY = 'cau-color-scheme'`, `LEGACY_KEY = 'theme'` and `MODES = ['system','light','dark']`.

- [ ] **Step 1: Install test tooling**

Run: `cd frontend && npm install -D vitest@^3.2.0 jsdom@^26.0.0 @vue/test-utils@^2.4.6`
Expected: `package.json` devDependencies now list `vitest`, `jsdom` and `@vue/test-utils`.

- [ ] **Step 2: Add the test script and Vitest config**

In `frontend/package.json` `scripts`, add after `"lint"`:

```json
        "test": "vitest run"
```

In `frontend/vite.config.mjs`, add a `test` key after `resolve` (inside `defineConfig({...})`):

```js
    test: {
        environment: 'jsdom',
        include: ['src/**/*.test.js', 'scripts/**/*.test.mjs']
    },
```

- [ ] **Step 3: Write the failing tests**

Create `frontend/src/theme/useColorScheme.test.js`:

```js
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const QUERY = '(prefers-color-scheme: dark)';

function mockMatchMedia(initialDark) {
    const listeners = new Set();
    const mql = {
        matches: initialDark,
        media: QUERY,
        addEventListener: (_type, cb) => listeners.add(cb),
        removeEventListener: (_type, cb) => listeners.delete(cb)
    };
    window.matchMedia = vi.fn(() => mql);
    return {
        setDark(value) {
            mql.matches = value;
            listeners.forEach((cb) => cb({ matches: value }));
        }
    };
}

async function loadFresh() {
    vi.resetModules();
    return import('./useColorScheme.js');
}

const root = () => document.documentElement;

describe('useColorScheme', () => {
    beforeEach(() => {
        window.localStorage.clear();
        root().className = '';
        root().style.colorScheme = '';
    });

    afterEach(() => {
        vi.restoreAllMocks();
        delete window.matchMedia;
    });

    it('defaults to system and follows the OS preference live', async () => {
        const media = mockMatchMedia(true);
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        scheme.init();

        expect(scheme.mode.value).toBe('system');
        expect(scheme.isDark.value).toBe(true);
        expect(root().classList.contains('app-dark')).toBe(true);
        expect(root().style.colorScheme).toBe('dark');

        media.setDark(false);

        expect(scheme.isDark.value).toBe(false);
        expect(root().classList.contains('app-dark')).toBe(false);
        expect(root().style.colorScheme).toBe('light');
    });

    it('setMode persists the choice and applies it', async () => {
        mockMatchMedia(false);
        const { useColorScheme, STORAGE_KEY } = await loadFresh();
        const scheme = useColorScheme();
        scheme.init();

        scheme.setMode('dark');
        expect(window.localStorage.getItem(STORAGE_KEY)).toBe('dark');
        expect(root().classList.contains('app-dark')).toBe(true);

        scheme.setMode('light');
        expect(window.localStorage.getItem(STORAGE_KEY)).toBe('light');
        expect(root().classList.contains('app-dark')).toBe(false);
        expect(root().style.colorScheme).toBe('light');
    });

    it('ignores unknown modes', async () => {
        mockMatchMedia(false);
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();
        scheme.init();

        scheme.setMode('sepia');

        expect(scheme.mode.value).toBe('system');
    });

    it('restores a stored mode on init', async () => {
        mockMatchMedia(false);
        window.localStorage.setItem('cau-color-scheme', 'dark');
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        scheme.init();

        expect(scheme.mode.value).toBe('dark');
        expect(root().classList.contains('app-dark')).toBe(true);
    });

    it('migrates the legacy theme key once', async () => {
        mockMatchMedia(false);
        window.localStorage.setItem('theme', 'dark');
        const { useColorScheme, STORAGE_KEY, LEGACY_KEY } = await loadFresh();
        const scheme = useColorScheme();

        scheme.init();

        expect(scheme.mode.value).toBe('dark');
        expect(window.localStorage.getItem(STORAGE_KEY)).toBe('dark');
        expect(window.localStorage.getItem(LEGACY_KEY)).toBeNull();
    });

    it('falls back to system when storage throws', async () => {
        mockMatchMedia(true);
        const denied = () => {
            throw new Error('storage denied');
        };
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(denied);
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(denied);
        vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(denied);
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        expect(() => scheme.init()).not.toThrow();
        expect(scheme.mode.value).toBe('system');
        expect(root().classList.contains('app-dark')).toBe(true);

        expect(() => scheme.setMode('light')).not.toThrow();
        expect(root().classList.contains('app-dark')).toBe(false);
    });

    it('works when matchMedia is unavailable', async () => {
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        expect(() => scheme.init()).not.toThrow();
        expect(scheme.isDark.value).toBe(false);
    });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd frontend && npm run test -- src/theme/useColorScheme.test.js`
Expected: FAIL. The suite errors with "Failed to load url ./useColorScheme.js" (or "Cannot find module").

- [ ] **Step 5: Implement the composable**

Create `frontend/src/theme/useColorScheme.js`:

```js
import { computed, readonly, ref } from 'vue';

export const STORAGE_KEY = 'cau-color-scheme';
export const LEGACY_KEY = 'theme';
export const MODES = ['system', 'light', 'dark'];

const QUERY = '(prefers-color-scheme: dark)';

// Module-level singleton state shared by every caller.
const mode = ref('system');
const systemDark = ref(false);
let mediaQuery = null;

const isDark = computed(() => mode.value === 'dark' || (mode.value === 'system' && systemDark.value));

function readStorage(key) {
    try {
        return window.localStorage.getItem(key);
    } catch (error) {
        // Storage unavailable (private mode, blocked site data): behave as empty.
        return null;
    }
}

function writeStorage(key, value) {
    try {
        window.localStorage.setItem(key, value);
    } catch (error) {
        // Storage unavailable: the choice lives for this page load only.
    }
}

function removeStorage(key) {
    try {
        window.localStorage.removeItem(key);
    } catch (error) {
        // Storage unavailable: nothing to clean up.
    }
}

function resolveStoredMode() {
    const stored = readStorage(STORAGE_KEY);
    if (MODES.includes(stored)) {
        return stored;
    }

    const legacy = readStorage(LEGACY_KEY);
    if (legacy === 'dark' || legacy === 'light') {
        writeStorage(STORAGE_KEY, legacy);
        removeStorage(LEGACY_KEY);
        return legacy;
    }

    return 'system';
}

function apply() {
    const root = document.documentElement;
    root.classList.toggle('app-dark', isDark.value);
    root.style.colorScheme = isDark.value ? 'dark' : 'light';
}

function handleSystemChange(event) {
    systemDark.value = event.matches;
    apply();
}

function init() {
    mode.value = resolveStoredMode();

    if (!mediaQuery && typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
        mediaQuery = window.matchMedia(QUERY);
        if (typeof mediaQuery.addEventListener === 'function') {
            mediaQuery.addEventListener('change', handleSystemChange);
        } else if (typeof mediaQuery.addListener === 'function') {
            mediaQuery.addListener(handleSystemChange);
        }
    }

    systemDark.value = mediaQuery ? mediaQuery.matches : false;
    apply();
}

function setMode(next) {
    if (!MODES.includes(next)) {
        return;
    }
    mode.value = next;
    writeStorage(STORAGE_KEY, next);
    apply();
}

export function useColorScheme() {
    return {
        mode: readonly(mode),
        isDark,
        setMode,
        init,
        apply
    };
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npm run test -- src/theme/useColorScheme.test.js`
Expected: PASS, 7 tests.

- [ ] **Step 7: Lint**

Run: `cd frontend && npm run lint`
Expected: exit code 0 and no errors reported for `src/theme/*`.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.mjs frontend/src/theme/useColorScheme.js frontend/src/theme/useColorScheme.test.js
git commit -m "feat(frontend): add persisted three-state color scheme composable"
```

---

### Task 2: CauPreset, status tokens, Tailwind wiring, fonts and anti-flash

**Files:**
- Create: `frontend/src/theme/cauPreset.js`
- Create: `frontend/src/theme/status.css`
- Test: `frontend/src/theme/cauPreset.test.js`
- Modify: `frontend/src/main.js` (Aura import, `app.use(PrimeVue, …)`, and the lines before `app.mount`)
- Modify: `frontend/tailwind.config.js` (whole file)
- Modify: `frontend/index.html` (head)
- Modify: `frontend/src/assets/styles.scss` (lines 7–15)

**Interfaces:**
- Consumes: `useColorScheme().init()` from Task 1.
- Produces:
  - The `CauPreset` named export.
  - CSS variables:
    - `--p-app-background`
    - `--p-app-subtle-background`
    - `--cau-status-{programado|presente|con-aviso|sin-aviso}-{fg|bg|border}`
  - Tailwind colors:
    - `card`, `ground`, `subtle`, `line`
    - `status.<s>.{fg,bg,border}`: classes like `bg-status-presente-bg`

- [ ] **Step 1: Write the failing preset test**

Create `frontend/src/theme/cauPreset.test.js`:

```js
import { describe, expect, it } from 'vitest';
import { CauPreset } from './cauPreset.js';

describe('CauPreset', () => {
    it('anchors the light primary on cau.700 and the dark primary on cau.400', () => {
        const { light, dark } = CauPreset.semantic.colorScheme;
        expect(CauPreset.primitive.cau[700]).toBe('#0f766e');
        expect(light.primary.color).toBe('{cau.700}');
        expect(dark.primary.color).toBe('{cau.400}');
    });

    it('defines app background tokens in both schemes', () => {
        const { light, dark } = CauPreset.semantic.colorScheme;
        expect(light.app.background).toBe('{surface.50}');
        expect(dark.app.background).toBe('{surface.950}');
        expect(dark.surface[950]).toBe('#0b1220');
        expect(dark.content.background).toBe('{surface.800}');
    });

    it('sets shape and focus ring', () => {
        expect(CauPreset.semantic.content.borderRadius).toBe('10px');
        expect(CauPreset.semantic.formField.borderRadius).toBe('8px');
        expect(CauPreset.semantic.focusRing.width).toBe('2px');
    });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- src/theme/cauPreset.test.js`
Expected: FAIL. The module `./cauPreset.js` is not found.

- [ ] **Step 3: Create the preset**

Create `frontend/src/theme/cauPreset.js`:

```js
import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

const slate = {
    0: '#ffffff',
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617'
};

export const CauPreset = definePreset(Aura, {
    primitive: {
        cau: {
            50: '#f0fdfa',
            100: '#ccfbf1',
            200: '#99f6e4',
            300: '#5eead4',
            400: '#2dd4bf',
            500: '#14b8a6',
            600: '#0d9488',
            700: '#0f766e',
            800: '#115e59',
            900: '#134e4a',
            950: '#042f2e'
        }
    },
    semantic: {
        primary: {
            50: '{cau.50}',
            100: '{cau.100}',
            200: '{cau.200}',
            300: '{cau.300}',
            400: '{cau.400}',
            500: '{cau.500}',
            600: '{cau.600}',
            700: '{cau.700}',
            800: '{cau.800}',
            900: '{cau.900}',
            950: '{cau.950}'
        },
        focusRing: {
            width: '2px',
            style: 'solid',
            color: '{primary.color}',
            offset: '2px',
            shadow: 'none'
        },
        formField: {
            borderRadius: '8px'
        },
        content: {
            borderRadius: '10px'
        },
        colorScheme: {
            light: {
                surface: slate,
                primary: {
                    color: '{cau.700}',
                    contrastColor: '#ffffff',
                    hoverColor: '{cau.800}',
                    activeColor: '{cau.900}'
                },
                highlight: {
                    background: '{cau.50}',
                    focusBackground: '{cau.100}',
                    color: '{cau.800}',
                    focusColor: '{cau.900}'
                },
                text: {
                    color: '{surface.900}',
                    hoverColor: '{surface.950}',
                    mutedColor: '{surface.500}',
                    hoverMutedColor: '{surface.600}'
                },
                app: {
                    background: '{surface.50}',
                    subtleBackground: '{surface.50}'
                }
            },
            dark: {
                surface: {
                    ...slate,
                    700: '#1e293b',
                    800: '#131c2e',
                    900: '#0f172a',
                    950: '#0b1220'
                },
                primary: {
                    color: '{cau.400}',
                    contrastColor: '#042f2e',
                    hoverColor: '{cau.300}',
                    activeColor: '{cau.200}'
                },
                highlight: {
                    background: 'rgba(45, 212, 191, 0.12)',
                    focusBackground: 'rgba(45, 212, 191, 0.2)',
                    color: '#5eead4',
                    focusColor: '{cau.200}'
                },
                text: {
                    color: '{surface.200}',
                    hoverColor: '{surface.0}',
                    mutedColor: '{surface.400}',
                    hoverMutedColor: '{surface.300}'
                },
                content: {
                    background: '{surface.800}',
                    hoverBackground: '{surface.700}',
                    borderColor: '{surface.700}'
                },
                overlay: {
                    select: { background: '{surface.800}', borderColor: '{surface.700}' },
                    popover: { background: '{surface.800}', borderColor: '{surface.700}' },
                    modal: { background: '{surface.800}', borderColor: '{surface.700}' }
                },
                formField: {
                    background: '{surface.900}'
                },
                app: {
                    background: '{surface.950}',
                    subtleBackground: '{surface.900}'
                }
            }
        }
    }
});
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- src/theme/cauPreset.test.js`
Expected: PASS, 3 tests. `definePreset` deep-merges, so the returned object keeps these keys.

- [ ] **Step 5: Create the status tokens**

Create `frontend/src/theme/status.css`:

```css
/* Appointment and signature status tokens (DB enum turnos.estado_asistencia). */
:root {
    --cau-status-programado-fg: #334155;
    --cau-status-programado-bg: #f1f5f9;
    --cau-status-programado-border: #cbd5e1;

    --cau-status-presente-fg: #15803d;
    --cau-status-presente-bg: #dcfce7;
    --cau-status-presente-border: #86efac;

    --cau-status-con-aviso-fg: #b45309;
    --cau-status-con-aviso-bg: #fef3c7;
    --cau-status-con-aviso-border: #fcd34d;

    --cau-status-sin-aviso-fg: #b91c1c;
    --cau-status-sin-aviso-bg: #fee2e2;
    --cau-status-sin-aviso-border: #fca5a5;
}

:root.app-dark {
    --cau-status-programado-fg: #cbd5e1;
    --cau-status-programado-bg: rgba(148, 163, 184, 0.14);
    --cau-status-programado-border: rgba(203, 213, 225, 0.32);

    --cau-status-presente-fg: #4ade80;
    --cau-status-presente-bg: rgba(74, 222, 128, 0.12);
    --cau-status-presente-border: rgba(74, 222, 128, 0.32);

    --cau-status-con-aviso-fg: #fbbf24;
    --cau-status-con-aviso-bg: rgba(251, 191, 36, 0.12);
    --cau-status-con-aviso-border: rgba(251, 191, 36, 0.32);

    --cau-status-sin-aviso-fg: #f87171;
    --cau-status-sin-aviso-bg: rgba(248, 113, 113, 0.12);
    --cau-status-sin-aviso-border: rgba(248, 113, 113, 0.32);
}
```

- [ ] **Step 6: Replace `tailwind.config.js`**

Overwrite `frontend/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
import PrimeUI from 'tailwindcss-primeui';

// Maps a CSS variable to a Tailwind color that still supports opacity modifiers (e.g. bg-line/60).
const token = (variable) => `color-mix(in srgb, var(${variable}) calc(100% * <alpha-value>), transparent)`;

const status = (name) => ({
    fg: token(`--cau-status-${name}-fg`),
    bg: token(`--cau-status-${name}-bg`),
    border: token(`--cau-status-${name}-border`)
});

export default {
    darkMode: ['class', '[class*="app-dark"]'],

    content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],

    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                heading: ['Figtree', 'sans-serif']
            },
            colors: {
                // PrimeVue keeps surface-0 white in dark mode; these follow the active scheme.
                card: token('--p-content-background'),
                ground: token('--p-app-background'),
                subtle: token('--p-app-subtle-background'),
                line: token('--p-content-border-color'),
                status: {
                    programado: status('programado'),
                    presente: status('presente'),
                    'con-aviso': status('con-aviso'),
                    'sin-aviso': status('sin-aviso')
                }
            }
        },

        screens: {
            sm: '576px',
            md: '768px',
            lg: '992px',
            xl: '1200px',
            '2xl': '1920px'
        }
    },

    plugins: [PrimeUI]
};
```

Removing the static `primary`, `surface` and `textcolor` palettes lets the `tailwindcss-primeui` mappings take effect (`bg-primary`, `text-primary`, `primary-50…950`, `surface-0…950`, `text-color`, `text-muted-color`, `border-surface`, `bg-emphasis`, `bg-highlight`). No file uses `textcolor-*`.

- [ ] **Step 7: Wire `main.js`**

In `frontend/src/main.js`:

Replace `import Aura from '@primeuix/themes/aura';` with:

```js
import { CauPreset } from '@/theme/cauPreset';
import { useColorScheme } from '@/theme/useColorScheme';
```

Replace the styles block:

```js
import 'primeicons/primeicons.css';
import '@/assets/styles.scss';
```

with:

```js
import 'primeicons/primeicons.css';
import '@/assets/styles.scss';
import '@/theme/status.css';
```

Replace the theme options:

```js
        theme: {
            preset: Aura,
            options: { darkModeSelector: '.app-dark' }
        }
```

with:

```js
        theme: {
            preset: CauPreset,
            options: { darkModeSelector: '.app-dark', cssLayer: false }
        }
```

Replace the mount block:

```js
    // 🔥 Ahora que el store tiene el rol, montamos la app
    app.mount('#app');
```

with:

```js
    // Color scheme must be resolved before the first render.
    useColorScheme().init();

    // 🔥 Ahora que el store tiene el rol, montamos la app
    app.mount('#app');
```

- [ ] **Step 8: Fonts and anti-flash script in `index.html`**

In `frontend/index.html`, replace the Google Fonts `<link href=…Figtree…Noto+Sans…>` line with the block below. The script mirrors `useColorScheme` resolution: new key, then the legacy key, then system.

```html
      <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
      <script>
        (function () {
          var mode = 'system';
          try {
            var stored = localStorage.getItem('cau-color-scheme');
            var legacy = localStorage.getItem('theme');
            if (stored === 'system' || stored === 'light' || stored === 'dark') mode = stored;
            else if (legacy === 'light' || legacy === 'dark') mode = legacy;
          } catch (e) { /* storage unavailable: fall back to system */ }
          var dark = mode === 'dark' || (mode === 'system' && !!window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
          document.documentElement.classList.toggle('app-dark', dark);
          document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
        })();
      </script>
```

- [ ] **Step 9: Update `styles.scss`**

In `frontend/src/assets/styles.scss`, replace everything from `@import '@/assets/theme-dark.css';` to the end of the file with:

```scss
/* Global typography: Figtree for headings, Inter for body */
body {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Figtree', sans-serif;
}
```

(`theme-dark.css` itself is deleted in Task 3. After this step it is simply no longer imported.)

- [ ] **Step 10: Verify**

Run: `cd frontend && npm run test && npm run build && npm run lint`
Expected:
- Tests: all pass, 10 tests.
- Build: succeeds.
- Lint: exit code 0.

To confirm the CSS output, run `rg -o "bg-status-presente-bg|\.bg-card" dist/assets/*.css`. It prints nothing yet, because no class uses these colors. That is expected: Tailwind emits only used classes.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/theme/cauPreset.js frontend/src/theme/cauPreset.test.js frontend/src/theme/status.css frontend/tailwind.config.js frontend/src/main.js frontend/index.html frontend/src/assets/styles.scss
git commit -m "feat(frontend): add CauPreset as single token source with status tokens"
```

---

### Task 3: ColorSchemeSwitcher and removal of the runtime configurator

**Files:**
- Create: `frontend/src/components/ui/ColorSchemeSwitcher.vue`
- Test: `frontend/src/components/ui/ColorSchemeSwitcher.test.js`
- Modify: `frontend/src/components/FloatingConfigurator.vue` (whole file)
- Modify: `frontend/src/layout/AppTopbar.vue`: script lines 1–8, line 29, lines 44–66
- Modify: `frontend/src/layout/composables/layout.js` (whole file)
- Delete: `frontend/src/layout/AppConfigurator.vue`, `frontend/src/assets/theme-dark.css`

**Interfaces:**
- Consumes: `useColorScheme()` → `{ mode, setMode }` (Task 1).
- Produces:
  - `<ColorSchemeSwitcher />`, which takes no props.
  - `useLayout()` returns only `{ layoutConfig, layoutState, toggleMenu, isSidebarActive, setActiveMenuItem }`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/ColorSchemeSwitcher.test.js`:

```js
import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import PrimeVue from 'primevue/config';
import ColorSchemeSwitcher from './ColorSchemeSwitcher.vue';
import { useColorScheme } from '@/theme/useColorScheme';

function mountSwitcher() {
    return mount(ColorSchemeSwitcher, {
        attachTo: document.body,
        global: { plugins: [[PrimeVue, { theme: 'none' }]] }
    });
}

describe('ColorSchemeSwitcher', () => {
    afterEach(() => {
        useColorScheme().setMode('system');
        document.body.innerHTML = '';
    });

    it('labels the trigger with the active mode', async () => {
        const wrapper = mountSwitcher();
        const trigger = wrapper.get('button[aria-controls="color-scheme-menu"]');

        expect(trigger.attributes('aria-label')).toBe('Tema: Sistema');
        expect(trigger.attributes('aria-haspopup')).toBe('true');

        useColorScheme().setMode('dark');
        await nextTick();

        expect(trigger.attributes('aria-label')).toBe('Tema: Oscuro');
        expect(trigger.find('.pi-moon').exists()).toBe(true);
        wrapper.unmount();
    });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- src/components/ui/ColorSchemeSwitcher.test.js`
Expected: FAIL, "Failed to resolve import ./ColorSchemeSwitcher.vue".

- [ ] **Step 3: Implement the switcher**

Create `frontend/src/components/ui/ColorSchemeSwitcher.vue`:

```vue
<script setup>
import { computed, ref } from 'vue';
import Button from 'primevue/button';
import Menu from 'primevue/menu';
import { useColorScheme } from '@/theme/useColorScheme';

const OPTIONS = [
    { mode: 'system', label: 'Sistema', icon: 'pi pi-desktop' },
    { mode: 'light', label: 'Claro', icon: 'pi pi-sun' },
    { mode: 'dark', label: 'Oscuro', icon: 'pi pi-moon' }
];

const { mode, setMode } = useColorScheme();
const menu = ref(null);

const current = computed(() => OPTIONS.find((option) => option.mode === mode.value) ?? OPTIONS[0]);

const items = computed(() =>
    OPTIONS.map((option) => ({
        label: option.label,
        icon: option.icon,
        mode: option.mode,
        command: () => setMode(option.mode)
    }))
);

function toggle(event) {
    menu.value.toggle(event);
}
</script>

<template>
    <Button type="button" text rounded severity="secondary" :icon="current.icon" :aria-label="`Tema: ${current.label}`" aria-haspopup="true" aria-controls="color-scheme-menu" @click="toggle" />
    <Menu id="color-scheme-menu" ref="menu" :model="items" popup>
        <template #item="{ item, props }">
            <a v-bind="props.action" class="flex items-center gap-2" :aria-label="`Tema ${item.label}`" :aria-current="item.mode === mode ? 'true' : undefined">
                <span :class="item.icon" />
                <span :class="item.mode === mode ? 'font-semibold text-primary' : 'text-color'">{{ item.label }}</span>
                <i v-if="item.mode === mode" class="pi pi-check ml-auto text-primary" />
            </a>
        </template>
    </Menu>
</template>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm run test -- src/components/ui/ColorSchemeSwitcher.test.js`
Expected: PASS, 1 test.

- [ ] **Step 5: Slim `FloatingConfigurator.vue`**

Overwrite `frontend/src/components/FloatingConfigurator.vue`. The old file read `localStorage` without try/catch and imported AppConfigurator.

```vue
<script setup>
import ColorSchemeSwitcher from '@/components/ui/ColorSchemeSwitcher.vue';
</script>

<template>
    <div class="fixed top-6 right-6 z-50">
        <ColorSchemeSwitcher />
    </div>
</template>
```

- [ ] **Step 6: Update `AppTopbar.vue`**

Replace the script block (lines 1–15) with:

```vue
<script setup>
import { useLayout } from '@/layout/composables/layout';
import UserMenu from '@/components/dashboard/UserMenu.vue';
import PacientesPresentesMenu from '@/components/dashboard/PacientesPresentesMenu.vue';
import ColorSchemeSwitcher from '@/components/ui/ColorSchemeSwitcher.vue';
import { useRouter } from 'vue-router';

const { toggleMenu } = useLayout();
const router = useRouter();

// 👉 Ir a Agenda
function irAgenda() {
    router.push('/turnos');
}
</script>
```

On line 29, replace `<div class="text-xs text-gray-500">Centro Asistencial Universitario</div>` with `<div class="text-xs text-muted-color">Centro Asistencial Universitario</div>`.

Delete both the `<!-- 🎨 Tema -->` button block and the whole `<!-- 🎛 Configurador -->` `<div class="relative">…<AppConfigurator /></div>` block. Then replace `<!-- 👤 Nuevo menú de usuario (foto + perfil + logout) -->` and the `<UserMenu />` line after it with:

```vue
            <!-- Color scheme (Sistema / Claro / Oscuro) -->
            <ColorSchemeSwitcher />

            <!-- 👤 Nuevo menú de usuario (foto + perfil + logout) -->
            <UserMenu />
```

- [ ] **Step 7: Rewrite `layout.js` without preset or dark state**

Overwrite `frontend/src/layout/composables/layout.js`:

```js
import { computed, reactive } from 'vue';

const layoutConfig = reactive({
    menuMode: 'static'
});

const layoutState = reactive({
    staticMenuDesktopInactive: false,
    overlayMenuActive: false,
    profileSidebarVisible: false,
    configSidebarVisible: false,
    staticMenuMobileActive: false,
    menuHoverActive: false,
    activeMenuItem: null
});

export function useLayout() {
    const setActiveMenuItem = (item) => {
        layoutState.activeMenuItem = item.value || item;
    };

    const toggleMenu = () => {
        if (layoutConfig.menuMode === 'overlay') {
            layoutState.overlayMenuActive = !layoutState.overlayMenuActive;
        }

        if (window.innerWidth > 991) {
            layoutState.staticMenuDesktopInactive = !layoutState.staticMenuDesktopInactive;
        } else {
            layoutState.staticMenuMobileActive = !layoutState.staticMenuMobileActive;
        }
    };

    const isSidebarActive = computed(() => layoutState.overlayMenuActive || layoutState.staticMenuMobileActive);

    return {
        layoutConfig,
        layoutState,
        toggleMenu,
        isSidebarActive,
        setActiveMenuItem
    };
}
```

Remaining consumers are `AppLayout.vue` (`layoutConfig`, `layoutState`, `isSidebarActive`), `AppMenuItem.vue` (`layoutState`, `setActiveMenuItem`, `toggleMenu`) and `AppTopbar.vue` (`toggleMenu`). All of them stay satisfied.

- [ ] **Step 8: Delete the configurator and the dark patch sheet**

```bash
git rm frontend/src/layout/AppConfigurator.vue frontend/src/assets/theme-dark.css
```

- [ ] **Step 9: Verify no dangling references**

Run: `cd frontend && rg -n "AppConfigurator|theme-dark|toggleDarkMode|isDarkTheme|getPrimary|getSurface|localStorage\.(get|set)Item\('theme'" src index.html`
Expected: no output. The inline script in `index.html` reads `'theme'` inside a `try` block, not through `localStorage.getItem('theme'` with the same quoting, so it is not matched.

- [ ] **Step 10: Test, build and lint**

Run: `cd frontend && npm run test && npm run build && npm run lint`
Expected: all green (11 tests).

- [ ] **Step 11: Commit**

```bash
git add -A frontend/src/components frontend/src/layout frontend/src/assets
git commit -m "feat(frontend): replace runtime theme configurator with color scheme switcher"
```

---

### Task 4: App shell restyle (Sakai SCSS and footer)

**Files:**
- Modify: `frontend/src/assets/layout/variables/_light.scss` (whole file)
- Modify: `frontend/src/assets/layout/variables/_dark.scss` (whole file)
- Modify: `frontend/src/assets/layout/_topbar.scss:3-29` (`.layout-topbar` and `.layout-topbar-logo`)
- Modify: `frontend/src/assets/layout/_menu.scss:15-16` (`.layout-sidebar`) and `:86-92` (`&.active-route`, `&:hover`)
- Modify: `frontend/src/assets/layout/_core.scss:8`
- Modify: `frontend/src/assets/layout/_typography.scss:43,52`
- Modify: `frontend/src/assets/layout/_preloading.scss:4`
- Modify: `frontend/src/assets/layout/_utils.scss` (`.card`)
- Modify: `frontend/src/layout/AppFooter.vue` (style block)

**Interfaces:**
- Consumes: `--p-*` variables from `CauPreset` (Task 2), including `--p-app-background` and `--p-highlight-background`/`--p-highlight-color`.
- Produces:
  - `--cau-card-shadow` (a soft shadow in light, `none` in dark).
  - `.card` gains a border and that shadow.
  - `--surface-*` Sakai variables now resolve to `--p-*` through `variables/_common.scss`, because the hex overrides are gone.

- [ ] **Step 1: Replace the variable overrides**

Overwrite `frontend/src/assets/layout/variables/_light.scss`. The old file overrode the `_common.scss` `--p-*` mappings with hex.

```scss
:root {
    --surface-ground: var(--p-app-background);
    --code-background: var(--p-surface-100);
    --code-color: var(--p-text-color);
    --cau-card-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);
}
```

Overwrite `frontend/src/assets/layout/variables/_dark.scss`:

```scss
:root[class*='app-dark'] {
    --code-background: var(--p-surface-800);
    --cau-card-shadow: none;
}
```

- [ ] **Step 2: Topbar**

In `_topbar.scss`, inside `.layout-topbar`, add a line after `background-color: var(--surface-card);`:

```scss
    border-bottom: 1px solid var(--surface-border);
```

In `.layout-topbar-logo`, replace:

```scss
        color: var(--text-color);
        font-weight: 500;
```

with:

```scss
        color: var(--primary-color);
        font-family: 'Figtree', sans-serif;
        font-weight: 600;
```

- [ ] **Step 3: Sidebar**

In `_menu.scss` `.layout-sidebar`, replace:

```scss
    background-color: var(--surface-overlay);
    border-radius: var(--content-border-radius);
```

with:

```scss
    background-color: var(--surface-card);
    border: 1px solid var(--surface-border);
    border-radius: var(--content-border-radius);
```

In `.layout-menu … a`, replace the `border-radius: var(--content-border-radius);` line (line 70) with `border-radius: 8px;`. Then replace:

```scss
            &.active-route {
                font-weight: 700;
                color: var(--primary-color);
            }
```

with:

```scss
            &.active-route {
                font-weight: 600;
                background-color: var(--p-highlight-background);
                color: var(--p-highlight-color);
            }
```

Leave `&:hover { background-color: var(--surface-hover); }` as is (`--surface-hover` → `--p-content-hover-background`, the same value as `bg-emphasis`).

- [ ] **Step 4: Core, typography, preloader and card**

- `_core.scss` line 8: `font-family: 'Lato', sans-serif;` → `font-family: 'Inter', sans-serif;`
- `_typography.scss` `mark`: `background: #fff8e1;` → `background: var(--p-highlight-background);`, then add `color: var(--p-highlight-color);` on the next line.
- `_typography.scss` `blockquote`: `border-left: 4px solid #90a4ae;` → `border-left: 4px solid var(--p-content-border-color);`
- `_preloading.scss` line 4: `background: #edf1f5;` → `background: var(--p-app-background);`
- `_utils.scss` `.card`: after `border-radius: var(--content-border-radius);`, add:

```scss
    border: 1px solid var(--surface-border);
    box-shadow: var(--cau-card-shadow);
```

- [ ] **Step 5: Footer**

In `frontend/src/layout/AppFooter.vue`, replace the three `var(--footer-*)` declarations in `.app-footer`:

```css
    border-top: 1px solid var(--footer-border);
    background-color: var(--footer-bg);
    color: var(--footer-text);
```

with:

```css
    border-top: 1px solid var(--p-content-border-color);
    background-color: var(--p-content-background);
    color: var(--p-text-muted-color);
```

In `.brand` and in `.author`, replace `color: var(--footer-brand);` and `color: var(--footer-author);` with `color: var(--p-primary-color);`. Delete everything from the `/* ====== 🎨 Tema claro ====== */` comment through the end of the `.app-dark` rule, just before `</style>`. That removes both hex variable blocks.

- [ ] **Step 6: Verify no literal colors remain in the shell**

Run: `cd frontend && rg -n "#[0-9a-fA-F]{3,8}\b" src/assets/layout src/layout/AppFooter.vue`
Expected: no output. (`_mixins.scss` or other partials that print output are the only allowed exceptions. If any appear, replace them with the matching `--p-*` variable.)

- [ ] **Step 7: Build, lint and visual smoke check**

Run: `cd frontend && npm run build && npm run lint`
Expected: both green.
Then run `npm run dev`, open `http://localhost:5173`, and toggle Claro and Oscuro with the topbar switcher. Check that:
- In Oscuro the topbar, sidebar and cards are dark slate (`#131c2e`) on a `#0b1220` background.
- The active menu item shows a teal highlight.
- The footer has no light strip.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/assets/layout frontend/src/layout/AppFooter.vue
git commit -m "style(frontend): restyle app shell on preset tokens"
```

---

### Task 5: Token guard `check:tokens`

**Files:**
- Create: `frontend/scripts/check-tokens.mjs`
- Test: `frontend/scripts/check-tokens.test.mjs`
- Modify: `frontend/package.json` (scripts)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `scanSource(content: string): Array<{ line: number, rule: string, match: string }>`
  - `ALLOWLIST: Set<string>` (paths relative to `frontend/`, forward slashes)
  - `ROOTS: string[]`
  - The CLI `npm run check:tokens` exits with 1 when it finds violations and prints `path:line  rule  match`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/scripts/check-tokens.test.mjs`:

```js
import { describe, expect, it } from 'vitest';
import { ALLOWLIST, scanSource } from './check-tokens.mjs';

const rules = (content) => scanSource(content).map((v) => v.rule);

describe('scanSource', () => {
    it('flags bg-white and gray utilities', () => {
        expect(rules('<div class="bg-white p-4"></div>')).toEqual(['bg-white']);
        expect(rules('<p class="text-gray-500"></p>')).toEqual(['gray-utility']);
        expect(rules('<p class="hover:bg-gray-50/50 border-gray-200"></p>')).toEqual(['gray-utility', 'gray-utility']);
    });

    it('flags dark: color utilities, including stacked variants', () => {
        expect(rules('<div class="dark:bg-surface-900"></div>')).toEqual(['dark-color-utility']);
        expect(rules('<div class="dark:hover:text-red-400"></div>')).toEqual(['dark-color-utility']);
    });

    it('ignores non-color dark variants and semantic utilities', () => {
        expect(rules('<div class="dark:hidden bg-card text-color border-surface"></div>')).toEqual([]);
    });

    it('flags hex colors in templates and styles', () => {
        const source = '<template><div style="color: #fff"></div></template>\n<style>\n.a { background: #d1d5db; }\n</style>';
        const found = scanSource(source);
        expect(found.map((v) => v.rule)).toEqual(['hex', 'hex']);
        expect(found[1].line).toBe(3);
    });

    it('ignores hex inside script blocks, slot shorthands and HTML entities', () => {
        const source = ["<script setup>\nconst color = '#3B82F6';\n</script>", '<template>', '<Column><template #add>x</template></Column>', '<span>&#8212;</span>', '</template>'].join('\n');
        expect(scanSource(source)).toEqual([]);
    });

    it('reports the correct line after a script block', () => {
        const source = "<script setup>\nconst a = '#fff';\nconst b = 1;\n</script>\n<template>\n<div class=\"bg-white\"></div>\n</template>";
        expect(scanSource(source)).toEqual([{ line: 6, rule: 'bg-white', match: 'bg-white' }]);
    });

    it('allowlists the Spec 2 calendar views', () => {
        expect(ALLOWLIST.has('src/views/pages/historias/Turnos.vue')).toBe(true);
        expect(ALLOWLIST.has('src/views/pages/turnos/CalendarioGrupo.vue')).toBe(true);
        expect(ALLOWLIST.has('src/views/pages/turnos/ModuloRehabilitacion.vue')).toBe(true);
    });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- scripts/check-tokens.test.mjs`
Expected: FAIL, "Failed to load url ./check-tokens.mjs".

- [ ] **Step 3: Implement the guard**

Create `frontend/scripts/check-tokens.mjs`:

```js
#!/usr/bin/env node
// Fails when hardcoded colors appear in .vue files outside the allowlist.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const ROOTS = ['src/views', 'src/layout', 'src/components'];

// Spec 2 (appointment calendar) files, until Spec 2 lands.
export const ALLOWLIST = new Set(['src/views/pages/historias/Turnos.vue', 'src/views/pages/turnos/CalendarioGrupo.vue', 'src/views/pages/turnos/ModuloRehabilitacion.vue']);

const CLASS_RULES = [
    { rule: 'bg-white', pattern: /(?<![\w-])bg-white(?![\w-])/g },
    { rule: 'gray-utility', pattern: /(?<![\w-])(?:text|bg|border|divide|ring|placeholder)-gray-\d{2,3}(?:\/\d+)?/g },
    { rule: 'dark-color-utility', pattern: /(?<![\w-])dark:(?:[a-z-]+:)*!?(?:bg|text|border|divide|ring|outline|from|via|to|fill|stroke|placeholder|shadow|decoration)-[\w/.[\]#-]*/g }
];

// Excludes HTML entities (&#8212;) and slot shorthands (#add>, #add="…").
const HEX_PATTERN = /(?<![&\w])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w=>-])/g;

function lineOf(content, index) {
    return content.slice(0, index).split('\n').length;
}

// Script blocks hold data (e.g. default group colors), not styling; keep newlines so line numbers stay right.
function blankScripts(content) {
    return content.replace(/<script\b[\s\S]*?<\/script>/g, (block) => block.replace(/[^\n]/g, ' '));
}

function collect(content, pattern, rule) {
    const found = [];
    for (const match of content.matchAll(pattern)) {
        found.push({ line: lineOf(content, match.index), rule, match: match[0] });
    }
    return found;
}

export function scanSource(content) {
    const violations = [];
    for (const { rule, pattern } of CLASS_RULES) {
        violations.push(...collect(content, pattern, rule));
    }
    violations.push(...collect(blankScripts(content), HEX_PATTERN, 'hex'));
    return violations.sort((a, b) => a.line - b.line);
}

function listVueFiles(dir) {
    const files = [];
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) {
            files.push(...listVueFiles(full));
        } else if (entry.name.endsWith('.vue')) {
            files.push(full);
        }
    }
    return files;
}

function main() {
    const frontendRoot = fileURLToPath(new URL('..', import.meta.url));
    let total = 0;

    for (const root of ROOTS) {
        for (const file of listVueFiles(join(frontendRoot, root))) {
            const rel = relative(frontendRoot, file).split(sep).join('/');
            if (ALLOWLIST.has(rel)) {
                continue;
            }
            for (const v of scanSource(readFileSync(file, 'utf8'))) {
                console.log(`${rel}:${v.line}  ${v.rule}  ${v.match}`);
                total += 1;
            }
        }
    }

    if (total > 0) {
        console.error(`\ncheck:tokens found ${total} hardcoded color(s). Use semantic utilities (bg-card, text-color, border-surface, ...).`);
        process.exit(1);
    }
    console.log('check:tokens OK');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    main();
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test -- scripts/check-tokens.test.mjs`
Expected: PASS, 7 tests.

- [ ] **Step 5: Add the npm script**

In `frontend/package.json` `scripts`, add after `"test"`:

```json
        "check:tokens": "node scripts/check-tokens.mjs"
```

- [ ] **Step 6: Run the guard to record the baseline**

Run: `cd frontend && npm run check:tokens`
Expected: exit code 1. The listing covers the views that Tasks 8–11 migrate. It must NOT include:
- `src/layout/AppFooter.vue`, `src/layout/AppTopbar.vue` or `src/components/FloatingConfigurator.vue` (fixed in Tasks 3–4);
- any allowlisted calendar file.

This task commits the guard in its red state on purpose. `check:tokens` is not wired into `build`, so the build stays green.

- [ ] **Step 7: Lint and commit**

Run: `cd frontend && npm run lint`
Expected: exit code 0.

```bash
git add frontend/scripts/check-tokens.mjs frontend/scripts/check-tokens.test.mjs frontend/package.json
git commit -m "test(frontend): add check:tokens guard against hardcoded colors"
```

---

### Task 6: Token migration codemod

**Files:**
- Create: `frontend/scripts/migrate-tokens.mjs`
- Test: `frontend/scripts/migrate-tokens.test.mjs`

**Interfaces:**
- Consumes: the color names from Task 2 (`card`, `ground`, `subtle`, `line`, `status-*`).
- Produces:
  - `migrateSource(content: string): string`
  - `TOKEN_MAP: Record<string, string>`
  - The CLI `node scripts/migrate-tokens.mjs <file.vue> [...]` rewrites files in place and prints `migrated <path>` for each changed file.

**Rules, applied in order:**
1. Pairs `bg-surface-50` + `dark:bg-surface-950` (in either order) become `bg-ground`.
2. Every `dark:` color utility is removed, since the preset now drives dark mode.
3. Light tokens are mapped through `TOKEN_MAP`. Solid action colors (`bg-blue-600`, `bg-green-500`, `bg-red-500`, `text-white`, and so on) are deliberately left alone, because they read in both modes. Their redesign belongs to WU3.
4. Leading and trailing whitespace inside `class="…"` is trimmed.

- [ ] **Step 1: Write the failing tests**

Create `frontend/scripts/migrate-tokens.test.mjs`:

```js
import { describe, expect, it } from 'vitest';
import { migrateSource } from './migrate-tokens.mjs';

describe('migrateSource', () => {
    it('maps page backgrounds to ground', () => {
        expect(migrateSource('<div class="bg-surface-50 dark:bg-surface-950 min-h-screen">')).toBe('<div class="bg-ground min-h-screen">');
        expect(migrateSource('<div class="dark:bg-surface-950 bg-surface-50">')).toBe('<div class="bg-ground">');
    });

    it('maps card surfaces and drops dark variants', () => {
        expect(migrateSource('<div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 p-5">')).toBe('<div class="bg-card border border-surface p-5">');
        expect(migrateSource('<div class="bg-white dark:bg-slate-900 rounded-2xl">')).toBe('<div class="bg-card rounded-2xl">');
    });

    it('maps text colors', () => {
        expect(migrateSource('<h1 class="text-3xl text-gray-800 dark:text-white">')).toBe('<h1 class="text-3xl text-color">');
        expect(migrateSource('<p class="text-gray-500 dark:text-gray-400 mt-1">')).toBe('<p class="text-muted-color mt-1">');
    });

    it('maps feedback colors to status tokens', () => {
        expect(migrateSource('<div class="bg-red-50 border border-red-200 text-red-700 dark:bg-red-900/20">')).toBe('<div class="bg-status-sin-aviso-bg border border-status-sin-aviso-border text-status-sin-aviso-fg">');
        expect(migrateSource('<div class="bg-green-100 text-green-700">')).toBe('<div class="bg-status-presente-bg text-status-presente-fg">');
    });

    it('keeps solid action colors and non-color dark variants', () => {
        const input = '<button class="bg-blue-600 hover:bg-blue-700 text-white dark:hidden">';
        expect(migrateSource(input)).toBe(input);
    });

    it('does not touch longer tokens that share a prefix', () => {
        expect(migrateSource('<i class="bg-surface-500 text-gray-5000x">')).toBe('<i class="bg-surface-500 text-gray-5000x">');
    });

    it('migrates dynamic class strings in bindings and scripts', () => {
        expect(migrateSource(":class=\"active ? 'bg-primary text-primary-contrast' : 'bg-gray-200 dark:bg-gray-700 text-gray-600'\"")).toBe(":class=\"active ? 'bg-primary text-primary-contrast' : 'bg-emphasis text-muted-color'\"");
    });

    it('maps hover states to emphasis', () => {
        expect(migrateSource('<tr class="hover:bg-surface-100 dark:hover:bg-surface-800">')).toBe('<tr class="hover:bg-emphasis">');
    });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- scripts/migrate-tokens.test.mjs`
Expected: FAIL, "Failed to load url ./migrate-tokens.mjs".

- [ ] **Step 3: Implement the codemod**

Create `frontend/scripts/migrate-tokens.mjs`:

```js
#!/usr/bin/env node
// One-shot codemod: rewrites palette/dark: utilities in .vue files to preset-backed semantic utilities.
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const muted = 'text-muted-color';
const border = 'border-surface';

export const TOKEN_MAP = {
    // Surfaces
    'bg-white': 'bg-card',
    'bg-surface-0': 'bg-card',
    'bg-surface-50': 'bg-subtle',
    'bg-surface-100': 'bg-subtle',
    'bg-gray-50': 'bg-subtle',
    'bg-slate-50': 'bg-subtle',
    'bg-gray-200': 'bg-emphasis',
    'bg-gray-300/60': 'bg-line/60',
    'hover:bg-surface-50': 'hover:bg-emphasis',
    'hover:bg-surface-100': 'hover:bg-emphasis',
    'hover:bg-surface-200': 'hover:bg-emphasis',
    'hover:bg-gray-300': 'hover:bg-emphasis',
    'hover:bg-gray-50/50': 'hover:bg-emphasis',
    // Text
    'text-gray-900': 'text-color',
    'text-gray-800': 'text-color',
    'text-gray-700': 'text-color',
    'text-surface-900': 'text-color',
    'text-gray-600': muted,
    'text-gray-500': muted,
    'text-gray-400': muted,
    'text-gray-300': muted,
    'text-surface-400': muted,
    'text-surface-500': muted,
    'text-surface-600': muted,
    // Borders, dividers, rings
    'border-surface-200': border,
    'border-surface-300': border,
    'border-surface-400': border,
    'border-gray-100': border,
    'border-gray-200': border,
    'border-gray-300': border,
    'border-cyan-100': border,
    'border-blue-100': border,
    'border-blue-200': border,
    'border-blue-300': border,
    'border-primary-100': border,
    'border-indigo-200': border,
    'divide-gray-100': 'divide-line',
    'divide-surface-100': 'divide-line',
    'ring-surface-200': 'ring-line',
    'ring-white': 'ring-card',
    // Brand accents
    'bg-blue-50': 'bg-highlight',
    'bg-blue-100': 'bg-highlight',
    'bg-primary-50': 'bg-highlight',
    'bg-indigo-50': 'bg-highlight',
    'hover:bg-blue-50': 'hover:bg-highlight',
    'hover:bg-blue-100': 'hover:bg-highlight',
    'ring-blue-500': 'ring-primary',
    'border-blue-500': 'border-primary',
    'text-blue-500': 'text-primary',
    'text-blue-600': 'text-primary',
    'text-blue-700': 'text-primary',
    'text-primary-500': 'text-primary',
    'text-primary-600': 'text-primary',
    'text-primary-700': 'text-primary',
    'text-indigo-700': 'text-primary',
    'hover:text-blue-800': 'hover:text-primary-emphasis',
    'hover:text-primary-600': 'hover:text-primary-emphasis',
    'hover:text-primary-800': 'hover:text-primary-emphasis',
    'hover:border-primary-300': 'hover:border-primary',
    // Feedback -> status tokens
    'bg-green-50': 'bg-status-presente-bg',
    'bg-green-100': 'bg-status-presente-bg',
    'bg-emerald-50': 'bg-status-presente-bg',
    'bg-emerald-100': 'bg-status-presente-bg',
    'text-green-600': 'text-status-presente-fg',
    'text-green-700': 'text-status-presente-fg',
    'text-emerald-600': 'text-status-presente-fg',
    'text-emerald-700': 'text-status-presente-fg',
    'border-green-200': 'border-status-presente-border',
    'border-green-300': 'border-status-presente-border',
    'border-emerald-200': 'border-status-presente-border',
    'bg-amber-50': 'bg-status-con-aviso-bg',
    'text-amber-500': 'text-status-con-aviso-fg',
    'text-amber-700': 'text-status-con-aviso-fg',
    'text-amber-800': 'text-status-con-aviso-fg',
    'border-amber-200': 'border-status-con-aviso-border',
    'border-amber-300': 'border-status-con-aviso-border',
    'bg-red-50': 'bg-status-sin-aviso-bg',
    'bg-red-100': 'bg-status-sin-aviso-bg',
    'hover:bg-red-50': 'hover:bg-status-sin-aviso-bg',
    'text-red-500': 'text-status-sin-aviso-fg',
    'text-red-600': 'text-status-sin-aviso-fg',
    'text-red-700': 'text-status-sin-aviso-fg',
    'text-red-800': 'text-status-sin-aviso-fg',
    'border-red-200': 'border-status-sin-aviso-border',
    'border-red-300': 'border-status-sin-aviso-border'
};

const escape = (value) => value.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');

// A token is delimited by whitespace, quotes, backticks, braces or line edges.
const BEFORE = "(?<=^|[\\s\"'`{(])";
const AFTER = "(?=$|[\\s\"'`}):,])";

const GROUND_PAIRS = [new RegExp(`${BEFORE}bg-surface-50(\\s+)dark:bg-surface-950${AFTER}`, 'gm'), new RegExp(`${BEFORE}dark:bg-surface-950(\\s+)bg-surface-50${AFTER}`, 'gm')];

const DARK_COLOR = new RegExp(`${BEFORE}dark:(?:[a-z-]+:)*!?(?:bg|text|border|divide|ring|outline|from|via|to|fill|stroke|placeholder|shadow|decoration)-[^\\s"'\`]*[ \\t]*`, 'gm');

const MAP_PATTERNS = Object.entries(TOKEN_MAP).map(([from, to]) => [new RegExp(`${BEFORE}${escape(from)}${AFTER}`, 'gm'), to]);

export function migrateSource(content) {
    let out = content;
    for (const pair of GROUND_PAIRS) {
        out = out.replace(pair, 'bg-ground');
    }
    out = out.replace(DARK_COLOR, '');
    for (const [pattern, to] of MAP_PATTERNS) {
        out = out.replace(pattern, to);
    }
    // Tidy whitespace left by removed tokens.
    // Only static class attributes are trimmed; quoted strings in bindings are left alone
    // (a generic quote-trim would corrupt ternaries such as `' : '`).
    out = out.replace(/class="\s+/g, 'class="').replace(/(class="[^"]*?)\s+"/g, '$1"');
    return out;
}

function main(files) {
    for (const file of files) {
        const before = readFileSync(file, 'utf8');
        const after = migrateSource(before);
        if (after !== before) {
            writeFileSync(file, after);
            console.log(`migrated ${file}`);
        }
    }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    main(process.argv.slice(2));
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test -- scripts/migrate-tokens.test.mjs`
Expected: PASS, 8 tests. The mapping table is the contract; if a test fails on whitespace, adjust only the `class="…"` tidy lines and never add a generic quoted-string trim (it corrupts `' : '` in ternaries).

- [ ] **Step 5: Lint and commit**

Run: `cd frontend && npm run lint`
Expected: exit code 0.

```bash
git add frontend/scripts/migrate-tokens.mjs frontend/scripts/migrate-tokens.test.mjs
git commit -m "chore(frontend): add token migration codemod"
```

---

### Task 7: Shared UI components

**Files:**
- Create: `frontend/src/components/ui/PageHeader.vue`, `StatTile.vue`, `EmptyState.vue`, `StatusTag.vue`
- Test: `frontend/src/components/ui/SharedUi.test.js`

**Interfaces:**
- Consumes: `--cau-status-*` (Task 2) and the `card`/`highlight` utilities.
- Produces:
  - `<PageHeader title subtitle?>`, with slots `breadcrumb` and `actions`.
  - `<StatTile label value icon? hint?>`, where `value: String|Number`.
  - `<EmptyState title icon?='pi pi-inbox' message?>`, with slot `action`, rendered with `role="status"`.
  - `<StatusTag status label?='' size?='md'|'sm'>`. `status` takes the DB enum values `programado | presente | con_aviso | sin_aviso | firmada | pendiente`. The component renders `data-status` with a hyphenated token.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/ui/SharedUi.test.js`:

```js
import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import PageHeader from './PageHeader.vue';
import StatTile from './StatTile.vue';
import EmptyState from './EmptyState.vue';
import StatusTag from './StatusTag.vue';

describe('PageHeader', () => {
    it('renders title, subtitle and actions', () => {
        const wrapper = mount(PageHeader, {
            props: { title: 'Pacientes', subtitle: 'Listado general' },
            slots: { actions: '<button>Nuevo</button>' }
        });
        expect(wrapper.get('h1').text()).toBe('Pacientes');
        expect(wrapper.text()).toContain('Listado general');
        expect(wrapper.get('button').text()).toBe('Nuevo');
    });

    it('omits the subtitle paragraph when empty', () => {
        const wrapper = mount(PageHeader, { props: { title: 'Inicio' } });
        expect(wrapper.find('p').exists()).toBe(false);
    });
});

describe('StatTile', () => {
    it('renders label, value and hint', () => {
        const wrapper = mount(StatTile, { props: { label: 'Turnos hoy', value: 12, icon: 'pi pi-calendar', hint: '3 presentes' } });
        expect(wrapper.text()).toContain('Turnos hoy');
        expect(wrapper.text()).toContain('12');
        expect(wrapper.text()).toContain('3 presentes');
        expect(wrapper.find('.pi-calendar').exists()).toBe(true);
    });
});

describe('EmptyState', () => {
    it('announces itself and renders the action slot', () => {
        const wrapper = mount(EmptyState, {
            props: { title: 'Sin resultados', message: 'Probá otra búsqueda' },
            slots: { action: '<button>Limpiar</button>' }
        });
        expect(wrapper.attributes('role')).toBe('status');
        expect(wrapper.find('.pi-inbox').exists()).toBe(true);
        expect(wrapper.text()).toContain('Sin resultados');
        expect(wrapper.get('button').text()).toBe('Limpiar');
    });
});

describe('StatusTag', () => {
    it.each([
        ['programado', 'programado', 'Programado'],
        ['presente', 'presente', 'Presente'],
        ['con_aviso', 'con-aviso', 'Ausente con aviso'],
        ['sin_aviso', 'sin-aviso', 'Ausente sin aviso'],
        ['firmada', 'presente', 'Firmada'],
        ['pendiente', 'con-aviso', 'Firma pendiente']
    ])('maps %s to the %s token', (status, token, label) => {
        const wrapper = mount(StatusTag, { props: { status } });
        expect(wrapper.attributes('data-status')).toBe(token);
        expect(wrapper.text()).toBe(label);
    });

    it('falls back to programado styling and the raw value for unknown statuses', () => {
        const wrapper = mount(StatusTag, { props: { status: 'reprogramado' } });
        expect(wrapper.attributes('data-status')).toBe('programado');
        expect(wrapper.text()).toBe('reprogramado');
    });

    it('prefers an explicit label and supports the small size', () => {
        const wrapper = mount(StatusTag, { props: { status: 'presente', label: 'En sala', size: 'sm' } });
        expect(wrapper.text()).toBe('En sala');
        expect(wrapper.classes()).toContain('text-xs');
    });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- src/components/ui/SharedUi.test.js`
Expected: FAIL, "Failed to resolve import ./PageHeader.vue".

- [ ] **Step 3: Implement `PageHeader.vue`**

```vue
<script setup>
defineProps({
    title: { type: String, required: true },
    subtitle: { type: String, default: '' }
});
</script>

<template>
    <header class="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div class="flex flex-col gap-1">
            <slot name="breadcrumb" />
            <h1 class="m-0 text-3xl font-semibold text-color">{{ title }}</h1>
            <p v-if="subtitle" class="m-0 text-base text-muted-color">{{ subtitle }}</p>
        </div>
        <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
            <slot name="actions" />
        </div>
    </header>
</template>
```

- [ ] **Step 4: Implement `StatTile.vue`**

```vue
<script setup>
defineProps({
    label: { type: String, required: true },
    value: { type: [String, Number], required: true },
    icon: { type: String, default: '' },
    hint: { type: String, default: '' }
});
</script>

<template>
    <div class="card !mb-0 flex items-start justify-between gap-4 !p-5">
        <div class="flex flex-col gap-1">
            <span class="text-sm font-medium text-muted-color">{{ label }}</span>
            <span class="text-3xl font-semibold text-color">{{ value }}</span>
            <span v-if="hint" class="text-sm text-muted-color">{{ hint }}</span>
        </div>
        <span v-if="icon" class="flex h-10 w-10 items-center justify-center rounded-border bg-highlight">
            <i :class="icon" class="text-lg" aria-hidden="true" />
        </span>
    </div>
</template>
```

- [ ] **Step 5: Implement `EmptyState.vue`**

```vue
<script setup>
defineProps({
    icon: { type: String, default: 'pi pi-inbox' },
    title: { type: String, required: true },
    message: { type: String, default: '' }
});
</script>

<template>
    <div role="status" class="flex flex-col items-center justify-center gap-2 px-4 py-12 text-center">
        <i :class="icon" class="text-4xl text-muted-color" aria-hidden="true" />
        <p class="m-0 text-lg font-semibold text-color">{{ title }}</p>
        <p v-if="message" class="m-0 max-w-md text-sm text-muted-color">{{ message }}</p>
        <div v-if="$slots.action" class="mt-2">
            <slot name="action" />
        </div>
    </div>
</template>
```

- [ ] **Step 6: Implement `StatusTag.vue`**

```vue
<script setup>
import { computed } from 'vue';

// DB enums: turnos.estado_asistencia and evoluciones.estado_firma.
const STATUS_MAP = {
    programado: { token: 'programado', label: 'Programado' },
    presente: { token: 'presente', label: 'Presente' },
    con_aviso: { token: 'con-aviso', label: 'Ausente con aviso' },
    sin_aviso: { token: 'sin-aviso', label: 'Ausente sin aviso' },
    firmada: { token: 'presente', label: 'Firmada' },
    pendiente: { token: 'con-aviso', label: 'Firma pendiente' }
};

const props = defineProps({
    status: { type: String, required: true },
    label: { type: String, default: '' },
    size: { type: String, default: 'md', validator: (value) => ['sm', 'md'].includes(value) }
});

const entry = computed(() => STATUS_MAP[props.status] ?? { token: 'programado', label: props.status });

const style = computed(() => {
    const token = entry.value.token;
    return {
        color: `var(--cau-status-${token}-fg)`,
        backgroundColor: `var(--cau-status-${token}-bg)`,
        borderColor: `var(--cau-status-${token}-border)`
    };
});

const sizeClass = computed(() => (props.size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'));
</script>

<template>
    <span class="inline-flex items-center gap-1 whitespace-nowrap rounded-full border font-medium" :class="sizeClass" :style="style" :data-status="entry.token">{{ label || entry.label }}</span>
</template>
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd frontend && npm run test -- src/components/ui/SharedUi.test.js`
Expected: PASS, 12 tests.

- [ ] **Step 8: Guard, lint, build and commit**

Run: `cd frontend && npm run check:tokens | rg "components/ui" ; npm run lint && npm run build`
Expected:
- The `rg` step prints nothing: no `components/ui` file is listed.
- Lint and build are green.

```bash
git add frontend/src/components/ui
git commit -m "feat(frontend): add PageHeader, StatTile, EmptyState and StatusTag"
```

---

### Task 8: Mechanical pass for auth and usuarios views

**Files:**
- Modify: `frontend/src/views/pages/auth/Login.vue`, `RecoverPassword.vue`, `ResetPassword.vue`, `Logout.vue`
- Modify: `frontend/src/views/pages/usuarios/Usuarios.vue`, `UsuariosInactivos.vue`, `MiPerfil.vue`, `EditarUsuario.vue`, `CrearUsuario.vue`, `CambiarPassword.vue`

**Interfaces:**
- Consumes: `node scripts/migrate-tokens.mjs` (Task 6) and `npm run check:tokens` (Task 5).
- Produces: none of these files appears in the `check:tokens` output.

- [ ] **Step 1: Run the codemod**

```bash
cd frontend && node scripts/migrate-tokens.mjs src/views/pages/auth/Login.vue src/views/pages/auth/RecoverPassword.vue src/views/pages/auth/ResetPassword.vue src/views/pages/auth/Logout.vue src/views/pages/usuarios/Usuarios.vue src/views/pages/usuarios/UsuariosInactivos.vue src/views/pages/usuarios/MiPerfil.vue src/views/pages/usuarios/EditarUsuario.vue src/views/pages/usuarios/CrearUsuario.vue src/views/pages/usuarios/CambiarPassword.vue
```

Expected: one `migrated …` line per file.

- [ ] **Step 2: Check the guard for these files**

Run: `cd frontend && npm run check:tokens | rg "pages/(auth|usuarios)/"`
Expected: no output. If a line remains, it is a token missing from `TOKEN_MAP`. Fix it by hand with this table:

| Leftover | Replace with |
|---|---|
| light page background | `bg-ground` |
| card or panel background | `bg-card` |
| inset or input background | `bg-subtle` |
| primary text | `text-color` |
| secondary text | `text-muted-color` |
| border color | `border-surface` |
| divider | `divide-line` |
| any `dark:` color class | delete it |

- [ ] **Step 3: Review the diff for codemod edge cases**

Run: `git diff --stat -- frontend/src/views/pages/auth frontend/src/views/pages/usuarios && git diff -- frontend/src/views/pages/auth frontend/src/views/pages/usuarios | rg -n "''|\"\s|\s\"$"`
Expected: no empty-string class keys (`'': cond`) and no class attributes with dangling spaces. Fix any hit by deleting the empty entry.

Spot-check `CambiarPassword.vue`:
- Inputs should now read `border border-surface … bg-subtle …` (or `bg-card`).
- The solid blue submit button (`bg-blue-600 hover:bg-blue-700 text-white`) stays as is. It is deferred to WU3.

- [ ] **Step 4: Build and lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: both green.

- [ ] **Step 5: Visual spot check**

With `npm run dev` and the API running, check `/auth/login`, `/usuarios` and `/usuarios/cambiar-password` in both Claro and Oscuro:
- no white panels in Oscuro;
- text is readable;
- error boxes use the red status tint.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/pages/auth frontend/src/views/pages/usuarios
git commit -m "refactor(frontend): migrate auth and user views to semantic tokens"
```

---

### Task 9: Mechanical pass for grupos, comunicados, agenda, availability and recetas

**Files:**
- Modify: `frontend/src/views/pages/grupos/CrearGrupo.vue`, `EditarGrupo.vue`, `GruposProfesionales.vue`, `PosteosGrupo.vue`
- Modify: `frontend/src/views/pages/comunicados/Comunicados.vue`
- Modify: `frontend/src/views/pages/Agenda/AgendaProfesional.vue`
- Modify: `frontend/src/views/pages/disponibilidades/DisponibilidadProfesional.vue`
- Modify: `frontend/src/views/pages/recetas/RecetasElectronicas.vue`

**Interfaces:**
- Consumes: the codemod (Task 6) and the guard (Task 5).
- Produces: none of these files appears in the `check:tokens` output.

- [ ] **Step 1: Run the codemod**

```bash
cd frontend && node scripts/migrate-tokens.mjs src/views/pages/grupos/CrearGrupo.vue src/views/pages/grupos/EditarGrupo.vue src/views/pages/grupos/GruposProfesionales.vue src/views/pages/grupos/PosteosGrupo.vue src/views/pages/comunicados/Comunicados.vue src/views/pages/Agenda/AgendaProfesional.vue src/views/pages/disponibilidades/DisponibilidadProfesional.vue src/views/pages/recetas/RecetasElectronicas.vue
```

Expected: one `migrated …` line per file.

- [ ] **Step 2: Check the guard for these files**

Run: `cd frontend && npm run check:tokens | rg "pages/(grupos|comunicados|Agenda|disponibilidades|recetas)/"`
Expected: no output. The `'#3B82F6'` in `CrearGrupo.vue` and the `'#00936B'` in `EditarGrupo.vue` live in `<script>` as default group color data. The guard skips them on purpose, so leave them.

If lines remain, fix them with this table:

| Leftover | Replace with |
|---|---|
| Dashed empty boxes: `border-dashed` plus a palette border | `bg-card border border-dashed border-surface` |
| Color `<input type="color">` border | `border-surface` |
| Info panels on `bg-primary-50`/`bg-blue-50` | `bg-highlight` (already done by the codemod). Keep inner `text-color` / `text-muted-color`. |
| Any other leftover | Use the table from Task 8 Step 2: `bg-ground`, `bg-card`, `bg-subtle`, `text-color`, `text-muted-color`, `border-surface`, `divide-line`, and delete `dark:` color classes. |

- [ ] **Step 3: Review the diff for codemod edge cases**

Run: `git diff -- frontend/src/views/pages/grupos frontend/src/views/pages/comunicados frontend/src/views/pages/Agenda frontend/src/views/pages/disponibilidades frontend/src/views/pages/recetas | rg -n "''\s*:|class=\" | \""`
Expected: no output.

In `DisponibilidadProfesional.vue`, confirm the selected/unselected day ternary now reads `'bg-primary text-primary-contrast' : 'bg-emphasis text-muted-color'`. If the codemod left it as `bg-primary text-white`, change it by hand to `bg-primary text-primary-contrast`, because white on the dark-mode teal fails contrast.

- [ ] **Step 4: Build and lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: both green.

- [ ] **Step 5: Visual spot check**

In Claro and Oscuro, check:
- `/grupos` (list, create, edit);
- `/comunicados`;
- `/agenda-profesional` (or the route that renders `AgendaProfesional.vue`);
- `/disponibilidades`;
- `/recetas`.

Look for no white cards or rows in Oscuro, and a visible selected state.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/pages/grupos frontend/src/views/pages/comunicados frontend/src/views/pages/Agenda frontend/src/views/pages/disponibilidades frontend/src/views/pages/recetas
git commit -m "refactor(frontend): migrate groups, agenda and availability views to semantic tokens"
```

---

### Task 10: Mechanical pass for historias and evolucion views

**Files:**
- Modify: `frontend/src/views/pages/historias/HistoriaPaciente.vue`
- Modify: `frontend/src/views/pages/historias/Pacientes.vue`
- Modify: `frontend/src/views/pages/historias/BuscarHistorias.vue`
- Modify: `frontend/src/views/pages/historias/NuevoTurno.vue`
- Modify: `frontend/src/views/pages/historias/BlockchainVerificar.vue` (delete the scoped `<style>` block at lines 299–316)
- Modify: `frontend/src/views/pages/evolucion/EvolucionDetalle.vue`
- Do NOT touch: `frontend/src/views/pages/historias/Turnos.vue` (Spec 2, allowlisted)

**Interfaces:**
- Consumes: the codemod (Task 6) and the guard (Task 5).
- Produces:
  - None of these files appears in the `check:tokens` output.
  - `BlockchainVerificar.vue` renders the real PrimeVue `Tag` with no overrides.

- [ ] **Step 1: Delete the Tag override in `BlockchainVerificar.vue`**

Remove the entire block that starts with `<style scoped>` and the comment `/* fallback rápido si no tenés PrimeVue Tag/Button:` and ends with `</style>` at the end of the file. The component already imports PrimeVue `Tag`, whose `severity` colors now come from the preset.

- [ ] **Step 2: Run the codemod**

```bash
cd frontend && node scripts/migrate-tokens.mjs src/views/pages/historias/HistoriaPaciente.vue src/views/pages/historias/Pacientes.vue src/views/pages/historias/BuscarHistorias.vue src/views/pages/historias/NuevoTurno.vue src/views/pages/historias/BlockchainVerificar.vue src/views/pages/evolucion/EvolucionDetalle.vue
```

Expected: a `migrated …` line for each file that had palette classes.

- [ ] **Step 3: Check the guard for these files**

Run: `cd frontend && npm run check:tokens | rg "pages/(historias|evolucion)/" | rg -v "historias/Turnos.vue"`
Expected: no output.

For `HistoriaPaciente.vue`, confirm with `rg -n "border-surface p-4 rounded-2xl bg-card|bg-card text-color|border-primary" src/views/pages/historias/HistoriaPaciente.vue` that:
- evolution cards read `border border-surface p-4 rounded-2xl bg-card` (the old `border dark:border-slate-700 … bg-white dark:bg-slate-900`);
- textareas keep a `bg-card` or `bg-subtle` background with `text-color`.

If a textarea still has no background class, add `bg-card text-color`.

The solid colored action buttons in `HistoriaPaciente.vue` (`bg-green-600`, `bg-blue-600`, and so on) stay as is. They are part of the WU3 screen polish.

- [ ] **Step 4: Review the diff for codemod edge cases**

Run: `git diff -- frontend/src/views/pages/historias frontend/src/views/pages/evolucion | rg -n "''\s*:|class=\" | \""`
Expected: no output.

- [ ] **Step 5: Build and lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: both green.

- [ ] **Step 6: Visual spot check**

In Claro and Oscuro, check:
- `/pacientes`
- `/historias/buscar`
- a patient's `HistoriaPaciente` with at least one evolution
- `/blockchain/verificar` (Tag colors come from PrimeVue)
- `EvolucionDetalle`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/pages/historias frontend/src/views/pages/evolucion
git commit -m "refactor(frontend): migrate clinical record views to semantic tokens"
```

---

### Task 11: Mechanical pass for Dashboard and dashboard components

**Files:**
- Modify: `frontend/src/views/Dashboard.vue`: script lines 90–108 (localStorage), the template, and the style block at lines 370–385
- Modify: `frontend/src/components/dashboard/PacientesPresentesMenu.vue`, `ProximoTurnoWidget.vue`, `StatsMedicoWidget.vue`, `UserMenu.vue`
- Modify: `frontend/src/components/UserBadge.vue`
- Note: `ProximoTurnoWidget.vue`, `StatsMedicoWidget.vue`, `RevenueStreamWidget.vue` and `UserBadge.vue` are imported nowhere today. They are still migrated because the guard scans `src/components`. The `'#3B82F6'` in `RevenueStreamWidget.vue` is chart data inside `<script>`, and the guard skips it.

**Interfaces:**
- Consumes: the codemod (Task 6), the guard (Task 5), and the `card`/`line` colors (Task 2).
- Produces:
  - None of these files appears in the `check:tokens` output.
  - Dashboard localStorage access is safe when storage throws.

- [ ] **Step 1: Wrap Dashboard localStorage in try/catch**

In `frontend/src/views/Dashboard.vue`, replace:

```js
        const hoyStr = new Date().toISOString().slice(0, 10);
        const ultimaAlertaVista = localStorage.getItem('ultima_alerta_turnos_vista');
```

with:

```js
        const hoyStr = new Date().toISOString().slice(0, 10);
        let ultimaAlertaVista = null;
        try {
            ultimaAlertaVista = localStorage.getItem('ultima_alerta_turnos_vista');
        } catch (error) {
            // Storage unavailable: show the alert again.
        }
```

and replace:

```js
    const hoyStr = new Date().toISOString().slice(0, 10);
    localStorage.setItem('ultima_alerta_turnos_vista', hoyStr);
    showTodayAlert.value = false;
```

with:

```js
    const hoyStr = new Date().toISOString().slice(0, 10);
    try {
        localStorage.setItem('ultima_alerta_turnos_vista', hoyStr);
    } catch (error) {
        // Storage unavailable: the alert will reappear on next visit.
    }
    showTodayAlert.value = false;
```

- [ ] **Step 2: Replace the Dashboard scrollbar hex**

In the Dashboard `<style scoped>`, replace:

```css
.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: #d1d5db;
    border-radius: 10px;
}
.dark .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: #4b5563;
}
```

with:

```css
.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: var(--p-content-border-color);
    border-radius: 10px;
}
```

- [ ] **Step 3: Run the codemod**

```bash
cd frontend && node scripts/migrate-tokens.mjs src/views/Dashboard.vue src/components/dashboard/PacientesPresentesMenu.vue src/components/dashboard/ProximoTurnoWidget.vue src/components/dashboard/StatsMedicoWidget.vue src/components/dashboard/UserMenu.vue src/components/dashboard/RevenueStreamWidget.vue src/components/UserBadge.vue
```

Expected: a `migrated …` line for each changed file.

- [ ] **Step 4: Check the guard (entire tree)**

Run: `cd frontend && npm run check:tokens`
Expected: `check:tokens OK` and exit code 0. This is the last migration task, so the whole tree must be clean now.

If lines remain, fix them with this table:

| Leftover | Replace with |
|---|---|
| `UserBadge.vue` director badge | `bg-highlight border border-surface` |
| `UserBadge.vue` other role badges | `bg-subtle border border-surface text-color` |
| `UserBadge.vue` skeleton | `bg-line/60` |
| `UserMenu.vue` avatar ring | `ring-1 ring-line` (avatar border: `ring-card`) |
| `UserMenu.vue` menu row hover | `hover:bg-emphasis` |
| `PacientesPresentesMenu.vue` list | `divide-line`; emerald "presente" chips → `bg-status-presente-bg text-status-presente-fg border-status-presente-border`; `text-surface-400` icon → `text-muted-color` |

- [ ] **Step 5: Review, build and lint**

Run: `git diff -- frontend/src/views/Dashboard.vue frontend/src/components | rg -n "''\s*:|class=\" | \""; cd frontend && npm run build && npm run lint`
Expected:
- The `rg` step prints nothing.
- Build and lint are green.

- [ ] **Step 6: Visual spot check**

In Claro and Oscuro, check the Dashboard (`/`), the topbar "pacientes presentes" popover and the user menu.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/Dashboard.vue frontend/src/components
git commit -m "refactor(frontend): migrate dashboard to semantic tokens and guard storage access"
```

---

### Task 12: Final verification

**Files:**
- No source changes expected. Fix regressions in the file that caused them.

**Interfaces:**
- Consumes: everything above.
- Produces: a green WU1+WU2 branch ready for review.

- [ ] **Step 1: Full automated suite**

Run: `cd frontend && npm run test && npm run build && npm run lint && npm run check:tokens`
Expected:
- Tests: all pass. There are 38 tests: 7 color scheme, 3 preset, 1 switcher, 7 guard, 8 codemod, 12 shared UI.
- Build: succeeds.
- Lint: exit code 0.
- Guard: `check:tokens OK`.

- [ ] **Step 2: Constraint sweep**

Run: `cd frontend && rg -n "localStorage\." src | rg -v "try|//"; rg -n "classList\.(add|remove|toggle)\('app-dark'" src`
Expected:
- First command: every hit is inside a `try { … }` block. Check each hit by reading the surrounding lines; the only files should be `src/theme/useColorScheme.js` and `src/views/Dashboard.vue`.
- Second command: the only hit is in `src/theme/useColorScheme.js`.

Run: `git log --format=%B main..HEAD | rg -i "co-authored-by|generated with"`
Expected: no output.

- [ ] **Step 3: Visual check in a browser (Playwright MCP or manual)**

Start the stack with `docker compose --env-file .env up -d --build`, or run `npm run dev` with the API on :5000. Then, for each screen, take a screenshot in Claro and in Oscuro (switcher in the topbar, or on Login via the floating switcher):

1. Login (`/auth/login`), an inherited screen that also shows the floating switcher
2. Dashboard (`/`)
3. Pacientes (`/pacientes`)
4. Usuarios (`/usuarios`)
5. Grupos profesionales (`/grupos`)
6. HistoriaPaciente for one patient

Pass criteria in Oscuro:
- no white or light panels, rows or inputs;
- body text is `#e2e8f0` on `#131c2e` cards over a `#0b1220` background;
- primary buttons are teal `#2dd4bf` with dark text;
- the footer is dark.

Pass criteria in Claro:
- cards are white with a soft shadow on `#f8fafc`;
- primary is `#0f766e`.

- [ ] **Step 4: Behavior checks**

1. Select "Sistema". Toggle the OS or browser dark preference (Playwright: `browser_emulate_media` with `colorScheme: 'dark'`/`'light'`). The app follows live, without a reload.
2. Select "Oscuro" and hard-reload. There is no light flash before paint, and the switcher shows the moon icon.
3. In DevTools, run `localStorage.clear(); localStorage.setItem('theme','dark')`, then reload. The app opens dark. Afterwards `localStorage.getItem('cau-color-scheme') === 'dark'` and `localStorage.getItem('theme') === null`.
4. In a private window with site data blocked, the app still renders following the OS preference.

- [ ] **Step 5: Record the result**

If everything passes, no commit is needed. If a fix was required, commit it with a scoped conventional message, for example `fix(frontend): restore card background in dark mode for <View>`.

---

## Self-Review

**Spec coverage:**

| Spec section | Where it is covered |
|---|---|
| §3.1 preset, primitives, schemes, shape, focus ring | Task 2 |
| §3.1 status tokens | Task 2 (`status.css`) |
| §3.1 wiring (`main.js`, Tailwind cleanup, fonts) | Task 2 |
| §3.1 removals | Task 3 (AppConfigurator, theme-dark.css, `layout.js` state) |
| §3.2 composable, legacy migration, try/catch | Task 1 |
| §3.2 anti-flash script, `init()` | Task 2 |
| §3.2 switcher in topbar and FloatingConfigurator | Task 3 |
| §3.3 shell (topbar, sidebar, main area, cards, footer, Sakai SCSS) | Task 4 |
| §3.4 PageHeader, StatTile, EmptyState, StatusTag | Task 7 |
| §3.4 ColorSchemeSwitcher | Task 3 |
| §3.6 mechanical pass, including zero-coverage views | Tasks 8–11. Zero-coverage views covered: BlockchainVerificar and BuscarHistorias (T10), Logout (T8), AppTopbar (T3), ProximoTurnoWidget (T11). |
| §4.1 Vitest | Task 1 |
| §4.2 guard | Task 5 |
| §4.3 build and lint | Every task, plus Task 12 |
| §4.4 visual check | Task 12 |
| §3.5 screen polish | Out of scope (WU3) |

**Deviations from the spec:**
1. `bg-card` / `bg-ground` / `bg-subtle` / `line` are used instead of `bg-surface-0` / `bg-surface-50`. PrimeVue keeps `surface-0` white in dark mode, so the spec's utilities would render light panels in Oscuro.
2. `cau.700` is `#0f766e` (the spec says it is "anchored on 600"). The light primary uses `{cau.700}`, as §3.1 states.
3. The guard skips hex inside `<script>` blocks, because those values are data such as default group colors or chart colors.
4. Status `-border` values are this plan's choice; the spec named the variable but gave no value.
5. `_main.scss` and `_footer.scss` needed no change: `_main.scss` has no color literals, and `_footer.scss` already uses `var(--surface-border)`.
6. Solid action buttons (blue, green and red CTAs) are left as is and deferred to WU3.
7. The mechanical pass uses a tested codemod that stays in `scripts/` for reuse by Spec 2.

**Placeholder scan:** there are no TBD or TODO items. Every code step shows full code, and every command shows its expected output.

**Type consistency:**
- `useColorScheme()` returns `{ mode, isDark, setMode, init, apply }` in Tasks 1, 2 and 3.
- `STORAGE_KEY` / `LEGACY_KEY` are the same in the composable, its tests and the inline script.
- Color names `card` / `ground` / `subtle` / `line` / `status-<s>-{fg,bg,border}` are identical in Tasks 2, 6, 7 and 8–11.
- `scanSource` / `ALLOWLIST` are the same in Task 5 and its tests.
- `migrateSource` / `TOKEN_MAP` are the same in Task 6 and its tests.
