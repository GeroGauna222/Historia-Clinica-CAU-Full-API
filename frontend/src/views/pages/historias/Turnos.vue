<script setup>
import { ref, onMounted, onUnmounted, reactive, computed } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import api from '@/api/axios';

// PrimeVue Imports
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';

/* -------------------------------------------------------------------------- */
/* LOCALE                                                                     */
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
        day: 'Dia',
        list: 'Agenda'
    },
    weekText: 'Sm',
    allDayText: 'Todo el dia',
    moreLinkText: 'mas',
    noEventsText: 'No hay eventos para mostrar'
};

/* -------------------------------------------------------------------------- */
/* VARIABLES                                                                   */
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
const rolUsuario = ref('');
const usuarioLogueadoId = ref(null);
const profesionales = ref([]);

const bloqueoModalVisible = ref(false);
const bloqueoGuardando = ref(false);
const bloqueoForm = reactive({
    fecha: '',
    todoDia: true,
    horaInicio: '08:00',
    horaFin: '09:00',
    motivo: '',
    usuario_id: ''
});

const esDirectorOAdmin = computed(() => ['director', 'administrativo'].includes((rolUsuario.value || '').toLowerCase().trim()));
const puedeEliminarAusencia = computed(() => {
    if (!turnoSeleccionado.value || turnoSeleccionado.value.tipo !== 'ausencia') return false;
    if (esDirectorOAdmin.value) return true;
    return Number(turnoSeleccionado.value.usuarioId) === Number(usuarioLogueadoId.value);
});

/* -------------------------------------------------------------------------- */
/* HELPERS                                                                     */
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
        if (c.length === 3) c = [c[0], c[0], c[1], c[1], c[2], c[2]];
        c = '0x' + c.join('');
        return 'rgba(' + [(c >> 16) & 255, (c >> 8) & 255, c & 255].join(',') + ',' + alpha + ')';
    }
    return hex;
}

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

    return inicio.getHours() === 0 && inicio.getMinutes() === 0 && inicio.getSeconds() === 0 && fin.getHours() === 23 && fin.getMinutes() === 59 && fin.getSeconds() >= 59 && inicio.toDateString() === fin.toDateString();
}

const formatearFecha = (date) => new Date(date).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
const formatearHora = (date) => new Date(date).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
const formatearRango = (inicio, fin) => `${formatearFecha(inicio)} ${formatearHora(inicio)} - ${formatearHora(fin)}`;

/* -------------------------------------------------------------------------- */
/* CONFIG CALENDARIO                                                          */
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
    slotEventOverlap: true,
    eventOverlap: true,
    eventOrder: 'order',
    events: eventos,

    dateClick(info) {
        abrirModalBloqueo(info.date);
    },

    eventClick(info) {
        const e = info.event;
        const tipo = e.extendedProps.tipo;
        if (tipo === 'ausencia_bg') return;

        turnoSeleccionado.value = {
            id: e.id,
            turnoId: e.extendedProps.turnoId,
            tipo,
            editable: e.extendedProps.editable,
            paciente: e.extendedProps.paciente,
            dni: e.extendedProps.dni,
            profesional: e.extendedProps.profesional,
            description: e.extendedProps.description,
            ausenciaId: e.extendedProps.ausenciaId,
            usuarioId: e.extendedProps.usuarioId,
            start: e.start,
            end: e.end
        };
        editando.value = false;
        modalVisible.value = true;
    },

    eventDidMount(info) {
        const tipo = info.event.extendedProps.tipo;
        if (tipo === 'ausencia_bg') return;

        if (tipo === 'ausencia') {
            const profesional = info.event.extendedProps.profesional || 'Profesional';
            const desc = info.event.extendedProps.description || 'Sin motivo';
            tippy(info.el, {
                content: `<strong>No disponible:</strong> ${profesional}<br><span style="font-size:0.8em; opacity:0.8">${desc}</span>`,
                allowHTML: true,
                placement: 'top'
            });
            return;
        }

        const desc = info.event.extendedProps.description || 'Sin motivo';
        const paciente = info.event.extendedProps.paciente;
        const profesional = info.event.extendedProps.profesional;
        const esGrupal = info.event.extendedProps.tipo === 'grupal';
        const tituloTooltip = esGrupal ? `<strong style="color: #ffcc80">${profesional}</strong><br>Paciente: ${paciente}` : `<strong>${paciente}</strong>`;

        tippy(info.el, {
            content: `${tituloTooltip}<br><span style="font-size:0.8em; opacity:0.8">${desc}</span>`,
            allowHTML: true,
            placement: 'top'
        });
    }
});

/* -------------------------------------------------------------------------- */
/* DATOS                                                                       */
/* -------------------------------------------------------------------------- */
async function cargarDatosUsuario() {
    try {
        const resp = await api.get('/usuarios/me', { withCredentials: true });
        const data = resp.data;
        duracionTurno.value = data.duracion_turno || 30;
        nombreProfesionalLogueado.value = data.nombre || data.email;
        rolUsuario.value = (data.rol || '').toLowerCase().trim();
        usuarioLogueadoId.value = data.id;
        bloqueoForm.usuario_id = ['director', 'administrativo'].includes(rolUsuario.value) ? '' : data.id || '';
    } catch (e) {
        console.error('Error cargando usuario', e);
    }
}

async function cargarProfesionales() {
    if (!esDirectorOAdmin.value) {
        profesionales.value = [];
        return;
    }

    try {
        const resp = await api.get('/profesionales', { withCredentials: true });
        profesionales.value = resp.data || [];
    } catch (e) {
        console.error('Error cargando profesionales', e);
    }
}

function crearEventosAusencia(ausencia) {
    const inicio = parseDateSafe(ausencia.fecha_inicio);
    const fin = parseDateSafe(ausencia.fecha_fin);
    if (!inicio || !fin) return [];

    const profesional = ausencia.nombre_usuario || 'Profesional';
    const descripcion = ausencia.motivo || '';

    const eventosAusencia = [
        {
            id: `ausencia-${ausencia.id}`,
            title: `No disponible: ${profesional}`,
            start: ausencia.fecha_inicio,
            end: ausencia.fecha_fin,
            backgroundColor: '#9ca3af',
            borderColor: '#6b7280',
            textColor: '#111827',
            classNames: ['evento-ausencia'],
            order: 15,
            extendedProps: {
                tipo: 'ausencia',
                ausenciaId: ausencia.id,
                usuarioId: ausencia.usuario_id,
                profesional,
                description: descripcion,
                editable: false
            }
        }
    ];

    if (esDiaCompletoAusencia(ausencia, inicio, fin)) {
        const inicioDia = new Date(inicio);
        inicioDia.setHours(0, 0, 0, 0);

        const finDia = new Date(inicioDia);
        finDia.setDate(finDia.getDate() + 1);

        eventosAusencia.push({
            id: `ausencia-bg-${ausencia.id}`,
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

async function cargarTurnosProfesional() {
    try {
        const [respTurnos, respAusencias] = await Promise.all([api.get('/turnos/profesional/completo', { withCredentials: true }), api.get('/ausencias', { withCredentials: true })]);
        const dataTurnos = respTurnos.data || [];
        const dataAusencias = respAusencias.data || [];

        const mapaTurnos = new Map();
        const gruposDetectados = {};
        const miNombre = (nombreProfesionalLogueado.value || '').toLowerCase().trim();

        dataTurnos.forEach((t) => {
            const profNombre = (t.profesional || '').toLowerCase().trim();
            const esPropio = miNombre && profNombre.includes(miNombre);
            const esGrupal = !esPropio;
            const colorFinal = esPropio ? '#1976D2' : stringToColor(t.profesional || 'Desconocido');

            if (!mapaTurnos.has(t.id)) {
                mapaTurnos.set(t.id, {
                    id: t.id,
                    title: esGrupal ? `${t.profesional} (${t.paciente})` : t.paciente,
                    start: t.start,
                    end: t.end,
                    backgroundColor: esGrupal ? hexToRgba(colorFinal, 0.1) : colorFinal,
                    borderColor: colorFinal,
                    textColor: esGrupal ? '#333' : '#ffffff',
                    classNames: esGrupal ? ['evento-grupal'] : ['evento-propio'],
                    order: esGrupal ? 0 : 10,
                    extendedProps: {
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

        const eventosAusencias = dataAusencias.flatMap((a) => crearEventosAusencia(a));

        eventos.value = [...Array.from(mapaTurnos.values()), ...eventosAusencias];
        calendarOptions.events = eventos.value;

        leyendaGrupos.value = Object.keys(gruposDetectados).map((nombre) => ({
            nombre,
            colorOriginal: gruposDetectados[nombre],
            colorTransparente: hexToRgba(gruposDetectados[nombre], 0.7)
        }));
    } catch (error) {
        console.error('Error cargando turnos/ausencias:', error);
    }
}

/* -------------------------------------------------------------------------- */
/* BLOQUEOS                                                                    */
/* -------------------------------------------------------------------------- */
function abrirModalBloqueo(fechaBase) {
    const base = fechaBase || new Date();
    const inicioBase = new Date(base);
    const finBase = new Date(base);
    finBase.setMinutes(finBase.getMinutes() + (duracionTurno.value || 30));

    bloqueoForm.fecha = toDateInput(inicioBase);
    bloqueoForm.todoDia = true;
    bloqueoForm.horaInicio = toTimeInput(inicioBase);
    bloqueoForm.horaFin = toTimeInput(finBase);
    bloqueoForm.motivo = '';

    if (!esDirectorOAdmin.value) {
        bloqueoForm.usuario_id = usuarioLogueadoId.value;
    }

    bloqueoModalVisible.value = true;
}

async function guardarBloqueo() {
    if (!bloqueoForm.fecha) {
        alert('Debes seleccionar una fecha');
        return;
    }

    if (esDirectorOAdmin.value && !bloqueoForm.usuario_id) {
        alert('Debes seleccionar un profesional');
        return;
    }

    const fechaInicio = bloqueoForm.todoDia ? `${bloqueoForm.fecha}T00:00:00` : `${bloqueoForm.fecha}T${bloqueoForm.horaInicio}:00`;
    const fechaFin = bloqueoForm.todoDia ? `${bloqueoForm.fecha}T23:59:59` : `${bloqueoForm.fecha}T${bloqueoForm.horaFin}:00`;

    if (new Date(fechaInicio) >= new Date(fechaFin)) {
        alert('La hora de fin debe ser mayor a la hora de inicio');
        return;
    }

    const payload = {
        fecha_inicio: fechaInicio,
        fecha_fin: fechaFin,
        motivo: bloqueoForm.motivo
    };

    if (bloqueoForm.usuario_id) {
        payload.usuario_id = Number(bloqueoForm.usuario_id);
    }

    bloqueoGuardando.value = true;
    try {
        await api.post('/ausencias', payload, { withCredentials: true });
        bloqueoModalVisible.value = false;
        await cargarTurnosProfesional();
    } catch (err) {
        console.error('Error creando bloqueo:', err);
        alert(err.response?.data?.error || 'No se pudo crear el bloqueo');
    } finally {
        bloqueoGuardando.value = false;
    }
}

async function eliminarAusencia() {
    if (!turnoSeleccionado.value?.ausenciaId) return;
    if (!confirm('Seguro que deseas desbloquear este rango?')) return;

    try {
        await api.delete(`/ausencias/${turnoSeleccionado.value.ausenciaId}`, { withCredentials: true });
        modalVisible.value = false;
        await cargarTurnosProfesional();
    } catch (err) {
        console.error('Error eliminando ausencia:', err);
        alert(err.response?.data?.error || 'No se pudo eliminar el bloqueo');
    }
}

/* -------------------------------------------------------------------------- */
/* TURNOS                                                                      */
/* -------------------------------------------------------------------------- */
function iniciarEdicion() {
    const fechaObj = new Date(turnoSeleccionado.value.start);
    fechaEdit.value = `${fechaObj.getFullYear()}-${pad(fechaObj.getMonth() + 1)}-${pad(fechaObj.getDate())}`;
    horaEdit.value = `${pad(fechaObj.getHours())}:${pad(fechaObj.getMinutes())}`;
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
        await cargarTurnosProfesional();
        alert('Turno actualizado correctamente');
    } catch (err) {
        console.error('Error actualizando turno:', err);
        alert('Error al actualizar: ' + (err.response?.data?.error || err.message));
    }
}

async function eliminarTurno() {
    if (!confirm('Seguro que deseas eliminar este turno?')) return;

    try {
        await api.delete(`/turnos/${turnoSeleccionado.value.id}`, { withCredentials: true });
        modalVisible.value = false;

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
    await cargarProfesionales();
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
                    Mi Agenda
                    <span class="text-xs font-normal text-gray-500 bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded">
                        {{ nombreProfesionalLogueado || 'Cargando...' }}
                    </span>
                </h1>
                <p class="text-xs text-gray-500 mt-1">Haz click en una celda del calendario para bloquear disponibilidad.</p>
            </div>

            <div class="flex flex-wrap items-center gap-4 text-sm">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-blue-600 border border-blue-800"></span>
                    <span class="text-gray-800 dark:text-gray-200 font-medium">Mis turnos</span>
                </div>

                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-sm bg-gray-400 border border-gray-600"></span>
                    <span class="text-gray-800 dark:text-gray-200 font-medium">No disponible</span>
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

        <Dialog v-model:visible="modalVisible" modal :header="editando ? 'Editar turno' : 'Detalle'" :style="{ width: '480px' }" class="p-fluid">
            <div v-if="turnoSeleccionado" class="space-y-4">
                <div v-if="turnoSeleccionado.tipo === 'ausencia'" class="bg-gray-50 p-4 rounded border border-gray-300">
                    <p class="text-gray-700 font-bold flex items-center gap-2"><i class="pi pi-ban"></i> Bloqueo de agenda</p>
                    <p class="text-sm text-gray-600 mt-2"><strong>Profesional:</strong> {{ turnoSeleccionado.profesional }}</p>
                    <p class="text-sm text-gray-600 mt-1"><strong>Rango:</strong> {{ formatearRango(turnoSeleccionado.start, turnoSeleccionado.end) }}</p>
                    <p class="text-sm text-gray-600 mt-1"><strong>Motivo:</strong> {{ turnoSeleccionado.description || 'Sin motivo' }}</p>

                    <div class="flex justify-end gap-2 mt-4">
                        <Button label="Cerrar" severity="secondary" text @click="modalVisible = false" />
                        <Button v-if="puedeEliminarAusencia" label="Desbloquear" icon="pi pi-trash" severity="danger" @click="eliminarAusencia" />
                    </div>
                </div>

                <div v-else>
                    <div v-if="editando">
                        <div class="field mb-3">
                            <label class="font-semibold block mb-1">Motivo / Descripcion</label>
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
                            <Button label="Guardar cambios" icon="pi pi-check" @click="guardarEdicion" />
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

        <Dialog v-model:visible="bloqueoModalVisible" modal header="Bloquear disponibilidad" :style="{ width: '480px' }" class="p-fluid">
            <div class="space-y-4">
                <div>
                    <label class="block mb-1 font-semibold">Fecha</label>
                    <InputText type="date" v-model="bloqueoForm.fecha" class="w-full" />
                </div>

                <div v-if="esDirectorOAdmin">
                    <label class="block mb-1 font-semibold">Profesional</label>
                    <select v-model="bloqueoForm.usuario_id" class="w-full p-2 border border-gray-300 rounded">
                        <option value="" disabled>Seleccionar profesional</option>
                        <option v-for="p in profesionales" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                    </select>
                </div>

                <label class="flex items-center gap-2">
                    <input v-model="bloqueoForm.todoDia" type="checkbox" />
                    <span>Todo el dia</span>
                </label>

                <div v-if="!bloqueoForm.todoDia" class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-semibold">Hora inicio</label>
                        <InputText type="time" v-model="bloqueoForm.horaInicio" class="w-full" />
                    </div>
                    <div>
                        <label class="block mb-1 font-semibold">Hora fin</label>
                        <InputText type="time" v-model="bloqueoForm.horaFin" class="w-full" />
                    </div>
                </div>

                <div>
                    <label class="block mb-1 font-semibold">Motivo (opcional)</label>
                    <InputText v-model="bloqueoForm.motivo" class="w-full" />
                </div>
            </div>

            <template #footer>
                <div class="flex justify-end gap-2">
                    <Button label="Cancelar" severity="secondary" text @click="bloqueoModalVisible = false" />
                    <Button label="Guardar bloqueo" icon="pi pi-lock" :loading="bloqueoGuardando" @click="guardarBloqueo" />
                </div>
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
:deep(.evento-grupal) {
    border-style: dashed !important;
    border-width: 2px !important;
    z-index: 1 !important;
}

:deep(.evento-propio) {
    border-style: solid !important;
    border-width: 0 !important;
    border-left-width: 4px !important;
    z-index: 10 !important;
    box-shadow:
        0 4px 6px -1px rgba(0, 0, 0, 0.1),
        0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

:deep(.evento-ausencia) {
    border-style: dashed !important;
    border-width: 2px !important;
    font-weight: 600;
}

:deep(.ausencia-background) {
    pointer-events: none !important;
}

:deep(.fc-event-title) {
    font-weight: 600;
}

:deep(.app-dark .fc),
:deep(html.dark .fc) {
    --fc-page-bg-color: #1b1b1b;
    --fc-neutral-bg-color: #2a2a2a;
    --fc-list-event-hover-bg-color: #333;
    --fc-theme-standard-border-color: #333;
    color: #e5e7eb;
}
</style>
