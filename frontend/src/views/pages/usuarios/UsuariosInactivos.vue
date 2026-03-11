<script setup>
import usuarioService from '@/service/usuarioService';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import { computed, onMounted, ref } from 'vue';

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
    return usuarios.value.filter((u) => u.nombre.toLowerCase().includes(busqueda.value.toLowerCase()) || u.username.toLowerCase().includes(busqueda.value.toLowerCase()) || u.email.toLowerCase().includes(busqueda.value.toLowerCase()));
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
    } catch (error) {
        console.error(error);
        alert('❌ Error al reactivar usuario.');
    }
};
</script>

<template>
    <div class="p-4">
        <h1 class="text-2xl font-bold mb-4">Usuarios inactivos</h1>

        <input v-model="busqueda" type="text" placeholder="Buscar por nombre o usuario" class="p-inputtext p-component w-full mb-4 border rounded px-3 py-2" />

        <div v-if="filtrados.length > 0" class="overflow-x-auto">
            <table class="min-w-full bg-white rounded shadow">
                <thead>
                    <tr>
                        <th class="py-2 px-4 border-b">ID</th>
                        <th class="py-2 px-4 border-b">Nombre</th>
                        <th class="py-2 px-4 border-b">Usuario</th>
                        <th class="py-2 px-4 border-b">Email</th>
                        <th class="py-2 px-4 border-b">Rol</th>
                        <th class="py-2 px-4 border-b">Especialidad</th>
                        <th class="py-2 px-4 border-b">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="usuario in filtrados" :key="usuario.id">
                        <td class="py-2 px-4 border-b">{{ usuario.id }}</td>
                        <td class="py-2 px-4 border-b">{{ usuario.nombre }}</td>
                        <td class="py-2 px-4 border-b">{{ usuario.username }}</td>
                        <td class="py-2 px-4 border-b">{{ usuario.email }}</td>
                        <td class="py-2 px-4 border-b">{{ usuario.rol }}</td>
                        <td class="py-2 px-4 border-b">{{ usuario.especialidad }}</td>
                        <td class="py-2 px-4 border-b flex gap-2">
                            <button class="bg-blue-500 text-white px-2 py-1 rounded" @click="confirmarReactivar(usuario)">Reactivar</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <p v-else>No se encontraron usuarios inactivos.</p>

        <!-- Modal de confirmación -->
        <Dialog v-model:visible="mostrarDialog" modal header="Confirmar Reactivación" :style="{ width: '350px' }">
            <p>
                ⚠️ Esta acción reactivará el usuario y podrá volver a iniciar sesión.<br />
                ¿Estás seguro que querés continuar?
            </p>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="cancelarReactivar" />
                <Button label="Reactivar" icon="pi pi-check" class="p-button-success" @click="reactivarUsuarioConfirmado" />
            </template>
        </Dialog>
    </div>
</template>
