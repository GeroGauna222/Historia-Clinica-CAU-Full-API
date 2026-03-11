<script setup>
import PacienteForm from '@/components/PacienteForm.vue';
import pacienteService from '@/service/pacienteService';
import { useRouter } from 'vue-router';

const router = useRouter();

const crearPaciente = async (data) => {
    await pacienteService.crearPaciente(data);
    router.push('/pacientes');
};
</script>

<template>
    <div class="p-4">
        <h1 class="text-2xl font-bold mb-4">Registrar Paciente</h1>
        <PacienteForm :onSubmit="crearPaciente" submitText="Registrar" />
    </div>
</template>
