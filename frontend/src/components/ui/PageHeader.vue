<script setup>
defineProps({
    title: { type: String, required: true },
    subtitle: { type: String, default: '' }
});
</script>

<template>
    <header class="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div class="flex flex-col gap-1">
            <slot name="breadcrumb" />
            <h1 class="m-0 text-3xl font-semibold text-color">{{ title }}</h1>
            <p v-if="subtitle" class="m-0 text-base text-muted-color">{{ subtitle }}</p>
        </div>
        <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
            <slot name="actions" />
        </div>
    </header>
</template>
