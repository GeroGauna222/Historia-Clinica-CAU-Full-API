# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Historia Clínica CAU is a web system for managing unified clinical records and medical scheduling. It integrates a Flask REST API backend, a Vue 3 (Vite) frontend, MySQL, Nginx, Docker, and optional blockchain integrity auditing via BFA (Blockchain Federal Argentina / Geth).

## Stack

- **Backend**: Flask (Python), Flask-Login (session auth), Flask-Mail, Flask-CORS, Flask-Talisman, mysql-connector-python, web3, Gunicorn (production), ReportLab
- **Frontend**: Vue 3, Vite, PrimeVue 4, Pinia, Vue Router, FullCalendar, Axios, Tailwind CSS
- **DB**: MySQL 8.0
- **Infra**: Docker Compose, Nginx reverse proxy, BFA/Geth node (dev mode by default)

## Development Commands

### Full stack (Docker)
```bash
docker compose --env-file .env up -d --build   # Start all services
docker compose down                              # Stop
docker compose logs -f web                       # Flask backend logs
docker compose logs -f frontend                  # Frontend logs
docker compose logs -f db                        # MySQL logs
```

### Frontend only (outside Docker)
```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173 (proxies /api to localhost:5000)
npm run build
npm run lint       # ESLint + auto-fix
```

### Backend only (outside Docker)
```bash
cd backend_flask/app
pip install -r requirements.txt
FLASK_APP=main.py flask run   # dev mode, port 5000
```

### Tests
```bash
# Backend unit tests (no DB required — uses mocked connections)
cd backend_flask && python -m pytest tests/ -q

# Frontend smoke test (requires running API + jq)
cd frontend/tests && bash test_usuarios.sh

# API health check
curl -I http://localhost/api/health/public
```

### Access
- **App**: `http://localhost` (via Nginx)
- **API**: `http://localhost/api`

## Architecture

```
Client (Vue 3)
    ↓ HTTP
Nginx (:80)
  ├── /uploads/ → served directly from shared Docker volume (20MB max, 30-day cache)
  ├── /api/ → Flask (:5000)
  │     └── MySQL (:3306) + BFA/Geth (:8545, optional)
  └── / → Vue frontend (:80 container)
```

### Backend structure (`backend_flask/app/`)

| Path | Purpose |
|------|---------|
| `__init__.py` | App factory: Flask, CORS, LoginManager, Mail, Talisman, blueprint registration |
| `auth.py` | `Usuario` model (Flask-Login `UserMixin`), filters `activo=1` |
| `database.py` | `get_connection()` — mysql-connector with retry logic |
| `config.py` | `Config` class — all settings via env vars |
| `main.py` | Entry point (imports `app` from `__init__`; Gunicorn targets this in production) |
| `routes/` | One Blueprint per domain (11 total): `auth`, `usuarios`, `pacientes`, `historias`, `turnos`, `grupos`, `disponibilidades`, `ausencias`, `dashboard`, `blockchain`, `health` |
| `utils/permisos.py` | `@requiere_rol('director', ...)` decorator |
| `utils/hashing.py` | SHA-256 helpers for clinical record integrity |
| `utils/validacion.py` | `password_valida()`, `validar_email()` |
| `utils/bfa_client.py` | Web3 client for BFA interaction |

All API routes are prefixed `/api/...` internally in each blueprint — no `url_prefix` is set at registration.

### Frontend structure (`frontend/src/`)

| Path | Purpose |
|------|---------|
| `api/axios.js` | Axios instance: `withCredentials: true`, `baseURL` from `VITE_API_URL` or `/api` (relative) |
| `stores/user.js` | Pinia store — user state, `fetchUser()` validates session against backend |
| `router/index.js` | Vue Router with `meta.roles` guards; `beforeEach` calls `fetchUser()` for auth check |
| `service/` | One service file per domain (e.g. `turnosService.js`, `historiaService.js`) |
| `views/pages/` | Feature views organized by domain (`auth/`, `historias/`, `turnos/`, `usuarios/`, `grupos/`, `disponibilidades/`, `evolucion/`) |
| `utils/eventBus.js` | Event bus for `user:updated` / `user:loggedOut` events |

### Database (`db/init.sql`)

10 tables: `usuarios`, `pacientes`, `historias` (1-per-patient), `evoluciones`, `evolucion_archivos`, `turnos`, `ausencias`, `disponibilidades`, `grupos_profesionales`, `grupo_miembros`, `auditorias_blockchain`. Schema changes must update `init.sql` and all affected backend/frontend callers in the same change.

### Test infrastructure (`backend_flask/tests/`)

Tests use `monkeypatch` to swap `get_connection` with `FakeConnection`/`FakeCursor` from `conftest.py` — no real database needed. Test files cover auth, RBAC, turnos, and disponibilidades.

## RBAC Roles

Roles are stored in `usuarios.rol` (DB enum) and enforced in two places:
- **Backend**: `@requiere_rol('director', 'profesional', ...)` decorator
- **Frontend**: `meta: { roles: [...] }` on routes + `router.beforeEach` guard

| Role | Access |
|------|--------|
| `director` | Full access: users, groups, audit, administration |
| `profesional` | Personal schedule, availability, clinical features |
| `administrativo` | Daily operations (patients, appointments) |
| `area` | Logical user representing a specialty/module; participates in group agendas |

## Key Patterns

- **Session-based auth (no JWT)**: Flask-Login sessions. Frontend uses `withCredentials: true`. The Pinia `userStore.fetchUser()` validates session against the backend; `localStorage` is no longer used for auth/role checks.
- **Database access**: All routes call `get_connection()` directly (no ORM). Always close cursor and connection (prefer `try/finally`). Use parameterized SQL (`%s` placeholders).
- **File uploads**: Files go to `/app/uploads/evoluciones/<evolucion_id>/...` (Flask) shared via Docker volume `uploads_data` with Nginx, which serves `/uploads/` directly. 20MB max.
- **Blockchain integrity**: `utils/hashing.py` generates SHA-256 hashes stored in DB; `blockchain_routes.py` / `bfa_client.py` optionally publish hashes to BFA. The BFA node runs in `--dev` mode by default.
- **Password hashing**: `werkzeug.security.generate_password_hash` with `method="scrypt"`.
- **Cookie security**: `SESSION_COOKIE_SECURE` and `REMEMBER_COOKIE_SECURE` are configurable per environment (HTTP dev / HTTPS prod).
- **Frontend services pattern**: Backend calls must go through `src/service/*` modules; components consume services/stores, not axios directly.

## Universal Rules

- Keep API contracts under `/api/*` backward-compatible unless migration is explicit.
- Keep RBAC role keys exact: `director`, `profesional`, `administrativo`, `area`.
- Any DB schema change must update both `db/init.sql` and all affected backend/frontend callers in the same change.
- If login/logout flow changes, update all three places together: `views/pages/auth/*`, `stores/user.js`, and router guards.
- Keep payload field names aligned between backend responses and frontend consumers.

## Environment Variables (`.env`)

```env
FLASK_ENV=development|production
SECRET_KEY=
DB_HOST=db   DB_USER=hc_app   DB_PASSWORD=   DB_NAME=hc_bfa
FRONTEND_URL=http://localhost
MAIL_SERVER= MAIL_PORT= MAIL_USE_TLS= MAIL_USERNAME= MAIL_PASSWORD= MAIL_DEFAULT_SENDER=
PRIVATE_KEY_BFA= ADDRESS_BFA= BFA_RPC_URL=http://bfa-node:8545
VITE_API_URL=           # optional override for frontend build
UPLOAD_FOLDER=/app/uploads
```
