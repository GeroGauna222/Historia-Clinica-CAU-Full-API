<script setup>
import usuarioService from '@/service/usuarioService';
import { computed, onMounted, ref } from 'vue';
import { useToast } from 'primevue/usetoast';

import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import IconField from 'primevue/iconfield';
import InputIcon from 'primevue/inputicon';
import Tag from 'primevue/tag';

const toast = useToast();
const usuarios = ref([]);
const busqueda = ref('');
const usuarioAReactivar = ref(null);
const mostrarDialog = ref(false);

const fetchUsuariosInactivos = async () => {
    try {
        const res = await usuarioService.getUsuarios({ inactivos: 1 });
        usuarios.value = res.data.filter((u) => u.activo === 0);
    } catch (err) {
        console.error(err);
    }
};

onMounted(fetchUsuariosInactivos);

const filtrados = computed(() => {
    if (!busqueda.value) return usuarios.value;
    const q = busqueda.value.toLowerCase();
    return usuarios.value.filter((u) => u.nombre.toLowerCase().includes(q) || u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
});

const confirmarReactivar = (usuario) => {
    usuarioAReactivar.value = usuario;
    mostrarDialog.value = true;
};

const cancelarReactivar = () => {
    usuarioAReactivar.value = null;
    mostrarDialog.value = false;
};

const reactivarUsuarioConfirmado = async () => {
    if (!usuarioAReactivar.value) return;
    try {
        await usuarioService.activarUsuario(usuarioAReactivar.value.id);
        usuarios.value = usuarios.value.filter((u) => u.id !== usuarioAReactivar.value.id);
        mostrarDialog.value = false;
        usuarioAReactivar.value = null;
        toast.add({ severity: 'success', summary: 'Reactivado', detail: 'El usuario fue reactivado correctamente', life: 3000 });
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo reactivar el usuario', life: 5000 });
    }
};
</script>

<template>
    <div class="p-6 md:p-8 w-full h-full">
        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-6 transition-colors">
            <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                <h1 class="text-3xl font-bold text-color">Usuarios inactivos</h1>

                <IconField iconPosition="left" class="w-full md:w-64">
                    <InputIcon class="pi pi-search" />
                    <InputText v-model="busqueda" placeholder="Buscar usuario..." class="w-full" />
                </IconField>
            </div>

            <DataTable :value="filtrados" paginator :rows="10" :rowsPerPageOptions="[5, 10, 20]" stripedRows class="p-datatable-sm">
                <template #empty>
                    <div class="flex flex-col items-center py-12 text-muted-color">
                        <i class="pi pi-user-minus text-4xl mb-3"></i>
                        <p class="text-lg font-medium">No hay usuarios inactivos</p>
                        <p class="text-sm">Todos los usuarios están activos en el sistema</p>
                    </div>
                </template>

                <Column field="nombre" header="Nombre" sortable></Column>
                <Column field="username" header="Usuario" sortable></Column>
                <Column field="email" header="Email" sortable></Column>
                <Column field="rol" header="Rol" sortable>
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.rol" severity="secondary" rounded />
                    </template>
                </Column>
                <Column field="especialidad" header="Especialidad"></Column>
                <Column header="Acciones" :exportable="false" style="width: 120px">
                    <template #body="slotProps">
                        <Button icon="pi pi-refresh" label="Reactivar" text rounded severity="success" size="small" @click="confirmarReactivar(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>
        </div>

        <Dialog v-model:visible="mostrarDialog" modal header="Confirmar Reactivación" :style="{ width: '400px' }">
            <div class="flex items-center gap-3 mb-4">
                <i class="pi pi-exclamation-triangle text-yellow-500 text-4xl"></i>
                <div class="text-color">
                    <p class="font-bold text-lg mb-1">¿Reactivar usuario?</p>
                    <p class="text-sm text-muted-color">
                        El usuario <strong>{{ usuarioAReactivar?.nombre }}</strong> podrá volver a iniciar sesión.
                    </p>
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="cancelarReactivar" />
                <Button label="Reactivar" icon="pi pi-check" severity="success" @click="reactivarUsuarioConfirmado" />
            </template>
        </Dialog>
    </div>
</template>
