<script setup>
import { ref, onMounted } from 'vue';
import api from '@/api/axios';
import { useRouter } from 'vue-router';

// Imports PrimeVue
import Button from 'primevue/button';
import Card from 'primevue/card';
import Dialog from 'primevue/dialog';
import Skeleton from 'primevue/skeleton';
import Select from 'primevue/select';
import Avatar from 'primevue/avatar';

const router = useRouter();
const grupos = ref([]);
const loading = ref(true);

// Modal
const modalMiembros = ref(false);
const grupoActual = ref(null);
const miembros = ref([]);
const cargandoMiembros = ref(false);

// Agregar miembros
const usuarios = ref([]);
const nuevoMiembro = ref('');

onMounted(async () => {
    try {
        const res = await api.get('/grupos', { withCredentials: true });
        grupos.value = res.data || [];
    } catch (err) {
        console.error('Error cargando grupos:', err);
    } finally {
        loading.value = false;
    }
});

function editarGrupo(grupo) {
    router.push({ name: 'EditarGrupo', params: { id: grupo.id } });
}

function crearGrupo() {
    router.push({ name: 'CrearGrupo' });
}

async function eliminar(grupo) {
    if (!confirm(`¿Eliminar el grupo "${grupo.nombre}"?`)) return;

    try {
        await api.delete(`/grupos/${grupo.id}`, { withCredentials: true });
        grupos.value = grupos.value.filter((g) => g.id !== grupo.id);
    } catch (err) {
        console.error('Error eliminando grupo:', err);
    }
}

async function verMiembros(grupo) {
    grupoActual.value = grupo;
    modalMiembros.value = true;
    cargandoMiembros.value = true;

    try {
        const [resMiembros, resUsuarios] = await Promise.all([api.get(`/grupos/${grupo.id}/miembros`, { withCredentials: true }), api.get('/usuarios', { withCredentials: true })]);

        // Lista de miembros actuales
        const miembrosActuales = resMiembros.data || [];
        miembros.value = miembrosActuales;

        // 🔓 CORRECCIÓN: Quitamos el filtro de 'profesional' o 'area'
        // Ahora solo ocultamos a los que YA son miembros del grupo
        const todosUsuarios = resUsuarios.data || [];

        usuarios.value = todosUsuarios.filter((u) => {
            const yaEsMiembro = miembrosActuales.some((m) => m.id === u.id);
            return !yaEsMiembro; // Si NO es miembro, lo mostramos para agregar
        });
    } catch (err) {
        console.error('Error cargando datos:', err);
    } finally {
        cargandoMiembros.value = false;
    }
}

async function agregarMiembro() {
    if (!nuevoMiembro.value) return;

    try {
        await api.post(`/grupos/${grupoActual.value.id}/miembros`, { usuario_id: nuevoMiembro.value }, { withCredentials: true });

        // Buscamos el usuario agregado en la lista 'usuarios' para pasarlo a 'miembros'
        const userIndex = usuarios.value.findIndex((u) => u.id === nuevoMiembro.value);

        if (userIndex !== -1) {
            // Lo agregamos a la lista visual de miembros
            miembros.value.push(usuarios.value[userIndex]);
            // Lo quitamos del desplegable para que no se pueda volver a agregar
            usuarios.value.splice(userIndex, 1);
        }

        nuevoMiembro.value = '';
    } catch (err) {
        console.error('Error agregando miembro:', err);
        // Sería bueno agregar un Toast aquí si tuvieras useToast importado
        alert('Error al agregar miembro: Verifique que sea Profesional o Área.');
    }
}

async function quitarMiembro(m) {
    if (!confirm(`¿Quitar a ${m.nombre}?`)) return;

    try {
        await api.delete(`/grupos/${grupoActual.value.id}/miembros/${m.id}`, { withCredentials: true });
        // Quitar de la lista visual de miembros
        miembros.value = miembros.value.filter((x) => x.id !== m.id);

        // (Opcional) Devolverlo a la lista de "disponibles" si cumple el rol
        if (['profesional', 'area'].includes(m.rol)) {
            usuarios.value.push(m);
            // Ordenar alfabéticamente para mantener orden
            usuarios.value.sort((a, b) => a.nombre.localeCompare(b.nombre));
        }
    } catch (err) {
        console.error('Error quitando miembro:', err);
    }
}

function verCalendario(grupo) {
    router.push({ name: 'CalendarioGrupo', params: { grupoId: grupo.id } });
}
</script>

<template>
    <div class="p-6 md:p-8 max-w-7xl mx-auto">
        <div class="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
            <h1 class="text-3xl font-bold text-gray-800 dark:text-white">Agendas Grupales</h1>

            <Button label="Nuevo Grupo" icon="pi pi-plus" @click="crearGrupo" raised />
        </div>

        <div v-if="loading" class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div v-for="i in 3" :key="i" class="p-4 border rounded-xl bg-white dark:bg-gray-800 shadow-sm">
                <Skeleton width="60%" height="1.5rem" class="mb-2"></Skeleton>
                <Skeleton width="100%" height="1rem" class="mb-4"></Skeleton>
                <div class="flex gap-2">
                    <Skeleton width="3rem" height="2rem"></Skeleton>
                    <Skeleton width="3rem" height="2rem"></Skeleton>
                </div>
            </div>
        </div>

        <div v-else-if="grupos.length === 0" class="text-center py-10">
            <i class="pi pi-folder-open text-6xl text-gray-300 dark:text-gray-600 mb-4"></i>
            <p class="text-gray-500 dark:text-gray-400 text-lg">No hay grupos registrados.</p>
            <Button label="Crear el primero" class="mt-4" text @click="crearGrupo" />
        </div>

        <div v-else class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <Card v-for="grupo in grupos" :key="grupo.id" class="shadow-md hover:shadow-lg transition-shadow border-l-4 overflow-hidden" :style="{ borderLeftColor: grupo.color }">
                <template #title>
                    <div class="flex justify-between items-start">
                        <span class="text-xl font-bold truncate" :title="grupo.nombre">{{ grupo.nombre }}</span>
                        <div class="flex gap-1">
                            <Button icon="pi pi-pencil" text rounded size="small" @click="editarGrupo(grupo)" v-tooltip.top="'Editar'" />
                            <Button icon="pi pi-trash" text rounded severity="danger" size="small" @click="eliminar(grupo)" v-tooltip.top="'Eliminar'" />
                        </div>
                    </div>
                </template>

                <template #content>
                    <p class="text-gray-600 dark:text-gray-300 text-sm h-10 line-clamp-2">
                        {{ grupo.descripcion || 'Sin descripción' }}
                    </p>
                </template>

                <template #footer>
                    <div class="flex flex-col gap-2 mt-2">
                        <Button label="Ver Miembros" icon="pi pi-users" severity="secondary" outlined class="w-full" @click="verMiembros(grupo)" />
                        <Button label="Ver Calendario" icon="pi pi-calendar" class="w-full" @click="verCalendario(grupo)" />
                    </div>
                </template>
            </Card>
        </div>

        <Dialog v-model:visible="modalMiembros" modal :header="`Miembros de ${grupoActual?.nombre}`" :style="{ width: '500px' }" class="p-fluid">
            <div v-if="cargandoMiembros" class="flex justify-center py-4">
                <i class="pi pi-spin pi-spinner text-3xl"></i>
            </div>

            <div v-else>
                <ul class="divide-y divide-gray-100 dark:divide-gray-700 mb-6">
                    <li v-for="m in miembros" :key="m.id" class="flex justify-between items-center py-3">
                        <div class="flex items-center gap-3">
                            <Avatar :label="m.nombre[0]" shape="circle" class="bg-blue-100 text-blue-600" />
                            <div class="flex flex-col">
                                <span class="font-medium text-gray-800 dark:text-gray-200">{{ m.nombre }}</span>
                                <span class="text-xs text-gray-500 capitalize">{{ m.rol }}</span>
                            </div>
                        </div>
                        <Button icon="pi pi-times" text rounded severity="danger" @click="quitarMiembro(m)" v-tooltip.left="'Quitar del grupo'" />
                    </li>
                    <li v-if="miembros.length === 0" class="text-center py-4 text-gray-500 text-sm">Este grupo aún no tiene miembros.</li>
                </ul>

                <div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-100 dark:border-gray-700">
                    <label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">Agregar profesional:</label>
                    <div class="flex gap-2">
                        <Select v-model="nuevoMiembro" :options="usuarios" optionLabel="nombre" optionValue="id" placeholder="Seleccionar..." class="w-full" filter />
                        <Button icon="pi pi-plus" @click="agregarMiembro" :disabled="!nuevoMiembro" />
                    </div>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<style scoped>
.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
