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
import '@/assets/calendar-medical.css';

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
                content: `<strong>No disponible</strong><br>${info.event.extendedProps.profesional || 'Profesional'}<br><span style="opacity:0.7">${info.event.extendedProps.description || ''}</span>`,
                allowHTML: true,
                placement: 'top',
                theme: 'medical'
            });
            return;
        }

        const pacNombre = info.event.extendedProps.paciente || '';
        const profNombre = info.event.extendedProps.profesional || '';
        const desc = info.event.extendedProps.description || '';
        tippy(info.el, {
            content: `<strong>${pacNombre}</strong><br>${profNombre}${desc ? '<br><span style="opacity:0.7">' + desc + '</span>' : ''}`,
            allowHTML: true,
            placement: 'top',
            theme: 'medical'
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
        backgroundColor: t.color || grupo.value?.color || '#0891B2',
        borderColor: t.color || grupo.value?.color || '#0E7490',
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
        backgroundColor: 'rgba(8, 145, 178, 0.1)',
        borderColor: '#0891B2',
        textColor: '#134E4A',
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
            backgroundColor: 'rgba(239,68,68,0.12)',
            borderColor: '#EF4444',
            textColor: '#991B1B',
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

        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl flex items-center justify-center shadow-sm" :style="{ backgroundColor: grupo?.color || '#0891B2' }">
                    <i class="pi pi-users text-white text-lg"></i>
                </div>
                <div>
                    <h1 class="text-2xl font-heading font-bold text-[#134E4A] dark:text-teal-100 tracking-tight">{{ grupo?.nombre || 'Cargando...' }}</h1>
                    <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5 font-sans">Turnos individuales y grupales del equipo</p>
                </div>
            </div>
            <div class="flex items-center gap-4 flex-wrap">
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0891B2]/10 text-[#0891B2] dark:bg-cyan-900/30 dark:text-cyan-300 text-xs font-medium">
                    <span class="w-2 h-2 rounded-full bg-[#0891B2] inline-block"></span> Individual
                </span>
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0891B2]/5 border border-dashed border-[#0891B2] text-[#0891B2] dark:border-cyan-400 dark:text-cyan-300 text-xs font-medium">
                    <span class="w-2 h-2 rounded-full border-2 border-dashed border-[#0891B2] dark:border-cyan-400 inline-block"></span> Grupal
                </span>
                <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 text-xs font-medium">
                    <span class="w-2 h-2 rounded-full bg-red-400 dark:bg-red-500 inline-block"></span> Ausencia
                </span>
            </div>
        </div>

        <!-- Calendar container -->
        <div class="flex-1 bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-[#E0F2FE] dark:border-slate-700 p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>

        <!-- Modal: Nuevo turno grupal -->
        <Dialog v-model:visible="modalNuevoVisible" modal header="Nuevo turno grupal" :style="{ width: '540px' }" :pt="{ header: { class: 'font-heading' } }">
            <div class="space-y-4">
                <!-- Modo selector -->
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Modo de carga</label>
                    <div class="flex gap-2">
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer"
                            :class="nuevoTurno.modo_creacion === 'simple' ? 'bg-[#0891B2] text-white shadow-md' : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-[#E0F2FE] dark:border-slate-600 hover:border-[#0891B2]'"
                            @click="nuevoTurno.modo_creacion = 'simple'"
                        >
                            <i class="pi pi-calendar mr-1.5"></i> Simple
                        </button>
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer"
                            :class="nuevoTurno.modo_creacion === 'tanda' ? 'bg-[#0891B2] text-white shadow-md' : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-[#E0F2FE] dark:border-slate-600 hover:border-[#0891B2]'"
                            @click="nuevoTurno.modo_creacion = 'tanda'"
                        >
                            <i class="pi pi-replay mr-1.5"></i> Tanda
                        </button>
                    </div>
                </div>
                <!-- Simple mode -->
                <div v-if="nuevoTurno.modo_creacion === 'simple'" class="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#F0FDFA] dark:bg-teal-900/20 text-[#0891B2] dark:text-cyan-300 text-sm font-medium">
                    <i class="pi pi-calendar"></i> {{ nuevoTurno.fecha }}
                </div>
                <!-- Tanda mode -->
                <div v-else class="space-y-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-[#E0F2FE] dark:border-slate-700">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Fecha base</label>
                            <InputText type="date" v-model="nuevoTurno.fecha_base" class="w-full" />
                        </div>
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Hora</label>
                            <InputText type="time" v-model="nuevoTurno.hora_tanda" class="w-full" />
                        </div>
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Dias de la semana</label>
                        <div class="flex flex-wrap gap-1.5">
                            <button
                                v-for="d in DIAS_TANDA"
                                :key="d.value"
                                type="button"
                                class="w-10 h-10 rounded-lg text-sm font-semibold transition-all cursor-pointer"
                                :class="
                                    nuevoTurno.dias_tanda.includes(d.value) ? 'bg-[#0891B2] text-white shadow-md' : 'bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-300 border border-[#E0F2FE] dark:border-slate-600 hover:border-[#0891B2]'
                                "
                                @click="toggleDiaTanda(d.value)"
                            >
                                {{ d.label }}
                            </button>
                        </div>
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Cantidad de semanas</label>
                        <InputText type="number" min="1" step="1" v-model.number="nuevoTurno.cantidad_tanda" class="w-full" />
                    </div>
                </div>
                <!-- Paciente -->
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-user mr-1.5 text-[#0891B2]"></i>Paciente</label>
                    <InputText v-model="nuevoTurno.pacienteBusqueda" @input="buscarPacientes" class="w-full" placeholder="Buscar por DNI o nombre..." />
                    <ul v-if="pacientes.length" class="border border-[#E0F2FE] dark:border-slate-600 rounded-lg mt-1.5 max-h-40 overflow-y-auto bg-white dark:bg-slate-800 shadow-lg">
                        <li
                            v-for="p in pacientes"
                            :key="p.id"
                            class="px-3 py-2.5 hover:bg-[#F0FDFA] dark:hover:bg-teal-900/20 cursor-pointer transition-colors text-sm border-b border-[#E0F2FE] dark:border-slate-700 last:border-0"
                            @click="seleccionarPaciente(p)"
                        >
                            <span class="font-medium text-[#134E4A] dark:text-slate-200">{{ p.apellido }} {{ p.nombre }}</span> <span class="text-slate-400 ml-1">DNI: {{ p.dni }}</span>
                        </li>
                    </ul>
                    <div v-if="nuevoTurno.paciente" class="flex items-center gap-2 mt-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-xs font-medium">
                        <i class="pi pi-check-circle"></i> {{ nuevoTurno.paciente.apellido }} {{ nuevoTurno.paciente.nombre }}
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-comment mr-1.5 text-[#0891B2]"></i>Motivo</label>
                        <InputText v-model="nuevoTurno.motivo" class="w-full" />
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-clock mr-1.5 text-[#0891B2]"></i>Duracion (min)</label>
                        <InputText type="number" min="5" step="5" v-model.number="nuevoTurno.duracion_minutos" class="w-full" />
                    </div>
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" class="!rounded-lg" @click="modalNuevoVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoNuevo" class="!rounded-lg !bg-[#0891B2] !border-[#0891B2]" @click="crearTurnoGrupal" />
            </template>
        </Dialog>

        <!-- Modal: Detalle turno -->
        <Dialog v-model:visible="mostrarModal" modal header="Detalle del turno" :style="{ width: '480px' }" :pt="{ header: { class: 'font-heading' } }">
            <div v-if="turnoSeleccionado" class="space-y-4">
                <div class="flex items-center gap-3 p-3 rounded-lg bg-[#F0FDFA] dark:bg-teal-900/15">
                    <div class="w-9 h-9 rounded-full bg-[#0891B2] flex items-center justify-center text-white text-sm font-heading font-bold shrink-0">
                        {{ (turnoSeleccionado.paciente || '?')[0].toUpperCase() }}
                    </div>
                    <div>
                        <p class="font-semibold text-[#134E4A] dark:text-slate-200">{{ turnoSeleccionado.paciente }}</p>
                        <p class="text-xs text-slate-400">DNI: {{ turnoSeleccionado.dni }}</p>
                    </div>
                </div>
                <div class="space-y-2 text-sm">
                    <p class="flex items-center gap-2">
                        <i class="pi pi-users text-[#0891B2]"></i> <span class="text-slate-600 dark:text-slate-300">{{ turnoSeleccionado.profesional }}</span>
                    </p>
                    <p class="flex items-center gap-2">
                        <i class="pi pi-comment text-[#0891B2]"></i> <span class="text-slate-600 dark:text-slate-300">{{ turnoSeleccionado.description || 'Sin motivo' }}</span>
                    </p>
                </div>
                <div class="flex justify-between pt-4 border-t border-[#E0F2FE] dark:border-slate-700">
                    <div class="flex gap-2">
                        <Button v-if="turnoSeleccionado.tipo === 'turno_grupal' && turnoSeleccionado.editable" label="Editar" icon="pi pi-pencil" text severity="warning" class="!rounded-lg" @click="abrirEdicionGrupal" />
                        <Button v-if="turnoSeleccionado.tipo === 'turno_grupal' && turnoSeleccionado.editable" label="Eliminar" icon="pi pi-trash" text severity="danger" :loading="eliminando" class="!rounded-lg" @click="eliminarTurnoGrupal" />
                    </div>
                    <Button label="Cerrar" text severity="secondary" class="!rounded-lg" @click="mostrarModal = false" />
                </div>
            </div>
        </Dialog>

        <!-- Modal: Editar turno grupal -->
        <Dialog v-model:visible="modalEditarVisible" modal header="Editar turno grupal" :style="{ width: '480px' }" :pt="{ header: { class: 'font-heading' } }">
            <div class="space-y-4">
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-calendar mr-1.5 text-[#0891B2]"></i>Fecha/hora</label>
                    <InputText type="datetime-local" v-model="editForm.fecha" class="w-full" />
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-comment mr-1.5 text-[#0891B2]"></i>Motivo</label>
                        <InputText v-model="editForm.motivo" class="w-full" />
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-clock mr-1.5 text-[#0891B2]"></i>Duracion (min)</label>
                        <InputText type="number" min="5" step="5" v-model.number="editForm.duracion_minutos" class="w-full" />
                    </div>
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" class="!rounded-lg" @click="modalEditarVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoEdicion" class="!rounded-lg !bg-[#0891B2] !border-[#0891B2]" @click="guardarEdicionGrupal" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
/* Calendar Medical Clean theme is loaded from @/assets/calendar-medical.css */
</style>
