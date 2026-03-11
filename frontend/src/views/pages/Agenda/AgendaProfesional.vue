<script setup>
import { ref, onMounted } from 'vue';
import turnosService from '@/service/turnosService';
import ausenciasService from '@/service/ausenciasService';
import { useToast } from 'primevue/usetoast';

// Imports PrimeVue
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import DatePicker from 'primevue/datepicker';
import Toast from 'primevue/toast';
import Tag from 'primevue/tag';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';

const toast = useToast();

const turnos = ref([]);
const ausencias = ref([]);
const fechaAusencia = ref(null);
const loading = ref(true);

// Cargar datos
const cargarDatos = async () => {
    loading.value = true;
    try {
        const [resTurnos, resAusencias] = await Promise.all([turnosService.listar(), ausenciasService.listar()]);
        turnos.value = resTurnos.data;
        ausencias.value = resAusencias.data;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo cargar la agenda', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// Agregar ausencia
const agregarAusencia = async () => {
    if (!fechaAusencia.value) return;

    try {
        // Ajuste de fecha para enviar string (YYYY-MM-DD)
        const fechaStr = fechaAusencia.value.toISOString().split('T')[0];

        await ausenciasService.crear({ fecha: fechaStr });
        toast.add({ severity: 'success', summary: 'Bloqueado', detail: 'Día bloqueado correctamente ✅', life: 3000 });
        fechaAusencia.value = null;
        await cargarDatos();
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo bloquear el día', life: 3000 });
    }
};

// Eliminar ausencia
const eliminarAusencia = async (id) => {
    try {
        await ausenciasService.eliminar(id);
        toast.add({ severity: 'info', summary: 'Eliminado', detail: 'Ausencia eliminada', life: 3000 });
        await cargarDatos();
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar', life: 3000 });
    }
};

// Formateadores
const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const formatDateTime = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
};

onMounted(() => {
    cargarDatos();
});
</script>

<template>
    <div class="p-6 md:p-8 w-full h-full">
        <Toast />

        <div class="bg-white dark:bg-[#1e1e1e] shadow-xl rounded-2xl p-6 transition-colors min-h-[500px]">
            <div class="mb-6">
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white flex items-center gap-2"><i class="pi pi-calendar text-primary"></i> Agenda General</h1>
                <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Visualizá los turnos programados y gestioná los días no laborables.</p>
            </div>

            <TabView>
                <TabPanel header="Turnos">
                    <div class="overflow-x-auto mt-2">
                        <DataTable :value="turnos" :loading="loading" paginator :rows="10" stripedRows class="p-datatable-sm" tableStyle="min-width: 50rem">
                            <template #empty>
                                <div class="text-center p-6 text-gray-500">No hay turnos registrados.</div>
                            </template>

                            <Column field="start" header="Fecha y Hora" sortable>
                                <template #body="slotProps">
                                    <span class="font-bold text-gray-700 dark:text-gray-200">
                                        {{ formatDateTime(slotProps.data.start) }}
                                    </span>
                                </template>
                            </Column>

                            <Column field="paciente" header="Paciente" sortable></Column>
                            <Column field="dni" header="DNI"></Column>

                            <Column field="profesional" header="Profesional" sortable>
                                <template #body="slotProps">
                                    <Tag severity="info" :value="slotProps.data.profesional" rounded />
                                </template>
                            </Column>

                            <Column field="description" header="Motivo"></Column>
                        </DataTable>
                    </div>
                </TabPanel>

                <TabPanel header="Bloqueos de Agenda">
                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-4">
                        <div class="lg:col-span-1 bg-gray-50 dark:bg-[#252525] p-6 rounded-xl border border-gray-100 dark:border-gray-700 h-fit">
                            <h3 class="text-lg font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2"><i class="pi pi-ban text-red-500"></i> Bloquear Día</h3>

                            <div class="flex flex-col gap-4">
                                <div class="flex flex-col gap-2">
                                    <label class="text-sm font-semibold text-gray-600 dark:text-gray-300">Seleccionar fecha</label>
                                    <DatePicker v-model="fechaAusencia" showIcon dateFormat="dd/mm/yy" placeholder="Elegir día..." class="w-full" />
                                </div>

                                <Button label="Bloquear Agenda" icon="pi pi-lock" severity="danger" @click="agregarAusencia" :disabled="!fechaAusencia" class="w-full" />
                                <small class="text-gray-500 text-xs"> * Al bloquear un día, no se podrán asignar nuevos turnos en esa fecha. </small>
                            </div>
                        </div>

                        <div class="lg:col-span-2">
                            <h3 class="text-lg font-bold text-gray-800 dark:text-white mb-4">Días Bloqueados</h3>

                            <div class="overflow-x-auto">
                                <DataTable :value="ausencias" :loading="loading" paginator :rows="5" class="p-datatable-sm">
                                    <template #empty>
                                        <div class="text-center p-4 text-gray-500">No hay días bloqueados.</div>
                                    </template>

                                    <Column field="fecha" header="Fecha Bloqueada" sortable>
                                        <template #body="slotProps">
                                            <span class="font-mono font-medium text-red-600 dark:text-red-400">
                                                {{ formatDate(slotProps.data.fecha) }}
                                            </span>
                                        </template>
                                    </Column>

                                    <Column header="Acciones" style="width: 8rem; text-align: right">
                                        <template #body="slotProps">
                                            <div class="flex justify-end">
                                                <Button icon="pi pi-trash" text rounded severity="secondary" @click="eliminarAusencia(slotProps.data.id)" v-tooltip.top="'Desbloquear día'" />
                                            </div>
                                        </template>
                                    </Column>
                                </DataTable>
                            </div>
                        </div>
                    </div>
                </TabPanel>
            </TabView>
        </div>
    </div>
</template>
