# Agenda turnos redesign — Design (Spec 2)

**Branch:** `feat/agenda-turnos`. It is cut from `feat/visual-foundation` and depends on that branch's tokens. The PRs are chained.
**Builds on:** `docs/superpowers/specs/2026-09-23-visual-foundation-design.md` (semantic tokens, `status.css`, CauPreset).

## 1. Problem

Appointments in the FullCalendar agendas are hard to read:

- In dark mode, the text is hard to read and some surfaces render broken or light.
- With several concurrent appointments, events are squeezed into unreadable columns.
- The three calendar views (`views/pages/historias/Turnos.vue`, `views/pages/turnos/CalendarioGrupo.vue`, `views/pages/turnos/ModuloRehabilitacion.vue`) duplicate their FullCalendar config and color logic.
- In `eventDidMount`, the views force hardcoded hex colors (`#C0392B`, `#E67E22`, `#059669`, `#0891B2`, …) with `!important`. This bypasses the app's status tokens and ignores dark mode.
- The status is also prepended to the title as text (`[Presente]`, `[Falta Con Aviso]`, `[Falta Sin Aviso]`).
- `assets/calendar-medical.css` keeps a parallel set of hex values for light and dark.
- It never themes FullCalendar's own `--fc-*` variables, so the "+more" popover and the non-business surfaces stay light in dark mode.

## 2. Decisions (approved with the user)

1. **Event card style "A": tinted card with a left bar.**
   - The background is the status tint.
   - The left bar is 4px wide.
   - Line 1 shows the time, colored with the status color and using tabular numbers, followed by the patient name in semibold.
   - Line 2 shows the motivo in muted color, as a single line with an ellipsis.
2. **Concurrency.**
   - In timeGrid views, at most 2 events are shown side by side (`eventMaxStack: 2`). The rest collapse into FullCalendar's "+N" link.
   - The link opens a themed popover that lists every event of that slot, using the same card. Each item stays clickable and opens the detail modal.
   - In dayGrid month, use `dayMaxEventRows` with the same themed popover.
   - This must support 6+ concurrent appointments; a rehab group can put a whole cohort in one slot.
3. **Color semantics.**
   - The status color comes from `estado_asistencia`:
     - `presente`, `con_aviso` and `sin_aviso` use the existing `--cau-status-*` tokens;
     - `programado` (and any unknown value) uses the primary teal (`--p-primary-color`), with the highlight tint as background.
   - The `--cau-status-programado-*` slate token stays in use for badges. It is not used in the calendar, where it would look washed out.
   - When the event carries a group color, as in Módulo Rehabilitación, the **left bar uses the group color** and identifies the group. The background tint and the time color still follow the status.
   - With no group color, the left bar uses the status color.
4. **No status text in titles.** The status is exposed as text in the tooltip and in the card's `aria-label`. `sin_aviso` also shows the patient name with a soft line-through, so the status does not depend on color alone.
5. **Group appointments** (`tipo === 'grupal'`), in Turnos and CalendarioGrupo:
   - a small `pi pi-users` icon before the name;
   - line 2 shows the group name;
   - the dashed outline is removed.
6. **Month view:** a compact single line with a status dot, the time and the patient.
7. **Background layers:**
   - Unavailability (Turnos only, as today) is a subtle gray hatch.
   - A full-day absence is a soft reddish hatch labeled "Ausencia".
   - Both are theme-aware and use tokens.
8. **Tooltip:**
   - It keeps tippy.js, with a theme driven by tokens.
   - It shows the patient, DNI, time range, status label, motivo, and the professional or group.

## 3. Architecture

New units (all under `frontend/src/`):

| Unit | Responsibility |
|---|---|
| `components/agenda/agendaEventStyle.js` | Pure helpers. `statusKey(estado_asistencia)` → `'programado' \| 'presente' \| 'con-aviso' \| 'sin-aviso'`, with `programado` as the fallback. `statusLabel(key)` returns the Spanish label: Programado / Presente / Falta con aviso / Falta sin aviso. `eventClassNames(event)` returns e.g. `['evt', 'evt-presente', 'evt-grupal']`. `barColor(event)` returns the group hex, or `null` to use the status color. |
| `components/agenda/AgendaEvent.vue` | The card rendered through FullCalendar's `#eventContent` slot. Props: `arg` (the FullCalendar `eventContent` arg). It reads `arg.event` and `arg.view.type`, and renders the timeGrid or month variant. It sets `aria-label` and the group icon, and sets `--evt-bar` inline only when a group color exists. |
| `composables/useAgendaCalendar.js` | `useAgendaCalendar(overrides)` returns a reactive FullCalendar options object with the shared base: plugins (dayGrid, timeGrid, interaction), `es` locale, `initialView: 'timeGridWeek'`, header toolbar, `slotMinTime '07:00:00'`, `slotMaxTime '22:00:00'`, `allDaySlot: false`, `height: '100%'`, `eventMaxStack: 2`, `dayMaxEventRows`, `eventClassNames`, and an `eventDidMount` that only attaches the tippy tooltip. Overrides are merged, e.g. `dateClick`, `eventClick`, `events`, and the slot durations Turnos rebinds from `duracionTurno`. |
| `assets/calendar-theme.css` | Replaces `calendar-medical.css`. It sets FullCalendar's `--fc-*` variables from semantic tokens: border, page background, neutral background, today background, list and popover backgrounds. It also defines `.evt-*` status classes as CSS custom properties (`--evt-fg`, `--evt-bg`, `--evt-bar`), the popover and "+N" link styling, the hatch layers, and the tippy theme. It contains no raw hex colors except where the token guard allows them. |

View changes:

- **All three views** adopt `useAgendaCalendar` and `<template #eventContent="arg"><AgendaEvent :arg="arg" /></template>`.
- **Removed from the views:**
  - `eventDidMount` color overrides;
  - `backgroundColor` / `borderColor` / `textColor` event props, except the group color passed as an `extendedProps` value;
  - status title prefixes;
  - duplicated locale and toolbar config.
- **Kept in each view:** its data loading, modals, and view-specific behavior (Turnos: `duracionTurno` watch and availability background events).
- **Normalized:** all views use the extendedProps key `creadoPorNombre`. Today Turnos uses `creadoPorNombre` while CalendarioGrupo and ModuloRehabilitacion use `creado_por_nombre`, and each view's detail modal must read the key it stores.

## 4. Out of scope

- No backend or API response changes. `/api/turnos/*` stays as is.
- No changes to the create and detail modals beyond reading the normalized key.
- `views/pages/Agenda/AgendaProfesional.vue` is a DataTable, not a calendar, and is not changed.
- No FullCalendar version upgrade (stay on 5.11.x).

## 5. Testing

- Vitest unit tests:
  - `agendaEventStyle.js`: every status key, the unknown-status fallback, `barColor` with and without a group color, and the class names for `grupal`.
  - `AgendaEvent.vue`:
    - it renders the time, patient and motivo;
    - it renders the month variant as a single line;
    - it shows the grupal icon and the group name;
    - its `aria-label` contains the status label;
    - `sin_aviso` gets the line-through class;
    - a group color sets `--evt-bar`.
  - `useAgendaCalendar`: the base options (`eventMaxStack: 2`, time range, locale) and the merging of overrides.
- `npm run test`, `npm run build`, `npm run lint` and `npm run check:tokens` all pass (token guard: 0 violations, including the new CSS).
- Manual visual check by the user of the three agendas, in light and dark mode:
  - a slot with 6+ concurrent events, including the "+N" popover;
  - absences;
  - unavailability hatch;
  - grupal events;
  - the rehab group bar color.

## 6. Risks

- FullCalendar 5.11 support for the `#eventContent` Vue slot and for `eventMaxStack` in timeGrid must be confirmed against the installed version before implementation.
- The calendar views have no tests today. Removing the inline color overrides can surface edge cases, which is why the manual visual pass is required.
