<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import usuarioService from '@/service/usuarioService';

// Imports PrimeVue
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import IconField from 'primevue/iconfield';
import InputIcon from 'primevue/inputicon';
import Tag from 'primevue/tag';

const usuarios = ref([]);
const busqueda = ref('');
const router = useRouter();

const usuarioAEliminar = ref(null);
const mostrarDialog = ref(false);

const fetchUsuarios = async () => {
    try {
        const res = await usuarioService.getUsuarios();
        usuarios.value = res.data;
    } catch (err) {
        console.error(err);
    }
};

onMounted(fetchUsuarios);

const filtrados = computed(() => {
    if (!busqueda.value) return usuarios.value;
    return usuarios.value.filter((u) => u.nombre.toLowerCase().includes(busqueda.value.toLowerCase()) || u.username.toLowerCase().includes(busqueda.value.toLowerCase()) || u.email.toLowerCase().includes(busqueda.value.toLowerCase()));
});

const editarUsuario = (id) => {
    router.push(`/usuarios/${id}/editar`);
};

const confirmarEliminar = (usuario) => {
    usuarioAEliminar.value = usuario;
    mostrarDialog.value = true;
};

const cancelarEliminar = () => {
    usuarioAEliminar.value = null;
    mostrarDialog.value = false;
};

const eliminarUsuarioConfirmado = async () => {
    if (!usuarioAEliminar.value) return;
    try {
        await usuarioService.deleteUsuario(usuarioAEliminar.value.id);
        const index = usuarios.value.findIndex((u) => u.id === usuarioAEliminar.value.id);
        if (index !== -1) {
            usuarios.value[index].activo = 0;
        }
        mostrarDialog.value = false;
        usuarioAEliminar.value = null;
    } catch (error) {
        console.error(error);
        alert('❌ Error al eliminar usuario.');
    }
};
</script>

<template>
    <div class="p-6 md:p-8 w-full h-full">
        <div class="bg-white dark:bg-[#1e1e1e] shadow-xl rounded-2xl p-6 transition-colors">
            <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white">Usuarios Registrados</h1>

                <div class="flex gap-2 w-full md:w-auto">
                    <IconField iconPosition="left" class="w-full md:w-64">
                        <InputIcon class="pi pi-search" />
                        <InputText v-model="busqueda" placeholder="Buscar usuario..." class="w-full" />
                    </IconField>

                    <Button icon="pi pi-plus" label="Nuevo" @click="router.push('/usuarios/crear')" />
                </div>
            </div>

            <div class="overflow-x-auto">
                <DataTable :value="filtrados" paginator :rows="5" :rowsPerPageOptions="[5, 10, 20]" tableStyle="min-width: 50rem" stripedRows class="p-datatable-sm">
                    <template #empty>
                        <div class="text-center p-4 text-gray-500">No se encontraron usuarios.</div>
                    </template>

                    <Column field="nombre" header="Nombre" sortable class="font-bold text-gray-700 dark:text-gray-200"></Column>
                    <Column field="username" header="Usuario" sortable></Column>
                    <Column field="email" header="Email" sortable></Column>

                    <Column field="rol" header="Rol" sortable>
                        <template #body="slotProps">
                            <span class="capitalize">{{ slotProps.data.rol }}</span>
                        </template>
                    </Column>

                    <Column field="especialidad" header="Especialidad">
                        <template #body="slotProps">
                            {{ slotProps.data.especialidad || '-' }}
                        </template>
                    </Column>

                    <Column field="activo" header="Estado" sortable>
                        <template #body="slotProps">
                            <Tag :value="slotProps.data.activo ? 'Activo' : 'Inactivo'" :severity="slotProps.data.activo ? 'success' : 'danger'" rounded />
                        </template>
                    </Column>

                    <Column header="Acciones" :exportable="false" style="min-width: 8rem">
                        <template #body="slotProps">
                            <div class="flex gap-2">
                                <Button icon="pi pi-pencil" text rounded severity="info" @click="editarUsuario(slotProps.data.id)" v-tooltip.top="'Editar'" />
                                <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmarEliminar(slotProps.data)" v-tooltip.top="'Eliminar'" />
                            </div>
                        </template>
                    </Column>
                </DataTable>
            </div>
        </div>

        <Dialog v-model:visible="mostrarDialog" modal header="Confirmar acción" :style="{ width: '400px' }" :draggable="false">
            <div class="flex items-center gap-3 mb-4">
                <i class="pi pi-exclamation-triangle text-orange-500 text-4xl"></i>
                <span class="text-gray-700 dark:text-gray-300">
                    Esta acción marcará al usuario <strong>{{ usuarioAEliminar?.username }}</strong> como inactivo. <br /><br />¿Estás seguro de continuar?
                </span>
            </div>

            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="cancelarEliminar" />
                <Button label="Sí, Eliminar" severity="danger" icon="pi pi-check" @click="eliminarUsuarioConfirmado" />
            </template>
        </Dialog>
    </div>
</template>
