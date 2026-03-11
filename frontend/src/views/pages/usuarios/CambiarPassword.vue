<script setup>
import { ref } from 'vue';
import api from '@/api/axios';
import { validarPasswordFuerte } from '@/utils/validators';

const actual = ref('');
const nueva = ref('');
const confirmar = ref('');
const mensaje = ref('');
const error = ref('');
const loading = ref(false);
const showActual = ref(false);
const showNueva = ref(false);
const showConfirmar = ref(false);

const cambiar = async () => {
    mensaje.value = '';
    error.value = '';

    const errPw = validarPasswordFuerte(nueva.value);
    if (errPw) {
        error.value = errPw;
        return;
    }

    if (nueva.value !== confirmar.value) {
        error.value = 'Las contraseñas no coinciden';
        return;
    }

    loading.value = true;
    try {
        const res = await api.post(
            '/usuario/cambiar-password',
            {
                actual: actual.value,
                nueva: nueva.value,
                confirmar: confirmar.value
            },
            { withCredentials: true }
        );

        mensaje.value = res.data.message;
        actual.value = '';
        nueva.value = '';
        confirmar.value = '';
    } catch (err) {
        error.value = err.response?.data?.error || 'No se pudo cambiar la contraseña';
    } finally {
        loading.value = false;
    }
};
</script>

<template>
    <div class="max-w-lg mx-auto bg-surface-0 dark:bg-surface-900 p-6 rounded-xl shadow text-surface-900 dark:text-surface-0">
        <h1 class="text-2xl font-bold mb-6">Cambiar Contraseña</h1>

        <!-- Contraseña actual -->
        <label class="block font-semibold mb-2">Contraseña actual</label>
        <div class="flex gap-2 items-center mb-4">
            <input v-model="actual" :type="showActual ? 'text' : 'password'" class="w-full p-2 rounded border border-surface-300 bg-surface-50 dark:bg-surface-800 text-surface-900 dark:text-surface-0" />
            <button type="button" @click="showActual = !showActual" class="px-3 py-2 rounded border border-surface-400 bg-surface-100 dark:bg-surface-700 hover:bg-surface-200 dark:hover:bg-surface-600 text-sm min-w-[80px]">
                {{ showActual ? 'Ocultar' : 'Ver' }}
            </button>
        </div>

        <!-- Nueva contraseña -->
        <label class="block font-semibold mb-2">Nueva contraseña</label>
        <div class="flex gap-2 items-center mb-4">
            <input v-model="nueva" :type="showNueva ? 'text' : 'password'" class="w-full p-2 rounded border border-surface-300 bg-surface-50 dark:bg-surface-800 text-surface-900 dark:text-surface-0" />
            <button type="button" @click="showNueva = !showNueva" class="px-3 py-2 rounded border border-surface-400 bg-surface-100 dark:bg-surface-700 hover:bg-surface-200 dark:hover:bg-surface-600 text-sm min-w-[80px]">
                {{ showNueva ? 'Ocultar' : 'Ver' }}
            </button>
        </div>

        <!-- Confirmar -->
        <label class="block font-semibold mb-2">Confirmar nueva contraseña</label>
        <div class="flex gap-2 items-center mb-4">
            <input v-model="confirmar" :type="showConfirmar ? 'text' : 'password'" class="w-full p-2 rounded border border-surface-300 bg-surface-50 dark:bg-surface-800 text-surface-900 dark:text-surface-0" />
            <button type="button" @click="showConfirmar = !showConfirmar" class="px-3 py-2 rounded border border-surface-400 bg-surface-100 dark:bg-surface-700 hover:bg-surface-200 dark:hover:bg-surface-600 text-sm min-w-[80px]">
                {{ showConfirmar ? 'Ocultar' : 'Ver' }}
            </button>
        </div>

        <button @click="cambiar" :disabled="loading" class="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg w-full font-medium hover:bg-blue-700 transition disabled:opacity-60">Guardar nueva contraseña</button>

        <p v-if="mensaje" class="text-green-500 mt-4 text-sm">{{ mensaje }}</p>
        <p v-if="error" class="text-red-500 mt-4 text-sm">{{ error }}</p>
    </div>
</template>
