<script setup>
import { ref, onMounted } from 'vue';
import api from '@/api/axios';
import { useRoute, useRouter } from 'vue-router';

import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import MultiSelect from 'primevue/multiselect';

const route = useRoute();
const router = useRouter();
const grupoId = route.params.id;

const grupo = ref({ nombre: '', descripcion: '', color: '#00936B', es_rehabilitacion: false });
const usuariosDisponibles = ref([]);
const miembrosOriginalesIds = ref([]);
const miembrosSeleccionadosIds = ref([]);

const cargando = ref(true);
const guardando = ref(false);
const mensaje = ref('');
const error = ref('');

onMounted(async () => {
    try {
        const [resUsuarios, resGrupo, resMiembros] = await Promise.all([api.get('/usuarios', { withCredentials: true }), api.get(`/grupos/${grupoId}`, { withCredentials: true }), api.get(`/grupos/${grupoId}/miembros`, { withCredentials: true })]);

        usuariosDisponibles.value = resUsuarios.data || [];
        grupo.value = {
            nombre: resGrupo.data?.nombre || '',
            descripcion: resGrupo.data?.descripcion || '',
            color: resGrupo.data?.color || '#00936B',
            es_rehabilitacion: Boolean(resGrupo.data?.es_rehabilitacion)
        };

        const ids = (resMiembros.data || []).map((m) => m.id);
        miembrosSeleccionadosIds.value = [...ids];
        miembrosOriginalesIds.value = [...ids];
    } catch (err) {
        console.error('Error cargando datos:', err);
        error.value = 'No se pudieron cargar los datos del grupo.';
    } finally {
        cargando.value = false;
    }
});

async function guardarCambios() {
    mensaje.value = '';
    error.value = '';
    guardando.value = true;

    try {
        await api.put(`/grupos/${grupoId}`, grupo.value, { withCredentials: true });

        const actuales = new Set(miembrosSeleccionadosIds.value);
        const originales = new Set(miembrosOriginalesIds.value);
        const paraAgregar = [...actuales].filter((id) => !originales.has(id));
        const paraBorrar = [...originales].filter((id) => !actuales.has(id));

        const promesas = [];
        for (const uid of paraAgregar) promesas.push(api.post(`/grupos/${grupoId}/miembros`, { usuario_id: uid }, { withCredentials: true }));
        for (const uid of paraBorrar) promesas.push(api.delete(`/grupos/${grupoId}/miembros/${uid}`, { withCredentials: true }));
        await Promise.all(promesas);

        miembrosOriginalesIds.value = [...miembrosSeleccionadosIds.value];
        mensaje.value = 'Cambios guardados correctamente';
    } catch (err) {
        console.error('Error guardando cambios:', err);
        error.value = err.response?.data?.error || 'Error al guardar cambios.';
    } finally {
        guardando.value = false;
    }
}
</script>

<template>
    <div class="flex justify-center items-start p-6 md:p-8">
        <div class="bg-surface-0 dark:bg-surface-900 shadow-xl rounded-2xl p-8 w-full max-w-3xl transition-colors">
            <div class="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
                <Button label="Volver" icon="pi pi-arrow-left" text severity="secondary" @click="router.push('/grupos')" />
                <div class="text-center md:text-right">
                    <h1 class="text-3xl font-bold text-primary mb-1">Editar Grupo</h1>
                </div>
            </div>

            <div v-if="cargando" class="flex flex-col items-center py-10">
                <i class="pi pi-spin pi-spinner text-4xl text-primary mb-2"></i>
                <p class="text-gray-500">Cargando datos del grupo...</p>
            </div>

            <form v-else @submit.prevent="guardarCambios" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="md:col-span-3 flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200">Nombre del grupo</label>
                        <InputText v-model="grupo.nombre" class="w-full" required />
                    </div>
                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200">Color</label>
                        <input v-model="grupo.color" type="color" class="w-full h-[42px] p-1 bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer" />
                    </div>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200">Descripcion</label>
                    <Textarea v-model="grupo.descripcion" rows="3" class="w-full" autoResize />
                </div>

                <label class="flex items-center gap-2">
                    <input v-model="grupo.es_rehabilitacion" type="checkbox" />
                    <span class="font-semibold text-gray-700 dark:text-gray-200">Grupo de Rehabilitacion</span>
                </label>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200">Miembros del grupo</label>
                    <MultiSelect v-model="miembrosSeleccionadosIds" :options="usuariosDisponibles" optionLabel="nombre" optionValue="id" placeholder="Gestionar miembros..." display="chip" filter class="w-full" :maxSelectedLabels="10">
                        <template #option="slotProps">
                            <div class="flex flex-col">
                                <span class="font-medium">{{ slotProps.option.nombre }}</span>
                                <span class="text-xs text-gray-500 capitalize">{{ slotProps.option.rol }}</span>
                            </div>
                        </template>
                    </MultiSelect>
                </div>

                <div class="flex justify-center pt-6 border-t border-gray-100 dark:border-gray-800">
                    <Button type="submit" label="Guardar Cambios" icon="pi pi-save" class="w-full md:w-auto px-8 py-3 font-bold shadow-lg" :loading="guardando" />
                </div>
            </form>

            <div v-if="mensaje" class="mt-6 p-3 rounded-lg bg-green-100 text-green-700 text-center font-medium border border-green-200">{{ mensaje }}</div>
            <div v-if="error" class="mt-6 p-3 rounded-lg bg-red-100 text-red-700 text-center font-medium border border-red-200">{{ error }}</div>
        </div>
    </div>
</template>
