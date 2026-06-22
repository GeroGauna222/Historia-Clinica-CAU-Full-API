<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';
import { fechaRangoBonito, fechaBonitaDashboard } from '@/utils/formatDate';

import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import Avatar from 'primevue/avatar';

const router = useRouter();
const user = useUserStore();

const loading = ref(true);
const error = ref(null);
const dashboard = ref(null);

const esAdmin = computed(() => ['director', 'administrativo'].includes(user.rol?.toLowerCase().trim()));

const saludo = computed(() => {
    const hora = new Date().getHours();
    if (hora < 12) return 'Buenos dias';
    if (hora < 19) return 'Buenas tardes';
    return 'Buenas noches';
});

const resumenItems = computed(() => {
    const resumen = dashboard.value?.resumen || {};
    const base = [
        { label: 'Turnos hoy', value: resumen.turnos_hoy || 0, icon: 'pi pi-calendar', severity: 'info' },
        { label: 'Disponibles hoy', value: resumen.disponibilidad_hoy || 0, icon: 'pi pi-clock', severity: 'success' }
    ];

    if (!esAdmin.value) return base;

    return [...base, { label: 'Superpuestos', value: resumen.turnos_superpuestos || 0, icon: 'pi pi-exclamation-triangle', severity: 'warning' }];
});

const proximoEvento = computed(() => dashboard.value?.proximo_evento || null);
const turnosHoy = computed(() => dashboard.value?.turnos || []);
const disponibilidadHoy = computed(() => dashboard.value?.disponibilidad_hoy || []);
const comunicados = computed(() => dashboard.value?.comunicados || []);
const alertas = computed(() => dashboard.value?.alertas || {});
const ausenciasBloqueos = computed(() => dashboard.value?.ausencias_bloqueos || []);

const fetchDashboard = async () => {
    try {
        loading.value = true;
        error.value = null;
        const res = await api.get('/dashboard', { withCredentials: true });
        dashboard.value = res.data;
    } catch (err) {
        console.error('Error dashboard:', err);
        error.value = 'No se pudo cargar el inicio.';
    } finally {
        loading.value = false;
    }
};

const verHistoria = (turno) => {
    if (!turno?.paciente_id) return;
    router.push({ name: 'historiaPaciente', params: { id: turno.paciente_id } });
};

const inicialEvento = (evento) => {
    const texto = evento?.titulo || evento?.paciente || evento?.tipo || '?';
    return texto.charAt(0).toUpperCase();
};

const tagSeverityEvento = (tipo) => {
    const limpio = (tipo || '').toLowerCase();
    if (limpio === 'turno') return 'info';
    if (limpio === 'reunion') return 'success';
    if (limpio === 'ausencia') return 'danger';
    return 'warning';
};

const horaAgenda = (fecha) => {
    if (!fecha) return '-';
    const d = new Date(fecha);
    if (Number.isNaN(d.getTime())) return '-';
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

onMounted(fetchDashboard);
</script>

<template>
    <div class="p-6 md:p-8 w-full transition-colors">
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 dark:text-white">
                <span v-if="user.nombre">{{ saludo }}, {{ user.nombre.split(' ')[0] }}</span>
                <span v-else>Inicio</span>
            </h1>
            <p class="text-gray-500 dark:text-gray-400 text-base mt-1">Agenda y novedades relevantes para hoy.</p>
        </div>

        <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-gray-400">
            <i class="pi pi-spin pi-spinner text-4xl mb-3"></i>
            <p>Cargando informacion...</p>
        </div>

        <div v-else-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg flex items-center gap-3">
            <i class="pi pi-exclamation-triangle text-xl"></i>
            <span>{{ error }}</span>
        </div>

        <div v-else class="grid grid-cols-12 gap-6">
            <div v-for="item in resumenItems" :key="item.label" class="col-span-12 sm:col-span-6 xl:col-span-3">
                <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 shadow-sm rounded-lg p-5 h-full">
                    <div class="flex items-center justify-between gap-4">
                        <div>
                            <span class="block text-gray-500 dark:text-gray-400 text-sm font-medium mb-2">{{ item.label }}</span>
                            <div class="text-3xl font-bold text-gray-800 dark:text-white">{{ item.value }}</div>
                        </div>
                        <div class="w-11 h-11 rounded-lg bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                            <i :class="[item.icon, 'text-xl text-blue-500']"></i>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-12 xl:col-span-7">
                <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 shadow-sm rounded-lg p-6 h-full">
                    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                            <i class="pi pi-calendar text-blue-500"></i>
                            Turnos de Hoy
                        </h2>
                        <Tag :value="turnosHoy.length + ' turnos'" severity="info" rounded />
                    </div>

                    <div v-if="turnosHoy.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
                        <i class="pi pi-calendar-times text-4xl mb-2 opacity-50"></i>
                        <p>No hay turnos programados.</p>
                    </div>

                    <DataTable v-else :value="turnosHoy" paginator :rows="6" class="p-datatable-sm" responsiveLayout="scroll">
                        <Column field="fecha_inicio" header="Hora">
                            <template #body="slotProps">
                                <span class="font-bold text-gray-700 dark:text-gray-200">{{ horaAgenda(slotProps.data.fecha_inicio) }}</span>
                            </template>
                        </Column>
                        <Column header="Paciente">
                            <template #body="slotProps">
                                <span class="font-medium text-gray-700 dark:text-gray-200"> {{ slotProps.data.paciente }} {{ slotProps.data.apellido }} </span>
                            </template>
                        </Column>
                        <Column v-if="esAdmin" field="profesional" header="Profesional" />
                        <Column header="" bodyClass="text-right">
                            <template #body="slotProps">
                                <Button icon="pi pi-folder-open" rounded outlined size="small" severity="info" v-tooltip.top="'Ver historia'" :disabled="!slotProps.data.paciente_id" @click="verHistoria(slotProps.data)" />
                            </template>
                        </Column>
                    </DataTable>
                </div>
            </div>

            <div class="col-span-12 xl:col-span-5">
                <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 shadow-sm rounded-lg p-6 h-full">
                    <h2 class="text-xl font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
                        <i class="pi pi-clock text-blue-500"></i>
                        Proximo evento de agenda
                    </h2>

                    <div v-if="proximoEvento" class="p-5 bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700">
                        <div class="flex items-start gap-4">
                            <Avatar :label="inicialEvento(proximoEvento)" size="large" shape="circle" class="bg-blue-500 text-white" />
                            <div class="min-w-0 flex-1">
                                <div class="flex flex-wrap items-center gap-2 mb-1">
                                    <h3 class="text-lg font-bold text-gray-800 dark:text-white truncate">{{ proximoEvento.titulo }}</h3>
                                    <Tag :value="proximoEvento.tipo" :severity="tagSeverityEvento(proximoEvento.tipo)" rounded />
                                </div>
                                <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 font-medium">
                                    <i class="pi pi-calendar"></i>
                                    {{ fechaRangoBonito(proximoEvento.fecha_inicio, proximoEvento.fecha_fin) }}
                                </div>
                                <p v-if="proximoEvento.profesional && esAdmin" class="text-sm text-gray-500 dark:text-gray-400 mt-2">
                                    {{ proximoEvento.profesional }}
                                </p>
                            </div>
                        </div>

                        <p v-if="proximoEvento.detalle" class="mt-5 pt-4 border-t border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300">
                            {{ proximoEvento.detalle }}
                        </p>

                        <div v-if="proximoEvento.tipo === 'Turno'" class="mt-5 flex justify-end">
                            <Button label="Ver historia" icon="pi pi-folder-open" iconPos="right" rounded :disabled="!proximoEvento.paciente_id" @click="verHistoria(proximoEvento)" />
                        </div>
                    </div>

                    <div v-else class="flex flex-col items-center justify-center py-12 text-gray-400">
                        <i class="pi pi-check-circle text-4xl mb-2 opacity-50"></i>
                        <p>No hay proximos eventos.</p>
                    </div>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-5">
                <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 shadow-sm rounded-lg p-6 h-full">
                    <div class="flex items-center justify-between gap-3 mb-4">
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                            <i class="pi pi-briefcase text-blue-500"></i>
                            Disponibilidad de hoy
                        </h2>
                        <Button v-if="!esAdmin" label="Editar" link size="small" @click="$router.push('/disponibilidad')" />
                    </div>

                    <ul v-if="disponibilidadHoy.length > 0" class="space-y-3 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
                        <li v-for="d in disponibilidadHoy" :key="`${d.usuario_id}-${d.hora_inicio}-${d.hora_fin}`" class="flex items-center justify-between gap-3 p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                            <div class="min-w-0">
                                <p class="font-medium text-gray-700 dark:text-gray-200 truncate">{{ esAdmin ? d.profesional : d.dia_semana }}</p>
                                <p v-if="esAdmin" class="text-xs text-gray-500 dark:text-gray-400">{{ d.dia_semana }}</p>
                            </div>
                            <span class="text-sm text-gray-600 dark:text-gray-300 font-mono whitespace-nowrap">{{ d.hora_inicio }} - {{ d.hora_fin }}</span>
                        </li>
                    </ul>
                    <p v-else class="text-gray-500 dark:text-gray-400 text-sm text-center py-8">Sin disponibilidad activa para hoy.</p>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-7">
                <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 shadow-sm rounded-lg p-6 h-full">
                    <h2 class="text-xl font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
                        <i class="pi pi-megaphone text-blue-500"></i>
                        Comunicados
                    </h2>

                    <div v-if="comunicados.length === 0" class="text-gray-500 dark:text-gray-400 text-sm text-center py-8">No hay comunicados recientes.</div>

                    <div v-else class="space-y-3 max-h-[340px] overflow-y-auto pr-1 custom-scrollbar">
                        <article v-for="c in comunicados" :key="`${c.origen}-${c.id}`" class="p-4 rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800">
                            <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
                                <h3 class="font-bold text-gray-800 dark:text-white">{{ c.titulo }}</h3>
                                <Tag :value="c.origen === 'grupo' ? c.grupo_nombre : 'Institucional'" :severity="c.origen === 'grupo' ? 'success' : 'info'" rounded />
                            </div>
                            <p class="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">{{ c.contenido }}</p>
                            <p class="text-xs text-gray-400 mt-3">{{ c.autor_nombre }} - {{ fechaBonitaDashboard(c.creado_en) }}</p>
                        </article>
                    </div>
                </div>
            </div>

            <template v-if="esAdmin">
                <div class="col-span-12 lg:col-span-6">
                    <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 shadow-sm rounded-lg p-6 h-full">
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
                            <i class="pi pi-exclamation-triangle text-amber-500"></i>
                            Alertas de agenda
                        </h2>

                        <div class="space-y-5">
                            <section>
                                <div class="flex items-center justify-between gap-3 mb-2">
                                    <h3 class="font-semibold text-gray-700 dark:text-gray-200">Turnos superpuestos</h3>
                                    <Tag :value="(alertas.turnos_superpuestos || []).length" severity="warning" rounded />
                                </div>
                                <ul v-if="(alertas.turnos_superpuestos || []).length" class="space-y-2">
                                    <li v-for="a in alertas.turnos_superpuestos" :key="`${a.turno_id}-${a.turno_solapado_id}`" class="text-sm p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-100">
                                        <b>{{ a.profesional }}</b
                                        >: {{ horaAgenda(a.fecha_inicio) }} {{ a.paciente }} / {{ horaAgenda(a.fecha_inicio_solapada) }} {{ a.paciente_solapado }}
                                    </li>
                                </ul>
                                <p v-else class="text-sm text-gray-500 dark:text-gray-400">Sin solapamientos detectados.</p>
                            </section>

                            <section>
                                <div class="flex items-center justify-between gap-3 mb-2">
                                    <h3 class="font-semibold text-gray-700 dark:text-gray-200">Agendas vacias con disponibilidad hoy</h3>
                                    <Tag :value="(alertas.agenda_vacia || []).length" severity="danger" rounded />
                                </div>
                                <ul v-if="(alertas.agenda_vacia || []).length" class="space-y-2">
                                    <li v-for="a in alertas.agenda_vacia" :key="`${a.usuario_id}-${a.hora_inicio}`" class="text-sm p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-100">
                                        <b>{{ a.profesional }}</b
                                        >: {{ a.hora_inicio }} - {{ a.hora_fin }}
                                    </li>
                                </ul>
                                <p v-else class="text-sm text-gray-500 dark:text-gray-400">No hay agendas vacias para profesionales disponibles.</p>
                            </section>
                        </div>
                    </div>
                </div>

                <div class="col-span-12 lg:col-span-6">
                    <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 shadow-sm rounded-lg p-6 h-full">
                        <h2 class="text-xl font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
                            <i class="pi pi-lock text-blue-500"></i>
                            Ausencias y bloqueos de hoy
                        </h2>

                        <ul v-if="ausenciasBloqueos.length > 0" class="space-y-3 max-h-[340px] overflow-y-auto pr-1 custom-scrollbar">
                            <li v-for="a in ausenciasBloqueos" :key="a.id" class="p-3 rounded-lg bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700">
                                <div class="flex flex-wrap items-center justify-between gap-2">
                                    <p class="font-semibold text-gray-800 dark:text-white">{{ a.profesional }}</p>
                                    <Tag :value="a.tipo_evento" :severity="tagSeverityEvento(a.tipo_evento)" rounded />
                                </div>
                                <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">{{ fechaRangoBonito(a.fecha_inicio, a.fecha_fin) }}</p>
                                <p v-if="a.detalle" class="text-sm text-gray-500 dark:text-gray-400 mt-2">{{ a.detalle }}</p>
                            </li>
                        </ul>
                        <p v-else class="text-gray-500 dark:text-gray-400 text-sm text-center py-8">No hay ausencias ni bloqueos proximos.</p>
                    </div>
                </div>
            </template>
        </div>
    </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
    width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: #d1d5db;
    border-radius: 10px;
}
.dark .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: #4b5563;
}
</style>
