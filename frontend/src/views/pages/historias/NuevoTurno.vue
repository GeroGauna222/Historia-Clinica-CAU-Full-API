<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useUserStore } from '@/stores/user';
import DatePicker from 'primevue/datepicker';
import Button from 'primevue/button';
import ausenciasService from '@/service/ausenciasService';

const userStore = useUserStore();
const searchPaciente = ref('');
const pacientes = ref([]);
const pacienteId = ref('');
const pacienteSeleccionado = ref('');
const usuarioId = ref('');
const fecha = ref(null);
const motivo = ref('');
const mensaje = ref('');
const error = ref('');
const profesionales = ref([]);
const ausenciasProfesional = ref([]);

// Campos para tanda
const esTanda = ref(false);
const cantidad = ref(10);
const diasSemana = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado'];
const diasSeleccionados = ref([]);

onMounted(async () => {
    try {
        const resp = await fetch('/api/profesionales', { credentials: 'include' });
        if (!resp.ok) throw new Error('Error al cargar profesionales');
        profesionales.value = await resp.json();
    } catch (e) {
        console.error('Error cargando profesionales', e);
        error.value = 'No se pudieron cargar los profesionales';
    }
});

watch(usuarioId, async (nuevoProfesionalId) => {
    await cargarAusenciasProfesional(nuevoProfesionalId);

    if (fecha.value && estaFechaTotalmenteBloqueada(fecha.value)) {
        fecha.value = null;
        error.value = 'La fecha seleccionada esta bloqueada para ese profesional';
    }
});

async function cargarAusenciasProfesional(profesionalId) {
    if (!profesionalId) {
        ausenciasProfesional.value = [];
        return;
    }

    try {
        const resp = await ausenciasService.listar();
        const todas = resp.data || [];
        ausenciasProfesional.value = todas.filter((a) => Number(a.usuario_id) === Number(profesionalId));
    } catch (e) {
        console.error('Error cargando ausencias', e);
        ausenciasProfesional.value = [];
    }
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

const ausenciasNormalizadas = computed(() => {
    return (ausenciasProfesional.value || [])
        .map((a) => {
            const inicio = parseDateSafe(a.fecha_inicio);
            const fin = parseDateSafe(a.fecha_fin);
            if (!inicio || !fin) return null;

            return {
                ...a,
                inicio,
                fin,
                esDiaCompleto: esDiaCompletoAusencia(a, inicio, fin)
            };
        })
        .filter(Boolean);
});

const disabledDates = computed(() => {
    const resultado = [];
    const vistos = new Set();

    for (const a of ausenciasNormalizadas.value) {
        if (!a.esDiaCompleto) continue;

        const fechaDia = new Date(a.inicio);
        fechaDia.setHours(0, 0, 0, 0);

        const key = fechaDia.toDateString();
        if (!vistos.has(key)) {
            vistos.add(key);
            resultado.push(new Date(fechaDia));
        }
    }

    return resultado;
});

function estaFechaTotalmenteBloqueada(fechaSeleccionada) {
    const fechaDia = new Date(fechaSeleccionada);
    fechaDia.setHours(0, 0, 0, 0);

    return disabledDates.value.some((d) => d.getTime() === fechaDia.getTime());
}

function rangoSolapado(inicioA, finA, inicioB, finB) {
    return inicioA < finB && finA > inicioB;
}

function hayBloqueoEnRango(inicio, fin) {
    return ausenciasNormalizadas.value.some((a) => rangoSolapado(inicio, fin, a.inicio, a.fin));
}

async function buscarPacientes() {
    if (!searchPaciente.value || searchPaciente.value.length < 2) {
        pacientes.value = [];
        return;
    }
    try {
        const resp = await fetch(`/api/pacientes/buscar?q=${encodeURIComponent(searchPaciente.value)}`, {
            credentials: 'include'
        });
        if (!resp.ok) throw new Error('Error de busqueda');
        const data = await resp.json();
        pacientes.value = data.pacientes || [];
    } catch (e) {
        console.error('Error buscando pacientes', e);
    }
}

function seleccionarPaciente(p) {
    pacienteId.value = p.id;
    pacienteSeleccionado.value = `${p.apellido} ${p.nombre} (DNI: ${p.dni})`;
    searchPaciente.value = pacienteSeleccionado.value;
    pacientes.value = [];
}

function formatearFechaBackend(dateObj) {
    if (!dateObj) return null;

    const d = new Date(dateObj);
    const pad = (n) => String(n).padStart(2, '0');

    const year = d.getFullYear();
    const month = pad(d.getMonth() + 1);
    const day = pad(d.getDate());
    const hour = pad(d.getHours());
    const minute = pad(d.getMinutes());

    return `${year}-${month}-${day}T${hour}:${minute}`;
}

function calcularFin(fechaInicio, minutos) {
    if (!fechaInicio) return null;

    const d = new Date(fechaInicio);
    d.setMinutes(d.getMinutes() + minutos);

    return formatearFechaBackend(d);
}

async function crearTurno() {
    mensaje.value = '';
    error.value = '';

    if (!pacienteId.value) {
        error.value = 'Debe seleccionar un paciente';
        return;
    }

    if (!usuarioId.value) {
        error.value = 'Debe seleccionar un profesional';
        return;
    }

    if (!fecha.value) {
        error.value = 'Debe seleccionar fecha y hora';
        return;
    }

    if (estaFechaTotalmenteBloqueada(fecha.value)) {
        error.value = 'Ese dia esta bloqueado para el profesional seleccionado';
        return;
    }

    const endpoint = esTanda.value ? '/api/turnos/tanda' : '/api/turnos';
    const duracion = userStore.duracion_turno || 30;
    const fechaInicioDate = new Date(fecha.value);
    const fechaFinDate = new Date(fechaInicioDate);
    fechaFinDate.setMinutes(fechaFinDate.getMinutes() + duracion);

    if (!esTanda.value && hayBloqueoEnRango(fechaInicioDate, fechaFinDate)) {
        error.value = 'La fecha/hora elegida coincide con un bloqueo de agenda';
        return;
    }

    const fechaInicioStr = formatearFechaBackend(fechaInicioDate);
    const fechaFinStr = calcularFin(fechaInicioDate, duracion);

    const payload = {
        paciente_id: pacienteId.value,
        usuario_id: usuarioId.value,
        fecha_inicio: fechaInicioStr,
        fecha_fin: fechaFinStr,
        motivo: motivo.value
    };

    if (esTanda.value) {
        payload.cantidad = cantidad.value;
        payload.dias_semana = diasSeleccionados.value;
        payload.fecha = fechaInicioStr;
    }

    try {
        const resp = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload)
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.error || 'Error al crear turno');
        }

        const data = await resp.json();
        mensaje.value = data.message || 'Turno creado correctamente';

        pacienteId.value = '';
        usuarioId.value = '';
        fecha.value = null;
        motivo.value = '';
        searchPaciente.value = '';
        pacienteSeleccionado.value = '';
        esTanda.value = false;
        diasSeleccionados.value = [];
        ausenciasProfesional.value = [];
    } catch (e) {
        error.value = e.message;
    }
}
</script>

<template>
    <div class="flex justify-center items-start p-8">
        <div class="bg-white shadow-xl rounded-2xl p-8 w-full max-w-2xl">
            <h1 class="text-3xl font-bold text-center mb-8 text-gray-800 dark:text-white">Nuevo Turno</h1>

            <form @submit.prevent="crearTurno" class="space-y-6">
                <div class="relative">
                    <label class="block mb-2 font-semibold text-gray-700">Paciente</label>
                    <input v-model="searchPaciente" @input="buscarPacientes" type="text" placeholder="Buscar por DNI o nombre" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" autocomplete="off" />
                    <ul v-if="pacientes.length > 0" class="absolute z-20 left-0 right-0 border rounded-lg mt-2 bg-white shadow-md divide-y max-h-48 overflow-y-auto">
                        <li v-for="p in pacientes" :key="p.id" @click="seleccionarPaciente(p)" class="px-3 py-2 hover:bg-blue-100 cursor-pointer">{{ p.apellido }} {{ p.nombre }} (DNI: {{ p.dni }})</li>
                    </ul>
                    <p v-if="pacienteId" class="mt-2 text-sm text-green-600 font-medium">Seleccionado: {{ pacienteSeleccionado }}</p>
                </div>

                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Profesional</label>
                    <select v-model="usuarioId" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" required>
                        <option value="" disabled>Seleccione un profesional</option>
                        <option v-for="p in profesionales" :key="p.id" :value="p.id">{{ p.nombre }} ({{ p.especialidad || 'Sin especialidad' }})</option>
                    </select>
                </div>

                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Fecha y hora</label>
                    <DatePicker
                        v-model="fecha"
                        showTime
                        hourFormat="24"
                        :stepMinute="5"
                        iconDisplay="input"
                        :disabledDates="disabledDates"
                        placeholder="Seleccionar fecha y hora"
                        fluid
                        class="w-full"
                        inputClass="w-full p-3 border rounded-xl shadow-sm"
                        required
                    />
                    <small v-if="disabledDates.length > 0" class="text-gray-500">Hay dias completamente bloqueados para este profesional.</small>
                </div>

                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Motivo</label>
                    <textarea v-model="motivo" rows="3" placeholder="Motivo del turno" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500"></textarea>
                </div>

                <div class="mt-6 border-t pt-4">
                    <label class="flex items-center gap-2 text-gray-700 font-semibold cursor-pointer">
                        <input type="checkbox" v-model="esTanda" class="accent-blue-600 w-5 h-5" />
                        Crear tanda de turnos (kinesiologia, rehabilitacion, etc.)
                    </label>

                    <transition name="fade">
                        <div v-if="esTanda" class="mt-4 space-y-4 bg-blue-50 p-4 rounded-xl border border-blue-100">
                            <div>
                                <label class="block mb-2 font-semibold text-gray-700">Cantidad de turnos</label>
                                <input v-model.number="cantidad" type="number" min="1" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" placeholder="Ejemplo: 10" />
                            </div>

                            <div>
                                <label class="block mb-2 font-semibold text-gray-700">Dias de la semana</label>
                                <div class="grid grid-cols-3 gap-2">
                                    <label v-for="(dia, idx) in diasSemana" :key="idx" class="flex items-center space-x-2">
                                        <input type="checkbox" v-model="diasSeleccionados" :value="dia" class="accent-blue-600 w-5 h-5" />
                                        <span>{{ dia }}</span>
                                    </label>
                                </div>
                                <p class="text-gray-500 text-sm mt-1">Selecciona los dias en que se repetira el turno</p>
                            </div>
                        </div>
                    </transition>
                </div>

                <div class="flex justify-center">
                    <Button type="submit" label="Guardar Turno" class="w-full md:w-auto px-6 py-3 font-semibold shadow-lg" />
                </div>
            </form>

            <p v-if="mensaje" class="mt-6 text-green-600 font-semibold text-center">
                {{ mensaje }}
            </p>
            <p v-if="error" class="mt-6 text-red-600 font-semibold text-center">
                {{ error }}
            </p>
        </div>
    </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
    transition: all 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
    transform: translateY(-5px);
}
</style>
