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
# Start all services
docker compose --env-file .env up -d --build

# Stop
docker compose down

# View logs
docker compose logs -f web      # Flask backend
docker compose logs -f frontend
docker compose logs -f db
```

### Frontend only (outside Docker)
```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173
npm run build
npm run lint       # ESLint + auto-fix
```
The Vite dev proxy forwards `/api` to `http://localhost:5000`.

### Backend only (outside Docker)
```bash
cd backend_flask/app
pip install -r requirements.txt
FLASK_APP=main.py flask run   # dev mode, port 5000
```
Set `FLASK_ENV=production` to use Gunicorn (3 workers on :5000) instead.

### Access
- **App**: `http://localhost` (via Nginx)
- **API**: `http://localhost/api`

## Architecture

```
Client (Vue 3)
    ↓ HTTP
Nginx (:80)
  ├── /uploads/ → served directly from shared Docker volume
  ├── /api/ → Flask (:5000)
  │     └── MySQL (:3306) + BFA/Geth (:8545, optional)
  └── / → Vue frontend (:80 container)
```

### Backend structure (`backend_flask/app/`)

| Path | Purpose |
|------|---------|
| `__init__.py` | App factory: Flask, CORS, LoginManager, Mail, Talisman, blueprint registration |
| `auth.py` | `Usuario` model (Flask-Login `UserMixin`) |
| `database.py` | `get_connection()` — mysql-connector with retry logic |
| `config.py` | `Config` class — all settings via env vars |
| `routes/` | One Blueprint per domain: `auth_routes`, `usuarios_routes`, `pacientes_routes`, `historias_routes`, `turnos_routes`, `grupos_routes`, `disponibilidades_routes`, `ausencias_routes`, `dashboard_routes`, `blockchain_routes`, `health_routes` |
| `utils/permisos.py` | `@requiere_rol('director', ...)` decorator |
| `utils/hashing.py` | SHA-256 helpers for clinical record integrity |
| `utils/validacion.py` | `password_valida()`, `validar_email()` |
| `utils/bfa_client.py` | Web3 client for BFA interaction |

All API routes are prefixed `/api/...` (enforced at Flask blueprint level, not via `url_prefix`).

### Frontend structure (`frontend/src/`)

| Path | Purpose |
|------|---------|
| `api/axios.js` | Axios instance with `withCredentials: true`, `baseURL` from `VITE_API_URL` or `window.location.origin + /api` |
| `stores/user.js` | Pinia store — user state + `rol` persisted to `localStorage` for router guards |
| `router/index.js` | Vue Router with `meta.roles` guards; reads `localStorage.getItem('user')` for role checks |
| `service/` | One service file per domain (e.g. `turnosService.js`, `historiaService.js`) |
| `views/pages/` | Feature views organized by domain (`auth/`, `historias/`, `turnos/`, `usuarios/`, `grupos/`, `disponibilidades/`, `evolucion/`) |
| `utils/eventBus.js` | Simple event bus used for `user:updated` / `user:loggedOut` events |

## RBAC Roles

Roles are stored in `usuarios.rol` (DB) and enforced in two places:
- **Backend**: `@requiere_rol('director', 'profesional', ...)` decorator in route files
- **Frontend**: `meta: { roles: [...] }` on routes + `router.beforeEach` guard

| Role | Access |
|------|--------|
| `director` | Full access: users, groups, audit, administration |
| `profesional` | Personal schedule, availability, clinical features |
| `administrativo` | Daily operations (patients, appointments) |
| `area` | Logical user representing a specialty/module; participates in group agendas |

## Key Patterns

- **Session-based auth**: Flask-Login sessions with `SESSION_COOKIE_SECURE=True`. The frontend uses `withCredentials: true` on all Axios requests.
- **No JWT**: Auth state is server-side sessions. The frontend stores `loggedIn` and `user` keys in `localStorage` only for router guards — not for authentication itself.
- **Database access**: All routes call `get_connection()` directly (no ORM). Always close connections: `conn.close()`.
- **File uploads**: Files go to `/app/uploads` (Flask) shared via Docker volume `uploads_data` with Nginx, which serves `/uploads/` directly without hitting Flask.
- **Blockchain integrity**: `utils/hashing.py` generates SHA-256 hashes stored in DB; `blockchain_routes.py` / `bfa_client.py` optionally publish hashes to BFA. The BFA node runs in `--dev` mode by default.
- **Password hashing**: `werkzeug.security.generate_password_hash` with `method="scrypt"`.

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
