# Security Policy

## Reporting a Vulnerability

If you discover a security issue in Historia Clínica CAU, please report it privately to the project maintainers. Do **not** open a public GitHub issue for undisclosed vulnerabilities.

Include:

- Affected component (backend, frontend, nginx, database, infrastructure)
- Steps to reproduce
- Impact assessment (confidentiality, integrity, availability)
- Suggested remediation, if available

## Security Principles

- Session-based authentication via Flask-Login (`HttpOnly` cookies, `withCredentials` on the frontend).
- RBAC roles: `director`, `profesional`, `administrativo`, `area`.
- Parameterized SQL (`%s` placeholders) for all user-supplied values.
- Secrets only via environment variables — never committed to version control.
- Clinical attachments must not be served without authentication.

## Audit Log

### 2026-06-25 — Automated AppSec audit (branch: `cursor/application-security-audit-28a8`)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Branch** | `cursor/application-security-audit-28a8` (base: `main`) |
| **Diff scope** | `migrate.py`, `20260618_bfa_tsa_receipts.sql`, `20260624_grupos_comunicados.sql` |
| **Status** | **Pending Fixes** |
| **Tests** | Backend: 28 passed, 1 failed (`test_login_success` — stub missing `especialidad` attr, not security-related) |
| **Lint** | Frontend ESLint: **Green** |

#### Diff review (branch changes)

No new security regressions identified in the migration diff. Changes are idempotent DDL for grupos/comunicados tables and cursor-buffering fixes in `migrate.py`. No user-controlled input paths introduced.

#### Outstanding critical findings (repository-wide)

| ID | Severity | File | Summary |
|----|----------|------|---------|
| SEC-001 | CRITICAL | `env` (tracked) | Live secrets in repo (`SECRET_KEY`, `DB_PASSWORD`, `MAIL_PASSWORD`, `PRIVATE_KEY_BFA`). `.gitignore` covers `.env` but not plain `env`. |
| SEC-002 | CRITICAL | `backend_flask/app/routes/pacientes_routes.py` | All 11 patient/clinical endpoints use `@login_required` only — no `@requiere_rol`. Any authenticated user can read/modify/delete PHI (IDOR). |
| SEC-003 | CRITICAL | `nginx/default*.conf` | `/uploads/` served publicly without auth — bypasses Flask-protected download route. Clinical attachments enumerable. |
| SEC-004 | CRITICAL | `backend_flask/app/__init__.py` | Profile photos served at `/static/fotos_usuarios/` and `/api/static/fotos_usuarios/` without authentication. |
| SEC-005 | CRITICAL | `db/init.sql` | Default `admin` user bootstrapped; password documented in `frontend/tests/test_usuarios.sh` (`admin123`). |

#### Outstanding high findings

| ID | Severity | File | Summary |
|----|----------|------|---------|
| SEC-006 | HIGH | `backend_flask/app/routes/historias_routes.py` | `GET /api/pacientes/<id>/historias` lacks RBAC. |
| SEC-007 | HIGH | `backend_flask/app/routes/blockchain_routes.py` | 7/8 endpoints lack `@requiere_rol`; any user can seal/verify records. |
| SEC-008 | HIGH | `backend_flask/app/routes/turnos_routes.py` | IDOR on `GET /api/turnos/profesional/<id>` and group turnos — exposes patient DNI. |
| SEC-009 | HIGH | `backend_flask/app/routes/usuarios_routes.py` | Profile photo upload accepts arbitrary extension; raw fallback on PIL failure. |
| SEC-010 | HIGH | `backend_flask/app/routes/pacientes_routes.py` | Evolución uploads lack extension/MIME whitelist. |
| SEC-011 | HIGH | `backend_flask/app/routes/auth_routes.py` | No rate limiting, no CSRF protection, no session rotation on login. |
| SEC-012 | HIGH | `backend_flask/app/__init__.py` | CSP disabled (`content_security_policy=None`); CORS hardcoded to localhost; `force_https=False`. |
| SEC-013 | HIGH | `nginx/default*.conf` | Missing HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy headers. |

#### Medium / low findings

- `config.py` / `database.py`: weak default `SECRET_KEY` and `DB_PASSWORD`; `database.py` uses separate defaults (`root`/`root`).
- `auth_routes.py`: sessions not invalidated after password reset.
- Multiple routes return `str(exception)` to clients (info disclosure).
- `frontend/src/stores/user.js`: PII logged to console in production builds.
- `health_routes.py`: verbose error strings in `/api/health/secure` response.
- No AI/LLM integrations found — no prompt-injection surface. External APIs: Qbitos (recetas), BFA TSA (blockchain).

#### Recommended remediation priority

1. Remove `env` from version control; rotate all exposed secrets; add `env` to `.gitignore`.
2. Add `@requiere_rol` to all patient/clinical/historia endpoints; enforce object-level access.
3. Remove or authenticate Nginx `/uploads/` public location.
4. Require auth for profile photos; remove unauthenticated `/static/` route.
5. Remove or force password change for default `admin` bootstrap account.
6. Add security headers (CSP, HSTS), production CORS from env, upload allowlisting, rate limiting, CSRF.

#### Next audit actions

- Re-run after SEC-001 through SEC-005 are addressed.
- Add RBAC integration tests for patient and upload endpoints.
- Consider adding `bandit` / `pip-audit` to CI pipeline.
