<script setup>
import logoUnsam from '@/assets/logo_unsam_sin_letras.png';
import api from '@/api/axios';
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { validarPasswordFuerte } from '@/utils/validators';

const route = useRoute();
const router = useRouter();

const password = ref('');
const confirmPassword = ref('');
const mensaje = ref('');
const error = ref('');
const loading = ref(false);

// Errores locales para feedback visual
const passwordError = ref('');
const confirmError = ref('');

// Validar mientras escribe
const validarEnVivo = () => {
    const err = validarPasswordFuerte(password.value);
    // Si validarPasswordFuerte devuelve string, es el error. Si devuelve null/false, está bien.
    passwordError.value = err || '';
};

// Observar confirmación para avisar si coinciden
watch([password, confirmPassword], () => {
    if (confirmPassword.value && password.value !== confirmPassword.value) {
        confirmError.value = 'Las contraseñas no coinciden';
    } else {
        confirmError.value = '';
    }
});

async function resetear() {
    mensaje.value = '';
    error.value = '';

    // Validación final por seguridad
    validarEnVivo();
    if (passwordError.value || confirmError.value) return;

    loading.value = true;
    try {
        const res = await api.post(`/reset/${route.params.token}`, {
            new_password: password.value,
            confirm_password: confirmPassword.value
        });

        mensaje.value = res.data.message || 'Contraseña actualizada correctamente';
        setTimeout(() => router.push('/auth/login'), 2500);
    } catch (err) {
        error.value = err.response?.data?.error || 'Error de conexión con el servidor';
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <div class="flex flex-col items-center justify-center">
            <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, var(--primary-color) 10%, rgba(33, 150, 243, 0) 30%)">
                <div class="w-full bg-surface-0 dark:bg-surface-900 py-20 px-8 sm:px-20" style="border-radius: 53px">
                    <div class="text-center mb-8">
                        <img :src="logoUnsam" alt="Logo CAU" class="mb-6 w-24 mx-auto" />
                        <div class="text-surface-900 dark:text-surface-0 text-3xl font-medium mb-4">Restablecer Contraseña</div>
                        <span class="text-muted-color font-medium"> Ingresá tu nueva contraseña para continuar. </span>
                    </div>

                    <form @submit.prevent="resetear" class="space-y-6 w-full md:w-[28rem]">
                        <div>
                            <label for="password" class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2"> Nueva contraseña </label>
                            <Password id="password" v-model="password" :toggleMask="true" :feedback="false" fluid placeholder="********" :invalid="!!passwordError" @input="validarEnVivo" />
                            <p v-if="passwordError" class="text-red-500 text-xs mt-1">
                                {{ passwordError }}
                            </p>
                            <p v-else class="text-muted-color text-xs mt-1">Mínimo 8 caracteres, una mayúscula, una minúscula, un número y un símbolo.</p>
                        </div>

                        <div>
                            <label for="confirmPassword" class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2"> Confirmar contraseña </label>
                            <Password id="confirmPassword" v-model="confirmPassword" :toggleMask="true" :feedback="false" fluid placeholder="********" :invalid="!!confirmError" />
                            <p v-if="confirmError" class="text-red-500 text-xs mt-1">Las contraseñas no coinciden.</p>
                        </div>

                        <Button type="submit" label="Guardar nueva contraseña" class="w-full" :loading="loading" :disabled="!!passwordError || !!confirmError || !password" />

                        <p v-if="mensaje" class="text-green-600 text-center mt-4 text-sm font-medium bg-green-50 dark:bg-green-950 p-2 rounded border border-green-200 dark:border-green-800">
                            {{ mensaje }}
                        </p>
                        <p v-if="error" class="text-red-600 text-center mt-4 text-sm font-medium bg-red-50 dark:bg-red-950 p-2 rounded border border-red-200 dark:border-red-800">
                            {{ error }}
                        </p>

                        <div class="text-center mt-6">
                            <router-link to="/auth/login" class="text-sm text-primary hover:underline"> &larr; Volver al inicio de sesión </router-link>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</template>
