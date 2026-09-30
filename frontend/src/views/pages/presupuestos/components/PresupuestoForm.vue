<script setup>
import { computed, ref } from 'vue';
import Select from 'primevue/select';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';

const props = defineProps({
    modelValue: {
        type: Object,
        required: true
    },
    pacientes: {
        type: Array,
        default: () => []
    },
    loadingPacientes: {
        type: Boolean,
        default: false
    }
});

const emit = defineEmits(['update:modelValue', 'step-number']);

// Referencia local reactiva para vincular inputs
const form = computed({
    get: () => props.modelValue,
    set: (val) => emit('update:modelValue', val)
});

// Selector de paciente
const selectedPatient = ref(null);

const patientOptions = computed(() => {
    const list = props.pacientes.map((p) => ({
        label: `${p.apellido}, ${p.nombre} (DNI ${p.dni || 'S/D'}${p.cobertura ? ' - ' + p.cobertura : ''})`,
        value: p
    }));
    return [{ label: '— Cargar datos manualmente —', value: 'custom' }, ...list];
});

function onPatientSelect(option) {
    if (!option || option === 'custom') {
        return;
    }
    const p = option;
    form.value.patientName = `${p.apellido || ''}, ${p.nombre || ''}`.trim().replace(/^,|,$/g, '');
    form.value.patientDni = p.dni || '';
    form.value.patientCoverage = p.cobertura || 'Particular';
    if (p.diagnostico && !form.value.summary) {
        form.value.summary = p.diagnostico;
    }
}

// Manejo de condiciones como texto multilinea
const conditionsText = computed({
    get: () => (form.value.conditions || []).join('\n'),
    set: (val) => {
        form.value.conditions = val
            .split('\n')
            .map((c) => c.trim())
            .filter((c) => c.length > 0);
    }
});

// Modos de cobro estrictamente seleccionables (no escribibles)
const modalityOptions = ['Pago único', 'Por sesión', 'Abono módulo (10 sesiones)', 'Abono mensual', 'Arancel preferencial'];

function addSection() {
    form.value.sections.push({
        id: Date.now(),
        title: 'Nueva Prestación / Práctica',
        concept: '',
        items: '',
        subtotal: 0,
        type: 'Por sesión'
    });
}

function removeSection(index) {
    if (form.value.sections.length > 1) {
        form.value.sections.splice(index, 1);
    }
}
</script>

<template>
    <div class="space-y-5">
        <!-- 1. Paciente Destinatario -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <div class="flex items-center justify-between mb-3">
                <label class="text-xs font-bold uppercase tracking-wider text-slate-600 font-heading"> 1. Destinatario / Paciente </label>
                <span class="text-[10px] bg-[#f0fdfa] text-[#0f766e] border border-[#ccfbf1] font-semibold px-2 py-0.5 rounded"> Padrón CAU </span>
            </div>

            <div>
                <label class="block text-xs font-medium text-slate-700 mb-1 font-heading"> Buscar paciente en el sistema: </label>
                <Select
                    v-model="selectedPatient"
                    :options="patientOptions"
                    option-label="label"
                    option-value="value"
                    filter
                    filter-placeholder="Buscar por apellido, nombre o DNI..."
                    placeholder="Seleccionar paciente del padrón..."
                    class="w-full text-xs"
                    :loading="loadingPacientes"
                    @change="onPatientSelect($event.value)"
                />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                <div>
                    <label class="block text-[11px] font-medium text-slate-600">Nombre Completo</label>
                    <InputText v-model="form.patientName" type="text" placeholder="Ej. Gómez, Juan" class="w-full text-xs mt-0.5" />
                </div>
                <div>
                    <label class="block text-[11px] font-medium text-slate-600">DNI / Documento</label>
                    <InputText v-model="form.patientDni" type="text" placeholder="Ej. 34.890.122" class="w-full text-xs mt-0.5" />
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-medium text-slate-600">Cobertura Médica / Obra Social</label>
                    <InputText v-model="form.patientCoverage" type="text" placeholder="Ej. Particular / OSDE / IOMA" class="w-full text-xs mt-0.5" />
                </div>
            </div>
        </div>

        <!-- 2. Emisión y Profesional Responsable -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <label class="text-xs font-bold uppercase tracking-wider text-slate-600 font-heading block mb-3"> 2. Emisión y Profesional Actuante </label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                    <div class="flex items-center justify-between">
                        <label class="block text-[11px] font-medium text-slate-600">N.º de Presupuesto</label>
                        <div class="flex items-center gap-1">
                            <button type="button" class="w-5 h-5 flex items-center justify-center rounded border border-slate-300 text-slate-600 hover:bg-slate-100 text-[10px] font-bold" title="Restar 1 al número" @click="emit('step-number', -1)">
                                -
                            </button>
                            <button type="button" class="w-5 h-5 flex items-center justify-center rounded border border-slate-300 text-slate-600 hover:bg-slate-100 text-[10px] font-bold" title="Sumar 1 al número (+1)" @click="emit('step-number', 1)">
                                +
                            </button>
                        </div>
                    </div>
                    <InputText v-model="form.number" type="text" placeholder="CAU-2026-0040" class="w-full text-xs font-mono mt-0.5" />
                </div>
                <div>
                    <label class="block text-[11px] font-medium text-slate-600">Fecha de Emisión</label>
                    <InputText v-model="form.date" type="date" class="w-full text-xs mt-0.5" />
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-medium text-slate-600">Profesional o Área Responsable</label>
                    <InputText v-model="form.doctor" type="text" placeholder="Ej. Lic. Martín Gómez (Kinesiología - MP 4821)" class="w-full text-xs mt-0.5" />
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-medium text-slate-600">Diagnóstico / Concepto General del Plan</label>
                    <InputText v-model="form.summary" type="text" placeholder="Ej. Plan integral de rehabilitación kinefisiátrica y evaluación postural" class="w-full text-xs mt-0.5" />
                </div>
            </div>
        </div>

        <!-- 3. Prestaciones y Aranceles -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <div class="flex items-center justify-between mb-3">
                <label class="text-xs font-bold uppercase tracking-wider text-slate-600 font-heading"> 3. Prestaciones y Prácticas </label>
                <Button label="+ Agregar Prestación" text size="small" class="p-0 text-xs font-semibold text-[#0f766e] hover:text-[#115e59]" @click="addSection" />
            </div>

            <div class="space-y-4">
                <div v-for="(sec, idx) in form.sections" :key="sec.id || idx" class="border border-slate-200 rounded-lg p-3.5 bg-slate-50 relative space-y-2.5">
                    <div class="flex justify-between items-center">
                        <span class="text-[11px] font-bold text-[#0f766e] uppercase font-heading"> Prestación #{{ idx + 1 }} </span>
                        <Button v-if="form.sections.length > 1" label="Eliminar" severity="danger" text size="small" class="p-0 text-xs font-semibold text-rose-600 hover:text-rose-800" @click="removeSection(idx)" />
                    </div>

                    <div>
                        <label class="block text-[10px] font-medium text-slate-500 font-heading"> Título de la prestación </label>
                        <InputText v-model="sec.title" type="text" placeholder="Ej. Módulo de Rehabilitación Motora" class="w-full text-xs mt-0.5 bg-white" />
                    </div>

                    <div>
                        <label class="block text-[10px] font-medium text-slate-500 font-heading"> Concepto detallado </label>
                        <InputText v-model="sec.concept" type="text" placeholder="Ej. 10 sesiones de fisioterapia y gimnasio terapéutico" class="w-full text-xs mt-0.5 bg-white" />
                    </div>

                    <div>
                        <label class="block text-[10px] font-medium text-slate-500 font-heading"> Ítems incluidos (uno por renglón) </label>
                        <Textarea v-model="sec.items" rows="2" placeholder="Análisis postural inicial&#10;Ejercicios de reeducación muscular&#10;Informe de evolución final" class="w-full text-xs mt-0.5 font-mono bg-white" auto-resize />
                    </div>

                    <div class="grid grid-cols-2 gap-2.5">
                        <div>
                            <label class="block text-[10px] font-medium text-slate-500 font-heading"> Subtotal ($ ARS) </label>
                            <input
                                v-model.number="sec.subtotal"
                                type="number"
                                min="0"
                                step="100"
                                class="w-full text-xs rounded-md border border-slate-300 bg-white px-2.5 py-1.5 mt-0.5 font-mono text-slate-900 focus:border-[#0f766e] focus:ring-1 focus:ring-[#0f766e] outline-none"
                            />
                        </div>
                        <div>
                            <label class="block text-[10px] font-medium text-slate-500 font-heading"> Modalidad </label>
                            <Select v-model="sec.type" :options="modalityOptions" placeholder="Seleccionar..." class="w-full text-xs mt-0.5 bg-white" />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 4. Condiciones Generales -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <label class="text-xs font-bold uppercase tracking-wider text-slate-600 font-heading block mb-2"> 4. Condiciones, Medios de Pago y Vigencia </label>
            <p class="text-[11px] text-slate-500 mb-2">Escribí cada condición o término en una línea separada.</p>
            <Textarea v-model="conditionsText" rows="3" class="w-full text-xs font-mono" placeholder="Validez de la propuesta: 15 días corridos.&#10;Medios de pago: Transferencia bancaria o tarjeta en administración CAU." auto-resize />
        </div>
    </div>
</template>
