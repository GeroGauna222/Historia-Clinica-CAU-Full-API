# Frontend Vue guidelines

## Data access and state

- Use `src/api/axios.js` as the single HTTP client.
- Keep backend calls in `src/service/*` modules; components should consume services/stores.
- Preserve `withCredentials` behavior for session-cookie auth.

## Routing and auth flow

- Keep public routes and guard logic in `src/router/index.js` coherent with backend auth rules.
- Role-gated views must define `meta.roles` using backend role keys.
- If login/logout flow changes, update all three places together:
  - `views/pages/auth/*`
  - `stores/user.js`
  - router guard/localStorage contract (`loggedIn`, `user`)

## UI and domain consistency

- Keep payload field names aligned with backend responses to avoid adapter drift.
- Prefer incremental edits in large views (`Pacientes`, `Turnos`, `Usuarios`) and preserve existing user workflows.
- Reuse shared utils (`src/utils/*`) before duplicating formatting or validation logic.
