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
import { fechaBonitaClinica, fechaBonitaDashboard } from '@/utils/formatDate.js';
import { nextTick } from 'vue';
import { computed } from 'vue';
import Tag from 'primevue/tag';
import Dialog from 'primevue/dialog';
import { useUserStore } from '@/stores/user';

const route = useRoute();
const pacienteId = route.params.id;
const router = useRouter();
const apiBase = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
const userStore = useUserStore();

const toast = useToast();

const paciente = ref(null);
const historias = ref([]);
const evoluciones = ref([]);
const historiaAdjuntos = ref([]);
const adjuntosHistoriaSeleccionados = ref([]);
const subiendoAdjuntosHistoria = ref(false);
const loading = ref(true);
const error = ref(null);

const showForm = ref(false);
const fecha = ref(new Date().toISOString().split('T')[0]);
const contenido = ref('');
const indicaciones = ref('');
const motivoRectificacion = ref('');
const archivos = ref([]);
const fileUploader = ref(null);
const showFirmaDialog = ref(false);
const confirmacionFirma = ref(false);
const firmaEnviando = ref(false);

// Variables para edicion
const isEditing = ref(false);
const editingEvoId = ref(null);

// Variables para dialogo de historial
const showHistorialDialog = ref(false);
const historialEvo = ref([]);
const historialEvoCargando = ref(false);
const selectedEvoParaHistorial = ref(null);

// Control de qué año está abierto
const accordionAbierto = ref({});

const canEvolve = computed(() => ['director', 'profesional'].includes(userStore.rol) && Boolean(userStore.matricula_tipo) && Boolean(userStore.matricula_numero));

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

const cargarAdjuntosHistoria = async () => {
    try {
        const { data } = await api.get(`/pacientes/${pacienteId}/adjuntos`, { withCredentials: true });
        historiaAdjuntos.value = data;
    } catch (err) {
        console.error('Error cargando documentos de la historia:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: err?.response?.data?.error || 'No se pudieron cargar los documentos adjuntos.',
            life: 4000
        });
    }
};

const onHistoriaFilesSelected = (event) => {
    const formatosPermitidos = ['application/pdf', 'image/jpeg', 'image/png'];
    const nuevos = Array.from(event.target.files || []);
    const existentes = new Set(adjuntosHistoriaSeleccionados.value.map((archivo) => archivo.name.toLowerCase()));

    nuevos.forEach((archivo) => {
        if (existentes.has(archivo.name.toLowerCase())) return;
        if (archivo.size > 10 * 1024 * 1024) {
            toast.add({ severity: 'warn', summary: 'Archivo muy grande', detail: `${archivo.name} supera los 10 MB.`, life: 3000 });
            return;
        }
        if (!formatosPermitidos.includes(archivo.type)) {
            toast.add({ severity: 'error', summary: 'Formato no permitido', detail: `${archivo.name} no es PDF/JPG/PNG válido.`, life: 3000 });
            return;
        }
        adjuntosHistoriaSeleccionados.value.push(archivo);
    });
    event.target.value = '';
};

const quitarAdjuntoHistoriaSeleccionado = (nombre) => {
    adjuntosHistoriaSeleccionados.value = adjuntosHistoriaSeleccionados.value.filter((archivo) => archivo.name !== nombre);
};

const subirAdjuntosHistoria = async () => {
    if (!adjuntosHistoriaSeleccionados.value.length) return;
    subiendoAdjuntosHistoria.value = true;
    try {
        const formData = new FormData();
        adjuntosHistoriaSeleccionados.value.forEach((archivo) => formData.append('archivos', archivo));
        await api.post(`/pacientes/${pacienteId}/adjuntos`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            withCredentials: true
        });
        adjuntosHistoriaSeleccionados.value = [];
        await cargarAdjuntosHistoria();
        toast.add({ severity: 'success', summary: 'Documento guardado', detail: 'El documento quedó incorporado a la historia.', life: 3000 });
    } catch (err) {
        console.error('Error subiendo documento de la historia:', err);
        toast.add({ severity: 'error', summary: 'Error', detail: err?.response?.data?.error || 'No se pudo guardar el documento.', life: 4000 });
    } finally {
        subiendoAdjuntosHistoria.value = false;
    }
};

/**
 * Guarda una nueva evolución
 */
const guardarEvolucion = () => {
    if (!fecha.value || !contenido.value.trim()) {
        toast.add({
            severity: 'warn',
            summary: 'Datos incompletos',
            detail: 'La fecha y el contenido de la evolución son obligatorios.',
            life: 3000
        });
        return;
    }
    if (isEditing.value && !motivoRectificacion.value.trim()) {
        toast.add({
            severity: 'warn',
            summary: 'Motivo requerido',
            detail: 'Indica el motivo de la rectificación antes de firmar.',
            life: 3000
        });
        return;
    }
    confirmacionFirma.value = false;
    showFirmaDialog.value = true;
};

const enviarEvolucion = async () => {
    firmaEnviando.value = true;
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
        formData.append('confirmar_firma', 'true');
        if (isEditing.value) {
            formData.append('motivo_rectificacion', motivoRectificacion.value.trim());
        }

        archivos.value.forEach((a) => {
            formData.append('archivos', a.file);
        });

        if (isEditing.value) {
            await api.put(`/pacientes/${pacienteId}/evolucion/${editingEvoId.value}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                withCredentials: true
            });
            toast.add({
                severity: 'success',
                summary: 'Éxito',
                detail: 'Rectificación firmada correctamente',
                life: 3000
            });
        } else {
            await api.post(`/pacientes/${pacienteId}/evolucion`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                withCredentials: true
            });
            toast.add({
                severity: 'success',
                summary: 'Éxito',
                detail: 'Evolución firmada y guardada correctamente',
                life: 3000
            });
        }

        showForm.value = false;
        contenido.value = '';
        indicaciones.value = '';
        motivoRectificacion.value = '';
        archivos.value = [];
        fileUploader.value?.clear();
        isEditing.value = false;
        editingEvoId.value = null;
        showFirmaDialog.value = false;

        await fetchHistoria();
    } catch (err) {
        console.error('Error al guardar evolución:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: err?.response?.data?.error || 'Error al guardar evolución',
            life: 3000
        });
    } finally {
        firmaEnviando.value = false;
    }
};

const iniciarEdicion = async (evo) => {
    isEditing.value = true;
    editingEvoId.value = evo.id;
    fecha.value = new Date(evo.fecha);
    contenido.value = evo.contenido;
    indicaciones.value = evo.indicaciones || '';
    motivoRectificacion.value = '';
    archivos.value = [];
    showForm.value = true;

    await nextTick();
    if (formRef.value) {
        formRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

const cancelarFormEvolucion = () => {
    showForm.value = false;
    contenido.value = '';
    indicaciones.value = '';
    motivoRectificacion.value = '';
    archivos.value = [];
    fileUploader.value?.clear();
    isEditing.value = false;
    editingEvoId.value = null;
};

const verHistorialEvo = async (evo) => {
    try {
        selectedEvoParaHistorial.value = evo;
        showHistorialDialog.value = true;
        historialEvoCargando.value = true;
        historialEvo.value = [];

        const res = await api.get(`/pacientes/${pacienteId}/evolucion/${evo.id}/historial`, {
            withCredentials: true
        });
        historialEvo.value = res.data;
    } catch (err) {
        console.error('Error al cargar historial de evolución:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No se pudo cargar el historial de cambios.',
            life: 4000
        });
    } finally {
        historialEvoCargando.value = false;
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
    if (!canEvolve.value) {
        toast.add({
            severity: 'warn',
            summary: 'Firma no habilitada',
            detail: 'Sólo profesionales con tipo y número de matrícula cargados pueden evolucionar.',
            life: 4000
        });
        return;
    }
    showForm.value = true;

    await nextTick();

    if (formRef.value) {
        formRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

/**
 * Verifica la integridad de una evolución individual
 */
const registrarEvolucionBfa = async (evoId) => {
    try {
        const { data } = await api.post(`/blockchain/registrar/evolucion/${evoId}`, {}, { withCredentials: true });
        toast.add({
            severity: 'success',
            summary: 'Blockchain',
            detail: data.mensaje || 'Evolucion anclada en BFA',
            life: 4000
        });
        await fetchHistoria();
    } catch (err) {
        console.error('Error al anclar evolucion:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: err?.response?.data?.error || 'No se pudo anclar la evolucion en BFA.',
            life: 4000
        });
    }
};

const verificarEvolucion = async (evoId) => {
    try {
        const { data } = await api.get(`/blockchain/verificar/evolucion/${evoId}`, {
            withCredentials: true
        });
        // estado_bfa: 'verificado' (ok), 'error' (alterado), 'pendiente' (aun no en blockchain)
        const severityPorEstado = { verificado: 'success', error: 'error', pendiente: 'warn' };
        toast.add({
            severity: severityPorEstado[data.estado_bfa] || 'info',
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

const verificarFirmaElectronica = async (evoId) => {
    try {
        const { data } = await api.get(`/pacientes/${pacienteId}/evolucion/${evoId}/firma`, {
            withCredentials: true
        });
        toast.add({
            severity: data.valida ? 'success' : 'warn',
            summary: 'Firma electrónica',
            detail: data.valida ? 'La huella coincide con el contenido firmado.' : 'No se pudo validar la huella de esta evolución.',
            life: 4000
        });
    } catch (err) {
        console.error('Error al verificar firma electrónica:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: err?.response?.data?.error || 'No se pudo verificar la firma electrónica.',
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
        router.push({ path: '/blockchain/verificar', query: { id: idHistoria, tipo: 'historia' } });
    }, 300);
};

onMounted(() => {
    fetchHistoria();
    cargarAdjuntosHistoria();
});
</script>

<template>
    <div class="p-4 md:p-8 min-h-screen bg-ground transition-colors">
        <Toast />

        <h1 class="text-3xl font-bold mb-4 text-color flex items-center">
            <i class="pi pi-user mr-3 text-primary"></i>
            Historia Clínica de {{ paciente?.apellido?.toUpperCase() }} {{ paciente?.nombre?.toUpperCase() }}
        </h1>

        <p v-if="loading" class="text-muted-color">Cargando...</p>
        <p v-if="error" class="text-status-sin-aviso-fg">{{ error }}</p>

        <!-- 📋 Datos del paciente -->
        <div v-if="paciente && !loading" class="mb-6 border border-surface p-4 rounded-2xl bg-card shadow-sm">
            <div class="grid md:grid-cols-2 gap-2 text-color text-sm">
                <p><strong>DNI:</strong> {{ paciente.dni }}</p>
                <p>
                    <strong>Cobertura:</strong> {{ paciente?.cobertura || '-' }} <span v-if="paciente?.nro_certificado" class="text-xs text-muted-color">({{ paciente.nro_certificado }})</span>
                </p>
                <p><strong>Nº HC:</strong> {{ paciente.nro_hc }}</p>
                <p><strong>Nº de Cobertura:</strong> {{ paciente?.nro_certificado || '-' }}</p>
                <p><strong>Fecha de nacimiento:</strong> {{ paciente.fecha_nacimiento || '-' }}</p>
            </div>
        </div>

        <!-- 📎 DOCUMENTOS GENERALES DE LA HISTORIA (no son evoluciones) -->
        <section v-if="paciente && !loading" class="mb-6 border border-surface p-4 rounded-2xl bg-card shadow-sm">
            <div class="flex flex-wrap justify-between items-center gap-2 mb-3">
                <h2 class="text-xl font-semibold text-color flex items-center"><i class="pi pi-paperclip mr-2 text-primary"></i> Documentos de la historia</h2>
                <span class="text-xs text-muted-color">Estudios externos, antecedentes y consentimientos</span>
            </div>

            <div class="flex flex-wrap items-center gap-3 mb-3">
                <label class="inline-flex items-center gap-2 cursor-pointer rounded-lg border border-surface px-3 py-2 text-sm text-primary hover:bg-highlight">
                    <i class="pi pi-upload"></i>
                    Seleccionar documentos
                    <input type="file" multiple accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" class="hidden" @change="onHistoriaFilesSelected" />
                </label>
                <button
                    type="button"
                    class="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    :disabled="!adjuntosHistoriaSeleccionados.length || subiendoAdjuntosHistoria"
                    @click="subirAdjuntosHistoria"
                >
                    <i class="pi pi-save mr-1"></i> {{ subiendoAdjuntosHistoria ? 'Guardando…' : 'Incorporar a la historia' }}
                </button>
            </div>

            <ul v-if="adjuntosHistoriaSeleccionados.length" class="mb-4 space-y-1 text-sm text-muted-color">
                <li v-for="archivo in adjuntosHistoriaSeleccionados" :key="archivo.name" class="flex items-center gap-2">
                    <i class="pi pi-file"></i>
                    <span class="truncate">{{ archivo.name }}</span>
                    <button type="button" class="ml-auto text-status-sin-aviso-fg hover:text-red-800" @click="quitarAdjuntoHistoriaSeleccionado(archivo.name)">Quitar</button>
                </li>
            </ul>

            <p v-if="!historiaAdjuntos.length" class="text-sm text-muted-color">No hay documentos generales adjuntos.</p>
            <ul v-else class="space-y-2">
                <li v-for="adjunto in historiaAdjuntos" :key="adjunto.id" class="flex flex-wrap items-center gap-2 rounded-lg border border-surface p-3 text-sm">
                    <i class="pi pi-file text-primary"></i>
                    <a :href="adjunto.url" target="_blank" rel="noopener" class="font-medium text-primary hover:underline">{{ adjunto.nombre }}</a>
                    <span class="text-xs text-muted-color">{{ fechaBonitaDashboard(adjunto.cargado_en) }} · {{ adjunto.cargado_por }}</span>
                    <span class="ml-auto text-xs text-muted-color">SHA-256: {{ adjunto.hash_sha256 }}</span>
                </li>
            </ul>
            <p class="mt-3 text-xs text-muted-color">Sólo PDF, JPG o PNG, hasta 10 MB. Los documentos quedan registrados sin reemplazo ni borrado.</p>
        </section>

        <!-- 🧠 EVOLUCIONES -->
        <div v-if="!loading">
            <div class="flex flex-wrap justify-between items-center mt-6 mb-3 gap-2">
                <h2 class="text-xl font-semibold text-color flex items-center"><i class="pi pi-book mr-2 text-primary"></i> Evoluciones</h2>

                <div class="flex flex-wrap justify-end gap-2">
                    <button @click="descargarHistoriaPDF" class="flex items-center bg-blue-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-blue-700 transition text-sm"><i class="pi pi-file-pdf mr-2"></i> Exportar Historia Completa</button>

                    <button @click="verAuditoriasBlockchain" class="flex items-center bg-purple-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-purple-700 transition text-sm"><i class="pi pi-list mr-2"></i> Ver Auditorías Blockchain</button>

                    <button v-if="canEvolve" @click="abrirFormEvolucion" class="flex items-center bg-green-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-green-700 transition text-sm">
                        <i class="pi pi-plus mr-2"></i> {{ showForm ? 'Cancelar' : 'Agregar Evolución' }}
                    </button>
                </div>
            </div>

            <div v-if="!canEvolve && ['director', 'profesional'].includes(userStore.rol)" class="mb-4 rounded-lg border border-status-con-aviso-border bg-status-con-aviso-bg px-4 py-3 text-sm text-status-con-aviso-fg">
                Para evolucionar necesitás tener el tipo y número de matrícula cargados.
            </div>

            <!-- Si no hay evoluciones -->
            <p v-if="evoluciones.length === 0" class="text-muted-color mt-3">No hay evoluciones registradas aún.</p>

            <!-- 📂 Evoluciones agrupadas por año -->
            <div v-for="{ año, items } in evolucionesPorAño" :key="año" class="mb-6">
                <!-- CABECERA DEL AÑO -->
                <button @click="accordionAbierto[año] = !accordionAbierto[año]" class="w-full flex justify-between items-center px-4 py-3 bg-subtle hover:bg-emphasis text-color rounded-lg transition font-semibold">
                    <span> {{ año }}</span>
                    <i :class="accordionAbierto[año] ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"></i>
                </button>

                <!-- CONTENIDO DEL AÑO -->
                <div v-show="accordionAbierto[año]" class="mt-3">
                    <div v-for="evo in items" :key="evo.id" class="border border-surface rounded-2xl mb-4 p-5 shadow-sm bg-card hover:shadow-md transition">
                        <div class="flex justify-between text-sm text-muted-color mb-2">
                            <div class="flex items-center gap-2">
                                <span class="font-medium">{{ fechaBonitaClinica(evo.fecha) }}</span>
                                <Tag v-if="evo.version > 1" value="Editado" severity="warn" rounded class="cursor-pointer text-xs" @click="verHistorialEvo(evo)" />
                            </div>

                            <div class="flex flex-col items-end text-right text-color">
                                <span>{{ evo.nombre_usuario }} — {{ evo.especialidad_usuario || 'Director' }}</span>
                                <span v-if="evo.estado_firma === 'firmada'" class="text-xs text-status-presente-fg"> Firma electrónica registrada </span>
                            </div>
                        </div>

                        <p class="text-color text-sm mb-4 line-clamp-3">{{ evo.contenido }}</p>

                        <p v-if="evo.indicaciones" class="text-color text-sm mb-2"><strong>Indicaciones:</strong> {{ evo.indicaciones }}</p>

                        <div class="flex justify-end gap-3">
                            <button @click="$router.push({ name: 'evolucionDetalle', params: { id: pacienteId, evoId: evo.id } })" class="text-primary hover:text-primary-emphasis text-sm flex items-center">
                                <i class="pi pi-eye mr-1"></i> Ver Detalle
                            </button>

                            <button @click="descargarEvolucionPDF(evo.id)" class="text-status-sin-aviso-fg hover:text-red-800 text-sm flex items-center"><i class="pi pi-file-pdf mr-1"></i> Exportar PDF</button>

                            <button v-if="canEvolve && (userStore.rol === 'director' || evo.usuario_id === userStore.id)" @click="iniciarEdicion(evo)" class="text-status-presente-fg hover:text-green-800 text-sm flex items-center">
                                <i class="pi pi-pencil mr-1"></i> Editar
                            </button>

                            <button v-if="!evo.tx_hash" @click="registrarEvolucionBfa(evo.id)" class="text-purple-600 hover:text-purple-800 text-sm flex items-center"><i class="pi pi-link mr-1"></i> Anclar BFA</button>

                            <button @click="verificarEvolucion(evo.id)" class="text-purple-600 hover:text-primary-emphasis text-sm flex items-center"><i class="pi pi-shield mr-1"></i> Verificar Integridad</button>

                            <button v-if="evo.estado_firma === 'firmada'" @click="verificarFirmaElectronica(evo.id)" class="text-teal-600 hover:text-teal-800 text-sm flex items-center"><i class="pi pi-check-circle mr-1"></i> Verificar firma</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 📝 FORMULARIO NUEVA EVOLUCIÓN -->
        <div v-if="showForm && canEvolve" ref="formRef" class="mt-6 border border-surface p-4 rounded-2xl bg-card shadow-sm animate-fade-in">
            <h3 class="text-lg font-semibold text-color mb-4">{{ isEditing ? 'Rectificar evolución clínica' : 'Registrar nueva evolución' }}</h3>

            <label for="fecha" class="block font-medium mb-2 text-color">Fecha</label>

            <DatePicker v-model="fecha" dateFormat="dd/mm/yy" :showIcon="true" class="p-inputtext p-component w-full h-12 mb-4" />

            <label for="contenido" class="block font-medium mb-2 text-color">Evolución</label>
            <textarea v-model="contenido" rows="5" class="p-2 border border-surface rounded w-full mb-4 bg-card text-color" placeholder="Escribí la evolución clínica..."></textarea>

            <label for="indicaciones" class="block font-medium mb-2 text-color">Indicaciones</label>
            <textarea v-model="indicaciones" rows="3" class="p-2 border border-surface rounded w-full mb-4 bg-card text-color" placeholder="Escribí las indicaciones médicas (opcional)..."></textarea>

            <template v-if="isEditing">
                <label for="motivoRectificacion" class="block font-medium mb-2 text-color">Motivo de la rectificación</label>
                <textarea id="motivoRectificacion" v-model="motivoRectificacion" rows="2" class="p-2 border border-surface rounded w-full mb-4 bg-card text-color" placeholder="Explicá por qué se rectifica esta evolución..."></textarea>
            </template>

            <label class="block font-medium mb-2 text-color">Archivos adjuntos (nuevos)</label>

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
                accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                class="mb-2"
                :previewWidth="0"
                :showPreview="false"
            />
            <p class="text-xs text-muted-color mt-1">Tipos permitidos: <strong>PDF, JPG, PNG</strong> — Máximo <strong>5 MB</strong> por archivo.</p>

            <!-- Lista de archivos seleccionados -->
            <ul v-if="archivos.length" class="mt-3 space-y-2">
                <li v-for="a in archivos" :key="a.name" class="flex items-center gap-3 p-2 border border-surface rounded-lg bg-subtle">
                    <!-- Imagen preview -->
                    <img v-if="a.type.startsWith('image/')" :src="a.previewUrl" class="w-12 h-12 rounded object-cover" />

                    <!-- Icono PDF -->
                    <div v-else-if="a.type === 'application/pdf'" class="w-12 h-12 flex items-center justify-center bg-status-sin-aviso-bg border border-status-sin-aviso-border text-status-sin-aviso-fg rounded">
                        <i class="pi pi-file-pdf text-xl"></i>
                    </div>

                    <!-- Info del archivo -->
                    <div class="flex flex-col">
                        <span class="font-medium text-color">{{ a.name }}</span>
                        <span class="text-xs text-muted-color">{{ (a.size / 1024).toFixed(1) }} KB</span>
                    </div>

                    <span class="ml-auto text-status-presente-fg font-medium">Listo</span>
                </li>
            </ul>
            <div class="mt-4 flex gap-2">
                <Button :label="isEditing ? 'Revisar y firmar rectificación' : 'Revisar y firmar evolución'" icon="pi pi-pencil" @click="guardarEvolucion" />
                <Button label="Cancelar" icon="pi pi-times" severity="secondary" @click="cancelarFormEvolucion" />
            </div>
        </div>

        <!-- 🔏 CONFIRMACIÓN EXPLÍCITA DE FIRMA ELECTRÓNICA -->
        <Dialog v-model:visible="showFirmaDialog" header="Confirmar firma electrónica" :modal="true" :closable="!firmaEnviando" :closeOnEscape="!firmaEnviando" :style="{ width: 'min(34rem, 92vw)' }">
            <div class="space-y-4 text-sm text-color">
                <p>Al confirmar, esta evolución quedará cerrada, vinculada a tu cuenta profesional y no podrá sobrescribirse.</p>
                <div class="rounded-lg border border-surface bg-highlight p-3">
                    <p><strong>Profesional:</strong> {{ userStore.nombre }}</p>
                    <p><strong>Matrícula:</strong> {{ userStore.matricula_tipo }} {{ userStore.matricula_numero }}{{ userStore.matricula_provincia ? ` (${userStore.matricula_provincia})` : '' }}</p>
                </div>
                <label class="flex items-start gap-2 cursor-pointer">
                    <input v-model="confirmacionFirma" type="checkbox" class="mt-1" />
                    <span>Confirmo que revisé el contenido y deseo firmar electrónicamente esta {{ isEditing ? 'rectificación' : 'evolución' }}.</span>
                </label>
            </div>
            <template #footer>
                <Button label="Cancelar" severity="secondary" :disabled="firmaEnviando" @click="showFirmaDialog = false" />
                <Button :label="firmaEnviando ? 'Firmando…' : 'Firmar evolución'" icon="pi pi-check" :loading="firmaEnviando" :disabled="!confirmacionFirma || firmaEnviando" @click="enviarEvolucion" />
            </template>
        </Dialog>

        <!-- 📜 DIALOG: HISTORIAL DE EDICIONES -->
        <Dialog v-model:visible="showHistorialDialog" header="Historial de Cambios" :modal="true" :breakpoints="{ '960px': '75vw', '640px': '90vw' }" :style="{ width: '50vw' }">
            <div v-if="historialEvoCargando" class="flex flex-col items-center justify-center py-6">
                <i class="pi pi-spin pi-spinner text-3xl text-primary mb-2"></i>
                <span>Cargando historial...</span>
            </div>
            <div v-else-if="historialEvo.length === 0" class="py-4 text-center text-muted-color">No se encontraron cambios registrados para esta evolución.</div>
            <div v-else class="space-y-6">
                <p class="text-sm text-muted-color mb-4">Se muestran todas las versiones de esta evolución clínica en orden cronológico. Los registros históricos son inmutables.</p>

                <div class="relative border-l-2 border-primary ml-3 space-y-6">
                    <div v-for="v in historialEvo" :key="v.id" class="relative pl-6">
                        <!-- Dot de la linea de tiempo -->
                        <div class="absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 bg-card" :class="v.activo ? 'border-green-500 bg-green-500' : 'border-primary'"></div>

                        <div class="p-4 rounded-xl border border-surface bg-subtle shadow-xs">
                            <div class="flex justify-between items-center mb-2 flex-wrap gap-1">
                                <span class="font-bold text-sm text-color"> Versión {{ v.version }} <Tag v-if="v.activo" value="Activa (Vigente)" severity="success" class="text-[10px] py-0 px-1 ml-1" /> </span>
                                <span class="text-xs text-muted-color">
                                    {{ fechaBonitaClinica(v.fecha || v.creado_en) }}
                                </span>
                            </div>

                            <p class="text-xs text-muted-color mb-2 font-medium">Por: {{ v.nombre_usuario }} ({{ v.especialidad_usuario }})</p>

                            <p v-if="v.motivo_rectificacion" class="text-xs text-status-con-aviso-fg mb-2"><strong>Motivo de rectificación:</strong> {{ v.motivo_rectificacion }}</p>

                            <p v-if="v.estado_firma === 'firmada'" class="text-xs text-status-presente-fg mb-2">Firma electrónica registrada</p>

                            <p class="text-color text-sm whitespace-pre-wrap mb-2 bg-card p-2 rounded border border-surface">{{ v.contenido }}</p>

                            <div v-if="v.indicaciones" class="text-xs text-muted-color mt-2">
                                <strong>Indicaciones:</strong>
                                <p class="whitespace-pre-wrap bg-card p-2 rounded border border-surface mt-1">{{ v.indicaciones }}</p>
                            </div>

                            <div v-if="v.archivos && v.archivos.length" class="mt-2 text-xs">
                                <strong>Archivos adjuntos:</strong>
                                <ul class="mt-1 space-y-1">
                                    <li v-for="file in v.archivos" :key="file.nombre">
                                        <a :href="file.url" target="_blank" class="text-primary hover:underline flex items-center gap-1"> <i class="pi pi-file"></i> {{ file.nombre }} </a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Dialog>
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
