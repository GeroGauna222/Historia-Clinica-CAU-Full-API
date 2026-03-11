<script setup>
import { ref } from 'vue';
import { useUserStore } from '@/stores/user';
import { useToast } from 'primevue/usetoast';

import Dropdown from 'primevue/dropdown';
import Button from 'primevue/button';
import Card from 'primevue/card';

const userStore = useUserStore();
const toast = useToast();

const opciones = [
    { label: '5 minutos', value: 5 },
    { label: '10 minutos', value: 10 },
    { label: '15 minutos', value: 15 },
    { label: '20 minutos', value: 20 },
    { label: '30 minutos', value: 30 },
    { label: '45 minutos', value: 45 },
    { label: '60 minutos', value: 60 }
];

const duracion = ref(userStore.duracion_turno);

const guardar = async () => {
    await userStore.actualizarDuracion(duracion.value);

    toast.add({
        severity: 'success',
        summary: 'Duración actualizada',
        detail: `Los turnos ahora tendrán ${duracion.value} minutos.`,
        life: 3000
    });
};
</script>

<template>
    <div class="p-4">
        <Card>
            <template #title> Configuración de Turnos </template>

            <template #content>
                <p class="mb-3">Duración de cada turno del profesional</p>

                <Dropdown v-model="duracion" :options="opciones" optionLabel="label" optionValue="value" class="w-full mt-3" />

                <Button class="mt-4" label="Guardar" icon="pi pi-save" @click="guardar" />
            </template>
        </Card>
    </div>
</template>
