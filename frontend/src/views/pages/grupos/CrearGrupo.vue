<script setup>
import { ref, onMounted } from 'vue';
import api from '@/api/axios';

// Imports de PrimeVue
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import MultiSelect from 'primevue/multiselect';

const grupo = ref({
    nombre: '',
    descripcion: '',
    color: '#3B82F6' // Un azul por defecto más bonito
});

const usuarios = ref([]);
const miembrosSeleccionados = ref([]); // MultiSelect guardará un array de IDs gracias a optionValue="id"
const mensaje = ref('');
const error = ref('');
const loading = ref(false);

// ✅ Cargar usuarios disponibles (SIN FILTROS)
onMounted(async () => {
    try {
        const res = await api.get('/usuarios', { withCredentials: true });
        // 👇 CORRECCIÓN: Asignamos directamente todos, sin .filter()
        usuarios.value = res.data || [];
    } catch (err) {
        console.error('Error cargando usuarios:', err);
    }
});

async function crearGrupo() {
    mensaje.value = '';
    error.value = '';
    loading.value = true;

    try {
        // 1️⃣ Crear grupo
        const resGrupo = await api.post('/grupos', grupo.value, { withCredentials: true });
        const grupoId = resGrupo.data.id;

        // 2️⃣ Agregar miembros seleccionados
        if (miembrosSeleccionados.value.length > 0) {
            for (const usuarioId of miembrosSeleccionados.value) {
                await api.post(`/grupos/${grupoId}/miembros`, { usuario_id: usuarioId }, { withCredentials: true });
            }
        }

        mensaje.value = '✅ Grupo creado y miembros asignados correctamente';

        // Resetear formulario
        grupo.value = { nombre: '', descripcion: '', color: '#3B82F6' };
        miembrosSeleccionados.value = [];
    } catch (err) {
        console.error('Error creando grupo:', err);
        error.value = err.response?.data?.error || 'Error al crear el grupo.';
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="flex justify-center items-start p-6 md:p-8">
        <div class="bg-white dark:bg-[#1e1e1e] shadow-xl rounded-2xl p-8 w-full max-w-3xl transition-colors">
            <div class="text-center mb-8">
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white mb-2">Crear Grupo Profesional</h1>

                <p class="text-gray-500 dark:text-gray-400">Agrupa profesionales por especialidad para gestionar sus agendas</p>
            </div>

            <form @submit.prevent="crearGrupo" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="md:col-span-3 flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> Nombre del grupo </label>
                        <InputText v-model="grupo.nombre" placeholder="Ej: Kinesiología, Pediatría..." class="w-full" required />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> Color </label>
                        <div class="flex items-center h-full">
                            <input v-model="grupo.color" type="color" class="w-full h-[42px] p-1 bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer" title="Elige un color identificativo" />
                        </div>
                    </div>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> Descripción </label>
                    <Textarea v-model="grupo.descripcion" rows="3" placeholder="Describe el propósito de este grupo..." class="w-full" autoResize />
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-user-plus mr-1 text-primary"></i> Asignar Miembros </label>
                    <MultiSelect v-model="miembrosSeleccionados" :options="usuarios" optionLabel="nombre" optionValue="id" placeholder="Buscar y seleccionar profesionales..." display="chip" filter class="w-full" :maxSelectedLabels="3">
                        <template #option="slotProps">
                            <div class="flex flex-col">
                                <span class="font-medium">{{ slotProps.option.nombre }}</span>
                                <span class="text-xs text-gray-500 capitalize">{{ slotProps.option.rol }}</span>
                            </div>
                        </template>
                    </MultiSelect>
                    <small class="text-gray-500 dark:text-gray-400"> Puedes buscar por nombre. Los seleccionados aparecerán como etiquetas. </small>
                </div>

                <div class="flex justify-center pt-4">
                    <Button type="submit" label="Guardar Grupo" icon="pi pi-check" class="w-full md:w-auto px-8 py-3 font-bold shadow-lg" :loading="loading" />
                </div>
            </form>

            <div v-if="mensaje" class="mt-6 p-3 rounded-lg bg-green-100 text-green-700 text-center font-medium border border-green-200"><i class="pi pi-check-circle mr-2"></i> {{ mensaje }}</div>
            <div v-if="error" class="mt-6 p-3 rounded-lg bg-red-100 text-red-700 text-center font-medium border border-red-200"><i class="pi pi-exclamation-circle mr-2"></i> {{ error }}</div>
        </div>
    </div>
</template>
