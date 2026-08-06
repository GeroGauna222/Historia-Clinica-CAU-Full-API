# Security Policy & Audit Log

Este documento registra las auditorías de seguridad periódicas del repositorio **Historia Clínica CAU Full API** y consolida hallazgos abiertos.

Para despliegue seguro en producción, ver también [`DOMAIN-SECURE.md`](DOMAIN-SECURE.md).

---

## Reportar vulnerabilidades

Si descubrís una vulnerabilidad, contactá al equipo responsable del repositorio de forma privada. No abras issues públicos con detalles explotables.

---

## Auditoría — 2026-06-23

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-06-23 |
| **Rama** | `cursor/application-security-audit-28c9` |
| **Base** | `main` (commit `6d8b955f`) |
| **Auditor** | Automatización DevSecOps (cron diario) |
| **Estado** | **Pending Fixes** |
| **Tests backend** | 28 passed, 1 failed (`test_login_success` — stub de test incompleto, no relacionado con seguridad) |
| **Lint frontend** | Green (`npm run lint`) |
| **Riesgos AI/Agent** | N/A — no hay integración LLM ni ejecución autónoma de herramientas en el código |

### Resumen ejecutivo

Se identificaron **4 hallazgos CRITICAL**, **9 HIGH**, **9 MEDIUM** y **6 LOW**. El stack no presenta vectores de inyección de prompts ni agentes autónomos. Los riesgos principales son exposición de datos clínicos (PHI) por falta de RBAC y archivos servidos sin autenticación.

### Hallazgos críticos (acción inmediata)

1. **Adjuntos clínicos públicos vía Nginx** — `nginx/default.conf`, `nginx/default.dev.conf`  
   `location /uploads/` sirve archivos sin autenticación. Cualquier actor que adivine `evolucion_id` + nombre de archivo puede descargar documentos clínicos.

2. **Fotos de perfil sin autenticación** — `backend_flask/app/__init__.py`  
   `GET /api/static/fotos_usuarios/<filename>` no tiene `@login_required`.

3. **`SECRET_KEY` por defecto inseguro** — `backend_flask/app/config.py`  
   Valor fallback `"CambiaEstoPorUnValorSeguro"` permite falsificación de sesiones si no se configura `.env`.

4. **RBAC ausente en endpoints de pacientes/historias** — `pacientes_routes.py`, `historias_routes.py`  
   Cualquier usuario autenticado puede leer/escribir PHI sin `@requiere_rol`.

### Hallazgos altos (prioridad alta)

| # | Área | Archivo(s) | Riesgo |
|---|------|------------|--------|
| 5 | IDOR descarga evoluciones | `pacientes_routes.py:374` | Usuario autenticado descarga adjuntos de cualquier paciente |
| 6 | IDOR turnos | `turnos_routes.py` | Lectura de agendas/DNI de otros profesionales |
| 7 | Blockchain sin RBAC | `blockchain_routes.py` | Operaciones BFA abiertas a cualquier sesión |
| 8 | Creación de usuario sin validar `rol` | `usuarios_routes.py` | Posible escalada de privilegios |
| 9 | Sin rate limiting en auth | `auth_routes.py` | Fuerza bruta en login/recover/reset |
| 10 | Reset no invalida sesiones | `auth_routes.py` | Sesiones robadas sobreviven al cambio de contraseña |
| 11 | CORS hardcodeado a localhost | `__init__.py` | Riesgo de misconfiguración en producción |
| 12 | HTTPS deshabilitado en Talisman | `__init__.py` | `force_https = False` siempre |
| 13 | Errores internos expuestos | múltiples routes | `str(e)` filtra detalles de infraestructura |

### Hallazgos medios (frontend + backend)

- Subida de archivos sin validación MIME/extensión (`pacientes_routes.py`, `usuarios_routes.py`)
- PII en logs (`print` en `__init__.py`, `usuarios_routes.py`; `console.log` en `stores/user.js`)
- Sin tokens CSRF en mutaciones con cookie de sesión
- Frontend: interceptor 401 no limpia Pinia store (`api/axios.js`)
- Frontend: PDF vía `window.open` puede omitir credenciales (`HistoriaPaciente.vue`)
- `ENABLE_BLOCKCHAIN_TEST_ENDPOINTS` habilitado por defecto fuera de producción

### Hallazgos bajos

- SQL dinámico con f-strings (seguro hoy, frágil a futuro)
- `password_hash` cargado en objeto de sesión
- `main.py` con `debug=True` en runner local
- CSP deshabilitado en Talisman

### SQL Injection

No se encontró inyección SQL explotables. Las consultas usan parámetros `%s`. El riesgo residual es de mantenibilidad en SQL dinámico con allowlists.

### Recomendaciones prioritarias

1. Eliminar o restringir `location /uploads/` en Nginx; servir archivos solo vía rutas Flask autenticadas con verificación de ownership.
2. Añadir `@requiere_rol(...)` a todos los endpoints de pacientes, historias y exportaciones PDF.
3. Fail-fast si `SECRET_KEY` no está configurado o es el placeholder.
4. Autenticar rutas de fotos de perfil; validar `secure_filename`.
5. Implementar rate limiting en `/api/login`, `/api/recover`, `/api/reset`.
6. Invalidar sesiones activas al resetear contraseña.
7. Parametrizar CORS vía `CORS_ORIGINS` y habilitar `force_https` en producción.
8. Eliminar `console.log`/`print` con PII; retornar errores genéricos al cliente.

### Próxima revisión

Programada por automatización cron (`0 8 * * *`). Revalidar tras aplicar remediaciones de severidad CRITICAL y HIGH.

---

## Historial de auditorías

| Fecha | Rama | Estado | Notas |
|-------|------|--------|-------|
| 2026-06-23 | `cursor/application-security-audit-28c9` | Pending Fixes | Primera auditoría documentada; 4 CRITICAL abiertos |
