<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';
import { useToast } from 'primevue/usetoast';

// Imports PrimeVue
import InputSwitch from 'primevue/inputswitch';
import Button from 'primevue/button';
import Avatar from 'primevue/avatar';
import Toast from 'primevue/toast';

const router = useRouter();
const userStore = useUserStore();
const toast = useToast();
const usuario = ref(userStore);

// Días con tildes para que se vea bonito en la pantalla
const diasSemana = ref([
    { nombre: 'Lunes', id: null, activo: false, hora_inicio: '09:00', hora_fin: '17:00' },
    { nombre: 'Martes', id: null, activo: false, hora_inicio: '09:00', hora_fin: '17:00' },
    { nombre: 'Miércoles', id: null, activo: false, hora_inicio: '09:00', hora_fin: '17:00' },
    { nombre: 'Jueves', id: null, activo: false, hora_inicio: '09:00', hora_fin: '17:00' },
    { nombre: 'Viernes', id: null, activo: false, hora_inicio: '09:00', hora_fin: '17:00' },
    { nombre: 'Sábado', id: null, activo: false, hora_inicio: '09:00', hora_fin: '13:00' },
    { nombre: 'Domingo', id: null, activo: false, hora_inicio: '09:00', hora_fin: '13:00' }
]);

const guardando = ref(false);

// 🛠️ Función para normalizar texto (Miércoles -> Miercoles)
const quitarTildes = (str) => {
    if (!str) return '';
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
};

// ░░ CARGA DE DISPONIBILIDADES ░░
// En Disponibilidad.vue

async function cargarDisponibilidades() {
    try {
        const url = `/disponibilidades?usuario_id=${userStore.id}`;

        const res = await api.get(url, { withCredentials: true });
        const datos = res.data;

        diasSemana.value.forEach((dia) => {
            const nombreLocalSinTilde = quitarTildes(dia.nombre);

            const encontrado = datos.find((d) => quitarTildes(d.dia_semana) === nombreLocalSinTilde);

            if (encontrado) {
                dia.id = encontrado.id;
                dia.activo = Boolean(encontrado.activo);
                dia.hora_inicio = encontrado.hora_inicio.slice(0, 5);
                dia.hora_fin = encontrado.hora_fin.slice(0, 5);
            }
        });
    } catch (err) {
        console.error(err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se cargaron los horarios', life: 3000 });
    }
}

// ░░ GUARDAR CAMBIOS (Corregido) ░░
async function guardarDisponibilidades() {
    guardando.value = true;

    try {
        const promesas = diasSemana.value.map(async (dia) => {
            if (dia.activo || dia.id) {
                const diaBackend = quitarTildes(dia.nombre);

                const payload = {
                    dia_semana: diaBackend, // ⭐ NECESARIO
                    hora_inicio: dia.hora_inicio,
                    hora_fin: dia.hora_fin,
                    activo: dia.activo
                };

                if (dia.id) {
                    // PUT → actualiza correctamente
                    await api.put(`/disponibilidades/${dia.id}`, payload, { withCredentials: true });
                } else if (dia.activo) {
                    // POST → ahora ya funciona
                    const res = await api.post('/disponibilidades', payload, { withCredentials: true });
                    dia.id = res.data.id;
                }
            }
        });

        await Promise.all(promesas);

        toast.add({ severity: 'success', summary: 'Guardado', detail: 'Horarios actualizados correctamente', life: 3000 });
    } catch (err) {
        console.error(err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Hubo un problema al guardar', life: 3000 });
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

        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-6 md:p-8 transition-colors border border-gray-100 dark:border-gray-800">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
                <div>
                    <h1 class="text-3xl font-bold text-gray-800 dark:text-white">Disponibilidad Horaria</h1>
                    <p class="text-gray-500 dark:text-gray-400 mt-1">Configurá los días y franjas horarias en las que atendés turnos.</p>
                </div>

                <div class="flex items-center gap-3 bg-primary-50 dark:bg-primary-900/20 px-4 py-2 rounded-xl border border-primary-100 dark:border-primary-800">
                    <Avatar :label="usuario?.nombre?.charAt(0)" shape="circle" class="bg-primary text-white" />
                    <span class="font-bold text-primary-700 dark:text-primary-300">{{ usuario?.nombre }}</span>
                </div>
            </div>

            <div class="space-y-4">
                <div class="hidden md:grid grid-cols-12 gap-4 px-4 text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">
                    <div class="col-span-3">Día</div>
                    <div class="col-span-2 text-center">Estado</div>
                    <div class="col-span-7 text-center">Horario de Atención</div>
                </div>

                <div
                    v-for="dia in diasSemana"
                    :key="dia.nombre"
                    class="group grid grid-cols-1 md:grid-cols-12 gap-4 items-center p-4 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all bg-surface-50 dark:bg-surface-800"
                    :class="{ 'opacity-60 grayscale': !dia.activo }"
                >
                    <div class="col-span-1 md:col-span-3 flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg transition-colors" :class="dia.activo ? 'bg-primary text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-500'">
                            {{ dia.nombre.charAt(0) }}
                        </div>
                        <span class="text-lg font-semibold text-gray-800 dark:text-gray-200 capitalize">
                            {{ dia.nombre }}
                        </span>
                    </div>

                    <div class="col-span-1 md:col-span-2 flex items-center md:justify-center justify-between">
                        <span class="md:hidden text-sm font-medium text-gray-500">¿Atiende este día?</span>
                        <InputSwitch v-model="dia.activo" />
                    </div>

                    <div class="col-span-1 md:col-span-7 flex flex-col md:flex-row items-center justify-center gap-3">
                        <div class="flex items-center gap-2 w-full md:w-auto">
                            <i class="pi pi-sun text-gray-400"></i>
                            <label class="md:hidden text-sm text-gray-500 w-16">Desde:</label>
                            <input type="time" v-model="dia.hora_inicio" :disabled="!dia.activo" class="p-inputtext p-component w-full md:w-32 text-center" />
                        </div>

                        <span class="hidden md:block text-gray-400">—</span>

                        <div class="flex items-center gap-2 w-full md:w-auto">
                            <i class="pi pi-moon text-gray-400"></i>
                            <label class="md:hidden text-sm text-gray-500 w-16">Hasta:</label>
                            <input type="time" v-model="dia.hora_fin" :disabled="!dia.activo" class="p-inputtext p-component w-full md:w-32 text-center" />
                        </div>
                    </div>
                </div>
            </div>

            <div class="flex justify-end items-center gap-4 mt-8 pt-6 border-t border-gray-100 dark:border-gray-800">
                <Button label="Cancelar" icon="pi pi-times" text severity="secondary" @click="irAlDashboard" />
                <Button label="Guardar Cambios" icon="pi pi-check" :loading="guardando" @click="guardarDisponibilidades" />
            </div>
        </div>
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
