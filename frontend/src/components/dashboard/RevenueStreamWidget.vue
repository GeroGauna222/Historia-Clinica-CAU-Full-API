<script setup>
import { ref, onMounted } from 'vue';
import Chart from 'primevue/chart';
import api from '@/api/axios';

const chartData = ref({ labels: [], datasets: [] });
const chartOptions = ref({
    responsive: true,
    plugins: { legend: { display: false } }
});

onMounted(async () => {
    const res = await api.get('/dashboard/semanal', { withCredentials: true });
    const { labels, values } = res.data;

    chartData.value = {
        labels,
        datasets: [
            {
                label: 'Turnos por día',
                data: values,
                backgroundColor: '#3B82F6'
            }
        ]
    };
});
</script>

<template>
    <div class="card">
        <h2 class="font-semibold text-xl mb-4">Turnos confirmados por día</h2>
        <Chart type="bar" :data="chartData" :options="chartOptions" class="h-80" />
    </div>
</template>
