# Security Policy & Audit Log

Política de seguridad y registro de auditorías automatizadas para **Historia Clínica CAU**.

Para hardening de producción (HTTPS, dominio, cookies), ver también [DOMAIN-SECURE.md](DOMAIN-SECURE.md).

---

## Reportar vulnerabilidades

Si encontrás una vulnerabilidad, reportala de forma privada al equipo responsable del repositorio. No abras issues públicos con detalles explotables.

---

## Controles de seguridad implementados

| Control | Estado |
|---------|--------|
| Autenticación por sesión Flask-Login (cookies HttpOnly) | ✅ |
| Hashing de contraseñas con scrypt (Werkzeug) | ✅ |
| SQL parametrizado (`%s`) en consultas | ✅ |
| `secure_filename()` en uploads de evoluciones | ✅ |
| `MAX_CONTENT_LENGTH` 20 MB (Flask + Nginx) | ✅ |
| RBAC backend (`@requiere_rol`) en rutas administrativas | ⚠️ Parcial |
| RBAC frontend (`meta.roles` en router) | ⚠️ Parcial |
| Protección CSRF explícita | ❌ Pendiente |
| Rate limiting en login/recover | ❌ Pendiente |
| Uploads clínicos con auth | ❌ Pendiente (Nginx público) |

---

## Hallazgos abiertos (prioridad)

### CRITICAL

1. **Nginx sirve `/uploads/` sin autenticación** — `nginx/default.conf` L42–47  
   Archivos clínicos en `uploads/evoluciones/<evo_id>/` accesibles por enumeración de IDs.

2. **IDOR en descarga de archivos de evolución** — `backend_flask/app/routes/pacientes_routes.py` L374–379  
   Cualquier usuario autenticado puede descargar adjuntos si conoce `evo_id` y nombre de archivo.

### HIGH

3. **Endpoints de pacientes sin `@requiere_rol`** — acceso PHI para cualquier rol autenticado.  
4. **`SECRET_KEY` con valor por defecto** — `backend_flask/app/config.py` L7 (fail-fast añadido en producción).  
5. **Fotos de perfil sin `@login_required`** — `backend_flask/app/__init__.py` L143–154.  
6. **Blockchain sin restricción de rol** — `backend_flask/app/routes/blockchain_routes.py`.  
7. **IDOR en turnos por profesional/grupo** — `backend_flask/app/routes/turnos_routes.py`.

### MEDIUM

8. Sin CSRF tokens en API con cookies de sesión.  
9. Sin rate limiting en `/api/login`, `/api/recover`, `/api/reset`.  
10. Uploads sin validación de tipo MIME/extensión.  
11. Router frontend no revalida sesión en cada navegación.  
12. PII en logs de backend (`print` con filenames/paths).

### LOW

13. Token de reset en URL path (riesgo Referer/logs).  
14. `password_hash` cargado en `current_user` en cada request.

---

## AI & Agent Risks

Este repositorio **no integra LLMs ni agentes autónomos**. No se detectaron vectores de prompt injection ni ejecución de herramientas sin supervisión humana en el código de aplicación.

---

## Audit Log

### 2026-06-24 — `cursor/application-security-audit-0a31`

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-24 |
| **Rama** | `cursor/application-security-audit-0a31` |
| **Base** | `main` |
| **Auditor** | Cursor Automation (DevSecOps cron) |
| **Estado** | **Pending Fixes** |
| **Tests backend** | 28/29 pass (`test_login_success` — stub incompleto, no de seguridad) |
| **Lint frontend** | Green (`npm run lint`) |
| **npm audit** | 15 vulnerabilidades en dependencias dev (no bloqueante para runtime) |

**Resumen:** Se confirmaron 2 hallazgos CRITICAL, 5 HIGH y múltiples MEDIUM sin remediación en main. SQL injection clásico no detectado. Controles positivos: scrypt, SQL parametrizado, sin `v-html` en frontend, sin tokens en localStorage.

**Acciones en esta rama:**
- Creación de `SECURITY.md` con registro de auditoría.
- Eliminación de logs de PII en consola del frontend (solo `import.meta.env.DEV`).
- Validación fail-fast de `SECRET_KEY` en entorno `production`.
- Corrección de stub de test `StubAuthUser` para suite verde.

**Pendiente para próximo sprint:**
- Bloquear `/uploads/` en Nginx; servir solo vía Flask con autorización.
- Añadir `@requiere_rol` a rutas clínicas y blockchain.
- CSRF tokens + rate limiting en auth.
- Completar `meta.roles` en router Vue.

---

### 2026-06-23 — `cursor/application-security-audit-28c9`

| Campo | Valor |
|-------|-------|
| **Estado** | Pending Fixes (4 CRITICAL, 9 HIGH) |
| **Notas** | Primera auditoría automatizada; hallazgos base documentados en memoria del agente. |
