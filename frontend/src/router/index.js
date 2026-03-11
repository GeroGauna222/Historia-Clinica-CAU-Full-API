import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';
import { useUserStore } from '@/stores/user';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        // 🔐 Autenticación
        {
            path: '/auth/login',
            name: 'login',
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/logout',
            name: 'logout',
            component: () => import('@/views/pages/auth/Logout.vue')
        },
        {
            path: '/recuperar',
            name: 'RecuperarContraseña',
            component: () => import('@/views/pages/auth/RecoverPassword.vue')
        },
        {
            path: '/reset/:token',
            name: 'ResetContraseña',
            component: () => import('@/views/pages/auth/ResetPassword.vue')
        },
        // 🌐 App principal (protegida)
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '',
                    name: 'dashboard',
                    component: () => import('@/views/Dashboard.vue')
                },
                // 📌 Pacientes
                {
                    path: 'pacientes',
                    name: 'pacientes',
                    component: () => import('@/views/pages/historias/Pacientes.vue')
                },
                {
                    path: 'pacientes/registrar',
                    name: 'registrarPaciente',
                    component: () => import('@/views/pages/historias/RegistrarPaciente.vue')
                },
                {
                    path: 'pacientes/:id/editar',
                    name: 'editarPaciente',
                    component: () => import('@/views/pages/historias/EditarPaciente.vue')
                },
                {
                    path: 'historias',
                    name: 'historias',
                    component: () => import('@/views/pages/historias/BuscarHistorias.vue')
                },
                {
                    path: 'pacientes/:id/historias',
                    name: 'historiaPaciente',
                    component: () => import('@/views/pages/historias/HistoriaPaciente.vue'),
                    props: true
                },
                {
                    path: 'pacientes/:id/evolucion/:evoId',
                    name: 'evolucionDetalle',
                    component: () => import('@/views/pages/evolucion/EvolucionDetalle.vue'),
                    props: true
                },
                // 📌 Turnos
                {
                    path: 'turnos',
                    name: 'turnos',
                    component: () => import('@/views/pages/historias/Turnos.vue')
                },
                {
                    path: 'turnos/nuevo',
                    name: 'nuevoTurno',
                    component: () => import('@/views/pages/historias/NuevoTurno.vue')
                },
                {
                    path: 'turnos/configuracion',
                    name: 'configuracionTurnos',
                    component: () => import('@/views/pages/turnos/ConfiguracionTurnos.vue'),
                    // Permitimos a todos los que gestionan agenda
                    meta: { roles: ['profesional', 'director', 'area'] }
                },

                // 📌 Usuarios (🔒 SECCIÓN BLINDADA - SOLO DIRECTOR)
                {
                    path: 'usuarios',
                    name: 'usuarios',
                    component: () => import('@/views/pages/usuarios/Usuarios.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'usuarios/crear',
                    name: 'crearUsuario',
                    component: () => import('@/views/pages/usuarios/CrearUsuario.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'usuarios/inactivos',
                    name: 'usuariosInactivos',
                    component: () => import('@/views/pages/usuarios/UsuariosInactivos.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'usuarios/:id/editar',
                    name: 'editarUsuario',
                    component: () => import('@/views/pages/usuarios/EditarUsuario.vue'),
                    props: true,
                    meta: { roles: ['director'] }
                },

                // 📌 Perfil (Para todos)
                {
                    path: 'mi-perfil',
                    name: 'miPerfil',
                    component: () => import('@/views/pages/usuarios/MiPerfil.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: '/cambiar-password',
                    name: 'cambiarPassword',
                    component: () => import('@/views/pages/usuarios/CambiarPassword.vue'),
                    meta: { requiresAuth: true }
                },

                // 📌 Disponibilidades
                {
                    path: 'disponibilidad',
                    name: 'disponibilidadProfesional',
                    component: () => import('@/views/pages/disponibilidades/DisponibilidadProfesional.vue')
                },

                // 📌 Grupos
                {
                    path: 'grupos',
                    name: 'GruposProfesionales',
                    component: () => import('../views/pages/grupos/GruposProfesionales.vue'),
                    meta: { requiresAuth: true } // Listado visible para todos
                },
                {
                    path: 'calendario-grupo/:grupoId',
                    name: 'CalendarioGrupo',
                    component: () => import('../views/pages/turnos/CalendarioGrupo.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: 'grupos/crear',
                    name: 'CrearGrupo',
                    component: () => import('../views/pages/grupos/CrearGrupo.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'grupos/editar/:id',
                    name: 'EditarGrupo',
                    component: () => import('../views/pages/grupos/EditarGrupo.vue'),
                    props: true,
                    meta: { roles: ['director'] }
                },

                // 📌 Blockchain
                {
                    path: 'blockchain/verificar',
                    name: 'blockchainVerificar',
                    component: () => import('@/views/pages/historias/BlockchainVerificar.vue')
                }
            ]
        },

        // 🚫 Ruta no encontrada
        {
            path: '/:pathMatch(.*)*',
            name: 'notfound',
            component: () => import('@/views/pages/NotFound.vue')
        }
    ]
});

// 🛡️ Guard global para proteger rutas
router.beforeEach(async (to) => {
    const publicPages = ['/auth/login', '/recuperar', '/logout'];
    const isResetRoute = to.path.startsWith('/reset/');
    const authRequired = !publicPages.includes(to.path) && !isResetRoute;
    const userStore = useUserStore();
    const needsUser = authRequired || Boolean(to.meta.roles);

    // Si la ruta requiere usuario y no está cargado, validamos contra backend.
    if (needsUser && !userStore.id) {
        try {
            await userStore.fetchUser();
        } catch {
            if (authRequired) return '/auth/login';
        }
    }

    // Si requiere auth y no pudimos cargar sesión válida -> login
    if (authRequired && !userStore.id) {
        return '/auth/login';
    }

    // Si está logueado y va a login, redirigimos al inicio.
    if (to.path === '/auth/login' && userStore.id) {
        return '/';
    }

    // Validación de roles basada en estado del store (derivado de backend)
    if (to.meta.roles) {
        const userRole = (userStore.rol || '').toLowerCase().trim();

        // Si el rol del usuario NO está en la lista permitida de la ruta
        if (!to.meta.roles.includes(userRole)) {
            console.warn(`⛔ Acceso denegado a ${to.path}. Rol actual: ${userRole}`);
            return '/';
        }
    }

    return true;
});

export default router;
