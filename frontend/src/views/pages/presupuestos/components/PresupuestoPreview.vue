<script setup>
import { computed } from 'vue';
import logoCauUnsam from '@/assets/logo_cau_unsam2.png';
import cauIcon from '@/assets/cau_icon.png';

const props = defineProps({
    draft: {
        type: Object,
        required: true
    }
});

const formattedDate = computed(() => {
    if (!props.draft.date) return '';
    try {
        const [year, month, day] = props.draft.date.split('-');
        if (!year || !month || !day) return props.draft.date;
        const d = new Date(Number(year), Number(month) - 1, Number(day));
        return d.toLocaleDateString('es-AR', {
            day: '2-digit',
            month: 'long',
            year: 'numeric'
        });
    } catch {
        return props.draft.date;
    }
});

function formatMoney(amount) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2
    }).format(Number(amount) || 0);
}

const grandTotal = computed(() => {
    if (!props.draft.sections || !Array.isArray(props.draft.sections)) return 0;
    return props.draft.sections.reduce((acc, sec) => acc + (Number(sec.subtotal) || 0), 0);
});

function parseItems(itemsText) {
    if (!itemsText) return [];
    if (Array.isArray(itemsText))
        return itemsText
            .map(String)
            .map((i) => i.trim())
            .filter((i) => i.length > 0);
    return String(itemsText)
        .split('\n')
        .map((i) => i.trim())
        .filter((i) => i.length > 0);
}
</script>

<template>
    <div class="print-sheet-area flex justify-center w-full">
        <article class="print-sheet relative isolate overflow-hidden w-full max-w-[760px] bg-white text-slate-900 p-7 sm:p-9 shadow-xl ring-1 ring-slate-200 rounded-sm">
            <!-- Watermark / Halftone Corner en Teal CAU (#0f766e) -->
            <div class="halftone-cau pointer-events-none absolute top-0 right-0 z-0 h-36 w-36 opacity-75"></div>

            <div class="relative z-10 flex flex-col min-h-[820px] print:min-h-0 print:h-auto justify-between">
                <div>
                    <!-- Header Institucional CAU / UNSAM -->
                    <header class="border-b-2 border-slate-900 pb-3.5">
                        <div class="flex items-start justify-between gap-4">
                            <div class="flex items-center gap-3">
                                <img :src="logoCauUnsam" alt="CAU UNSAM" class="h-10 w-auto max-w-[160px] object-contain shrink-0" @error="(e) => (e.target.src = cauIcon)" />
                                <div class="border-l border-slate-300 pl-2.5">
                                    <h2 class="text-xs font-black tracking-tight text-slate-900 font-heading uppercase leading-tight">Centro Asistencial Universitario</h2>
                                    <p class="text-[10px] font-medium text-[#0f766e] mt-0.5 tracking-wide font-sans">Universidad Nacional de San Martín · UNSAM</p>
                                </div>
                            </div>

                            <div class="text-right">
                                <p v-if="draft.number" class="text-xs font-mono font-bold tracking-wider text-slate-900 uppercase">N.º {{ draft.number }}</p>
                                <p class="text-[10px] font-mono text-slate-500 uppercase mt-0.5">
                                    {{ formattedDate }}
                                </p>
                            </div>
                        </div>

                        <div class="mt-4 flex items-baseline justify-between">
                            <div>
                                <span class="text-[10px] font-bold tracking-widest text-[#0f766e] uppercase block font-heading"> Documento de Estimación Clínica </span>
                                <h1 class="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 uppercase font-heading">Presupuesto</h1>
                            </div>
                            <span class="text-[11px] font-semibold px-2 py-0.5 bg-slate-100 text-slate-800 border border-slate-300 uppercase tracking-widest font-heading rounded"> Validez Oficial </span>
                        </div>
                    </header>

                    <!-- Datos del Paciente y Clínicos -->
                    <section class="mt-3.5 border-b border-slate-900 pb-3">
                        <div class="grid grid-cols-2 gap-y-2 text-xs font-sans">
                            <div>
                                <span class="text-slate-500 font-medium uppercase text-[10px] tracking-wider block font-heading"> Destinatario / Paciente </span>
                                <strong class="text-sm font-bold text-slate-900 font-heading">
                                    {{ draft.patientName || '—' }}
                                </strong>
                            </div>
                            <div>
                                <span class="text-slate-500 font-medium uppercase text-[10px] tracking-wider block font-heading"> Documento (DNI) </span>
                                <span class="font-mono text-slate-800 font-medium">
                                    {{ draft.patientDni || '—' }}
                                </span>
                            </div>
                            <div>
                                <span class="text-slate-500 font-medium uppercase text-[10px] tracking-wider block font-heading"> Cobertura Médica </span>
                                <span class="text-slate-800 font-medium">
                                    {{ draft.patientCoverage || 'Particular' }}
                                </span>
                            </div>
                            <div>
                                <span class="text-slate-500 font-medium uppercase text-[10px] tracking-wider block font-heading"> Profesional / Especialidad </span>
                                <span class="text-[#0f766e] font-semibold">
                                    {{ draft.doctor || '—' }}
                                </span>
                            </div>
                        </div>

                        <div v-if="draft.summary" class="mt-2.5 pt-2 border-t border-dashed border-slate-300">
                            <span class="text-slate-500 font-medium uppercase text-[10px] tracking-wider block font-heading"> Concepto General / Plan de Trabajo </span>
                            <p class="text-xs text-slate-700 mt-0.5 leading-relaxed font-sans">
                                {{ draft.summary }}
                            </p>
                        </div>
                    </section>

                    <!-- Prestaciones y Prácticas -->
                    <section class="mt-3.5 space-y-3">
                        <div v-for="(sec, idx) in draft.sections" :key="sec.id || idx" class="border-t border-slate-900 pt-2.5">
                            <div class="flex items-baseline justify-between">
                                <h3 class="text-xs font-bold text-slate-900 uppercase tracking-tight font-heading">
                                    {{ sec.title || `Prestación #${idx + 1}` }}
                                </h3>
                                <span class="text-[10px] font-mono font-semibold uppercase text-[#0f766e] bg-[#f0fdfa] px-1.5 py-0.5 rounded border border-[#ccfbf1]">
                                    {{ sec.type || 'Pago único' }}
                                </span>
                            </div>

                            <p v-if="sec.concept" class="text-xs font-semibold text-slate-700 mt-0.5 font-sans">Concepto: {{ sec.concept }}</p>

                            <ul v-if="parseItems(sec.items).length > 0" class="mt-1.5 border-t border-slate-200">
                                <li v-for="(item, iIdx) in parseItems(sec.items)" :key="iIdx" class="border-b border-slate-200 py-0.5 text-[11px] text-slate-800 font-sans">
                                    {{ item }}
                                </li>
                            </ul>

                            <div class="flex items-baseline justify-between pt-1.5 text-xs font-bold text-slate-900">
                                <span class="font-heading text-[11px]">Subtotal</span>
                                <span class="font-mono text-xs tabular-nums text-slate-950">
                                    {{ formatMoney(sec.subtotal) }}
                                </span>
                            </div>
                        </div>
                    </section>

                    <!-- Total General con Acento CAU -->
                    <div class="mt-4 border-t-2 border-slate-900 pt-2.5">
                        <div class="flex items-baseline justify-between">
                            <div>
                                <span class="uppercase tracking-wider text-xs font-bold text-slate-600 block font-heading"> Total Presupuestado </span>
                                <span class="text-[10px] text-slate-500 font-mono"> Aranceles expresados en Pesos Argentinos (ARS) </span>
                            </div>
                            <span class="text-xl font-mono tracking-tight font-extrabold text-[#0f766e] tabular-nums">
                                {{ formatMoney(grandTotal) }}
                            </span>
                        </div>
                    </div>

                    <!-- Condiciones y Modalidad de Pago -->
                    <section v-if="draft.conditions && draft.conditions.length > 0" class="mt-3.5 border-t border-slate-300 pt-2 text-[10.5px] text-slate-700">
                        <h4 class="font-bold text-[11px] uppercase tracking-wider text-slate-900 mb-1 font-heading">Condiciones Generales y Medios de Pago</h4>
                        <ul class="list-disc pl-4 space-y-0.5 text-slate-600 leading-normal font-sans">
                            <li v-for="(cond, cIdx) in draft.conditions" :key="cIdx">
                                {{ cond }}
                            </li>
                        </ul>
                    </section>
                </div>

                <!-- Pie Institucional -->
                <footer class="mt-6 pt-3 border-t border-slate-200">
                    <div class="flex justify-between items-center text-[10px] text-slate-500 font-sans">
                        <div>
                            <p class="font-bold text-slate-700 font-heading">Centro Asistencial Universitario · UNSAM</p>
                            <p>Campus Miguelete · San Martín, Pcia. de Buenos Aires · cau@unsam.edu.ar</p>
                        </div>
                        <div class="text-right">
                            <p class="font-mono text-slate-400">Comprobante de presupuesto no válido como factura</p>
                        </div>
                    </div>
                </footer>
            </div>
        </article>
    </div>
</template>

<style scoped>
.halftone-cau {
    background-image: radial-gradient(circle, #0f766e 1.2px, transparent 1.3px);
    background-size: 8px 8px;
    mask-image: radial-gradient(ellipse 90% 80% at 100% 0%, black 15%, transparent 75%);
    -webkit-mask-image: radial-gradient(ellipse 90% 80% at 100% 0%, black 15%, transparent 75%);
}

@media print {
    /* Suprime cabecera/pie nativos del navegador (URL, fecha/hora, título) */
    @page {
        size: A4 portrait;
        margin: 0;
    }

    :global(html),
    :global(body) {
        background: white !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        height: auto !important;
        min-height: 0 !important;
    }

    :global(.layout-wrapper),
    :global(.layout-main-container),
    :global(.layout-main),
    :global(.layout-main > div) {
        background: white !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        min-height: 0 !important;
        height: auto !important;
        display: block !important;
    }

    /* Ocultar elementos de navegación y pie de página de la aplicación */
    :global(.layout-sidebar),
    :global(.layout-topbar),
    :global(.layout-mask),
    :global(.app-footer),
    :global(footer.app-footer),
    :global(.p-toast),
    :global(.no-print) {
        display: none !important;
    }

    /* Contenedor en flujo normal para evitar replicación de elementos fijos en multipágina */
    .print-sheet-area {
        display: block !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        position: static !important;
        background: white !important;
    }

    .print-sheet {
        position: static !important;
        box-shadow: none !important;
        border: none !important;
        border-radius: 0 !important;
        width: 210mm !important;
        max-width: 210mm !important;
        margin: 0 auto !important;
        padding: 12mm 16mm 10mm 16mm !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        page-break-after: avoid !important;
        page-break-before: avoid !important;
        page-break-inside: avoid !important;
        break-after: avoid !important;
        break-before: avoid !important;
        break-inside: avoid !important;
    }
}
</style>
