# Security Policy & Audit Log

Historia Clínica CAU (ClinicView) — políticas de seguridad y registro de auditorías automatizadas.

## Reporting vulnerabilities

Reportar hallazgos de seguridad al equipo de desarrollo (Dither Labs / ClinicView). No abrir issues públicos con detalles explotables.

## Security controls (baseline)

| Control | Estado actual |
|---------|---------------|
| Autenticación | Flask-Login, cookies HttpOnly, `withCredentials` en frontend |
| RBAC | Decorador `@requiere_rol` en dominios operativos; **gap en PHI/pacientes** |
| SQL | Consultas parametrizadas (`%s`) de forma consistente |
| Passwords | Werkzeug scrypt |
| Uploads | `secure_filename`, límite 20MB; **sin allowlist MIME** |
| HTTPS | Configurado en producción vía Nginx + Let's Encrypt |
| Blockchain test endpoints | Deshabilitados en producción (`ENABLE_BLOCKCHAIN_TEST_ENDPOINTS=False`) |
| LLM / AI agents | **No integrados** — sin superficie de prompt injection |

## Outstanding risks (prioritized)

Ver entradas de auditoría recientes. Ítems abiertos de mayor severidad:

1. **CRITICAL** — Nginx sirve `/uploads/` sin autenticación (PHI expuesto).
2. **CRITICAL** — Archivo `env` versionado en git con secretos reales.
3. **CRITICAL** — RBAC ausente en rutas de pacientes/historias/evoluciones.
4. **HIGH** — IDOR en descarga de adjuntos y agendas de turnos.
5. **HIGH** — `SECRET_KEY` con fallback conocido si falta env var.
6. **HIGH** — XSS almacenado vía Tippy `allowHTML` en calendarios.
7. **MEDIUM** — PII en `console.log` del frontend; sin CSRF tokens; sin rate limiting en login.

## Audit log

### 2026-06-28 — AppSec cron audit

| Campo | Valor |
|-------|-------|
| **Branch** | `cursor/code-security-review-220e` (base: `main`) |
| **Commit** | `f5e629fa` |
| **Auditor** | Cursor Automation (DevSecOps cron) |
| **Security Status** | **Pending Fixes** |
| **Test/Lint** | Backend 28/29 pass · Frontend lint green |

#### Scope

Revisión completa de backend Flask (14 blueprints), frontend Vue 3, Nginx/Docker, `db/init.sql`, auth/RBAC, taint analysis input→sink, y vectores AI/agent.

#### Findings summary

| Severity | Count | Notable items |
|----------|-------|---------------|
| CRITICAL | 4 | Public `/uploads/`, secrets in git (`env`), PHI without RBAC, default admin seed |
| HIGH | 9 | Photo routes unauthenticated, IDOR files/turnos, blockchain unrestricted, XSS Tippy, SECRET_KEY default |
| MEDIUM | 6 | Error leakage, no CSRF, no session rotation, file upload validation gaps, PII console logs |
| LOW | 4 | Debug prints, CORS localhost-only, cursor leaks, grupos dynamic IN-list anti-pattern |

#### AI / Agent risks

**None detected.** No LLM prompts, agent tooling, or autonomous write paths in codebase.

#### SQL injection

**No exploitable vectors.** Parameterized queries used consistently; dynamic SQL limited to whitelisted column names.

#### Test results

```
pytest tests/  → 28 passed, 1 failed (test_login_success: StubAuthUser missing especialidad — test stub drift, not security)
npm run lint   → pass
```

#### Actions taken this run

- Created/updated `SECURITY.md` with this audit entry.
- Posted ClinicView project status update in Linear.

#### Recommended remediation order

1. Remove public Nginx `/uploads/` alias; serve via authenticated Flask endpoint with ownership check.
2. Rotate all secrets; add `env` to `.gitignore`; purge from git history.
3. Apply `@requiere_rol` to all clinical endpoints; restrict DELETE to `director`.
4. Fix `crear_turnos_tanda` missing `get_connection()` (HTTP 500 on `/api/turnos/tanda`).
5. Disable Tippy `allowHTML` or sanitize with DOMPurify.
6. Require `SECRET_KEY` at startup in production (fail-fast).
7. Remove PII from frontend `console.log` in production builds.

---

### 2026-06-27 — AppSec cron audit (reference)

Branch `cursor/code-security-review-e775`. Findings aligned with 2026-06-28 audit; no code remediations merged. See Linear ClinicView project updates.

### 2026-06-26 — Code Checker multi-model audit (reference)

Branch `main` @ `f5e629fa`. Full report in Linear issue OFF-29 and ClinicView project activity.
