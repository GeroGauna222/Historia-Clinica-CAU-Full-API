<script setup>
import { ref, onMounted, reactive } from 'vue';
import { useRoute } from 'vue-router';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import ausenciasService from '@/service/ausenciasService';

// Imports PrimeVue
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';

const esLocale = {
    code: 'es',
    week: { dow: 1, doy: 4 },
    buttonText: {
        prev: 'Ant',
        next: 'Sig',
        today: 'Hoy',
        month: 'Mes',
        week: 'Semana',
        day: 'Dia',
        list: 'Agenda'
    },
    weekText: 'Sm',
    allDayText: 'Todo el dia',
    moreLinkText: 'mas',
    noEventsText: 'No hay eventos para mostrar'
};

const route = useRoute();
const grupoId = route.params.grupoId;
const grupo = ref(null);
const eventos = ref([]);
const turnoSeleccionado = ref(null);
const mostrarModal = ref(false);

const calendarOptions = reactive({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'timeGridWeek',
    locale: esLocale,
    headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay'
    },
    slotMinTime: '07:00:00',
    slotMaxTime: '22:00:00',
    allDaySlot: false,
    height: '100%',
    expandRows: true,
    stickyHeaderDates: true,
    slotEventOverlap: false,
    eventMaxStack: 4,
    events: eventos,

    eventClick(info) {
        const tipo = info.event.extendedProps.tipo;
        if (tipo === 'ausencia_bg') return;

        turnoSeleccionado.value = {
            id: info.event.id,
            tipo,
            paciente: info.event.extendedProps.paciente,
            dni: info.event.extendedProps.dni,
            profesional: info.event.extendedProps.profesional,
            description: info.event.extendedProps.description,
            start: info.event.start,
            end: info.event.end
        };
        mostrarModal.value = true;
    },

    eventDidMount(info) {
        const tipo = info.event.extendedProps.tipo;
        if (tipo === 'ausencia_bg') return;

        if (tipo === 'ausencia') {
            const profesional = info.event.extendedProps.profesional || 'Profesional';
            const motivo = info.event.extendedProps.description || 'Sin motivo';
            tippy(info.el, {
                content: `<strong>No disponible:</strong> ${profesional}<br><span style="opacity:0.8">${motivo}</span>`,
                allowHTML: true,
                placement: 'top'
            });
            return;
        }

        tippy(info.el, {
            content: `
        <div class="text-xs text-left">
          <strong>${info.event.extendedProps.paciente}</strong><br>
          <span style="opacity: 0.8">${info.event.extendedProps.profesional}</span>
        </div>
      `,
            allowHTML: true,
            placement: 'top'
        });
    }
});

function getContrastColor(hexColor) {
    if (!hexColor) return '#ffffff';
    if (hexColor.length === 4) {
        hexColor = '#' + hexColor[1] + hexColor[1] + hexColor[2] + hexColor[2] + hexColor[3] + hexColor[3];
    }
    const r = parseInt(hexColor.substr(1, 2), 16);
    const g = parseInt(hexColor.substr(3, 2), 16);
    const b = parseInt(hexColor.substr(5, 2), 16);
    const yiq = (r * 299 + g * 587 + b * 114) / 1000;
    return yiq >= 128 ? '#000000' : '#ffffff';
}

function pad(n) {
    return String(n).padStart(2, '0');
}

function toLocalDateTimeString(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function parseDateSafe(value) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return d;
}

function esDiaCompletoAusencia(ausencia, inicio, fin) {
    if (typeof ausencia?.es_dia_completo === 'boolean') return ausencia.es_dia_completo;
    if (!inicio || !fin) return false;

    return inicio.getHours() === 0 && inicio.getMinutes() === 0 && inicio.getSeconds() === 0 && fin.getHours() === 23 && fin.getMinutes() === 59 && fin.getSeconds() >= 59 && inicio.toDateString() === fin.toDateString();
}

function crearEventosAusencia(a) {
    const inicio = parseDateSafe(a.fecha_inicio);
    const fin = parseDateSafe(a.fecha_fin);
    if (!inicio || !fin) return [];

    const eventosAusencia = [
        {
            id: `ausencia-${a.id}`,
            title: `No disponible: ${a.nombre_usuario}`,
            start: a.fecha_inicio,
            end: a.fecha_fin,
            backgroundColor: '#9ca3af',
            borderColor: '#6b7280',
            textColor: '#111827',
            classNames: ['evento-ausencia'],
            extendedProps: {
                tipo: 'ausencia',
                profesional: a.nombre_usuario,
                description: a.motivo || 'Sin motivo'
            }
        }
    ];

    if (esDiaCompletoAusencia(a, inicio, fin)) {
        const inicioDia = new Date(inicio);
        inicioDia.setHours(0, 0, 0, 0);
        const finDia = new Date(inicioDia);
        finDia.setDate(finDia.getDate() + 1);

        eventosAusencia.push({
            id: `ausencia-bg-${a.id}`,
            display: 'background',
            start: toLocalDateTimeString(inicioDia),
            end: toLocalDateTimeString(finDia),
            classNames: ['ausencia-background'],
            backgroundColor: 'rgba(156, 163, 175, 0.25)',
            extendedProps: {
                tipo: 'ausencia_bg'
            }
        });
    }

    return eventosAusencia;
}

const formatearFecha = (date) => new Date(date).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
const formatearHora = (date) => new Date(date).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

async function cargarTurnosGrupo() {
    try {
        const [resGrupo, resTurnos, resAusencias] = await Promise.all([fetch(`/api/grupos/${grupoId}`, { credentials: 'include' }), fetch(`/api/turnos/grupo/${grupoId}`, { credentials: 'include' }), ausenciasService.listarPorGrupo(grupoId)]);

        if (!resGrupo.ok || !resTurnos.ok) throw new Error('Error al cargar datos');

        grupo.value = await resGrupo.json();
        const dataTurnos = await resTurnos.json();
        const dataAusencias = resAusencias.data || [];

        const eventosTurnos = dataTurnos.map((t) => {
            const bgColor = t.color || grupo.value.color || '#00936B';
            return {
                id: `turno-${t.id}`,
                title: t.paciente,
                start: t.start,
                end: t.end,
                backgroundColor: bgColor,
                borderColor: 'transparent',
                textColor: getContrastColor(bgColor),
                extendedProps: {
                    tipo: 'turno',
                    paciente: t.paciente,
                    dni: t.dni,
                    profesional: t.profesional,
                    description: t.description || 'Sin motivo'
                }
            };
        });

        const eventosAusencias = dataAusencias.flatMap((a) => crearEventosAusencia(a));
        eventos.value = [...eventosTurnos, ...eventosAusencias];
        calendarOptions.events = eventos.value;
    } catch (err) {
        console.error('Error cargando agenda grupal:', err);
    }
}

onMounted(() => {
    cargarTurnosGrupo();
});
</script>

<template>
    <div class="p-6 h-screen flex flex-col">
        <div class="flex justify-between items-center mb-4">
            <h1 class="text-2xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                <span class="w-4 h-4 rounded-full" :style="{ backgroundColor: grupo?.color }"></span>
                Agenda: {{ grupo?.nombre || 'Cargando...' }}
            </h1>

            <div class="text-sm text-gray-500"><i class="pi pi-info-circle"></i> Haz clic en un turno o bloqueo para ver detalles</div>
        </div>

        <div class="flex-1 bg-white dark:bg-[#1e1e1e] rounded-xl shadow-lg p-4 overflow-hidden">
            <FullCalendar ref="fullCalendar" :options="calendarOptions" class="h-full" />
        </div>

        <Dialog v-model:visible="mostrarModal" modal header="Detalle" :style="{ width: '420px' }" class="p-fluid">
            <div v-if="turnoSeleccionado" class="space-y-4">
                <div v-if="turnoSeleccionado.tipo === 'ausencia'" class="p-3 bg-gray-50 rounded-lg border-l-4 border-gray-500">
                    <p class="text-sm text-gray-500">Profesional</p>
                    <p class="text-lg font-bold text-gray-800 dark:text-white">{{ turnoSeleccionado.profesional }}</p>
                    <p class="text-sm text-gray-500 mt-2">Bloqueo</p>
                    <p class="font-medium">{{ formatearFecha(turnoSeleccionado.start) }} - {{ formatearHora(turnoSeleccionado.start) }} / {{ formatearHora(turnoSeleccionado.end) }}</p>
                    <p class="text-sm text-gray-600 mt-2"><strong>Motivo:</strong> {{ turnoSeleccionado.description || 'Sin motivo' }}</p>
                </div>

                <div v-else>
                    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                        <p class="text-sm text-gray-500 dark:text-gray-400">Paciente</p>
                        <p class="text-lg font-bold text-gray-800 dark:text-white">
                            {{ turnoSeleccionado.paciente }}
                        </p>
                        <p class="text-sm text-gray-600 dark:text-gray-300">DNI: {{ turnoSeleccionado.dni }}</p>
                    </div>

                    <div>
                        <p class="text-sm text-gray-500 dark:text-gray-400">Profesional / Area</p>
                        <p class="font-medium flex items-center gap-2">
                            <i class="pi pi-user-md text-green-600"></i>
                            {{ turnoSeleccionado.profesional }}
                        </p>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <p class="text-sm text-gray-500">Fecha</p>
                            <p class="font-medium">{{ formatearFecha(turnoSeleccionado.start) }}</p>
                        </div>
                        <div>
                            <p class="text-sm text-gray-500">Hora</p>
                            <p class="font-medium">{{ formatearHora(turnoSeleccionado.start) }}</p>
                        </div>
                    </div>

                    <div v-if="turnoSeleccionado.description">
                        <p class="text-sm text-gray-500">Motivo</p>
                        <p class="italic text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 p-2 rounded">"{{ turnoSeleccionado.description }}"</p>
                    </div>
                </div>
            </div>

            <template #footer>
                <Button label="Cerrar" icon="pi pi-times" text @click="mostrarModal = false" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
:deep(.fc) {
    font-family: inherit;
}

:deep(.fc-timegrid-event) {
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    border: none;
}

:deep(.evento-ausencia) {
    border-style: dashed !important;
    border-width: 2px !important;
}

:deep(.ausencia-background) {
    pointer-events: none !important;
}

:deep(.fc-event-title) {
    font-weight: 700;
    font-size: 0.85rem;
}

:deep(.fc-event-time) {
    font-size: 0.75rem;
    opacity: 0.8;
}

:deep(.app-dark .fc),
:deep(html.dark .fc) {
    --fc-page-bg-color: #1e1e1e;
    --fc-neutral-bg-color: #2a2a2a;
    --fc-list-event-hover-bg-color: #333;
    --fc-theme-standard-border-color: #333;
    color: #e5e7eb;
}

:deep(.app-dark .fc-col-header-cell),
:deep(html.dark .fc-col-header-cell) {
    background-color: #252525;
    color: #fff;
}
</style>
