<script setup>
import { computed } from 'vue';

// DB enums: turnos.estado_asistencia and evoluciones.estado_firma.
const STATUS_MAP = {
    programado: { token: 'programado', label: 'Programado' },
    presente: { token: 'presente', label: 'Presente' },
    con_aviso: { token: 'con-aviso', label: 'Ausente con aviso' },
    sin_aviso: { token: 'sin-aviso', label: 'Ausente sin aviso' },
    firmada: { token: 'presente', label: 'Firmada' },
    pendiente: { token: 'con-aviso', label: 'Firma pendiente' }
};

const props = defineProps({
    status: { type: String, required: true },
    label: { type: String, default: '' },
    size: { type: String, default: 'md', validator: (value) => ['sm', 'md'].includes(value) }
});

const entry = computed(() => STATUS_MAP[props.status] ?? { token: 'programado', label: props.status });

const style = computed(() => {
    const token = entry.value.token;
    return {
        color: `var(--cau-status-${token}-fg)`,
        backgroundColor: `var(--cau-status-${token}-bg)`,
        borderColor: `var(--cau-status-${token}-border)`
    };
});

const sizeClass = computed(() => (props.size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'));
</script>

<template>
    <span class="inline-flex items-center gap-1 whitespace-nowrap rounded-full border font-medium" :class="sizeClass" :style="style" :data-status="entry.token">{{ label || entry.label }}</span>
</template>
