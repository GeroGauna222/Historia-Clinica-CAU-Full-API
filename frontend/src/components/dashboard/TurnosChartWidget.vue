<script setup>
import Chart from 'primevue/chart';
import { onMounted, ref } from 'vue';

const chartData = ref();
const chartOptions = ref();

onMounted(() => {
    chartData.value = {
        labels: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
        datasets: [
            {
                label: 'Turnos Confirmados',
                backgroundColor: '#42A5F5',
                data: [5, 7, 4, 6, 3]
            }
        ]
    };

    chartOptions.value = {
        responsive: true,
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: '#495057'
                }
            }
        },
        scales: {
            x: {
                ticks: { color: '#495057' },
                grid: { color: '#ebedef' }
            },
            y: {
                ticks: { color: '#495057' },
                grid: { color: '#ebedef' }
            }
        }
    };
});
</script>

<template>
    <div class="card">
        <div class="font-semibold text-xl mb-4">Turnos confirmados por día</div>
        <Chart type="bar" :data="chartData" :options="chartOptions" style="height: 300px" />
    </div>
</template>
