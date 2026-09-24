# Agenda Turnos Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the three FullCalendar agendas (Turnos, CalendarioGrupo, ModuloRehabilitacion) readable in light and dark mode. Status colors come from tokens and render as a tinted card with a left bar. Concurrency is capped at 2 side-by-side events per slot, with a themed "+N" popover for the rest. The duplicated calendar config and hex color logic are removed.

**Architecture:**
- Pure helpers (`src/components/agenda/agendaEventStyle.js`) map an event to a status key, a Spanish label, FullCalendar class names and an optional group bar color.
- A small card component (`src/components/agenda/AgendaEvent.vue`) is rendered by FullCalendar's `#eventContent` slot.
- A composable (`src/composables/useAgendaCalendar.js`) returns the shared reactive FullCalendar options:
  - plugins, `es` locale, toolbar and time range;
  - `eventMaxStack: 2` and `dayMaxEventRows`;
  - `eventClassNames`;
  - a tippy tooltip that is built with HTML escaping.
- Views pass only their own overrides.
- `src/assets/calendar-theme.css` replaces `calendar-medical.css`. It themes the `--fc-*` variables, the `.evt-*` status classes, the popover, the hatch layers and the tippy theme, using only semantic tokens.

**Tech Stack:** Vue 3.4 (`<script setup>`), FullCalendar 5.11.5 (`@fullcalendar/vue3`, core, common, daygrid, timegrid, interaction), tippy.js 6.3.7, PrimeVue 4.3 with CauPreset (`--p-*` tokens), `src/theme/status.css` (`--cau-status-*` tokens), Tailwind 3.4 with `tailwindcss-primeui`, Vitest 3 with jsdom and `@vue/test-utils` 2.

**Spec:** `docs/superpowers/specs/2026-09-24-agenda-turnos-design.md` (binding).

## FullCalendar 5.11 verification (done before writing this plan)

The installed version is 5.11.5 for every `@fullcalendar/*` package (`frontend/node_modules/@fullcalendar/core/package.json`).

1. **The `#eventContent` scoped slot is supported.**
   - Evidence: `frontend/node_modules/@fullcalendar/vue3/dist/FullCalendar.js`. In `mounted()`, `this.slotOptions = mapHash(this.$slots, wrapVDomGenerator)`, and `buildOptions()` spreads `slotOptions` before the passed options. A slot named `eventContent` therefore becomes the `eventContent` option.
   - Consequences:
     - Slots are captured once, at mount.
     - An explicit `eventContent` option would override the slot, so the composable must NOT define `eventContent`.
2. **The slot renders in a detached Vue app.**
   - Evidence: `frontend/node_modules/@fullcalendar/vue3/dist/custom-content-type.js`. `initApp()` calls `createApp(...)` ("TODO: do something with appContext") and mounts into an artificial inner `<span>`.
   - Consequences for `AgendaEvent.vue`:
     - It must use only plain elements and global CSS classes, such as `pi pi-users`. It cannot use PrimeVue components, directives or plugins.
     - The CSS must make that wrapper `<span>` a full-size block.
3. **`eventMaxStack` is a valid 5.11 option.**
   - It is refined as `eventMaxStack: Number` in `frontend/node_modules/@fullcalendar/common/main.js:1592`.
   - timeGrid uses it in `computeFgSegPlacements` (`frontend/node_modules/@fullcalendar/timegrid/main.js:790-794`), which produces hidden groups and the `.fc-timegrid-more-link` "+N" link.
   - `dayMaxEventRows` is used by dayGrid in `frontend/node_modules/@fullcalendar/daygrid/main.js:276-288`.
   - `moreLinkClick` defaults to `'popover'` (`common/main.js:9567-9593`).
   - The popover (`.fc-popover.fc-more-popover`) is portaled into the closest `.fc-view-harness` (`common/main.js:9632`), so `.fc`-scoped CSS applies to it.
   - Popover events render through the same `options.eventContent` hook (`common/main.js:9280`).
4. **Background events also go through `eventContent`, `eventClassNames` and `eventDidMount`.**
   - Evidence: `BgEvent` renders through `EventRoot` (`common/main.js:9399`, `EventRoot` at `9246`/`9280`).
   - Consequences: the helpers and `AgendaEvent` must handle background events (`display: 'background'`, `tipo` `indisponible_bg`/`ausencia_bg`), and the tooltip must skip them.
5. **Test-environment gotcha.** Importing `@fullcalendar/daygrid` in Vitest before the FullCalendar core throws "Please import the top-level fullcalendar lib before attempting to import a plugin." (`@fullcalendar/common/vdom.cjs.js:7`). Importing `'@fullcalendar/core/vdom'` first fixes it. This was verified with a throwaway Vitest probe. The composable does that import first.

## Global Constraints

- **Branch:** work on `feat/agenda-turnos`. Do not switch branches.
- **Frontend only:** no backend, API, `db/init.sql` or response-shape changes. `/api/*` stays as is.
- **Semantic tokens only:**
  - New and modified styling uses `--p-*` / `--cau-status-*` CSS variables or token Tailwind classes (`bg-card`, `border-line`, `bg-subtle`, `text-muted-color`, `bg-status-*-bg`, `text-status-*-fg`, `bg-highlight`, `text-primary`).
  - No hex values in `calendar-theme.css` or in `src/components/agenda/*.vue`.
  - `npm run check:tokens` must report 0 violations (`check:tokens OK`).
  - The three views stay on the allowlist because their out-of-scope modals still hold legacy colors.
- **Language:** code, identifiers and comments are in English. UI copy is in Spanish ("Programado", "Presente", "Falta con aviso", "Falta sin aviso", "Ausencia", "más").
- **Dates:** event times always come from the offset-aware `start` / `end` fields of turnos, never `fecha_inicio`. Ausencias keep their own `fecha_inicio` / `fecha_fin` API fields, which are unchanged.
- **Commits:** conventional commits (`feat(agenda): …`, `style(agenda): …`, `refactor(turnos): …`, `chore(agenda): …`). NO `Co-Authored-By` or AI attribution lines. Stage explicit paths only; never `git add -A`, because `src/components/dashboard/PacientesPresentesMenu.vue` has unrelated local changes.
- **Shell:** use `rg` / `fd` (not grep/find). `fd` is not installed in Git Bash on this machine, so the plan uses `rg --files` where a file listing is needed.
- **TDD:** `agendaEventStyle.js`, `AgendaEvent.vue` and `useAgendaCalendar.js` are written test-first: RED, then GREEN, then commit.
- **Commands:** run every command from `frontend/`:
  - `npm run test`
  - `npm run build`
  - `npm run lint`
  - `npm run check:tokens`
- **Out of scope:**
  - modal changes beyond the `creadoPorNombre` / `creadoEn` key normalization;
  - `views/pages/Agenda/AgendaProfesional.vue`;
  - FullCalendar upgrades.

## Decisions made while planning

- **Grupal detection:** grupal means `tipo` is `'grupal'` (Turnos) or `'turno_grupal'` (CalendarioGrupo).
- **Group bar color:**
  - Only ModuloRehabilitacion sets `extendedProps.grupoColor` (`t.color || REHAB_COLOR_DEFAULT`).
  - CalendarioGrupo individual events drop their `t.color || grupo.color` fill and follow status colors, per spec §2.3.
  - `barColor()` accepts only `#rgb` / `#rrggbb` values and returns `null` otherwise.
- **New keys:**
  - `extendedProps.grupoNombre` (camelCase, added in all three views) feeds line 2 of grupal cards and the tooltip.
  - `extendedProps.creadoPorNombre` / `creadoEn` are used everywhere.
- **Absences:**
  - The foreground absence (`tipo: 'ausencia'`) gets an `evt-ausencia` card: line 1 is the time and the `tipoEvento`, line 2 is the professional.
  - CalendarioGrupo passes `tipoEvento: 'No disponible'` to keep its current wording.
  - The full-day background absence renders the "Ausencia" label through `AgendaEvent`, because FullCalendar runs `eventContent` for background events.
- **Month rows:** `dayMaxEventRows: 3`.
- **More link:** the locale's `moreLinkText` becomes `'más'`, so the link reads "+N más". The locale also gets the accents in "Día" and "Todo el día".
- **Tooltip teardown:** `eventWillUnmount` destroys the tippy instance, so tooltips no longer leak on re-render.
- **CalendarioGrupo:** keeps `expandRows` and `stickyHeaderDates` as overrides. Its `eventMaxStack: 6` is dropped in favor of the shared 2.
- **Removed defaults:** `slotEventOverlap: true` / `eventOverlap: true` were FullCalendar defaults and are dropped.
- **Legends:** the Turnos and CalendarioGrupo legends switch to token classes and show the four statuses plus Grupal, Ausencia and (Turnos only) No disponible. The dashed "Grupal" legend is gone, like the dashed outline.

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/agenda/agendaEventStyle.js` | Create | Pure helpers: `statusKey`, `statusLabel`, `eventStatus`, `isGrupal`, `isAusencia`, `isBackgroundEvent`, `eventClassNames`, `barColor`, `formatTime`. |
| `frontend/src/components/agenda/agendaEventStyle.test.js` | Create | Unit tests for the helpers. |
| `frontend/src/components/agenda/AgendaEvent.vue` | Create | Event card for the `#eventContent` slot: timeGrid, month, absence and background variants. |
| `frontend/src/components/agenda/AgendaEvent.test.js` | Create | Component tests. |
| `frontend/src/composables/useAgendaCalendar.js` | Create | Shared reactive FullCalendar options, locale, `buildTooltipContent`. |
| `frontend/src/composables/useAgendaCalendar.test.js` | Create | Composable and tooltip tests. |
| `frontend/src/assets/calendar-theme.css` | Create | Token-based FullCalendar theme, `.evt-*` classes, popover, hatch layers, tippy `agenda` theme. |
| `frontend/src/assets/calendar-medical.css` | Delete | Replaced by `calendar-theme.css`. |
| `frontend/src/views/pages/historias/Turnos.vue` | Modify | Adopt the composable and slot; drop hex, prefixes and locale; add `grupoNombre`; token legend and container. |
| `frontend/src/views/pages/turnos/CalendarioGrupo.vue` | Modify | Same, plus the `creadoPorNombre` normalization. |
| `frontend/src/views/pages/turnos/ModuloRehabilitacion.vue` | Modify | Same, plus `grupoColor` / `grupoNombre`; `hexToRgba` removed. |
| `frontend/scripts/check-tokens.mjs` | Modify | Allowlist comment only; the list is unchanged. |

---

### Task 1: Event style helpers

**Files:**
- Create: `frontend/src/components/agenda/agendaEventStyle.test.js`
- Create: `frontend/src/components/agenda/agendaEventStyle.js`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/agenda/agendaEventStyle.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { barColor, eventClassNames, eventStatus, formatTime, isBackgroundEvent, statusKey, statusLabel } from './agendaEventStyle';

function event(extendedProps = {}, extra = {}) {
    return { title: 'Ana Pérez', display: 'auto', extendedProps, ...extra };
}

describe('statusKey', () => {
    it.each([
        ['programado', 'programado'],
        ['presente', 'presente'],
        ['con_aviso', 'con-aviso'],
        ['sin_aviso', 'sin-aviso']
    ])('maps %s to %s', (estado, key) => {
        expect(statusKey(estado)).toBe(key);
    });

    it('falls back to programado for unknown or missing values', () => {
        expect(statusKey('cancelado')).toBe('programado');
        expect(statusKey(undefined)).toBe('programado');
        expect(statusKey(null)).toBe('programado');
    });
});

describe('statusLabel', () => {
    it.each([
        ['programado', 'Programado'],
        ['presente', 'Presente'],
        ['con-aviso', 'Falta con aviso'],
        ['sin-aviso', 'Falta sin aviso']
    ])('labels %s as %s', (key, label) => {
        expect(statusLabel(key)).toBe(label);
    });

    it('falls back to Programado for unknown keys', () => {
        expect(statusLabel('otro')).toBe('Programado');
    });
});

describe('eventStatus', () => {
    it('reads estado_asistencia and falls back to the legacy ausencia field', () => {
        expect(eventStatus(event({ estado_asistencia: 'presente' }))).toBe('presente');
        expect(eventStatus(event({ ausencia: 'con_aviso' }))).toBe('con-aviso');
        expect(eventStatus(event({}))).toBe('programado');
    });
});

describe('eventClassNames', () => {
    it('returns the base and status classes for an individual turno', () => {
        expect(eventClassNames(event({ tipo: 'individual', estado_asistencia: 'presente' }))).toEqual(['evt', 'evt-presente']);
    });

    it('adds evt-grupal for grupal turnos in Turnos', () => {
        expect(eventClassNames(event({ tipo: 'grupal', estado_asistencia: 'sin_aviso' }))).toEqual(['evt', 'evt-sin-aviso', 'evt-grupal']);
    });

    it('adds evt-grupal for turno_grupal in CalendarioGrupo', () => {
        expect(eventClassNames(event({ tipo: 'turno_grupal' }))).toEqual(['evt', 'evt-programado', 'evt-grupal']);
    });

    it('uses programado for an unknown status', () => {
        expect(eventClassNames(event({ estado_asistencia: 'raro' }))).toEqual(['evt', 'evt-programado']);
    });

    it('returns the absence card classes', () => {
        expect(eventClassNames(event({ tipo: 'ausencia' }))).toEqual(['evt', 'evt-ausencia']);
    });

    it('returns the unavailable hatch classes', () => {
        expect(eventClassNames(event({ tipo: 'indisponible_bg' }, { display: 'background' }))).toEqual(['bg-hatch', 'bg-hatch-unavailable']);
    });

    it('returns the absence hatch classes', () => {
        expect(eventClassNames(event({ tipo: 'ausencia_bg' }, { display: 'background' }))).toEqual(['bg-hatch', 'bg-hatch-absence']);
    });
});

describe('barColor', () => {
    it('returns the group color when present', () => {
        expect(barColor(event({ grupoColor: '#7C3AED' }))).toBe('#7C3AED');
    });

    it('returns null without a group color', () => {
        expect(barColor(event({}))).toBeNull();
    });

    it('returns null for values that are not hex colors', () => {
        expect(barColor(event({ grupoColor: 'red; background: url(x)' }))).toBeNull();
    });
});

describe('formatTime', () => {
    it('formats a date as HH:mm in local time', () => {
        expect(formatTime(new Date(2026, 8, 24, 9, 5))).toBe('09:05');
    });

    it('returns an empty string for missing or invalid dates', () => {
        expect(formatTime(null)).toBe('');
        expect(formatTime(new Date('nope'))).toBe('');
    });
});

describe('isBackgroundEvent', () => {
    it('detects background events by display or tipo', () => {
        expect(isBackgroundEvent(event({}, { display: 'background' }))).toBe(true);
        expect(isBackgroundEvent(event({ tipo: 'ausencia_bg' }))).toBe(true);
        expect(isBackgroundEvent(event({ tipo: 'individual' }))).toBe(false);
    });
});
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `npx vitest run src/components/agenda/agendaEventStyle.test.js`
Expected: FAIL. The suite errors with `Failed to resolve import "./agendaEventStyle"` (0 tests run).

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/agenda/agendaEventStyle.js`:

```js
// Pure helpers that map a FullCalendar event to agenda card styling.
// They accept FullCalendar EventApi objects or plain objects with the same shape.

const STATUS_KEYS = {
    programado: 'programado',
    presente: 'presente',
    con_aviso: 'con-aviso',
    sin_aviso: 'sin-aviso'
};

const STATUS_LABELS = {
    programado: 'Programado',
    presente: 'Presente',
    'con-aviso': 'Falta con aviso',
    'sin-aviso': 'Falta sin aviso'
};

const GRUPAL_TIPOS = new Set(['grupal', 'turno_grupal']);
const BACKGROUND_TIPOS = new Set(['ausencia_bg', 'indisponible_bg']);
const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

function props(event) {
    return event?.extendedProps || {};
}

function pad(n) {
    return String(n).padStart(2, '0');
}

export function statusKey(estado) {
    return STATUS_KEYS[estado] || 'programado';
}

export function statusLabel(key) {
    return STATUS_LABELS[key] || STATUS_LABELS.programado;
}

export function eventStatus(event) {
    const p = props(event);
    return statusKey(p.estado_asistencia || p.ausencia);
}

export function isGrupal(event) {
    return GRUPAL_TIPOS.has(props(event).tipo);
}

export function isAusencia(event) {
    return props(event).tipo === 'ausencia';
}

export function isBackgroundEvent(event) {
    return event?.display === 'background' || BACKGROUND_TIPOS.has(props(event).tipo);
}

export function eventClassNames(event) {
    const tipo = props(event).tipo;
    if (tipo === 'indisponible_bg') return ['bg-hatch', 'bg-hatch-unavailable'];
    if (tipo === 'ausencia_bg') return ['bg-hatch', 'bg-hatch-absence'];
    if (tipo === 'ausencia') return ['evt', 'evt-ausencia'];

    const classes = ['evt', `evt-${eventStatus(event)}`];
    if (isGrupal(event)) classes.push('evt-grupal');
    return classes;
}

// Group color for the left bar (Rehab); null means "use the status color".
export function barColor(event) {
    const color = props(event).grupoColor;
    return typeof color === 'string' && HEX_COLOR.test(color) ? color : null;
}

export function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `npx vitest run src/components/agenda/agendaEventStyle.test.js`
Expected: PASS. `Test Files  1 passed (1)`, `Tests  24 passed (24)`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/agenda/agendaEventStyle.js frontend/src/components/agenda/agendaEventStyle.test.js
git commit -m "feat(agenda): add event style helpers"
```

---

### Task 2: AgendaEvent card component

**Files:**
- Create: `frontend/src/components/agenda/AgendaEvent.test.js`
- Create: `frontend/src/components/agenda/AgendaEvent.vue`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/agenda/AgendaEvent.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import AgendaEvent from './AgendaEvent.vue';

function makeArg(extendedProps = {}, { viewType = 'timeGridWeek', display = 'auto', title = 'Ana Pérez' } = {}) {
    return {
        view: { type: viewType },
        event: {
            title,
            display,
            start: new Date(2026, 8, 24, 10, 0),
            end: new Date(2026, 8, 24, 10, 20),
            extendedProps: { tipo: 'individual', paciente: 'Ana Pérez', description: 'Control', estado_asistencia: 'programado', ...extendedProps }
        }
    };
}

function mountEvent(...args) {
    return mount(AgendaEvent, { props: { arg: makeArg(...args) } });
}

describe('AgendaEvent', () => {
    it('renders time, patient and motivo in the timeGrid card', () => {
        const wrapper = mountEvent();
        expect(wrapper.find('.evt-time').text()).toBe('10:00');
        expect(wrapper.find('.evt-name').text()).toBe('Ana Pérez');
        expect(wrapper.find('.evt-detail').text()).toBe('Control');
    });

    it('renders a single-line variant in month view', () => {
        const wrapper = mountEvent({}, { viewType: 'dayGridMonth' });
        expect(wrapper.find('.evt-card--month').exists()).toBe(true);
        expect(wrapper.find('.evt-dot').exists()).toBe(true);
        expect(wrapper.find('.evt-detail').exists()).toBe(false);
        expect(wrapper.text()).toContain('10:00');
        expect(wrapper.text()).toContain('Ana Pérez');
    });

    it('shows the group icon and the group name for grupal turnos', () => {
        const wrapper = mountEvent({ tipo: 'grupal', grupoNombre: 'Kinesiología' });
        expect(wrapper.find('.pi-users').exists()).toBe(true);
        expect(wrapper.find('.evt-detail').text()).toBe('Kinesiología');
    });

    it('includes the status label in the aria-label', () => {
        const wrapper = mountEvent({ estado_asistencia: 'presente' });
        const label = wrapper.find('.evt-card').attributes('aria-label');
        expect(label).toContain('Presente');
        expect(label).toContain('Ana Pérez');
        expect(label).toContain('10:00');
    });

    it('strikes the patient name for sin_aviso', () => {
        const wrapper = mountEvent({ estado_asistencia: 'sin_aviso' });
        expect(wrapper.find('.evt-name').classes()).toContain('evt-name--struck');
        expect(wrapper.find('.evt-card').attributes('aria-label')).toContain('Falta sin aviso');
    });

    it('sets --evt-bar inline when the event has a group color', () => {
        const wrapper = mountEvent({ grupoColor: '#7c3aed' });
        expect(wrapper.find('.evt-card').element.style.getPropertyValue('--evt-bar')).toBe('#7c3aed');
    });

    it('does not set --evt-bar without a group color', () => {
        const wrapper = mountEvent();
        expect(wrapper.find('.evt-card').element.style.getPropertyValue('--evt-bar')).toBe('');
    });

    it('renders an absence with its type and professional', () => {
        const wrapper = mountEvent({ tipo: 'ausencia', tipoEvento: 'Reunion', profesional: 'Dra. Gómez', paciente: undefined, estado_asistencia: undefined });
        expect(wrapper.find('.evt-name').text()).toBe('Reunion');
        expect(wrapper.find('.evt-detail').text()).toBe('Dra. Gómez');
        expect(wrapper.find('.evt-card').attributes('aria-label')).toContain('Ausencia');
    });

    it('renders only the Ausencia label for a full-day absence background', () => {
        const wrapper = mountEvent({ tipo: 'ausencia_bg' }, { display: 'background', title: '' });
        expect(wrapper.find('.evt-card').exists()).toBe(false);
        expect(wrapper.find('.bg-hatch-label').text()).toBe('Ausencia');
    });
});
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `npx vitest run src/components/agenda/AgendaEvent.test.js`
Expected: FAIL. The suite errors with `Failed to resolve import "./AgendaEvent.vue"` (0 tests run).

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/agenda/AgendaEvent.vue`:

```vue
<script setup>
// Rendered by FullCalendar's #eventContent slot inside a detached Vue app (no appContext):
// use plain elements and global CSS classes only, never PrimeVue components or plugins.
import { computed } from 'vue';
import { barColor, eventStatus, formatTime, isAusencia, isBackgroundEvent, isGrupal, statusLabel } from './agendaEventStyle';

const props = defineProps({
    arg: { type: Object, required: true }
});

const event = computed(() => props.arg.event);
const extended = computed(() => event.value.extendedProps || {});
const background = computed(() => isBackgroundEvent(event.value));
const month = computed(() => String(props.arg.view?.type || '').startsWith('dayGrid'));
const status = computed(() => eventStatus(event.value));
const grupal = computed(() => isGrupal(event.value));
const ausencia = computed(() => isAusencia(event.value));
const time = computed(() => formatTime(event.value.start));

const name = computed(() => {
    if (ausencia.value) return extended.value.tipoEvento || 'Ausencia';
    return extended.value.paciente || event.value.title || '';
});

const detail = computed(() => {
    if (ausencia.value) return extended.value.profesional || '';
    if (grupal.value) return extended.value.grupoNombre || extended.value.profesional || '';
    return extended.value.description || '';
});

const label = computed(() => {
    const kind = ausencia.value ? 'Ausencia' : statusLabel(status.value);
    return [kind, time.value, name.value, detail.value].filter(Boolean).join(', ');
});

const struck = computed(() => !ausencia.value && status.value === 'sin-aviso');

const cardStyle = computed(() => {
    const color = barColor(event.value);
    return color ? { '--evt-bar': color } : undefined;
});

const backgroundLabel = computed(() => (extended.value.tipo === 'ausencia_bg' ? 'Ausencia' : ''));
</script>

<template>
    <span v-if="background" class="bg-hatch-label">{{ backgroundLabel }}</span>
    <div v-else-if="month" class="evt-card evt-card--month" :style="cardStyle" role="group" :aria-label="label">
        <span class="evt-dot" aria-hidden="true"></span>
        <span class="evt-time">{{ time }}</span>
        <i v-if="grupal" class="pi pi-users evt-icon" aria-hidden="true"></i>
        <span class="evt-name" :class="{ 'evt-name--struck': struck }">{{ name }}</span>
    </div>
    <div v-else class="evt-card" :style="cardStyle" role="group" :aria-label="label">
        <div class="evt-line">
            <span class="evt-time">{{ time }}</span>
            <i v-if="grupal" class="pi pi-users evt-icon" aria-hidden="true"></i>
            <span class="evt-name" :class="{ 'evt-name--struck': struck }">{{ name }}</span>
        </div>
        <div v-if="detail" class="evt-detail">{{ detail }}</div>
    </div>
</template>
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `npx vitest run src/components/agenda/AgendaEvent.test.js`
Expected: PASS. `Test Files  1 passed (1)`, `Tests  9 passed (9)`.

- [ ] **Step 5: Run the token guard on the new component**

Run: `npm run check:tokens`
Expected: `check:tokens OK`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/agenda/AgendaEvent.vue frontend/src/components/agenda/AgendaEvent.test.js
git commit -m "feat(agenda): add AgendaEvent card component"
```

---

### Task 3: useAgendaCalendar composable and tooltip builder

**Files:**
- Create: `frontend/src/composables/useAgendaCalendar.test.js`
- Create: `frontend/src/composables/useAgendaCalendar.js`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/composables/useAgendaCalendar.test.js`:

```js
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { isReactive } from 'vue';

vi.mock('tippy.js', () => ({ default: vi.fn() }));

import tippy from 'tippy.js';
import { AGENDA_LOCALE, buildTooltipContent, useAgendaCalendar } from './useAgendaCalendar';

function turno(extendedProps = {}, extra = {}) {
    return {
        title: 'Ana Pérez',
        display: 'auto',
        start: new Date(2026, 8, 24, 10, 0),
        end: new Date(2026, 8, 24, 10, 20),
        extendedProps: { tipo: 'individual', paciente: 'Ana Pérez', ...extendedProps },
        ...extra
    };
}

describe('useAgendaCalendar', () => {
    beforeEach(() => {
        tippy.mockClear();
    });

    it('returns the shared base options', () => {
        const options = useAgendaCalendar();
        expect(options.plugins).toHaveLength(3);
        expect(options.initialView).toBe('timeGridWeek');
        expect(options.slotMinTime).toBe('07:00:00');
        expect(options.slotMaxTime).toBe('22:00:00');
        expect(options.allDaySlot).toBe(false);
        expect(options.height).toBe('100%');
        expect(options.eventMaxStack).toBe(2);
        expect(options.dayMaxEventRows).toBe(3);
        expect(options.headerToolbar).toEqual({ left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' });
        expect(options.eventContent).toBeUndefined();
    });

    it('uses the Spanish locale', () => {
        const options = useAgendaCalendar();
        expect(options.locale.code).toBe('es');
        expect(AGENDA_LOCALE.moreLinkText).toBe('más');
        expect(AGENDA_LOCALE.buttonText.today).toBe('Hoy');
    });

    it('merges overrides over the base options', () => {
        const dateClick = vi.fn();
        const options = useAgendaCalendar({ slotDuration: '00:30:00', initialView: 'dayGridMonth', expandRows: true, dateClick });
        expect(options.slotDuration).toBe('00:30:00');
        expect(options.initialView).toBe('dayGridMonth');
        expect(options.expandRows).toBe(true);
        expect(options.dateClick).toBe(dateClick);
        expect(options.eventMaxStack).toBe(2);
        expect(options.locale.code).toBe('es');
    });

    it('returns a reactive object so views can rebind options', () => {
        const options = useAgendaCalendar();
        expect(isReactive(options)).toBe(true);
        options.slotDuration = '00:15:00';
        expect(options.slotDuration).toBe('00:15:00');
    });

    it('delegates eventClassNames to the style helpers', () => {
        const options = useAgendaCalendar();
        expect(options.eventClassNames({ event: turno({ estado_asistencia: 'presente' }) })).toEqual(['evt', 'evt-presente']);
    });

    it('attaches a themed tippy tooltip on mount', () => {
        const options = useAgendaCalendar();
        const el = document.createElement('a');
        options.eventDidMount({ event: turno(), el });
        expect(tippy).toHaveBeenCalledWith(el, expect.objectContaining({ theme: 'agenda', allowHTML: true, placement: 'top' }));
    });

    it('skips tooltips for background events', () => {
        const options = useAgendaCalendar();
        options.eventDidMount({ event: turno({ tipo: 'ausencia_bg' }, { display: 'background' }), el: document.createElement('div') });
        expect(tippy).not.toHaveBeenCalled();
    });

    it('destroys the tooltip on unmount', () => {
        const options = useAgendaCalendar();
        const destroy = vi.fn();
        const el = document.createElement('a');
        el._tippy = { destroy };
        options.eventWillUnmount({ event: turno(), el });
        expect(destroy).toHaveBeenCalledTimes(1);
    });
});

describe('buildTooltipContent', () => {
    it('lists patient, DNI, time range, status, motivo and professional', () => {
        const html = buildTooltipContent(turno({ dni: '30111222', estado_asistencia: 'presente', description: 'Control', profesional: 'Dra. Gómez' }));
        expect(html).toContain('<strong>Ana Pérez</strong>');
        expect(html).toContain('DNI 30111222');
        expect(html).toContain('10:00 – 10:20');
        expect(html).toContain('Presente');
        expect(html).toContain('Control');
        expect(html).toContain('Dra. Gómez');
    });

    it('escapes HTML coming from the data', () => {
        const html = buildTooltipContent(turno({ paciente: '<img src=x onerror=alert(1)>' }));
        expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
        expect(html).not.toContain('<img');
    });

    it('describes an absence with its type and professional', () => {
        const html = buildTooltipContent(turno({ tipo: 'ausencia', tipoEvento: 'Reunion', profesional: 'Dra. Gómez', paciente: undefined }));
        expect(html).toContain('<strong>Reunion</strong>');
        expect(html).toContain('Dra. Gómez');
        expect(html).toContain('10:00 – 10:20');
    });

    it('shows the group line once', () => {
        const html = buildTooltipContent(turno({ tipo: 'turno_grupal', profesional: 'Grupo: Kinesio', grupoNombre: 'Kinesio' }));
        expect(html.split('Grupo: Kinesio').length - 1).toBe(1);
    });
});
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `npx vitest run src/composables/useAgendaCalendar.test.js`
Expected: FAIL. The suite errors with `Failed to resolve import "./useAgendaCalendar"` (0 tests run).

- [ ] **Step 3: Write the implementation**

Create `frontend/src/composables/useAgendaCalendar.js`:

```js
// Shared FullCalendar setup for the agenda views (Turnos, CalendarioGrupo, ModuloRehabilitacion).
// Event markup comes from the view's #eventContent slot (AgendaEvent); do not set eventContent here,
// because an explicit option would override the slot.
import { reactive } from 'vue';
// FullCalendar plugins throw unless the core VDOM is loaded first.
import '@fullcalendar/core/vdom';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import { eventClassNames, eventStatus, formatTime, isAusencia, isBackgroundEvent, statusLabel } from '@/components/agenda/agendaEventStyle';

export const AGENDA_LOCALE = {
    code: 'es',
    week: { dow: 1, doy: 4 },
    buttonText: { prev: 'Ant', next: 'Sig', today: 'Hoy', month: 'Mes', week: 'Semana', day: 'Día', list: 'Agenda' },
    weekText: 'Sm',
    allDayText: 'Todo el día',
    moreLinkText: 'más',
    noEventsText: 'No hay eventos para mostrar'
};

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => HTML_ESCAPES[ch]);
}

function muted(text) {
    return text ? `<span class="agenda-tip-muted">${escapeHtml(text)}</span>` : '';
}

function timeRange(event) {
    const start = formatTime(event.start);
    const end = formatTime(event.end);
    return end ? `${start} – ${end}` : start;
}

export function buildTooltipContent(event) {
    const p = event.extendedProps || {};

    if (isAusencia(event)) {
        return [`<strong>${escapeHtml(p.tipoEvento || 'Ausencia')}</strong>`, escapeHtml(p.profesional || 'Profesional'), timeRange(event), muted(p.description)].filter(Boolean).join('<br>');
    }

    const key = eventStatus(event);
    const grupoLine = p.grupoNombre ? `Grupo: ${p.grupoNombre}` : '';
    const profesional = p.profesional && p.profesional !== grupoLine ? p.profesional : '';

    return [
        `<strong>${escapeHtml(p.paciente || event.title)}</strong>`,
        p.dni ? `DNI ${escapeHtml(p.dni)}` : '',
        `${timeRange(event)} · <span class="agenda-tip-status agenda-tip-status--${key}">${statusLabel(key)}</span>`,
        muted(p.description),
        escapeHtml(profesional),
        escapeHtml(grupoLine)
    ]
        .filter(Boolean)
        .join('<br>');
}

function attachTooltip(info) {
    if (isBackgroundEvent(info.event)) return;
    tippy(info.el, {
        content: buildTooltipContent(info.event),
        allowHTML: true,
        placement: 'top',
        theme: 'agenda'
    });
}

function detachTooltip(info) {
    info.el?._tippy?.destroy();
}

function baseOptions() {
    return {
        plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
        initialView: 'timeGridWeek',
        locale: AGENDA_LOCALE,
        headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' },
        slotMinTime: '07:00:00',
        slotMaxTime: '22:00:00',
        allDaySlot: false,
        height: '100%',
        eventMaxStack: 2,
        dayMaxEventRows: 3,
        eventClassNames: (arg) => eventClassNames(arg.event),
        eventDidMount: attachTooltip,
        eventWillUnmount: detachTooltip
    };
}

// Overrides are shallow-merged: a view's key replaces the base key entirely.
export function useAgendaCalendar(overrides = {}) {
    return reactive({ ...baseOptions(), ...overrides });
}
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `npx vitest run src/composables/useAgendaCalendar.test.js`
Expected: PASS. `Test Files  1 passed (1)`, `Tests  12 passed (12)`.

- [ ] **Step 5: Lint**

Run: `npm run lint`
Expected: exits 0 with no errors reported.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/composables/useAgendaCalendar.js frontend/src/composables/useAgendaCalendar.test.js
git commit -m "feat(agenda): add useAgendaCalendar composable"
```

---

### Task 4: Token-based calendar theme replaces calendar-medical.css

**Files:**
- Create: `frontend/src/assets/calendar-theme.css`
- Delete: `frontend/src/assets/calendar-medical.css`
- Modify: `frontend/src/composables/useAgendaCalendar.js` (add the theme import)
- Modify: `frontend/src/views/pages/historias/Turnos.vue`, `frontend/src/views/pages/turnos/CalendarioGrupo.vue`, `frontend/src/views/pages/turnos/ModuloRehabilitacion.vue` (import line only)

- [ ] **Step 1: Create the theme**

Create `frontend/src/assets/calendar-theme.css`. It must contain no hex colors, not even in comments.

```css
/*
 * Agenda calendar theme (FullCalendar 5.11 + AgendaEvent + tippy "agenda").
 * Colors come only from PrimeVue --p-* tokens and --cau-status-* tokens (src/theme/status.css),
 * so light and dark mode follow .app-dark automatically.
 */

/* ---------- FullCalendar chrome ---------- */
.fc {
    --fc-border-color: var(--p-content-border-color);
    --fc-page-bg-color: var(--p-content-background);
    --fc-neutral-bg-color: var(--p-app-subtle-background);
    --fc-neutral-text-color: var(--p-text-muted-color);
    --fc-today-bg-color: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
    --fc-non-business-color: color-mix(in srgb, var(--p-text-muted-color) 8%, transparent);
    --fc-highlight-color: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
    --fc-now-indicator-color: var(--cau-status-sin-aviso-fg);
    --fc-bg-event-opacity: 1;
    --fc-more-link-bg-color: var(--p-highlight-background);
    --fc-more-link-text-color: var(--p-highlight-color);
    --fc-small-font-size: 0.75rem;
    --fc-event-bg-color: var(--p-highlight-background);
    --fc-event-border-color: var(--p-primary-color);
    --fc-event-text-color: var(--p-text-color);
    --fc-event-selected-overlay-color: color-mix(in srgb, var(--p-text-color) 12%, transparent);
    --fc-button-text-color: var(--p-text-color);
    --fc-button-bg-color: var(--p-content-background);
    --fc-button-border-color: var(--p-content-border-color);
    --fc-button-hover-bg-color: var(--p-content-hover-background);
    --fc-button-hover-border-color: var(--p-content-border-color);
    --fc-button-active-bg-color: var(--p-primary-color);
    --fc-button-active-border-color: var(--p-primary-color);
    color: var(--p-text-color);
    font-size: 0.875rem;
}

.fc .fc-toolbar.fc-header-toolbar {
    margin-bottom: 1rem;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.fc .fc-toolbar-title {
    font-size: 1.125rem;
    font-weight: 600;
    text-transform: capitalize;
    color: var(--p-text-color);
}

.fc .fc-button {
    border-radius: 8px;
    font-size: 0.8125rem;
    font-weight: 500;
    padding: 0.375rem 0.75rem;
    box-shadow: none;
}

.fc .fc-button-primary:not(:disabled).fc-button-active,
.fc .fc-button-primary:not(:disabled):active {
    color: var(--p-primary-contrast-color);
}

.fc .fc-button-primary:focus,
.fc .fc-button-primary:not(:disabled).fc-button-active:focus,
.fc .fc-button-primary:not(:disabled):active:focus {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}

.fc .fc-button-primary:disabled {
    color: var(--p-text-muted-color);
    opacity: 0.6;
}

.fc .fc-col-header-cell-cushion {
    color: var(--p-text-muted-color);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 6px 4px;
}

.fc .fc-timegrid-slot-label-cushion,
.fc .fc-timegrid-axis-cushion {
    color: var(--p-text-muted-color);
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
}

.fc .fc-daygrid-day-number {
    color: var(--p-text-color);
    font-size: 0.8125rem;
}

.fc .fc-day-today .fc-daygrid-day-number,
.fc .fc-day-today .fc-col-header-cell-cushion {
    color: var(--p-primary-color);
    font-weight: 700;
}

/* ---------- Event status variables (set on the FullCalendar event root) ---------- */
.evt {
    --evt-fg: var(--p-primary-color);
    --evt-bg: var(--p-highlight-background);
    --evt-bar: var(--evt-fg);
}

.evt-presente {
    --evt-fg: var(--cau-status-presente-fg);
    --evt-bg: var(--cau-status-presente-bg);
}

.evt-con-aviso {
    --evt-fg: var(--cau-status-con-aviso-fg);
    --evt-bg: var(--cau-status-con-aviso-bg);
}

.evt-sin-aviso {
    --evt-fg: var(--cau-status-sin-aviso-fg);
    --evt-bg: var(--cau-status-sin-aviso-bg);
}

.evt-ausencia {
    --evt-fg: var(--p-text-muted-color);
    --evt-bg: var(--p-content-hover-background);
    --evt-bar: var(--cau-status-sin-aviso-border);
}

/* The card draws the visuals; the FullCalendar root stays transparent. */
.fc .fc-event.evt,
.fc .fc-event.evt:hover {
    background: transparent;
    border-color: transparent;
}

.fc .fc-event.evt .fc-event-main {
    padding: 0;
    color: inherit;
}

/* The Vue slot mounts inside an artificial <span>; make it fill the event box. */
.fc .fc-event.evt > span,
.fc .fc-event.evt .fc-event-main > span,
.fc .fc-bg-event.bg-hatch > span {
    display: block;
    width: 100%;
    height: 100%;
    min-width: 0;
}

/* ---------- AgendaEvent card ---------- */
.evt-card {
    display: flex;
    flex-direction: column;
    gap: 1px;
    height: 100%;
    min-width: 0;
    padding: 2px 6px 2px 8px;
    border-left: 4px solid var(--evt-bar);
    border-radius: 6px;
    background: var(--evt-bg);
    color: var(--p-text-color);
    font-size: 0.75rem;
    line-height: 1.25;
    overflow: hidden;
    cursor: pointer;
}

.evt-line {
    display: flex;
    align-items: baseline;
    gap: 4px;
    min-width: 0;
    white-space: nowrap;
}

.evt-time {
    flex: none;
    color: var(--evt-fg);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.evt-icon {
    flex: none;
    color: var(--evt-fg);
    font-size: 0.6875rem;
}

.evt-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 600;
}

.evt-name--struck {
    text-decoration: line-through;
    text-decoration-thickness: 1px;
    text-decoration-color: color-mix(in srgb, var(--evt-fg) 60%, transparent);
}

.evt-detail {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--p-text-muted-color);
}

/* Month view: compact single line with a status dot. */
.evt-card--month {
    flex-direction: row;
    align-items: center;
    gap: 4px;
    padding: 1px 4px;
    border-left: 0;
    background: transparent;
}

.evt-dot {
    flex: none;
    width: 8px;
    height: 8px;
    border-radius: 9999px;
    background: var(--evt-bar);
}

.fc .fc-daygrid-dot-event.evt:hover {
    background: var(--p-content-hover-background);
}

/* ---------- "+N" links and popover ---------- */
.fc .fc-timegrid-more-link {
    background: var(--fc-more-link-bg-color);
    color: var(--fc-more-link-text-color);
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
}

.fc .fc-daygrid-more-link {
    color: var(--p-primary-color);
    font-size: 0.75rem;
    font-weight: 600;
}

.fc .fc-popover {
    background: var(--p-overlay-popover-background, var(--p-content-background));
    border: 1px solid var(--p-content-border-color);
    border-radius: 10px;
    box-shadow: 0 10px 30px color-mix(in srgb, var(--p-text-color) 18%, transparent);
    overflow: hidden;
    z-index: 20;
}

.fc .fc-popover-header {
    background: var(--p-app-subtle-background);
    color: var(--p-text-color);
    font-weight: 600;
    padding: 6px 10px;
}

.fc .fc-popover-close {
    color: var(--p-text-muted-color);
    opacity: 1;
}

.fc .fc-more-popover .fc-popover-body {
    min-width: 240px;
    max-height: 320px;
    overflow-y: auto;
    padding: 6px;
}

.fc .fc-more-popover .fc-daygrid-event.evt {
    margin: 2px 0;
}

.fc .fc-more-popover .evt-card {
    height: auto;
}

/* ---------- Background layers ---------- */
.fc .fc-bg-event.bg-hatch {
    opacity: 1;
}

.fc .fc-bg-event.bg-hatch-unavailable,
.agenda-swatch-unavailable {
    background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--p-text-muted-color) 16%, transparent) 0 6px, transparent 6px 12px);
}

.fc .fc-bg-event.bg-hatch-absence,
.agenda-swatch-absence {
    background: repeating-linear-gradient(
        135deg,
        color-mix(in srgb, var(--cau-status-sin-aviso-fg) 16%, transparent) 0 6px,
        color-mix(in srgb, var(--cau-status-sin-aviso-fg) 5%, transparent) 6px 12px
    );
}

.bg-hatch-label {
    display: block;
    padding: 4px 6px;
    color: var(--cau-status-sin-aviso-fg);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.bg-hatch-label:empty {
    display: none;
}

/* ---------- Tooltip (tippy theme "agenda", appended to <body>) ---------- */
.tippy-box[data-theme~='agenda'] {
    background: var(--p-overlay-popover-background, var(--p-content-background));
    color: var(--p-text-color);
    border: 1px solid var(--p-content-border-color);
    border-radius: 8px;
    box-shadow: 0 8px 24px color-mix(in srgb, var(--p-text-color) 16%, transparent);
    font-size: 0.8125rem;
    line-height: 1.45;
}

.tippy-box[data-theme~='agenda'] > .tippy-content {
    padding: 8px 10px;
}

.tippy-box[data-theme~='agenda'] > .tippy-arrow {
    color: var(--p-overlay-popover-background, var(--p-content-background));
}

.tippy-box[data-theme~='agenda'] strong {
    color: var(--p-text-color);
}

.agenda-tip-muted {
    color: var(--p-text-muted-color);
}

.agenda-tip-status {
    font-weight: 600;
    color: var(--p-primary-color);
}

.agenda-tip-status--presente {
    color: var(--cau-status-presente-fg);
}

.agenda-tip-status--con-aviso {
    color: var(--cau-status-con-aviso-fg);
}

.agenda-tip-status--sin-aviso {
    color: var(--cau-status-sin-aviso-fg);
}
```

- [ ] **Step 2: Load the theme from the composable**

In `frontend/src/composables/useAgendaCalendar.js`, add this line directly after `import 'tippy.js/dist/tippy.css';`:

```js
import '@/assets/calendar-theme.css';
```

- [ ] **Step 3: Point the three views at the new theme and delete the old one**

In each of these files, replace the line `import '@/assets/calendar-medical.css';` with `import '@/assets/calendar-theme.css';`:
- `frontend/src/views/pages/historias/Turnos.vue`
- `frontend/src/views/pages/turnos/CalendarioGrupo.vue`
- `frontend/src/views/pages/turnos/ModuloRehabilitacion.vue`

This is a temporary bridge so each commit builds and the chrome is themed. Tasks 5-7 remove these direct imports again once each view uses the composable.

Then delete the old file:

```bash
git rm frontend/src/assets/calendar-medical.css
```

- [ ] **Step 4: Verify there are no hex colors and no import of the old file**

Run: `rg -n "#[0-9a-fA-F]{3,8}\b" src/assets/calendar-theme.css`
Expected: no output (exit code 1).

Run: `rg -n "calendar-medical\.css';" src`
Expected: no output (exit code 1). The `<style scoped>` comments that mention calendar-medical are removed in Tasks 5-7.

- [ ] **Step 5: Test and build**

Run: `npm run test`
Expected: all test files pass (`Tests  N passed`, 0 failed).

Run: `npm run build`
Expected: `✓ built in …` with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/assets/calendar-theme.css frontend/src/composables/useAgendaCalendar.js frontend/src/views/pages/historias/Turnos.vue frontend/src/views/pages/turnos/CalendarioGrupo.vue frontend/src/views/pages/turnos/ModuloRehabilitacion.vue
git commit -m "style(agenda): replace calendar-medical with token-based calendar theme"
```

(The `git rm` from Step 3 is already staged.)

---

### Task 5: Migrate Turnos.vue

**Files:**
- Modify: `frontend/src/views/pages/historias/Turnos.vue`

- [ ] **Step 1: Replace the imports**

Replace these lines at the top of `<script setup>`:

```js
import { ref, onMounted, onUnmounted, reactive, computed, watch } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import api from '@/api/axios';
import { fechaBonitaCompleta } from '@/utils/formatDate';
import '@/assets/calendar-theme.css';
```

with:

```js
import { ref, onMounted, onUnmounted, reactive, computed, watch } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import api from '@/api/axios';
import { fechaBonitaCompleta } from '@/utils/formatDate';
import AgendaEvent from '@/components/agenda/AgendaEvent.vue';
import { useAgendaCalendar } from '@/composables/useAgendaCalendar';
```

- [ ] **Step 2: Delete the local locale**

Delete the whole `const esLocale = { … };` block (code `'es'`, `buttonText`, `moreLinkText: 'mas'`, …). The composable provides `AGENDA_LOCALE`.

- [ ] **Step 3: Replace the unavailability background events with class-only hatch events**

In `crearEventosNoDisponibilidad`, each of the three `eventos.push({ … })` calls currently has:

```js
                display: 'background',
                classNames: ['no-disponible-background'],
                backgroundColor: 'rgba(107, 114, 128, 0.22)',
                extendedProps: { tipo: 'indisponible_bg' }
```

(indentation differs per call). In all three, delete the `classNames` and `backgroundColor` lines, leaving:

```js
                display: 'background',
                extendedProps: { tipo: 'indisponible_bg' }
```

`eventClassNames` in the composable adds `bg-hatch bg-hatch-unavailable`.

- [ ] **Step 4: Replace `calendarOptions`**

Replace the whole `const calendarOptions = reactive({ … });` block, from `const calendarOptions = reactive({` through the closing `});` after `eventDidMount`, with:

```js
const calendarOptions = useAgendaCalendar({
    slotDuration: '00:20:00',
    snapDuration: '00:20:00',
    slotLabelInterval: '00:20:00',
    events: eventos,
    dateClick(info) {
        abrirModalNuevoTurno(info.date);
    },
    eventClick(info) {
        const e = info.event;
        const tipo = e.extendedProps.tipo;
        if (tipo === 'ausencia_bg' || tipo === 'indisponible_bg') return;

        turnoSeleccionado.value = {
            id: e.id,
            turnoId: e.extendedProps.turnoId || e.id,
            tipo,
            editable: Boolean(e.extendedProps.editable),
            paciente: e.extendedProps.paciente,
            dni: e.extendedProps.dni,
            cobertura: e.extendedProps.cobertura,
            nro_certificado: e.extendedProps.nro_certificado,
            profesional: e.extendedProps.profesional,
            description: e.extendedProps.description,
            observaciones: e.extendedProps.observaciones,
            ausencia: e.extendedProps.ausencia,
            estado_asistencia: e.extendedProps.estado_asistencia || (e.extendedProps.ausencia ? e.extendedProps.ausencia : 'programado'),
            paciente_id: e.extendedProps.paciente_id,
            tipoEvento: e.extendedProps.tipoEvento || 'Bloqueo',
            ausenciaId: e.extendedProps.ausenciaId,
            usuarioId: e.extendedProps.usuarioId,
            grupoId: e.extendedProps.grupoId,
            creadoPorNombre: e.extendedProps.creadoPorNombre,
            creadoEn: e.extendedProps.creadoEn,
            start: e.start,
            end: e.end
        };

        // Fetch absence counts for the detail view
        ausenciasConteoDetalle.value = null;
        if (e.extendedProps.paciente_id) {
            api.get(`/pacientes/${e.extendedProps.paciente_id}/ausencias`, { withCredentials: true })
                .then((res) => {
                    ausenciasConteoDetalle.value = res.data;
                })
                .catch((err) => console.error(err));
        }

        editando.value = false;
        modalVisible.value = true;
    }
});
```

The `watch(duracionTurno, …)` block that follows stays as it is. It still rebinds `slotDuration` / `snapDuration` / `slotLabelInterval` on the reactive object.

- [ ] **Step 5: Strip the colors from the absence events**

In `crearEventosAusencia`, the first row loses `title` color prefixes (it has none), `backgroundColor`, `borderColor`, `textColor` and `classNames`. Replace:

```js
            title: `${tipoEvento}: ${ausencia.nombre_usuario || 'Profesional'}`,
            start: ausencia.fecha_inicio,
            end: ausencia.fecha_fin,
            backgroundColor: 'rgba(239,68,68,0.12)',
            borderColor: '#EF4444',
            textColor: '#991B1B',
            classNames: ['evento-ausencia'],
            extendedProps: {
```

with:

```js
            title: `${tipoEvento}: ${ausencia.nombre_usuario || 'Profesional'}`,
            start: ausencia.fecha_inicio,
            end: ausencia.fecha_fin,
            extendedProps: {
```

In the full-day background row, replace:

```js
            classNames: ['ausencia-background'],
            backgroundColor: 'rgba(248, 113, 113, 0.15)',
            extendedProps: { tipo: 'ausencia_bg' }
```

with:

```js
            extendedProps: { tipo: 'ausencia_bg' }
```

- [ ] **Step 6: Replace `adaptarEventoTurno`**

Replace the whole function with:

```js
function adaptarEventoTurno(t) {
    const tipo = t.tipo || 'individual';
    const esGrupal = tipo === 'grupal';
    const estadoAsistencia = t.estado_asistencia || (t.ausencia ? t.ausencia : 'programado');
    return {
        id: t.id,
        title: t.paciente || '',
        start: t.start,
        end: t.end,
        extendedProps: {
            tipo,
            turnoId: t.turnoId || t.id,
            paciente: t.paciente,
            dni: t.dni,
            cobertura: t.cobertura,
            nro_certificado: t.nro_certificado ?? t.nro_cobertura,
            profesional: t.profesional,
            grupoNombre: t.grupo_nombre,
            description: t.description,
            observaciones: t.observaciones,
            ausencia: t.ausencia,
            estado_asistencia: estadoAsistencia,
            paciente_id: t.paciente_id,
            creadoPorNombre: t.creado_por_nombre,
            creadoEn: t.creado_en,
            editable: Boolean(t.editable) && !esGrupal,
            grupoId: t.grupo_id
        }
    };
}
```

- [ ] **Step 7: Replace the legend and the calendar container in the template**

Replace the `<!-- Leyenda -->` block and the `<!-- Calendar container -->` block, from `<!-- Leyenda -->` through the `</div>` that closes the container around `<FullCalendar … />`, with:

```html
        <!-- Leyenda -->
        <div class="flex items-center gap-2 mb-4 flex-wrap text-xs font-medium">
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-highlight text-primary"> <span class="w-2.5 h-2.5 rounded-full bg-primary inline-block"></span> Programado </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-presente-bg text-status-presente-fg"> <span class="w-2.5 h-2.5 rounded-full bg-status-presente-fg inline-block"></span> Presente </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-con-aviso-bg text-status-con-aviso-fg"> <span class="w-2.5 h-2.5 rounded-full bg-status-con-aviso-fg inline-block"></span> Falta con aviso </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-sin-aviso-bg text-status-sin-aviso-fg"> <span class="w-2.5 h-2.5 rounded-full bg-status-sin-aviso-fg inline-block"></span> Falta sin aviso </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-subtle text-muted-color border border-line"> <i class="pi pi-users text-[10px]"></i> Grupal </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-subtle text-muted-color border border-line"> <span class="w-2.5 h-2.5 rounded-sm agenda-swatch-absence inline-block"></span> Ausencia </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-subtle text-muted-color border border-line"> <span class="w-2.5 h-2.5 rounded-sm agenda-swatch-unavailable inline-block"></span> No disponible </span>
        </div>

        <!-- Calendar container -->
        <div class="flex-1 bg-card rounded-2xl shadow-sm border border-line p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full">
                <template #eventContent="arg">
                    <AgendaEvent :arg="arg" />
                </template>
            </FullCalendar>
        </div>
```

- [ ] **Step 8: Remove the obsolete scoped style block**

Delete the last block of the file:

```html
<style scoped>
/* Calendar Medical Clean theme is loaded from @/assets/calendar-medical.css */
/* Only view-specific overrides go here */
</style>
```

- [ ] **Step 9: Verify the view**

Run: `rg -n "setProperty\(|\[Presente\]|\[Falta|esLocale|tippy|calendar-medical|backgroundColor|borderColor|textColor|extendedProps\.creado_por_nombre|extendedProps\.creado_en" src/views/pages/historias/Turnos.vue`
Expected: no output (exit code 1).

Run: `npm run lint`
Expected: exits 0 with no errors reported.

Run: `npm run test`
Expected: all test files pass, 0 failed.

Run: `npm run build`
Expected: `✓ built in …` with no errors.

Run: `npm run check:tokens`
Expected: `check:tokens OK`.

- [ ] **Step 10: Manual smoke check (dev server)**

Run `npm run dev` and open `/turnos` (the Turnos route):
- the week view shows tinted cards with time + patient + motivo;
- in a slot with 3+ turnos, the "+N más" link opens a themed popover, and clicking a card opens the detail modal;
- the gray hatch shows outside availability;
- a full-day absence shows the reddish hatch with "AUSENCIA";
- toggle dark mode and confirm there are no light surfaces.

Stop the server.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/views/pages/historias/Turnos.vue
git commit -m "refactor(turnos): migrate Turnos agenda to shared calendar setup"
```

---

### Task 6: Migrate CalendarioGrupo.vue

**Files:**
- Modify: `frontend/src/views/pages/turnos/CalendarioGrupo.vue`

- [ ] **Step 1: Replace the imports**

Replace:

```js
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import api from '@/api/axios';
import { fechaBonitaCompleta } from '@/utils/formatDate';
import '@/assets/calendar-theme.css';
```

with:

```js
import FullCalendar from '@fullcalendar/vue3';
import api from '@/api/axios';
import { fechaBonitaCompleta } from '@/utils/formatDate';
import AgendaEvent from '@/components/agenda/AgendaEvent.vue';
import { useAgendaCalendar } from '@/composables/useAgendaCalendar';
```

(`import { ref, onMounted, reactive } from 'vue';` and `useRoute` stay; `reactive` is still used by the form state.)

- [ ] **Step 2: Delete the local locale**

Delete the whole `const esLocale = { … };` block.

- [ ] **Step 3: Replace `calendarOptions`**

Replace the whole `const calendarOptions = reactive({ … });` block, through the `});` after `eventDidMount`, with:

```js
const calendarOptions = useAgendaCalendar({
    expandRows: true,
    stickyHeaderDates: true,
    events: eventos,
    dateClick(info) {
        if (!puedeEditarGrupal()) return;
        nuevoTurno.fecha = toLocalDateTimeString(info.date);
        nuevoTurno.modo_creacion = 'simple';
        nuevoTurno.fecha_base = toLocalDateString(info.date);
        nuevoTurno.hora_tanda = toLocalTimeString(info.date);
        nuevoTurno.dias_tanda = [jsDayToMondayIndex(info.date.getDay())];
        nuevoTurno.cantidad_tanda = 4;
        nuevoTurno.pacienteBusqueda = '';
        nuevoTurno.paciente = null;
        nuevoTurno.motivo = '';
        nuevoTurno.observaciones = '';
        nuevoTurno.duracion_minutos = DURACION_GRUPAL_DEFAULT;
        pacientes.value = [];
        modalNuevoVisible.value = true;
    },
    eventClick(info) {
        const tipo = info.event.extendedProps.tipo;
        if (tipo === 'ausencia_bg') return;

        turnoSeleccionado.value = {
            id: info.event.extendedProps.turnoId || info.event.id,
            turnoId: info.event.extendedProps.turnoId,
            tipo,
            paciente: info.event.extendedProps.paciente,
            dni: info.event.extendedProps.dni,
            cobertura: info.event.extendedProps.cobertura,
            nro_certificado: info.event.extendedProps.nro_certificado,
            profesional: info.event.extendedProps.profesional,
            description: info.event.extendedProps.description,
            observaciones: info.event.extendedProps.observaciones,
            ausencia: info.event.extendedProps.ausencia,
            estado_asistencia: info.event.extendedProps.estado_asistencia || (info.event.extendedProps.ausencia ? info.event.extendedProps.ausencia : 'programado'),
            paciente_id: info.event.extendedProps.paciente_id,
            creadoPorNombre: info.event.extendedProps.creadoPorNombre,
            creadoEn: info.event.extendedProps.creadoEn,
            start: info.event.start,
            end: info.event.end,
            editable: Boolean(info.event.extendedProps.editable)
        };

        ausenciasConteoDetalle.value = null;
        if (info.event.extendedProps.paciente_id) {
            api.get(`/pacientes/${info.event.extendedProps.paciente_id}/ausencias`, { withCredentials: true })
                .then((res) => {
                    ausenciasConteoDetalle.value = res.data;
                })
                .catch((err) => console.error(err));
        }

        mostrarModal.value = true;
    }
});
```

- [ ] **Step 4: Replace `crearEventoIndividual` and `crearEventoGrupal`**

Replace both functions with:

```js
function crearEventoIndividual(t) {
    const estadoAsistencia = t.estado_asistencia || (t.ausencia ? t.ausencia : 'programado');
    return {
        id: `ind-${t.id}`,
        title: t.paciente || '',
        start: t.start,
        end: t.end,
        extendedProps: {
            tipo: 'turno_individual',
            turnoId: t.id,
            paciente: t.paciente,
            dni: t.dni,
            cobertura: t.cobertura,
            nro_certificado: t.nro_certificado ?? t.nro_cobertura,
            profesional: t.profesional,
            description: t.description || '',
            observaciones: t.observaciones,
            ausencia: t.ausencia,
            estado_asistencia: estadoAsistencia,
            paciente_id: t.paciente_id,
            creadoPorNombre: t.creado_por_nombre,
            creadoEn: t.creado_en,
            editable: false
        }
    };
}

function crearEventoGrupal(t) {
    const estadoAsistencia = t.estado_asistencia || (t.ausencia ? t.ausencia : 'programado');
    const grupoNombre = t.grupo_nombre || grupo.value?.nombre || '';
    return {
        id: `grp-${t.id}`,
        title: t.paciente || '',
        start: t.start,
        end: t.end,
        extendedProps: {
            tipo: 'turno_grupal',
            turnoId: t.id,
            paciente: t.paciente,
            dni: t.dni,
            cobertura: t.cobertura,
            nro_certificado: t.nro_certificado ?? t.nro_cobertura,
            profesional: `Grupo: ${grupoNombre}`,
            grupoNombre,
            description: t.description || '',
            observaciones: t.observaciones,
            ausencia: t.ausencia,
            estado_asistencia: estadoAsistencia,
            paciente_id: t.paciente_id,
            creadoPorNombre: t.creado_por_nombre,
            creadoEn: t.creado_en,
            editable: Boolean(t.editable)
        }
    };
}
```

- [ ] **Step 5: Strip the colors from the absence events**

In `crearEventosAusencia`, replace:

```js
            title: `No disponible: ${a.nombre_usuario}`,
            start: a.fecha_inicio,
            end: a.fecha_fin,
            backgroundColor: 'rgba(239,68,68,0.12)',
            borderColor: '#EF4444',
            textColor: '#991B1B',
            classNames: ['evento-ausencia'],
            extendedProps: { tipo: 'ausencia', profesional: a.nombre_usuario, description: a.motivo || '' }
```

with:

```js
            title: `No disponible: ${a.nombre_usuario}`,
            start: a.fecha_inicio,
            end: a.fecha_fin,
            extendedProps: { tipo: 'ausencia', tipoEvento: 'No disponible', profesional: a.nombre_usuario, description: a.motivo || '' }
```

In the full-day background row, replace:

```js
            classNames: ['ausencia-background'],
            backgroundColor: 'rgba(156, 163, 175, 0.25)',
            extendedProps: { tipo: 'ausencia_bg' }
```

with:

```js
            extendedProps: { tipo: 'ausencia_bg' }
```

- [ ] **Step 6: Replace the legend and the calendar container in the template**

In the header, replace the three legend `<span>`s inside `<div class="flex items-center gap-4 flex-wrap">` (Individual, Grupal with dashed border, Ausencia) with:

```html
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-highlight text-primary text-xs font-medium"> <span class="w-2 h-2 rounded-full bg-primary inline-block"></span> Programado </span>
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-presente-bg text-status-presente-fg text-xs font-medium"> <span class="w-2 h-2 rounded-full bg-status-presente-fg inline-block"></span> Presente </span>
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-con-aviso-bg text-status-con-aviso-fg text-xs font-medium"> <span class="w-2 h-2 rounded-full bg-status-con-aviso-fg inline-block"></span> Falta con aviso </span>
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-sin-aviso-bg text-status-sin-aviso-fg text-xs font-medium"> <span class="w-2 h-2 rounded-full bg-status-sin-aviso-fg inline-block"></span> Falta sin aviso </span>
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-subtle text-muted-color border border-line text-xs font-medium"> <i class="pi pi-users text-[10px]"></i> Grupal </span>
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-subtle text-muted-color border border-line text-xs font-medium"> <span class="w-2 h-2 rounded-sm agenda-swatch-absence inline-block"></span> Ausencia </span>
```

Replace the calendar container:

```html
        <div class="flex-1 bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-[#E0F2FE] dark:border-slate-700 p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>
```

with:

```html
        <div class="flex-1 bg-card rounded-2xl shadow-sm border border-line p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full">
                <template #eventContent="arg">
                    <AgendaEvent :arg="arg" />
                </template>
            </FullCalendar>
        </div>
```

The header group swatch (`:style="{ backgroundColor: grupo?.color || '#0891B2' }"`) is group data, not a status color, and stays.

- [ ] **Step 7: Remove the obsolete scoped style block**

Delete:

```html
<style scoped>
/* Calendar Medical Clean theme is loaded from @/assets/calendar-medical.css */
</style>
```

- [ ] **Step 8: Verify the view**

Run: `rg -n "setProperty\(|\[Presente\]|\[Falta|esLocale|tippy|calendar-medical|borderColor|textColor|extendedProps\.creado_por_nombre|extendedProps\.creado_en|eventMaxStack" src/views/pages/turnos/CalendarioGrupo.vue`
Expected: no output (exit code 1).

Run: `rg -n "backgroundColor" src/views/pages/turnos/CalendarioGrupo.vue`
Expected: one match, the header group swatch `:style="{ backgroundColor: grupo?.color || '#0891B2' }"`.

Run: `rg -n "creadoPorNombre" src/views/pages/turnos/CalendarioGrupo.vue`
Expected: the two event-builder mappings, the `eventClick` read and the modal reads (`turnoSeleccionado.creadoPorNombre`). There are no snake_case extendedProps reads.

Run: `npm run lint && npm run test && npm run build && npm run check:tokens`
Expected:
- lint exits 0;
- all tests pass;
- `✓ built in …`;
- `check:tokens OK`.

- [ ] **Step 9: Manual smoke check (dev server)**

Run `npm run dev` and open a group calendar (`/grupos/<id>/calendario`, reached from the Grupos list):
- grupal cards show the `pi-users` icon and the group name on line 2, with no dashed outline;
- the detail modal shows "Creado por" (key normalization);
- 6+ turnos in one slot collapse into "+N más", and the popover lists them all;
- check dark mode.

Stop the server.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/views/pages/turnos/CalendarioGrupo.vue
git commit -m "refactor(turnos): migrate CalendarioGrupo to shared calendar setup"
```

---

### Task 7: Migrate ModuloRehabilitacion.vue

**Files:**
- Modify: `frontend/src/views/pages/turnos/ModuloRehabilitacion.vue`

- [ ] **Step 1: Replace the imports**

Replace:

```js
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import api from '@/api/axios';
import { fechaBonitaCompleta } from '@/utils/formatDate';
import '@/assets/calendar-theme.css';
```

with:

```js
import FullCalendar from '@fullcalendar/vue3';
import api from '@/api/axios';
import { fechaBonitaCompleta } from '@/utils/formatDate';
import AgendaEvent from '@/components/agenda/AgendaEvent.vue';
import { useAgendaCalendar } from '@/composables/useAgendaCalendar';
```

- [ ] **Step 2: Delete the local locale**

Delete the whole `const esLocale = { … };` block.

- [ ] **Step 3: Replace `calendarOptions`, `hexToRgba` and `mapEvento`**

Replace everything from `const calendarOptions = reactive({` through the end of `function mapEvento(t) { … }` with the block below. That span includes `calendarOptions`, `REHAB_COLOR_DEFAULT`, `hexToRgba` and `mapEvento`.

```js
const calendarOptions = useAgendaCalendar({
    events: eventos,
    dateClick(info) {
        if (!canEdit()) return;
        nuevo.modo_creacion = 'simple';
        nuevo.fecha_inicio = toLocalDateTimeString(info.date);
        nuevo.fecha_base = toLocalDateString(info.date);
        nuevo.hora_tanda = toLocalTimeString(info.date);
        nuevo.dias_tanda = [jsDayToMondayIndex(info.date.getDay())];
        nuevo.cantidad_tanda = 4;
        nuevo.paciente = null;
        nuevo.pacienteBusqueda = '';
        nuevo.motivo = '';
        nuevo.observaciones = '';
        nuevo.duracion_minutos = DURACION_GRUPAL_DEFAULT;
        pacientes.value = [];
        if (filtroGrupoId.value) nuevo.grupo_id = filtroGrupoId.value;
        modalNuevoVisible.value = true;
    },
    eventClick(info) {
        seleccionado.value = {
            id: info.event.extendedProps.turnoId || info.event.id,
            turnoId: info.event.extendedProps.turnoId,
            grupo_nombre: info.event.extendedProps.grupoNombre,
            paciente: info.event.extendedProps.paciente,
            dni: info.event.extendedProps.dni,
            cobertura: info.event.extendedProps.cobertura,
            nro_certificado: info.event.extendedProps.nro_certificado,
            paciente_id: info.event.extendedProps.paciente_id,
            description: info.event.extendedProps.description,
            observaciones: info.event.extendedProps.observaciones,
            ausencia: info.event.extendedProps.ausencia,
            estado_asistencia: info.event.extendedProps.estado_asistencia || (info.event.extendedProps.ausencia ? info.event.extendedProps.ausencia : 'programado'),
            editable: Boolean(info.event.extendedProps.editable),
            creadoPorNombre: info.event.extendedProps.creadoPorNombre,
            creadoEn: info.event.extendedProps.creadoEn,
            start: info.event.start,
            end: info.event.end
        };
        detalleVisible.value = true;
    }
});

// Fallback group color for the card's left bar; status colors come from tokens.
const REHAB_COLOR_DEFAULT = '#059669';

function mapEvento(t) {
    const estadoAsistencia = t.estado_asistencia || (t.ausencia ? t.ausencia : 'programado');
    return {
        id: `rehab-${t.id}`,
        title: t.paciente || '',
        start: t.start,
        end: t.end,
        extendedProps: {
            turnoId: t.id,
            grupo_id: t.grupo_id,
            grupoNombre: t.grupo_nombre,
            grupoColor: t.color || REHAB_COLOR_DEFAULT,
            paciente: t.paciente,
            dni: t.dni,
            cobertura: t.cobertura,
            nro_certificado: t.nro_certificado ?? t.nro_cobertura,
            description: t.description,
            observaciones: t.observaciones,
            ausencia: t.ausencia,
            estado_asistencia: estadoAsistencia,
            paciente_id: t.paciente_id,
            creadoPorNombre: t.creado_por_nombre,
            creadoEn: t.creado_en,
            editable: Boolean(t.editable)
        }
    };
}
```

The detail modal keeps reading `seleccionado.grupo_nombre`, which is still populated from `extendedProps.grupoNombre`, and `seleccionado.creadoPorNombre`.

- [ ] **Step 4: Replace the calendar container in the template**

Replace:

```html
        <div class="flex-1 bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-[#E0F2FE] dark:border-slate-700 p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>
```

with:

```html
        <div class="flex-1 bg-card rounded-2xl shadow-sm border border-line p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full">
                <template #eventContent="arg">
                    <AgendaEvent :arg="arg" />
                </template>
            </FullCalendar>
        </div>
```

- [ ] **Step 5: Remove the obsolete scoped style block**

Delete:

```html
<style scoped>
/* Calendar Medical Clean theme is loaded from @/assets/calendar-medical.css */
</style>
```

- [ ] **Step 6: Verify the view**

Run: `rg -n "setProperty\(|\[Presente\]|\[Falta|esLocale|hexToRgba|calendar-medical|backgroundColor|borderColor|textColor|extendedProps\.creado_por_nombre|extendedProps\.creado_en|extendedProps\.color\b|extendedProps\.grupo_nombre" src/views/pages/turnos/ModuloRehabilitacion.vue`
Expected: no output (exit code 1).

Run: `npm run lint && npm run test && npm run build && npm run check:tokens`
Expected:
- lint exits 0;
- all tests pass;
- `✓ built in …`;
- `check:tokens OK`.

- [ ] **Step 7: Manual smoke check (dev server)**

Run `npm run dev` and open Módulo Rehabilitación:
- each card's left bar uses its group color, while the background tint and the time color follow the status (mark one turno "Presente" and check it turns green with the group bar kept);
- a cohort of 6+ in one slot collapses into "+N más";
- the tooltip shows "Grupo: <nombre>";
- check dark mode.

Stop the server.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/pages/turnos/ModuloRehabilitacion.vue
git commit -m "refactor(turnos): migrate ModuloRehabilitacion to shared calendar setup"
```

---

### Task 8: Final verification

**Files:**
- Modify: `frontend/scripts/check-tokens.mjs` (comment only)

- [ ] **Step 1: Update the allowlist comment**

In `frontend/scripts/check-tokens.mjs`, replace:

```js
// Spec 2 (appointment calendar) files, until Spec 2 lands.
```

with:

```js
// Calendar views: the calendar itself is tokenized (Spec 2), but their create/detail modals
// still hold legacy color classes, which are out of Spec 2 scope.
```

The `ALLOWLIST` set itself is unchanged.

- [ ] **Step 2: Run the full suite**

Run: `npm run test`
Expected: all test files pass, 0 failed. This includes `agendaEventStyle.test.js` (24), `AgendaEvent.test.js` (9) and `useAgendaCalendar.test.js` (12).

Run: `npm run lint`
Expected: exits 0 with no errors reported.

Run: `npm run build`
Expected: `✓ built in …` with no errors.

Run: `npm run check:tokens`
Expected: `check:tokens OK` (0 violations).

- [ ] **Step 3: Leftover checks**

Run: `rg -n "setProperty\('(background-color|border-color|color)'" src`
Expected: no output. No `!important` inline color overrides are left.

Run: `rg -n "!important" src/assets/calendar-theme.css`
Expected: no output.

Run: `rg -n "\[Presente\]|\[Falta Con Aviso\]|\[Falta Sin Aviso\]" src`
Expected: no output. No status title prefixes are left.

Run: `rg -n "calendar-medical" src`
Expected: no output.

Run: `rg --files src/assets | rg calendar`
Expected: exactly `src/assets/calendar-theme.css` (`src\assets\calendar-theme.css` on Windows).

Run: `rg -n "#[0-9a-fA-F]{3,8}\b" src/assets/calendar-theme.css src/components/agenda/AgendaEvent.vue`
Expected: no output.

Run: `rg -n "extendedProps\.creado_por_nombre|extendedProps\.creado_en" src/views`
Expected: no output. Every view reads `creadoPorNombre` / `creadoEn`.

Run: `rg -n "fecha_inicio" src/components/agenda src/composables`
Expected: no output. The shared units use `start` / `end`.

- [ ] **Step 4: Manual visual pass by the user (spec §5)**

Ask the user to check the three agendas in light and dark mode:
- a slot with 6+ concurrent turnos, including the "+N más" popover and clicking an item from it;
- absences (foreground card and full-day hatch);
- the unavailability hatch in Turnos;
- grupal events (icon, group name, no dashed outline);
- the Rehab group bar color;
- tooltips (themed, with the status label).

- [ ] **Step 5: Commit**

```bash
git add frontend/scripts/check-tokens.mjs
git commit -m "chore(agenda): update token guard allowlist note"
```

---

## Self-review against the spec

| Spec item | Covered by |
|---|---|
| §2.1 Card "A": status tint, 4px left bar, time in status color with tabular numbers, semibold patient, muted one-line motivo | Task 2 (`AgendaEvent.vue`), Task 4 (`.evt-card`, `.evt-time`, `.evt-name`, `.evt-detail`) |
| §2.2 `eventMaxStack: 2`, "+N" themed popover with clickable cards, `dayMaxEventRows` in month, 6+ concurrent | Task 3 (options + test), Task 4 (popover / more-link CSS), Tasks 5-7 manual checks |
| §2.3 Statuses from `--cau-status-*`; programado and unknown use primary + highlight; group color only on the bar (Rehab) | Task 1 (`statusKey` fallback, `barColor`), Task 4 (`.evt`, `.evt-*`), Task 7 (`grupoColor`) |
| §2.4 No status text in titles; status in tooltip and aria-label; `sin_aviso` line-through | Tasks 5-7 (titles = patient), Task 2 (aria-label, `evt-name--struck`), Task 3 (tooltip status) |
| §2.5 Grupal: `pi pi-users`, group name on line 2, no dashed outline (`grupal` and `turno_grupal`) | Task 1 (`isGrupal`), Task 2, Tasks 5-6 (`grupoNombre`); dashed CSS deleted with `calendar-medical.css` |
| §2.6 Month compact single line with dot | Task 2 (`evt-card--month`), Task 4 |
| §2.7 Gray hatch (Turnos) and reddish "Ausencia" hatch, token-based | Task 1 (bg classes), Task 2 (label), Task 4 (`bg-hatch-*`), Tasks 5-6 (bg props stripped) |
| §2.8 Tippy with token theme: patient, DNI, range, status, motivo, professional or group | Task 3 (`buildTooltipContent`, theme `agenda`), Task 4 (tippy CSS) |
| §3 Units: helpers, AgendaEvent, composable, calendar-theme.css | Tasks 1-4 |
| §3 Views: slot + composable; removed overrides, color props, prefixes, locale; kept loading, modals, `duracionTurno` watch, availability bg | Tasks 5-7 |
| §3 `creadoPorNombre` normalization | Tasks 5-7 (builders + `eventClick`), Task 8 `rg` check |
| §4 Out of scope respected (no backend, modals only key rename, no AgendaProfesional, no FC upgrade) | Global Constraints |
| §5 Tests and `test` / `build` / `lint` / `check:tokens` | Tasks 1-3 (TDD), Task 8 |
| §5 Manual visual check | Tasks 5-7 smoke checks, Task 8 Step 4 |
| §6 Risk: FC 5.11 slot + `eventMaxStack` | "FullCalendar 5.11 verification" header |
