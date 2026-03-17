<script setup>
import authService from '@/service/authService';
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();

onMounted(async () => {
    userStore.startLogout();
    try {
        await authService.logout();
    } catch (error) {
        console.error(error);
    } finally {
        userStore.logout();
        router.replace('/auth/login?logged_out=1');
    }
});
</script>

<template>
    <div class="flex items-center justify-center min-h-screen">
        <p class="text-gray-700">Cerrando sesión...</p>
    </div>
</template>

<style scoped></style>
