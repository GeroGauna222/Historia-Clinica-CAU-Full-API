# Security Policy & Audit Log

## Reporting Vulnerabilities

If you discover a security issue in Historia Clínica CAU, report it privately to the repository maintainers. Do not open public issues for exploitable vulnerabilities.

## Scope

- Flask REST API (`backend_flask/`)
- Vue 3 frontend (`frontend/`)
- Nginx reverse proxy (`nginx/`)
- MySQL schema and seeds (`db/`)
- Docker Compose deployment

## Security Audit Log

### 2026-07-17 — Branch `cursor/code-security-review-8657`

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 (UTC) |
| **Branch** | `cursor/code-security-review-8657` (base: `main`) |
| **Reviewer** | Cursor Security Automation (cron) |
| **Status** | **Pending Fixes** |
| **Backend tests** | 45/45 passed (`python3 -m pytest tests/ -q`) |
| **Frontend lint** | Green (`npm run lint`) |
| **AI/Agent risks** | Not applicable — no LLM or autonomous agent integrations in codebase |

#### Summary

Static analysis and taint review completed. No SQL injection vectors confirmed (parameterized queries throughout). Session-based auth (Flask-Login) is correctly enforced on most endpoints. **Three CRITICAL and multiple HIGH findings remain open** — primarily unauthenticated file access, default credentials, and authorization gaps (IDOR / missing RBAC).

#### Open findings (priority order)

| Severity | Area | Finding |
|----------|------|---------|
| CRITICAL | Nginx `/uploads/` | Clinical attachments served without authentication via `alias /var/www/uploads/` (`nginx/default.conf:42-47`). Bypasses Flask RBAC. |
| CRITICAL | `db/init.sql` | Default `admin` user seeded with known password (`admin123` per `frontend/tests/test_usuarios.sh`). Must be removed or forced rotation on first deploy. |
| CRITICAL | `config.py` | `SECRET_KEY` falls back to hardcoded `"CambiaEstoPorUnValorSeguro"` if unset — enables session forgery and reset-token abuse in misconfigured production. |
| HIGH | `__init__.py` | Profile photos at `/static/fotos_usuarios/<filename>` served without `@login_required`; enumerable `user_{id}` filenames. |
| HIGH | `turnos_routes.py` | IDOR: `GET /api/turnos/profesional/<usuario_id>` returns patient PII for any professional ID without ownership check. |
| HIGH | `blockchain_routes.py` | Most blockchain endpoints (`registrar`, `verificar`, `auditorias`) lack `@requiere_rol` — any authenticated role can anchor/read audit data. |
| HIGH | `historias_routes.py` | `GET /api/pacientes/<id>/historias` missing `@requiere_rol` — any logged-in user can read consolidated clinical records. |
| HIGH | `frontend/src/stores/user.js` | Full user state (DNI, email, phone) logged via `console.log` in production builds. |
| MEDIUM | `auth_routes.py` | No rate limiting on `/api/login` or `/api/recover` (brute-force / email abuse). |
| MEDIUM | `auth_routes.py` | Session fixation: no `session.clear()` before `login_user()`. |
| MEDIUM | `usuarios_routes.py` | Profile photo upload accepts arbitrary extensions; raw save fallback on PIL failure (stored XSS risk). |
| MEDIUM | `pacientes_routes.py` | Evolution file uploads lack MIME/extension allowlist. |
| MEDIUM | Multiple routes | Raw exception strings returned to clients (`str(e)`). |
| LOW | `recetas_routes.py` | Medication lookup proxies external API without role restriction. |
| LOW | `axios.js` | 401 interceptor redirects without clearing Pinia user store. |

#### Verified mitigations

- `.env` / `production.env` are gitignored and not tracked in repository.
- SQL queries use `%s` parameterization; dynamic column names come from server-side whitelists.
- Password hashing uses Werkzeug `scrypt`.
- `load_user` filters `activo = 1`.
- No `v-html` / `innerHTML` in frontend; Vue text interpolation for clinical content.
- Auth tokens are not stored in `localStorage` (session cookies only).
- `ENABLE_BLOCKCHAIN_TEST_ENDPOINTS` defaults to `false` in production.

#### Recommended next actions

1. Serve uploads only through authenticated Flask routes (or signed short-TTL URLs); remove public Nginx `/uploads/` alias.
2. Remove default admin seed from `init.sql` or require password change on first login.
3. Fail fast on startup when `SECRET_KEY` is unset in production.
4. Add `@login_required` + ownership checks to photo and turno read endpoints.
5. Add `@requiere_rol` to blockchain and historias GET endpoints.
6. Remove PHI `console.log` calls from frontend store/bootstrap.
7. Add rate limiting (Flask-Limiter) on login and password recovery.

#### Related documentation

- Production hardening runbook: [DOMAIN-SECURE.md](./DOMAIN-SECURE.md)
- Agent operations: [docs/agents/testing-and-validation.md](./docs/agents/testing-and-validation.md)

---

### 2026-07-16 — Branch `cursor/code-security-review-14d9`

Initial automated audit. Findings largely unchanged as of 2026-07-17. Backend test count: 45 passing. See git history for prior review branch.
