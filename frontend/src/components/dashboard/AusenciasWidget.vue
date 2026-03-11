<script setup>
import { ref, onMounted } from 'vue';
import api from '@/api/axios';

const ausencias = ref([]);

onMounted(async () => {
    try {
        const res = await api.get('/ausencias', { withCredentials: true });
        ausencias.value = res.data;
    } catch (err) {
        console.error('Error cargando ausencias:', err);
    }
});
</script>

<template>
    <div class="card">
        <div class="font-semibold text-xl mb-4">Ausencias / Bloqueos</div>
        <DataTable :value="ausencias" paginator :rows="5" responsiveLayout="scroll">
            <Column field="fecha_inicio" header="Inicio" :body="(r) => new Date(r.fecha_inicio).toLocaleDateString()" />
            <Column field="fecha_fin" header="Fin" :body="(r) => new Date(r.fecha_fin).toLocaleDateString()" />
            <Column field="motivo" header="Motivo" />
        </DataTable>
    </div>
</template>
