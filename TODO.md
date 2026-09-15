# TODO - Auditoria tecnica (bugs y riesgos)

Fecha de auditoria: 2026-04-13

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

- [x] **P0-07 - Levantar dominio - pending**
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

## P4 - Produccion (dominio, HTTPS, seguridad)

- [x] **P4-01 - Comprar dominio y configurar DNS**
  - Impacto: sin dominio no hay HTTPS ni marca profesional.
  - Referencia: `SECURE-DOMAIN.md`.
  - Criterio de cierre: dominio activo, DNS apuntando a VPS, `nslookup` OK.
  - Estado: pendiente.

- [x] **P4-02 - Configurar Nginx con HTTPS y certificados Lets Encrypt**
  - Impacto: sin HTTPS el proyecto no es apto para produccion.
  - Referencia: `SECURE-DOMAIN.md`.
  - Criterio de cierre: Nginx sirve HTTPS, redireccion HTTP->HTTPS, certificados validos.
  - Estado: pendiente.

- [x] **P4-03 - Endurecer cookies y sesiones**
  - Impacto: seguridad de sesiones en entorno publico.
  - Referencia: `SECURE-DOMAIN.md`.
  - Criterio de cierre: `SESSION_COOKIE_SECURE=True`, `SAMESITE=Lax`.
  - Estado: pendiente.

- [x] **P4-04 - Firewall minimo en VPS**
  - Impacto: exposicion innecesaria de puertos.
  - Referencia: `SECURE-DOMAIN.md`.
  - Criterio de cierre: solo 22, 80, 443 expuestos publicamente.
  - Estado: pendiente.

- [x] **P4-05 - Rotar secretos y asegurar `production.env`**
  - Impacto: fuga de credenciales en entorno real.
  - Referencia: `SECURE-DOMAIN.md`.
  - Criterio de cierre: `production.env` fuera de Git, permisos `600`, secretos fuertes.
  - Estado: pendiente.

## Checklist de validacion final

- [x] Login/logout y persistencia de sesion funcionando en entorno actual.
  - Verificado en vivo (docker local): login -> reload de pagina -> `/api/usuarios/me` sigue autenticado (200) -> logout -> `/api/usuarios/me` devuelve 401. De paso se arreglo `tests/test_auth_routes.py::test_login_success`, que fallaba porque el `StubAuthUser` de prueba no tenia los campos (`especialidad`, `dni`, matricula, lugar de atencion, etc.) que `auth_routes.py` ya serializa en el login desde hace tiempo.
- [x] Usuarios inactivos bloqueados.
  - Verificado en vivo: usuario de prueba creado, dado de baja logica (`DELETE /api/usuarios/<id>` -> `activo=0`), intento de login con sus credenciales -> 401 "Credenciales incorrectas". Confirma que `auth.py` (`WHERE activo = 1`) sigue funcionando en la version actual.
- [x] RBAC consistente en rutas sensibles.
  - Decision de negocio: los 4 roles (`director`, `profesional`, `administrativo`, `area`) tienen acceso a CRUD de pacientes. Se agrego `@requiere_rol('director', 'profesional', 'administrativo', 'area')` explicito a los 11 endpoints de `pacientes_routes.py` (crear, editar, listar, obtener, eliminar, buscar, proximo-nro-hc, evolucion, evoluciones, adjuntos, PDFs), igualando el patron ya usado en `historias_routes.py`. No cambia el comportamiento actual (los 4 roles ya tenian acceso), pero ahora es explicito y future-proof: un rol nuevo que se agregue no tendria acceso automatico. Con TDD: tests nuevos en `test_pacientes_routes.py` (`test_crear_paciente_permite_los_4_roles`, `test_crear_paciente_deniega_rol_no_reconocido` con un rol ficticio "invitado", rojo antes del fix -> 200, verde despues -> 403). Verificado en vivo (docker): Director sigue listando pacientes normalmente tras el cambio. Suite completa: 35 passed.
- [x] CRUD de disponibilidades sin errores por dias.
  - `pytest tests/test_disponibilidades_routes.py` OK (normalizacion de dia y rol `area` verificada).
- [x] Alta/edicion/baja de turnos respeta reglas de disponibilidad y solapes.
  - `pytest tests/test_turnos_routes.py` OK: 7 tests cubriendo rechazo por no disponibilidad (alta y edicion), solape permitido para rol `area`, solape general con ausencias, y validacion de tandas.
- [x] Frontend funciona sin URLs hardcodeadas a localhost.
  - `grep -r "localhost" frontend/src` sin resultados.
- [x] Hora del programa en horario Argentina (OS, MySQL, backend) en todo el sistema.
  - Verificado: OS del contenedor `web`, sesion de MySQL (`db`) y todos los usos de `datetime.now()`/`TIMESTAMP DEFAULT CURRENT_TIMESTAMP` en -03. Unico punto corregido: `recetas_routes.py` usaba `datetime.utcnow()` para `creado_en`/`actualizado_en` de recetas electronicas (ver item "Hora del programa" en Post-MVP).
- [x] `npm run build` OK y `npm run lint` OK.
- [x] Tests backend minimos ejecutando en CI/local.
  - `pytest tests/ -q` -> 33 passed, 0 failed (se corrigio el ultimo test roto, `test_login_success`).

## Changes

### Post-MVP

- [x] Hora del programa, debe ser GMT+3.00 (Argentina)
  - Estado: verificado que `TZ=America/Argentina/Buenos_Aires` ya estaba correctamente configurado a nivel OS (Dockerfile/docker-compose, contenedor `web`) y a nivel MySQL (`--default-time-zone`, contenedor `db`) — confirmado en vivo (`date`, `NOW()`, `datetime.now()` en el contenedor: todo en -03, consistente). El bug real estaba en `recetas_routes.py::_store_receta`: guardaba `creado_en`/`actualizado_en` de recetas electronicas con `datetime.utcnow()` (UTC), 3 horas adelantado respecto al resto de la app (que usa hora local Argentina via `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` o `datetime.now()`). Fix con TDD: test `test_store_receta_guarda_hora_local_argentina_no_utc` (rojo con utcnow, verde tras cambiar a `datetime.now()`). Suite completa: 32 passed, 1 fail preexistente no relacionado (`test_login_success`).
  - Nota: no se pudo verificar end-to-end en navegador porque `/api/recetas` depende de la API externa Qbitos (sin credenciales de prueba); la verificacion quedo a nivel test (mockeado, determinista) en vez de click-through real.

- [x] No funciona el Subir Foto de Perfil
  - Estado: implementado. Corregida ruta física hardcodeada en Flask (`usuarios_routes.py`) y agregada recuperación del stream de datos (`seek(0)`) ante fallas de Pillow para evitar archivos vacíos (0 bytes). En el frontend (`MiPerfil.vue`), se desacopló el botón del label y se controla programáticamente para evitar el bloqueo del evento click.

- [x] Poder hacer en un mismo día de Disponibilidad cortes, es decir Disponible de 10 a 12 y de 14 a 16
  - Estado: implementado. Rediseñado el frontend (`DisponibilidadProfesional.vue`) para permitir agregar múltiples franjas horarias por día de la semana y gestionarlas con botones de añadir y borrar individuales. Implementada validación en frontend para evitar solapamientos y creado el endpoint backend `/api/disponibilidades/validar` para detectar turnos futuros huérfanos antes de confirmar los cambios de horario, alertando al profesional.

- [ ] Re-ver Mobile Version

- [x] Anotaciones en modo Oscuro
  - Estado: agregadas variantes `dark:` a tarjetas de evolucion, formulario de nueva evolucion y tarjeta de datos del paciente en `HistoriaPaciente.vue`, siguiendo la convencion ya usada en `Comunicados.vue`/`PosteosGrupo.vue`. Verificado con datos reales: tarjetas de evolucion confirman fondo oscuro + texto claro correctos. Nota: se detecto un problema pre-existente y no relacionado (fuera de este cambio) donde algunos elementos no recalculan su estilo dark hasta que ocurre otra interaccion en la pagina; no afecta legibilidad (el texto sigue siendo oscuro sobre blanco en ese caso), pero vale la pena investigarlo aparte.

- [x] Ver en la agenda QUIEN cargo cada evento y CUANDO
  - Estado: implementado. Se unifico la trazabilidad de creacion en los tres tipos de evento de agenda. Estado previo (inconsistente): `turnos_grupales` ya tenia `creado_por` + `creado_en`; `ausencias` tenia `creado_por` pero no `creado_en`; `turnos` no tenia ninguno de los dos. Ojo: `turnos.usuario_id` NO es quien cargo el turno sino el profesional dueño de la agenda, por eso hizo falta columna nueva.
  - Backend: migracion `20260727_trazabilidad_creacion_agenda.sql` (`turnos.creado_por` + `turnos.creado_en`, `ausencias.creado_en`). Los INSERT de `api_turnos`, `crear_turnos_tanda` y `crear_ausencia` guardan `current_user.id` + `datetime.now()`. Los endpoints que alimentan las agendas (`turnos_profesional_completo`, `turnos_por_grupo`, `listar_turnos_grupales`, `listar_ausencias`) devuelven `creado_por_nombre` y `creado_en` via `LEFT JOIN usuarios`.
  - Frontend: el modal de detalle de las tres agendas (`Turnos.vue`, `CalendarioGrupo.vue`, `ModuloRehabilitacion.vue`) muestra "Cargado por X el DD/MM/AAAA HH:MM" al ampliar el evento.
  - Limitacion conocida: los eventos anteriores a esta migracion no tienen el dato y no es recuperable — se muestran como "Sin registro de carga". Las columnas se agregaron `NULL DEFAULT NULL` a proposito: con `DEFAULT CURRENT_TIMESTAMP`, MySQL le estampa a todas las filas viejas la fecha de la migracion (verificado), lo que seria un dato falso con apariencia de valido. El `LEFT JOIN` es obligatorio: con `JOIN` los eventos historicos desaparecerian de la agenda.

- [ ] Registrar tambien QUIEN modifico y QUIEN elimino cada evento de agenda
  - Continuacion del item anterior, postergada a pedido. Hoy solo se registra la creacion.
  - Requiere mas que columnas nuevas: eliminar un bloqueo es un `DELETE` duro (`DELETE FROM ausencias`), asi que para saber quien desbloqueo hace falta soft-delete o una tabla de auditoria aparte. Mismo caso para turnos.
  - Relacionado: el item de abajo (no desbloquear agendas de dias anteriores) se resuelve mejor con esto que con una prohibicion dura.

- [ ] No se debe poder desbloquear agendas de dias anteriores (por seguridad interna).
  - Analisis hecho: hoy NO hay ninguna validacion de fecha pasada en el flujo de agenda. Se puede borrar un bloqueo de una fecha pasada (`DELETE /api/ausencias/<id>`), crear un bloqueo en el pasado (`POST /api/ausencias`) y crear turnos en el pasado (`POST /api/turnos`). La cadena que importa: borrar el bloqueo de un dia pasado hace que `medico_disponible()` pase, y permite cargar un turno retroactivo en un dia donde el profesional figuraba ausente.
  - Arreglar solo el desbloqueo (lo que pide el titulo) deja abiertas las otras dos puertas.
  - Pendiente de definicion: prohibicion dura para todos, o prohibicion con excepcion auditada para director.

- [x] Permititr ediciones de Historia auditadas (se registra que fue una anotacion editada, se puede ver la anterior)
  - Estado: implementado. Modelo append-only en `evoluciones` (`padre_id`, `version`, `activo` + FK autoreferencial e indice `idx_evoluciones_padre_activo`): editar no pisa el registro, inserta una version nueva y desactiva las anteriores del mismo arbol. Backend: `PUT /api/pacientes/<id>/evolucion/<evo_id>` (solo el autor original o director) y `GET .../historial` para ver todas las versiones. Los listados y ambos PDFs filtran `activo = 1` y marcan "(Editado)" cuando `version > 1`. Frontend: `HistoriaPaciente.vue` con formulario de edicion y dialogo de historial de cambios. Migracion `20260727_ausencias_observaciones_evoluciones_auditadas.sql`.
  - Nota operativa: cada edicion deja la evolucion nueva y la historia consolidada del paciente en `estado_bfa = 'pendiente'`. El sellado en la TSA de BFA es manual, asi que hay que re-sellar despues de editar.

- [x] Sugerir numero de Historia Last (actualmente en 2567) - se puede registrar numero custom o 'proxima disponible'
  - Estado: implementado. Endpoint backend `GET /api/pacientes/proximo-nro-hc` (MAX numerico + 1). Integrado en `PacienteForm.vue` del frontend para auto-completar por defecto en el alta y mostrar recomendación visual cliqueable.

- [x] Reemplazar Sexo por N° H.C. en listado de pacientes para ordenar y buscar por historia
  - Estado: implementado. Modificado endpoint `/api/pacientes` en backend para incluir `nro_hc` y reemplazada la columna "Sexo" por "N° H.C." en la grilla del frontend (`Pacientes.vue`), permitiendo ordenar y buscar localmente a los pacientes por su número de historia clínica.

- [x] Búsqueda reactiva en tiempo real y precisa al buscar Historias Clínicas
  - Estado: implementado. Añadidos watchers y debounce (400ms) en los inputs de `BuscarHistorias.vue` para buscar sin clickear el botón. Además, el backend ahora soporta parámetros por columna (`nro_hc`, `dni`, `nombre`, `apellido`) para evitar cruzar búsquedas (ej. que H.C. 2 traiga DNI 2) y el frontend limpia automáticamente los otros campos al escribir para mantener un único parámetro activo de forma clara e intuitiva.

- [x] Poder marcar turnos como ausente
  - Estado: implementado. Añadido campo `ausencia` (con_aviso / sin_aviso) a tablas `turnos` y `turnos_grupales` en base de datos. Implementados endpoints backend `PATCH` para ausencias de turnos individuales/grupales, y `GET` para contador de ausencias por paciente. En el frontend, se implementaron indicadores visuales en las tres vistas de agenda (`Turnos.vue`, `CalendarioGrupo.vue`, `ModuloRehabilitacion.vue`) pintando los turnos de rojo ladrillo (sin aviso) o naranja (con aviso). Se agregaron controles de asistencia en el modal de detalle de turnos y alertas informativas al dar un nuevo turno si el paciente cuenta con 3+ ausencias sin aviso.

- [x] Informar sobre turnos del dia proximo a profesionales
  - Estado: implementado. `backend_flask/app/utils/alertas.py` arma y envia por mail el resumen de la agenda del dia siguiente, expuesto como comando CLI `flask enviar-alertas` (registrado en `app/__init__.py`). Reciben el mail los profesionales activos con disponibilidad horaria cargada y activa para el dia de la semana de mañana — es decir, solo los dias que asisten. Si ese dia no tienen turnos, igual reciben el mail avisando que la agenda esta vacia (decision de negocio confirmada).
  - Programacion: el envio NO es automatico hasta correr el instalador. `sudo bash deploy/templates/install_alertas_system.sh` instala el script en `/usr/local/bin/`, crea `/var/log/historia_cau/` con logrotate mensual y agenda el cron diario a las 20:00 hora Argentina. Ver seccion 7 de `deploy/DEPLOY.md`.
  - Detalle: el cron corre en el host, no en el contenedor, asi que el instalador agrega `CRON_TZ=America/Argentina/Buenos_Aires` DESPUES de las tareas ya existentes (el backup de las 03:00 no cambia de horario). El script valida ademas el marcador "Proceso finalizado" en la salida, porque `procesar_y_enviar_alertas()` captura sus errores de DB y termina con exit 0 igual.

- [x] Médico --> Profesional en HC evolucion
  - Estado: renombrado en los dos PDFs de evolucion (`pacientes_routes.py`, exportar historia completa y exportar evolucion individual). El frontend ya mostraba "nombre — especialidad" sin la palabra "Médico".

- [x] Conexiones a MySQL colgadas (encontradas en prod via `SHOW FULL PROCESSLIST` / `SHOW ENGINE INNODB STATUS`)
  - Hallazgo (incidente real en el VPS): `DELETE /api/pacientes/<id>` no tenia try/except. `evoluciones`, `recetas_electronicas`, `turnos` y `turnos_grupales` referencian `pacientes(id)` **sin `ON DELETE CASCADE`** (solo `historias` lo tiene) -> borrar un paciente con evoluciones/turnos/recetas asociadas choca con la FK -> `IntegrityError` sin capturar -> 500, pero ademas **la conexion nunca se cerraba ni se hacia rollback** (no habia `finally`). `database.py` no usa pool, cada request abre una conexion TCP nueva a MySQL (`mysql.connector.connect`) -> la transaccion quedaba abierta, sosteniendo un row lock, indefinidamente (hasta `wait_timeout` de MySQL, 8hs por defecto, o hasta un `KILL` manual como hizo Gero en prod).
  - Fix: `api_eliminar_paciente` ahora envuelve todo en `try/finally` (garantiza `cursor.close()`/`conn.close()` siempre) con un `except IntegrityError` interno que hace `rollback()` y devuelve 400 con mensaje claro en vez de 500 + conexion colgada. Con TDD: se extendio `FakeCursor` en `conftest.py` para poder simular una excepcion en un `execute()` especifico (`execute_side_effects`); test `test_eliminar_paciente_con_evoluciones_devuelve_400_no_500_y_hace_rollback` (rojo -> excepcion sin capturar, conexion nunca cerrada; verde -> 400, `rollback()` llamado, conexion cerrada). Verificado en vivo (docker): paciente con evolucion asociada -> DELETE devuelve 400 claro, y `SHOW FULL PROCESSLIST` en MySQL despues confirma que no queda ninguna conexion colgada.
  - Auditoria del resto de endpoints DELETE del sistema: `disponibilidades`, `usuarios` (baja logica, no DELETE real), `grupos`/`turnos_grupales`/`grupo_posteos` (FKs con `ON DELETE CASCADE`, sin este riesgo), `comunicados`, `ausencias`, `turnos` — no se encontro el mismo patron de FK sin cascada + sin try/except en los demas; `pacientes` era el unico caso con hijos no-cascade sin manejo de excepcion.
  - Referencia: `backend_flask/app/routes/pacientes_routes.py`, `backend_flask/tests/conftest.py`.
  - Defensa en profundidad (a pedido de Gero, ademas del fix de codigo): timeouts de MySQL bajados y persistidos en `docker-compose.yml` (`command:` del servicio `db`, mismo lugar donde ya vive `--default-time-zone`, para que sobrevivan a un restart del contenedor -- un `SET GLOBAL` a mano se pierde en el proximo restart): `wait_timeout=300`, `interactive_timeout=300` (una conexion viva-pero-idle por un bug futuro se mata sola a los 5 min en vez de 8hs), `innodb_lock_wait_timeout=10` (si una transaccion viva bloquea una fila, otras queries fallan rapido con error claro en vez de colgarse en cola). Antes de aplicar se verifico que ninguna operacion legitima del sistema mantiene una conexion abierta cerca de ese umbral: el codigo que sella/verifica en la TSA de BFA (`blockchain_routes.py`) sostiene la conexion durante la llamada HTTP externa, pero esa llamada tiene `timeout=30` (`bfa_client.py`) y es una unica request sin backoff bloqueante -- 300s da margen de sobra. Verificado en vivo: `SHOW VARIABLES LIKE '%timeout%'` en el contenedor `db` recien recreado confirma los 3 valores activos, y la app sigue funcionando normalmente (login, listar pacientes) tras el restart de la DB.
  - Nota: esto es una red de seguridad a nivel MySQL, no un reemplazo del fix de codigo -- si aparece el mismo patron (excepcion sin capturar que deja una conexion sin cerrar) en algun endpoint no auditado, ahora se autolimita a 5 minutos en vez de 8 horas, pero la causa raiz sigue siendo el codigo sin `try/finally`.

- [x] Ver Error 400
  - Causa real (peor de lo que parecia): `api_crear_paciente` solo validaba DNI duplicado. `nro_hc` es `UNIQUE NOT NULL` en la DB pero no se validaba, y el `INSERT` no tenia try/except -> al repetir un `nro_hc` (ej. cambiar el DNI pero olvidar cambiar el N° HC) explotaba con `IntegrityError` sin capturar -> **500** silencioso, no un 400 informativo.
  - Fix: se agrego validacion explicita de `nro_hc` duplicado (400 con mensaje claro) antes del INSERT, y se envolvio el INSERT en try/except `IntegrityError` como defensa ante condicion de carrera (400 en vez de 500). Con TDD: `test_crear_paciente_nro_hc_duplicado_devuelve_400_no_500` (rojo -> 200 con datos que antes rompian en runtime real; verde -> 400). Verificado en vivo (docker): crear con `nro_hc` repetido devuelve 400 "Ya existe un paciente con N° HC X", ya no 500.
  - Referencia: `backend_flask/app/routes/pacientes_routes.py`.

- [x] 500 al cargar un paciente "de 0" (causa distinta a la del punto anterior)
  - Hallazgo: reportado como "tambien pasa al cargar de 0" — se verifico que NO era el mismo bug que el DNI/nro_hc duplicado (un alta genuinamente nueva con datos unicos tambien rompia). Causa real: `cert_discapacidad` es `ENUM('Sí','No') DEFAULT NULL` en la DB. El `<select>` del form manda `""` cuando queda en "Seleccionar" (caso normal: paciente sin certificado). El backend hacia `if cert_discapacidad:` — con `""` (falsy) NUNCA entraba a normalizar, y el `""` crudo se insertaba en el ENUM -> MySQL strict mode: `1265 Data truncated for column 'cert_discapacidad'` -> 500 sin capturar. Reproducido en vivo con el payload exacto del form antes de tocar el codigo.
  - Fix directo (sin TDD, a pedido): normalizacion explicita en `api_crear_paciente` y `api_modificar_paciente` — cualquier valor que no sea literalmente "si"/"sí"/"no" (incluyendo `""`) ahora resuelve a `None`, nunca a un string vacio. Verificado en vivo (docker): el mismo payload que daba 500 ahora devuelve 200. Suite completa: 38 passed.
  - Referencia: `backend_flask/app/routes/pacientes_routes.py`.

- [x] Administrativo no podia configurar su disponibilidad horaria (403)
  - Hallazgo: `disponibilidades_routes.py` tenia `@requiere_rol` inconsistente entre metodos — el GET incluia `administrativo`, pero POST/PUT/DELETE no. La pantalla "Disponibilidad Horaria" (`DisponibilidadProfesional.vue`) cargaba bien (GET) pero al guardar cualquier dia, el POST/PUT devolvia 403 para ese rol.
  - Fix: se agrego `administrativo` a `@requiere_rol` en POST, PUT y DELETE de `disponibilidades_routes.py`, igualando al GET. Con TDD: `test_administrativo_puede_crear_su_disponibilidad` y `test_administrativo_puede_editar_disponibilidad` (rojo -> 403; verde -> 201/200). Verificado en vivo (docker): usuario `administrativo` de prueba crea su disponibilidad -> 201.
  - Referencia: `backend_flask/app/routes/disponibilidades_routes.py`.

- [ ] Agregar forms de faltas

- [x] Tandas no semanales (cada 2 semanas, cada 3, cada 4, etc)
  - Estado: implementado. Modificada la lógica del backend (`_generar_fechas_tanda` en `turnos_routes.py`) utilizando diferencia de semanas calendario modulo `frecuencia_semanas`. Añadido Dropdown de frecuencia (Semanal, Quincenal, Cada 3 semanas, Mensual) en `ModuloRehabilitacion.vue` y `CalendarioGrupo.vue` del frontend, enviando el nuevo parámetro al backend. Corregido además el bug de inicialización de conexión en el endpoint de tandas individuales del backend.

- [x] Diferentes colores para Turnos en Rehab / Grupos
  - Estado: cada grupo (`grupos_profesionales.color`) ya tenia color propio configurable en `CrearGrupo.vue`/`EditarGrupo.vue`, y el backend (`turnos_profesional_completo`, `turnos_por_grupo`, `listar_turnos_grupales`) ya lo devolvia. El bug real estaba en `ModuloRehabilitacion.vue`: `mapEvento()` ignoraba `t.color` y forzaba el mismo verde para todos los grupos, y ademas `calendar-medical.css` fuerza `.evento-rehab` con `!important`, pisando cualquier color inline de FullCalendar. Fix: se usa `t.color` (con fallback) para armar el evento, y se agrego `eventDidMount` que aplica el color por grupo via `style.setProperty(..., 'important')` para ganarle al `!important` del CSS global. Verificado en navegador con 2 grupos de colores distintos (rojo/azul): cada uno se ve con su propio color en la agenda de Rehabilitacion. Nota: los turnos individuales (no grupales) siguen con color fijo hardcodeado (`#1976D2`/`#007AFF`), eso no formaba parte de este pedido.

- [ ] Sección de Informes Particulares en Area - 

- [x] **Agregar campo 'Observaciones' en turnos (además de motivo)**
  - Detalle: Las observaciones son de uso interno y no deben enviarse al paciente en el mail del turno.
  - Notificación: El paciente recibe por mail el turno (fecha/hora) y el motivo (las observaciones quedan excluidas).

### Funcionalidad General

- [x] Cuando toco el cerrar sesion, por un momento el nombre del usuario pasa a ser 'Usuario' y luego de tocar algo mas recien cierra
  - Estado: ajustado logout para limpiar store y redirigir de inmediato; se removio fallback a `Usuario`.

- [x] Agendas: por defecto, cuando entro a la seccion debe mostrarme mi agenda, luego si tengo el permiso tendre el desplegable
  - Estado: ahora Director/Administrativo ven desplegable, pero la seleccion inicial es su propia agenda.

- [x] Los botones no permitidos NO deben ser visibles para quien no puede usarlos
  - Estado: ocultadas acciones de gestion de grupos para no-director y bloqueada carga de usuarios no permitida.

- [x] Agregar alternativas a Turnos ademas de Bloqueos:
  - Reunion
  - Turno
  - Bloqueo
  - Ausencia
  - Estado: modal de eventos de agenda con selector de tipo y persistencia via `motivo` etiquetado.

- [x] Agregar seccion de Comunicados, donde Directivos y Administrativos pueden postear Avisos institucionales
  - Estado: creada vista + servicios + endpoints `/api/comunicados`.

- [x] Agregar seccion de Posteos de Grupo en cada grupo, donde los integrantes del Equipo pueden postear comunicados para que el grupo lea
  - Estado: creada vista por grupo + servicios + endpoints `/api/grupos/<grupo_id>/posteos`.

- [ ] Comunicacion inter-grupos (puedo postear en los posteos de un grupo, ese posteo lo puedo ver yo y la gente del grupo, no otros)

- [ ] Respuesta a posteo (Marcar Leído / Ok)
