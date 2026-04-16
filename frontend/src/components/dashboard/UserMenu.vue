<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { buildFotoURL } from '@/utils/fotoUrl.js';
import authService from '@/service/authService';

const router = useRouter();
const userStore = useUserStore();

const menuActive = ref(false);
const menuRef = ref(null);
const imageError = ref(false);

onMounted(async () => {
    if (!userStore.id) {
        await userStore.fetchUser();
    }
    document.addEventListener('click', onOutsideClick);
});

onBeforeUnmount(() => {
    document.removeEventListener('click', onOutsideClick);
});

const fotoUrl = computed(() => {
    if (imageError.value) return null;
    if (userStore.foto) {
        return buildFotoURL(userStore.foto, userStore.fotoVersion);
    }
    return null;
});

const inicial = computed(() => (userStore.nombre ? userStore.nombre.charAt(0).toUpperCase() : 'U'));

userStore.$subscribe((mutation) => {
    if (mutation.events.key === 'fotoVersion') {
        imageError.value = false;
    }
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

const irPerfil = () => {
    closeMenu();
    router.push('/mi-perfil');
};

const irPassword = () => {
    closeMenu();
    router.push('/cambiar-password');
};

const logout = async () => {
    userStore.startLogout();
    const logoutPromise = authService.logout().catch((e) => {
        console.error('Error cerrando sesion en backend:', e);
    });
    try {
        closeMenu();
        userStore.logout();
        await router.replace('/auth/login?logged_out=1');
    } finally {
        await logoutPromise;
    }
};
</script>

<template>
    <div class="relative" ref="menuRef">
        <button @click="toggleMenu" class="flex items-center gap-3 p-1.5 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition focus:outline-none cursor-pointer border-none bg-transparent">
            <div class="hidden md:flex flex-col items-end leading-tight text-right mr-1">
                <span class="font-bold text-sm text-color">{{ userStore.loggingOut ? 'Cerrando sesion...' : userStore.nombre || userStore.username || '' }}</span>
                <span class="text-[10px] uppercase tracking-wide text-muted-color font-semibold">{{ userStore.rol }}</span>
            </div>

            <div class="relative w-9 h-9">
                <img v-if="fotoUrl" :src="fotoUrl" alt="Perfil" class="w-full h-full rounded-full object-cover border border-gray-300 shadow-sm" @error="imageError = true" />

                <div v-else class="w-full h-full rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-sm select-none">
                    {{ inicial }}
                </div>

                <span class="absolute bottom-0 right-0 block h-2.5 w-2.5 rounded-full bg-green-500 ring-2 ring-white"></span>
            </div>
        </button>

        <transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
        >
            <div v-if="menuActive" class="absolute right-0 mt-2 w-64 origin-top-right bg-surface-0 dark:bg-surface-800 rounded-xl shadow-xl ring-1 ring-surface-200 dark:ring-surface-700 z-50 overflow-hidden">
                <div class="px-4 py-3 border-b border-surface-200 dark:border-surface-700 md:hidden bg-surface-50 dark:bg-surface-900">
                    <p class="text-sm font-medium text-color">{{ userStore.nombre }}</p>
                    <p class="text-xs text-muted-color truncate">{{ userStore.email }}</p>
                </div>

                <div class="py-1">
                    <button @click="irPerfil" class="flex w-full items-center px-4 py-2.5 text-sm text-color hover:bg-primary/10 transition text-left">
                        <i class="pi pi-user mr-3 text-primary"></i>
                        Mi Perfil
                    </button>

                    <button @click="irPassword" class="flex w-full items-center px-4 py-2.5 text-sm text-color hover:bg-primary/10 transition text-left">
                        <i class="pi pi-key mr-3 text-muted-color"></i>
                        Cambiar contrasena
                    </button>

                    <div class="border-t border-surface-200 dark:border-surface-700 my-1"></div>

                    <button @click="logout" class="flex w-full items-center px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition text-left">
                        <i class="pi pi-sign-out mr-3"></i>
                        Cerrar Sesion
                    </button>
                </div>
            </div>
        </transition>
    </div>
</template>
