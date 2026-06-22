# Dashboard Inicio Operativo Design

## Objetivo

Redisenar el Dashboard de Inicio para que funcione como una consola diaria de agenda, no como un panel generico de contadores. El usuario debe ver que tiene que hacer hoy, cual es su proximo evento y que situaciones operativas requieren atencion.

## Alcance

- Reemplazar las tarjetas de Pacientes, Usuarios y Evoluciones por resumenes operativos.
- Mantener Turnos de Hoy como listado principal.
- Cambiar Proximo Turno por Proximo evento de agenda, incluyendo Turno, Reunion, Bloqueo o Ausencia.
- Mantener Disponibilidad, priorizando la disponibilidad del dia.
- Agregar Comunicados institucionales y posteos de grupos accesibles por el usuario.
- Mostrar Ausencias/Bloqueos y alertas operativas solo para roles `director` y `administrativo`.

## Roles

- `profesional` y `area`: ven su propia agenda, disponibilidad, proximo evento, turnos propios y comunicados accesibles.
- `director` y `administrativo`: ven agenda global del dia, disponibilidad por profesional, ausencias/bloqueos y alertas globales.

## Backend

El endpoint `/api/dashboard` sera la fuente principal del Inicio. Mantendra autenticacion con Flask-Login y devolvera una respuesta enriquecida con:

- `turnos`: turnos del dia filtrados por rol.
- `proximo_evento`: primer turno, reunion, bloqueo o ausencia futura segun acceso del rol.
- `disponibilidad_hoy`: disponibilidad activa del dia, propia o global.
- `ausencias_bloqueos`: eventos de ausencia, bloqueo o reunion proximos para roles administrativos.
- `alertas`: turnos superpuestos, profesionales con disponibilidad hoy y profesionales con agenda vacia teniendo disponibilidad hoy para roles administrativos.
- `comunicados`: ultimos institucionales y posteos de grupos accesibles.
- `resumen`: contadores operativos del dia.

No se agregan cambios de esquema.

## Frontend

`frontend/src/views/Dashboard.vue` presentara el dashboard con secciones por rol:

- encabezado con saludo y descripcion breve.
- resumen operativo compacto.
- Turnos de Hoy con hora, paciente y accion Ver historia.
- Proximo evento de agenda con tipo, horario, detalle y accion cuando sea turno.
- Disponibilidad de hoy.
- Comunicados.
- Para `director` y `administrativo`: alertas y ausencias/bloqueos.

## Testing

- Agregar pruebas backend para validar forma de respuesta y consultas principales por rol.
- Ejecutar pruebas de dashboard.
- Ejecutar lint frontend si las dependencias estan instaladas.
