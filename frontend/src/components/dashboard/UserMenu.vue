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
const imageError = ref(false); // Variable para saber si la imagen falló

onMounted(async () => {
    if (!userStore.id) {
        await userStore.fetchUser();
    }
    document.addEventListener('click', onOutsideClick);
});

onBeforeUnmount(() => {
    document.removeEventListener('click', onOutsideClick);
});

// URL de la foto (escuchando la versión para romper caché)
const fotoUrl = computed(() => {
    // Si hubo error de carga, devolvemos null para mostrar la inicial
    if (imageError.value) return null;

    if (userStore.foto) {
        return buildFotoURL(userStore.foto, userStore.fotoVersion);
    }
    return null;
});

// Inicial del nombre
const inicial = computed(() => (userStore.nombre ? userStore.nombre.charAt(0).toUpperCase() : 'U'));

// Resetear el error si cambia la versión de la foto (nueva subida)
userStore.$subscribe((mutation) => {
    if (mutation.events.key === 'fotoVersion') {
        imageError.value = false;
    }
});

// --- ACCIONES ---
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
    try {
        await authService.logout();
    } catch (e) {
        console.error('Error cerrando sesión en backend:', e);
    } finally {
        userStore.logout();
        closeMenu();
        router.push('/auth/login');
    }
};
</script>

<template>
    <div class="relative" ref="menuRef">
        <button @click="toggleMenu" class="flex items-center gap-3 p-1.5 rounded-lg hover:bg-gray-100 transition focus:outline-none focus:ring-2 focus:ring-blue-100 cursor-pointer border-none bg-transparent">
            <div class="hidden md:flex flex-col items-end leading-tight text-right mr-1">
                <span class="font-bold text-sm text-gray-700">{{ userStore.nombre || 'Usuario' }}</span>
                <span class="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">{{ userStore.rol }}</span>
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
            <div v-if="menuActive" class="absolute right-0 mt-2 w-64 origin-top-right bg-white rounded-xl shadow-xl ring-1 ring-black ring-opacity-5 z-50 overflow-hidden">
                <div class="px-4 py-3 border-b border-gray-100 md:hidden bg-gray-50">
                    <p class="text-sm font-medium text-gray-900">{{ userStore.nombre }}</p>
                    <p class="text-xs text-gray-500 truncate">{{ userStore.email }}</p>
                </div>

                <div class="py-1">
                    <button @click="irPerfil" class="flex w-full items-center px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition text-left">
                        <i class="pi pi-user mr-3 text-blue-500"></i>
                        Mi Perfil
                    </button>

                    <button @click="irPassword" class="flex w-full items-center px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition text-left">
                        <i class="pi pi-key mr-3 text-gray-400"></i>
                        Cambiar contraseña
                    </button>

                    <div class="border-t border-gray-100 my-1"></div>

                    <button @click="logout" class="flex w-full items-center px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 hover:text-red-700 transition text-left">
                        <i class="pi pi-sign-out mr-3"></i>
                        Cerrar Sesión
                    </button>
                </div>
            </div>
        </transition>
    </div>
</template>
