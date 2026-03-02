# Architecture guidelines

## Project layout

- `backend_flask/app`: Flask app factory-ish module (`__init__.py`), config, auth, DB access, and blueprints.
- `backend_flask/app/routes`: domain routes (`auth`, `usuarios`, `pacientes`, `turnos`, etc.).
- `frontend/src`: Vue 3 app (router, Pinia store, services, views, components).
- `db/init.sql`: full schema bootstrap and seed admin user.
- `nginx/default.conf`: public entrypoint (`/` to frontend, `/api/` to backend).
- `docker-compose.yml`: canonical local/prod-like orchestration.

## Runtime boundaries

- Public traffic enters by `nginx:80`; backend should stay behind `/api` proxy path.
- Auth is session-cookie based (Flask-Login), not JWT.
- Blockchain routes are optional integrations; core clinical flow must work without external chain state.

## Design constraints for changes

- Keep route prefixes and payload fields stable for existing frontend service calls.
- Keep role names and semantics consistent across DB, backend decorators, and router guards.
- Prefer additive changes over destructive rewrites in routes with clinical data (`pacientes`, `historias`, `turnos`).
- If introducing new env vars, document them in root `README.md` and deployment docs.
