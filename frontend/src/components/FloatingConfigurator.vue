<script setup>
import { onMounted } from 'vue';
import { useLayout } from '@/layout/composables/layout';
import AppConfigurator from '@/layout/AppConfigurator.vue';

const { toggleDarkMode, isDarkTheme } = useLayout();

/**
 * Alterna entre modo oscuro y claro
 * y sincroniza con las clases globales y localStorage.
 */
const handleToggleDark = () => {
    const html = document.documentElement;

    // Primero alterna en PrimeVue
    toggleDarkMode();

    // Luego ajusta las clases del DOM según el nuevo estado
    const newTheme = isDarkTheme.value ? 'light' : 'dark'; // valor antes del cambio

    if (newTheme === 'dark') {
        html.classList.add('app-dark');
        html.style.colorScheme = 'dark';
        localStorage.setItem('theme', 'dark');
    } else {
        html.classList.remove('app-dark');
        html.style.colorScheme = 'light';
        localStorage.setItem('theme', 'light');
    }
};

/**
 * Al montar, aplica el tema guardado previamente.
 */
onMounted(() => {
    const html = document.documentElement;
    const savedTheme = localStorage.getItem('theme');

    if (savedTheme === 'dark') {
        html.classList.add('app-dark');
        html.style.colorScheme = 'dark';
    } else {
        html.classList.remove('app-dark');
        html.style.colorScheme = 'light';
    }
});
</script>

<template>
    <div class="fixed flex gap-3 top-6 right-6 z-50">
        <!-- Botón de cambio de tema -->
        <Button
            type="button"
            @click="handleToggleDark"
            rounded
            outlined
            class="shadow-md"
            :icon="isDarkTheme ? 'pi pi-sun' : 'pi pi-moon'"
            :severity="isDarkTheme ? 'contrast' : 'secondary'"
            v-tooltip.bottom="isDarkTheme ? 'Modo Claro' : 'Modo Oscuro'"
        />

        <!-- Panel de configuración visual -->
        <div class="relative">
            <Button
                icon="pi pi-palette"
                rounded
                outlined
                class="shadow-md"
                v-styleclass="{
                    selector: '@next',
                    enterFromClass: 'hidden',
                    enterActiveClass: 'animate-scalein',
                    leaveToClass: 'hidden',
                    leaveActiveClass: 'animate-fadeout',
                    hideOnOutsideClick: true
                }"
                v-tooltip.bottom="'Configuración del Tema'"
            />
            <AppConfigurator />
        </div>
    </div>
</template>

<style scoped>
/* Animaciones suaves */
.animate-scalein {
    animation: scalein 0.15s ease-in-out;
}

.animate-fadeout {
    animation: fadeout 0.15s ease-in-out;
}

@keyframes scalein {
    0% {
        transform: scale(0.9);
        opacity: 0;
    }
    100% {
        transform: scale(1);
        opacity: 1;
    }
}

@keyframes fadeout {
    0% {
        opacity: 1;
    }
    100% {
        opacity: 0;
    }
}
</style>
