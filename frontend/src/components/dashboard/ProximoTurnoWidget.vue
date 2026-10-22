<script setup>
import { computed } from 'vue';
import Avatar from 'primevue/avatar';
import Tag from 'primevue/tag';
import Button from 'primevue/button';
import { fechaRangoBonito } from '@/utils/formatDate';

const props = defineProps({
    turnoEnCurso: {
        type: Object,
        default: null
    },
    atencionesEnCurso: {
        type: Array,
        default: () => []
    },
    proximoEvento: {
        type: Object,
        default: null
    },
    esAdmin: {
        type: Boolean,
        default: false
    },
    esDirector: {
        type: Boolean,
        default: false
    }
});

const emit = defineEmits(['verHistoria', 'cambiarAsistencia', 'verAgenda']);

const horaAgenda = (fecha) => {
    if (!fecha) return '-';
    const d = new Date(fecha);
    if (Number.isNaN(d.getTime())) return '-';
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

const tiempoRelativo = (fecha) => {
    if (!fecha) return '';
    const target = new Date(fecha);
    if (Number.isNaN(target.getTime())) return '';
    const ahora = new Date();
    const diffMs = target.getTime() - ahora.getTime();
    const diffMin = Math.round(diffMs / 60000);

    if (diffMin <= 0 && diffMin >= -30) return 'Ahora';
    if (diffMin > 0 && diffMin <= 60) return `en ${diffMin} min`;
    if (diffMin > 60 && diffMin <= 240) {
        const h = Math.floor(diffMin / 60);
        const m = diffMin % 60;
        return m > 0 ? `en ${h}h ${m}m` : `en ${h}h`;
    }
    return '';
};

const inicialNombre = (nombre, apellido) => {
    const texto = (nombre || apellido || '?').trim();
    return texto.charAt(0).toUpperCase();
};

const inicialEvento = (evento) => {
    const texto = evento?.titulo || evento?.paciente || evento?.tipo || '?';
    return texto.charAt(0).toUpperCase();
};

const calcularEdad = (fechaNacimiento) => {
    if (!fechaNacimiento) return null;
    const nac = new Date(fechaNacimiento);
    if (Number.isNaN(nac.getTime())) return null;
    const hoy = new Date();
    let edad = hoy.getFullYear() - nac.getFullYear();
    const m = hoy.getMonth() - nac.getMonth();
    if (m < 0 || (m === 0 && hoy.getDate() < nac.getDate())) {
        edad--;
    }
    return edad >= 0 ? `${edad} años` : null;
};

const tagSeverityEvento = (tipo) => {
    const limpio = (tipo || '').toLowerCase();
    if (limpio === 'turno') return 'info';
    if (limpio === 'reunion') return 'success';
    if (limpio === 'ausencia') return 'danger';
    return 'warn';
};

const atencionesActivas = computed(() => {
    if (props.atencionesEnCurso && props.atencionesEnCurso.length > 0) {
        return props.atencionesEnCurso;
    }
    return props.turnoEnCurso ? [props.turnoEnCurso] : [];
});

const tituloWidget = computed(() => {
    if (props.esDirector) return 'Atenciones en Curso';
    if (props.turnoEnCurso) return 'Atención en Curso';
    if (props.proximoEvento?.tipo === 'Turno') return 'Próximo Turno en Agenda';
    if (props.proximoEvento) return 'Próximo Evento de Agenda';
    return 'Agenda de Hoy';
});

const iconoWidget = computed(() => {
    if (props.esDirector) return 'pi pi-users';
    if (props.turnoEnCurso) return 'pi pi-user-check';
    if (props.proximoEvento?.tipo === 'Turno') return 'pi pi-clock';
    if (props.proximoEvento) return 'pi pi-calendar';
    return 'pi pi-calendar-check';
});
</script>

<template>
    <div class="bg-card border border-surface shadow-sm rounded-lg p-6 h-full flex flex-col justify-between transition-colors">
        <!-- Encabezado del widget -->
        <div>
            <div class="flex items-center justify-between gap-3 mb-4">
                <h2 class="text-xl font-bold text-color flex items-center gap-2">
                    <i :class="[iconoWidget, 'text-primary text-xl']"></i>
                    <span>{{ tituloWidget }}</span>
                </h2>
                <div class="flex items-center gap-2">
                    <Tag v-if="esDirector && atencionesActivas.length > 0" :value="atencionesActivas.length + (atencionesActivas.length === 1 ? ' en atención' : ' en atención')" severity="success" rounded class="animate-pulse font-semibold" />
                    <Tag v-else-if="esDirector" value="Sin atenciones activas" severity="secondary" rounded class="text-xs" />
                    <Tag v-else-if="turnoEnCurso" value="Presente" severity="success" rounded class="animate-pulse font-semibold" />
                    <Button label="Ver agenda" icon="pi pi-arrow-right" iconPos="right" text size="small" @click="emit('verAgenda')" />
                </div>
            </div>

            <!-- CASO DIRECTOR: Supervisión de Atenciones en Curso en toda la clínica -->
            <div v-if="esDirector">
                <!-- D1: Si hay 1 o más atenciones activas simultáneas -->
                <div v-if="atencionesActivas.length > 0" class="space-y-4 max-h-[520px] overflow-y-auto pr-1">
                    <div v-for="atencion in atencionesActivas" :key="atencion.id" class="p-4 rounded-xl border border-status-presente-border bg-status-presente-bg/20 transition-all shadow-sm">
                        <!-- Barra superior con indicador en vivo, profesional y horario -->
                        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="inline-flex items-center gap-1.5 text-xs font-bold tracking-wider uppercase text-status-presente-fg">
                                    <span class="w-2 h-2 rounded-full bg-status-presente-fg animate-ping"></span>
                                    En atención
                                </span>
                                <Tag v-if="atencion.es_sobreturno" value="Sobreturno" severity="warn" rounded class="text-[10px] font-bold" />
                                <span v-if="atencion.profesional" class="text-xs font-semibold px-2 py-0.5 rounded-full bg-card text-color border border-surface flex items-center gap-1">
                                    <i class="pi pi-user-md text-primary text-xs"></i>
                                    {{ atencion.profesional }}
                                </span>
                            </div>
                            <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-card text-color border border-surface flex items-center gap-1 shadow-sm">
                                <i class="pi pi-clock text-status-presente-fg"></i>
                                {{ horaAgenda(atencion.fecha_inicio) }} - {{ horaAgenda(atencion.fecha_fin) }}
                            </span>
                        </div>

                        <!-- Datos del paciente -->
                        <div class="flex items-start gap-3 mb-3">
                            <Avatar :label="inicialNombre(atencion.paciente, atencion.apellido)" size="large" shape="circle" class="bg-status-presente-fg text-white font-bold shrink-0 shadow-sm" />
                            <div class="min-w-0 flex-1">
                                <h3 class="text-base font-bold text-color leading-tight truncate">{{ atencion.paciente }} {{ atencion.apellido }}</h3>
                                <div class="flex flex-wrap items-center gap-1.5 mt-1 text-xs">
                                    <span v-if="atencion.nro_hc" class="font-semibold px-1.5 py-0.5 rounded bg-card text-color border border-surface"> HC: {{ atencion.nro_hc }} </span>
                                    <span v-if="atencion.dni" class="text-muted-color"> DNI: {{ atencion.dni }} </span>
                                    <span v-if="calcularEdad(atencion.fecha_nacimiento)" class="text-muted-color"> · {{ calcularEdad(atencion.fecha_nacimiento) }} </span>
                                    <span v-if="atencion.cobertura" class="text-muted-color"> · {{ atencion.cobertura }} </span>
                                    <span v-if="atencion.nro_afiliado || atencion.nro_certificado" class="font-semibold px-1.5 py-0.5 rounded bg-card text-color border border-surface">
                                        Afiliado: {{ atencion.nro_afiliado || atencion.nro_certificado }}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Motivo y notas -->
                        <div class="mb-3 p-2.5 rounded-lg bg-card border border-surface text-xs space-y-1">
                            <div class="flex items-start gap-1.5">
                                <i class="pi pi-info-circle text-primary text-xs mt-0.5"></i>
                                <div class="min-w-0 flex-1">
                                    <span class="text-[10px] font-semibold text-muted-color uppercase block">Motivo:</span>
                                    <p class="font-medium text-color truncate">{{ atencion.motivo || 'Consulta médica' }}</p>
                                </div>
                            </div>
                            <div v-if="atencion.observaciones" class="pt-1.5 border-t border-surface text-muted-color flex items-start gap-1">
                                <i class="pi pi-pencil text-[10px] mt-0.5"></i>
                                <span class="truncate"><b>Notas:</b> {{ atencion.observaciones }}</span>
                            </div>
                        </div>

                        <!-- Acción rápida -->
                        <div class="flex items-center justify-between gap-2 pt-2 border-t border-surface">
                            <Button label="Abrir Historia Clínica" icon="pi pi-folder-open" size="small" rounded class="font-semibold text-xs" :disabled="!atencion.paciente_id" @click="emit('verHistoria', atencion)" />
                        </div>
                    </div>
                </div>

                <!-- D2: Sin pacientes presentes en la clínica -->
                <div v-else class="p-5 bg-subtle rounded-xl border border-surface space-y-4">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-full bg-card border border-surface flex items-center justify-center shrink-0">
                            <i class="pi pi-users text-lg text-primary"></i>
                        </div>
                        <div>
                            <h4 class="text-sm font-bold text-color">Sin atenciones simultáneas en curso</h4>
                            <p class="text-xs text-muted-color">Actualmente no se registran pacientes en consulta activa en la clínica.</p>
                        </div>
                    </div>

                    <div v-if="proximoEvento" class="p-3.5 rounded-lg bg-card border border-surface">
                        <div class="flex items-center justify-between gap-2 mb-2">
                            <span class="text-xs font-semibold text-muted-color uppercase tracking-wider">Próximo turno en institución</span>
                            <span class="text-xs font-mono font-bold text-primary">{{ horaAgenda(proximoEvento.fecha_inicio) }}</span>
                        </div>
                        <div class="flex items-center justify-between gap-2">
                            <div class="min-w-0">
                                <p class="text-sm font-bold text-color truncate">{{ proximoEvento.paciente ? `${proximoEvento.paciente} ${proximoEvento.apellido}` : proximoEvento.titulo }}</p>
                                <p v-if="proximoEvento.profesional" class="text-xs text-muted-color mt-0.5">
                                    Profesional: <span class="font-medium text-color">{{ proximoEvento.profesional }}</span>
                                </p>
                            </div>
                            <Tag v-if="tiempoRelativo(proximoEvento.fecha_inicio)" :value="tiempoRelativo(proximoEvento.fecha_inicio)" severity="info" rounded class="text-xs font-bold" />
                        </div>
                    </div>
                </div>
            </div>

            <!-- VISTA PROFESIONAL Y OTROS ROLES (individual) -->
            <div v-else>
                <!-- CASO 1: Paciente actualmente en curso (último marcado como presente) -->
                <div v-if="turnoEnCurso" class="p-5 rounded-xl border border-status-presente-border bg-status-presente-bg/20 transition-all">
                    <!-- Barra superior con indicador en vivo y horario -->
                    <div class="flex flex-wrap items-center justify-between gap-2 mb-4">
                        <div class="flex items-center gap-2">
                            <span class="inline-flex items-center gap-2 text-xs font-bold tracking-wider uppercase text-status-presente-fg">
                                <span class="w-2.5 h-2.5 rounded-full bg-status-presente-fg animate-ping"></span>
                                En atención ahora
                            </span>
                            <Tag v-if="turnoEnCurso.es_sobreturno" value="Sobreturno" severity="warn" rounded class="text-[11px] font-bold" />
                        </div>
                        <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-card text-color border border-surface flex items-center gap-1.5 shadow-sm">
                            <i class="pi pi-clock text-status-presente-fg"></i>
                            {{ horaAgenda(turnoEnCurso.fecha_inicio) }} - {{ horaAgenda(turnoEnCurso.fecha_fin) }}
                        </span>
                    </div>

                    <!-- Datos principales del paciente -->
                    <div class="flex items-start gap-3.5 mb-4">
                        <Avatar :label="inicialNombre(turnoEnCurso.paciente, turnoEnCurso.apellido)" size="xlarge" shape="circle" class="bg-status-presente-fg text-white font-bold shrink-0 shadow-sm" />
                        <div class="min-w-0 flex-1">
                            <h3 class="text-xl font-bold text-color leading-tight truncate">{{ turnoEnCurso.paciente }} {{ turnoEnCurso.apellido }}</h3>
                            <div class="flex flex-wrap items-center gap-2 mt-1.5">
                                <span v-if="turnoEnCurso.nro_hc" class="text-xs font-semibold px-2 py-0.5 rounded bg-card text-color border border-surface"> HC: {{ turnoEnCurso.nro_hc }} </span>
                                <span v-if="turnoEnCurso.dni" class="text-xs text-muted-color font-medium"> DNI: {{ turnoEnCurso.dni }} </span>
                                <span v-if="calcularEdad(turnoEnCurso.fecha_nacimiento)" class="text-xs text-muted-color"> · {{ calcularEdad(turnoEnCurso.fecha_nacimiento) }} </span>
                                <span v-if="turnoEnCurso.cobertura" class="text-xs text-muted-color"> · {{ turnoEnCurso.cobertura }} </span>
                                <span v-if="turnoEnCurso.nro_afiliado || turnoEnCurso.nro_certificado" class="text-xs font-semibold px-2 py-0.5 rounded bg-card text-color border border-surface">
                                    Afiliado: {{ turnoEnCurso.nro_afiliado || turnoEnCurso.nro_certificado }}
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- Motivo y observaciones clínicas -->
                    <div class="mb-4 p-3 rounded-lg bg-card border border-surface text-sm space-y-1">
                        <div class="flex items-start gap-2">
                            <i class="pi pi-info-circle text-primary text-xs mt-0.5"></i>
                            <div class="min-w-0 flex-1">
                                <span class="text-xs font-semibold text-muted-color uppercase block">Motivo:</span>
                                <p class="font-medium text-color">{{ turnoEnCurso.motivo || 'Consulta general' }}</p>
                            </div>
                        </div>
                        <div v-if="turnoEnCurso.observaciones" class="pt-2 border-t border-surface text-xs text-muted-color flex items-start gap-1.5">
                            <i class="pi pi-pencil text-xs mt-0.5"></i>
                            <span><b>Notas:</b> {{ turnoEnCurso.observaciones }}</span>
                        </div>
                    </div>

                    <!-- Acciones rápidas para el turno en atención -->
                    <div class="flex items-center justify-between gap-2 pt-3 border-t border-surface">
                        <Button label="Abrir Historia Clínica" icon="pi pi-folder-open" rounded class="font-semibold" :disabled="!turnoEnCurso.paciente_id" @click="emit('verHistoria', turnoEnCurso)" />
                    </div>

                    <!-- Vista previa del próximo turno programado (si existe a continuación) -->
                    <div v-if="proximoEvento && proximoEvento.id !== turnoEnCurso.id" class="mt-4 pt-3 border-t border-surface flex items-center justify-between text-xs text-muted-color">
                        <div class="flex items-center gap-2 truncate">
                            <span class="font-semibold text-color">A continuación:</span>
                            <span class="font-mono text-primary font-bold">{{ horaAgenda(proximoEvento.fecha_inicio) }}</span>
                            <span class="truncate font-medium text-color">{{ proximoEvento.titulo }}</span>
                            <Tag v-if="proximoEvento.es_sobreturno" value="ST" severity="warn" rounded class="text-[9px] !py-0 !px-1 font-bold" />
                        </div>
                        <span v-if="tiempoRelativo(proximoEvento.fecha_inicio)" class="text-xs whitespace-nowrap opacity-80">
                            {{ tiempoRelativo(proximoEvento.fecha_inicio) }}
                        </span>
                    </div>
                </div>

                <!-- CASO 2: Sin paciente presente, pero hay próximo evento en agenda -->
                <div v-else-if="proximoEvento" class="p-5 bg-subtle rounded-xl border border-surface">
                    <!-- Si el evento es un Turno médico -->
                    <template v-if="proximoEvento.tipo === 'Turno'">
                        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
                            <div class="flex items-center gap-2">
                                <Tag value="Próximo Turno" severity="info" rounded class="font-semibold" />
                                <Tag v-if="proximoEvento.es_sobreturno" value="Sobreturno" severity="warn" rounded class="text-[11px] font-bold" />
                            </div>
                            <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-card text-color border border-surface flex items-center gap-1.5 shadow-sm">
                                <i class="pi pi-clock text-primary"></i>
                                {{ horaAgenda(proximoEvento.fecha_inicio) }} - {{ horaAgenda(proximoEvento.fecha_fin) }}
                                <span v-if="tiempoRelativo(proximoEvento.fecha_inicio)" class="text-primary font-bold"> · {{ tiempoRelativo(proximoEvento.fecha_inicio) }} </span>
                            </span>
                        </div>

                        <div class="flex items-start gap-3.5 mb-4">
                            <Avatar :label="inicialNombre(proximoEvento.paciente, proximoEvento.apellido)" size="xlarge" shape="circle" class="bg-primary text-white font-bold shrink-0" />
                            <div class="min-w-0 flex-1">
                                <h3 class="text-lg font-bold text-color leading-tight truncate">{{ proximoEvento.paciente }} {{ proximoEvento.apellido }}</h3>
                                <div class="flex flex-wrap items-center gap-2 mt-1.5">
                                    <span v-if="proximoEvento.nro_hc" class="text-xs font-semibold px-2 py-0.5 rounded bg-card text-color border border-surface"> HC: {{ proximoEvento.nro_hc }} </span>
                                    <span v-if="proximoEvento.dni" class="text-xs text-muted-color"> DNI: {{ proximoEvento.dni }} </span>
                                    <span v-if="calcularEdad(proximoEvento.fecha_nacimiento)" class="text-xs text-muted-color"> · {{ calcularEdad(proximoEvento.fecha_nacimiento) }} </span>
                                    <span v-if="proximoEvento.cobertura" class="text-xs text-muted-color"> · {{ proximoEvento.cobertura }} </span>
                                    <span v-if="proximoEvento.nro_afiliado || proximoEvento.nro_certificado" class="text-xs font-semibold px-2 py-0.5 rounded bg-card text-color border border-surface">
                                        Afiliado: {{ proximoEvento.nro_afiliado || proximoEvento.nro_certificado }}
                                    </span>
                                </div>
                                <p v-if="proximoEvento.profesional && esAdmin" class="text-xs text-muted-color mt-1">
                                    Profesional: <b>{{ proximoEvento.profesional }}</b>
                                </p>
                            </div>
                        </div>

                        <div class="mb-4 p-3 rounded-lg bg-card border border-surface text-sm space-y-1">
                            <span class="text-xs font-semibold text-muted-color uppercase block">Motivo de consulta:</span>
                            <p class="font-medium text-color">{{ proximoEvento.motivo || proximoEvento.detalle || 'Control' }}</p>
                            <p v-if="proximoEvento.observaciones" class="text-xs text-muted-color mt-1 italic">Nota: {{ proximoEvento.observaciones }}</p>
                        </div>

                        <!-- Acciones rápidas para el próximo turno -->
                        <div class="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-surface">
                            <div class="flex items-center gap-2">
                                <Button v-if="!esAdmin" label="Marcar Presente" icon="pi pi-check" severity="success" rounded class="font-semibold" @click="emit('cambiarAsistencia', { turnoId: proximoEvento.id, estado: 'presente' })" />
                                <Button label="Ver Historia" icon="pi pi-folder-open" severity="info" outlined rounded :disabled="!proximoEvento.paciente_id" @click="emit('verHistoria', proximoEvento)" />
                            </div>
                            <div v-if="!esAdmin" class="flex items-center gap-1">
                                <Button label="Con aviso" size="small" severity="warn" text rounded v-tooltip.top="'Paciente avisó que no viene'" @click="emit('cambiarAsistencia', { turnoId: proximoEvento.id, estado: 'con_aviso' })" />
                                <Button label="Sin aviso" size="small" severity="danger" text rounded v-tooltip.top="'Paciente ausente sin aviso'" @click="emit('cambiarAsistencia', { turnoId: proximoEvento.id, estado: 'sin_aviso' })" />
                            </div>
                        </div>
                    </template>

                    <!-- Si el evento es una Reunión, Ausencia o Bloqueo -->
                    <template v-else>
                        <div class="flex items-start gap-4">
                            <Avatar :label="inicialEvento(proximoEvento)" size="large" shape="circle" class="bg-primary text-white" />
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
                        <p v-if="proximoEvento.detalle" class="mt-4 pt-3 border-t border-surface text-sm text-color">
                            {{ proximoEvento.detalle }}
                        </p>
                    </template>
                </div>

                <!-- CASO 3: Sin turnos en curso ni próximos eventos -->
                <div v-else class="flex flex-col items-center justify-center py-12 text-center text-muted-color">
                    <div class="w-14 h-14 rounded-full bg-subtle flex items-center justify-center mb-3">
                        <i class="pi pi-calendar-check text-2xl text-status-presente-fg"></i>
                    </div>
                    <h3 class="text-base font-bold text-color mb-1">Sin turnos pendientes hoy</h3>
                    <p class="text-sm max-w-xs mb-4">No tenés más pacientes en espera ni eventos programados para el resto del día.</p>
                    <Button label="Abrir agenda" icon="pi pi-calendar" outlined size="small" rounded @click="emit('verAgenda')" />
                </div>
            </div>
        </div>
    </div>
</template>
