# Historia Clinica CAU Full API

Flask + Vue + MySQL + Nginx + Docker for clinical records, appointments, and optional blockchain audit (BFA).

## Quick reference

- Package manager: npm (frontend)
- Main stack command: `docker compose --env-file .env up -d --build`
- Stop stack: `docker compose down`
- API health: `curl -I http://localhost/api/health/public`
- Frontend lint: `cd frontend && npm run lint`
- User-route smoke test: `cd frontend/tests && bash test_usuarios.sh` (requires local API login data)

## Universal rules

- Keep API contracts under `/api/*` backward-compatible unless migration is explicit.
- Keep auth model based on `Flask-Login` session cookies (`withCredentials` on frontend requests).
- Keep RBAC role keys exact: `director`, `profesional`, `administrativo`, `area`.
- Any DB schema change must update both `db/init.sql` and all affected backend/frontend callers in same change.
- Never hardcode secrets; use `.env` variables only.

## Detailed instructions

- [Architecture](docs/agents/architecture.md)
- [Backend Flask](docs/agents/backend-flask.md)
- [Frontend Vue](docs/agents/frontend-vue.md)
- [Operations and deploy](docs/agents/operations.md)
- [Testing and validation](docs/agents/testing-and-validation.md)
