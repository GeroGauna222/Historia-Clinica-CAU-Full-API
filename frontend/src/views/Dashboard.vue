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
import Dialog from 'primevue/dialog';

const router = useRouter();
const user = useUserStore();

const loading = ref(true);
const error = ref(null);
const dashboard = ref(null);
const showTodayAlert = ref(false);

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

onMounted(async () => {
    await fetchDashboard();

    // Solo mostramos alerta a profesionales si tienen turnos programados hoy
    if (turnosHoy.value && turnosHoy.value.length > 0) {
        const hoyStr = new Date().toISOString().slice(0, 10);
        let ultimaAlertaVista = null;
        try {
            ultimaAlertaVista = localStorage.getItem('ultima_alerta_turnos_vista');
        } catch (error) {
            // Storage unavailable: show the alert again.
        }

        if (ultimaAlertaVista !== hoyStr) {
            showTodayAlert.value = true;
        }
    }
});

const cerrarAlertaHoy = () => {
    const hoyStr = new Date().toISOString().slice(0, 10);
    try {
        localStorage.setItem('ultima_alerta_turnos_vista', hoyStr);
    } catch (error) {
        // Storage unavailable: the alert will reappear on next visit.
    }
    showTodayAlert.value = false;
};
</script>

<template>
    <div class="p-6 md:p-8 w-full transition-colors">
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-color">
                <span v-if="user.nombre">{{ saludo }}, {{ user.nombre.split(' ')[0] }}</span>
                <span v-else>Inicio</span>
            </h1>
            <p class="text-muted-color text-base mt-1">Agenda y novedades relevantes para hoy.</p>
        </div>

        <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-muted-color">
            <i class="pi pi-spin pi-spinner text-4xl mb-3"></i>
            <p>Cargando informacion...</p>
        </div>

        <div v-else-if="error" class="bg-status-sin-aviso-bg border border-status-sin-aviso-border text-status-sin-aviso-fg p-4 rounded-lg flex items-center gap-3">
            <i class="pi pi-exclamation-triangle text-xl"></i>
            <span>{{ error }}</span>
        </div>

        <div v-else class="grid grid-cols-12 gap-6">
            <div v-for="item in resumenItems" :key="item.label" class="col-span-12 sm:col-span-6 xl:col-span-3">
                <div class="bg-card border border-surface shadow-sm rounded-lg p-5 h-full">
                    <div class="flex items-center justify-between gap-4">
                        <div>
                            <span class="block text-muted-color text-sm font-medium mb-2">{{ item.label }}</span>
                            <div class="text-3xl font-bold text-color">{{ item.value }}</div>
                        </div>
                        <div class="w-11 h-11 rounded-lg bg-subtle flex items-center justify-center">
                            <i :class="[item.icon, 'text-xl text-primary']"></i>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-12 xl:col-span-7">
                <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full">
                    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <h2 class="text-xl font-bold text-color flex items-center gap-2">
                            <i class="pi pi-calendar text-primary"></i>
                            Turnos de Hoy
                        </h2>
                        <Tag :value="turnosHoy.length + ' turnos'" severity="info" rounded />
                    </div>

                    <div v-if="turnosHoy.length === 0" class="flex flex-col items-center justify-center py-12 text-muted-color">
                        <i class="pi pi-calendar-times text-4xl mb-2 opacity-50"></i>
                        <p>No hay turnos programados.</p>
                    </div>

                    <DataTable v-else :value="turnosHoy" paginator :rows="6" class="p-datatable-sm" responsiveLayout="scroll">
                        <Column field="fecha_inicio" header="Hora">
                            <template #body="slotProps">
                                <span class="font-bold text-color">{{ horaAgenda(slotProps.data.fecha_inicio) }}</span>
                            </template>
                        </Column>
                        <Column header="Paciente">
                            <template #body="slotProps">
                                <span class="font-medium text-color"> {{ slotProps.data.paciente }} {{ slotProps.data.apellido }} </span>
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
                <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full">
                    <h2 class="text-xl font-bold text-color mb-4 flex items-center gap-2">
                        <i class="pi pi-clock text-primary"></i>
                        Proximo evento de agenda
                    </h2>

                    <div v-if="proximoEvento" class="p-5 bg-subtle rounded-lg border border-surface">
                        <div class="flex items-start gap-4">
                            <Avatar :label="inicialEvento(proximoEvento)" size="large" shape="circle" class="bg-blue-500 text-white" />
                            <div class="min-w-0 flex-1">
                                <div class="flex flex-wrap items-center gap-2 mb-1">
                                    <h3 class="text-lg font-bold text-color truncate">{{ proximoEvento.titulo }}</h3>
                                    <Tag :value="proximoEvento.tipo" :severity="tagSeverityEvento(proximoEvento.tipo)" rounded />
                                </div>
                                <div class="flex items-center gap-2 text-sm text-muted-color font-medium">
                                    <i class="pi pi-calendar"></i>
                                    {{ fechaRangoBonito(proximoEvento.fecha_inicio, proximoEvento.fecha_fin) }}
                                </div>
                                <p v-if="proximoEvento.profesional && esAdmin" class="text-sm text-muted-color mt-2">
                                    {{ proximoEvento.profesional }}
                                </p>
                            </div>
                        </div>

                        <p v-if="proximoEvento.detalle" class="mt-5 pt-4 border-t border-surface text-color">
                            {{ proximoEvento.detalle }}
                        </p>

                        <div v-if="proximoEvento.tipo === 'Turno'" class="mt-5 flex justify-end">
                            <Button label="Ver historia" icon="pi pi-folder-open" iconPos="right" rounded :disabled="!proximoEvento.paciente_id" @click="verHistoria(proximoEvento)" />
                        </div>
                    </div>

                    <div v-else class="flex flex-col items-center justify-center py-12 text-muted-color">
                        <i class="pi pi-check-circle text-4xl mb-2 opacity-50"></i>
                        <p>No hay proximos eventos.</p>
                    </div>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-5">
                <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full">
                    <div class="flex items-center justify-between gap-3 mb-4">
                        <h2 class="text-xl font-bold text-color flex items-center gap-2">
                            <i class="pi pi-briefcase text-primary"></i>
                            Disponibilidad de hoy
                        </h2>
                        <Button v-if="!esAdmin" label="Editar" link size="small" @click="$router.push('/disponibilidad')" />
                    </div>

                    <ul v-if="disponibilidadHoy.length > 0" class="space-y-3 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
                        <li v-for="d in disponibilidadHoy" :key="`${d.usuario_id}-${d.hora_inicio}-${d.hora_fin}`" class="flex items-center justify-between gap-3 p-3 bg-subtle rounded-lg">
                            <div class="min-w-0">
                                <p class="font-medium text-color truncate">{{ esAdmin ? d.profesional : d.dia_semana }}</p>
                                <p v-if="esAdmin" class="text-xs text-muted-color">{{ d.dia_semana }}</p>
                            </div>
                            <span class="text-sm text-muted-color font-mono whitespace-nowrap">{{ d.hora_inicio }} - {{ d.hora_fin }}</span>
                        </li>
                    </ul>
                    <p v-else class="text-muted-color text-sm text-center py-8">Sin disponibilidad activa para hoy.</p>
                </div>
            </div>

            <div class="col-span-12 lg:col-span-7">
                <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full">
                    <h2 class="text-xl font-bold text-color mb-4 flex items-center gap-2">
                        <i class="pi pi-megaphone text-primary"></i>
                        Comunicados
                    </h2>

                    <div v-if="comunicados.length === 0" class="text-muted-color text-sm text-center py-8">No hay comunicados recientes.</div>

                    <div v-else class="space-y-3 max-h-[340px] overflow-y-auto pr-1 custom-scrollbar">
                        <article v-for="c in comunicados" :key="`${c.origen}-${c.id}`" class="p-4 rounded-lg border border-surface bg-subtle">
                            <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
                                <h3 class="font-bold text-color">{{ c.titulo }}</h3>
                                <Tag :value="c.origen === 'grupo' ? c.grupo_nombre : 'Institucional'" :severity="c.origen === 'grupo' ? 'success' : 'info'" rounded />
                            </div>
                            <p class="text-sm text-muted-color line-clamp-2">{{ c.contenido }}</p>
                            <p class="text-xs text-muted-color mt-3">{{ c.autor_nombre }} - {{ fechaBonitaDashboard(c.creado_en) }}</p>
                        </article>
                    </div>
                </div>
            </div>

            <template v-if="esAdmin">
                <div class="col-span-12 lg:col-span-6">
                    <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full">
                        <h2 class="text-xl font-bold text-color mb-4 flex items-center gap-2">
                            <i class="pi pi-exclamation-triangle text-status-con-aviso-fg"></i>
                            Alertas de agenda
                        </h2>

                        <div class="space-y-5">
                            <section>
                                <div class="flex items-center justify-between gap-3 mb-2">
                                    <h3 class="font-semibold text-color">Turnos superpuestos</h3>
                                    <Tag :value="(alertas.turnos_superpuestos || []).length" severity="warning" rounded />
                                </div>
                                <ul v-if="(alertas.turnos_superpuestos || []).length" class="space-y-2">
                                    <li v-for="a in alertas.turnos_superpuestos" :key="`${a.turno_id}-${a.turno_solapado_id}`" class="text-sm p-3 rounded-lg bg-status-con-aviso-bg text-status-con-aviso-fg">
                                        <b>{{ a.profesional }}</b
                                        >: {{ horaAgenda(a.fecha_inicio) }} {{ a.paciente }} / {{ horaAgenda(a.fecha_inicio_solapada) }} {{ a.paciente_solapado }}
                                    </li>
                                </ul>
                                <p v-else class="text-sm text-muted-color">Sin solapamientos detectados.</p>
                            </section>

                            <section>
                                <div class="flex items-center justify-between gap-3 mb-2">
                                    <h3 class="font-semibold text-color">Agendas vacias con disponibilidad hoy</h3>
                                    <Tag :value="(alertas.agenda_vacia || []).length" severity="danger" rounded />
                                </div>
                                <ul v-if="(alertas.agenda_vacia || []).length" class="space-y-2">
                                    <li v-for="a in alertas.agenda_vacia" :key="`${a.usuario_id}-${a.hora_inicio}`" class="text-sm p-3 rounded-lg bg-status-sin-aviso-bg text-status-sin-aviso-fg">
                                        <b>{{ a.profesional }}</b
                                        >: {{ a.hora_inicio }} - {{ a.hora_fin }}
                                    </li>
                                </ul>
                                <p v-else class="text-sm text-muted-color">No hay agendas vacias para profesionales disponibles.</p>
                            </section>
                        </div>
                    </div>
                </div>

                <div class="col-span-12 lg:col-span-6">
                    <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full">
                        <h2 class="text-xl font-bold text-color mb-4 flex items-center gap-2">
                            <i class="pi pi-lock text-primary"></i>
                            Ausencias y bloqueos de hoy
                        </h2>

                        <ul v-if="ausenciasBloqueos.length > 0" class="space-y-3 max-h-[340px] overflow-y-auto pr-1 custom-scrollbar">
                            <li v-for="a in ausenciasBloqueos" :key="a.id" class="p-3 rounded-lg bg-subtle border border-surface">
                                <div class="flex flex-wrap items-center justify-between gap-2">
                                    <p class="font-semibold text-color">{{ a.profesional }}</p>
                                    <Tag :value="a.tipo_evento" :severity="tagSeverityEvento(a.tipo_evento)" rounded />
                                </div>
                                <p class="text-sm text-muted-color mt-1">{{ fechaRangoBonito(a.fecha_inicio, a.fecha_fin) }}</p>
                                <p v-if="a.detalle" class="text-sm text-muted-color mt-2">{{ a.detalle }}</p>
                            </li>
                        </ul>
                        <p v-else class="text-muted-color text-sm text-center py-8">No hay ausencias ni bloqueos proximos.</p>
                    </div>
                </div>
            </template>
        </div>
    </div>

    <!-- Alerta de Turnos de Hoy -->
    <Dialog v-model:visible="showTodayAlert" header="📅 Tus turnos de hoy" :modal="true" :closable="true" :breakpoints="{ '960px': '75vw', '640px': '90vw' }" :style="{ width: '500px' }" @hide="cerrarAlertaHoy">
        <div class="py-2">
            <p class="text-muted-color text-sm mb-4">
                Hola <b>{{ user.nombre?.split(' ')[0] }}</b
                >, tenés <b>{{ turnosHoy.length }}</b> turno(s) programado(s) para hoy:
            </p>
            <div class="max-h-[300px] overflow-y-auto pr-1 custom-scrollbar space-y-3">
                <div v-for="t in turnosHoy" :key="t.id" class="p-3 bg-subtle border border-surface rounded-lg flex items-center justify-between gap-4">
                    <div class="min-w-0">
                        <p class="font-bold text-color text-sm">{{ horaAgenda(t.fecha_inicio) }} - {{ t.paciente }} {{ t.apellido || '' }}</p>
                        <p class="text-xs text-muted-color truncate mt-1">Motivo: {{ t.motivo || 'Control' }}</p>
                    </div>
                    <Button
                        icon="pi pi-folder-open"
                        rounded
                        outlined
                        size="small"
                        severity="info"
                        v-tooltip.top="'Ver historia'"
                        :disabled="!t.paciente_id"
                        @click="
                            () => {
                                showTodayAlert = false;
                                verHistoria(t);
                            }
                        "
                    />
                </div>
            </div>
        </div>
        <template #footer>
            <div class="flex justify-end pt-2">
                <Button label="Entendido" icon="pi pi-check" rounded @click="cerrarAlertaHoy" class="p-button-sm font-semibold" />
            </div>
        </template>
    </Dialog>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
    width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: var(--p-content-border-color);
    border-radius: 10px;
}
</style>
