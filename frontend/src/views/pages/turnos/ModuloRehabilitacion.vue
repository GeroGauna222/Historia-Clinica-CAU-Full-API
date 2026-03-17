<script setup>
import { ref, reactive, onMounted } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import api from '@/api/axios';

import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const gruposRehab = ref([]);
const filtroGrupoId = ref('');
const rolUsuario = ref('');
const eventos = ref([]);
const seleccionado = ref(null);
const detalleVisible = ref(false);

const modalNuevoVisible = ref(false);
const DURACION_GRUPAL_DEFAULT = 20;
const nuevo = reactive({
    grupo_id: '',
    fecha_inicio: '',
    motivo: '',
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
        nuevo.fecha_inicio = toLocalDateTimeString(info.date);
        nuevo.paciente = null;
        nuevo.pacienteBusqueda = '';
        nuevo.motivo = '';
        nuevo.duracion_minutos = DURACION_GRUPAL_DEFAULT;
        pacientes.value = [];
        if (filtroGrupoId.value) nuevo.grupo_id = filtroGrupoId.value;
        modalNuevoVisible.value = true;
    },
    eventClick(info) {
        seleccionado.value = {
            id: info.event.extendedProps.turnoId || info.event.id,
            grupo_nombre: info.event.extendedProps.grupo_nombre,
            paciente: info.event.extendedProps.paciente,
            dni: info.event.extendedProps.dni,
            description: info.event.extendedProps.description,
            editable: Boolean(info.event.extendedProps.editable),
            start: info.event.start,
            end: info.event.end
        };
        detalleVisible.value = true;
    }
});

function mapEvento(t) {
    return {
        id: `rehab-${t.id}`,
        title: `${t.grupo_nombre}: ${t.paciente}`,
        start: t.start,
        end: t.end,
        backgroundColor: 'rgba(16, 185, 129, 0.18)',
        borderColor: '#059669',
        textColor: '#111827',
        classNames: ['evento-rehab'],
        extendedProps: {
            turnoId: t.id,
            grupo_id: t.grupo_id,
            grupo_nombre: t.grupo_nombre,
            paciente: t.paciente,
            dni: t.dni,
            description: t.description,
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
}

async function crearTurno() {
    if (!nuevo.grupo_id || !nuevo.fecha_inicio || !nuevo.paciente) return;
    const fechaFin = sumarMinutosISO(nuevo.fecha_inicio, nuevo.duracion_minutos);
    if (!fechaFin) {
        toast.add({ severity: 'error', summary: 'Fecha invalida', detail: 'No se pudo calcular la fecha de fin del turno.', life: 4500 });
        return;
    }
    guardandoNuevo.value = true;
    try {
        const resp = await api.post(
            '/turnos/grupales',
            {
                grupo_id: Number(nuevo.grupo_id),
                paciente_id: nuevo.paciente.id,
                fecha_inicio: nuevo.fecha_inicio,
                fecha_fin: fechaFin,
                motivo: nuevo.motivo
            },
            { withCredentials: true }
        );
        if (resp.data?.ajuste_horario?.aplicado) {
            toast.add({ severity: 'info', summary: 'Horario ajustado', detail: `Inicio ajustado a ${resp.data.ajuste_horario.inicio_ajustado}`, life: 4500 });
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
        const resp = await api.put(`/turnos/grupales/${seleccionado.value.id}`, { fecha_inicio: edit.fecha_inicio, fecha_fin: fechaFin, motivo: edit.motivo }, { withCredentials: true });
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
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div>
                <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">Modulo de Rehabilitacion</h1>
                <p class="text-xs text-gray-500 mt-1">Visor combinado de turnos grupales de grupos marcados como rehabilitacion.</p>
            </div>
            <div class="flex items-center gap-3">
                <select v-model="filtroGrupoId" class="p-2 border border-gray-300 rounded min-w-56" @change="cargarTurnos">
                    <option value="">Todos los grupos rehab</option>
                    <option v-for="g in gruposRehab" :key="g.id" :value="g.id">{{ g.nombre }}</option>
                </select>
                <Button v-if="canEdit()" label="Nuevo turno grupal" icon="pi pi-plus" @click="modalNuevoVisible = true" />
            </div>
        </div>

        <div class="flex-1 bg-surface-0 dark:bg-surface-900 rounded-2xl shadow border border-surface-200 dark:border-surface-700 p-4 overflow-hidden">
            <FullCalendar :options="calendarOptions" class="h-full" />
        </div>

        <Dialog v-model:visible="modalNuevoVisible" modal header="Nuevo turno grupal rehab" :style="{ width: '520px' }">
            <div class="space-y-3">
                <div>
                    <label class="font-semibold block mb-1">Grupo</label>
                    <select v-model="nuevo.grupo_id" class="w-full p-2 border border-gray-300 rounded">
                        <option value="" disabled>Seleccionar grupo</option>
                        <option v-for="g in gruposRehab" :key="g.id" :value="g.id">{{ g.nombre }}</option>
                    </select>
                </div>
                <div>
                    <label class="font-semibold block mb-1">Fecha/hora</label>
                    <InputText type="datetime-local" v-model="nuevo.fecha_inicio" class="w-full" />
                </div>
                <div>
                    <label class="font-semibold block mb-1">Paciente</label>
                    <InputText v-model="nuevo.pacienteBusqueda" @input="buscarPacientes" class="w-full" />
                    <ul v-if="pacientes.length" class="border rounded mt-1 max-h-40 overflow-y-auto">
                        <li v-for="p in pacientes" :key="p.id" class="px-2 py-1 hover:bg-gray-100 cursor-pointer" @click="seleccionarPaciente(p)">{{ p.apellido }} {{ p.nombre }} ({{ p.dni }})</li>
                    </ul>
                </div>
                <div>
                    <label class="font-semibold block mb-1">Motivo</label>
                    <InputText v-model="nuevo.motivo" class="w-full" />
                </div>
                <div>
                    <label class="font-semibold block mb-1">Duracion (minutos)</label>
                    <InputText type="number" min="5" step="5" v-model.number="nuevo.duracion_minutos" class="w-full" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="modalNuevoVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoNuevo" @click="crearTurno" />
            </template>
        </Dialog>

        <Dialog v-model:visible="detalleVisible" modal header="Detalle turno rehab" :style="{ width: '460px' }">
            <div v-if="seleccionado" class="space-y-2">
                <p><strong>Grupo:</strong> {{ seleccionado.grupo_nombre }}</p>
                <p><strong>Paciente:</strong> {{ seleccionado.paciente }}</p>
                <p><strong>DNI:</strong> {{ seleccionado.dni }}</p>
                <p><strong>Motivo:</strong> {{ seleccionado.description || 'Sin motivo' }}</p>
                <div class="flex justify-between mt-4">
                    <div class="flex gap-2">
                        <Button v-if="seleccionado.editable" label="Editar" icon="pi pi-pencil" text severity="warning" @click="abrirEditar" />
                        <Button v-if="seleccionado.editable" label="Eliminar" icon="pi pi-trash" text severity="danger" :loading="eliminando" @click="eliminarTurno" />
                    </div>
                    <Button label="Cerrar" text severity="secondary" @click="detalleVisible = false" />
                </div>
            </div>
        </Dialog>

        <Dialog v-model:visible="modalEditarVisible" modal header="Editar turno rehab" :style="{ width: '460px' }">
            <div class="space-y-3">
                <div>
                    <label class="font-semibold block mb-1">Fecha/hora</label>
                    <InputText type="datetime-local" v-model="edit.fecha_inicio" class="w-full" />
                </div>
                <div>
                    <label class="font-semibold block mb-1">Motivo</label>
                    <InputText v-model="edit.motivo" class="w-full" />
                </div>
                <div>
                    <label class="font-semibold block mb-1">Duracion (minutos)</label>
                    <InputText type="number" min="5" step="5" v-model.number="edit.duracion_minutos" class="w-full" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="modalEditarVisible = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardandoEdit" @click="guardarEdicion" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
:deep(.evento-rehab) {
    border-style: dashed !important;
    border-width: 2px !important;
}
</style>
