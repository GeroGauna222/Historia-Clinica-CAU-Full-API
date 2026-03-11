<script setup>
defineProps({ stats: Object });
</script>

<template>
    <div class="col-span-12 lg:col-span-6 xl:col-span-3" v-if="stats">
        <div class="card mb-0">
            <div class="flex justify-between mb-4">
                <div>
                    <span class="block text-muted-color font-medium mb-4">Turnos del día</span>
                    <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">
                        {{ stats.turnos_hoy }}
                    </div>
                </div>
                <div class="flex items-center justify-center bg-blue-100 rounded-border" style="width: 2.5rem; height: 2.5rem">
                    <i class="pi pi-calendar text-blue-500 !text-xl"></i>
                </div>
            </div>
            <span class="text-primary font-medium">+{{ stats.turnos_hoy || 0 }}</span>
            <span class="text-muted-color"> programados hoy</span>
        </div>
    </div>

    <div class="col-span-12 lg:col-span-6 xl:col-span-3">
        <div class="card mb-0">
            <div class="flex justify-between mb-4">
                <div>
                    <span class="block text-muted-color font-medium mb-4">Próximo turno</span>
                    <div class="text-surface-900 dark:text-surface-0 font-medium text-xl">
                        {{ stats.proximo_turno?.paciente || '—' }}
                    </div>
                </div>
                <div class="flex items-center justify-center bg-green-100 rounded-border" style="width: 2.5rem; height: 2.5rem">
                    <i class="pi pi-user text-green-500 !text-xl"></i>
                </div>
            </div>
            <span class="text-primary font-medium">{{ stats.proximo_turno?.hora || '' }}</span>
            <span class="text-muted-color"> próximo paciente</span>
        </div>
    </div>
</template>
