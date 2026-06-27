# Security Policy & Audit Log

Historia Clínica CAU — security review checkpoints, findings, and remediation tracking.

## Reporting Vulnerabilities

Report security issues privately to the project maintainers. Do not open public issues for undisclosed vulnerabilities.

## Pre-Deploy Checklist

- [ ] Rotate all secrets if `env` was ever committed or shared
- [ ] Remove or gate default `admin` seed (`db/init.sql`) in production
- [ ] Authenticate `/uploads/` at Nginx or proxy all downloads through Flask
- [ ] Add `@requiere_rol` to all clinical endpoints (`pacientes_routes`, `historias_routes`, `blockchain_routes`)
- [ ] Enforce ownership checks on turnos read endpoints and evolution file downloads
- [ ] Require auth for profile photo routes (`__init__.py`)
- [ ] Strip PII from frontend `console.log` / `console.error` in production builds
- [ ] Set `SECRET_KEY`, `DB_PASSWORD` via env — fail fast if missing in production
- [ ] Add `env` to `.gitignore`; use `.env` only locally (never commit)

---

## Audit Log

### 2026-06-27 — `cursor/code-security-review-e775` (base: `main`)

| Field | Value |
|-------|-------|
| **Status** | Pending Fixes |
| **Reviewer** | DevSecOps automation (cron) |
| **Branch delta** | Migration idempotency fixes (`migrate.py`, SQL migrations) — no security remediations in diff |
| **Tests** | Backend: 28/29 pass (`test_login_success` stub incomplete — unrelated to security) |
| **Lint** | Frontend ESLint: Green |

#### Vectors Reviewed

| Vector | Result |
|--------|--------|
| Taint analysis (input → SQL/shell/files) | No exploitable SQL injection found; parameterized queries used consistently. File upload lacks extension allowlist. |
| Auth & authorization | **FAIL** — `pacientes_routes.py` uses only `@login_required`; no `@requiere_rol`. IDOR on patients, turnos, evolution files. |
| AI & agent risks | **N/A** — No LLM prompts or autonomous agent tooling in codebase. |
| Data privacy | **FAIL** — PII logged to browser console (`user.js`); debug `print` in photo serving; public Nginx `/uploads/` bypasses Flask auth. |

#### Open Findings (summary)

| Sev | File | Issue |
|-----|------|-------|
| CRITICAL | `nginx/default.conf`, `default.dev.conf` | `/uploads/` served without authentication — clinical attachments publicly accessible |
| CRITICAL | `env` (tracked in git) | Live secrets (SECRET_KEY, DB_PASSWORD, mail, BFA private key) |
| CRITICAL | `db/init.sql` | Default director `admin` / known password (`admin123` in test docs) |
| CRITICAL | `pacientes_routes.py` | Any authenticated user can read/modify/delete all patients (IDOR + missing RBAC) |
| HIGH | `backend_flask/app/__init__.py` | Profile photos served without `@login_required` |
| HIGH | `pacientes_routes.py` | Evolution file download without patient-access check |
| HIGH | `blockchain_routes.py` | Audit/registrar endpoints lack role restriction |
| HIGH | `turnos_routes.py` | Read endpoints expose patient DNI without ownership check |
| HIGH | `frontend/src/stores/user.js` | Full user PII logged via `console.log(this.$state)` |
| MEDIUM | `frontend/src/router/index.js` | Sensitive routes lack `meta.roles` (UI-only RBAC) |
| MEDIUM | `backend_flask/app/config.py` | Weak default fallbacks for SECRET_KEY / DB_PASSWORD |
| LOW | `docker-compose.yml` | Dev bind-mount, no non-root user, unpinned `nginx:latest` |

#### Positive Controls

- Session-based auth (Flask-Login) with `withCredentials` on frontend — no JWT in localStorage
- Talisman CSP/HTTP headers configured
- `secure_filename` on uploads; `MAX_CONTENT_LENGTH` enforced
- `ausencias_routes`, `disponibilidades_routes`, `grupo_posteos_routes` implement ownership checks
- SQL uses `%s` placeholders throughout reviewed routes

#### Next Actions

1. Remediation PR: RBAC on `pacientes_routes` + Nginx uploads auth
2. Rotate secrets; remove `env` from git history (`git filter-repo` / BFG)
3. Production bootstrap without default admin password
4. Re-run audit after remediation merges

---

### 2026-06-26 — `cursor/code-security-review-c469` (base: `main`)

Initial security audit. Findings above were first catalogued. `SECURITY.md` created.
