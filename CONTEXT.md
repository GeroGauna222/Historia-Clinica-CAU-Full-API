# Historia Clínica CAU

Sistema de historia clínica unificada y agenda de turnos del CAU. Este documento fija el lenguaje del dominio para que código, documentación y conversaciones usen los mismos términos.

## Language

### Agenda y atención

**Consultorio**:
Etiqueta del lugar físico donde atiende un profesional o un grupo, en texto libre (admite números y nombres, por ejemplo "3" o "Gimnasio").
_Avoid_: Sala, box, lugar de atención

**Turno grupal**:
Turno de un único paciente en la agenda compartida de un grupo; no es una sesión donde varios pacientes se atienden juntos.
_Avoid_: Sesión de grupo, sesión grupal

**Presente**:
Asistencia registrada de un paciente que llegó a la sala. Un presente que todavía no fue llamado está esperando; **Llamar** lo pasa a **En atención**.
_Avoid_: En curso

**Llamar**:
Acción con la que el profesional hace pasar a un paciente que está esperando.
_Avoid_: Marcar que pase, dar paso

**En atención**:
Estado de un turno desde que el paciente fue llamado hasta que termina su atención.
_Avoid_: En curso, turno actual

**Pantalla de llamados**:
Vista pública que se muestra en un televisor de la sala de espera con los turnos **En atención** y los que siguen en cada **Consultorio**.
_Avoid_: Gestor de turnos, TV, cartelera

**Nombre abreviado**:
Forma en que la **Pantalla de llamados** identifica al paciente: nombre de pila e inicial del apellido ("Juan P."), con una letra más del apellido si dos coinciden.

**Vincular**:
Acción con la que el director autoriza a un televisor a mostrar la **Pantalla de llamados**, cargando en el sistema el código que ese televisor muestra.
_Avoid_: Emparejar, parear, dar de alta la pantalla

## Relationships

- La **Pantalla de llamados** identifica al paciente solo por su **Nombre abreviado**, junto al **Consultorio** y el nombre del profesional; nunca muestra la especialidad ni el motivo del turno
- Un televisor muestra la **Pantalla de llamados** solo después de que el director lo **vincula**, y deja de mostrarla cuando el director lo desvincula
- En cada **Consultorio**, la **Pantalla de llamados** muestra como siguientes solo a los pacientes presentes que esperan, hasta tres, ordenados por horario de turno
- Director y administrativo eligen qué profesionales y grupos son visibles en la **Pantalla de llamados**; de los visibles, cada día aparecen solo los que tienen turnos ese día
- Un profesional o grupo nuevo no es visible en la **Pantalla de llamados** hasta que director o administrativo lo habilitan
- Un grupo sin **Consultorio** no puede ser visible en la **Pantalla de llamados**; un profesional sin **Consultorio** sí, identificado por su nombre
- Un profesional tiene asignado como máximo un **Consultorio**
- Un grupo tiene asignado como máximo un **Consultorio**
- Los profesionales usan **Consultorios** numerados; los grupos usan espacios con nombre
- Un profesional tiene como máximo un turno **En atención** a la vez: **Llamar** al siguiente termina la atención del anterior
- Un grupo puede tener varios **Turnos grupales** **En atención** a la vez: **Llamar** a un paciente no termina la atención de los demás, y cada atención termina sola al llegar la hora de fin de su turno o, si lo llamaron después de esa hora, cuando pasa la duración del turno contada desde el llamado
- **Llamar** a un paciente de la agenda propia lo hace el dueño de esa agenda; **Llamar** a un paciente de un **Turno grupal** lo hace cualquier miembro del grupo
- Un turno ya atendido se puede volver a **Llamar** solo desde la lista de turnos del día, no desde el aviso de llegada ni desde el menú de presentes
- Volver a **Llamar** un turno que ya está **En atención** solo repite el tono en la **Pantalla de llamados**; no cambia nada más
- No se puede **Llamar** a un paciente ausente ni a un turno que no es de hoy; **Llamar** a un paciente que figura como programado lo pasa a presente
- Marcar ausente o volver a "programado" un turno borra su atención; reprogramarlo también, y si cambia de día su asistencia vuelve a "programado"
- "Profesional" en estas reglas es cualquier usuario con agenda propia, sea de rol `profesional` o `area`

## Example dialogue

> **Dev:** "Si la Dra. Gómez atiende hoy en otro lado, ¿cambio el **Consultorio** del turno?"
> **Domain expert:** "No, el **Consultorio** es del profesional, no del turno. Se cambia en el profesional y aplica a todos sus turnos."

## Flagged ambiguities

- "en curso" se usaba en el Dashboard para el último turno marcado presente (el paciente llegó). Resuelto: el Dashboard pasa a mostrar los turnos **En atención** (el paciente fue llamado) y deja de derivarlo de la asistencia.
- "lugar de atención" ya existe en el sistema (`lugar_atencion_*` en usuarios) y significa el domicilio del establecimiento que figura en las recetas; no es el **Consultorio**.
