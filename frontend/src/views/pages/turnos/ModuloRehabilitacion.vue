<script setup>
import { ref, reactive, onMounted } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import api from '@/api/axios';
import { fechaBonitaCompleta } from '@/utils/formatDate';
import '@/assets/calendar-medical.css';

import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import Textarea from 'primevue/textarea';

const toast = useToast();

const gruposRehab = ref([]);
const filtroGrupoId = ref('');
const rolUsuario = ref('');
const eventos = ref([]);
const seleccionado = ref(null);
const detalleVisible = ref(false);

const ausenciasConteoNuevoTurno = ref(null);
const ausenciasConteoDetalle = ref(null);
const guardandoAusencia = ref(false);

async function fetchAusenciasConteo(pacienteId) {
    ausenciasConteoNuevoTurno.value = null;
    try {
        const res = await api.get(`/pacientes/${pacienteId}/ausencias`, { withCredentials: true });
        ausenciasConteoNuevoTurno.value = res.data;
        if (res.data && res.data.sin_aviso >= 3) {
            toast.add({
                severity: 'warn',
                summary: 'Alerta de Ausencias',
                detail: `El paciente seleccionado tiene ${res.data.sin_aviso} ausencias sin aviso.`,
                life: 6000
            });
        }
    } catch (e) {
        console.error(e);
    }
}

async function guardarAsistenciaTurno(estado) {
    if (!seleccionado.value) return;
    guardandoAusencia.value = true;
    try {
        const url = `/turnos/grupales/${seleccionado.value.turnoId}/asistencia`;
        await api.patch(url, { estado_asistencia: estado }, { withCredentials: true });
        seleccionado.value.estado_asistencia = estado;
        seleccionado.value.ausencia = estado === 'con_aviso' || estado === 'sin_aviso' ? estado : null;

        // Recargar agenda para refrescar color
        await cargarTurnos();

        // Volver a buscar conteo para actualizar el detalle
        if (seleccionado.value.paciente_id) {
            const res = await api.get(`/pacientes/${seleccionado.value.paciente_id}/ausencias`, { withCredentials: true });
            ausenciasConteoDetalle.value = res.data;
        }
        toast.add({ severity: 'success', summary: 'Estado de asistencia', detail: 'Se actualizó el estado de asistencia correctamente.', life: 3000 });
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo actualizar el estado de asistencia.', life: 3500 });
    } finally {
        guardandoAusencia.value = false;
    }
}

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
const opcionesFrecuencia = [
    { label: 'Semanal (Cada 1 semana)', value: 1 },
    { label: 'Quincenal (Cada 2 semanas)', value: 2 },
    { label: 'Cada 3 semanas', value: 3 },
    { label: 'Mensual (Cada 4 semanas)', value: 4 }
];
const nuevo = reactive({
    modo_creacion: 'simple',
    grupo_id: '',
    fecha_inicio: '',
    fecha_base: '',
    hora_tanda: '',
    dias_tanda: [],
    cantidad_tanda: 4,
    frecuencia_semanas: 1,
    motivo: '',
    observaciones: '',
    pacienteBusqueda: '',
    paciente: null,
    duracion_minutos: DURACION_GRUPAL_DEFAULT
});
const pacientes = ref([]);
const guardandoNuevo = ref(false);

const modalEditarVisible = ref(false);
const edit = reactive({
    fecha_inicio: '',
    motivo: '',
    observaciones: '',
    duracion_minutos: DURACION_GRUPAL_DEFAULT
});
const guardandoEdit = ref(false);
const eliminando = ref(false);

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
function canEdit() {
    return ['director', 'administrativo', 'area'].includes((rolUsuario.value || '').toLowerCase().trim());
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
    events: eventos,
    dateClick(info) {
        if (!canEdit()) return;
        nuevo.modo_creacion = 'simple';
        nuevo.fecha_inicio = toLocalDateTimeString(info.date);
        nuevo.fecha_base = toLocalDateString(info.date);
        nuevo.hora_tanda = toLocalTimeString(info.date);
        nuevo.dias_tanda = [jsDayToMondayIndex(info.date.getDay())];
        nuevo.cantidad_tanda = 4;
        nuevo.paciente = null;
        nuevo.pacienteBusqueda = '';
        nuevo.motivo = '';
        nuevo.observaciones = '';
        nuevo.duracion_minutos = DURACION_GRUPAL_DEFAULT;
        pacientes.value = [];
        if (filtroGrupoId.value) nuevo.grupo_id = filtroGrupoId.value;
        modalNuevoVisible.value = true;
    },
    eventClick(info) {
        seleccionado.value = {
            id: info.event.extendedProps.turnoId || info.event.id,
            turnoId: info.event.extendedProps.turnoId,
            grupo_nombre: info.event.extendedProps.grupo_nombre,
            paciente: info.event.extendedProps.paciente,
            dni: info.event.extendedProps.dni,
            paciente_id: info.event.extendedProps.paciente_id,
            description: info.event.extendedProps.description,
            observaciones: info.event.extendedProps.observaciones,
            ausencia: info.event.extendedProps.ausencia,
            estado_asistencia: info.event.extendedProps.estado_asistencia || (info.event.extendedProps.ausencia ? info.event.extendedProps.ausencia : 'programado'),
            editable: Boolean(info.event.extendedProps.editable),
            creadoPorNombre: info.event.extendedProps.creado_por_nombre,
            creadoEn: info.event.extendedProps.creado_en,
            start: info.event.start,
            end: info.event.end
        };
        detalleVisible.value = true;
    },
    eventDidMount(info) {
        const estadoAsistencia = info.event.extendedProps.estado_asistencia || (info.event.extendedProps.ausencia ? info.event.extendedProps.ausencia : 'programado');
        if (estadoAsistencia === 'sin_aviso') {
            info.el.style.setProperty('background-color', '#C0392B', 'important');
            info.el.style.setProperty('border-color', '#C0392B', 'important');
            info.el.style.setProperty('color', '#ffffff', 'important');
            return;
        } else if (estadoAsistencia === 'con_aviso') {
            info.el.style.setProperty('background-color', '#E67E22', 'important');
            info.el.style.setProperty('border-color', '#E67E22', 'important');
            info.el.style.setProperty('color', '#ffffff', 'important');
            return;
        } else if (estadoAsistencia === 'presente') {
            info.el.style.setProperty('background-color', '#059669', 'important');
            info.el.style.setProperty('border-color', '#047857', 'important');
            info.el.style.setProperty('color', '#ffffff', 'important');
            return;
        }

        // calendar-medical.css fuerza el color de .evento-rehab con !important;
        // se pisa con !important inline para respetar el color propio de cada grupo.
        const color = info.event.extendedProps.color;
        if (!color) return;
        info.el.style.setProperty('background-color', hexToRgba(color, 0.12), 'important');
        info.el.style.setProperty('border-color', color, 'important');
        info.el.style.setProperty('color', color, 'important');
    }
});

const REHAB_COLOR_DEFAULT = '#059669';

function hexToRgba(hex, alpha) {
    const clean = (hex || '').replace('#', '');
    if (!/^[0-9a-f]{6}$/i.test(clean)) return null;
    const r = parseInt(clean.slice(0, 2), 16);
    const g = parseInt(clean.slice(2, 4), 16);
    const b = parseInt(clean.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function mapEvento(t) {
    const color = t.color || REHAB_COLOR_DEFAULT;
    const estadoAsistencia = t.estado_asistencia || (t.ausencia ? t.ausencia : 'programado');
    let title = `${t.grupo_nombre}: ${t.paciente}`;
    if (estadoAsistencia === 'sin_aviso') {
        title = `[Falta Sin Aviso] ${title}`;
    } else if (estadoAsistencia === 'con_aviso') {
        title = `[Falta Con Aviso] ${title}`;
    } else if (estadoAsistencia === 'presente') {
        title = `[Presente] ${title}`;
    }
    return {
        id: `rehab-${t.id}`,
        title,
        start: t.start,
        end: t.end,
        backgroundColor: estadoAsistencia === 'presente' ? '#059669' : hexToRgba(color, 0.12) || hexToRgba(REHAB_COLOR_DEFAULT, 0.12),
        borderColor: estadoAsistencia === 'presente' ? '#047857' : color,
        textColor: estadoAsistencia === 'presente' ? '#ffffff' : color,
        classNames: ['evento-rehab'],
        extendedProps: {
            turnoId: t.id,
            grupo_id: t.grupo_id,
            grupo_nombre: t.grupo_nombre,
            color,
            paciente: t.paciente,
            dni: t.dni,
            description: t.description,
            observaciones: t.observaciones,
            ausencia: t.ausencia,
            estado_asistencia: estadoAsistencia,
            paciente_id: t.paciente_id,
            creado_por_nombre: t.creado_por_nombre,
            creado_en: t.creado_en,
            editable: Boolean(t.editable)
        }
    };
}

async function cargarContexto() {
    const [resMe, resGrupos] = await Promise.all([api.get('/usuarios/me', { withCredentials: true }), api.get('/grupos', { withCredentials: true })]);
    rolUsuario.value = (resMe.data?.rol || '').toLowerCase().trim();
    gruposRehab.value = (resGrupos.data || []).filter((g) => Boolean(g.es_rehabilitacion));
}

async function cargarTurnos() {
    const params = { solo_rehabilitacion: 1 };
    if (filtroGrupoId.value) params.grupo_id = filtroGrupoId.value;
    const resp = await api.get('/turnos/grupales', { params, withCredentials: true });
    eventos.value = (resp.data || []).map(mapEvento);
    calendarOptions.events = eventos.value;
}

async function buscarPacientes() {
    if (!nuevo.pacienteBusqueda || nuevo.pacienteBusqueda.length < 2) {
        pacientes.value = [];
        return;
    }
    const resp = await api.get(`/pacientes/buscar?q=${encodeURIComponent(nuevo.pacienteBusqueda)}`, { withCredentials: true });
    pacientes.value = resp.data?.pacientes || [];
}

function seleccionarPaciente(p) {
    nuevo.paciente = p;
    nuevo.pacienteBusqueda = `${p.apellido} ${p.nombre} (DNI: ${p.dni})`;
    pacientes.value = [];
    fetchAusenciasConteo(p.id);
}

function toggleDiaTanda(day) {
    const pos = nuevo.dias_tanda.indexOf(day);
    if (pos >= 0) {
        nuevo.dias_tanda.splice(pos, 1);
    } else {
        nuevo.dias_tanda.push(day);
        nuevo.dias_tanda.sort((a, b) => a - b);
    }
}

async function crearTurno() {
    const esTanda = nuevo.modo_creacion === 'tanda';
    const fechaInicioRef = esTanda ? `${nuevo.fecha_base}T${nuevo.hora_tanda}:00` : nuevo.fecha_inicio;
    if (!nuevo.grupo_id || !fechaInicioRef || !nuevo.paciente) return;
    const fechaFin = sumarMinutosISO(fechaInicioRef, nuevo.duracion_minutos);
    if (!fechaFin || !fechaInicioRef) {
        toast.add({ severity: 'error', summary: 'Fecha invalida', detail: 'No se pudo calcular la fecha de fin del turno.', life: 4500 });
        return;
    }
    if (esTanda && (!nuevo.fecha_base || !nuevo.hora_tanda || !nuevo.dias_tanda.length || Number(nuevo.cantidad_tanda) <= 0)) {
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
                grupo_id: Number(nuevo.grupo_id),
                paciente_id: nuevo.paciente.id,
                fecha_inicio: fechaInicioRef,
                fecha_fin: fechaFin,
                motivo: nuevo.motivo,
                observaciones: nuevo.observaciones,
                modo: esTanda ? 'tanda' : 'simple',
                dias_semana: esTanda ? nuevo.dias_tanda : undefined,
                cantidad: esTanda ? Number(nuevo.cantidad_tanda) : undefined,
                hora: esTanda ? nuevo.hora_tanda : undefined,
                frecuencia_semanas: esTanda ? Number(nuevo.frecuencia_semanas) : undefined
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
        await cargarTurnos();
    } finally {
        guardandoNuevo.value = false;
    }
}

function abrirEditar() {
    if (!seleccionado.value) return;
    edit.fecha_inicio = toLocalDateTimeString(new Date(seleccionado.value.start));
    edit.motivo = seleccionado.value.description || '';
    edit.observaciones = seleccionado.value.observaciones || '';
    edit.duracion_minutos = minutosEntreFechas(seleccionado.value.start, seleccionado.value.end);
    modalEditarVisible.value = true;
}

async function guardarEdicion() {
    if (!seleccionado.value) return;
    const fechaFin = sumarMinutosISO(edit.fecha_inicio, edit.duracion_minutos);
    if (!fechaFin) {
        toast.add({ severity: 'error', summary: 'Fecha invalida', detail: 'No se pudo calcular la fecha de fin del turno.', life: 4500 });
        return;
    }
    guardandoEdit.value = true;
    try {
        const resp = await api.put(`/turnos/grupales/${seleccionado.value.id}`, { fecha_inicio: edit.fecha_inicio, fecha_fin: fechaFin, motivo: edit.motivo, observaciones: edit.observaciones }, { withCredentials: true });
        if (resp.data?.ajuste_horario?.aplicado) {
            toast.add({ severity: 'info', summary: 'Horario ajustado', detail: `Inicio ajustado a ${resp.data.ajuste_horario.inicio_ajustado}`, life: 4500 });
        }
        modalEditarVisible.value = false;
        detalleVisible.value = false;
        await cargarTurnos();
    } finally {
        guardandoEdit.value = false;
    }
}

async function eliminarTurno() {
    if (!seleccionado.value) return;
    eliminando.value = true;
    try {
        await api.delete(`/turnos/grupales/${seleccionado.value.id}`, { withCredentials: true });
        detalleVisible.value = false;
        await cargarTurnos();
    } finally {
        eliminando.value = false;
    }
}

onMounted(async () => {
    await cargarContexto();
    await cargarTurnos();
});
</script>

<template>
    <div class="p-6 h-screen flex flex-col">
        <Toast />
        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow-sm">
                    <i class="pi pi-heart text-white text-lg"></i>
                </div>
                <div>
                    <h1 class="text-2xl font-heading font-bold text-[#134E4A] dark:text-teal-100 tracking-tight">Rehabilitacion</h1>
                    <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5 font-sans">Turnos grupales de los equipos de rehabilitacion</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <select
                    v-model="filtroGrupoId"
                    class="px-3 py-2 rounded-lg border border-[#E0F2FE] dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-[#134E4A] dark:text-slate-200 min-w-56 font-sans focus:outline-none focus:ring-2 focus:ring-[#0891B2]/30 focus:border-[#0891B2] transition-colors cursor-pointer"
                    @change="cargarTurnos"
                >
                    <option value="">Todos los grupos</option>
                    <option v-for="g in gruposRehab" :key="g.id" :value="g.id">{{ g.nombre }}</option>
                </select>
                <Button v-if="canEdit()" label="Nuevo turno" icon="pi pi-plus" class="!rounded-lg !bg-emerald-600 !border-emerald-600 hover:!bg-emerald-700 !text-sm !font-sans" @click="modalNuevoVisible = true" />
            </div>
        </div>

        <!-- Calendar container -->
        <div class="flex-1 bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-[#E0F2FE] dark:border-slate-700 p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>

        <!-- Modal: Nuevo turno grupal rehab -->
        <Dialog v-model:visible="modalNuevoVisible" modal header="Nuevo turno de rehabilitacion" :style="{ width: '540px' }" :pt="{ header: { class: 'font-heading' } }">
            <div class="space-y-4">
                <!-- Modo selector -->
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Modo de carga</label>
                    <div class="flex gap-2">
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer"
                            :class="nuevo.modo_creacion === 'simple' ? 'bg-emerald-600 text-white shadow-md' : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-[#E0F2FE] dark:border-slate-600 hover:border-emerald-500'"
                            @click="nuevo.modo_creacion = 'simple'"
                        >
                            <i class="pi pi-calendar mr-1.5"></i> Simple
                        </button>
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer"
                            :class="nuevo.modo_creacion === 'tanda' ? 'bg-emerald-600 text-white shadow-md' : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-[#E0F2FE] dark:border-slate-600 hover:border-emerald-500'"
                            @click="nuevo.modo_creacion = 'tanda'"
                        >
                            <i class="pi pi-replay mr-1.5"></i> Tanda
                        </button>
                    </div>
                </div>
                <!-- Grupo selector -->
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-users mr-1.5 text-emerald-600"></i>Grupo</label>
                    <select
                        v-model="nuevo.grupo_id"
                        class="w-full px-3 py-2 rounded-lg border border-[#E0F2FE] dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-[#134E4A] dark:text-slate-200 font-sans focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 cursor-pointer"
                    >
                        <option value="" disabled>Seleccionar grupo</option>
                        <option v-for="g in gruposRehab" :key="g.id" :value="g.id">{{ g.nombre }}</option>
                    </select>
                </div>
                <!-- Simple mode -->
                <div v-if="nuevo.modo_creacion === 'simple'">
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-calendar mr-1.5 text-emerald-600"></i>Fecha/hora</label>
                    <InputText type="datetime-local" v-model="nuevo.fecha_inicio" class="w-full" />
                </div>
                <!-- Tanda mode -->
                <div v-else class="space-y-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-[#E0F2FE] dark:border-slate-700">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Fecha base</label>
                            <InputText type="date" v-model="nuevo.fecha_base" class="w-full" />
                        </div>
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Hora</label>
                            <InputText type="time" v-model="nuevo.hora_tanda" class="w-full" />
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
                                    nuevo.dias_tanda.includes(d.value) ? 'bg-emerald-600 text-white shadow-md' : 'bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-300 border border-[#E0F2FE] dark:border-slate-600 hover:border-emerald-500'
                                "
                                @click="toggleDiaTanda(d.value)"
                            >
                                {{ d.label }}
                            </button>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Frecuencia</label>
                            <Dropdown v-model="nuevo.frecuencia_semanas" :options="opcionesFrecuencia" optionLabel="label" optionValue="value" class="w-full" />
                        </div>
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Cantidad total de turnos</label>
                            <InputText type="number" min="1" step="1" v-model.number="nuevo.cantidad_tanda" class="w-full" />
                        </div>
                    </div>
                </div>
                <!-- Paciente -->
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-user mr-1.5 text-emerald-600"></i>Paciente</label>
                    <InputText v-model="nuevo.pacienteBusqueda" @input="buscarPacientes" class="w-full" placeholder="Buscar por DNI o nombre..." />
                    <ul v-if="pacientes.length" class="border border-[#E0F2FE] dark:border-slate-600 rounded-lg mt-1.5 max-h-40 overflow-y-auto bg-white dark:bg-slate-800 shadow-lg">
                        <li
                            v-for="p in pacientes"
                            :key="p.id"
                            class="px-3 py-2.5 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 cursor-pointer transition-colors text-sm border-b border-[#E0F2FE] dark:border-slate-700 last:border-0"
                            @click="seleccionarPaciente(p)"
                        >
                            <span class="font-medium text-[#134E4A] dark:text-slate-200">{{ p.apellido }} {{ p.nombre }}</span> <span class="text-slate-400 ml-1">DNI: {{ p.dni }}</span>
                        </li>
                    </ul>
                    <div v-if="nuevo.paciente" class="flex items-center gap-2 mt-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-xs font-medium">
                        <i class="pi pi-check-circle"></i> {{ nuevo.paciente.apellido }} {{ nuevo.paciente.nombre }}
                    </div>
                    <div v-if="nuevo.paciente && ausenciasConteoNuevoTurno" class="flex flex-col gap-1.5 mt-2">
                        <div
                            v-if="ausenciasConteoNuevoTurno.sin_aviso >= 3"
                            class="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-xs font-semibold border border-red-200 dark:border-red-900"
                        >
                            <i class="pi pi-exclamation-triangle text-sm"></i>
                            <span>¡Alerta! El paciente tiene {{ ausenciasConteoNuevoTurno.sin_aviso }} ausencias sin aviso.</span>
                        </div>
                        <div class="text-[11px] text-slate-500 px-1">
                            Historial de ausencias: <strong class="text-slate-700 dark:text-slate-300">{{ ausenciasConteoNuevoTurno.total }}</strong> total (<span class="text-orange-600 font-semibold"
                                >{{ ausenciasConteoNuevoTurno.con_aviso }} con aviso</span
                            >, <span class="text-red-600 font-semibold">{{ ausenciasConteoNuevoTurno.sin_aviso }} sin aviso</span>)
                        </div>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-comment mr-1.5 text-emerald-600"></i>Motivo</label>
                        <InputText v-model="nuevo.motivo" class="w-full" />
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-clock mr-1.5 text-emerald-600"></i>Duracion (min)</label>
                        <InputText type="number" min="5" step="5" v-model.number="nuevo.duracion_minutos" class="w-full" />
                    </div>
                </div>
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-align-left mr-1.5 text-emerald-600"></i>Observaciones</label>
                    <Textarea v-model="nuevo.observaciones" rows="3" autoResize class="w-full" placeholder="Observaciones adicionales" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" class="!rounded-lg" @click="modalNuevoVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoNuevo" class="!rounded-lg !bg-emerald-600 !border-emerald-600" @click="crearTurno" />
            </template>
        </Dialog>

        <!-- Modal: Detalle turno rehab -->
        <Dialog v-model:visible="detalleVisible" modal header="Detalle de turno" :style="{ width: '480px' }" :pt="{ header: { class: 'font-heading' } }">
            <div v-if="seleccionado" class="space-y-4">
                <div class="flex items-center gap-3 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/15">
                    <div class="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center text-white text-sm font-heading font-bold shrink-0">
                        {{ (seleccionado.paciente || '?')[0].toUpperCase() }}
                    </div>
                    <div>
                        <p class="font-semibold text-[#134E4A] dark:text-slate-200">{{ seleccionado.paciente }}</p>
                        <p class="text-xs text-slate-400">DNI: {{ seleccionado.dni }}</p>
                    </div>
                </div>
                <div class="space-y-2 text-sm">
                    <p class="flex items-center gap-2">
                        <i class="pi pi-users text-emerald-600"></i> <span class="text-slate-600 dark:text-slate-300">{{ seleccionado.grupo_nombre }}</span>
                    </p>
                    <p class="flex items-center gap-2">
                        <i class="pi pi-comment text-emerald-600"></i> <span class="text-slate-600 dark:text-slate-300">{{ seleccionado.description || 'Sin motivo' }}</span>
                    </p>
                    <div v-if="seleccionado.observaciones" class="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 text-xs border border-slate-100 dark:border-slate-700">
                        <span class="font-semibold text-slate-500 block mb-1"><i class="pi pi-align-left mr-1 text-emerald-600"></i>Observaciones:</span>
                        <p class="text-slate-600 dark:text-slate-300 whitespace-pre-wrap">{{ seleccionado.observaciones }}</p>
                    </div>
                    <div class="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700 space-y-2">
                        <span class="font-semibold text-slate-500 text-xs block"><i class="pi pi-check-square mr-1 text-[#059669]"></i>Asistencia del Paciente:</span>
                        <div class="flex flex-wrap gap-2 pt-1">
                            <Button
                                label="Programado"
                                icon="pi pi-calendar"
                                :severity="seleccionado.estado_asistencia === 'programado' ? 'info' : 'secondary'"
                                :outlined="seleccionado.estado_asistencia !== 'programado'"
                                size="small"
                                class="!text-xs !py-1 !px-2.5 !rounded-lg"
                                :loading="guardandoAusencia"
                                @click="guardarAsistenciaTurno('programado')"
                            />
                            <Button
                                label="Presente"
                                icon="pi pi-check"
                                :severity="seleccionado.estado_asistencia === 'presente' ? 'success' : 'secondary'"
                                :outlined="seleccionado.estado_asistencia !== 'presente'"
                                size="small"
                                class="!text-xs !py-1 !px-2.5 !rounded-lg"
                                :loading="guardandoAusencia"
                                @click="guardarAsistenciaTurno('presente')"
                            />
                            <Button
                                label="Faltó con aviso"
                                icon="pi pi-envelope"
                                :severity="seleccionado.estado_asistencia === 'con_aviso' ? 'warning' : 'secondary'"
                                :outlined="seleccionado.estado_asistencia !== 'con_aviso'"
                                size="small"
                                class="!text-xs !py-1 !px-2.5 !rounded-lg"
                                :loading="guardandoAusencia"
                                @click="guardarAsistenciaTurno('con_aviso')"
                            />
                            <Button
                                label="Faltó sin aviso"
                                icon="pi pi-times"
                                :severity="seleccionado.estado_asistencia === 'sin_aviso' ? 'danger' : 'secondary'"
                                :outlined="seleccionado.estado_asistencia !== 'sin_aviso'"
                                size="small"
                                class="!text-xs !py-1 !px-2.5 !rounded-lg"
                                :loading="guardandoAusencia"
                                @click="guardarAsistenciaTurno('sin_aviso')"
                            />
                        </div>
                        <div v-if="ausenciasConteoDetalle" class="text-[11px] text-slate-400 pt-1">
                            Historial: {{ ausenciasConteoDetalle.total }} ausencias ({{ ausenciasConteoDetalle.con_aviso }} con aviso, {{ ausenciasConteoDetalle.sin_aviso }} sin aviso)
                        </div>
                    </div>
                    <div class="pt-3 border-t border-slate-100 dark:border-slate-700 text-xs text-slate-400 dark:text-slate-500">
                        <i class="pi pi-user-edit mr-1"></i>
                        <template v-if="seleccionado.creadoPorNombre">
                            Cargado por <span class="font-medium text-slate-500 dark:text-slate-400">{{ seleccionado.creadoPorNombre }}</span>
                            <template v-if="seleccionado.creadoEn"> el {{ fechaBonitaCompleta(seleccionado.creadoEn) }}</template>
                        </template>
                        <template v-else>Sin registro de carga</template>
                    </div>
                </div>
                <div class="flex justify-between pt-4 border-t border-[#E0F2FE] dark:border-slate-700">
                    <div class="flex gap-2">
                        <Button v-if="seleccionado.editable" label="Editar" icon="pi pi-pencil" text severity="warning" class="!rounded-lg" @click="abrirEditar" />
                        <Button v-if="seleccionado.editable" label="Eliminar" icon="pi pi-trash" text severity="danger" :loading="eliminando" class="!rounded-lg" @click="eliminarTurno" />
                    </div>
                    <Button label="Cerrar" text severity="secondary" class="!rounded-lg" @click="detalleVisible = false" />
                </div>
            </div>
        </Dialog>

        <!-- Modal: Editar turno rehab -->
        <Dialog v-model:visible="modalEditarVisible" modal header="Editar turno" :style="{ width: '480px' }" :pt="{ header: { class: 'font-heading' } }">
            <div class="space-y-4">
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-calendar mr-1.5 text-emerald-600"></i>Fecha/hora</label>
                    <InputText type="datetime-local" v-model="edit.fecha_inicio" class="w-full" />
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-comment mr-1.5 text-emerald-600"></i>Motivo</label>
                        <InputText v-model="edit.motivo" class="w-full" />
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-clock mr-1.5 text-emerald-600"></i>Duracion (min)</label>
                        <InputText type="number" min="5" step="5" v-model.number="edit.duracion_minutos" class="w-full" />
                    </div>
                </div>
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-align-left mr-1.5 text-emerald-600"></i>Observaciones</label>
                    <Textarea v-model="edit.observaciones" rows="3" autoResize class="w-full" placeholder="Observaciones adicionales" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" class="!rounded-lg" @click="modalEditarVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoEdit" class="!rounded-lg !bg-emerald-600 !border-emerald-600" @click="guardarEdicion" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
/* Calendar Medical Clean theme is loaded from @/assets/calendar-medical.css */
</style>
