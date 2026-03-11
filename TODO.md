# TODO - Auditoria tecnica (bugs y riesgos)

Fecha de auditoria: 2026-03-09
Estado: Pendiente de correccion

## Como usar este archivo

- Marcar con `[x]` cada punto resuelto.
- Mantener el orden de prioridad (P0 -> P3).
- En cada item, validar cierre con prueba manual o automatica.

## P0 - Critico (seguridad/acceso)

- [x] **P0-01 - Usuarios inactivos pueden iniciar sesion**
  - Hallazgo: el login no filtra `activo=1`.
  - Impacto: cuentas desactivadas siguen accediendo.
  - Referencias:
    - `backend_flask/app/auth.py` (consulta por username)
    - `backend_flask/app/routes/usuarios_routes.py` (baja logica con `activo=0`)
  - Criterio de cierre: usuario con `activo=0` recibe 401 en login.
  - Estado: implementado en `auth.py` y `load_user` de `__init__.py`.

- [x] **P0-02 - Endpoint blockchain de prueba expuesto sin auth**
  - Hallazgo: `/api/blockchain/test_tx` no tiene `@login_required`.
  - Impacto: cualquiera puede disparar transacciones de prueba.
  - Referencia: `backend_flask/app/routes/blockchain_routes.py`.
  - Criterio de cierre: endpoint protegido por auth+rol o deshabilitado en produccion.
  - Estado: protegido con login+rol director y bloqueado por config en prod.

- [x] **P0-04 - Inconsistencia critica de dias (DB vs backend/frontend)**
  - Hallazgo: enum SQL usa dias sin tilde y sin domingo, backend/frontend usan variantes con tilde y domingo.
  - Impacto: errores al crear/editar disponibilidades y validaciones de agenda.
  - Referencias:
    - `db/init.sql`
    - `backend_flask/app/routes/disponibilidades_routes.py`
    - `backend_flask/app/routes/turnos_routes.py`
    - `frontend/src/views/pages/disponibilidades/DisponibilidadProfesional.vue`
  - Criterio de cierre: representacion unica de dias y migracion aplicada.
  - Estado: canonicalizado a `Lunes..Domingo` sin tildes en DB/backend.

- [x] **P0-05 - Config de cookies no alineada con despliegue HTTP actual**
  - Hallazgo: cookies secure activadas mientras el stack esta servido en HTTP:80.
  - Impacto: sesiones que no persisten o comportamiento inconsistente.
  - Referencias:
    - `backend_flask/app/config.py`
    - `nginx/default.conf`
  - Criterio de cierre: configuracion por entorno (dev HTTP / prod HTTPS) funcionando.
  - Estado: `SESSION_COOKIE_SECURE` y `REMEMBER_COOKIE_SECURE` ahora configurables por entorno/env vars.

- [ ] **P0-06 - Secretos sensibles expuestos**
  - Hallazgo: credenciales y claves reales en `.env` y passwords hardcodeados en SQL.
  - Impacto: compromiso total de correo, DB y blockchain.
  - Referencias:
    - `.env`
    - `db/init.sql`
  - Criterio de cierre: rotacion completa + eliminacion de secretos del repo.
  - Estado: parcial. Se eliminaron hardcodeados SQL y se separo `production.env`; falta rotacion real de secretos y saneo de historico Git.

- [ ] **P0-07 - Levantar dominio - pending**
  - Impacto: roles no permitidos pueden cambiar duraciones ajenas.
  - Referencia: `SECURE-DOMAIN.md`.
  - Nota de Negocio: NIC Argentina y HTTPs

## P1 - Alto (logica de negocio/robustez API)

- [x] **P1-01 - Uso fragil de `request.json` en varias rutas**
  - Hallazgo: llamadas directas a `request.json` sin fallback.
  - Impacto: posibles 500 con payload vacio o JSON invalido.
  - Referencias:
    - `backend_flask/app/routes/auth_routes.py`
    - `backend_flask/app/routes/usuarios_routes.py`
    - otras rutas similares
  - Criterio de cierre: uso consistente de `request.get_json(silent=True) or {}`.
  - Estado: implementado en `auth_routes`, `usuarios_routes`, `turnos_routes`, `disponibilidades_routes`, `grupos_routes` y `pacientes_routes`.

- [x] **P1-02 - Editar turno no revalida disponibilidad/ausencias/solapes**
  - Hallazgo: `PUT /api/turnos/<id>` actualiza horario sin validar reglas de agenda.
  - Impacto: turnos invalidos pueden guardarse por edicion.
  - Referencia: `backend_flask/app/routes/turnos_routes.py`.
  - Criterio de cierre: validacion equivalente a alta de turno.
  - Estado: implementado con politica de negocio. `editar_turno` revalida via `medico_disponible(...)` y permite solape cuando opera `administrativo` o `area`.

- [x] **P1-03 - Riesgo de loop infinito en creacion de tanda**
  - Hallazgo: si `dias_semana` no mapea a dias validos, el while puede no terminar.
  - Impacto: request colgada / consumo de recursos.
  - Referencia: `backend_flask/app/routes/turnos_routes.py`.
  - Criterio de cierre: validacion previa de `dias_semana` y salida controlada con 400.
  - Estado: implementado con validacion de `dias_indices` y respuesta 400 cuando es invalido/vacio.

- [x] **P1-04 - RBAC inconsistente en rutas de turnos**
  - Hallazgo: permisos distintos entre `POST/PUT/DELETE/tanda` para roles `area`/`administrativo`.
  - Impacto: comportamiento inesperado y fisuras de autorizacion.
  - Referencia: `backend_flask/app/routes/turnos_routes.py`.
  - Criterio de cierre: matriz RBAC unica y aplicada en todas las operaciones.
  - Estado: implementado y alineado a negocio. Se unifico con `ROLES_TURNOS`; `area` puede operar sobre turnos de terceros y la restriccion por ownership queda solo para `profesional`.

## P2 - Medio (frontend, UX, consistencia operativa)

- [x] **P2-01 - Base URL frontend puede forzar downgrade HTTPS -> HTTP**
  - Hallazgo: fallback de axios reemplaza `https://` por `http://`.
  - Impacto: mixed content y fallas en produccion segura.
  - Referencia: `frontend/src/api/axios.js`.
  - Criterio de cierre: base URL neutral y segura (`/api` o env valida).
  - Estado: implementado. `axios` usa `VITE_API_URL` o fallback seguro relativo `/api`.

- [x] **P2-02 - URLs hardcodeadas a localhost**
  - Hallazgo: varias rutas/servicios usan `http://localhost:5000`.
  - Impacto: rompe deploy y entornos con dominio/HTTPS.
  - Referencias:
    - `frontend/src/utils/fotoUrl.js`
    - `frontend/src/views/pages/historias/HistoriaPaciente.vue`
    - `frontend/src/service/pacienteService.js` (constante sin uso)
  - Criterio de cierre: todo consume `VITE_API_URL` o rutas relativas.
  - Estado: implementado. Se removieron hardcodeados y se unifico en `VITE_API_URL`/`/api`.

- [x] **P2-03 - Guard frontend confia en localStorage para auth/rol**
  - Hallazgo: router toma `loggedIn` y `user.rol` desde localStorage.
  - Impacto: bypass visual de navegacion (aunque backend proteja datos).
  - Referencia: `frontend/src/router/index.js`.
  - Criterio de cierre: estado de sesion derivado del backend/store validado.
  - Estado: implementado. Guard ahora valida con `userStore.fetchUser()` (backend) y rol del store; se elimino dependencia de `localStorage` para auth/rol.

- [x] **P2-04 - Update de paciente puede armar SQL invalido si payload vacio**
  - Hallazgo: `SET` dinamico sin validar que haya campos para actualizar.
  - Impacto: error SQL en runtime.
  - Referencia: `backend_flask/app/routes/pacientes_routes.py`.
  - Criterio de cierre: responder 400 "sin cambios" cuando no hay campos.
  - Estado: implementado. Si no hay campos validos para update devuelve `400` con `Sin cambios para actualizar`.

- [x] **P2-05 - Enumeracion de cuentas en recover password**
  - Hallazgo: devuelve 404 si email no existe.
  - Impacto: permite inferir usuarios registrados.
  - Referencia: `backend_flask/app/routes/auth_routes.py`.
  - Criterio de cierre: respuesta generica indistinguible para email existente/no existente.
  - Estado: implementado. `/api/recover` ahora devuelve mensaje generico y status 200 en ambos casos.

## P3 - Mantenimiento (deuda tecnica y calidad)

- [x] **P3-01 - Dependencias frontend con vulnerabilidades reportadas**
  - Hallazgo: `npm audit` reporta 10 vulnerabilidades (5 moderadas, 5 altas).
  - Paquetes destacados: `axios`, `vite`, `rollup`, `minimatch`.
  - Referencia: `frontend/package.json` y lockfile.
  - Criterio de cierre: actualizar dependencias y revalidar build/lint.
  - Estado: implementado. Dependencias actualizadas (`npm audit fix` + upgrade a `vite@7.3.1` y `@vitejs/plugin-vue@6.0.1`), `npm audit` en 0 vulnerabilidades y `npm run build`/`npm run lint` OK.

- [x] **P3-02 - Cobertura de tests insuficiente**
  - Hallazgo: no hay tests backend detectados por `pytest`.
  - Impacto: alto riesgo de regresion en cambios criticos.
  - Criterio de cierre: suite minima para auth, RBAC, turnos, disponibilidades.
  - Estado: implementado. Nueva suite en `backend_flask/tests/` con 6 tests para auth, RBAC, turnos y disponibilidades; `pytest -q` OK.

- [x] **P3-03 - Hallazgos de lint frontend**
  - Hallazgo inicial: errores `no-unused-vars` detectados en lint.
  - Archivos reportados originalmente:
    - `frontend/src/components/FloatingConfigurator.vue`
    - `frontend/src/components/dashboard/UserMenu.vue`
    - `frontend/src/service/pacienteService.js`
    - `frontend/src/utils/formatDate.js`
    - `frontend/src/views/pages/historias/Turnos.vue`
  - Criterio de cierre: lint limpio sin introducir cambios funcionales inesperados.
  - Estado: implementado. Limpieza de imports/variables sin uso y `npm run lint` OK.

## Checklist de validacion final

- [ ] Login/logout y persistencia de sesion funcionando en entorno actual.
- [ ] Usuarios inactivos bloqueados.
- [ ] RBAC consistente en rutas sensibles.
- [ ] CRUD de disponibilidades sin errores por dias.
- [ ] Alta/edicion/baja de turnos respeta reglas de disponibilidad y solapes.
- [ ] Frontend funciona sin URLs hardcodeadas a localhost.
- [x] `npm run build` OK y `npm run lint` OK.
- [x] Tests backend minimos ejecutando en CI/local.
