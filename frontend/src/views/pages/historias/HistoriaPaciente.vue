<script setup>
import FileUpload from 'primevue/fileupload';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import historiaService from '@/service/historiaService';
import api from '@/api/axios';
import { useRouter } from 'vue-router';
import DatePicker from 'primevue/datepicker';
import { fechaBonitaClinica, fechaBonitaCompleta } from '@/utils/formatDate.js';
import { nextTick } from 'vue';
import { computed } from 'vue';

const route = useRoute();
const pacienteId = route.params.id;
const router = useRouter();
const apiBase = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

const toast = useToast();

const paciente = ref(null);
const historias = ref([]);
const evoluciones = ref([]);
const loading = ref(true);
const error = ref(null);

const showForm = ref(false);
const fecha = ref(new Date().toISOString().split('T')[0]);
const contenido = ref('');
const indicaciones = ref('');
const archivos = ref([]);
const fileUploader = ref(null);

// Control de qué año está abierto
const accordionAbierto = ref({});

/**
 * Agrupa evoluciones por año
 */
const evolucionesPorAño = computed(() => {
    const grupos = {};

    evoluciones.value.forEach((e) => {
        const fecha = new Date(e.fecha);
        const año = fecha.getFullYear();

        if (!grupos[año]) grupos[año] = [];
        grupos[año].push(e);
    });

    // Ordenar del año más reciente al más viejo
    return Object.keys(grupos)
        .sort((a, b) => b - a)
        .map((año) => ({
            año,
            items: grupos[año]
        }));
});

/**
 * Carga los datos del paciente, sus historias y evoluciones
 */
const fetchHistoria = async () => {
    try {
        loading.value = true;

        const resPaciente = await api.get(`/pacientes/${pacienteId}`, { withCredentials: true });
        paciente.value = resPaciente.data;

        const resHistorias = await historiaService.getHistorias(pacienteId);
        historias.value = resHistorias.data;

        const resEvoluciones = await api.get(`/pacientes/${pacienteId}/evoluciones`, { withCredentials: true });
        evoluciones.value = resEvoluciones.data;
    } catch (err) {
        console.error(err);
        error.value = 'Error cargando la historia clínica.';
    } finally {
        loading.value = false;
    }
};

/**
 * Guarda una nueva evolución
 */
const guardarEvolucion = async () => {
    try {
        let fechaNormalizada = fecha.value;

        if (fecha.value instanceof Date) {
            // Si viene desde DatePicker
            const y = fecha.value.getFullYear();
            const m = String(fecha.value.getMonth() + 1).padStart(2, '0');
            const d = String(fecha.value.getDate()).padStart(2, '0');
            fechaNormalizada = `${y}-${m}-${d}`; // ISO seguro
        } else if (typeof fecha.value === 'string') {
            // Si ya es string "YYYY-MM-DD", aseguramos formato
            const partes = fecha.value.split('-');
            if (partes.length === 3) {
                const [y, m, d] = partes;
                fechaNormalizada = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
            }
        }

        const formData = new FormData();
        formData.append('fecha', fechaNormalizada);
        formData.append('contenido', contenido.value);
        formData.append('indicaciones', indicaciones.value);

        archivos.value.forEach((a) => {
            formData.append('archivos', a.file);
        });

        await api.post(`/pacientes/${pacienteId}/evolucion`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            withCredentials: true
        });

        toast.add({
            severity: 'success',
            summary: 'Éxito',
            detail: 'Evolución guardada correctamente',
            life: 3000
        });

        showForm.value = false;
        contenido.value = '';
        indicaciones.value = '';
        archivos.value = [];
        fileUploader.value?.clear();

        await fetchHistoria();
    } catch (err) {
        console.error('Error al guardar evolución:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Error al guardar evolución',
            life: 3000
        });
    }
};

/**
 * Exporta toda la historia clínica en PDF
 */
const descargarHistoriaPDF = () => {
    window.open(`${apiBase}/pacientes/${pacienteId}/historia/pdf`, '_blank');
};

/**
 * Exporta una evolución individual en PDF
 */
const descargarEvolucionPDF = (evoId) => {
    window.open(`${apiBase}/pacientes/${pacienteId}/evolucion/${evoId}/pdf`, '_blank');
};

const normalizar = (nombre) => nombre.toLowerCase().replace(/\s+/g, '').replace(/[()]/g, '').trim();

const onFileSelect = (event) => {
    // Nombres normalizados de archivos YA cargados
    const existentes = new Set(archivos.value.map((a) => normalizar(a.name)));

    // Filtrar solo archivos realmente nuevos
    const nuevos = event.files.filter((f) => !existentes.has(normalizar(f.name)));

    nuevos.forEach((f) => {
        // ---- Validaciones ----
        if (f.size > 5 * 1024 * 1024) {
            toast.add({
                severity: 'warn',
                summary: 'Archivo muy grande',
                detail: `${f.name} supera los 5 MB.`,
                life: 2500
            });
            return;
        }

        const formatosPermitidos = ['application/pdf', 'image/jpeg', 'image/png'];
        if (!formatosPermitidos.includes(f.type)) {
            toast.add({
                severity: 'error',
                summary: 'Formato no permitido',
                detail: `${f.name} no es PDF/JPG/PNG válido.`,
                life: 2500
            });
            return;
        }

        // Crear preview
        let preview = null;
        if (f.type.startsWith('image/')) preview = URL.createObjectURL(f);
        if (f.type === 'application/pdf') preview = '/icons/pdf-icon.png';

        // Agregar archivo limpio
        archivos.value.push({
            file: f,
            name: f.name,
            size: f.size,
            type: f.type,
            previewUrl: preview
        });
    });
};

const onFileRemove = (event) => {
    archivos.value = archivos.value.filter((a) => a.name !== event.file.name);
};

const formRef = ref(null);

const abrirFormEvolucion = async () => {
    showForm.value = true;

    await nextTick();

    if (formRef.value) {
        formRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

/**
 * Verifica la integridad de una evolución individual
 */
const verificarEvolucion = async (evoId) => {
    try {
        const { data } = await api.get(`/blockchain/verificar/evolucion/${evoId}`, {
            withCredentials: true
        });
        toast.add({
            severity: data.valido ? 'success' : 'warn',
            summary: 'Verificación Blockchain',
            detail: data.mensaje,
            life: 4000
        });
    } catch (err) {
        console.error('Error al verificar evolución:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No se pudo verificar la integridad de la evolución.',
            life: 4000
        });
    }
};

const verAuditoriasBlockchain = () => {
    // ✅ Usamos el id real de la historia consolidada más reciente
    const idHistoria = historias.value?.[0]?.id || null;

    if (!idHistoria) {
        toast.add({
            severity: 'warn',
            summary: 'Sin historia registrada',
            detail: 'El paciente aún no tiene una historia consolidada.',
            life: 4000
        });
        return;
    }

    toast.add({
        severity: 'info',
        summary: 'Redirigiendo...',
        detail: 'Abriendo auditorías Blockchain',
        life: 800
    });

    setTimeout(() => {
        // ✅ pasamos el id correcto de la tabla `historias`
        router.push({ path: '/blockchain/verificar', query: { id: idHistoria } });
    }, 300);
};

onMounted(fetchHistoria);
</script>

<template>
    <div class="p-4 md:p-8 min-h-screen bg-gray-50 dark:bg-[#121212] transition-colors">
        <Toast />

        <h1 class="text-3xl font-bold mb-4 text-gray-800 flex items-center">
            <i class="pi pi-user mr-3 text-blue-600"></i>
            Historia Clínica de {{ paciente?.apellido?.toUpperCase() }} {{ paciente?.nombre?.toUpperCase() }}
        </h1>

        <p v-if="loading" class="text-gray-500">Cargando...</p>
        <p v-if="error" class="text-red-500">{{ error }}</p>

        <!-- 📋 Datos del paciente -->
        <div v-if="paciente && !loading" class="mb-6 border p-4 rounded-2xl bg-white shadow-sm">
            <div class="grid md:grid-cols-2 gap-2 text-gray-700 text-sm">
                <p><strong>DNI:</strong> {{ paciente.dni }}</p>
                <p><strong>Cobertura:</strong> {{ paciente?.cobertura || '-' }}</p>
                <p><strong>Nº HC:</strong> {{ paciente.nro_hc }}</p>
                <p><strong>Fecha de nacimiento:</strong> {{ paciente.fecha_nacimiento || '-' }}</p>
            </div>
        </div>

        <!-- 🧠 EVOLUCIONES -->
        <div v-if="!loading">
            <div class="flex flex-wrap justify-between items-center mt-6 mb-3 gap-2">
                <h2 class="text-xl font-semibold text-gray-800 flex items-center"><i class="pi pi-book mr-2 text-blue-500"></i> Evoluciones</h2>

                <div class="flex flex-wrap justify-end gap-2">
                    <button @click="descargarHistoriaPDF" class="flex items-center bg-blue-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-blue-700 transition text-sm"><i class="pi pi-file-pdf mr-2"></i> Exportar Historia Completa</button>

                    <button @click="verAuditoriasBlockchain" class="flex items-center bg-purple-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-purple-700 transition text-sm"><i class="pi pi-list mr-2"></i> Ver Auditorías Blockchain</button>

                    <button @click="abrirFormEvolucion" class="flex items-center bg-green-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-green-700 transition text-sm">
                        <i class="pi pi-plus mr-2"></i> {{ showForm ? 'Cancelar' : 'Agregar Evolución' }}
                    </button>
                </div>
            </div>

            <!-- Si no hay evoluciones -->
            <p v-if="evoluciones.length === 0" class="text-gray-500 mt-3">No hay evoluciones registradas aún.</p>

            <!-- 📂 Evoluciones agrupadas por año -->
            <div v-for="{ año, items } in evolucionesPorAño" :key="año" class="mb-6">
                <!-- CABECERA DEL AÑO -->
                <button
                    @click="accordionAbierto[año] = !accordionAbierto[año]"
                    class="w-full flex justify-between items-center px-4 py-3 bg-gray-200 dark:bg-gray-800 hover:bg-gray-300 dark:hover:bg-gray-700 text-gray-800 dark:text-white rounded-lg transition font-semibold"
                >
                    <span> {{ año }}</span>
                    <i :class="accordionAbierto[año] ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"></i>
                </button>

                <!-- CONTENIDO DEL AÑO -->
                <div v-show="accordionAbierto[año]" class="mt-3">
                    <div v-for="evo in items" :key="evo.id" class="border rounded-2xl mb-4 p-5 shadow-sm bg-white hover:shadow-md transition">
                        <div class="flex justify-between text-sm text-gray-600 mb-2">
                            <span class="font-medium">{{ fechaBonitaClinica(evo.fecha) }}</span>

                            <div class="flex flex-col items-end text-right">
                                <span>{{ evo.nombre_usuario }} — {{ evo.especialidad_usuario || 'Director' }}</span>
                                <span class="text-xs text-gray-400"> Registrado: {{ fechaBonitaCompleta(evo.creado_en) }} </span>
                            </div>
                        </div>

                        <p class="text-gray-800 text-sm mb-4 line-clamp-3">{{ evo.contenido }}</p>

                        <p v-if="evo.indicaciones" class="text-gray-700 text-sm mb-2"><strong>Indicaciones:</strong> {{ evo.indicaciones }}</p>

                        <div class="flex justify-end gap-3">
                            <button @click="$router.push({ name: 'evolucionDetalle', params: { id: pacienteId, evoId: evo.id } })" class="text-blue-600 hover:text-blue-800 text-sm flex items-center"><i class="pi pi-eye mr-1"></i> Ver Detalle</button>

                            <button @click="descargarEvolucionPDF(evo.id)" class="text-red-600 hover:text-red-800 text-sm flex items-center"><i class="pi pi-file-pdf mr-1"></i> Exportar PDF</button>

                            <button @click="verificarEvolucion(evo.id)" class="text-purple-600 hover:text-blue-800 text-sm flex items-center"><i class="pi pi-shield mr-1"></i> Verificar Integridad</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 📝 FORMULARIO NUEVA EVOLUCIÓN -->
        <div v-if="showForm" ref="formRef" class="mt-6 border p-4 rounded-2xl bg-white shadow-sm animate-fade-in">
            <h3 class="text-lg font-semibold text-gray-700 mb-4">Registrar nueva evolución</h3>

            <label for="fecha" class="block font-medium mb-2 text-gray-700">Fecha</label>

            <DatePicker v-model="fecha" dateFormat="dd/mm/yy" :showIcon="true" class="p-inputtext p-component w-full h-12 mb-4" />

            <label for="contenido" class="block font-medium mb-2 text-gray-700">Evolución</label>
            <textarea v-model="contenido" rows="5" class="p-2 border rounded w-full mb-4" placeholder="Escribí la evolución clínica..."></textarea>

            <label for="indicaciones" class="block font-medium mb-2 text-gray-700">Indicaciones</label>
            <textarea v-model="indicaciones" rows="3" class="p-2 border rounded w-full mb-4" placeholder="Escribí las indicaciones médicas (opcional)..."></textarea>

            <label class="block font-medium mb-2 text-gray-700">Archivos adjuntos</label>

            <FileUpload
                ref="fileUploader"
                name="archivos"
                customUpload
                :multiple="true"
                @select="onFileSelect"
                @remove="onFileRemove"
                :auto="false"
                :showUpload="false"
                :showCancel="false"
                accept=".pdf,image/*"
                class="mb-2"
                :previewWidth="0"
                :showPreview="false"
            />
            <p class="text-xs text-gray-500 mt-1">Tipos permitidos: <strong>PDF, JPG, PNG</strong> — Máximo <strong>5 MB</strong> por archivo.</p>

            <!-- Lista de archivos seleccionados -->
            <ul v-if="archivos.length" class="mt-3 space-y-2">
                <li v-for="a in archivos" :key="a.name" class="flex items-center gap-3 p-2 border rounded-lg bg-gray-50">
                    <!-- Imagen preview -->
                    <img v-if="a.type.startsWith('image/')" :src="a.previewUrl" class="w-12 h-12 rounded object-cover" />

                    <!-- Icono PDF -->
                    <div v-else-if="a.type === 'application/pdf'" class="w-12 h-12 flex items-center justify-center bg-red-100 border border-red-300 text-red-700 rounded">
                        <i class="pi pi-file-pdf text-xl"></i>
                    </div>

                    <!-- Info del archivo -->
                    <div class="flex flex-col">
                        <span class="font-medium text-gray-800">{{ a.name }}</span>
                        <span class="text-xs text-gray-500">{{ (a.size / 1024).toFixed(1) }} KB</span>
                    </div>

                    <span class="ml-auto text-green-600 font-medium">Listo</span>
                </li>
            </ul>
            <div class="mt-4">
                <Button label="Guardar Evolución" icon="pi pi-save" @click="guardarEvolucion" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.animate-fade-in {
    animation: fadeIn 0.4s ease-in-out;
}
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
