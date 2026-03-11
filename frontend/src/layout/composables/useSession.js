// src/layout/composables/useSession.js
import { ref, computed } from 'vue';
import { useUserStore } from '@/stores/user';
import { on } from '@/utils/eventBus';

// Estas refs globales están OK:
const loading = ref(false);
const error = ref('');

export function useSession() {
    // ⬅️ El store SOLO debe obtenerse dentro de la función,
    //    donde ya existe Pinia y es seguro usarlo.
    const userStore = useUserStore();

    // Usuario derivado del store
    const user = computed(() => {
        if (!userStore.id) return null;

        return {
            id: userStore.id,
            nombre: userStore.nombre || userStore.username || 'Usuario',
            username: userStore.username || '',
            email: userStore.email || '',
            rol: userStore.rol || '',
            foto: userStore.foto || null
        };
    });

    async function loadCurrentUser(force = false) {
        if (userStore.id && !force) return user.value;

        loading.value = true;
        error.value = '';

        try {
            await userStore.fetchUser();
            return user.value;
        } catch (e) {
            console.warn('⚠️ No se pudo obtener el usuario actual:', e);
            error.value = e?.message || 'No se pudo obtener el usuario';
            return null;
        } finally {
            loading.value = false;
        }
    }

    function clearUser() {
        userStore.logout();
    }

    // Eventos globales
    on('user:updated', (data) => {
        console.log('🔔 user:updated recibido en useSession', data);
    });

    return { user, loading, error, loadCurrentUser, clearUser };
}
