<script setup>
import { reactive, ref } from 'vue';
import usuarioService from '@/service/usuarioService';
import { validarPasswordFuerte, validarEmail } from '@/utils/validators';

// Imports de PrimeVue
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Dropdown from 'primevue/dropdown'; // ✅ Corregido: Usamos Dropdown en vez de Select
import Button from 'primevue/button';

const form = reactive({
    nombre: '',
    username: '',
    email: '',
    password: '',
    rol: '',
    especialidad: ''
});

const loading = ref(false);
const error = ref('');
const ok = ref('');

// ✅ Lista de roles corregida (incluye Área)
const roles = ref(['Director', 'Profesional', 'Administrativo', 'Área']);

function validate() {
    if (!form.nombre || !form.username || !form.email || !form.password || !form.rol) {
        return 'Todos los campos son obligatorios';
    }

    if (!validarEmail(form.email)) {
        return 'Email inválido';
    }

    const errPw = validarPasswordFuerte(form.password);
    if (errPw) return errPw;

    if (!roles.value.includes(form.rol)) {
        return 'Rol inválido';
    }

    // Validar especialidad solo si es Profesional
    if (form.rol === 'Profesional' && !form.especialidad) {
        return 'La especialidad es obligatoria para profesionales';
    }

    return '';
}

async function onSubmit() {
    error.value = '';
    ok.value = '';

    const v = validate();
    if (v) {
        error.value = v;
        return;
    }

    loading.value = true;
    try {
        // 1. Clonamos el formulario para no modificar la vista
        const payload = { ...form };

        // 2. Mapeo de roles para el Backend
        // El backend espera: 'director', 'profesional', 'administrativo', 'area'
        if (payload.rol === 'Área') {
            payload.rol = 'area';
        } else {
            payload.rol = payload.rol.toLowerCase();
        }

        // 3. Limpiamos especialidad si no es profesional
        if (payload.rol !== 'profesional') {
            payload.especialidad = null;
        }

        // 4. Enviamos el payload transformado
        const resp = await usuarioService.createUsuario(payload);
        ok.value = resp.data?.message || 'Usuario creado correctamente ✅';

        // Limpiar campos
        form.nombre = '';
        form.username = '';
        form.email = '';
        form.password = '';
        form.rol = '';
        form.especialidad = '';
    } catch (e) {
        error.value = e.response?.data?.error || e.message || 'Error al crear usuario';
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="flex justify-center items-start p-6 md:p-8">
        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-8 w-full max-w-2xl transition-colors">
            <div class="text-center mb-8">
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white mb-2">Crear Usuario</h1>
                <p class="text-gray-500 dark:text-gray-400">Registrar un nuevo miembro del personal</p>
            </div>

            <form @submit.prevent="onSubmit" class="space-y-6">
                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-id-card mr-1 text-primary"></i> Nombre completo </label>
                    <InputText v-model.trim="form.nombre" placeholder="Ej: Ana Pérez (o Módulo Kinesiología)" class="w-full" :disabled="loading" />
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-user mr-1 text-primary"></i> Usuario </label>
                        <InputText v-model.trim="form.username" placeholder="Ej: aperez" class="w-full" :disabled="loading" />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-envelope mr-1 text-primary"></i> Email </label>
                        <InputText v-model.trim="form.email" type="email" placeholder="ana@ejemplo.com" class="w-full" :disabled="loading" />
                    </div>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-lock mr-1 text-primary"></i> Contraseña </label>
                    <Password v-model="form.password" :feedback="false" toggleMask placeholder="********" class="w-full" inputClass="w-full" :disabled="loading" />
                    <small class="text-gray-500 dark:text-gray-400"> Mínimo 8 caracteres, mayúscula, minúscula y número. </small>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-briefcase mr-1 text-primary"></i> Rol </label>
                    <Dropdown v-model="form.rol" :options="roles" placeholder="Seleccioná un rol" class="w-full" :disabled="loading" />
                </div>

                <transition name="fade">
                    <div v-if="form.rol === 'Profesional'" class="flex flex-col gap-2 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-heart mr-1 text-primary"></i> Especialidad </label>
                        <InputText v-model.trim="form.especialidad" placeholder="Ej: Cardiología, Pediatría..." class="w-full" :disabled="loading" />
                    </div>
                </transition>

                <div v-if="error" class="p-3 rounded-lg bg-red-100 text-red-700 text-center font-medium border border-red-200"><i class="pi pi-times-circle mr-2"></i> {{ error }}</div>

                <div v-if="ok" class="p-3 rounded-lg bg-green-100 text-green-700 text-center font-medium border border-green-200"><i class="pi pi-check-circle mr-2"></i> {{ ok }}</div>

                <div class="flex justify-center pt-4">
                    <Button type="submit" label="Crear Usuario" icon="pi pi-user-plus" class="w-full md:w-auto px-8 py-3 font-bold shadow-lg" :loading="loading" />
                </div>
            </form>
        </div>
    </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
    transition:
        opacity 0.3s ease,
        transform 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}
</style>
