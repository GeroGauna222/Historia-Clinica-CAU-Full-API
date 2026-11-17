// Reglas de las acciones de atención (Llamar / Finalizar / Volver a llamar) en la lista de turnos del día.
// Vocabulario en CONTEXT.md. El backend valida los permisos igual; esto solo decide qué botones mostrar.

export const idReal = (t) => t.turnoId || t.id;

export function claveTurno(t) {
    return `${t.es_grupal ? 'g' : 'i'}-${idReal(t)}`;
}

// ctx = { esAdmin, userId }. La lista de un profesional ya trae solo sus turnos y los de sus grupos;
// director y administrativo ven los de todos, y solo pueden llamar los individuales que son suyos.
export function puedeLlamar(t, { esAdmin, userId }) {
    if (t.estado_asistencia === 'con_aviso' || t.estado_asistencia === 'sin_aviso') return false;
    if (!esAdmin) return true;
    return !t.es_grupal && userId != null && t.usuario_id === userId;
}

function nombrePaciente(t) {
    return [t.paciente, t.apellido].filter(Boolean).join(' ').trim();
}

// Acciones disponibles para una fila, en orden de aparición.
// Volver a llamar un atendido solo está disponible en esta lista (no en el aviso de llegada ni en el menú de presentes, ver CONTEXT.md).
export function accionesAtencion(t, ctx) {
    if (!puedeLlamar(t, ctx)) return [];
    const paciente = nombrePaciente(t);
    const aria = (texto) => (paciente ? `${texto} ${paciente}` : texto);

    if (t.estado_atencion === 'en_atencion') {
        const acciones = [];
        // Un turno grupal termina solo (hora de fin del turno): el backend no tiene "finalizar" para grupales.
        if (!t.es_grupal) {
            acciones.push({ accion: 'finalizar', label: 'Finalizar', icon: 'pi pi-check', severity: 'secondary', text: false, ariaLabel: aria('Finalizar atención de') });
        }
        acciones.push({ accion: 'llamar', label: 'Volver a llamar', icon: 'pi pi-megaphone', severity: undefined, text: true, ariaLabel: aria('Volver a llamar a') });
        return acciones;
    }

    const label = t.estado_atencion === 'atendido' ? 'Volver a llamar' : 'Llamar';
    return [{ accion: 'llamar', label, icon: 'pi pi-megaphone', severity: undefined, text: false, ariaLabel: aria(`${label} a`) }];
}
