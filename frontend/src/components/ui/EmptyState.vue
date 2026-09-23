<script setup>
defineProps({
    icon: { type: String, default: 'pi pi-inbox' },
    title: { type: String, required: true },
    message: { type: String, default: '' }
});
</script>

<template>
    <div role="status" class="flex flex-col items-center justify-center gap-2 px-4 py-12 text-center">
        <i :class="icon" class="text-4xl text-muted-color" aria-hidden="true" />
        <p class="m-0 text-lg font-semibold text-color">{{ title }}</p>
        <p v-if="message" class="m-0 max-w-md text-sm text-muted-color">{{ message }}</p>
        <div v-if="$slots.action" class="mt-2">
            <slot name="action" />
        </div>
    </div>
</template>
