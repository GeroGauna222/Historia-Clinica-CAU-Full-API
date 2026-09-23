<script setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';
import { useToast } from 'primevue/usetoast';

// Imports PrimeVue
import InputSwitch from 'primevue/inputswitch';
import Button from 'primevue/button';
import Avatar from 'primevue/avatar';
import Toast from 'primevue/toast';
import Dialog from 'primevue/dialog';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const toast = useToast();

const usuarioId = ref(userStore.id);
const nombreUsuario = ref(userStore.nombre);

// Permitir que directores/administrativos editen horarios de terceros
if (['director', 'administrativo'].includes(userStore.rol) && route.query.usuario_id) {
    usuarioId.value = Number(route.query.usuario_id);
    nombreUsuario.value = route.query.nombre_usuario || 'Profesional';
}

const diasSemana = ref([
    { nombre: 'Lunes', activo: false, rangos: [] },
    { nombre: 'Martes', activo: false, rangos: [] },
    { nombre: 'Miércoles', activo: false, rangos: [] },
    { nombre: 'Jueves', activo: false, rangos: [] },
    { nombre: 'Viernes', activo: false, rangos: [] },
    { nombre: 'Sábado', activo: false, rangos: [] },
    { nombre: 'Domingo', activo: false, rangos: [] }
]);

const idsEliminados = ref([]);
const guardando = ref(false);
const turnosAfectados = ref([]);
const mostrarAdvertenciaTurnos = ref(false);

// 🛠️ Función para normalizar texto (Miércoles -> Miercoles)
const quitarTildes = (str) => {
    if (!str) return '';
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
};

// ░░ CARGA DE DISPONIBILIDADES ░░
async function cargarDisponibilidades() {
    try {
        const url = `/disponibilidades?usuario_id=${usuarioId.value}`;
        const res = await api.get(url, { withCredentials: true });
        const datos = res.data;

        // Reset
        diasSemana.value.forEach((d) => {
            d.activo = false;
            d.rangos = [];
        });

        // Group by day of week
        datos.forEach((d) => {
            const nombreLocalSinTilde = quitarTildes(d.dia_semana);
            const diaMatch = diasSemana.value.find((dia) => quitarTildes(dia.nombre) === nombreLocalSinTilde);
            if (diaMatch) {
                diaMatch.activo = diaMatch.activo || Boolean(d.activo);
                diaMatch.rangos.push({
                    id: d.id,
                    hora_inicio: d.hora_inicio.slice(0, 5),
                    hora_fin: d.hora_fin.slice(0, 5),
                    activo: Boolean(d.activo)
                });
            }
        });

        // Asegurar que cada día tenga al menos un rango slot por defecto
        diasSemana.value.forEach((dia) => {
            if (dia.rangos.length === 0) {
                dia.rangos.push({
                    id: null,
                    hora_inicio: '09:00',
                    hora_fin: '17:00',
                    activo: true
                });
            }
        });
    } catch (err) {
        console.error(err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se cargaron los horarios', life: 3000 });
    }
}

function onDiaSwitchChange(dia) {
    dia.rangos.forEach((r) => {
        r.activo = dia.activo;
    });
}

function agregarRango(dia) {
    if (!dia.activo) {
        dia.activo = true;
    }
    dia.rangos.push({
        id: null,
        hora_inicio: '09:00',
        hora_fin: '17:00',
        activo: true
    });
}

function eliminarRango(dia, index) {
    const rango = dia.rangos[index];
    if (rango.id) {
        idsEliminados.value.push(rango.id);
    }
    dia.rangos.splice(index, 1);

    if (dia.rangos.length === 0) {
        dia.activo = false;
        dia.rangos.push({
            id: null,
            hora_inicio: '09:00',
            hora_fin: '17:00',
            activo: false
        });
    }
}

// Validar solapamientos en el frontend
function verificarSolapamientos() {
    for (const dia of diasSemana.value) {
        if (!dia.activo) continue;
        const activos = dia.rangos.filter((r) => r.activo);
        for (let i = 0; i < activos.length; i++) {
            const r1_ini = activos[i].hora_inicio;
            const r1_fin = activos[i].hora_fin;
            if (!r1_ini || !r1_fin) {
                return `Debe completar todos los horarios para el ${dia.nombre}.`;
            }
            if (r1_ini >= r1_fin) {
                return `El horario de inicio (${r1_ini}) debe ser menor al de fin (${r1_fin}) para el ${dia.nombre}.`;
            }
            for (let j = i + 1; j < activos.length; j++) {
                const r2_ini = activos[j].hora_inicio;
                const r2_fin = activos[j].hora_fin;
                if (r1_ini < r2_fin && r2_ini < r1_fin) {
                    return `Hay franjas horarias solapadas el ${dia.nombre} (${r1_ini}-${r1_fin} y ${r2_ini}-${r2_fin}).`;
                }
            }
        }
    }
    return null;
}

// ░░ GUARDAR CAMBIOS ░░
async function guardarDisponibilidades() {
    const errorSolapamiento = verificarSolapamientos();
    if (errorSolapamiento) {
        toast.add({ severity: 'error', summary: 'Error de Validación', detail: errorSolapamiento, life: 5000 });
        return;
    }

    guardando.value = true;

    // Generar payload propuesto
    const propuestas = [];
    diasSemana.value.forEach((dia) => {
        dia.rangos.forEach((r) => {
            propuestas.push({
                dia_semana: quitarTildes(dia.nombre),
                hora_inicio: r.hora_inicio,
                hora_fin: r.hora_fin,
                activo: dia.activo && r.activo
            });
        });
    });

    try {
        // Validar contra turnos futuros
        const resVal = await api.post(
            '/disponibilidades/validar',
            {
                usuario_id: usuarioId.value,
                disponibilidades: propuestas
            },
            { withCredentials: true }
        );

        if (resVal.data && resVal.data.length > 0) {
            turnosAfectados.value = resVal.data;
            mostrarAdvertenciaTurnos.value = true;
            guardando.value = false;
            return;
        }

        // Si no hay turnos huérfanos, guardamos de una
        await ejecutarGuardado();
    } catch (err) {
        console.error(err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Hubo un problema al validar los horarios', life: 3000 });
        guardando.value = false;
    }
}

async function ejecutarGuardado() {
    guardando.value = true;
    mostrarAdvertenciaTurnos.value = false;
    try {
        // 1. Eliminar franjas quitadas
        const deletePromesas = idsEliminados.value.map((id) => api.delete(`/disponibilidades/${id}`, { withCredentials: true }));
        await Promise.all(deletePromesas);
        idsEliminados.value = [];

        // 2. Guardar franjas restantes
        const savePromesas = [];
        diasSemana.value.forEach((dia) => {
            dia.rangos.forEach((r) => {
                const payload = {
                    usuario_id: usuarioId.value,
                    dia_semana: quitarTildes(dia.nombre),
                    hora_inicio: r.hora_inicio,
                    hora_fin: r.hora_fin,
                    activo: dia.activo && r.activo
                };

                if (r.id) {
                    savePromesas.push(api.put(`/disponibilidades/${r.id}`, payload, { withCredentials: true }));
                } else if (dia.activo && r.activo) {
                    savePromesas.push(api.post('/disponibilidades', payload, { withCredentials: true }));
                }
            });
        });

        await Promise.all(savePromesas);
        toast.add({ severity: 'success', summary: 'Guardado', detail: 'Horarios actualizados correctamente', life: 3000 });
        await cargarDisponibilidades();
    } catch (err) {
        console.error(err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Hubo un problema al guardar los horarios', life: 3000 });
    } finally {
        guardando.value = false;
    }
}

const irAlDashboard = () => router.push({ name: 'dashboard' });

onMounted(cargarDisponibilidades);
</script>

<template>
    <div class="p-6 md:p-8 w-full max-w-5xl mx-auto">
        <Toast />

        <div class="bg-card shadow-xl rounded-2xl p-6 md:p-8 transition-colors border border-surface">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
                <div>
                    <h1 class="text-3xl font-bold text-color">Disponibilidad Horaria</h1>
                    <p class="text-muted-color mt-1">Configurá los días y franjas horarias en las que atendés turnos.</p>
                </div>

                <div class="flex items-center gap-3 bg-highlight px-4 py-2 rounded-xl border border-surface">
                    <Avatar :label="nombreUsuario?.charAt(0)" shape="circle" class="bg-primary text-white" />
                    <span class="font-bold text-primary">{{ nombreUsuario }}</span>
                </div>
            </div>

            <div class="space-y-4">
                <div class="hidden md:grid grid-cols-12 gap-4 px-4 text-sm font-bold text-muted-color uppercase tracking-wider mb-2">
                    <div class="col-span-3">Día</div>
                    <div class="col-span-2 text-center">Estado</div>
                    <div class="col-span-7 text-center">Franjas Horarias de Atención</div>
                </div>

                <div
                    v-for="dia in diasSemana"
                    :key="dia.nombre"
                    class="group grid grid-cols-1 md:grid-cols-12 gap-4 items-start p-4 rounded-xl border border-surface hover:border-primary hover:shadow-md transition-all bg-subtle"
                    :class="{ 'opacity-60 grayscale': !dia.activo }"
                >
                    <!-- Día -->
                    <div class="col-span-1 md:col-span-3 flex items-center gap-3 py-1">
                        <div class="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg transition-colors" :class="dia.activo ? 'bg-primary text-primary-contrast' : 'bg-emphasis text-muted-color'">
                            {{ dia.nombre.charAt(0) }}
                        </div>
                        <span class="text-lg font-semibold text-color capitalize">
                            {{ dia.nombre }}
                        </span>
                    </div>

                    <!-- Toggle Activo -->
                    <div class="col-span-1 md:col-span-2 flex items-center md:justify-center justify-between py-1">
                        <span class="md:hidden text-sm font-medium text-muted-color">¿Atiende este día?</span>
                        <InputSwitch v-model="dia.activo" @change="onDiaSwitchChange(dia)" />
                    </div>

                    <!-- Franjas horarias -->
                    <div class="col-span-1 md:col-span-7 flex flex-col gap-3">
                        <div v-for="(rango, rIdx) in dia.rangos" :key="rIdx" class="flex flex-col md:flex-row items-center gap-3 w-full" :class="{ 'opacity-50': !dia.activo || !rango.activo }">
                            <div class="flex items-center gap-2 w-full md:w-auto">
                                <i class="pi pi-sun text-muted-color"></i>
                                <label class="md:hidden text-sm text-muted-color w-16">Desde:</label>
                                <input type="time" v-model="rango.hora_inicio" :disabled="!dia.activo || !rango.activo" class="p-inputtext p-component w-full md:w-32 text-center" />
                            </div>

                            <span class="hidden md:block text-muted-color">—</span>

                            <div class="flex items-center gap-2 w-full md:w-auto">
                                <i class="pi pi-moon text-muted-color"></i>
                                <label class="md:hidden text-sm text-muted-color w-16">Hasta:</label>
                                <input type="time" v-model="rango.hora_fin" :disabled="!dia.activo || !rango.activo" class="p-inputtext p-component w-full md:w-32 text-center" />
                            </div>

                            <!-- Botón Eliminar Franja -->
                            <div class="flex items-center gap-2">
                                <Button icon="pi pi-trash" severity="danger" text rounded @click="eliminarRango(dia, rIdx)" title="Eliminar Franja" class="p-button-sm" :disabled="!dia.activo" />
                            </div>
                        </div>

                        <!-- Botón Agregar Franja -->
                        <div class="flex justify-start items-center">
                            <button type="button" @click="agregarRango(dia)" class="flex items-center gap-1.5 text-sm font-semibold text-primary hover:text-primary-emphasis transition-colors focus:outline-none cursor-pointer mt-1">
                                <i class="pi pi-plus text-xs"></i>
                                Agregar Franja Horaria
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Botones -->
            <div class="flex justify-end items-center gap-4 mt-8 pt-6 border-t border-surface">
                <Button label="Cancelar" icon="pi pi-times" text severity="secondary" @click="irAlDashboard" />
                <Button label="Guardar Cambios" icon="pi pi-check" :loading="guardando" @click="guardarDisponibilidades" />
            </div>
        </div>

        <!-- Diálogo de Advertencia por Turnos Huérfanos -->
        <Dialog v-model:visible="mostrarAdvertenciaTurnos" modal header="⚠️ Turnos Fuera de Rango Horario" :style="{ width: '50rem' }" :breakpoints="{ '1199px': '75vw', '575px': '90vw' }">
            <div class="p-fluid">
                <p class="text-status-sin-aviso-fg font-semibold mb-4 text-base">Informar a administración sobre los turnos futuros que quedan fuera del nuevo rango horario:</p>
                <div class="max-h-72 overflow-y-auto border border-surface rounded-xl mb-4">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-subtle text-muted-color font-semibold text-sm border-b border-surface">
                                <th class="p-3">Fecha y Hora</th>
                                <th class="p-3">Paciente</th>
                                <th class="p-3">Motivo</th>
                            </tr>
                        </thead>
                        <tbody class="text-sm">
                            <tr v-for="t in turnosAfectados" :key="t.id" class="border-b border-surface text-color hover:bg-emphasis transition-colors">
                                <td class="p-3 font-medium">{{ t.fecha }} hs</td>
                                <td class="p-3 font-semibold">{{ t.paciente }}</td>
                                <td class="p-3 text-muted-color">{{ t.motivo }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <p class="text-sm text-muted-color mb-6">¿Desea confirmar el cambio de disponibilidad y conservar estos turnos como excepciones fuera de horario?</p>
            </div>
            <template #footer>
                <Button label="Cancelar y Corregir" icon="pi pi-times" class="p-button-text" severity="secondary" @click="mostrarAdvertenciaTurnos = false" />
                <Button label="Confirmar y Guardar" icon="pi pi-check" severity="danger" :loading="guardando" @click="ejecutarGuardado" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
/* Ajuste para que el input time nativo se vea como PrimeVue */
input[type='time'] {
    font-family: inherit;
    cursor: pointer;
}
.p-inputtext {
    transition:
        background-color 0.2s,
        color 0.2s,
        border-color 0.2s,
        box-shadow 0.2s;
}
</style>
