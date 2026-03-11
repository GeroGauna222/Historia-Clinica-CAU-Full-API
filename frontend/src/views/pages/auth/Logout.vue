<script setup>
import authService from '@/service/authService';
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

onMounted(async () => {
    try {
        await authService.logout();
        router.push('/auth/login');
    } catch (error) {
        console.error(error);
        router.push('/auth/login');
    }
});
</script>

<template>
    <div class="flex items-center justify-center min-h-screen">
        <p class="text-gray-700">Cerrando sesión...</p>
    </div>
</template>

<style scoped></style>
