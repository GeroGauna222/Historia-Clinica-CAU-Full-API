# Pantalla de llamados — diseño

Fecha: 2026-11-16 · Estado: implementado en la rama `feat/pantalla-de-llamados` (pendiente el recorrido manual en el televisor real)

Vocabulario en [`CONTEXT.md`](../../../CONTEXT.md). Decisión de acceso sin sesión en [`ADR 0001`](../../adr/0001-pantalla-de-llamados-sin-sesion.md).

## Objetivo

Un televisor en la sala de espera muestra, por consultorio, los pacientes **en atención** y los que siguen. El profesional **llama** al paciente desde el sistema (lista de turnos del día o aviso de llegada) y la pantalla se actualiza sola, con un tono.

## Enfoque

- Ruta pública `/pantalla` en el frontend Vue, fuera del layout con menú, más un blueprint nuevo `backend_flask/app/routes/pantalla_routes.py`.
- El televisor consulta cada 5 s. Descartados: página HTML estática servida por Nginx (queda como plan B si el navegador del televisor no carga el frontend) y WebSocket/SSE (sin necesidad a este volumen).
- El primer paso del plan es abrir una página de prueba en el televisor real.

## 1. Datos

### Columnas nuevas

| Tabla | Columna | Tipo |
|---|---|---|
| `usuarios` | `consultorio` | `VARCHAR(50) NULL` (`utf8mb4_unicode_ci` explícito) |
| `usuarios` | `mostrar_en_pantalla` | `TINYINT(1) NOT NULL DEFAULT 0` |
| `grupos_profesionales` | `consultorio`, `mostrar_en_pantalla` | ídem |
| `turnos`, `turnos_grupales` | `atencion_inicio`, `atencion_fin` | `DATETIME NULL` |

### Tabla nueva `pantallas` (un registro por televisor)

`id`, `nombre`, `codigo` (6 caracteres), `codigo_expira`, `clave_hash` (hash de la clave, nunca la clave), `vinculada_en`, `vinculada_por`, `revocada_en`, `ultimo_acceso`, `creado_en`.

Va en `db/init.sql` y en `db/migrations/20261116_pantalla_de_llamados.sql`. Los `INSERT` existentes usan listas de columnas explícitas, así que las columnas nuevas nullable no los rompen.

### Estado de atención (se deriva al leer, sin cron)

- **Esperando:** `estado_asistencia = 'presente'` y sin `atencion_inicio`.
- **En atención (individual):** `atencion_inicio` de hoy y sin `atencion_fin`.
- **En atención (grupal):** igual, y todavía no llegó la hora de cierre.
- **Atendido:** tiene `atencion_fin`, o es grupal y pasó la hora de cierre, o cambió el día.

Cierre de un grupal: `fecha_fin` del turno; si lo llamaron después, `atencion_inicio` + duración del turno (10:00–10:30 llamado a las 10:35 cierra a las 11:05).

`llamar` siempre fija `atencion_inicio = NOW()` y `atencion_fin = NULL`. Por eso volver a llamar un turno en atención refresca `atencion_inicio`, y el televisor detecta el llamado nuevo porque ese valor cambió. El tono depende de ese cambio.

Se usa el reloj de MySQL (`NOW()`/`CURDATE()`), como ya hace `presentes-hoy`.

### Reglas que interactúan con lo existente

1. Reprogramar un turno (`PUT /api/turnos/<id>` y `/grupales/<id>`) borra la atención si cambia fecha u hora; si cambia de día, `estado_asistencia` vuelve a `programado`.
2. Dashboard: `turno_en_curso` y `atenciones_en_curso` salen de los turnos en atención, con los mismos nombres de campo. Quedan vacíos si nadie fue llamado.
3. Llamar tiene permiso propio: el dueño del turno (individual) o miembros del grupo vía `grupo_miembros` (grupal). No depende de `ROLES_TURNOS_GRUPALES`.
4. Cambiar la asistencia a algo distinto de `presente` borra la atención.
5. Un grupo sin consultorio no puede ser visible. Un profesional sin consultorio sí (se identifica por nombre).
6. "Profesional" es cualquier usuario con agenda propia (`profesional` o `area`). El aviso de llegada solo salta para rol `profesional`; los `area` llaman desde la lista del día.
7. No interactúa con sobreturnos, borrado de turnos, login, facturación ni usuarios inactivos (un profesional inactivo deja de aparecer).

## 2. Backend

### Con sesión

| Endpoint | Roles | Función |
|---|---|---|
| `POST /api/turnos/<id>/llamar` | dueño del turno | Abre la atención, cierra la otra atención abierta del profesional, `programado` → `presente`. 403 si no es el dueño; 409 si está ausente o no es de hoy. Sobre un turno atendido lo reabre. |
| `POST /api/turnos/<id>/finalizar` | dueño | Cierra la atención. |
| `POST /api/turnos/grupales/<id>/llamar` | miembro del grupo | Abre la atención sin cerrar las demás. 403 si no es miembro; 409 si está ausente o no es de hoy. No hay `finalizar` para grupales. |
| `GET /api/pantalla/vista-previa` | director, administrativo | Misma función que usa el televisor. |
| `GET /api/pantalla/visibles` | director, administrativo | Profesionales y grupos con consultorio, visibilidad y si tienen turnos hoy. |
| `PATCH /api/pantalla/visibles/<tipo>/<id>` | director, administrativo | Visibilidad y consultorio. Rechaza grupo visible sin consultorio (400); un profesional visible sin consultorio se acepta. Un cuerpo que no es un objeto JSON responde 400 con la clave `message`; los demás rechazos usan `error`. |
| `GET /api/pantalla/televisores` | director | Lista de televisores. |
| `POST /api/pantalla/televisores` | director | Recibe código y nombre, vincula. |
| `DELETE /api/pantalla/televisores/<id>` | director | Desvincula (revoca la clave). |

Director y administrativo no llaman en nombre de un profesional. No se reutiliza el patrón laxo de `PATCH /api/turnos/<id>/asistencia`, que cae a `turnos_grupales` por el mismo id sin chequear membresía.

### Sin sesión (ADR 0001)

- `POST /api/pantalla/vinculacion`: el televisor pide un código y recibe código y clave. La clave no sirve hasta que se vincula.
- `GET /api/pantalla/llamados` con la clave en un encabezado: tarjetas si está vinculada, "pendiente" si todavía no, 401 si fue revocada o venció.
- Código de 6 caracteres sin confundibles (sin 0, O, 1, I, L), vence a los 10 minutos. Máximo 20 pedidos pendientes; los vencidos se borran en cada pedido nuevo.

### Contenido de cada tarjeta

Consultorio, nombre del profesional, pacientes en atención y hasta tres siguientes (presentes que esperan, por horario de turno). Los pacientes se identifican solo por **Nombre abreviado**: primera palabra del nombre más inicial del apellido ("María G."), con una letra más del apellido si dos coinciden. Nunca viajan nombre completo, DNI, especialidad ni motivo. El único dato extra por paciente es el valor de `atencion_inicio`, que el televisor usa para detectar llamados nuevos.

### Endpoints existentes

`presentes-hoy`, agenda y Dashboard agregan `estado_atencion` (`esperando`, `en_atencion`, `atendido`). No se quita ni renombra nada. Los `PUT` de usuario y grupo aceptan `consultorio`; los formularios siguen siendo solo de director, y administrativo lo edita desde la lista de visibles.

## 3. Frontend

### Televisor (`/pantalla`, pública)

- **Sin vincular:** código en grande con la indicación de pedirle al director que lo cargue; se renueva solo al vencer.
- **Vinculada:** tarjetas, reloj y botón "Activar sonido" (operable con control remoto, desaparece al activarse).
- **Desvinculada:** borra la clave y muestra un código nuevo.
- Tarjeta: consultorio grande, profesional, en atención, hasta tres siguientes.
- Orden: consultorios numerados ascendente, espacios con nombre alfabético, profesionales sin consultorio al final. Una tarjeta por profesional o grupo.
- Fondo oscuro, letra grande, sin scroll. Hasta 12 tarjetas por página (`porPagina`) en una grilla de 1 a 4 columnas; con más, páginas que rotan cada 10 s. Con 4 tarjetas o menos la página usa la clase `grande` (letra ×1.4) y con 10 o más la clase `densa` (×0.85).
- Tono: el mismo del aviso de llegada, en cada llamado nuevo, incluido "Volver a llamar". Sin anuncio grande en pantalla.
- La clave se guarda en `localStorage` del televisor.
- `/pantalla` se declara pública con `meta.publica` en `router/index.js`; el guard (`router/accesoRutas.js`) y el interceptor 401 de `api/axios.js` leen esa marca en lugar de comparar rutas por texto.

### Vista "Pantalla de llamados" (menú; director y administrativo)

- **Vista previa:** mismo componente que el televisor.
- **Visibles:** tabla con consultorio editable e interruptor de visibilidad; avisa si alguien tiene turnos hoy y está oculto.
- **Televisores (solo director):** campo de código y nombre, lista con último acceso, "Desvincular".

### Pantallas existentes

- Lista de turnos del día del Dashboard: "Llamar", "Finalizar" o "Volver a llamar" según el estado, solo en turnos propios o de grupos del usuario. "Volver a llamar" también sobre turnos ya en atención: solo repite el tono.
- Aviso de llegada (`ArrivalNoticeDialog`): botón "Llamar" por paciente, que llama y da por informado solo a ese paciente. "Informado" sigue cerrando sin llamar.
- Menú de presentes: esperando / en atención / atendido, con "Llamar" solo en los que esperan.
- Widget de atención del Dashboard (`ProximoTurnoWidget`): muestra al paciente llamado como "En atención" (profesional) o "Pacientes en atención" (director); ya no usa "en curso" ni la etiqueta "Presente" en el texto visible; los nombres de campos del API (`atenciones_en_curso`, `turno_en_curso`) se mantienen.
- Formularios de usuario y grupo: campo Consultorio.
- Las llamadas van por `src/service/*`, no por axios directo.

## 4. Errores

**Televisor**
- Sin respuesta: sigue mostrando lo último y reintenta cada 5 s; a los 30 s oculta las tarjetas y muestra "Reconectando…". Vuelve sola.
- Código vencido: pide otro solo. Desvinculado o `localStorage` borrado: muestra código nuevo.
- Sin sonido activado: funciona sin tono y el botón queda visible. Cada vez que se abre la página alguien debe activarlo una vez (limitación de los navegadores).
- Al abrir con llamados ya hechos no suena; solo los posteriores, un tono por actualización como máximo.

**Llamar**
- Turno ausente o de otro día: rechazo con mensaje, sin cambios.
- Falla de red: muestra el error y el botón queda disponible; en el aviso de llegada el paciente no se da por informado.
- Dos miembros llaman al mismo tiempo: queda un solo llamado.
- Un profesional llama dos pacientes desde dos pestañas: queda en atención el último.

**Vincular y configurar**
- Código inválido o vencido: mensaje claro.
- Más de 20 pedidos pendientes: el televisor muestra "Probá en unos minutos". Un tercero podría bloquear vinculaciones nuevas mientras insista; los televisores ya vinculados no se afectan.
- Quitar el consultorio a un grupo visible: se rechaza hasta ocultarlo.

## 5. Pruebas

**Backend (pytest con `FakeConnection`/`FakeCursor`).** Como la base está simulada, el estado de atención y el Nombre abreviado se calculan en funciones Python y se prueban directo.
- Estado de atención: esperando, en atención y atendido; cierre grupal a horario, con llamado tardío y con cambio de día.
- Nombre abreviado: compuestos, varios apellidos, coincidencias.
- Llamar/finalizar: permisos, cierre del anterior solo en individuales, programado → presente, rechazo de ausentes y de otro día, reapertura, repetición sobre un turno en atención.
- Limpieza: cambio de asistencia, reprogramación el mismo día y a otro día.
- Pantalla: respuesta pendiente, vinculada y revocada; solo campos permitidos; permisos por rol; grupo visible sin consultorio.
- Dashboard: "en curso" sale de los turnos en atención.

**Frontend (vitest).** Orden y paginado de tarjetas; detección de llamado nuevo para el tono; `/pantalla` abre sin sesión y un 401 ahí no redirige al login.

**A mano.**
1. Primero: página de prueba en el televisor real. Si el navegador no carga el frontend, agregar compilación para navegadores viejos solo para esa página (o el plan B estático).
2. Recorrido completo: vincular, llamar desde la sesión de un profesional, ver el cambio y el tono en menos de 5 s, cortar la red, desvincular.
3. Migración sobre la base de desarrollo, comparando con `init.sql`.
