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
import Dialog from 'primevue/dialog';
import { useToast } from 'primevue/usetoast';

import ProximoTurnoWidget from '@/components/dashboard/ProximoTurnoWidget.vue';

const router = useRouter();
const user = useUserStore();
const toast = useToast();

const loading = ref(true);
const error = ref(null);
const dashboard = ref(null);
const showTodayAlert = ref(false);

const esAdmin = computed(() => ['director', 'administrativo'].includes(user.rol?.toLowerCase().trim()));
const esDirector = computed(() => user.isDirector || user.rol?.toLowerCase().trim() === 'director');

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

    // Los superpuestos deben figurar en profesionales, no en directivos
    if (esDirector.value) return base;

    return [...base, { label: 'Superpuestos', value: resumen.turnos_superpuestos || 0, icon: 'pi pi-exclamation-triangle', severity: 'warning' }];
});

const proximoEvento = computed(() => dashboard.value?.proximo_evento || null);
const turnosHoy = computed(() => dashboard.value?.turnos || []);
const atencionesEnCurso = computed(() => {
    if (dashboard.value?.atenciones_en_curso && dashboard.value.atenciones_en_curso.length > 0) {
        return dashboard.value.atenciones_en_curso;
    }
    return turnosHoy.value.filter((t) => t.estado_asistencia === 'presente');
});
const turnoEnCurso = computed(() => dashboard.value?.turno_en_curso || atencionesEnCurso.value.slice(-1)[0] || null);
const disponibilidadHoy = computed(() => dashboard.value?.disponibilidad_hoy || []);
const comunicados = computed(() => dashboard.value?.comunicados || []);
const alertas = computed(() => dashboard.value?.alertas || {});
const ausenciasBloqueos = computed(() => dashboard.value?.ausencias_bloqueos || []);

const fetchDashboard = async (silencioso = false) => {
    try {
        if (!silencioso) loading.value = true;
        error.value = null;
        const res = await api.get('/dashboard', { withCredentials: true });
        dashboard.value = res.data;
    } catch (err) {
        console.error('Error dashboard:', err);
        error.value = 'No se pudo cargar el inicio.';
    } finally {
        if (!silencioso) loading.value = false;
    }
};

const verHistoria = (turno) => {
    if (!turno?.paciente_id) return;
    router.push({ name: 'historiaPaciente', params: { id: turno.paciente_id } });
};

const tagSeverityEvento = (tipo) => {
    const limpio = (tipo || '').toLowerCase();
    if (limpio === 'turno') return 'info';
    if (limpio === 'reunion') return 'success';
    if (limpio === 'ausencia') return 'danger';
    return 'warning';
};

const tagTextoAsistencia = (estado) => {
    const s = (estado || 'programado').toLowerCase();
    if (s === 'presente') return 'Presente';
    if (s === 'con_aviso') return 'Con aviso';
    if (s === 'sin_aviso') return 'Sin aviso';
    return 'Programado';
};

const tagSeverityAsistencia = (estado) => {
    const s = (estado || 'programado').toLowerCase();
    if (s === 'presente') return 'success';
    if (s === 'con_aviso') return 'warn';
    if (s === 'sin_aviso') return 'danger';
    return 'info';
};

const filaTurnoClass = (data) => {
    if (data?.id) {
        if (esDirector.value) {
            if (atencionesEnCurso.value.some((t) => t.id === data.id)) {
                return '!bg-status-presente-bg/30 !border-l-4 !border-status-presente-fg font-semibold';
            }
        } else if (data.id === turnoEnCurso.value?.id) {
            return '!bg-status-presente-bg/30 !border-l-4 !border-status-presente-fg font-semibold';
        }
    }
    return '';
};

const actualizarAsistencia = async ({ turnoId, estado }) => {
    try {
        await api.patch(`/turnos/${turnoId}/asistencia`, { estado_asistencia: estado }, { withCredentials: true });

        const target = turnosHoy.value.find((item) => item.id === turnoId);
        if (target) {
            target.estado_asistencia = estado;
            target.ausencia = ['con_aviso', 'sin_aviso'].includes(estado) ? estado : null;
        }

        const texto = estado === 'presente' ? 'Presente' : estado === 'con_aviso' ? 'Con aviso' : estado === 'sin_aviso' ? 'Sin aviso' : 'Programado';

        toast.add({
            severity: 'success',
            summary: 'Asistencia actualizada',
            detail: `Turno marcado como ${texto}`,
            life: 3000
        });

        await fetchDashboard(true);
    } catch (err) {
        console.error('Error al actualizar asistencia:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No se pudo actualizar el estado de asistencia.',
            life: 3500
        });
    }
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

        <div v-else class="space-y-6">
            <!-- KPI Summary Cards Row -->
            <div class="grid grid-cols-12 gap-6">
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
            </div>

            <!-- Alerta de Turnos Superpuestos para el Profesional -->
            <div v-if="!esDirector && (alertas.turnos_superpuestos || []).length > 0" class="p-4 rounded-lg bg-status-con-aviso-bg border border-status-con-aviso-border text-status-con-aviso-fg flex items-start gap-3 shadow-sm">
                <i class="pi pi-exclamation-triangle text-xl shrink-0 mt-0.5"></i>
                <div class="flex-1 text-sm">
                    <p class="font-bold">Turnos superpuestos detectados en tu agenda de hoy ({{ alertas.turnos_superpuestos.length }})</p>
                    <ul class="mt-1 list-disc list-inside text-xs space-y-0.5 opacity-90">
                        <li v-for="a in alertas.turnos_superpuestos" :key="`${a.turno_id}-${a.turno_solapado_id}`">{{ horaAgenda(a.fecha_inicio) }} {{ a.paciente }} solapado con {{ horaAgenda(a.fecha_inicio_solapada) }} {{ a.paciente_solapado }}</li>
                    </ul>
                </div>
            </div>

            <!-- Main Content Grid -->
            <div class="grid grid-cols-12 gap-6">
                <div class="col-span-12 xl:col-span-5">
                    <ProximoTurnoWidget
                        :turno-en-curso="turnoEnCurso"
                        :atenciones-en-curso="atencionesEnCurso"
                        :proximo-evento="proximoEvento"
                        :es-admin="esAdmin"
                        :es-director="esDirector"
                        @ver-historia="verHistoria"
                        @cambiar-asistencia="actualizarAsistencia"
                        @ver-agenda="$router.push('/turnos')"
                    />
                </div>

                <div class="col-span-12 xl:col-span-7">
                    <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full">
                        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                            <h2 class="text-xl font-bold text-color flex items-center gap-2">
                                <i class="pi pi-calendar text-primary"></i>
                                Turnos de Hoy
                            </h2>
                            <div class="flex items-center gap-2">
                                <Tag :value="turnosHoy.length + ' turnos'" severity="info" rounded />
                                <Tag v-if="atencionesEnCurso.length > 0" :value="atencionesEnCurso.length + (atencionesEnCurso.length === 1 ? ' en atención' : ' en atención')" severity="success" rounded class="font-semibold" />
                            </div>
                        </div>

                        <div v-if="turnosHoy.length === 0" class="flex flex-col items-center justify-center py-12 text-muted-color">
                            <i class="pi pi-calendar-times text-4xl mb-2 opacity-50"></i>
                            <p>No hay turnos programados.</p>
                        </div>

                        <DataTable v-else :value="turnosHoy" paginator :rows="6" :rowClass="filaTurnoClass" class="p-datatable-sm" responsiveLayout="scroll">
                            <Column field="fecha_inicio" header="Hora" style="width: 16%">
                                <template #body="slotProps">
                                    <div class="flex flex-col">
                                        <span class="font-bold text-color">{{ horaAgenda(slotProps.data.fecha_inicio) }}</span>
                                        <span class="text-xs text-muted-color">{{ horaAgenda(slotProps.data.fecha_fin) }}</span>
                                    </div>
                                </template>
                            </Column>
                            <Column header="Paciente" style="min-width: 13rem">
                                <template #body="slotProps">
                                    <div class="flex flex-col min-w-0">
                                        <div class="flex items-center gap-2">
                                            <span class="font-bold text-color truncate"> {{ slotProps.data.paciente }} {{ slotProps.data.apellido }} </span>
                                            <Tag v-if="slotProps.data.es_sobreturno" value="Sobreturno" severity="warn" class="!text-[10px] !py-0 !px-1.5 font-bold" rounded />
                                        </div>
                                        <div class="flex flex-wrap items-center gap-1.5 text-xs text-muted-color mt-0.5">
                                            <span v-if="slotProps.data.nro_hc" class="font-semibold text-color">HC: {{ slotProps.data.nro_hc }}</span>
                                            <span v-if="slotProps.data.dni">· DNI: {{ slotProps.data.dni }}</span>
                                            <span v-if="slotProps.data.cobertura">· {{ slotProps.data.cobertura }}</span>
                                            <span v-if="slotProps.data.nro_afiliado || slotProps.data.nro_certificado">· Afil: {{ slotProps.data.nro_afiliado || slotProps.data.nro_certificado }}</span>
                                        </div>
                                    </div>
                                </template>
                            </Column>
                            <Column v-if="esAdmin" field="profesional" header="Profesional" />
                            <Column header="Estado" style="width: 20%">
                                <template #body="slotProps">
                                    <Tag :value="tagTextoAsistencia(slotProps.data.estado_asistencia)" :severity="tagSeverityAsistencia(slotProps.data.estado_asistencia)" rounded class="text-xs font-semibold" />
                                </template>
                            </Column>
                            <Column header="" bodyClass="text-right" style="width: 20%">
                                <template #body="slotProps">
                                    <div class="flex items-center justify-end gap-1.5">
                                        <Button
                                            v-if="!esAdmin && slotProps.data.estado_asistencia === 'programado'"
                                            icon="pi pi-check"
                                            rounded
                                            size="small"
                                            severity="success"
                                            v-tooltip.top="'Marcar presente'"
                                            @click="actualizarAsistencia({ turnoId: slotProps.data.id, estado: 'presente' })"
                                        />
                                        <Button icon="pi pi-folder-open" rounded outlined size="small" severity="info" v-tooltip.top="'Ver historia clínica'" :disabled="!slotProps.data.paciente_id" @click="verHistoria(slotProps.data)" />
                                    </div>
                                </template>
                            </Column>
                        </DataTable>
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
                                <section v-if="!esDirector">
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
