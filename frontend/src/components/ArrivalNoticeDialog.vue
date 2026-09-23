<script setup>
import { computed } from 'vue';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import { usePacientesPresentes } from '@/layout/composables/usePacientesPresentes';

const { pendientes, marcarInformado } = usePacientesPresentes();

const visible = computed(() => pendientes.value.length > 0);

const titulo = computed(() => {
    const n = pendientes.value.length;
    return n === 1 ? 'Paciente en recepción' : `${n} pacientes en recepción`;
});

function formatoHora(isoString) {
    if (!isoString) return '';
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
}
</script>

<template>
    <Dialog :visible="visible" modal :closable="false" :closeOnEscape="false" :dismissableMask="false" :draggable="false" :style="{ width: '32rem', maxWidth: '92vw' }">
        <div class="flex flex-col items-center gap-4 py-2 text-center">
            <div class="flex h-16 w-16 items-center justify-center rounded-full bg-highlight text-primary">
                <i class="pi pi-bell text-3xl"></i>
            </div>

            <h2 class="text-xl font-bold text-color">{{ titulo }}</h2>

            <div class="w-full divide-y divide-line text-left">
                <div v-for="t in pendientes" :key="t.id" class="py-3">
                    <p class="text-lg font-bold text-color">{{ t.paciente }}</p>
                    <div class="mt-1 flex items-center gap-3 text-sm text-muted-color">
                        <span class="font-mono">{{ formatoHora(t.start) }}</span>
                        <span v-if="t.dni">DNI: {{ t.dni }}</span>
                    </div>
                </div>
            </div>

            <Button label="Informado" class="w-full" @click="marcarInformado" />
        </div>
    </Dialog>
</template>
