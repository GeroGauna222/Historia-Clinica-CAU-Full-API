<script setup>
import pacienteService from '@/service/pacienteService';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';

import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import IconField from 'primevue/iconfield';
import InputIcon from 'primevue/inputicon';

const toast = useToast();
const pacientes = ref([]);
const busqueda = ref('');
const router = useRouter();

const pacienteAEliminar = ref(null);
const mostrarDialog = ref(false);

const fetchPacientes = async () => {
    try {
        const res = await pacienteService.getPacientes();
        pacientes.value = res.data;
    } catch (err) {
        console.error(err);
    }
};

onMounted(() => {
    fetchPacientes();
});

const filtrados = computed(() => {
    if (!busqueda.value) return pacientes.value;
    const q = busqueda.value.toLowerCase();
    return pacientes.value.filter((p) => p.nombre.toLowerCase().includes(q) || p.apellido.toLowerCase().includes(q) || p.dni.includes(q));
});

const editarPaciente = (id) => {
    router.push(`/pacientes/${id}/editar`);
};

const confirmarEliminar = (paciente) => {
    pacienteAEliminar.value = paciente;
    mostrarDialog.value = true;
};

const cancelarEliminar = () => {
    pacienteAEliminar.value = null;
    mostrarDialog.value = false;
};

const eliminarPacienteConfirmado = async () => {
    if (!pacienteAEliminar.value) return;
    try {
        await pacienteService.deletePaciente(pacienteAEliminar.value.id);
        pacientes.value = pacientes.value.filter((p) => p.id !== pacienteAEliminar.value.id);
        mostrarDialog.value = false;
        pacienteAEliminar.value = null;
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar el paciente. Puede tener historias clínicas asociadas.', life: 5000 });
    }
};

const formatFecha = (fecha) => {
    if (!fecha) return '-';
    const d = new Date(fecha);
    return new Intl.DateTimeFormat('es-AR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(d);
};
</script>

<template>
    <div class="p-6 md:p-8 w-full h-full">
        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-6 transition-colors">
            <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white">Listado de Pacientes</h1>

                <div class="flex gap-2 w-full md:w-auto">
                    <IconField iconPosition="left" class="w-full md:w-64">
                        <InputIcon class="pi pi-search" />
                        <InputText v-model="busqueda" placeholder="Buscar paciente..." class="w-full" />
                    </IconField>

                    <Button icon="pi pi-user-plus" label="Nuevo" @click="router.push('/pacientes/registrar')" />
                </div>
            </div>

            <div class="overflow-x-auto">
                <DataTable :value="filtrados" paginator :rows="10" :rowsPerPageOptions="[5, 10, 20]" tableStyle="min-width: 60rem" stripedRows class="p-datatable-sm">
                    <template #empty>
                        <div class="text-center p-8 text-gray-500">
                            <i class="pi pi-users text-4xl mb-3 block"></i>
                            No se encontraron pacientes.
                        </div>
                    </template>

                    <Column field="dni" header="DNI" sortable class="font-bold"></Column>
                    <Column field="apellido" header="Apellido" sortable></Column>
                    <Column field="nombre" header="Nombre" sortable></Column>

                    <Column field="fecha_nacimiento" header="Nacimiento" sortable>
                        <template #body="slotProps">
                            {{ formatFecha(slotProps.data.fecha_nacimiento) }}
                        </template>
                    </Column>

                    <Column field="sexo" header="Sexo" sortable></Column>

                    <Column field="telefono" header="Teléfono">
                        <template #body="slotProps">
                            <span v-if="slotProps.data.telefono || slotProps.data.celular" class="text-sm flex items-center gap-1">
                                <i class="pi pi-phone text-gray-400"></i>
                                {{ slotProps.data.celular || slotProps.data.telefono }}
                            </span>
                            <span v-else class="text-gray-400 text-sm">-</span>
                        </template>
                    </Column>

                    <Column header="Acciones" :exportable="false" headerClass="text-right" bodyClass="text-right" style="width: 120px; text-align: right" headerStyle="width: 120px; text-align: right;">
                        <template #body="slotProps">
                            <div class="flex justify-end gap-2 pr-1">
                                <Button icon="pi pi-pencil" text rounded severity="info" @click="editarPaciente(slotProps.data.id)" />
                                <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmarEliminar(slotProps.data)" />
                            </div>
                        </template>
                    </Column>
                </DataTable>
            </div>
        </div>

        <Dialog v-model:visible="mostrarDialog" modal header="Confirmar Eliminación" :style="{ width: '400px' }" :draggable="false">
            <div class="flex items-center gap-3 mb-4">
                <i class="pi pi-exclamation-triangle text-red-500 text-4xl"></i>
                <div class="text-gray-700 dark:text-gray-300">
                    <p class="font-bold text-lg mb-1">¿Estás seguro?</p>
                    <p class="text-sm">
                        Vas a eliminar al paciente <strong>{{ pacienteAEliminar?.apellido }} {{ pacienteAEliminar?.nombre }}</strong
                        >. <br />Esta acción eliminará sus datos permanentemente.
                    </p>
                </div>
            </div>

            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="cancelarEliminar" />
                <Button label="Sí, Eliminar" severity="danger" icon="pi pi-trash" @click="eliminarPacienteConfirmado" />
            </template>
        </Dialog>
    </div>
</template>
