# Security Policy & Audit Log

Sistema: **Historia Clínica CAU / ClinicView** — Flask + Vue + MySQL + Nginx + Docker.

## Reporting vulnerabilities

Reportar hallazgos de seguridad al equipo de desarrollo (Ditherlabs / Gero Gauna) de forma privada. No abrir issues públicos con detalles explotables.

---

## Audit Log

### 2026-06-26 — Automated DevSecOps review (`cursor/code-security-review-c469`)

| Campo | Valor |
|-------|-------|
| **Branch** | `cursor/code-security-review-c469` (base: `main`) |
| **Status** | **Pending Fixes** |
| **Backend tests** | 28 passed, 1 failed (`test_login_success` — stub incompleto, no relacionado con seguridad) |
| **Frontend lint** | Green |
| **AI/Agent risks** | N/A — no hay integración LLM ni ejecución autónoma de herramientas |

#### Resumen ejecutivo

Se identificaron **4 hallazgos CRITICAL**, **9 HIGH**, **12 MEDIUM** y varios LOW. No se detectó SQL injection explotable en rutas API (consultas parametrizadas). El riesgo principal es **exposición de datos clínicos (PHI)** por arquitectura de uploads públicos, RBAC incompleto en endpoints de pacientes/evoluciones, y secretos/credenciales en repositorio.

#### Hallazgos CRITICAL

| ID | Archivo | Threat path | Remediation |
|----|---------|-------------|-------------|
| C-01 | `nginx/default.conf`, `nginx/default.dev.conf` | `GET /uploads/evoluciones/{id}/{file}` → Nginx sirve volumen compartido sin cookie ni `auth_request` | Eliminar `location /uploads/` público; servir solo vía Flask (`/api/uploads/...`) con `@login_required` + verificación de ownership, o URLs firmadas |
| C-02 | `backend_flask/app/__init__.py` L143–154 | `GET /api/static/fotos_usuarios/<filename>` sin autenticación | Añadir `@login_required`; validar que el solicitante tenga permiso |
| C-03 | `env` (tracked en git) | Archivo con `SECRET_KEY`, `DB_PASSWORD`, `MAIL_PASSWORD`, `PRIVATE_KEY_BFA` versionado | Rotar todos los secretos; añadir `env` a `.gitignore`; eliminar del historial git (`git filter-repo`); usar solo `.env` local |
| C-04 | `db/init.sql` L337–343 | Deploy fresco → usuario `admin` con hash de contraseña conocida (`admin123` en `test_usuarios.sh`) | No seedear admin con password conocido; forzar cambio en primer login o usar variable de entorno |

#### Hallazgos HIGH (selección)

| ID | Archivo | Threat path | Remediation |
|----|---------|-------------|-------------|
| H-01 | `pacientes_routes.py` | Cualquier usuario autenticado → CRUD completo de pacientes y evoluciones (sin `@requiere_rol`) | `@requiere_rol('director','profesional','administrativo')` + ownership por relación de atención |
| H-02 | `blockchain_routes.py` | Cualquier usuario autenticado → sellado/verificación/auditoría global | Restringir a `director` o roles clínicos autorizados |
| H-03 | `config.py` L7, L38 | `SECRET_KEY` / `DB_PASSWORD` con defaults predecibles si faltan env vars | Fail-fast en `ENV=production` si valores por defecto |
| H-04 | `frontend/src/stores/user.js` L52 | `console.log(this.$state)` expone DNI, email, teléfono en consola del navegador | Eliminar o gatear con `import.meta.env.DEV` |
| H-05 | Nginx (todos los configs) | Sin HSTS, CSP, X-Frame-Options, X-Content-Type-Options | Añadir headers de seguridad en bloque `server` |
| H-06 | `pacientes_routes.py` L291–298 | Uploads de evoluciones sin whitelist de extensión/MIME | Validar tipo de archivo; `Content-Disposition: attachment` al servir |

#### Hallazgos MEDIUM (selección)

- IDOR en `turnos_routes.py`: `GET /api/turnos/profesional/{usuario_id}` sin verificación de ownership
- `str(e)` devuelto al cliente en múltiples rutas → fuga de detalles internos
- Sin rate limiting en `/api/login`, `/api/recover`, `/api/reset/<token>`
- Sesiones no invalidadas tras reset de contraseña
- `database.py` defaults (`root`/`root`) inconsistentes con `config.py`

#### Controles positivos

- Autenticación por sesión Flask-Login con cookies HttpOnly
- Sin tokens de auth en `localStorage` (solo preferencia de tema)
- SQL parametrizado en rutas API revisadas
- `@requiere_rol` correcto en usuarios, disponibilidades, ausencias, recetas (emisión)
- Sin `v-html` en frontend Vue
- Sin integración LLM / riesgos de prompt injection
- Puertos MySQL/Flask no expuestos en `docker-compose.yml`

#### Acciones pendientes (prioridad)

1. Rotar secretos y sacar `env` del repositorio
2. Proteger `/uploads/` (arquitectura)
3. RBAC en pacientes, historias, blockchain
4. Autenticar fotos de usuario
5. Eliminar PII de `console.log` en producción
6. Headers de seguridad en Nginx + Talisman CSP en producción
7. Cambiar/eliminar admin seed por defecto

---

### 2026-06-24 — Automated DevSecOps review (`cursor/application-security-audit-0a31`)

| Campo | Valor |
|-------|-------|
| **Status** | Pending Fixes (mitigaciones parciales en rama separada, no mergeadas a `main`) |
| **Tests** | 29/29 pass (rama anterior) |

Hallazgos recurrentes documentados en memoria de automatización: uploads públicos, pacientes sin RBAC, fotos sin auth, blockchain sin rol, IDOR en turnos.

---

## Security checklist (pre-deploy)

- [ ] `SECRET_KEY` único y ≥ 32 bytes aleatorios
- [ ] `DB_PASSWORD` y `MYSQL_ROOT_PASSWORD` fuertes, no defaults
- [ ] `env` / `.env` fuera de git; secretos rotados
- [ ] Admin seed eliminado o password forzado en primer login
- [ ] `/uploads/` no público en Nginx
- [ ] `SESSION_COOKIE_SECURE=True` en producción HTTPS
- [ ] RBAC backend alineado con matriz de roles
- [ ] Frontend `meta.roles` alineado con backend
- [ ] Headers de seguridad en Nginx
- [ ] Sin `console.log` de PII en build de producción
