<script setup>
import { onMounted, reactive, ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import Button from 'primevue/button';
import pacienteService from '@/service/pacienteService';
import PresupuestoForm from './components/PresupuestoForm.vue';
import PresupuestoPreview from './components/PresupuestoPreview.vue';

const toast = useToast();

const pacientes = ref([]);
const loadingPacientes = ref(false);

const COUNTER_KEY = 'cau-presupuesto-counter';

function getStoredCounter() {
    try {
        const saved = localStorage.getItem(COUNTER_KEY);
        const parsed = parseInt(saved, 10);
        return Number.isFinite(parsed) && parsed >= 40 ? parsed : 40;
    } catch {
        return 40;
    }
}

function saveStoredCounter(val) {
    try {
        localStorage.setItem(COUNTER_KEY, String(val));
    } catch (e) {
        console.error('Error guardando contador en localStorage:', e);
    }
}

const currentCounter = ref(getStoredCounter());

function formatBudgetNumber(num) {
    const today = new Date();
    const yyyy = today.getFullYear();
    return `CAU-${yyyy}-${String(num).padStart(4, '0')}`;
}

function getInitialDraft(counterVal = currentCounter.value) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');

    return {
        number: formatBudgetNumber(counterVal),
        date: `${yyyy}-${mm}-${dd}`,
        doctor: 'Área Asistencial CAU',
        patientName: '',
        patientDni: '',
        patientCoverage: 'Particular',
        summary: 'Plan integral de tratamiento asistencial y rehabilitación funcional.',
        sections: [
            {
                id: 1,
                title: 'Evaluación y Diagnóstico Inicial',
                concept: 'Sesión interdisciplinaria de evaluación funcional',
                items: 'Análisis clínico y anamnesis inicial\nDefinición de objetivos terapéuticos\nDevolución y entrega de informe',
                subtotal: 35000,
                type: 'Pago único'
            },
            {
                id: 2,
                title: 'Módulo de Tratamiento (10 Sesiones)',
                concept: 'Sesiones de atención ambulatoria personalizada',
                items: 'Tratamiento activo según protocolo específico\nSeguimiento y control evolutivo de objetivos\nReevaluación de alta terapéutica',
                subtotal: 100000,
                type: 'Abono módulo (10 sesiones)'
            }
        ],
        conditions: [
            'Validez de la presente propuesta: 15 días corridos desde la fecha de emisión.',
            'Medios de pago habilitados: Transferencia bancaria institucional o tarjetas en secretaría CAU.',
            'Cancelaciones o reprogramaciones deben notificarse con al menos 24 horas de antelación.'
        ]
    };
}

const draft = reactive(getInitialDraft());

function handleStepNumber(delta) {
    const nextVal = Math.max(40, currentCounter.value + delta);
    currentCounter.value = nextVal;
    saveStoredCounter(nextVal);
    draft.number = formatBudgetNumber(nextVal);
}

function avanzarSiguienteNumero() {
    handleStepNumber(1);
    toast.add({
        severity: 'info',
        summary: 'Siguiente Presupuesto',
        detail: `Número avanzado a ${draft.number}`,
        life: 2000
    });
}

async function cargarPacientes() {
    loadingPacientes.value = true;
    try {
        const { data } = await pacienteService.getPacientes();
        if (Array.isArray(data)) {
            pacientes.value = data;
        } else if (data && Array.isArray(data.pacientes)) {
            pacientes.value = data.pacientes;
        } else {
            pacientes.value = [];
        }
    } catch (error) {
        console.error('Error al cargar lista de pacientes:', error);
        toast.add({
            severity: 'warn',
            summary: 'Padrón de Pacientes',
            detail: 'No se pudo precargar la lista de pacientes. Podés completar los datos manualmente.',
            life: 4000
        });
    } finally {
        loadingPacientes.value = false;
    }
}

function resetDraft() {
    const initial = getInitialDraft(currentCounter.value);
    Object.assign(draft, initial);
    toast.add({
        severity: 'info',
        summary: 'Plantilla reestablecida',
        detail: `Presupuesto listo con N.º ${draft.number}`,
        life: 2500
    });
}

function exportPdf() {
    window.print();
    // Al exportar/imprimir avanzamos automáticamente el contador en 1 para el siguiente
    const nextVal = currentCounter.value + 1;
    currentCounter.value = nextVal;
    saveStoredCounter(nextVal);
    draft.number = formatBudgetNumber(nextVal);
}

onMounted(() => {
    cargarPacientes();
});
</script>

<template>
    <div class="space-y-6 print:space-y-0 print:m-0 print:p-0">
        <!-- Barra Superior / Acciones Principales -->
        <div class="no-print bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 sm:p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div>
                <div class="flex items-center gap-2">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-[#ccfbf1] text-[#0f766e]"> Administración & Dirección </span>
                    <span class="text-xs text-slate-500 font-mono">· Estimación Arancelaria</span>
                </div>
                <h1 class="text-2xl font-black tracking-tight text-slate-900 dark:text-white font-heading mt-1">Generador de Presupuestos</h1>
                <p class="text-xs text-slate-500 mt-0.5">Completá los datos a la izquierda. La vista previa editorial se actualiza en tiempo real lista para imprimir o descargar en PDF.</p>
            </div>

            <div class="flex items-center gap-2.5">
                <Button label="Nuevo (+1)" icon="pi pi-plus" severity="secondary" outlined size="small" class="text-xs font-semibold" title="Avanzar al siguiente número de presupuesto" @click="avanzarSiguienteNumero" />
                <Button label="Restablecer" icon="pi pi-refresh" severity="secondary" outlined size="small" class="text-xs" @click="resetDraft" />
                <Button label="Exportar PDF / Imprimir" icon="pi pi-print" size="small" class="text-xs font-semibold !bg-[#0f766e] !border-[#0f766e] hover:!bg-[#115e59] text-white shadow-sm" @click="exportPdf" />
            </div>
        </div>

        <!-- Layout Split-Pane -->
        <div class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start print:block print:w-full print:m-0 print:p-0">
            <!-- Panel Izquierdo: Formulario Reactivo (No se imprime) -->
            <div class="no-print xl:col-span-5">
                <PresupuestoForm v-model="draft" :pacientes="pacientes" :loading-pacientes="loadingPacientes" @step-number="handleStepNumber" />
            </div>

            <!-- Panel Derecho: Live Preview A4 Editorial (Se imprime) -->
            <div class="xl:col-span-7 flex justify-center print:block print:w-full print:m-0 print:p-0">
                <PresupuestoPreview :draft="draft" />
            </div>
        </div>
    </div>
</template>
