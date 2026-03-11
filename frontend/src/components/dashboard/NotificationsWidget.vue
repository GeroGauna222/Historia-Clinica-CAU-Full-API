<script setup>
import { ref } from 'vue';

const menu = ref(null);

const items = ref([
    { label: 'Marcar todas como leídas', icon: 'pi pi-fw pi-check' },
    { label: 'Eliminar notificaciones', icon: 'pi pi-fw pi-trash' }
]);
</script>

<template>
    <div class="card">
        <div class="flex items-center justify-between mb-6">
            <div class="font-semibold text-xl">Notificaciones</div>
            <div>
                <Button icon="pi pi-ellipsis-v" class="p-button-text p-button-plain p-button-rounded" @click="$refs.menu.toggle($event)"></Button>
                <Menu ref="menu" popup :model="items" class="!min-w-40"></Menu>
            </div>
        </div>

        <span class="block text-muted-color font-medium mb-4">HOY</span>
        <ul class="p-0 mx-0 mt-0 mb-6 list-none">
            <li class="flex items-center py-2 border-b border-surface">
                <div class="w-12 h-12 flex items-center justify-center bg-green-100 dark:bg-green-400/10 rounded-full mr-4 shrink-0">
                    <i class="pi pi-check-square !text-xl text-green-500"></i>
                </div>
                <span class="text-surface-900 dark:text-surface-0 leading-normal">Se creó la historia clínica de <strong>Juan Pérez</strong>.</span>
            </li>
            <li class="flex items-center py-2">
                <div class="w-12 h-12 flex items-center justify-center bg-blue-100 dark:bg-blue-400/10 rounded-full mr-4 shrink-0">
                    <i class="pi pi-calendar !text-xl text-blue-500"></i>
                </div>
                <span class="text-surface-900 dark:text-surface-0 leading-normal">Nuevo turno confirmado para <strong>María Gómez</strong>.</span>
            </li>
        </ul>

        <span class="block text-muted-color font-medium mb-4">AYER</span>
        <ul class="p-0 m-0 list-none mb-6">
            <li class="flex items-center py-2 border-b border-surface">
                <div class="w-12 h-12 flex items-center justify-center bg-orange-100 dark:bg-orange-400/10 rounded-full mr-4 shrink-0">
                    <i class="pi pi-user-edit !text-xl text-orange-500"></i>
                </div>
                <span class="text-surface-900 dark:text-surface-0 leading-normal">Actualización en la ficha de <strong>Luis Fernández</strong>.</span>
            </li>
            <li class="flex items-center py-2">
                <div class="w-12 h-12 flex items-center justify-center bg-purple-100 dark:bg-purple-400/10 rounded-full mr-4 shrink-0">
                    <i class="pi pi-envelope !text-xl text-purple-500"></i>
                </div>
                <span class="text-surface-900 dark:text-surface-0 leading-normal">Mensaje recibido de <strong>Dr. García</strong>.</span>
            </li>
        </ul>
    </div>
</template>
