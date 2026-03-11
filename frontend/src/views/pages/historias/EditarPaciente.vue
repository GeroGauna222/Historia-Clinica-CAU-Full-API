<script setup>
import PacienteForm from '@/components/PacienteForm.vue';
import pacienteService from '@/service/pacienteService';
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

const paciente = ref({});

onMounted(async () => {
    const res = await pacienteService.getPaciente(route.params.id);
    const p = res.data;

    // Convertir fecha si existe
    if (p.fecha_nacimiento) {
        try {
            const fecha = new Date(p.fecha_nacimiento);
            // aseguramos formato YYYY-MM-DD
            p.fecha_nacimiento = fecha.toISOString().split('T')[0];
        } catch (e) {
            console.warn('Error al parsear fecha:', p.fecha_nacimiento);
        }
    }

    paciente.value = p;
});

const actualizarPaciente = async (data) => {
    await pacienteService.updatePaciente(route.params.id, data);
    router.push('/pacientes');
};
</script>

<template>
    <div class="p-4">
        <h1 class="text-2xl font-bold mb-4">Editar Paciente</h1>
        <PacienteForm :paciente="paciente" :onSubmit="actualizarPaciente" submitText="Guardar Cambios" />
    </div>
</template>
