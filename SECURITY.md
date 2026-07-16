# Security Policy & Audit Log

## Reporting vulnerabilities

Report security issues privately to the repository maintainers. Do not open public issues for undisclosed vulnerabilities.

## Audit log

### 2026-07-16 — Automated DevSecOps review (`cursor/code-security-review-14d9`)

| Field | Value |
|-------|-------|
| **Date** | 2026-07-16 |
| **Branch** | `cursor/code-security-review-14d9` (aligned with `main`, 0 commits ahead) |
| **Status** | **Pending Fixes** |
| **Backend tests** | Green — 45/45 passed (`pytest tests/ -q`) |
| **Frontend lint** | Green (`npm run lint`) |
| **AI/Agent surface** | None detected — no LLM prompts or autonomous agent tooling in codebase |

#### Critical findings (open)

1. **Public clinical uploads via Nginx** — `nginx/default.conf`, `nginx/default.dev.conf`, and `nginx/default.ssl.conf.example` expose `location /uploads/` without authentication, bypassing Flask `@login_required` on `/api/uploads/evoluciones/...`. Sequential `evo_id` enables PHI enumeration.
2. **Secrets tracked in Git** — File `env` (not covered by `.gitignore`, which only ignores `.env`) is committed and contains production credentials (`SECRET_KEY`, `DB_PASSWORD`, `MAIL_PASSWORD`, `PRIVATE_KEY_BFA`). Rotate all exposed values and remove from version control.
3. **Default admin bootstrap** — `db/init.sql` seeds `admin` / known password hash as `director`. Remove or gate behind first-boot env var; force password change on first login.

#### High findings (open)

4. **Profile photos without auth** — `backend_flask/app/__init__.py` serves `/static/fotos_usuarios/` and `/api/static/fotos_usuarios/` without `@login_required`.
5. **Blockchain endpoints under-protected** — `blockchain_routes.py`: registrar/verificar/auditorias require only `@login_required`; any authenticated user can stamp or list global audits.
6. **Historias RBAC gap** — `GET /api/pacientes/<id>/historias` in `historias_routes.py` lacks `@requiere_rol` (IDOR within any logged-in session).
7. **Turnos enumeration IDOR** — `turnos_profesional`, `turnos_profesional_completo`, `turnos_por_grupo`, `listar_turnos_grupales` lack role checks and object-level authorization; exposes patient DNI.
8. **PII in browser console** — `frontend/src/stores/user.js` logs full user state (`dni`, `email`, `telefono`, etc.) on session load.
9. **Upload IDOR in Flask** — `uploaded_file` does not verify filename against `evolucion_archivos` DB record.
10. **Weak config fallbacks** — `config.py` defaults `SECRET_KEY` and `DB_PASSWORD` if env vars missing.

#### Medium / low (selected)

- No CSRF tokens for cookie-based session mutations.
- No rate limiting on `/api/login` or `/api/recover`.
- CORS hardcoded to localhost; Talisman `force_https=False` and CSP disabled.
- File uploads lack MIME/extension allowlist; profile photo fallback saves raw file on PIL failure.
- Debug `print()` in backend routes may leak filenames/tracebacks to container logs.

#### Mitigations verified since prior audit (2026-06-27)

- `pacientes_routes.py` now applies `@requiere_rol('director', 'profesional', 'administrativo', 'area')` on clinical endpoints.
- Backend test suite expanded and passing (45 tests).

#### Recommended remediation priority

1. Remove public Nginx `/uploads/` alias; serve files only through authenticated Flask routes (or `auth_request`).
2. `git rm --cached env`, add `env` to `.gitignore`, rotate all secrets, scrub Git history if repo was public.
3. Remove or secure default admin seed in `db/init.sql`.
4. Add `@login_required` + `@requiere_rol` to photo routes, historias GET, blockchain routes, and turnos enumeration endpoints.
5. Strip PII `console.log` from frontend; add login rate limiting and config fail-fast.

#### Next audit focus

Re-verify CRITICAL items after remediation PRs merge: uploads auth, `env` removal, admin seed, historias/blockchain RBAC, turnos IDOR.

---

### 2026-06-27 — Automated DevSecOps review (`cursor/code-security-review-e775`)

| Field | Value |
|-------|-------|
| **Status** | Pending Fixes |
| **Tests** | Backend 28/29 pass; frontend lint green |
| **Linear** | Status update posted to ClinicView project |

Initial audit identified public uploads, tracked secrets, default admin, pacientes RBAC gaps, and PII logging. Pacientes RBAC subsequently addressed.
