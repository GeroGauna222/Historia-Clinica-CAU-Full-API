<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { usePacientesPresentes } from '@/layout/composables/usePacientesPresentes';

const router = useRouter();
const { presentes, cantidadPresentes, iniciarPolling, detenerPolling } = usePacientesPresentes();

const menuActive = ref(false);
const menuRef = ref(null);

onMounted(() => {
    iniciarPolling();
    document.addEventListener('click', onOutsideClick);
});

onBeforeUnmount(() => {
    detenerPolling();
    document.removeEventListener('click', onOutsideClick);
});

const toggleMenu = () => {
    menuActive.value = !menuActive.value;
};

const closeMenu = () => {
    menuActive.value = false;
};

const onOutsideClick = (event) => {
    if (menuRef.value && !menuRef.value.contains(event.target)) {
        closeMenu();
    }
};

const irAgenda = () => {
    closeMenu();
    router.push('/turnos');
};

function formatoHora(isoString) {
    if (!isoString) return '';
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
}
</script>

<template>
    <div class="relative" ref="menuRef">
        <button
            type="button"
            class="layout-topbar-action relative flex items-center justify-center p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition focus:outline-none border-none bg-transparent cursor-pointer"
            :class="{ '!text-emerald-600': cantidadPresentes > 0 }"
            title="Pacientes en recepción"
            @click="toggleMenu"
        >
            <i class="pi pi-user-check text-lg"></i>
            <span
                v-if="cantidadPresentes > 0"
                class="absolute -top-1 -right-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[11px] font-bold text-white shadow-sm ring-2 ring-white dark:ring-surface-900 animate-pulse"
            >
                {{ cantidadPresentes }}
            </span>
        </button>

        <transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
        >
            <div v-if="menuActive" class="absolute right-0 mt-2 w-80 max-w-[90vw] origin-top-right bg-surface-0 dark:bg-surface-800 rounded-xl shadow-xl ring-1 ring-surface-200 dark:ring-surface-700 z-50 overflow-hidden">
                <div class="px-4 py-3 border-b border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <i class="pi pi-building text-emerald-600"></i>
                        <span class="font-semibold text-sm text-color">Recepción / Sala de Espera</span>
                    </div>
                    <span v-if="cantidadPresentes > 0" class="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 font-semibold px-2 py-0.5 rounded-full">
                        {{ cantidadPresentes }} presente{{ cantidadPresentes > 1 ? 's' : '' }}
                    </span>
                </div>

                <div class="max-h-72 overflow-y-auto divide-y divide-surface-100 dark:divide-surface-700/50">
                    <div v-if="cantidadPresentes === 0" class="p-5 text-center text-sm text-muted-color">
                        <i class="pi pi-check-circle text-2xl text-surface-400 block mb-2"></i>
                        No hay pacientes esperando en recepción.
                    </div>

                    <div v-for="p in presentes" :key="p.id" class="p-3 hover:bg-surface-50 dark:hover:bg-surface-700/40 transition cursor-pointer" @click="irAgenda">
                        <div class="flex items-start justify-between gap-2">
                            <div>
                                <p class="text-sm font-semibold text-color leading-tight">{{ p.paciente }}</p>
                                <p v-if="p.dni" class="text-xs text-muted-color">DNI: {{ p.dni }}</p>
                            </div>
                            <span class="text-xs font-mono font-medium text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60 px-1.5 py-0.5 rounded">
                                {{ formatoHora(p.start) }}
                            </span>
                        </div>
                        <p v-if="p.motivo" class="text-xs text-muted-color mt-1 truncate"><span class="font-medium text-surface-600 dark:text-surface-300">Motivo:</span> {{ p.motivo }}</p>
                    </div>
                </div>

                <div class="p-2 border-t border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 text-center">
                    <button type="button" class="w-full text-xs font-semibold text-primary hover:underline py-1.5 focus:outline-none cursor-pointer border-none bg-transparent" @click="irAgenda">Ver agenda de turnos &rarr;</button>
                </div>
            </div>
        </transition>
    </div>
</template>
