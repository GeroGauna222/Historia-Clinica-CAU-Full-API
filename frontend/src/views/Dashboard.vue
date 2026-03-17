<script setup>
import { ref, onMounted, computed, reactive, watch } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';
import { horaExacta, fechaRangoBonito } from '@/utils/formatDate';

// Imports PrimeVue
import Chart from 'primevue/chart';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Accordion from 'primevue/accordion';
import AccordionTab from 'primevue/accordiontab';
import Tag from 'primevue/tag';
import Avatar from 'primevue/avatar';

// ===============================
//  Configuración
// ===============================
const router = useRouter();
const user = useUserStore();
const esDirector = computed(() => user.rol?.toLowerCase().trim() === 'director');

// ===============================
//  Saludo Dinámico 🌤️
// ===============================
const saludo = computed(() => {
    const hora = new Date().getHours();
    if (hora < 12) return 'Buenos días';
    if (hora < 19) return 'Buenas tardes';
    return 'Buenas noches';
});

// ===============================
//  Variables reactivas
// ===============================
const loading = ref(true);
const error = ref(null);
const dashboard = ref(null);
const disponibilidades = ref([]);
const profesionalesAgrupados = reactive([]);

// Gráficos
const chartData = ref(null);
const chartOptions = ref(null);

// ===============================
//  Acciones
// ===============================
const atenderPaciente = (turno) => {
    if (turno.paciente_id) {
        router.push({ name: 'historiaPaciente', params: { id: turno.paciente_id } });
    } else {
        console.warn('El turno no tiene ID de paciente asociado.');
    }
};

// ===============================
//  Cargar Datos
// ===============================
const fetchDashboard = async () => {
    try {
        loading.value = true;

        const [resDashboard, resSemanal, resDisponibilidad] = await Promise.all([api.get('/dashboard', { withCredentials: true }), api.get('/dashboard/semanal', { withCredentials: true }), api.get('/disponibilidades', { withCredentials: true })]);

        dashboard.value = resDashboard.data;
        disponibilidades.value = resDisponibilidad.data;

        // --- Configurar Gráfico ---
        const { labels, turnos } = resSemanal.data;
        // Usamos el color primary de tu tema o un verde/azul estándar
        const colores = turnos.map((v) => (v > 5 ? '#10B981' : '#3B82F6'));

        chartData.value = {
            labels,
            datasets: [
                {
                    label: 'Turnos',
                    data: turnos,
                    backgroundColor: colores,
                    borderRadius: 6,
                    barThickness: 20
                }
            ]
        };

        chartOptions.value = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: false }
            },
            scales: {
                x: {
                    ticks: { color: '#9CA3AF', font: { size: 11 } },
                    grid: { display: false }
                },
                y: {
                    ticks: { stepSize: 1, color: '#9CA3AF' },
                    beginAtZero: true,
                    grid: { color: '#F3F4F6' },
                    border: { display: false }
                }
            },
            layout: { padding: 0 }
        };
    } catch (err) {
        console.error('Error dashboard:', err);
        error.value = 'No se pudo cargar el panel de control.';
    } finally {
        loading.value = false;
    }
};

// --- Agrupar Disponibilidades (Solo Director) ---
watch(
    disponibilidades,
    (nuevas) => {
        profesionalesAgrupados.length = 0;
        const mapa = {};
        for (const d of nuevas) {
            if (!mapa[d.profesional]) {
                mapa[d.profesional] = { nombre: d.profesional, disponibilidades: [] };
            }
            mapa[d.profesional].disponibilidades.push(d);
        }
        for (const key in mapa) profesionalesAgrupados.push(mapa[key]);
    },
    { immediate: true }
);

onMounted(fetchDashboard);
</script>

<template>
    <div class="p-6 md:p-8 w-full transition-colors">
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                <span v-if="user.nombre">{{ saludo }}, {{ user.nombre.split(' ')[0] }}</span>
                <span v-else>Panel de Control</span>
                <span class="text-3xl">👋</span>
            </h1>
            <p class="text-gray-500 dark:text-gray-400 text-base mt-1">Este es el resumen de tu actividad para hoy.</p>
        </div>

        <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-gray-400">
            <i class="pi pi-spin pi-spinner text-4xl mb-3"></i>
            <p>Cargando información...</p>
        </div>

        <div v-else-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl flex items-center gap-3">
            <i class="pi pi-exclamation-triangle text-xl"></i>
            <span>{{ error }}</span>
        </div>

        <div v-else class="grid grid-cols-12 gap-6">
            <div class="col-span-12 sm:col-span-6 xl:col-span-3 transition-transform hover:-translate-y-1 duration-300" v-for="(value, key) in dashboard.estadisticas" :key="key">
                <div class="bg-surface-0 dark:bg-surface-900 shadow-lg rounded-2xl p-5 h-full flex flex-col justify-between relative overflow-hidden group">
                    <div class="absolute right-[-10px] top-[-10px] bg-blue-50 dark:bg-blue-900/10 w-24 h-24 rounded-full transition-transform group-hover:scale-110"></div>

                    <div class="relative z-10 flex justify-between items-start">
                        <div>
                            <span class="block text-gray-500 dark:text-gray-400 capitalize text-sm font-medium mb-1">
                                {{ key.replace('_', ' ') }}
                            </span>
                            <div class="text-4xl font-bold text-gray-800 dark:text-white">{{ value }}</div>
                        </div>

                        <div class="bg-surface-0 dark:bg-surface-800 p-2 rounded-xl shadow-sm">
                            <i class="pi pi-chart-bar text-blue-500 text-xl"></i>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-6">
                <div class="bg-surface-0 dark:bg-surface-900 shadow-lg rounded-2xl p-6 h-full flex flex-col">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white flex items-center gap-2"><i class="pi pi-calendar text-blue-500"></i> Turnos de Hoy</h2>
                        <Tag :value="dashboard.turnos.length + ' pendientes'" severity="info" rounded></Tag>
                    </div>

                    <div v-if="dashboard.turnos.length === 0" class="flex flex-col items-center justify-center py-10 text-gray-400 flex-1">
                        <i class="pi pi-calendar-times text-4xl mb-2 opacity-50"></i>
                        <p>No hay turnos programados.</p>
                    </div>

                    <div v-else class="overflow-x-auto">
                        <DataTable
                            :value="dashboard.turnos"
                            paginator
                            :rows="3"
                            class="p-datatable-sm"
                            responsiveLayout="scroll"
                            :pt="{
                                headerRow: { class: 'text-sm text-gray-600' },
                                bodyRow: { class: 'text-sm' }
                            }"
                        >
                            <Column field="fecha_inicio" header="Hora">
                                <template #body="slotProps">
                                    <span class="font-bold text-gray-700 dark:text-gray-200">
                                        {{ horaExacta(slotProps.data.fecha_inicio) }}
                                    </span>
                                </template>
                            </Column>

                            <Column field="paciente" header="Paciente" class="font-medium text-gray-600 dark:text-gray-300"></Column>
                            <Column field="motivo" header="Motivo" class="hidden sm:table-cell text-gray-500"></Column>

                            <Column header="Acción" headerClass="text-right" bodyClass="text-right">
                                <template #body="slotProps">
                                    <Button icon="pi pi-play" rounded outlined size="small" severity="success" v-tooltip.top="'Atender ahora'" @click="atenderPaciente(slotProps.data)" />
                                </template>
                            </Column>
                        </DataTable>
                    </div>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-6">
                <div class="bg-surface-0 dark:bg-surface-900 shadow-lg rounded-2xl p-6 h-full flex flex-col">
                    <h2 class="text-xl font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2"><i class="pi pi-clock text-blue-500"></i> Próximo Turno</h2>

                    <div v-if="dashboard.proximo_turno" class="flex-1 flex flex-col justify-center">
                        <div class="p-6 bg-surface-50 dark:bg-surface-800 rounded-2xl border border-surface-200 dark:border-surface-700">
                            <div class="flex items-start gap-4">
                                <Avatar :label="dashboard.proximo_turno.paciente.charAt(0)" size="large" shape="circle" class="bg-blue-500 text-white" />
                                <div>
                                    <h3 class="text-lg font-bold text-gray-800 dark:text-white">{{ dashboard.proximo_turno.paciente }} {{ dashboard.proximo_turno.apellido }}</h3>
                                    <div class="mt-1 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 font-medium">
                                        <i class="pi pi-calendar"></i>
                                        {{ fechaRangoBonito(dashboard.proximo_turno.fecha_inicio, dashboard.proximo_turno.fecha_fin) }}
                                    </div>
                                </div>
                            </div>

                            <div class="mt-5 pt-4 border-t border-gray-200 dark:border-gray-600">
                                <p class="text-xs text-gray-400 uppercase font-bold tracking-wider mb-1">Motivo de consulta</p>
                                <p class="text-gray-700 dark:text-gray-300 italic">"{{ dashboard.proximo_turno.motivo }}"</p>
                            </div>

                            <div class="mt-6 flex justify-end">
                                <Button label="Iniciar Consulta" icon="pi pi-arrow-right" iconPos="right" rounded @click="atenderPaciente(dashboard.proximo_turno)" />
                            </div>
                        </div>
                    </div>

                    <div v-else class="flex flex-col items-center justify-center py-10 text-gray-400 flex-1">
                        <i class="pi pi-check-circle text-4xl mb-2 opacity-50"></i>
                        <p>Todo al día. No hay próximos turnos.</p>
                    </div>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-8">
                <div class="bg-surface-0 dark:bg-surface-900 shadow-lg rounded-2xl p-6 h-full border-l-4 border-blue-500">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white">Estadística Semanal</h2>
                        <small class="text-gray-400">Últimos 7 días</small>
                    </div>
                    <div class="h-[250px] w-full relative">
                        <Chart type="bar" :data="chartData" :options="chartOptions" class="h-full w-full" />
                    </div>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-4">
                <div class="bg-surface-0 dark:bg-surface-900 shadow-lg rounded-2xl p-6 h-full flex flex-col max-h-[380px]">
                    <h2 class="text-xl font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2"><i class="pi pi-briefcase text-blue-500"></i> Disponibilidad</h2>

                    <div class="overflow-y-auto pr-2 custom-scrollbar flex-1">
                        <template v-if="esDirector">
                            <Accordion :multiple="true" class="w-full shadow-none">
                                <AccordionTab v-for="(prof, index) in profesionalesAgrupados" :key="index" :header="prof.nombre">
                                    <ul class="space-y-2">
                                        <li v-for="(d, i) in prof.disponibilidades" :key="i" class="flex justify-between text-sm border-b dark:border-gray-700 pb-1 last:border-0">
                                            <span class="text-gray-600 dark:text-gray-400">{{ d.dia_semana }}</span>
                                            <span :class="d.activo ? 'text-green-600 font-bold' : 'text-red-400'">
                                                {{ d.activo ? 'Activo' : 'Inactivo' }}
                                            </span>
                                        </li>
                                    </ul>
                                </AccordionTab>
                            </Accordion>
                            <p v-if="profesionalesAgrupados.length === 0" class="text-gray-500 text-sm mt-2">Sin datos.</p>
                        </template>

                        <template v-else>
                            <ul v-if="disponibilidades.length > 0" class="space-y-3">
                                <li v-for="(d, i) in disponibilidades" :key="i" class="flex justify-between items-center p-3 bg-surface-50 dark:bg-surface-800 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors">
                                    <div class="flex items-center gap-3">
                                        <div class="w-2 h-2 rounded-full" :class="d.activo ? 'bg-green-500' : 'bg-red-500'"></div>
                                        <span class="font-medium text-gray-700 dark:text-gray-200">{{ d.dia_semana }}</span>
                                    </div>

                                    <div class="flex items-center gap-3">
                                        <span v-if="d.activo" class="text-sm text-gray-500 dark:text-gray-400 font-mono"> {{ d.hora_inicio }} - {{ d.hora_fin }} </span>
                                    </div>
                                </li>
                            </ul>
                            <p v-else class="text-gray-500 text-sm text-center py-4">No has cargado horarios.</p>

                            <div class="mt-4 text-center">
                                <Button label="Editar Horarios" link size="small" @click="$router.push('/disponibilidad')" />
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* Scrollbar fino y elegante */
.custom-scrollbar::-webkit-scrollbar {
    width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: #e5e7eb;
    border-radius: 10px;
}
.dark .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: #4b5563;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background-color: #d1d5db;
}
</style>
