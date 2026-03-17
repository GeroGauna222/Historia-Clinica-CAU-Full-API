<script setup>
import { ref, onMounted, onUnmounted, reactive, computed, watch } from 'vue';
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
import Select from 'primevue/select';
import Checkbox from 'primevue/checkbox';
import Tag from 'primevue/tag';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const esLocale = {
    code: 'es',
    week: { dow: 1, doy: 4 },
    buttonText: { prev: 'Ant', next: 'Sig', today: 'Hoy', month: 'Mes', week: 'Semana', day: 'Dia', list: 'Agenda' },
    weekText: 'Sm',
    allDayText: 'Todo el dia',
    moreLinkText: 'mas',
    noEventsText: 'No hay eventos para mostrar'
};

const DIAS_INDEX = { Lunes: 1, Martes: 2, Miercoles: 3, Jueves: 4, Viernes: 5, Sabado: 6, Domingo: 0 };

const eventos = ref([]);
const turnoSeleccionado = ref(null);
const modalVisible = ref(false);
const editando = ref(false);
const fechaEdit = ref('');
const horaEdit = ref('');
const duracionTurno = ref(20);

const rolUsuario = ref('');
const usuarioLogueadoId = ref(null);
const nombreUsuarioLogueado = ref('');

const sujetos = ref([]);
const sujetoSeleccionadoId = ref(null);

const bloqueoModalVisible = ref(false);
const bloqueoGuardando = ref(false);
const bloqueoForm = reactive({
    fecha: '',
    todoDia: false,
    horaInicio: '08:00',
    horaFin: '09:00',
    motivo: '',
    usuario_id: ''
});

const nuevoTurnoModalVisible = ref(false);
const pacienteBusqueda = ref('');
const pacientes = ref([]);
const pacienteSeleccionado = ref(null);
const nuevoTurnoMotivo = ref('');
const nuevoTurnoFecha = ref('');
const nuevoTurnoGuardando = ref(false);

const canSelectSubject = computed(() => ['director', 'administrativo'].includes((rolUsuario.value || '').toLowerCase().trim()));
const canDeleteAusencia = computed(() => {
    if (!turnoSeleccionado.value || turnoSeleccionado.value.tipo !== 'ausencia') return false;
    if (['director', 'administrativo'].includes((rolUsuario.value || '').toLowerCase().trim())) return true;
    return Number(turnoSeleccionado.value.usuarioId) === Number(usuarioLogueadoId.value);
});
const sujetoActualNombre = computed(() => sujetos.value.find((s) => Number(s.id) === Number(sujetoSeleccionadoId.value))?.nombre || nombreUsuarioLogueado.value || 'Cargando...');

function pad(n) {
    return String(n).padStart(2, '0');
}

function toDateInput(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function toTimeInput(date) {
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toLocalDateTimeString(date, withSeconds = true) {
    const base = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    return withSeconds ? `${base}:${pad(date.getSeconds())}` : base;
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

function normalizarHHMM(v, fallback = '00:00') {
    if (!v || typeof v !== 'string') return fallback;
    const clean = v.trim().slice(0, 5);
    return /^\d{2}:\d{2}$/.test(clean) ? clean : fallback;
}
function minutosDesdeHHMM(hhmm) {
    const val = normalizarHHMM(hhmm, '00:00');
    const [h, m] = val.split(':').map(Number);
    return h * 60 + m;
}
function minutosATiempo(minutos, forEnd = false) {
    if (forEnd && minutos >= 24 * 60) return '23:59:59';
    const total = Math.max(0, Math.min(minutos, 24 * 60 - 1));
    const h = Math.floor(total / 60);
    const m = total % 60;
    return `${pad(h)}:${pad(m)}:00`;
}

function crearEventosNoDisponibilidad(disponibilidades) {
    const disponiblesPorDia = {};
    const eventos = [];
    const inicioDia = 0;
    const finDia = 24 * 60;

    for (const d of disponibilidades || []) {
        if (!d.activo) continue;
        const idx = DIAS_INDEX[d.dia_semana];
        if (idx === undefined) continue;
        const inicio = minutosDesdeHHMM(d.hora_inicio);
        const fin = minutosDesdeHHMM(d.hora_fin);
        if (fin <= inicio) continue;
        if (!disponiblesPorDia[idx]) disponiblesPorDia[idx] = [];
        disponiblesPorDia[idx].push({ inicio, fin });
    }

    for (const idx of [0, 1, 2, 3, 4, 5, 6]) {
        const rangos = (disponiblesPorDia[idx] || []).slice().sort((a, b) => a.inicio - b.inicio);

        if (!rangos.length) {
            eventos.push({
                daysOfWeek: [idx],
                startTime: '00:00:00',
                endTime: '23:59:59',
                display: 'background',
                classNames: ['no-disponible-background'],
                backgroundColor: 'rgba(107, 114, 128, 0.22)',
                extendedProps: { tipo: 'indisponible_bg' }
            });
            continue;
        }

        const merged = [];
        for (const r of rangos) {
            if (!merged.length || r.inicio > merged[merged.length - 1].fin) {
                merged.push({ ...r });
            } else {
                merged[merged.length - 1].fin = Math.max(merged[merged.length - 1].fin, r.fin);
            }
        }

        let cursor = inicioDia;
        for (const r of merged) {
            if (r.inicio > cursor) {
                eventos.push({
                    daysOfWeek: [idx],
                    startTime: minutosATiempo(cursor),
                    endTime: minutosATiempo(r.inicio, true),
                    display: 'background',
                    classNames: ['no-disponible-background'],
                    backgroundColor: 'rgba(107, 114, 128, 0.22)',
                    extendedProps: { tipo: 'indisponible_bg' }
                });
            }
            cursor = Math.max(cursor, r.fin);
        }

        if (cursor < finDia) {
            eventos.push({
                daysOfWeek: [idx],
                startTime: minutosATiempo(cursor),
                endTime: minutosATiempo(finDia, true),
                display: 'background',
                classNames: ['no-disponible-background'],
                backgroundColor: 'rgba(107, 114, 128, 0.22)',
                extendedProps: { tipo: 'indisponible_bg' }
            });
        }
    }

    return eventos;
}

const calendarOptions = reactive({
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'timeGridWeek',
    locale: esLocale,
    headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' },
    slotMinTime: '07:00:00',
    slotMaxTime: '22:00:00',
    slotDuration: '00:20:00',
    snapDuration: '00:20:00',
    slotLabelInterval: '00:20:00',
    allDaySlot: false,
    height: '100%',
    slotEventOverlap: true,
    eventOverlap: true,
    events: eventos,
    dateClick(info) {
        abrirModalNuevoTurno(info.date);
    },
    eventClick(info) {
        const e = info.event;
        const tipo = e.extendedProps.tipo;
        if (tipo === 'ausencia_bg' || tipo === 'indisponible_bg') return;

        turnoSeleccionado.value = {
            id: e.id,
            turnoId: e.extendedProps.turnoId || e.id,
            tipo,
            editable: Boolean(e.extendedProps.editable),
            paciente: e.extendedProps.paciente,
            dni: e.extendedProps.dni,
            profesional: e.extendedProps.profesional,
            description: e.extendedProps.description,
            ausenciaId: e.extendedProps.ausenciaId,
            usuarioId: e.extendedProps.usuarioId,
            grupoId: e.extendedProps.grupoId,
            start: e.start,
            end: e.end
        };
        editando.value = false;
        modalVisible.value = true;
    },
    eventDidMount(info) {
        const tipo = info.event.extendedProps.tipo;
        if (tipo === 'ausencia_bg' || tipo === 'indisponible_bg') return;

        if (tipo === 'ausencia') {
            tippy(info.el, {
                content: `<strong>No disponible:</strong> ${info.event.extendedProps.profesional || 'Profesional'}<br>${info.event.extendedProps.description || ''}`,
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

watch(duracionTurno, (d) => {
    const dur = Number(d) > 0 ? Number(d) : 20;
    const hh = `00:${pad(dur)}:00`;
    calendarOptions.slotDuration = hh;
    calendarOptions.snapDuration = hh;
    calendarOptions.slotLabelInterval = hh;
});

async function cargarDatosUsuario() {
    const resp = await api.get('/usuarios/me', { withCredentials: true });
    const data = resp.data || {};
    nombreUsuarioLogueado.value = data.nombre || data.email || '';
    rolUsuario.value = (data.rol || '').toLowerCase().trim();
    usuarioLogueadoId.value = data.id;
    duracionTurno.value = data.duracion_turno || 20;
    bloqueoForm.usuario_id = data.id;
}

async function cargarSujetos() {
    if (canSelectSubject.value) {
        const resp = await api.get('/agenda/sujetos', { withCredentials: true });
        sujetos.value = resp.data || [];
        if (!sujetoSeleccionadoId.value && sujetos.value.length) {
            sujetoSeleccionadoId.value = sujetos.value[0].id;
        }
    } else {
        sujetos.value = [{ id: usuarioLogueadoId.value, nombre: nombreUsuarioLogueado.value, rol: rolUsuario.value, duracion_turno: duracionTurno.value }];
        sujetoSeleccionadoId.value = usuarioLogueadoId.value;
    }
}

function crearEventosAusencia(ausencia) {
    const inicio = parseDateSafe(ausencia.fecha_inicio);
    const fin = parseDateSafe(ausencia.fecha_fin);
    if (!inicio || !fin) return [];

    const rows = [
        {
            id: `ausencia-${ausencia.id}`,
            title: `No disponible: ${ausencia.nombre_usuario || 'Profesional'}`,
            start: ausencia.fecha_inicio,
            end: ausencia.fecha_fin,
            backgroundColor: '#f87171',
            borderColor: '#dc2626',
            textColor: '#ffffff',
            classNames: ['evento-ausencia'],
            extendedProps: { tipo: 'ausencia', ausenciaId: ausencia.id, usuarioId: ausencia.usuario_id, profesional: ausencia.nombre_usuario, description: ausencia.motivo || '' }
        }
    ];

    if (esDiaCompletoAusencia(ausencia, inicio, fin)) {
        const inicioDia = new Date(inicio);
        inicioDia.setHours(0, 0, 0, 0);
        const finDia = new Date(inicioDia);
        finDia.setDate(finDia.getDate() + 1);
        rows.push({
            id: `ausencia-bg-${ausencia.id}`,
            display: 'background',
            start: toLocalDateTimeString(inicioDia),
            end: toLocalDateTimeString(finDia),
            classNames: ['ausencia-background'],
            backgroundColor: 'rgba(248, 113, 113, 0.15)',
            extendedProps: { tipo: 'ausencia_bg' }
        });
    }
    return rows;
}

function adaptarEventoTurno(t) {
    const tipo = t.tipo || 'individual';
    const esGrupal = tipo === 'grupal';
    return {
        id: t.id,
        title: esGrupal ? `${t.grupo_nombre || t.profesional} (${t.paciente})` : t.paciente,
        start: t.start,
        end: t.end,
        backgroundColor: esGrupal ? 'rgba(59,130,246,0.15)' : '#1976D2',
        borderColor: esGrupal ? '#2563eb' : '#1976D2',
        textColor: esGrupal ? '#111827' : '#ffffff',
        classNames: esGrupal ? ['evento-grupal'] : ['evento-propio'],
        extendedProps: {
            tipo,
            turnoId: t.turnoId || t.id,
            paciente: t.paciente,
            dni: t.dni,
            profesional: t.profesional,
            description: t.description,
            editable: Boolean(t.editable) && !esGrupal,
            grupoId: t.grupo_id
        }
    };
}

async function cargarAgenda() {
    if (!sujetoSeleccionadoId.value) return;
    const params = { usuario_id: sujetoSeleccionadoId.value };
    const [resTurnos, resAusencias, resDisponibilidades] = await Promise.all([
        api.get('/turnos/profesional/completo', { params, withCredentials: true }),
        api.get('/ausencias', { params, withCredentials: true }),
        api.get('/disponibilidades', { params, withCredentials: true })
    ]);

    const turnos = (resTurnos.data || []).map(adaptarEventoTurno);
    const ausencias = (resAusencias.data || []).flatMap(crearEventosAusencia);
    const disponibilidadBg = crearEventosNoDisponibilidad(resDisponibilidades.data || []);
    eventos.value = [...disponibilidadBg, ...turnos, ...ausencias];
    calendarOptions.events = eventos.value;

    const sujeto = sujetos.value.find((s) => Number(s.id) === Number(sujetoSeleccionadoId.value));
    if (sujeto?.duracion_turno) duracionTurno.value = sujeto.duracion_turno;
}

function abrirModalBloqueo(fechaBase = new Date()) {
    const inicio = new Date(fechaBase);
    const fin = new Date(fechaBase);
    fin.setMinutes(fin.getMinutes() + (duracionTurno.value || 20));
    bloqueoForm.fecha = toDateInput(inicio);
    bloqueoForm.horaInicio = toTimeInput(inicio);
    bloqueoForm.horaFin = toTimeInput(fin);
    bloqueoForm.todoDia = false;
    bloqueoForm.motivo = '';
    bloqueoForm.usuario_id = sujetoSeleccionadoId.value;
    bloqueoModalVisible.value = true;
}

async function guardarBloqueo() {
    if (!bloqueoForm.fecha) return;
    if (!bloqueoForm.todoDia) {
        const inicioMin = minutosDesdeHHMM(bloqueoForm.horaInicio);
        const finMin = minutosDesdeHHMM(bloqueoForm.horaFin);
        if (finMin <= inicioMin) {
            toast.add({ severity: 'warn', summary: 'Rango invalido', detail: 'La hora de fin debe ser mayor a la hora de inicio.', life: 4000 });
            return;
        }
    }
    const fechaInicio = bloqueoForm.todoDia ? `${bloqueoForm.fecha}T00:00:00` : `${bloqueoForm.fecha}T${bloqueoForm.horaInicio}:00`;
    const fechaFin = bloqueoForm.todoDia ? `${bloqueoForm.fecha}T23:59:59` : `${bloqueoForm.fecha}T${bloqueoForm.horaFin}:00`;
    bloqueoGuardando.value = true;
    try {
        await api.post('/ausencias', { fecha_inicio: fechaInicio, fecha_fin: fechaFin, motivo: bloqueoForm.motivo, usuario_id: Number(bloqueoForm.usuario_id) }, { withCredentials: true });
        bloqueoModalVisible.value = false;
        await cargarAgenda();
    } finally {
        bloqueoGuardando.value = false;
    }
}

function abrirModalNuevoTurno(date) {
    nuevoTurnoFecha.value = toLocalDateTimeString(date);
    pacienteBusqueda.value = '';
    pacientes.value = [];
    pacienteSeleccionado.value = null;
    nuevoTurnoMotivo.value = '';
    nuevoTurnoModalVisible.value = true;
}

async function buscarPacientes() {
    if (!pacienteBusqueda.value || pacienteBusqueda.value.length < 2) {
        pacientes.value = [];
        return;
    }
    const resp = await api.get(`/pacientes/buscar?q=${encodeURIComponent(pacienteBusqueda.value)}`, { withCredentials: true });
    pacientes.value = resp.data?.pacientes || [];
}

function seleccionarPaciente(p) {
    pacienteSeleccionado.value = p;
    pacienteBusqueda.value = `${p.apellido} ${p.nombre} (DNI: ${p.dni})`;
    pacientes.value = [];
}

async function guardarNuevoTurno() {
    if (!pacienteSeleccionado.value || !sujetoSeleccionadoId.value || !nuevoTurnoFecha.value) return;
    nuevoTurnoGuardando.value = true;
    try {
        const resp = await api.post('/turnos', { paciente_id: pacienteSeleccionado.value.id, usuario_id: Number(sujetoSeleccionadoId.value), fecha_inicio: nuevoTurnoFecha.value, motivo: nuevoTurnoMotivo.value }, { withCredentials: true });
        if (resp.data?.ajuste_horario?.aplicado) {
            toast.add({ severity: 'info', summary: 'Horario ajustado', detail: `Inicio ajustado a ${resp.data.ajuste_horario.inicio_ajustado}`, life: 4500 });
        }
        nuevoTurnoModalVisible.value = false;
        await cargarAgenda();
    } finally {
        nuevoTurnoGuardando.value = false;
    }
}

async function eliminarAusencia() {
    if (!turnoSeleccionado.value?.ausenciaId) return;
    await api.delete(`/ausencias/${turnoSeleccionado.value.ausenciaId}`, { withCredentials: true });
    modalVisible.value = false;
    await cargarAgenda();
}

function iniciarEdicion() {
    const f = new Date(turnoSeleccionado.value.start);
    fechaEdit.value = toDateInput(f);
    horaEdit.value = toTimeInput(f);
    editando.value = true;
}

async function guardarEdicion() {
    const resp = await api.put(`/turnos/${turnoSeleccionado.value.turnoId}`, { fecha_inicio: `${fechaEdit.value}T${horaEdit.value}:00`, motivo: turnoSeleccionado.value.description }, { withCredentials: true });
    if (resp.data?.ajuste_horario?.aplicado) {
        toast.add({ severity: 'info', summary: 'Horario ajustado', detail: `Inicio ajustado a ${resp.data.ajuste_horario.inicio_ajustado}`, life: 4500 });
    }
    modalVisible.value = false;
    await cargarAgenda();
}

async function eliminarTurno() {
    await api.delete(`/turnos/${turnoSeleccionado.value.turnoId}`, { withCredentials: true });
    modalVisible.value = false;
    await cargarAgenda();
}

let intervalo = null;
watch(sujetoSeleccionadoId, async () => {
    bloqueoForm.usuario_id = sujetoSeleccionadoId.value;
    await cargarAgenda();
});

onMounted(async () => {
    await cargarDatosUsuario();
    await cargarSujetos();
    await cargarAgenda();
    intervalo = setInterval(cargarAgenda, 60000);
});

onUnmounted(() => {
    clearInterval(intervalo);
});
</script>

<template>
    <div class="p-6 h-screen flex flex-col">
        <Toast />

        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div>
                <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">Agenda</h1>
                <p class="text-xs text-gray-500 mt-1">Click en celda para crear turno. Los horarios no disponibles se muestran en gris.</p>
            </div>

            <div class="flex items-center gap-3">
                <Select v-if="canSelectSubject" v-model="sujetoSeleccionadoId" :options="sujetos" optionValue="id" optionLabel="nombre" filter class="min-w-56">
                    <template #option="slotProps">
                        {{ slotProps.option.nombre }} <span class="text-muted-color text-xs">({{ slotProps.option.rol }})</span>
                    </template>
                </Select>
                <span v-else class="text-sm text-gray-600 font-semibold">{{ sujetoActualNombre }}</span>
                <Button label="Bloquear horario" icon="pi pi-lock" severity="secondary" @click="abrirModalBloqueo(new Date())" />
            </div>
        </div>

        <!-- Leyenda -->
        <div class="flex items-center gap-6 mb-3 text-xs text-muted-color">
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-[#1976D2] inline-block"></span> Turno individual</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm border-2 border-dashed border-[#2563eb] bg-blue-100 dark:bg-blue-900/30 inline-block"></span> Turno grupal</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-[#f87171] inline-block"></span> Ausencia / Bloqueo</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-gray-300 dark:bg-gray-600 inline-block"></span> No disponible</span>
        </div>

        <div class="flex-1 bg-surface-0 dark:bg-surface-900 rounded-2xl shadow border border-surface-200 dark:border-surface-700 p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>

        <Dialog v-model:visible="nuevoTurnoModalVisible" modal header="Nuevo turno" :style="{ width: '520px' }">
            <div class="space-y-3">
                <p class="text-sm text-gray-500">Fecha/hora: {{ nuevoTurnoFecha }}</p>
                <div>
                    <label class="font-semibold block mb-1">Paciente</label>
                    <InputText v-model="pacienteBusqueda" @input="buscarPacientes" class="w-full" placeholder="Buscar por DNI o nombre" />
                    <ul v-if="pacientes.length" class="border border-surface-200 dark:border-surface-700 rounded-lg mt-1 max-h-40 overflow-y-auto bg-surface-0 dark:bg-surface-800 shadow-lg">
                        <li v-for="p in pacientes" :key="p.id" class="px-3 py-2 hover:bg-primary/10 cursor-pointer transition-colors text-color text-sm" @click="seleccionarPaciente(p)">
                            <span class="font-medium">{{ p.apellido }} {{ p.nombre }}</span> <span class="text-muted-color">(DNI: {{ p.dni }})</span>
                        </li>
                    </ul>
                    <p v-if="pacienteSeleccionado" class="text-xs text-green-600 mt-1">Paciente seleccionado: {{ pacienteSeleccionado.apellido }} {{ pacienteSeleccionado.nombre }}</p>
                </div>
                <div>
                    <label class="font-semibold block mb-1">Motivo</label>
                    <InputText v-model="nuevoTurnoMotivo" class="w-full" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="nuevoTurnoModalVisible = false" />
                <Button label="Guardar turno" icon="pi pi-check" :loading="nuevoTurnoGuardando" @click="guardarNuevoTurno" />
            </template>
        </Dialog>

        <Dialog v-model:visible="bloqueoModalVisible" modal header="Bloquear agenda" :style="{ width: '480px' }">
            <div class="space-y-3">
                <div><label class="font-semibold block mb-1">Fecha</label><InputText type="date" v-model="bloqueoForm.fecha" class="w-full" /></div>
                <label class="flex items-center gap-2 cursor-pointer"><Checkbox v-model="bloqueoForm.todoDia" :binary="true" /><span>Todo el dia</span></label>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="font-semibold block mb-1">Hora inicio</label><InputText type="time" v-model="bloqueoForm.horaInicio" class="w-full" :disabled="bloqueoForm.todoDia" /></div>
                    <div><label class="font-semibold block mb-1">Hora fin</label><InputText type="time" v-model="bloqueoForm.horaFin" class="w-full" :disabled="bloqueoForm.todoDia" /></div>
                </div>
                <div><label class="font-semibold block mb-1">Motivo</label><InputText v-model="bloqueoForm.motivo" class="w-full" /></div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="bloqueoModalVisible = false" />
                <Button label="Guardar bloqueo" icon="pi pi-lock" :loading="bloqueoGuardando" @click="guardarBloqueo" />
            </template>
        </Dialog>

        <Dialog v-model:visible="modalVisible" modal :header="editando ? 'Editar turno' : 'Detalle'" :style="{ width: '480px' }">
            <div v-if="turnoSeleccionado" class="space-y-3">
                <div v-if="turnoSeleccionado.tipo === 'ausencia'">
                    <p><strong>Profesional:</strong> {{ turnoSeleccionado.profesional }}</p>
                    <p><strong>Motivo:</strong> {{ turnoSeleccionado.description || 'Sin motivo' }}</p>
                    <div class="flex justify-end gap-2 mt-4">
                        <Button label="Cerrar" text severity="secondary" @click="modalVisible = false" />
                        <Button v-if="canDeleteAusencia" label="Desbloquear" severity="danger" @click="eliminarAusencia" />
                    </div>
                </div>
                <div v-else-if="editando">
                    <div class="grid grid-cols-2 gap-3">
                        <div><label class="font-semibold block mb-1">Fecha</label><InputText type="date" v-model="fechaEdit" class="w-full" /></div>
                        <div><label class="font-semibold block mb-1">Hora</label><InputText type="time" v-model="horaEdit" class="w-full" /></div>
                    </div>
                    <div><label class="font-semibold block mb-1">Motivo</label><InputText v-model="turnoSeleccionado.description" class="w-full" /></div>
                    <div class="flex justify-end gap-2 mt-4">
                        <Button label="Cancelar" text severity="secondary" @click="editando = false" />
                        <Button label="Guardar cambios" @click="guardarEdicion" />
                    </div>
                </div>
                <div v-else>
                    <div class="mb-3">
                        <Tag :value="turnoSeleccionado.tipo === 'grupal' ? 'Grupal' : 'Individual'" :severity="turnoSeleccionado.tipo === 'grupal' ? 'info' : 'primary'" rounded />
                    </div>
                    <div class="space-y-2">
                        <p class="flex items-center gap-2"><i class="pi pi-user text-muted-color"></i> <strong>Paciente:</strong> {{ turnoSeleccionado.paciente }}</p>
                        <p class="flex items-center gap-2"><i class="pi pi-id-card text-muted-color"></i> <strong>DNI:</strong> {{ turnoSeleccionado.dni }}</p>
                        <p class="flex items-center gap-2"><i class="pi pi-briefcase text-muted-color"></i> <strong>Profesional:</strong> {{ turnoSeleccionado.profesional }}</p>
                        <p class="flex items-center gap-2"><i class="pi pi-comment text-muted-color"></i> <strong>Motivo:</strong> {{ turnoSeleccionado.description || 'Sin motivo' }}</p>
                    </div>
                    <div class="flex justify-between pt-4 border-t border-surface-200 dark:border-surface-700 mt-4">
                        <div class="flex gap-2">
                            <Button v-if="turnoSeleccionado.editable" icon="pi pi-pencil" label="Editar" text severity="warning" size="small" @click="iniciarEdicion" />
                            <Button v-if="turnoSeleccionado.editable" icon="pi pi-trash" label="Eliminar" text severity="danger" size="small" @click="eliminarTurno" />
                            <span v-if="!turnoSeleccionado.editable" class="text-xs text-muted-color italic flex items-center">Solo lectura</span>
                        </div>
                        <Button label="Cerrar" text severity="secondary" @click="modalVisible = false" />
                    </div>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<style scoped>
/* === Event types === */
:deep(.evento-propio) {
    border-left: 4px solid #0f4fa8 !important;
    border-radius: 6px !important;
}
:deep(.evento-grupal) {
    border-style: dashed !important;
    border-width: 2px !important;
    border-color: #2563eb !important;
    background-color: rgba(59, 130, 246, 0.2) !important;
    border-radius: 6px !important;
}
:deep(.evento-ausencia) {
    border-style: solid !important;
    border-width: 1px !important;
    border-color: #dc2626 !important;
    background-color: rgba(248, 113, 113, 0.75) !important;
    background-image: repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0 6px, rgba(255, 255, 255, 0.05) 6px 12px) !important;
    color: #ffffff !important;
    border-radius: 6px !important;
}

/* === Background: unavailable hours === */
:deep(.fc .fc-bg-event.no-disponible-background) {
    pointer-events: none !important;
    opacity: 1 !important;
    border: 0 !important;
    background-color: rgba(107, 114, 128, 0.22) !important;
    background-image: none !important;
}

/* === Background: absence full day === */
:deep(.fc .fc-bg-event.ausencia-background) {
    pointer-events: none !important;
    opacity: 1 !important;
    border: 0 !important;
    background-color: rgba(248, 113, 113, 0.1) !important;
    background-image: none !important;
}

/* === Today highlight === */
:deep(.fc .fc-day-today) {
    background-color: rgba(56, 189, 248, 0.08) !important;
}

:deep(.fc .fc-col-header-cell.fc-day-today) {
    background-color: rgba(56, 189, 248, 0.14) !important;
}

:deep(.fc .fc-col-header-cell.fc-day-today .fc-col-header-cell-cushion) {
    color: #0369a1 !important;
    font-weight: 700 !important;
    text-decoration: underline;
    text-decoration-color: rgba(3, 105, 161, 0.4);
    text-underline-offset: 4px;
}

/* === Dark mode: FullCalendar chrome === */
:deep(.app-dark .fc .fc-toolbar-title),
:deep(html.dark .fc .fc-toolbar-title) {
    color: var(--text-color) !important;
}
:deep(.app-dark .fc .fc-col-header-cell),
:deep(html.dark .fc .fc-col-header-cell) {
    background-color: var(--surface-card) !important;
    color: var(--text-color) !important;
}
:deep(.app-dark .fc .fc-col-header-cell-cushion),
:deep(html.dark .fc .fc-col-header-cell-cushion) {
    color: var(--text-color) !important;
}
:deep(.app-dark .fc .fc-timegrid-slot),
:deep(html.dark .fc .fc-timegrid-slot) {
    border-color: var(--surface-border) !important;
}
:deep(.app-dark .fc .fc-timegrid-axis),
:deep(html.dark .fc .fc-timegrid-axis) {
    border-color: var(--surface-border) !important;
}
:deep(.app-dark .fc .fc-timegrid-slot-label-cushion),
:deep(html.dark .fc .fc-timegrid-slot-label-cushion) {
    color: var(--text-color) !important;
}
:deep(.app-dark .fc .fc-scrollgrid),
:deep(html.dark .fc .fc-scrollgrid) {
    border-color: var(--surface-border) !important;
}
:deep(.app-dark .fc td),
:deep(html.dark .fc td),
:deep(.app-dark .fc th),
:deep(html.dark .fc th) {
    border-color: var(--surface-border) !important;
}
:deep(.app-dark .fc .fc-button),
:deep(html.dark .fc .fc-button) {
    background-color: var(--surface-card) !important;
    border-color: var(--surface-border) !important;
    color: var(--text-color) !important;
}
:deep(.app-dark .fc .fc-button-active),
:deep(html.dark .fc .fc-button-active) {
    background-color: var(--primary-color) !important;
    border-color: var(--primary-color) !important;
    color: #ffffff !important;
}
:deep(.app-dark .fc .fc-daygrid-day-number),
:deep(html.dark .fc .fc-daygrid-day-number) {
    color: var(--text-color) !important;
}

/* === Dark mode: backgrounds === */
:deep(.app-dark .fc .fc-bg-event.no-disponible-background),
:deep(html.dark .fc .fc-bg-event.no-disponible-background) {
    background-color: rgba(148, 163, 184, 0.2) !important;
    background-image: none !important;
}
:deep(.app-dark .fc .fc-bg-event.ausencia-background),
:deep(html.dark .fc .fc-bg-event.ausencia-background) {
    background-color: rgba(220, 38, 38, 0.15) !important;
    background-image: none !important;
}

:deep(.app-dark .fc .fc-day-today),
:deep(html.dark .fc .fc-day-today) {
    background-color: rgba(56, 189, 248, 0.12) !important;
}

:deep(.app-dark .fc .fc-col-header-cell.fc-day-today),
:deep(html.dark .fc .fc-col-header-cell.fc-day-today) {
    background-color: rgba(56, 189, 248, 0.2) !important;
}

:deep(.app-dark .fc .fc-col-header-cell.fc-day-today .fc-col-header-cell-cushion),
:deep(html.dark .fc .fc-col-header-cell.fc-day-today .fc-col-header-cell-cushion) {
    color: #7dd3fc !important;
    text-decoration-color: rgba(125, 211, 252, 0.45);
}
</style>
