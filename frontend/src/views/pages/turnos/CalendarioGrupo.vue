<script setup>
import { ref, onMounted, reactive } from 'vue';
import { useRoute } from 'vue-router';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import api from '@/api/axios';

import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const route = useRoute();
const grupoId = route.params.grupoId;

const grupo = ref(null);
const eventos = ref([]);
const turnoSeleccionado = ref(null);
const mostrarModal = ref(false);
const rolUsuario = ref('');

const modalNuevoVisible = ref(false);
const DURACION_GRUPAL_DEFAULT = 20;
const DIAS_TANDA = [
    { value: 0, label: 'Lun' },
    { value: 1, label: 'Mar' },
    { value: 2, label: 'Mie' },
    { value: 3, label: 'Jue' },
    { value: 4, label: 'Vie' },
    { value: 5, label: 'Sab' },
    { value: 6, label: 'Dom' }
];
const nuevoTurno = reactive({
    modo_creacion: 'simple',
    fecha: '',
    fecha_base: '',
    hora_tanda: '',
    dias_tanda: [],
    cantidad_tanda: 4,
    pacienteBusqueda: '',
    paciente: null,
    motivo: '',
    duracion_minutos: DURACION_GRUPAL_DEFAULT
});
const pacientes = ref([]);
const guardandoNuevo = ref(false);

const modalEditarVisible = ref(false);
const editForm = reactive({
    fecha: '',
    motivo: '',
    duracion_minutos: DURACION_GRUPAL_DEFAULT
});
const guardandoEdicion = ref(false);
const eliminando = ref(false);

const puedeEditarGrupal = () => ['director', 'administrativo', 'area'].includes((rolUsuario.value || '').toLowerCase().trim());

const esLocale = {
    code: 'es',
    week: { dow: 1, doy: 4 },
    buttonText: { prev: 'Ant', next: 'Sig', today: 'Hoy', month: 'Mes', week: 'Semana', day: 'Dia', list: 'Agenda' },
    weekText: 'Sm',
    allDayText: 'Todo el dia',
    moreLinkText: 'mas',
    noEventsText: 'No hay eventos para mostrar'
};

function pad(n) {
    return String(n).padStart(2, '0');
}
function toLocalDateTimeString(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}
function toLocalDateString(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
function toLocalTimeString(date) {
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function jsDayToMondayIndex(jsDay) {
    return jsDay === 0 ? 6 : jsDay - 1;
}
function toPositiveMinutes(value, fallback = DURACION_GRUPAL_DEFAULT) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
    return Math.round(parsed);
}
function sumarMinutosISO(fechaISO, minutos) {
    const inicio = new Date(fechaISO);
    if (Number.isNaN(inicio.getTime())) return null;
    const fin = new Date(inicio.getTime() + toPositiveMinutes(minutos) * 60 * 1000);
    return toLocalDateTimeString(fin);
}
function minutosEntreFechas(inicio, fin) {
    const inicioDate = new Date(inicio);
    const finDate = new Date(fin);
    if (Number.isNaN(inicioDate.getTime()) || Number.isNaN(finDate.getTime())) return DURACION_GRUPAL_DEFAULT;
    const minutos = Math.round((finDate.getTime() - inicioDate.getTime()) / (60 * 1000));
    return toPositiveMinutes(minutos);
}

const calendarOptions = reactive({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'timeGridWeek',
    locale: esLocale,
    headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' },
    slotMinTime: '07:00:00',
    slotMaxTime: '22:00:00',
    allDaySlot: false,
    height: '100%',
    expandRows: true,
    stickyHeaderDates: true,
    slotEventOverlap: true,
    eventMaxStack: 6,
    events: eventos,
    dateClick(info) {
        if (!puedeEditarGrupal()) return;
        nuevoTurno.fecha = toLocalDateTimeString(info.date);
        nuevoTurno.modo_creacion = 'simple';
        nuevoTurno.fecha_base = toLocalDateString(info.date);
        nuevoTurno.hora_tanda = toLocalTimeString(info.date);
        nuevoTurno.dias_tanda = [jsDayToMondayIndex(info.date.getDay())];
        nuevoTurno.cantidad_tanda = 4;
        nuevoTurno.pacienteBusqueda = '';
        nuevoTurno.paciente = null;
        nuevoTurno.motivo = '';
        nuevoTurno.duracion_minutos = DURACION_GRUPAL_DEFAULT;
        pacientes.value = [];
        modalNuevoVisible.value = true;
    },
    eventClick(info) {
        const tipo = info.event.extendedProps.tipo;
        if (tipo === 'ausencia_bg') return;

        turnoSeleccionado.value = {
            id: info.event.extendedProps.turnoId || info.event.id,
            tipo,
            paciente: info.event.extendedProps.paciente,
            dni: info.event.extendedProps.dni,
            profesional: info.event.extendedProps.profesional,
            description: info.event.extendedProps.description,
            start: info.event.start,
            end: info.event.end,
            editable: Boolean(info.event.extendedProps.editable)
        };
        mostrarModal.value = true;
    },
    eventDidMount(info) {
        const tipo = info.event.extendedProps.tipo;
        if (tipo === 'ausencia_bg') return;
        if (tipo === 'ausencia') {
            tippy(info.el, {
                content: `<strong>No disponible:</strong> ${info.event.extendedProps.profesional || 'Profesional'}`,
                allowHTML: true,
                placement: 'top'
            });
            return;
        }

        tippy(info.el, {
            content: `<strong>${info.event.extendedProps.paciente || ''}</strong><br>${info.event.extendedProps.profesional || ''}`,
            allowHTML: true,
            placement: 'top'
        });
    }
});

async function cargarContextoUsuario() {
    const resp = await api.get('/usuarios/me', { withCredentials: true });
    rolUsuario.value = (resp.data?.rol || '').toLowerCase().trim();
}

function crearEventoIndividual(t) {
    return {
        id: `ind-${t.id}`,
        title: t.paciente,
        start: t.start,
        end: t.end,
        backgroundColor: t.color || grupo.value?.color || '#00936B',
        borderColor: t.color || grupo.value?.color || '#00936B',
        textColor: '#ffffff',
        classNames: ['evento-individual'],
        extendedProps: {
            tipo: 'turno_individual',
            turnoId: t.id,
            paciente: t.paciente,
            dni: t.dni,
            profesional: t.profesional,
            description: t.description || '',
            editable: false
        }
    };
}

function crearEventoGrupal(t) {
    return {
        id: `grp-${t.id}`,
        title: t.paciente,
        start: t.start,
        end: t.end,
        backgroundColor: 'rgba(37, 99, 235, 0.2)',
        borderColor: '#1d4ed8',
        textColor: '#111827',
        classNames: ['evento-grupal'],
        extendedProps: {
            tipo: 'turno_grupal',
            turnoId: t.id,
            paciente: t.paciente,
            dni: t.dni,
            profesional: `Grupo: ${t.grupo_nombre || grupo.value?.nombre || ''}`,
            description: t.description || '',
            editable: Boolean(t.editable)
        }
    };
}

function parseDateSafe(value) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return d;
}

function esDiaCompletoAusencia(ausencia, inicio, fin) {
    if (typeof ausencia?.es_dia_completo === 'boolean') return ausencia.es_dia_completo;
    if (!inicio || !fin) return false;
    return inicio.getHours() === 0 && inicio.getMinutes() === 0 && fin.getHours() === 23 && fin.getMinutes() === 59 && inicio.toDateString() === fin.toDateString();
}

function crearEventosAusencia(a) {
    const inicio = parseDateSafe(a.fecha_inicio);
    const fin = parseDateSafe(a.fecha_fin);
    if (!inicio || !fin) return [];

    const rows = [
        {
            id: `aus-${a.id}`,
            title: `No disponible: ${a.nombre_usuario}`,
            start: a.fecha_inicio,
            end: a.fecha_fin,
            backgroundColor: '#9ca3af',
            borderColor: '#6b7280',
            textColor: '#111827',
            classNames: ['evento-ausencia'],
            extendedProps: { tipo: 'ausencia', profesional: a.nombre_usuario, description: a.motivo || '' }
        }
    ];

    if (esDiaCompletoAusencia(a, inicio, fin)) {
        const inicioDia = new Date(inicio);
        inicioDia.setHours(0, 0, 0, 0);
        const finDia = new Date(inicioDia);
        finDia.setDate(finDia.getDate() + 1);
        rows.push({
            id: `aus-bg-${a.id}`,
            display: 'background',
            start: toLocalDateTimeString(inicioDia),
            end: toLocalDateTimeString(finDia),
            classNames: ['ausencia-background'],
            backgroundColor: 'rgba(156, 163, 175, 0.25)',
            extendedProps: { tipo: 'ausencia_bg' }
        });
    }
    return rows;
}

async function cargarTurnosGrupo() {
    const [resGrupo, resIndividuales, resGrupales, resAusencias] = await Promise.all([
        api.get(`/grupos/${grupoId}`, { withCredentials: true }),
        api.get(`/turnos/grupo/${grupoId}`, { withCredentials: true }),
        api.get('/turnos/grupales', { params: { grupo_id: grupoId }, withCredentials: true }),
        api.get(`/grupos/${grupoId}/ausencias`, { withCredentials: true })
    ]);

    grupo.value = resGrupo.data;
    const individuales = (resIndividuales.data || []).map(crearEventoIndividual);
    const grupales = (resGrupales.data || []).map(crearEventoGrupal);
    const ausencias = (resAusencias.data || []).flatMap(crearEventosAusencia);
    eventos.value = [...individuales, ...grupales, ...ausencias];
    calendarOptions.events = eventos.value;
}

async function buscarPacientes() {
    if (!nuevoTurno.pacienteBusqueda || nuevoTurno.pacienteBusqueda.length < 2) {
        pacientes.value = [];
        return;
    }
    const resp = await api.get(`/pacientes/buscar?q=${encodeURIComponent(nuevoTurno.pacienteBusqueda)}`, { withCredentials: true });
    pacientes.value = resp.data?.pacientes || [];
}

function seleccionarPaciente(p) {
    nuevoTurno.paciente = p;
    nuevoTurno.pacienteBusqueda = `${p.apellido} ${p.nombre} (DNI: ${p.dni})`;
    pacientes.value = [];
}

function toggleDiaTanda(day) {
    const pos = nuevoTurno.dias_tanda.indexOf(day);
    if (pos >= 0) {
        nuevoTurno.dias_tanda.splice(pos, 1);
    } else {
        nuevoTurno.dias_tanda.push(day);
        nuevoTurno.dias_tanda.sort((a, b) => a - b);
    }
}

async function crearTurnoGrupal() {
    if (!nuevoTurno.paciente) return;
    const esTanda = nuevoTurno.modo_creacion === 'tanda';
    const fechaInicioRef = esTanda ? `${nuevoTurno.fecha_base}T${nuevoTurno.hora_tanda}:00` : nuevoTurno.fecha;
    const fechaFin = sumarMinutosISO(fechaInicioRef, nuevoTurno.duracion_minutos);
    if (!fechaFin || !fechaInicioRef) {
        toast.add({ severity: 'error', summary: 'Fecha invalida', detail: 'No se pudo calcular la fecha de fin del turno.', life: 4500 });
        return;
    }
    if (esTanda && (!nuevoTurno.fecha_base || !nuevoTurno.hora_tanda || !nuevoTurno.dias_tanda.length || Number(nuevoTurno.cantidad_tanda) <= 0)) {
        toast.add({
            severity: 'warn',
            summary: 'Datos incompletos',
            detail: 'Para la tanda debe indicar fecha base, hora, dias y cantidad.',
            life: 4500
        });
        return;
    }
    guardandoNuevo.value = true;
    try {
        const resp = await api.post(
            '/turnos/grupales',
            {
                grupo_id: Number(grupoId),
                paciente_id: nuevoTurno.paciente.id,
                fecha_inicio: fechaInicioRef,
                fecha_fin: fechaFin,
                motivo: nuevoTurno.motivo,
                modo: esTanda ? 'tanda' : 'simple',
                dias_semana: esTanda ? nuevoTurno.dias_tanda : undefined,
                cantidad: esTanda ? Number(nuevoTurno.cantidad_tanda) : undefined,
                hora: esTanda ? nuevoTurno.hora_tanda : undefined
            },
            { withCredentials: true }
        );
        if (resp.data?.ajuste_horario?.aplicado) {
            toast.add({ severity: 'info', summary: 'Horario ajustado', detail: `Inicio ajustado a ${resp.data.ajuste_horario.inicio_ajustado}`, life: 4500 });
        } else if (esTanda && Number(resp.data?.cantidad_creada || 0) > 0) {
            toast.add({
                severity: 'success',
                summary: 'Tanda creada',
                detail: `Se crearon ${resp.data.cantidad_creada} turnos grupales.`,
                life: 4200
            });
        }
        modalNuevoVisible.value = false;
        await cargarTurnosGrupo();
    } finally {
        guardandoNuevo.value = false;
    }
}

function abrirEdicionGrupal() {
    if (!turnoSeleccionado.value || turnoSeleccionado.value.tipo !== 'turno_grupal') return;
    const d = new Date(turnoSeleccionado.value.start);
    editForm.fecha = toLocalDateTimeString(d);
    editForm.motivo = turnoSeleccionado.value.description || '';
    editForm.duracion_minutos = minutosEntreFechas(turnoSeleccionado.value.start, turnoSeleccionado.value.end);
    modalEditarVisible.value = true;
}

async function guardarEdicionGrupal() {
    if (!turnoSeleccionado.value) return;
    const fechaFin = sumarMinutosISO(editForm.fecha, editForm.duracion_minutos);
    if (!fechaFin) {
        toast.add({ severity: 'error', summary: 'Fecha invalida', detail: 'No se pudo calcular la fecha de fin del turno.', life: 4500 });
        return;
    }
    guardandoEdicion.value = true;
    try {
        const resp = await api.put(`/turnos/grupales/${turnoSeleccionado.value.id}`, { fecha_inicio: editForm.fecha, fecha_fin: fechaFin, motivo: editForm.motivo }, { withCredentials: true });
        if (resp.data?.ajuste_horario?.aplicado) {
            toast.add({ severity: 'info', summary: 'Horario ajustado', detail: `Inicio ajustado a ${resp.data.ajuste_horario.inicio_ajustado}`, life: 4500 });
        }
        modalEditarVisible.value = false;
        mostrarModal.value = false;
        await cargarTurnosGrupo();
    } finally {
        guardandoEdicion.value = false;
    }
}

async function eliminarTurnoGrupal() {
    if (!turnoSeleccionado.value) return;
    eliminando.value = true;
    try {
        await api.delete(`/turnos/grupales/${turnoSeleccionado.value.id}`, { withCredentials: true });
        mostrarModal.value = false;
        await cargarTurnosGrupo();
    } finally {
        eliminando.value = false;
    }
}

onMounted(async () => {
    await cargarContextoUsuario();
    await cargarTurnosGrupo();
});
</script>

<template>
    <div class="p-6 h-screen flex flex-col">
        <Toast />

        <div class="flex justify-between items-center mb-4">
            <h1 class="text-2xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                <span class="w-4 h-4 rounded-full" :style="{ backgroundColor: grupo?.color }"></span>
                Agenda de Grupo: {{ grupo?.nombre || 'Cargando...' }}
            </h1>
            <div class="text-sm text-gray-500">Turnos individuales + grupales</div>
        </div>

        <div class="flex-1 bg-surface-0 dark:bg-surface-900 rounded-xl shadow-lg p-4 overflow-hidden">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>

        <Dialog v-model:visible="modalNuevoVisible" modal header="Nuevo turno grupal" :style="{ width: '520px' }">
            <div class="space-y-3">
                <div>
                    <label class="font-semibold block mb-1">Modo de carga</label>
                    <select v-model="nuevoTurno.modo_creacion" class="w-full p-2 border border-gray-300 rounded">
                        <option value="simple">Simple (1 turno)</option>
                        <option value="tanda">Tanda (dias + hora + cantidad)</option>
                    </select>
                </div>
                <p v-if="nuevoTurno.modo_creacion === 'simple'" class="text-sm text-gray-500">Fecha/hora: {{ nuevoTurno.fecha }}</p>
                <div v-else class="space-y-2">
                    <div>
                        <label class="font-semibold block mb-1">Fecha base</label>
                        <InputText type="date" v-model="nuevoTurno.fecha_base" class="w-full" />
                    </div>
                    <div>
                        <label class="font-semibold block mb-1">Hora</label>
                        <InputText type="time" v-model="nuevoTurno.hora_tanda" class="w-full" />
                    </div>
                    <div>
                        <label class="font-semibold block mb-1">Dias</label>
                        <div class="flex flex-wrap gap-2">
                            <button
                                v-for="d in DIAS_TANDA"
                                :key="d.value"
                                type="button"
                                class="px-2 py-1 border rounded text-sm"
                                :class="nuevoTurno.dias_tanda.includes(d.value) ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'"
                                @click="toggleDiaTanda(d.value)"
                            >
                                {{ d.label }}
                            </button>
                        </div>
                    </div>
                    <div>
                        <label class="font-semibold block mb-1">Cantidad</label>
                        <InputText type="number" min="1" step="1" v-model.number="nuevoTurno.cantidad_tanda" class="w-full" />
                    </div>
                </div>
                <div>
                    <label class="font-semibold block mb-1">Paciente</label>
                    <InputText v-model="nuevoTurno.pacienteBusqueda" @input="buscarPacientes" class="w-full" placeholder="Buscar por DNI o nombre" />
                    <ul v-if="pacientes.length" class="border rounded mt-1 max-h-40 overflow-y-auto">
                        <li v-for="p in pacientes" :key="p.id" class="px-2 py-1 hover:bg-gray-100 cursor-pointer" @click="seleccionarPaciente(p)">{{ p.apellido }} {{ p.nombre }} ({{ p.dni }})</li>
                    </ul>
                </div>
                <div>
                    <label class="font-semibold block mb-1">Motivo</label>
                    <InputText v-model="nuevoTurno.motivo" class="w-full" />
                </div>
                <div>
                    <label class="font-semibold block mb-1">Duracion (minutos)</label>
                    <InputText type="number" min="5" step="5" v-model.number="nuevoTurno.duracion_minutos" class="w-full" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="modalNuevoVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoNuevo" @click="crearTurnoGrupal" />
            </template>
        </Dialog>

        <Dialog v-model:visible="mostrarModal" modal header="Detalle" :style="{ width: '460px' }">
            <div v-if="turnoSeleccionado" class="space-y-2">
                <p><strong>Paciente:</strong> {{ turnoSeleccionado.paciente }}</p>
                <p><strong>Profesional/Grupo:</strong> {{ turnoSeleccionado.profesional }}</p>
                <p><strong>Motivo:</strong> {{ turnoSeleccionado.description || 'Sin motivo' }}</p>
                <div class="flex justify-between mt-4">
                    <div class="flex gap-2">
                        <Button v-if="turnoSeleccionado.tipo === 'turno_grupal' && turnoSeleccionado.editable" label="Editar" icon="pi pi-pencil" text severity="warning" @click="abrirEdicionGrupal" />
                        <Button v-if="turnoSeleccionado.tipo === 'turno_grupal' && turnoSeleccionado.editable" label="Eliminar" icon="pi pi-trash" text severity="danger" :loading="eliminando" @click="eliminarTurnoGrupal" />
                    </div>
                    <Button label="Cerrar" text severity="secondary" @click="mostrarModal = false" />
                </div>
            </div>
        </Dialog>

        <Dialog v-model:visible="modalEditarVisible" modal header="Editar turno grupal" :style="{ width: '460px' }">
            <div class="space-y-3">
                <div>
                    <label class="font-semibold block mb-1">Fecha/hora</label>
                    <InputText type="datetime-local" v-model="editForm.fecha" class="w-full" />
                </div>
                <div>
                    <label class="font-semibold block mb-1">Motivo</label>
                    <InputText v-model="editForm.motivo" class="w-full" />
                </div>
                <div>
                    <label class="font-semibold block mb-1">Duracion (minutos)</label>
                    <InputText type="number" min="5" step="5" v-model.number="editForm.duracion_minutos" class="w-full" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="modalEditarVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoEdicion" @click="guardarEdicionGrupal" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
:deep(.evento-grupal) {
    border-style: dashed !important;
    border-width: 2px !important;
}

:deep(.evento-ausencia) {
    border-style: solid !important;
    border-width: 1px !important;
    border-color: #6b7280 !important;
    background-color: rgba(107, 114, 128, 0.72) !important;
    background-image: repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.24) 0 6px, rgba(255, 255, 255, 0.08) 6px 12px) !important;
    color: #111827 !important;
}

:deep(.fc .fc-bg-event.ausencia-background) {
    pointer-events: none !important;
    opacity: 1 !important;
    border: 0 !important;
    background-color: rgba(107, 114, 128, 0.2) !important;
    background-image: linear-gradient(180deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0)), repeating-linear-gradient(45deg, rgba(55, 65, 81, 0.2) 0 6px, rgba(55, 65, 81, 0.08) 6px 12px) !important;
}

:deep(html.dark .fc .fc-bg-event.ausencia-background),
:deep(.app-dark .fc .fc-bg-event.ausencia-background) {
    background-color: rgba(75, 85, 99, 0.3) !important;
    background-image: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(0, 0, 0, 0)), repeating-linear-gradient(45deg, rgba(209, 213, 219, 0.14) 0 6px, rgba(209, 213, 219, 0.05) 6px 12px) !important;
}
</style>
