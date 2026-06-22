<script setup>
import { reactive, ref } from 'vue';
import usuarioService from '@/service/usuarioService';
import { validarPasswordFuerte, validarEmail } from '@/utils/validators';

import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Dropdown from 'primevue/dropdown';
import Button from 'primevue/button';

const form = reactive({
    nombre: '',
    username: '',
    email: '',
    password: '',
    rol: '',
    especialidad: '',
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

const loading = ref(false);
const error = ref('');
const ok = ref('');

const roles = ref(['Director', 'Profesional', 'Administrativo', 'Area']);
const sexos = ref([
    { label: 'Femenino', value: 'F' },
    { label: 'Masculino', value: 'M' },
    { label: 'Otro', value: 'X' }
]);
const tiposMatricula = ref(['MN', 'MP', 'OP']);
const rolPuedePrescribir = () => ['Profesional', 'Director'].includes(form.rol);

function validate() {
    if (!form.nombre || !form.username || !form.email || !form.password || !form.rol) {
        return 'Todos los campos son obligatorios';
    }

    if (!validarEmail(form.email)) {
        return 'Email invalido';
    }

    const errPw = validarPasswordFuerte(form.password);
    if (errPw) return errPw;

    if (!roles.value.includes(form.rol)) {
        return 'Rol invalido';
    }

    if (form.rol === 'Profesional' && !form.especialidad) {
        return 'La especialidad es obligatoria para profesionales';
    }

    if (rolPuedePrescribir() && (!form.dni || !form.matricula_numero || !form.lugar_atencion_direccion)) {
        return 'Para recetas electronicas completa DNI, matricula y direccion de atencion';
    }

    return '';
}

function resetForm() {
    Object.assign(form, {
        nombre: '',
        username: '',
        email: '',
        password: '',
        rol: '',
        especialidad: '',
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
        const payload = { ...form };
        payload.rol = payload.rol === 'Area' ? 'area' : payload.rol.toLowerCase();

        if (payload.rol !== 'profesional') {
            payload.especialidad = null;
        }

        const resp = await usuarioService.createUsuario(payload);
        ok.value = resp.data?.message || 'Usuario creado correctamente';
        resetForm();
    } catch (e) {
        error.value = e.response?.data?.error || e.message || 'Error al crear usuario';
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="flex justify-center items-start p-6 md:p-8">
        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-8 w-full max-w-3xl transition-colors">
            <div class="text-center mb-8">
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white mb-2">Crear Usuario</h1>
                <p class="text-gray-500 dark:text-gray-400">Registrar un nuevo miembro del personal</p>
            </div>

            <form @submit.prevent="onSubmit" class="space-y-6">
                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200">Nombre completo</label>
                    <InputText v-model.trim="form.nombre" placeholder="Ej: Ana Perez" class="w-full" :disabled="loading" />
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200">Usuario</label>
                        <InputText v-model.trim="form.username" placeholder="Ej: aperez" class="w-full" :disabled="loading" />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200">Email</label>
                        <InputText v-model.trim="form.email" type="email" placeholder="ana@ejemplo.com" class="w-full" :disabled="loading" />
                    </div>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200">Contrasena</label>
                    <Password v-model="form.password" :feedback="false" toggleMask placeholder="********" class="w-full" inputClass="w-full" :disabled="loading" />
                    <small class="text-gray-500 dark:text-gray-400">Minimo 8 caracteres, mayuscula, minuscula y numero.</small>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200">Rol</label>
                    <Dropdown v-model="form.rol" :options="roles" placeholder="Selecciona un rol" class="w-full" :disabled="loading" />
                </div>

                <transition name="fade">
                    <div v-if="rolPuedePrescribir()" class="space-y-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
                        <div class="flex flex-col gap-2">
                            <label class="font-semibold text-gray-700 dark:text-gray-200">Especialidad</label>
                            <InputText v-model.trim="form.especialidad" placeholder="Ej: Cardiologia, Pediatria..." class="w-full" :disabled="loading" />
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">DNI profesional</label>
                                <InputText v-model.trim="form.dni" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Sexo</label>
                                <Dropdown v-model="form.sexo" :options="sexos" optionLabel="label" optionValue="value" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Telefono</label>
                                <InputText v-model.trim="form.telefono" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Tipo matricula</label>
                                <Dropdown v-model="form.matricula_tipo" :options="tiposMatricula" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Numero matricula</label>
                                <InputText v-model.trim="form.matricula_numero" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Provincia matricula</label>
                                <InputText v-model.trim="form.matricula_provincia" class="w-full" :disabled="loading" />
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Lugar de atencion</label>
                                <InputText v-model.trim="form.lugar_atencion_nombre" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Direccion de atencion</label>
                                <InputText v-model.trim="form.lugar_atencion_direccion" placeholder="Calle y numero" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Contacto de atencion</label>
                                <InputText v-model.trim="form.lugar_atencion_contacto" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="font-semibold text-gray-700 dark:text-gray-200">Email de atencion</label>
                                <InputText v-model.trim="form.lugar_atencion_email" type="email" class="w-full" :disabled="loading" />
                            </div>
                        </div>
                    </div>
                </transition>

                <div v-if="error" class="p-3 rounded-lg bg-red-100 text-red-700 text-center font-medium border border-red-200">{{ error }}</div>
                <div v-if="ok" class="p-3 rounded-lg bg-green-100 text-green-700 text-center font-medium border border-green-200">{{ ok }}</div>

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
