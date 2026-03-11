<script setup>
import { ref } from 'vue';

const turnos = ref([
    { paciente: 'Juan Pérez', fecha: '04/07/2025', hora: '09:00' },
    { paciente: 'Ana López', fecha: '04/07/2025', hora: '10:30' },
    { paciente: 'Luis Fernández', fecha: '05/07/2025', hora: '08:00' },
    { paciente: 'María Gómez', fecha: '05/07/2025', hora: '11:00' }
]);
</script>

<template>
    <div class="card">
        <div class="font-semibold text-xl mb-4">Próximos turnos</div>
        <ul class="p-0 m-0 list-none">
            <li v-for="t in turnos" :key="t.paciente + t.fecha" class="flex justify-between py-2 border-b border-surface">
                <div>
                    <span class="block font-medium text-surface-900 dark:text-surface-0">{{ t.paciente }}</span>
                    <small class="text-muted-color">{{ t.fecha }} — {{ t.hora }}</small>
                </div>
                <Button icon="pi pi-calendar" class="p-button-text p-button-plain p-button-rounded" />
            </li>
        </ul>
    </div>
</template>
