<script setup>
import { computed, onMounted } from 'vue';
import { useSession } from '@/layout/composables/useSession';
import { buildFotoURL } from '@/utils/fotoUrl.js';

const { user, loading, loadCurrentUser } = useSession();

onMounted(() => {
    loadCurrentUser(true);
});

/* Iniciales si no hay foto */
const initials = computed(() => {
    const n = user.value?.nombre?.trim() || user.value?.username || '';
    if (!n) return '?';
    const parts = n.split(/\s+/).slice(0, 2);
    return parts.map((p) => p[0]?.toUpperCase()).join('');
});

/* URL de la foto reutilizando helper */
const fotoURL = computed(() => buildFotoURL(user.value?.foto));

/* Clases por rol */
const roleClass = computed(() => {
    const r = (user.value?.rol || '').toLowerCase();

    switch (r) {
        case 'director':
            return 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900 dark:border-emerald-700 dark:text-emerald-200';
        case 'administrativo':
            return 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900 dark:border-indigo-700 dark:text-indigo-200';
        case 'profesional':
            return 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900 dark:border-amber-700 dark:text-amber-200';
        default:
            return 'bg-gray-50 border-gray-200 text-gray-700 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300';
    }
});
</script>

<template>
    <div class="flex items-center gap-3">
        <!-- Placeholder mientras carga -->
        <div v-if="loading" class="flex items-center gap-2">
            <div class="animate-pulse w-8 h-8 rounded-full bg-gray-300/60"></div>
            <div class="animate-pulse h-4 w-28 rounded bg-gray-300/60"></div>
            <div class="animate-pulse h-5 w-16 rounded bg-gray-300/60"></div>
        </div>

        <!-- Usuario autenticado -->
        <template v-else-if="user">
            <div class="text-right leading-tight hidden sm:block">
                <div class="font-medium text-sm text-gray-800 dark:text-gray-100">
                    {{ user.nombre }}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{{ user.username }}</div>
            </div>

            <!-- Avatar -->
            <div class="w-8 h-8 rounded-full overflow-hidden flex items-center justify-center bg-sky-600 text-white font-semibold" :title="user.email || user.username">
                <!-- Foto -->
                <img v-if="fotoURL" :src="fotoURL" class="w-full h-full object-cover" alt="perfil" />

                <!-- Iniciales si no hay foto -->
                <span v-else>{{ initials }}</span>
            </div>

            <!-- Rol -->
            <span class="px-2 py-1 text-xs rounded-full border transition-colors" :class="roleClass" :title="`Rol: ${user.rol}`">
                {{ user.rol || '—' }}
            </span>
        </template>

        <!-- Sin usuario -->
        <template v-else>
            <span class="text-sm text-gray-500 dark:text-gray-400">No autenticado</span>
        </template>
    </div>
</template>
