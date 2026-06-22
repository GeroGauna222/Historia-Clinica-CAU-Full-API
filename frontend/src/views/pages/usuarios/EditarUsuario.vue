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
    password: '',
    dni: '',
    sexo: 'X',
    telefono: '',
    matricula_tipo: 'MN',
    matricula_numero: '',
    matricula_provincia: '',
    lugar_atencion_nombre: 'CAU - UNSAM',
    lugar_atencion_direccion: '',
    lugar_atencion_contacto: '',
    lugar_atencion_email: ''
});

const ROLES = [
    { label: 'Director', value: 'director' },
    { label: 'Profesional', value: 'profesional' },
    { label: 'Administrativo', value: 'administrativo' },
    { label: 'Area', value: 'area' }
];
const SEXOS = [
    { label: 'Femenino', value: 'F' },
    { label: 'Masculino', value: 'M' },
    { label: 'Otro', value: 'X' }
];
const TIPOS_MATRICULA = ['MN', 'MP', 'OP'];
const rolPuedePrescribir = () => ['profesional', 'director'].includes(form.rol);

const loading = ref(false);

onMounted(async () => {
    try {
        loading.value = true;
        const res = await usuarioService.getUsuario(userId);
        Object.assign(form, res.data);
        form.sexo ||= 'X';
        form.matricula_tipo ||= 'MN';
        form.lugar_atencion_nombre ||= 'CAU - UNSAM';
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
        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-8 w-full max-w-3xl transition-colors">
            <h1 class="text-3xl font-bold text-center mb-8 text-color">Editar usuario</h1>

            <form @submit.prevent="onSubmit" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                        <label class="block mb-2 font-semibold text-color">Nueva contrasena</label>
                        <Password v-model="form.password" :toggleMask="true" :feedback="false" fluid :disabled="loading" placeholder="Dejar vacio para no cambiar" />
                    </div>

                    <div>
                        <label class="block mb-2 font-semibold text-color">Rol</label>
                        <Select v-model="form.rol" :options="ROLES" optionLabel="label" optionValue="value" class="w-full" :disabled="loading" required />
                    </div>

                    <div v-if="form.rol === 'profesional'">
                        <label class="block mb-2 font-semibold text-color">Especialidad</label>
                        <InputText v-model.trim="form.especialidad" class="w-full" :disabled="loading" required />
                    </div>
                </div>

                <section v-if="rolPuedePrescribir()" class="space-y-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
                    <h2 class="text-lg font-semibold m-0 text-color">Datos para recetas electronicas</h2>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="block mb-2 font-semibold text-color">DNI profesional</label>
                            <InputText v-model.trim="form.dni" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Sexo</label>
                            <Select v-model="form.sexo" :options="SEXOS" optionLabel="label" optionValue="value" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Telefono</label>
                            <InputText v-model.trim="form.telefono" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Tipo matricula</label>
                            <Select v-model="form.matricula_tipo" :options="TIPOS_MATRICULA" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Numero matricula</label>
                            <InputText v-model.trim="form.matricula_numero" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Provincia matricula</label>
                            <InputText v-model.trim="form.matricula_provincia" class="w-full" :disabled="loading" />
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block mb-2 font-semibold text-color">Lugar de atencion</label>
                            <InputText v-model.trim="form.lugar_atencion_nombre" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Direccion de atencion</label>
                            <InputText v-model.trim="form.lugar_atencion_direccion" placeholder="Calle y numero" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Contacto de atencion</label>
                            <InputText v-model.trim="form.lugar_atencion_contacto" class="w-full" :disabled="loading" />
                        </div>
                        <div>
                            <label class="block mb-2 font-semibold text-color">Email de atencion</label>
                            <InputText v-model.trim="form.lugar_atencion_email" type="email" class="w-full" :disabled="loading" />
                        </div>
                    </div>
                </section>

                <div class="flex justify-center pt-4">
                    <Button type="submit" :label="loading ? 'Guardando...' : 'Guardar cambios'" icon="pi pi-check" :loading="loading" />
                </div>
            </form>
        </div>
    </div>
</template>
