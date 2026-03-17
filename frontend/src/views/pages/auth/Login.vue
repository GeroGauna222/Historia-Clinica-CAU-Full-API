<script setup>
import logoUnsam from '@/assets/logo_unsam_sin_letras.png';
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import api from '@/api/axios';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { useToast } from 'primevue/usetoast';

const usuario = ref('');
const password = ref('');
const checked = ref(false);
const router = useRouter();
const userStore = useUserStore();
const toast = useToast();

const login = async () => {
    try {
        await api.post('/login', {
            username: usuario.value,
            password: password.value,
            remember: checked.value
        });

        await userStore.fetchUser();
        router.push('/');
    } catch (error) {
        const msg = error.response?.data?.error || 'Credenciales incorrectas o error de red';
        toast.add({ severity: 'error', summary: 'Error de inicio de sesión', detail: msg, life: 5000 });
    }
};

const irARecuperar = () => {
    router.push('/recuperar');
};
</script>

<template>
    <Toast />
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <div class="flex flex-col items-center justify-center">
            <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, var(--primary-color) 10%, rgba(33, 150, 243, 0) 30%)">
                <div class="w-full bg-surface-0 dark:bg-surface-900 py-20 px-8 sm:px-20" style="border-radius: 53px">
                    <div class="text-center mb-8">
                        <img :src="logoUnsam" alt="Logo CAU" class="mb-6 w-20 mx-auto" />
                        <div class="text-surface-900 dark:text-surface-0 text-3xl font-medium mb-4">Bienvenido al Sistema de <br />Historias Clínicas del CAU</div>
                        <span class="text-muted-color font-medium">Iniciá sesión para continuar</span>
                    </div>

                    <div>
                        <label for="usuario1" class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2">Usuario</label>
                        <InputText id="usuario1" type="text" placeholder="Usuario" class="w-full md:w-[30rem] mb-8" v-model="usuario" />

                        <label for="password1" class="block text-surface-900 dark:text-surface-0 font-medium text-xl mb-2">Contraseña</label>
                        <Password id="password1" v-model="password" placeholder="Contraseña" :toggleMask="true" class="mb-4" fluid :feedback="false" @keyup.enter="login"></Password>

                        <div class="flex items-center justify-between mt-2 mb-8 gap-8">
                            <div class="flex items-center">
                                <Checkbox v-model="checked" id="rememberme1" binary class="mr-2"></Checkbox>
                                <label for="rememberme1">Recordarme</label>
                            </div>
                            <span @click="irARecuperar" class="font-medium no-underline ml-2 text-right cursor-pointer text-primary hover:underline transition"> ¿Olvidaste tu contraseña? </span>
                        </div>
                        <Button label="Ingresar" class="w-full" @click="login"></Button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.pi-eye,
.pi-eye-slash {
    transform: scale(1.6);
    margin-right: 1rem;
}
</style>
