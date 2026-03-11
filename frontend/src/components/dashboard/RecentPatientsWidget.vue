<script setup>
import { ref } from 'vue';

const pacientes = ref([
    { nombre: 'Juan Pérez', edad: 45, fecha: '03/07/2025' },
    { nombre: 'María Gómez', edad: 32, fecha: '02/07/2025' },
    { nombre: 'Luis Fernández', edad: 56, fecha: '01/07/2025' },
    { nombre: 'Ana López', edad: 28, fecha: '01/07/2025' }
]);
</script>

<template>
    <div class="card">
        <div class="font-semibold text-xl mb-4">Pacientes recientes</div>
        <ul class="p-0 m-0 list-none">
            <li v-for="p in pacientes" :key="p.nombre" class="flex items-center justify-between py-2 border-b border-surface">
                <div>
                    <span class="block font-medium text-surface-900 dark:text-surface-0">{{ p.nombre }}</span>
                    <small class="text-muted-color">Edad: {{ p.edad }} — Ingresado: {{ p.fecha }}</small>
                </div>
                <Button icon="pi pi-eye" class="p-button-text p-button-plain p-button-rounded" />
            </li>
        </ul>
    </div>
</template>
