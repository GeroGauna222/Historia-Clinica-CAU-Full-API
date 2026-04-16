<script setup>
import { ref, computed, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';
import comunicadoService from '@/service/comunicadoService';

import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const userStore = useUserStore();

const loading = ref(true);
const guardando = ref(false);
const comunicados = ref([]);
const form = ref({ titulo: '', contenido: '' });

const puedePublicar = computed(() => {
    const rol = (userStore.rol || '').toLowerCase().trim();
    return rol === 'director' || rol === 'administrativo';
});

function formatearFecha(value) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value || '';
    return d.toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' });
}

async function cargarComunicados() {
    loading.value = true;
    try {
        const res = await comunicadoService.listar();
        comunicados.value = res.data || [];
    } catch (err) {
        console.error('Error cargando comunicados:', err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudieron cargar los comunicados.', life: 4000 });
    } finally {
        loading.value = false;
    }
}

async function publicarComunicado() {
    if (!puedePublicar.value) return;
    const titulo = (form.value.titulo || '').trim();
    const contenido = (form.value.contenido || '').trim();

    if (!titulo || !contenido) {
        toast.add({ severity: 'warn', summary: 'Campos incompletos', detail: 'Ingrese titulo y contenido.', life: 3500 });
        return;
    }

    guardando.value = true;
    try {
        await comunicadoService.crear({ titulo, contenido });
        form.value = { titulo: '', contenido: '' };
        toast.add({ severity: 'success', summary: 'Publicado', detail: 'Comunicado publicado correctamente.', life: 3200 });
        await cargarComunicados();
    } catch (err) {
        console.error('Error publicando comunicado:', err);
        const detail = err?.response?.data?.error || 'No se pudo publicar el comunicado.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4200 });
    } finally {
        guardando.value = false;
    }
}

async function eliminarComunicado(comunicado) {
    if (!comunicado?.id) return;
    if (!confirm('Eliminar este comunicado?')) return;

    try {
        await comunicadoService.eliminar(comunicado.id);
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Comunicado eliminado.', life: 2800 });
        await cargarComunicados();
    } catch (err) {
        console.error('Error eliminando comunicado:', err);
        const detail = err?.response?.data?.error || 'No se pudo eliminar el comunicado.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4200 });
    }
}

onMounted(async () => {
    await cargarComunicados();
});
</script>

<template>
    <div class="p-6 md:p-8 max-w-5xl mx-auto space-y-6">
        <Toast />

        <div>
            <h1 class="text-3xl font-bold text-gray-800 dark:text-white">Comunicados</h1>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Avisos institucionales para todo el equipo.</p>
        </div>

        <Card v-if="puedePublicar" class="border border-cyan-100 dark:border-slate-700">
            <template #title>Nuevo comunicado</template>
            <template #content>
                <div class="space-y-3">
                    <InputText v-model="form.titulo" class="w-full" placeholder="Titulo" />
                    <Textarea v-model="form.contenido" rows="5" class="w-full" placeholder="Escriba el comunicado" autoResize />
                    <div class="flex justify-end">
                        <Button label="Publicar" icon="pi pi-send" :loading="guardando" @click="publicarComunicado" />
                    </div>
                </div>
            </template>
        </Card>

        <div v-if="loading" class="text-sm text-gray-500">Cargando comunicados...</div>

        <div v-else-if="comunicados.length === 0" class="text-sm text-gray-500 dark:text-gray-400 bg-white dark:bg-slate-900 border border-dashed border-gray-300 dark:border-slate-700 rounded-xl p-6 text-center">
            No hay comunicados publicados por el momento.
        </div>

        <div v-else class="space-y-4">
            <Card v-for="c in comunicados" :key="c.id" class="border border-gray-100 dark:border-slate-700">
                <template #title>
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{{ c.titulo }}</h2>
                            <p class="text-xs text-gray-500 mt-1">{{ c.autor_nombre }} ({{ c.autor_rol }}) - {{ formatearFecha(c.creado_en) }}</p>
                        </div>
                        <Button v-if="c.puede_eliminar" icon="pi pi-trash" text severity="danger" @click="eliminarComunicado(c)" />
                    </div>
                </template>
                <template #content>
                    <p class="whitespace-pre-line text-sm text-gray-700 dark:text-gray-200">{{ c.contenido }}</p>
                </template>
            </Card>
        </div>
    </div>
</template>
