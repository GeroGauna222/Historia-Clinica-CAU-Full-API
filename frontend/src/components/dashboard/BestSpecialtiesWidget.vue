<script setup>
import { ref } from 'vue';

const especialidades = ref([
    { nombre: 'Clínica Médica', porcentaje: 35 },
    { nombre: 'Cardiología', porcentaje: 25 },
    { nombre: 'Pediatría', porcentaje: 20 },
    { nombre: 'Ginecología', porcentaje: 10 },
    { nombre: 'Dermatología', porcentaje: 10 }
]);
</script>

<template>
    <div class="card">
        <div class="font-semibold text-xl mb-4">Especialidades más consultadas</div>
        <ul class="p-0 m-0 list-none">
            <li v-for="esp in especialidades" :key="esp.nombre" class="flex justify-between py-2 border-b border-surface">
                <span>{{ esp.nombre }}</span>
                <span class="font-bold text-primary">{{ esp.porcentaje }}%</span>
            </li>
        </ul>
    </div>
</template>
