<script setup>
import { ref, computed, onMounted } from 'vue';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';
import { buildFotoURL } from '@/utils/fotoUrl.js';
import { useToast } from 'primevue/usetoast';

import InputText from 'primevue/inputtext';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';

const userStore = useUserStore();
const toast = useToast();

const nombre = ref('');
const email = ref('');
const archivoFoto = ref(null);
const previewFoto = ref(null);
const imgVersion = ref(Date.now());
const confirmarEliminarFoto = ref(false);

onMounted(async () => {
    if (!userStore.id) {
        await userStore.fetchUser();
    }
    nombre.value = userStore.nombre || '';
    email.value = userStore.email || '';
});

const imagenA_Mostrar = computed(() => {
    if (previewFoto.value) return previewFoto.value;
    if (userStore.foto) return buildFotoURL(userStore.foto, imgVersion.value);
    return null;
});

const onFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) {
        archivoFoto.value = null;
        previewFoto.value = null;
        return;
    }
    archivoFoto.value = file;
    previewFoto.value = URL.createObjectURL(file);
};

const actualizarPerfil = async () => {
    try {
        const form = new FormData();
        form.append('nombre', nombre.value);
        form.append('email', email.value);

        if (archivoFoto.value) {
            form.append('foto', archivoFoto.value);
        }

        await api.post('/usuario/perfil', form, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        toast.add({ severity: 'success', summary: 'Perfil actualizado', detail: 'Los cambios se guardaron correctamente', life: 3000 });

        await userStore.fetchUser();
        userStore.recargarImagen();
        previewFoto.value = null;
        archivoFoto.value = null;
        imgVersion.value = Date.now();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo actualizar el perfil', life: 5000 });
    }
};

const eliminarFoto = async () => {
    try {
        await api.delete('/usuario/foto');

        await userStore.fetchUser();
        userStore.recargarImagen();
        previewFoto.value = null;
        archivoFoto.value = null;
        imgVersion.value = Date.now();
        confirmarEliminarFoto.value = false;

        toast.add({ severity: 'info', summary: 'Foto eliminada', detail: 'Tu foto de perfil fue removida', life: 3000 });
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar la foto', life: 5000 });
    }
};
</script>

<template>
    <div class="max-w-lg mx-auto bg-surface-0 dark:bg-surface-900 p-8 rounded-2xl shadow-lg mt-6 border border-surface-200 dark:border-surface-700 transition-colors">
        <h1 class="text-2xl font-bold mb-8 text-color text-center">Editar mi Perfil</h1>

        <div class="flex flex-col items-center mb-8">
            <div v-if="imagenA_Mostrar" class="mb-4">
                <img :src="imagenA_Mostrar" class="w-32 h-32 rounded-full object-cover border-4 border-primary/20 shadow-md" alt="Foto de perfil" />
            </div>
            <div v-else class="mb-4 w-32 h-32 rounded-full bg-primary/10 flex items-center justify-center text-primary text-5xl font-bold shadow-md select-none">
                {{ nombre ? nombre.charAt(0).toUpperCase() : 'U' }}
            </div>

            <label class="cursor-pointer">
                <Button :label="userStore.foto || previewFoto ? 'Cambiar foto' : 'Subir foto'" icon="pi pi-camera" severity="secondary" outlined size="small" />
                <input type="file" class="hidden" accept="image/*" @change="onFileChange" />
            </label>
        </div>

        <div class="space-y-5">
            <div>
                <label class="block mb-2 font-semibold text-color text-sm">Nombre completo</label>
                <InputText v-model="nombre" class="w-full" />
            </div>

            <div>
                <label class="block mb-2 font-semibold text-color text-sm">Correo electrónico</label>
                <InputText v-model="email" type="email" class="w-full" />
            </div>
        </div>

        <div class="flex justify-between items-center mt-8 pt-6 border-t border-surface-200 dark:border-surface-700">
            <Button v-if="userStore.foto" label="Eliminar foto" icon="pi pi-trash" text severity="danger" size="small" @click="confirmarEliminarFoto = true" />
            <div v-else></div>
            <Button label="Guardar cambios" icon="pi pi-check" @click="actualizarPerfil" />
        </div>

        <Dialog v-model:visible="confirmarEliminarFoto" modal header="Eliminar foto" :style="{ width: '350px' }">
            <p class="text-color">¿Estás seguro de que querés eliminar tu foto de perfil?</p>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="confirmarEliminarFoto = false" />
                <Button label="Eliminar" severity="danger" icon="pi pi-trash" @click="eliminarFoto" />
            </template>
        </Dialog>
    </div>
</template>
