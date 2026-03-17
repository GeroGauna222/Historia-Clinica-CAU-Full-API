<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import usuarioService from '@/service/usuarioService';
import { useToast } from 'primevue/usetoast';

import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Select from 'primevue/select';
import Button from 'primevue/button';

const toast = useToast();
const route = useRoute();
const userId = route.params.id;

const form = reactive({
    nombre: '',
    username: '',
    email: '',
    rol: '',
    especialidad: '',
    password: ''
});

const ROLES = [
    { label: 'Director', value: 'director' },
    { label: 'Profesional', value: 'profesional' },
    { label: 'Administrativo', value: 'administrativo' },
    { label: 'Área', value: 'area' }
];

const loading = ref(false);

onMounted(async () => {
    try {
        loading.value = true;
        const res = await usuarioService.getUsuario(userId);
        Object.assign(form, res.data);
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo cargar el usuario', life: 5000 });
    } finally {
        loading.value = false;
    }
});

async function onSubmit() {
    loading.value = true;
    try {
        const payload = { ...form };
        if (!payload.password) delete payload.password;

        await usuarioService.updateUsuario(userId, payload);
        toast.add({ severity: 'success', summary: 'Actualizado', detail: 'Usuario actualizado correctamente', life: 3000 });
        form.password = '';
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Error', detail: e.response?.data?.error || 'Error al actualizar usuario', life: 5000 });
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="flex justify-center items-start p-8">
        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-8 w-full max-w-2xl transition-colors">
            <h1 class="text-3xl font-bold text-center mb-8 text-color">Editar usuario</h1>

            <form @submit.prevent="onSubmit" class="space-y-6">
                <div>
                    <label class="block mb-2 font-semibold text-color">Nombre completo</label>
                    <InputText v-model.trim="form.nombre" class="w-full" :disabled="loading" required />
                </div>

                <div>
                    <label class="block mb-2 font-semibold text-color">Usuario</label>
                    <InputText v-model.trim="form.username" class="w-full" :disabled="loading" required />
                </div>

                <div>
                    <label class="block mb-2 font-semibold text-color">Email</label>
                    <InputText v-model.trim="form.email" type="email" class="w-full" :disabled="loading" required />
                </div>

                <div>
                    <label class="block mb-2 font-semibold text-color">Nueva contraseña (opcional)</label>
                    <Password v-model="form.password" :toggleMask="true" :feedback="false" fluid :disabled="loading" placeholder="Dejar vacío para no cambiar" />
                </div>

                <div>
                    <label class="block mb-2 font-semibold text-color">Rol</label>
                    <Select v-model="form.rol" :options="ROLES" optionLabel="label" optionValue="value" class="w-full" :disabled="loading" required />
                </div>

                <div v-if="form.rol === 'profesional'">
                    <label class="block mb-2 font-semibold text-color">Especialidad</label>
                    <InputText v-model.trim="form.especialidad" class="w-full" :disabled="loading" required />
                </div>

                <div class="flex justify-center pt-4">
                    <Button type="submit" :label="loading ? 'Guardando...' : 'Guardar cambios'" icon="pi pi-check" :loading="loading" />
                </div>
            </form>
        </div>
    </div>
</template>
