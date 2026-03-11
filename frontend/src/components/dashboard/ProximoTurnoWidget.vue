<script setup>
defineProps({ turno: Object });
</script>

<template>
    <div class="card">
        <div class="font-semibold text-xl mb-4">Próximo Turno</div>
        <div v-if="turno">
            <p><b>Paciente:</b> {{ turno.paciente }}</p>
            <p><b>Hora:</b> {{ new Date(turno.fecha).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</p>
            <p><b>Motivo:</b> {{ turno.motivo }}</p>
        </div>
        <div v-else class="text-gray-500">No hay turnos próximos</div>
    </div>
</template>
