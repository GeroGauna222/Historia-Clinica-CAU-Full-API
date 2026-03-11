<script setup>
import { computed } from 'vue';
import AppMenuItem from './AppMenuItem.vue';
import authService from '@/service/authService';
import { useRouter } from 'vue-router';
import { useSession } from './composables/useSession';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const { clearUser } = useSession();
const userStore = useUserStore(); // 3. Instanciar el store

async function handleLogout() {
    try {
        await authService.logout();
    } catch (e) {
        console.error('Error cerrando sesión:', e);
    } finally {
        clearUser();
        router.push('/auth/login');
    }
}

// 4. Cambiamos 'ref' por 'computed' para poder usar lógica dinámica
const model = computed(() => {
    // Normalizamos el rol para evitar errores de mayúsculas/espacios
    const esDirector = userStore.rol?.toLowerCase().trim() === 'director';

    return [
        {
            label: 'Inicio',
            items: [{ label: 'Dashboard', icon: 'pi pi-fw pi-home', to: '/' }]
        },
        {
            label: 'Pacientes',
            items: [
                { label: 'Listado', icon: 'pi pi-fw pi-users', to: '/pacientes' },
                { label: 'Registrar', icon: 'pi pi-fw pi-user-plus', to: '/pacientes/registrar' }
            ]
        },
        {
            label: 'Historias Clínicas',
            items: [{ label: 'Ver Historias', icon: 'pi pi-fw pi-book', to: '/historias' }]
        },
        {
            label: 'Turnos',
            items: [
                { label: 'Agenda', icon: 'pi pi-fw pi-calendar', to: '/turnos' },
                { label: 'Nuevo Turno', icon: 'pi pi-fw pi-calendar-plus', to: '/turnos/nuevo' },
                { label: 'Disponibilidad', icon: 'pi pi-fw pi-clock', to: '/disponibilidad' },
                // Configuración solo visible para profesionales (opcional, por si quieres ocultarlo a admin)
                {
                    label: 'Configuración de Turnos',
                    icon: 'pi pi-clock',
                    to: '/turnos/configuracion',
                    visible: ['profesional', 'director', 'area'].includes(userStore.rol)
                }
            ]
        },

        // 🔒 SECCIÓN USUARIOS PROTEGIDA
        {
            label: 'Usuarios',
            visible: esDirector, // <--- ESTA ES LA CLAVE: Solo se muestra si es true
            items: [
                { label: 'Listado', icon: 'pi pi-fw pi-id-card', to: '/usuarios' },
                { label: 'Crear Usuario', icon: 'pi pi-fw pi-user-edit', to: '/usuarios/crear' },
                { label: 'Inactivos', icon: 'pi pi-fw pi-user-minus', to: '/usuarios/inactivos' }
            ]
        },

        {
            label: 'Agendas Grupales',
            items: [
                { label: 'Ver grupos', icon: 'pi pi-fw pi-users', to: '/grupos' },
                { label: 'Crear grupo', icon: 'pi pi-plus', to: '/grupos/crear', visible: esDirector }
            ]
        },
        {
            label: 'Blockchain',
            items: [{ label: 'Verificar Hash', icon: 'pi pi-fw pi-search', to: '/blockchain/verificar' }]
        },
        {
            label: 'Salir',
            items: [{ label: 'Cerrar sesión', icon: 'pi pi-fw pi-sign-out', command: handleLogout }]
        }
    ];
});
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="i">
            <app-menu-item v-if="!item.separator && item.visible !== false" :item="item" :index="i" />
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>
