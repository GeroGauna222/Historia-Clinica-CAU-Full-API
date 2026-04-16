<script setup>
import { ref, onMounted, onUnmounted, reactive, computed, watch } from 'vue';
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
const TIPOS_EVENTO_AGENDA = [
    { label: 'Reunion', value: 'Reunion' },
    { label: 'Turno', value: 'Turno' },
    { label: 'Bloqueo', value: 'Bloqueo' },
    { label: 'Ausencia', value: 'Ausencia' }
];

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
    tipo_evento: 'Bloqueo',
    motivo: '',
    usuario_id: ''
});

const nuevoTurnoModalVisible = ref(false);
const pacienteBusqueda = ref('');
const pacientes = ref([]);
const pacienteSeleccionado = ref(null);
const nuevoTurnoTipoEvento = ref('Turno');
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

function normalizarTipoEvento(tipo) {
    const limpio = String(tipo || '')
        .trim()
        .toLowerCase();
    const match = TIPOS_EVENTO_AGENDA.find((opt) => opt.value.toLowerCase() === limpio);
    return match ? match.value : 'Bloqueo';
}

function extraerTipoEventoYMotivo(motivo) {
    const texto = String(motivo || '').trim();
    const match = texto.match(/^\[(Reunion|Turno|Bloqueo|Ausencia)\]\s*(.*)$/i);
    if (!match) {
        return {
            tipoEvento: 'Bloqueo',
            motivoLimpio: texto
        };
    }
    return {
        tipoEvento: normalizarTipoEvento(match[1]),
        motivoLimpio: match[2] || ''
    };
}

function construirMotivoEvento(tipoEvento, motivoLibre) {
    const tipo = normalizarTipoEvento(tipoEvento);
    const detalle = String(motivoLibre || '').trim();
    return detalle ? `[${tipo}] ${detalle}` : `[${tipo}]`;
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
            tipoEvento: e.extendedProps.tipoEvento || 'Bloqueo',
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
            const tipoEvento = info.event.extendedProps.tipoEvento || 'Bloqueo';
            tippy(info.el, {
                content: `<strong>${tipoEvento}</strong><br>${info.event.extendedProps.profesional || 'Profesional'}<br><span style="opacity:0.7">${info.event.extendedProps.description || ''}</span>`,
                allowHTML: true,
                placement: 'top',
                theme: 'medical'
            });
            return;
        }

        const pacNombre = info.event.extendedProps.paciente || '';
        const profNombre = info.event.extendedProps.profesional || '';
        const motivo = info.event.extendedProps.description || '';
        tippy(info.el, {
            content: `<strong>${pacNombre}</strong><br>${profNombre}${motivo ? '<br><span style="opacity:0.7">' + motivo + '</span>' : ''}`,
            allowHTML: true,
            placement: 'top',
            theme: 'medical'
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

        const sujetoActualExiste = sujetos.value.some((s) => Number(s.id) === Number(sujetoSeleccionadoId.value));
        const propio = sujetos.value.find((s) => Number(s.id) === Number(usuarioLogueadoId.value));

        if (!sujetoActualExiste) {
            // Por defecto mostramos la agenda propia; si no aparece en lista, usamos el primer sujeto disponible.
            sujetoSeleccionadoId.value = propio?.id ?? sujetos.value[0]?.id ?? null;
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
    const { tipoEvento, motivoLimpio } = extraerTipoEventoYMotivo(ausencia.motivo);

    const rows = [
        {
            id: `ausencia-${ausencia.id}`,
            title: `${tipoEvento}: ${ausencia.nombre_usuario || 'Profesional'}`,
            start: ausencia.fecha_inicio,
            end: ausencia.fecha_fin,
            backgroundColor: 'rgba(239,68,68,0.12)',
            borderColor: '#EF4444',
            textColor: '#991B1B',
            classNames: ['evento-ausencia'],
            extendedProps: {
                tipo: 'ausencia',
                tipoEvento,
                ausenciaId: ausencia.id,
                usuarioId: ausencia.usuario_id,
                profesional: ausencia.nombre_usuario,
                description: motivoLimpio
            }
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
        backgroundColor: esGrupal ? 'rgba(8,145,178,0.1)' : '#0891B2',
        borderColor: esGrupal ? '#0891B2' : '#0E7490',
        textColor: esGrupal ? '#134E4A' : '#ffffff',
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
    bloqueoForm.tipo_evento = 'Bloqueo';
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
    const motivo = construirMotivoEvento(bloqueoForm.tipo_evento, bloqueoForm.motivo);
    bloqueoGuardando.value = true;
    try {
        await api.post('/ausencias', { fecha_inicio: fechaInicio, fecha_fin: fechaFin, motivo, usuario_id: Number(bloqueoForm.usuario_id) }, { withCredentials: true });
        bloqueoModalVisible.value = false;
        await cargarAgenda();
    } finally {
        bloqueoGuardando.value = false;
    }
}

function abrirModalNuevoTurno(date) {
    nuevoTurnoFecha.value = toLocalDateTimeString(date);
    nuevoTurnoTipoEvento.value = 'Turno';
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
    if (!sujetoSeleccionadoId.value || !nuevoTurnoFecha.value) return;
    const tipoEvento = normalizarTipoEvento(nuevoTurnoTipoEvento.value);
    nuevoTurnoGuardando.value = true;
    try {
        if (tipoEvento === 'Turno') {
            if (!pacienteSeleccionado.value) {
                toast.add({ severity: 'warn', summary: 'Paciente requerido', detail: 'Selecciona un paciente para crear un turno.', life: 3500 });
                return;
            }
            const resp = await api.post(
                '/turnos',
                { paciente_id: pacienteSeleccionado.value.id, usuario_id: Number(sujetoSeleccionadoId.value), fecha_inicio: nuevoTurnoFecha.value, motivo: nuevoTurnoMotivo.value },
                { withCredentials: true }
            );
            if (resp.data?.ajuste_horario?.aplicado) {
                toast.add({ severity: 'info', summary: 'Horario ajustado', detail: `Inicio ajustado a ${resp.data.ajuste_horario.inicio_ajustado}`, life: 4500 });
            }
        } else {
            const inicio = parseDateSafe(nuevoTurnoFecha.value);
            if (!inicio) {
                toast.add({ severity: 'warn', summary: 'Fecha invalida', detail: 'No se pudo interpretar la fecha del evento.', life: 3500 });
                return;
            }
            const fin = new Date(inicio);
            fin.setMinutes(fin.getMinutes() + (duracionTurno.value || 20));
            const motivo = construirMotivoEvento(tipoEvento, nuevoTurnoMotivo.value);
            await api.post(
                '/ausencias',
                {
                    fecha_inicio: toLocalDateTimeString(inicio),
                    fecha_fin: toLocalDateTimeString(fin),
                    motivo,
                    usuario_id: Number(sujetoSeleccionadoId.value)
                },
                { withCredentials: true }
            );
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

        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
            <div>
                <h1 class="text-2xl font-heading font-bold text-[#134E4A] dark:text-teal-100 tracking-tight">Agenda</h1>
                <p class="text-xs text-slate-400 dark:text-slate-500 mt-1 font-sans">Click en una celda para crear un evento. Las zonas grises indican horarios no disponibles.</p>
            </div>

            <div class="flex items-center gap-3">
                <Select v-if="canSelectSubject" v-model="sujetoSeleccionadoId" :options="sujetos" optionValue="id" optionLabel="nombre" filter class="min-w-56">
                    <template #option="slotProps">
                        {{ slotProps.option.nombre }} <span class="text-muted-color text-xs">({{ slotProps.option.rol }})</span>
                    </template>
                </Select>
                <span v-else class="text-sm font-heading font-semibold text-[#134E4A] dark:text-teal-200">{{ sujetoActualNombre }}</span>
                <Button label="Agregar evento" icon="pi pi-calendar-plus" severity="secondary" class="!rounded-lg !text-sm !font-sans" @click="abrirModalBloqueo(new Date())" />
            </div>
        </div>

        <!-- Leyenda -->
        <div class="flex items-center gap-4 mb-4 flex-wrap">
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0891B2]/10 text-[#0891B2] dark:bg-cyan-900/30 dark:text-cyan-300 text-xs font-medium">
                <span class="w-2.5 h-2.5 rounded-full bg-[#0891B2] inline-block"></span> Individual
            </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0891B2]/5 border border-dashed border-[#0891B2] text-[#0891B2] dark:border-cyan-400 dark:text-cyan-300 text-xs font-medium">
                <span class="w-2.5 h-2.5 rounded-full border-2 border-dashed border-[#0891B2] dark:border-cyan-400 inline-block"></span> Grupal
            </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 text-xs font-medium">
                <span class="w-2.5 h-2.5 rounded-full bg-red-400 dark:bg-red-500 inline-block"></span> Ausencia
            </span>
            <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 text-xs font-medium">
                <span class="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-600 inline-block"></span> No disponible
            </span>
        </div>

        <!-- Calendar container -->
        <div class="flex-1 bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-[#E0F2FE] dark:border-slate-700 p-4 overflow-hidden transition-colors">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>

        <!-- Modal: Nuevo turno -->
        <Dialog
            v-model:visible="nuevoTurnoModalVisible"
            modal
            :header="nuevoTurnoTipoEvento === 'Turno' ? 'Nuevo turno' : 'Nuevo evento de agenda'"
            :style="{ width: '520px' }"
            :pt="{ header: { class: 'font-heading' } }"
        >
            <div class="space-y-4">
                <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#F0FDFA] dark:bg-teal-900/20 text-[#0891B2] dark:text-cyan-300 text-sm font-medium">
                    <i class="pi pi-calendar"></i>
                    <span>{{ nuevoTurnoFecha }}</span>
                </div>
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-tag mr-1.5 text-[#0891B2]"></i>Tipo de evento</label>
                    <Select v-model="nuevoTurnoTipoEvento" :options="TIPOS_EVENTO_AGENDA" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div v-if="nuevoTurnoTipoEvento === 'Turno'">
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-user mr-1.5 text-[#0891B2]"></i>Paciente</label>
                    <InputText v-model="pacienteBusqueda" @input="buscarPacientes" class="w-full" placeholder="Buscar por DNI o nombre..." />
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
                    <div v-if="pacienteSeleccionado" class="flex items-center gap-2 mt-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-xs font-medium">
                        <i class="pi pi-check-circle"></i>
                        {{ pacienteSeleccionado.apellido }} {{ pacienteSeleccionado.nombre }}
                    </div>
                </div>
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">
                        <i class="pi pi-comment mr-1.5 text-[#0891B2]"></i>{{ nuevoTurnoTipoEvento === 'Turno' ? 'Motivo' : 'Detalle' }}
                    </label>
                    <InputText
                        v-model="nuevoTurnoMotivo"
                        class="w-full"
                        :placeholder="nuevoTurnoTipoEvento === 'Turno' ? 'Motivo de la consulta' : 'Detalle opcional del evento'"
                    />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" class="!rounded-lg" @click="nuevoTurnoModalVisible = false" />
                <Button
                    :label="nuevoTurnoTipoEvento === 'Turno' ? 'Guardar turno' : 'Guardar evento'"
                    icon="pi pi-check"
                    :loading="nuevoTurnoGuardando"
                    class="!rounded-lg !bg-[#0891B2] !border-[#0891B2]"
                    @click="guardarNuevoTurno"
                />
            </template>
        </Dialog>

        <!-- Modal: Evento de agenda -->
        <Dialog v-model:visible="bloqueoModalVisible" modal header="Evento de agenda" :style="{ width: '480px' }" :pt="{ header: { class: 'font-heading' } }">
            <div class="space-y-4">
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-tag mr-1.5 text-red-500"></i>Tipo de evento</label>
                    <Select v-model="bloqueoForm.tipo_evento" :options="TIPOS_EVENTO_AGENDA" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-calendar mr-1.5 text-red-500"></i>Fecha</label>
                    <InputText type="date" v-model="bloqueoForm.fecha" class="w-full" />
                </div>
                <label class="flex items-center gap-2.5 cursor-pointer px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                    <Checkbox v-model="bloqueoForm.todoDia" :binary="true" />
                    <span class="text-sm font-medium text-[#134E4A] dark:text-slate-200">Todo el dia</span>
                </label>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Hora inicio</label>
                        <InputText type="time" v-model="bloqueoForm.horaInicio" class="w-full" :disabled="bloqueoForm.todoDia" />
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Hora fin</label>
                        <InputText type="time" v-model="bloqueoForm.horaFin" class="w-full" :disabled="bloqueoForm.todoDia" />
                    </div>
                </div>
                <div>
                    <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200"><i class="pi pi-comment mr-1.5 text-red-500"></i>Detalle</label>
                    <InputText v-model="bloqueoForm.motivo" class="w-full" placeholder="Detalle opcional del evento" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" class="!rounded-lg" @click="bloqueoModalVisible = false" />
                <Button label="Guardar evento" icon="pi pi-check" :loading="bloqueoGuardando" severity="danger" class="!rounded-lg" @click="guardarBloqueo" />
            </template>
        </Dialog>

        <!-- Modal: Detalle / Editar turno -->
        <Dialog v-model:visible="modalVisible" modal :header="editando ? 'Editar turno' : 'Detalle del turno'" :style="{ width: '480px' }" :pt="{ header: { class: 'font-heading' } }">
            <div v-if="turnoSeleccionado" class="space-y-4">
                <!-- Ausencia -->
                <div v-if="turnoSeleccionado.tipo === 'ausencia'">
                    <div class="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm font-medium">
                        <i class="pi pi-calendar-times"></i> {{ turnoSeleccionado.tipoEvento || 'Bloqueo' }}
                    </div>
                    <div class="space-y-2 text-sm">
                        <p class="flex items-center gap-2">
                            <i class="pi pi-user text-slate-400"></i> <strong class="text-[#134E4A] dark:text-slate-200">Profesional:</strong> <span class="text-slate-600 dark:text-slate-300">{{ turnoSeleccionado.profesional }}</span>
                        </p>
                        <p class="flex items-center gap-2">
                            <i class="pi pi-comment text-slate-400"></i> <strong class="text-[#134E4A] dark:text-slate-200">Detalle:</strong> <span class="text-slate-600 dark:text-slate-300">{{ turnoSeleccionado.description || 'Sin detalle' }}</span>
                        </p>
                    </div>
                    <div class="flex justify-end gap-2 mt-5">
                        <Button label="Cerrar" text severity="secondary" class="!rounded-lg" @click="modalVisible = false" />
                        <Button v-if="canDeleteAusencia" label="Eliminar evento" severity="danger" icon="pi pi-trash" class="!rounded-lg" @click="eliminarAusencia" />
                    </div>
                </div>
                <!-- Editando -->
                <div v-else-if="editando">
                    <div class="grid grid-cols-2 gap-3 mb-3">
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Fecha</label>
                            <InputText type="date" v-model="fechaEdit" class="w-full" />
                        </div>
                        <div>
                            <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Hora</label>
                            <InputText type="time" v-model="horaEdit" class="w-full" />
                        </div>
                    </div>
                    <div>
                        <label class="font-heading font-semibold text-sm block mb-1.5 text-[#134E4A] dark:text-slate-200">Motivo</label>
                        <InputText v-model="turnoSeleccionado.description" class="w-full" />
                    </div>
                    <div class="flex justify-end gap-2 mt-5">
                        <Button label="Cancelar" text severity="secondary" class="!rounded-lg" @click="editando = false" />
                        <Button label="Guardar cambios" icon="pi pi-check" class="!rounded-lg !bg-[#0891B2] !border-[#0891B2]" @click="guardarEdicion" />
                    </div>
                </div>
                <!-- Vista detalle -->
                <div v-else>
                    <div class="mb-4">
                        <Tag :value="turnoSeleccionado.tipo === 'grupal' ? 'Grupal' : 'Individual'" :severity="turnoSeleccionado.tipo === 'grupal' ? 'info' : 'primary'" rounded class="!font-heading" />
                    </div>
                    <div class="space-y-3 text-sm">
                        <div class="flex items-center gap-3 p-3 rounded-lg bg-[#F0FDFA] dark:bg-teal-900/15">
                            <div class="w-9 h-9 rounded-full bg-[#0891B2] flex items-center justify-center text-white text-sm font-heading font-bold shrink-0">
                                {{ (turnoSeleccionado.paciente || '?')[0].toUpperCase() }}
                            </div>
                            <div>
                                <p class="font-semibold text-[#134E4A] dark:text-slate-200">{{ turnoSeleccionado.paciente }}</p>
                                <p class="text-xs text-slate-400">DNI: {{ turnoSeleccionado.dni }}</p>
                            </div>
                        </div>
                        <p class="flex items-center gap-2">
                            <i class="pi pi-briefcase text-[#0891B2]"></i> <span class="text-slate-600 dark:text-slate-300">{{ turnoSeleccionado.profesional }}</span>
                        </p>
                        <p class="flex items-center gap-2">
                            <i class="pi pi-comment text-[#0891B2]"></i> <span class="text-slate-600 dark:text-slate-300">{{ turnoSeleccionado.description || 'Sin motivo' }}</span>
                        </p>
                    </div>
                    <div class="flex justify-between pt-4 border-t border-[#E0F2FE] dark:border-slate-700 mt-4">
                        <div class="flex gap-2">
                            <Button v-if="turnoSeleccionado.editable" icon="pi pi-pencil" label="Editar" text severity="warning" size="small" class="!rounded-lg" @click="iniciarEdicion" />
                            <Button v-if="turnoSeleccionado.editable" icon="pi pi-trash" label="Eliminar" text severity="danger" size="small" class="!rounded-lg" @click="eliminarTurno" />
                            <span v-if="!turnoSeleccionado.editable" class="text-xs text-slate-400 italic flex items-center gap-1"><i class="pi pi-eye text-xs"></i>Solo lectura</span>
                        </div>
                        <Button label="Cerrar" text severity="secondary" class="!rounded-lg" @click="modalVisible = false" />
                    </div>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<style scoped>
/* Calendar Medical Clean theme is loaded from @/assets/calendar-medical.css */
/* Only view-specific overrides go here */
</style>
