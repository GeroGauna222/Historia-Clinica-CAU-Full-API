<script setup>
import { ref, onMounted, onUnmounted, reactive } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import api from '@/api/axios'; // Asegúrate de importar tu instancia de axios

// PrimeVue Imports
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';

/* -------------------------------------------------------------------------- */
/* LOCALE (SOLUCIÓN ERROR VITE)                                              */
/* -------------------------------------------------------------------------- */
const esLocale = {
    code: 'es',
    week: { dow: 1, doy: 4 },
    buttonText: {
        prev: 'Ant',
        next: 'Sig',
        today: 'Hoy',
        month: 'Mes',
        week: 'Semana',
        day: 'Día',
        list: 'Agenda'
    },
    weekText: 'Sm',
    allDayText: 'Todo el día',
    moreLinkText: 'más',
    noEventsText: 'No hay eventos para mostrar'
};

/* -------------------------------------------------------------------------- */
/* VARIABLES                                                                 */
/* -------------------------------------------------------------------------- */
const eventos = ref([]);
const leyendaGrupos = ref([]);
const turnoSeleccionado = ref(null);
const modalVisible = ref(false);
const editando = ref(false);
const fechaEdit = ref('');
const horaEdit = ref('');
const duracionTurno = ref(30);
const nombreProfesionalLogueado = ref('');

/* -------------------------------------------------------------------------- */
/* CONFIG CALENDARIO                                                         */
/* -------------------------------------------------------------------------- */
const calendarOptions = reactive({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'timeGridWeek',
    locale: esLocale,
    headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay'
    },
    slotMinTime: '08:00:00',
    slotMaxTime: '21:00:00',
    allDaySlot: false,
    height: '100%',

    // Lógica de superposición
    slotEventOverlap: true, // Permitir que se monten para ver conflictos
    eventOverlap: true,
    eventOrder: 'order', // Ordenar por prioridad (Mis turnos arriba)

    events: eventos,

    eventClick(info) {
        const e = info.event;
        turnoSeleccionado.value = {
            id: e.id, // ID del turno en BD
            turnoId: e.extendedProps.turnoId,
            tipo: e.extendedProps.tipo,
            editable: e.extendedProps.editable,
            paciente: e.extendedProps.paciente,
            dni: e.extendedProps.dni,
            profesional: e.extendedProps.profesional,
            description: e.extendedProps.description,
            start: e.start,
            end: e.end
        };
        editando.value = false;
        modalVisible.value = true;
    },

    eventDidMount(info) {
        if (info.event.extendedProps.tipo === 'ausencia') return;

        const desc = info.event.extendedProps.description || 'Sin motivo';
        const paciente = info.event.extendedProps.paciente;
        const profesional = info.event.extendedProps.profesional;
        const esGrupal = info.event.extendedProps.tipo === 'grupal';

        // Tooltip diferente si es mi turno o de un colega
        const tituloTooltip = esGrupal ? `<strong style="color: #ffcc80">${profesional}</strong><br>Paciente: ${paciente}` : `<strong>${paciente}</strong>`;

        tippy(info.el, {
            content: `${tituloTooltip}<br><span style="font-size:0.8em; opacity:0.8">${desc}</span>`,
            allowHTML: true,
            placement: 'top'
        });
    }
});

/* -------------------------------------------------------------------------- */
/* HELPERS                                                                   */
/* -------------------------------------------------------------------------- */
function stringToColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
    const c = (hash & 0x00ffffff).toString(16).toUpperCase();
    return '#' + '00000'.substring(0, 6 - c.length) + c;
}

function hexToRgba(hex, alpha) {
    if (!hex) return 'rgba(59, 130, 246, 1)';
    let c;
    if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
        c = hex.substring(1).split('');
        if (c.length == 3) c = [c[0], c[0], c[1], c[1], c[2], c[2]];
        c = '0x' + c.join('');
        return 'rgba(' + [(c >> 16) & 255, (c >> 8) & 255, c & 255].join(',') + ',' + alpha + ')';
    }
    return hex;
}

const formatearFecha = (date) => new Date(date).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
const formatearHora = (date) => new Date(date).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

/* -------------------------------------------------------------------------- */
/* LÓGICA DE DATOS                                                           */
/* -------------------------------------------------------------------------- */
async function cargarDatosUsuario() {
    try {
        const resp = await api.get('/usuarios/me', { withCredentials: true });
        const data = resp.data;
        duracionTurno.value = data.duracion_turno || 30;
        nombreProfesionalLogueado.value = data.nombre || data.email;
    } catch (e) {
        console.error('Error cargando usuario', e);
    }
}

async function cargarTurnosProfesional() {
    try {
        const resp = await api.get('/turnos/profesional/completo', { withCredentials: true });
        const data = resp.data;

        const mapaTurnos = new Map();
        const gruposDetectados = {};

        // Normalizar nombres para comparación
        const miNombre = (nombreProfesionalLogueado.value || '').toLowerCase().trim();

        data.forEach((t) => {
            const profNombre = (t.profesional || '').toLowerCase().trim();

            // Lógica de propiedad: ¿Es mi turno o de un grupo?
            const esPropio = miNombre && profNombre.includes(miNombre);
            const esGrupal = !esPropio;

            // Colores
            let colorFinal = esPropio ? '#1976D2' : stringToColor(t.profesional || 'Desconocido');

            if (!mapaTurnos.has(t.id)) {
                mapaTurnos.set(t.id, {
                    id: t.id,
                    title: esGrupal ? `${t.profesional} (${t.paciente})` : t.paciente,
                    start: t.start,
                    end: t.end,

                    // Estilos visuales
                    backgroundColor: esGrupal ? hexToRgba(colorFinal, 0.1) : colorFinal, // Fondo suave si es grupal
                    borderColor: colorFinal,
                    textColor: esGrupal ? '#333' : '#ffffff', // Texto oscuro si fondo es claro
                    classNames: esGrupal ? ['evento-grupal'] : ['evento-propio'],

                    extendedProps: {
                        order: esGrupal ? 0 : 10,
                        tipo: esGrupal ? 'grupal' : 'individual',
                        editable: esPropio ? t.editable === 1 || t.editable === true : false,
                        turnoId: t.id,
                        paciente: t.paciente,
                        dni: t.dni,
                        profesional: t.profesional,
                        description: t.description
                    }
                });
            }

            if (esGrupal) {
                gruposDetectados[t.profesional] = colorFinal;
            }
        });

        eventos.value = Array.from(mapaTurnos.values());
        calendarOptions.events = eventos.value;

        // Actualizar leyenda
        leyendaGrupos.value = Object.keys(gruposDetectados).map((nombre) => ({
            nombre,
            colorOriginal: gruposDetectados[nombre],
            colorTransparente: hexToRgba(gruposDetectados[nombre], 0.7)
        }));
    } catch (error) {
        console.error('Error cargando turnos:', error);
    }
}

/* -------------------------------------------------------------------------- */
/* OPERACIONES CRUD (Las que faltaban)                                       */
/* -------------------------------------------------------------------------- */
function iniciarEdicion() {
    const fechaObj = new Date(turnoSeleccionado.value.start);

    // Ajuste para input date/time (YYYY-MM-DD y HH:MM)
    // Nota: toISOString usa UTC, cuidado con la zona horaria. Mejor hacerlo manual.
    const anio = fechaObj.getFullYear();
    const mes = String(fechaObj.getMonth() + 1).padStart(2, '0');
    const dia = String(fechaObj.getDate()).padStart(2, '0');

    const hora = String(fechaObj.getHours()).padStart(2, '0');
    const min = String(fechaObj.getMinutes()).padStart(2, '0');

    fechaEdit.value = `${anio}-${mes}-${dia}`;
    horaEdit.value = `${hora}:${min}`;
    editando.value = true;
}

async function guardarEdicion() {
    if (!fechaEdit.value || !horaEdit.value) {
        alert('Fecha y hora son obligatorias');
        return;
    }

    try {
        const fechaHoraInicio = `${fechaEdit.value}T${horaEdit.value}:00`;

        await api.put(
            `/turnos/${turnoSeleccionado.value.id}`,
            {
                fecha: fechaHoraInicio,
                motivo: turnoSeleccionado.value.description
            },
            { withCredentials: true }
        );

        modalVisible.value = false;
        cargarTurnosProfesional(); // Recargar calendario
        alert('Turno actualizado correctamente');
    } catch (err) {
        console.error('Error actualizando turno:', err);
        alert('Error al actualizar: ' + (err.response?.data?.error || err.message));
    }
}

async function eliminarTurno() {
    if (!confirm('¿Seguro que deseas eliminar este turno?')) return;

    try {
        await api.delete(`/turnos/${turnoSeleccionado.value.id}`, { withCredentials: true });
        modalVisible.value = false;

        // Eliminar visualmente sin recargar todo (más rápido)
        eventos.value = eventos.value.filter((e) => e.id !== turnoSeleccionado.value.id);
        calendarOptions.events = eventos.value;
    } catch (err) {
        console.error('Error eliminando turno:', err);
        alert('Error al eliminar');
    }
}

let intervalo = null;

onMounted(async () => {
    await cargarDatosUsuario();
    await cargarTurnosProfesional();
    intervalo = setInterval(cargarTurnosProfesional, 60000);
});

onUnmounted(() => {
    clearInterval(intervalo);
});
</script>

<template>
    <div class="p-6 h-screen flex flex-col">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div>
                <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                    📅 Mi Agenda
                    <span class="text-xs font-normal text-gray-500 bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded">
                        {{ nombreProfesionalLogueado || 'Cargando...' }}
                    </span>
                </h1>
            </div>

            <div class="flex flex-wrap items-center gap-4 text-sm">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-blue-600 border border-blue-800"></span>
                    <span class="text-gray-800 dark:text-gray-200 font-medium">Mis Turnos</span>
                </div>

                <div v-for="g in leyendaGrupos" :key="g.nombre" class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full border border-dashed" :style="{ backgroundColor: g.colorTransparente, borderColor: g.colorOriginal }"></span>
                    <span class="text-gray-500 dark:text-gray-400 text-xs">
                        {{ g.nombre }}
                    </span>
                </div>
            </div>
        </div>

        <div class="flex-1 bg-white dark:bg-[#1b1b1b] rounded-2xl shadow border border-gray-200 dark:border-gray-700 p-4 overflow-hidden">
            <FullCalendar ref="fullCalendar" :options="calendarOptions" class="h-full" />
        </div>

        <Dialog v-model:visible="modalVisible" modal :header="editando ? 'Editar Turno' : 'Detalles del Turno'" :style="{ width: '450px' }" class="p-fluid">
            <div v-if="turnoSeleccionado" class="space-y-4">
                <div v-if="turnoSeleccionado.tipo === 'ausencia'" class="bg-red-50 p-4 rounded border border-red-200">
                    <p class="text-red-700 font-bold flex items-center gap-2"><i class="pi pi-ban"></i> Día Bloqueado</p>
                    <p class="text-gray-600 mt-2">{{ turnoSeleccionado.description || 'Sin motivo especificado' }}</p>
                </div>

                <div v-else>
                    <div v-if="editando">
                        <div class="field mb-3">
                            <label class="font-semibold block mb-1">Motivo / Descripción</label>
                            <InputText v-model="turnoSeleccionado.description" class="w-full" />
                        </div>

                        <div class="grid grid-cols-2 gap-4 mb-3">
                            <div class="field">
                                <label class="font-semibold block mb-1">Fecha</label>
                                <InputText type="date" v-model="fechaEdit" class="w-full" />
                            </div>
                            <div class="field">
                                <label class="font-semibold block mb-1">Hora</label>
                                <InputText type="time" v-model="horaEdit" class="w-full" />
                            </div>
                        </div>

                        <div class="flex justify-end gap-2 mt-4">
                            <Button label="Cancelar" severity="secondary" text @click="editando = false" />
                            <Button label="Guardar Cambios" icon="pi pi-check" @click="guardarEdicion" />
                        </div>
                    </div>

                    <div v-else>
                        <div class="p-3 rounded-lg border-l-4 mb-4" :class="turnoSeleccionado.editable ? 'bg-blue-50 border-blue-500' : 'bg-gray-50 border-gray-400 border-dashed'">
                            <p class="text-sm text-gray-500">Paciente</p>
                            <p class="text-lg font-bold text-gray-800">{{ turnoSeleccionado.paciente }}</p>
                            <p class="text-sm text-gray-600">DNI: {{ turnoSeleccionado.dni }}</p>

                            <div v-if="!turnoSeleccionado.editable" class="mt-2 text-xs text-gray-500 flex items-center gap-1">
                                <i class="pi pi-users"></i>
                                Turno de: <strong>{{ turnoSeleccionado.profesional }}</strong>
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-4 mb-3">
                            <div>
                                <span class="text-xs text-gray-500 uppercase font-bold">Fecha</span>
                                <p>{{ formatearFecha(turnoSeleccionado.start) }}</p>
                            </div>
                            <div>
                                <span class="text-xs text-gray-500 uppercase font-bold">Hora</span>
                                <p>{{ formatearHora(turnoSeleccionado.start) }}</p>
                            </div>
                        </div>

                        <div class="mb-4">
                            <span class="text-xs text-gray-500 uppercase font-bold">Motivo</span>
                            <p class="italic text-gray-700 bg-gray-100 p-2 rounded text-sm">
                                {{ turnoSeleccionado.description || 'Sin motivo' }}
                            </p>
                        </div>

                        <div class="flex justify-between items-center pt-4 border-t border-gray-100">
                            <div v-if="turnoSeleccionado.editable" class="flex gap-2">
                                <Button icon="pi pi-pencil" severity="warning" text rounded v-tooltip="'Editar'" @click="iniciarEdicion" />
                                <Button icon="pi pi-trash" severity="danger" text rounded v-tooltip="'Eliminar'" @click="eliminarTurno" />
                            </div>
                            <div v-else class="text-xs text-gray-400 italic">Solo lectura (Grupo)</div>

                            <Button label="Cerrar" severity="secondary" text @click="modalVisible = false" />
                        </div>
                    </div>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<style scoped>
/* CLASES DINÁMICAS PARA FULLCALENDAR */
:deep(.evento-grupal) {
    border-style: dashed !important;
    border-width: 2px !important;
    z-index: 1 !important;
}

:deep(.evento-propio) {
    border-style: solid !important;
    border-width: 0 !important;
    border-left-width: 4px !important; /* Estilo moderno: barra lateral */
    z-index: 10 !important;
    box-shadow:
        0 4px 6px -1px rgba(0, 0, 0, 0.1),
        0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

:deep(.fc-event-title) {
    font-weight: 600;
}

/* Modo Oscuro */
:deep(.app-dark .fc),
:deep(html.dark .fc) {
    --fc-page-bg-color: #1b1b1b;
    --fc-neutral-bg-color: #2a2a2a;
    --fc-list-event-hover-bg-color: #333;
    --fc-theme-standard-border-color: #333;
    color: #e5e7eb;
}
</style>
