<script setup>
defineProps({
    label: { type: String, required: true },
    value: { type: [String, Number], required: true },
    icon: { type: String, default: '' },
    hint: { type: String, default: '' }
});
</script>

<template>
    <div class="card !mb-0 flex items-start justify-between gap-4 !p-5">
        <div class="flex flex-col gap-1">
            <span class="text-sm font-medium text-muted-color">{{ label }}</span>
            <span class="text-3xl font-semibold text-color">{{ value }}</span>
            <span v-if="hint" class="text-sm text-muted-color">{{ hint }}</span>
        </div>
        <span v-if="icon" class="flex h-10 w-10 items-center justify-center rounded-border bg-highlight">
            <i :class="icon" class="text-lg" aria-hidden="true" />
        </span>
    </div>
</template>
