<script setup>
import { computed, ref } from 'vue';
import Button from 'primevue/button';
import Menu from 'primevue/menu';
import { useColorScheme } from '@/theme/useColorScheme';

const OPTIONS = [
    { mode: 'system', label: 'Sistema', icon: 'pi pi-desktop' },
    { mode: 'light', label: 'Claro', icon: 'pi pi-sun' },
    { mode: 'dark', label: 'Oscuro', icon: 'pi pi-moon' }
];

const { mode, setMode } = useColorScheme();
const menu = ref(null);

const current = computed(() => OPTIONS.find((option) => option.mode === mode.value) ?? OPTIONS[0]);

const items = computed(() =>
    OPTIONS.map((option) => ({
        label: option.label,
        icon: option.icon,
        mode: option.mode,
        command: () => setMode(option.mode)
    }))
);

function toggle(event) {
    menu.value.toggle(event);
}
</script>

<template>
    <Button type="button" text rounded severity="secondary" :icon="current.icon" :aria-label="`Tema: ${current.label}`" aria-haspopup="true" aria-controls="color-scheme-menu" @click="toggle" />
    <Menu id="color-scheme-menu" ref="menu" :model="items" popup>
        <template #item="{ item, props }">
            <a v-bind="props.action" class="flex items-center gap-2" :aria-label="`Tema ${item.label}`" :aria-current="item.mode === mode ? 'true' : undefined">
                <span :class="item.icon" />
                <span :class="item.mode === mode ? 'font-semibold text-primary' : 'text-color'">{{ item.label }}</span>
                <i v-if="item.mode === mode" class="pi pi-check ml-auto text-primary" />
            </a>
        </template>
    </Menu>
</template>
