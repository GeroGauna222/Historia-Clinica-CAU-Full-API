<script setup>
// Rendered by FullCalendar's #eventContent slot inside a detached Vue app (no appContext):
// use plain elements and global CSS classes only, never PrimeVue components or plugins.
import { computed } from 'vue';
import { barColor, eventStatus, formatTime, isAusencia, isBackgroundEvent, isGrupal, statusLabel } from './agendaEventStyle';

const props = defineProps({
    arg: { type: Object, required: true }
});

const event = computed(() => props.arg.event);
const extended = computed(() => event.value.extendedProps || {});
const background = computed(() => isBackgroundEvent(event.value));
const month = computed(() => String(props.arg.view?.type || '').startsWith('dayGrid'));
const status = computed(() => eventStatus(event.value));
const grupal = computed(() => isGrupal(event.value));
const ausencia = computed(() => isAusencia(event.value));
const time = computed(() => formatTime(event.value.start));

const name = computed(() => {
    if (ausencia.value) return extended.value.tipoEvento || 'Ausencia';
    return extended.value.paciente || event.value.title || '';
});

const detail = computed(() => {
    if (ausencia.value) return extended.value.profesional || '';
    if (grupal.value) return extended.value.grupoNombre || extended.value.profesional || '';
    return extended.value.description || '';
});

const label = computed(() => {
    const kind = ausencia.value ? 'Ausencia' : statusLabel(status.value);
    return [kind, time.value, name.value, detail.value].filter(Boolean).join(', ');
});

const struck = computed(() => !ausencia.value && status.value === 'sin-aviso');

const cardStyle = computed(() => {
    const color = barColor(event.value);
    return color ? { '--evt-bar': color } : undefined;
});

const backgroundLabel = computed(() => (extended.value.tipo === 'ausencia_bg' ? 'Ausencia' : ''));
</script>

<template>
    <span v-if="background" class="bg-hatch-label">{{ backgroundLabel }}</span>
    <div v-else-if="month" class="evt-card evt-card--month" :style="cardStyle" role="group" :aria-label="label">
        <span class="evt-dot" aria-hidden="true"></span>
        <span class="evt-time">{{ time }}</span>
        <i v-if="grupal" class="pi pi-users evt-icon" aria-hidden="true"></i>
        <span class="evt-name" :class="{ 'evt-name--struck': struck }">{{ name }}</span>
    </div>
    <div v-else class="evt-card" :style="cardStyle" role="group" :aria-label="label">
        <div class="evt-line">
            <span class="evt-time">{{ time }}</span>
            <i v-if="grupal" class="pi pi-users evt-icon" aria-hidden="true"></i>
            <span class="evt-name" :class="{ 'evt-name--struck': struck }">{{ name }}</span>
        </div>
        <div v-if="detail" class="evt-detail">{{ detail }}</div>
    </div>
</template>
