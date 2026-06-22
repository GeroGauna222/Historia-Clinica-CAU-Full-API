# Dashboard Inicio Operativo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a role-aware operational home dashboard centered on today's agenda, next agenda event, availability, alerts, absences/blocks, and communications.

**Architecture:** Enrich `/api/dashboard` so role and agenda rules live in Flask, then simplify `Dashboard.vue` to render the returned sections. Keep existing `/api/dashboard/semanal` untouched unless frontend no longer needs it.

**Tech Stack:** Flask, Flask-Login, MySQL queries through `get_connection()`, Vue 3 Composition API, PrimeVue, Axios with `withCredentials`.

---

### Task 1: Backend dashboard payload

**Files:**
- Modify: `backend_flask/app/routes/dashboard_routes.py`
- Test: `backend_flask/tests/test_dashboard_routes.py`

- [ ] Add helper functions for ISO conversion, role checks, day names, event type parsing, and overlap detection.
- [ ] Replace `/api/dashboard` internals with a payload containing `resumen`, `turnos`, `proximo_evento`, `disponibilidad_hoy`, `ausencias_bloqueos`, `alertas`, and `comunicados`.
- [ ] Include institutional comunicados from `comunicados`.
- [ ] Include group posts from `grupo_posteos`, restricted to groups the user can access unless the role is `director` or `administrativo`.
- [ ] Add tests for professional and administrative payloads.
- [ ] Run `cd backend_flask && pytest tests/test_dashboard_routes.py -q`.

### Task 2: Frontend dashboard view

**Files:**
- Modify: `frontend/src/views/Dashboard.vue`

- [ ] Remove generic statistic cards for Pacientes, Usuarios and Evoluciones.
- [ ] Remove the weekly chart from Inicio.
- [ ] Render the new operational summary cards.
- [ ] Render Turnos de Hoy with only hour, patient, professional when global, and Ver historia action.
- [ ] Render Proximo evento de agenda using `proximo_evento`.
- [ ] Render Disponibilidad de hoy.
- [ ] Render Comunicados from both institutional and group sources.
- [ ] Render admin-only alert and ausencias/bloqueos sections.

### Task 3: Validation

**Files:**
- No new files.

- [ ] Run backend dashboard tests.
- [ ] Run `cd frontend && npm run lint`.
- [ ] If practical, start the local frontend and inspect the dashboard visually.
