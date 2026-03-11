<script setup>
import { ref, onMounted, reactive } from 'vue';
import { useRoute } from 'vue-router';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';

// Imports PrimeVue
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';

// ---------------------------------------------------------
// 🌍 LOCALE ESPAÑOL
// ---------------------------------------------------------
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

// ---------------------------------------------------------
// ⚙️ SETUP
// ---------------------------------------------------------
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
        turnoSeleccionado.value = {
            id: info.event.id,
            paciente: info.event.extendedProps.paciente,
            dni: info.event.extendedProps.dni,
            profesional: info.event.extendedProps.profesional,
            description: info.event.extendedProps.description,
            start: info.event.start
        };
        mostrarModal.value = true;
    },

    eventDidMount(info) {
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

// ---------------------------------------------------------
// 🎨 UTILIDAD: CALCULAR CONTRASTE (BLANCO/NEGRO)
// ---------------------------------------------------------
function getContrastColor(hexColor) {
    if (!hexColor) return '#ffffff';
    // Normalizar hex corto #FFF a #FFFFFF
    if (hexColor.length === 4) {
        hexColor = '#' + hexColor[1] + hexColor[1] + hexColor[2] + hexColor[2] + hexColor[3] + hexColor[3];
    }
    // Convertir a RGB
    const r = parseInt(hexColor.substr(1, 2), 16);
    const g = parseInt(hexColor.substr(3, 2), 16);
    const b = parseInt(hexColor.substr(5, 2), 16);
    // Fórmula de luminosidad YIQ
    const yiq = (r * 299 + g * 587 + b * 114) / 1000;
    // Si es oscuro devuelve blanco, si es claro devuelve negro
    return yiq >= 128 ? '#000000' : '#ffffff';
}

const formatearFecha = (date) => new Date(date).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
const formatearHora = (date) => new Date(date).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

// ---------------------------------------------------------
// 🚀 CARGA DE DATOS
// ---------------------------------------------------------
async function cargarTurnosGrupo() {
    try {
        const [resGrupo, resTurnos] = await Promise.all([fetch(`/api/grupos/${grupoId}`, { credentials: 'include' }), fetch(`/api/turnos/grupo/${grupoId}`, { credentials: 'include' })]);

        if (!resGrupo.ok || !resTurnos.ok) throw new Error('Error al cargar datos');

        grupo.value = await resGrupo.json();
        const dataTurnos = await resTurnos.json();

        // Mapear eventos con color inteligente
        eventos.value = dataTurnos.map((t) => {
            // Tomamos el color del grupo por defecto
            const bgColor = t.color || grupo.value.color || '#00936B';

            return {
                id: t.id,
                title: t.paciente,
                start: t.start,
                end: t.end,
                backgroundColor: bgColor,
                borderColor: 'transparent',
                // 👇 AQUI APLICAMOS LA MAGIA DEL CONTRASTE
                textColor: getContrastColor(bgColor),
                extendedProps: {
                    paciente: t.paciente,
                    dni: t.dni,
                    profesional: t.profesional,
                    description: t.description || 'Sin motivo'
                }
            };
        });

        calendarOptions.events = eventos.value;
    } catch (err) {
        console.error('Error cargando turnos grupales:', err);
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

            <div class="text-sm text-gray-500"><i class="pi pi-info-circle"></i> Haz clic en un turno para ver detalles</div>
        </div>

        <div class="flex-1 bg-white dark:bg-[#1e1e1e] rounded-xl shadow-lg p-4 overflow-hidden">
            <FullCalendar ref="fullCalendar" :options="calendarOptions" class="h-full" />
        </div>

        <Dialog v-model:visible="mostrarModal" modal header="Detalle del Turno" :style="{ width: '400px' }" class="p-fluid">
            <div v-if="turnoSeleccionado" class="space-y-4">
                <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                    <p class="text-sm text-gray-500 dark:text-gray-400">Paciente</p>
                    <p class="text-lg font-bold text-gray-800 dark:text-white">
                        {{ turnoSeleccionado.paciente }}
                    </p>
                    <p class="text-sm text-gray-600 dark:text-gray-300">DNI: {{ turnoSeleccionado.dni }}</p>
                </div>

                <div>
                    <p class="text-sm text-gray-500 dark:text-gray-400">Profesional / Área</p>
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
:deep(.fc-event-title) {
    font-weight: 700;
    font-size: 0.85rem;
}
:deep(.fc-event-time) {
    font-size: 0.75rem;
    opacity: 0.8; /* Ligeramente más suave que el título */
}

/* Modo Oscuro */
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
