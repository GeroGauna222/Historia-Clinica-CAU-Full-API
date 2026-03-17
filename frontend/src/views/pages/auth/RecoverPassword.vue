<script setup>
import logoUnsam from '@/assets/logo_unsam_sin_letras.png';
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import api from '@/api/axios';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { validarEmail } from '@/utils/validators';

const email = ref('');
const mensaje = ref('');
const error = ref('');
const loading = ref(false);
const router = useRouter();

// Enviar solicitud al backend Flask
const recuperar = async () => {
    mensaje.value = '';
    error.value = '';
    loading.value = true;

    try {
        if (!validarEmail(email.value)) {
            error.value = 'Ingresá un correo válido';
            loading.value = false;
            return;
        }
        const res = await api.post('/recover', { email: email.value });
        mensaje.value = res.data.message;
    } catch (err) {
        error.value = err.response?.data?.error || 'Error de conexión con el servidor';
    } finally {
        loading.value = false;
    }
};

// Volver al login
const irLogin = () => {
    router.push('/auth/login');
};
</script>

<template>
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <div class="flex flex-col items-center justify-center">
            <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, var(--primary-color) 10%, rgba(33, 150, 243, 0) 30%)">
                <div class="w-full bg-surface-0 dark:bg-surface-900 py-20 px-8 sm:px-20" style="border-radius: 53px">
                    <div class="text-center mb-8">
                        <img :src="logoUnsam" alt="Logo CAU" class="mb-6 w-20 mx-auto" />
                        <div class="text-surface-900 dark:text-surface-0 text-3xl font-medium mb-4">Recuperar Contraseña</div>
                        <span class="text-muted-color font-medium"> Ingresá tu correo electrónico para recibir un enlace de recuperación. </span>
                    </div>

                    <!-- Formulario -->
                    <form @submit.prevent="recuperar" class="flex flex-col">
                        <label for="email" class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2">Correo electrónico</label>
                        <InputText id="email" v-model="email" type="email" placeholder="ejemplo@unsam.edu.ar" class="w-full md:w-[30rem] mb-8" required />

                        <Button label="Enviar enlace de recuperación" class="w-full mb-4" :disabled="loading" @click="recuperar">
                            <template v-if="loading"> <i class="pi pi-spin pi-spinner mr-2"></i> Enviando... </template>
                        </Button>

                        <div class="text-center mt-2">
                            <span @click="irLogin" class="text-primary font-medium text-sm cursor-pointer hover:underline transition"> ← Volver al inicio de sesión </span>
                        </div>

                        <p v-if="mensaje" class="text-green-600 text-center text-sm mt-4 font-medium">
                            {{ mensaje }}
                        </p>
                        <p v-if="error" class="text-red-500 text-center text-sm mt-4 font-medium">
                            {{ error }}
                        </p>
                    </form>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.pi-eye {
    transform: scale(1.6);
    margin-right: 1rem;
}

.pi-eye-slash {
    transform: scale(1.6);
    margin-right: 1rem;
}
</style>
