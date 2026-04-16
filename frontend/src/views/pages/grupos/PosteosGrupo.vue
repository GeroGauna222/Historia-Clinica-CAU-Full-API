<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import api from '@/api/axios';
import grupoPosteosService from '@/service/grupoPosteosService';

import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const grupoId = Number(route.params.grupoId);
const grupo = ref(null);
const posteos = ref([]);
const loading = ref(true);
const guardando = ref(false);
const accesoDenegado = ref(false);

const form = ref({ titulo: '', contenido: '' });

const puedePostear = computed(() => Boolean(userStore.id));

function formatearFecha(value) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value || '';
    return d.toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' });
}

async function cargarContexto() {
    try {
        const [resGrupo, resPosteos] = await Promise.all([api.get(`/grupos/${grupoId}`, { withCredentials: true }), grupoPosteosService.listar(grupoId)]);
        grupo.value = resGrupo.data;
        posteos.value = resPosteos.data || [];
        accesoDenegado.value = false;
    } catch (err) {
        console.error('Error cargando posteos de grupo:', err);
        if (err?.response?.status === 403) {
            accesoDenegado.value = true;
            return;
        }
        const detail = err?.response?.data?.error || 'No se pudo cargar la informacion del grupo.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4200 });
    } finally {
        loading.value = false;
    }
}

async function publicarPosteo() {
    if (!puedePostear.value) return;

    const contenido = (form.value.contenido || '').trim();
    if (!contenido) {
        toast.add({ severity: 'warn', summary: 'Contenido vacio', detail: 'Escriba un mensaje para publicar.', life: 3500 });
        return;
    }

    guardando.value = true;
    try {
        await grupoPosteosService.crear(grupoId, { titulo: (form.value.titulo || '').trim(), contenido });
        form.value = { titulo: '', contenido: '' };
        toast.add({ severity: 'success', summary: 'Publicado', detail: 'Posteo publicado en el grupo.', life: 3000 });
        await cargarContexto();
    } catch (err) {
        console.error('Error publicando posteo:', err);
        const detail = err?.response?.data?.error || 'No se pudo publicar el posteo.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4200 });
    } finally {
        guardando.value = false;
    }
}

async function eliminarPosteo(posteo) {
    if (!posteo?.id) return;
    if (!confirm('Eliminar este posteo?')) return;

    try {
        await grupoPosteosService.eliminar(grupoId, posteo.id);
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Posteo eliminado.', life: 2800 });
        await cargarContexto();
    } catch (err) {
        console.error('Error eliminando posteo:', err);
        const detail = err?.response?.data?.error || 'No se pudo eliminar el posteo.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4200 });
    }
}

onMounted(async () => {
    await cargarContexto();
});
</script>

<template>
    <div class="p-6 md:p-8 max-w-5xl mx-auto space-y-6">
        <Toast />

        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white">Posteos de Grupo</h1>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ grupo?.nombre || 'Grupo' }} - Comunicacion interna del equipo.</p>
            </div>
            <Button label="Volver a grupos" icon="pi pi-arrow-left" text @click="router.push('/grupos')" />
        </div>

        <div v-if="loading" class="text-sm text-gray-500">Cargando posteos...</div>

        <div v-else-if="accesoDenegado" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl p-4">No tiene permisos para ver los posteos de este grupo.</div>

        <template v-else>
            <Card v-if="puedePostear" class="border border-cyan-100 dark:border-slate-700">
                <template #title>Nuevo posteo</template>
                <template #content>
                    <div class="space-y-3">
                        <InputText v-model="form.titulo" class="w-full" placeholder="Titulo (opcional)" />
                        <Textarea v-model="form.contenido" rows="4" class="w-full" placeholder="Escriba un mensaje para el grupo" autoResize />
                        <div class="flex justify-end">
                            <Button label="Publicar" icon="pi pi-send" :loading="guardando" @click="publicarPosteo" />
                        </div>
                    </div>
                </template>
            </Card>

            <div v-if="posteos.length === 0" class="text-sm text-gray-500 dark:text-gray-400 bg-white dark:bg-slate-900 border border-dashed border-gray-300 dark:border-slate-700 rounded-xl p-6 text-center">Todavia no hay posteos en este grupo.</div>

            <div v-else class="space-y-4">
                <Card v-for="p in posteos" :key="p.id" class="border border-gray-100 dark:border-slate-700">
                    <template #title>
                        <div class="flex items-start justify-between gap-3">
                            <div>
                                <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100">{{ p.titulo || 'Posteo del equipo' }}</h2>
                                <p class="text-xs text-gray-500 mt-1">{{ p.autor_nombre }} ({{ p.autor_rol }}) - {{ formatearFecha(p.creado_en) }}</p>
                            </div>
                            <Button v-if="p.puede_eliminar" icon="pi pi-trash" text severity="danger" @click="eliminarPosteo(p)" />
                        </div>
                    </template>
                    <template #content>
                        <p class="whitespace-pre-line text-sm text-gray-700 dark:text-gray-200">{{ p.contenido }}</p>
                    </template>
                </Card>
            </div>
        </template>
    </div>
</template>
