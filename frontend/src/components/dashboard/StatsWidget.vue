<script setup>
import { ref } from 'vue';

const totalPacientes = ref(230);
const totalHistorias = ref(185);
const totalTurnos = ref(67);
const totalUsuarios = ref(12);
</script>

<template>
    <div class="col-span-12 lg:col-span-6 xl:col-span-3">
        <div class="card mb-0">
            <div class="flex justify-between mb-4">
                <div>
                    <span class="block text-muted-color font-medium mb-4">Pacientes</span>
                    <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">{{ totalPacientes }}</div>
                </div>
                <div class="flex items-center justify-center bg-blue-100 dark:bg-blue-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                    <i class="pi pi-users text-blue-500 !text-xl"></i>
                </div>
            </div>
            <span class="text-primary font-medium">+5 </span>
            <span class="text-muted-color">registrados hoy</span>
        </div>
    </div>

    <div class="col-span-12 lg:col-span-6 xl:col-span-3">
        <div class="card mb-0">
            <div class="flex justify-between mb-4">
                <div>
                    <span class="block text-muted-color font-medium mb-4">Historias Clínicas</span>
                    <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">{{ totalHistorias }}</div>
                </div>
                <div class="flex items-center justify-center bg-green-100 dark:bg-green-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                    <i class="pi pi-file text-green-500 !text-xl"></i>
                </div>
            </div>
            <span class="text-primary font-medium">+3 </span>
            <span class="text-muted-color">actualizadas hoy</span>
        </div>
    </div>

    <div class="col-span-12 lg:col-span-6 xl:col-span-3">
        <div class="card mb-0">
            <div class="flex justify-between mb-4">
                <div>
                    <span class="block text-muted-color font-medium mb-4">Turnos Activos</span>
                    <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">{{ totalTurnos }}</div>
                </div>
                <div class="flex items-center justify-center bg-orange-100 dark:bg-orange-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                    <i class="pi pi-calendar text-orange-500 !text-xl"></i>
                </div>
            </div>
            <span class="text-primary font-medium">+2 </span>
            <span class="text-muted-color">hoy</span>
        </div>
    </div>

    <div class="col-span-12 lg:col-span-6 xl:col-span-3">
        <div class="card mb-0">
            <div class="flex justify-between mb-4">
                <div>
                    <span class="block text-muted-color font-medium mb-4">Usuarios</span>
                    <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">{{ totalUsuarios }}</div>
                </div>
                <div class="flex items-center justify-center bg-purple-100 dark:bg-purple-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                    <i class="pi pi-user text-purple-500 !text-xl"></i>
                </div>
            </div>
            <span class="text-primary font-medium">1 </span>
            <span class="text-muted-color">nuevo esta semana</span>
        </div>
    </div>
</template>
