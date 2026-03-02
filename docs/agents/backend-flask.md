# Backend Flask guidelines

## Core patterns

- Add API endpoints as blueprints under `backend_flask/app/routes` and register them in `backend_flask/app/__init__.py`.
- Keep endpoint namespace under `/api/*`.
- Use `get_connection()` from `backend_flask/app/database.py` for DB access.
- Always close `cursor` and `conn` (prefer `try/finally` in non-trivial handlers).

## Auth and RBAC

- For protected routes use `@login_required`.
- For role-gated routes use `@requiere_rol(...)` with exact role keys.
- Keep response semantics (`401` unauthorized vs `403` forbidden) aligned with current utilities.

## SQL and data safety

- Use parameterized SQL (`%s` placeholders) for user input.
- If dynamic `IN (...)` is required, generate placeholders safely and bind values.
- Keep DB schema changes synchronized with `db/init.sql`.

## Files, PDF, and uploads

- Existing upload convention is `uploads/evoluciones/<evolucion_id>/...`.
- Keep generated URL shapes compatible with frontend consumers.
- Preserve 20MB upload assumptions (`nginx client_max_body_size` and Flask `MAX_CONTENT_LENGTH`).

## Configuration

- Read secrets and runtime settings from environment variables only.
- Do not commit private keys, mail credentials, or production endpoints.
