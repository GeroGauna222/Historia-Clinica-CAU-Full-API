<script setup>
import { computed, ref } from 'vue';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import { usePacientesPresentes } from '@/layout/composables/usePacientesPresentes';

const { pendientes, marcarInformado, llamarYMarcar } = usePacientesPresentes();

const llamandoId = ref(null);
const errorLlamado = ref('');

// Llamar a un paciente lo da por informado solo a él; si falla, sigue pendiente.
async function llamar(t) {
    errorLlamado.value = '';
    llamandoId.value = t.id;
    try {
        await llamarYMarcar(t);
    } catch (e) {
        errorLlamado.value = e?.response?.data?.error || e?.response?.data?.message || 'No se pudo llamar al paciente. Reintentá.';
    } finally {
        llamandoId.value = null;
    }
}

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
                    <div class="flex items-center justify-between gap-3">
                        <p class="text-lg font-bold text-color">{{ t.paciente }}</p>
                        <Button label="Llamar" icon="pi pi-megaphone" size="small" :aria-label="`Llamar a ${t.paciente}`" :loading="llamandoId === t.id" :disabled="llamandoId !== null && llamandoId !== t.id" @click="llamar(t)" />
                    </div>
                    <div class="mt-1 flex items-center gap-3 text-sm text-muted-color">
                        <span class="font-mono">{{ formatoHora(t.start) }}</span>
                        <span v-if="t.dni">DNI: {{ t.dni }}</span>
                    </div>
                </div>
            </div>

            <p v-if="errorLlamado" class="w-full text-sm text-status-sin-aviso-fg" role="alert">{{ errorLlamado }}</p>

            <Button label="Informado" class="w-full" @click="marcarInformado" />
        </div>
    </Dialog>
</template>
