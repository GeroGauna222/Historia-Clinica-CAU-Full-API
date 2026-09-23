<script setup>
import pacienteService from '@/service/pacienteService';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/api/axios';

import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import IconField from 'primevue/iconfield';
import InputIcon from 'primevue/inputicon';

const toast = useToast();
const pacientes = ref([]);
const busqueda = ref('');
const router = useRouter();

const pacienteAEliminar = ref(null);
const mostrarDialog = ref(false);

// Estado Historial de Turnos
const pacienteHistorial = ref(null);
const turnosHistorial = ref([]);
const mostrarHistorialDialog = ref(false);
const cargandoHistorial = ref(false);

// Estado Edición de Turno dentro del Historial
const turnoAEditar = ref(null);
const mostrarEditarTurnoDialog = ref(false);
const editMotivo = ref('');
const editObservaciones = ref('');
const guardandoEditTurno = ref(false);

// Estado Eliminación de Turno dentro del Historial
const turnoAEliminar = ref(null);
const mostrarEliminarTurnoDialog = ref(false);

const opcionesAsistencia = [
    { label: 'Programado', value: 'programado' },
    { label: 'Presente', value: 'presente' },
    { label: 'Falta con aviso', value: 'con_aviso' },
    { label: 'Falta sin aviso', value: 'sin_aviso' }
];

const fetchPacientes = async () => {
    try {
        const res = await pacienteService.getPacientes();
        pacientes.value = res.data;
    } catch (err) {
        console.error(err);
    }
};

onMounted(() => {
    fetchPacientes();
});

const filtrados = computed(() => {
    if (!busqueda.value) return pacientes.value;
    const q = busqueda.value.toLowerCase();
    return pacientes.value.filter((p) => p.nombre.toLowerCase().includes(q) || p.apellido.toLowerCase().includes(q) || p.dni.includes(q) || (p.nro_hc && p.nro_hc.toLowerCase().includes(q)));
});

const editarPaciente = (id) => {
    router.push(`/pacientes/${id}/editar`);
};

const confirmarEliminar = (paciente) => {
    pacienteAEliminar.value = paciente;
    mostrarDialog.value = true;
};

const cancelarEliminar = () => {
    pacienteAEliminar.value = null;
    mostrarDialog.value = false;
};

const eliminarPacienteConfirmado = async () => {
    if (!pacienteAEliminar.value) return;
    try {
        await pacienteService.deletePaciente(pacienteAEliminar.value.id);
        pacientes.value = pacientes.value.filter((p) => p.id !== pacienteAEliminar.value.id);
        mostrarDialog.value = false;
        pacienteAEliminar.value = null;
        toast.add({ severity: 'success', summary: 'Éxito', detail: 'Paciente eliminado correctamente.', life: 3000 });
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar el paciente. Puede tener historias clínicas asociadas.', life: 5000 });
    }
};

const formatFecha = (fecha) => {
    if (!fecha) return '-';
    const d = new Date(fecha);
    return new Intl.DateTimeFormat('es-AR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(d);
};

const formatFechaHora = (iso) => {
    if (!iso) return '-';
    const d = new Date(iso);
    return new Intl.DateTimeFormat('es-AR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(d);
};

// Historial
const verHistorial = async (paciente) => {
    pacienteHistorial.value = paciente;
    turnosHistorial.value = [];
    cargandoHistorial.value = true;
    mostrarHistorialDialog.value = true;

    try {
        const res = await pacienteService.getTurnos(paciente.id);
        turnosHistorial.value = res.data || [];
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo cargar el historial de turnos.', life: 4000 });
    } finally {
        cargandoHistorial.value = false;
    }
};

const cambiarAsistenciaTurno = async (turno, estado) => {
    try {
        const isGrupal = turno.tipo === 'grupal';
        const url = isGrupal ? `/turnos/grupales/${turno.turnoId}/asistencia` : `/turnos/${turno.turnoId}/asistencia`;
        await api.patch(url, { estado_asistencia: estado }, { withCredentials: true });
        turno.estado_asistencia = estado;
        turno.ausencia = estado === 'con_aviso' || estado === 'sin_aviso' ? estado : null;
        toast.add({ severity: 'success', summary: 'Asistencia', detail: 'Estado de asistencia actualizado.', life: 3000 });
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo actualizar la asistencia.', life: 3500 });
    }
};

const abrirEditarTurno = (turno) => {
    turnoAEditar.value = turno;
    editMotivo.value = turno.description || '';
    editObservaciones.value = turno.observaciones || '';
    mostrarEditarTurnoDialog.value = true;
};

const guardarEdicionTurno = async () => {
    if (!turnoAEditar.value) return;
    guardandoEditTurno.value = true;
    try {
        const isGrupal = turnoAEditar.value.tipo === 'grupal';
        const url = isGrupal ? `/turnos/grupales/${turnoAEditar.value.turnoId}` : `/turnos/${turnoAEditar.value.turnoId}`;
        const payload = { motivo: editMotivo.value, observaciones: editObservaciones.value };
        await api.put(url, payload, { withCredentials: true });

        turnoAEditar.value.description = editMotivo.value;
        turnoAEditar.value.observaciones = editObservaciones.value;
        mostrarEditarTurnoDialog.value = false;
        toast.add({ severity: 'success', summary: 'Éxito', detail: 'Turno actualizado correctamente.', life: 3000 });
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo actualizar el turno.', life: 3500 });
    } finally {
        guardandoEditTurno.value = false;
    }
};

const confirmarEliminarTurno = (turno) => {
    turnoAEliminar.value = turno;
    mostrarEliminarTurnoDialog.value = true;
};

const eliminarTurnoConfirmado = async () => {
    if (!turnoAEliminar.value) return;
    try {
        const isGrupal = turnoAEliminar.value.tipo === 'grupal';
        const url = isGrupal ? `/turnos/grupales/${turnoAEliminar.value.turnoId}` : `/turnos/${turnoAEliminar.value.turnoId}`;
        await api.delete(url, { withCredentials: true });

        turnosHistorial.value = turnosHistorial.value.filter((t) => t.id !== turnoAEliminar.value.id);
        mostrarEliminarTurnoDialog.value = false;
        turnoAEliminar.value = null;
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Turno eliminado correctamente.', life: 3000 });
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar el turno.', life: 3500 });
    }
};
</script>

<template>
    <div class="p-6 md:p-8 w-full h-full">
        <div class="bg-card shadow-xl rounded-2xl p-6 transition-colors">
            <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                <h1 class="text-3xl font-bold text-color">Listado de Pacientes</h1>

                <div class="flex gap-2 w-full md:w-auto">
                    <IconField iconPosition="left" class="w-full md:w-64">
                        <InputIcon class="pi pi-search" />
                        <InputText v-model="busqueda" placeholder="Buscar paciente..." class="w-full" />
                    </IconField>

                    <Button icon="pi pi-user-plus" label="Nuevo" @click="router.push('/pacientes/registrar')" />
                </div>
            </div>

            <div class="overflow-x-auto">
                <DataTable :value="filtrados" paginator :rows="10" :rowsPerPageOptions="[5, 10, 20]" tableStyle="min-width: 60rem" stripedRows class="p-datatable-sm">
                    <template #empty>
                        <div class="text-center p-8 text-muted-color">
                            <i class="pi pi-users text-4xl mb-3 block"></i>
                            No se encontraron pacientes.
                        </div>
                    </template>

                    <Column field="dni" header="DNI" sortable class="font-bold"></Column>
                    <Column field="apellido" header="Apellido" sortable></Column>
                    <Column field="nombre" header="Nombre" sortable></Column>

                    <Column field="fecha_nacimiento" header="Nacimiento" sortable>
                        <template #body="slotProps">
                            {{ formatFecha(slotProps.data.fecha_nacimiento) }}
                        </template>
                    </Column>

                    <Column field="nro_hc" header="N° H.C." sortable></Column>

                    <Column field="telefono" header="Teléfono">
                        <template #body="slotProps">
                            <span v-if="slotProps.data.telefono || slotProps.data.celular" class="text-sm flex items-center gap-1">
                                <i class="pi pi-phone text-muted-color"></i>
                                {{ slotProps.data.celular || slotProps.data.telefono }}
                            </span>
                            <span v-else class="text-muted-color text-sm">-</span>
                        </template>
                    </Column>

                    <Column header="Acciones" :exportable="false" headerClass="text-right" bodyClass="text-right" style="width: 160px; text-align: right" headerStyle="width: 160px; text-align: right;">
                        <template #body="slotProps">
                            <div class="flex justify-end gap-1 pr-1">
                                <Button icon="pi pi-history" text rounded severity="help" title="Historial de Turnos" @click="verHistorial(slotProps.data)" />
                                <Button icon="pi pi-pencil" text rounded severity="info" title="Editar Paciente" @click="editarPaciente(slotProps.data.id)" />
                                <Button icon="pi pi-trash" text rounded severity="danger" title="Eliminar Paciente" @click="confirmarEliminar(slotProps.data)" />
                            </div>
                        </template>
                    </Column>
                </DataTable>
            </div>
        </div>

        <!-- Dialog Confirmar Eliminación Paciente -->
        <Dialog v-model:visible="mostrarDialog" modal header="Confirmar Eliminación" :style="{ width: '400px' }" :draggable="false">
            <div class="flex items-center gap-3 mb-4">
                <i class="pi pi-exclamation-triangle text-status-sin-aviso-fg text-4xl"></i>
                <div class="text-color">
                    <p class="font-bold text-lg mb-1">¿Estás seguro?</p>
                    <p class="text-sm">
                        Vas a eliminar al paciente <strong>{{ pacienteAEliminar?.apellido }} {{ pacienteAEliminar?.nombre }}</strong
                        >. <br />Esta acción eliminará sus datos permanentemente.
                    </p>
                </div>
            </div>

            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="cancelarEliminar" />
                <Button label="Sí, Eliminar" severity="danger" icon="pi pi-trash" @click="eliminarPacienteConfirmado" />
            </template>
        </Dialog>

        <!-- Modal Historial de Turnos del Paciente -->
        <Dialog v-model:visible="mostrarHistorialDialog" modal :header="`Historial de Turnos - ${pacienteHistorial?.apellido || ''} ${pacienteHistorial?.nombre || ''}`" :style="{ width: '90vw', maxWidth: '1000px' }" :draggable="false">
            <div v-if="cargandoHistorial" class="text-center p-8 text-muted-color">
                <i class="pi pi-spin pi-spinner text-3xl mb-2 block"></i>
                Cargando historial de turnos...
            </div>

            <div v-else class="overflow-x-auto">
                <DataTable :value="turnosHistorial" paginator :rows="5" :rowsPerPageOptions="[5, 10, 20]" stripedRows class="p-datatable-sm" tableStyle="min-width: 50rem">
                    <template #empty>
                        <div class="text-center p-6 text-muted-color">
                            <i class="pi pi-calendar-times text-3xl mb-2 block"></i>
                            El paciente no tiene turnos registrados.
                        </div>
                    </template>

                    <Column header="Fecha / Hora" sortable field="start" style="width: 180px">
                        <template #body="slotProps">
                            <span class="font-medium">{{ formatFechaHora(slotProps.data.start) }}</span>
                        </template>
                    </Column>

                    <Column header="Tipo" field="tipo" style="width: 110px">
                        <template #body="slotProps">
                            <Tag :severity="slotProps.data.tipo === 'grupal' ? 'info' : 'success'" :value="slotProps.data.tipo === 'grupal' ? 'Grupal' : 'Individual'" />
                        </template>
                    </Column>

                    <Column header="Profesional / Grupo" field="profesional">
                        <template #body="slotProps">
                            <span class="font-semibold">{{ slotProps.data.profesional || '-' }}</span>
                        </template>
                    </Column>

                    <Column header="Motivo / Obs." field="description">
                        <template #body="slotProps">
                            <div>
                                <p class="text-sm font-medium">{{ slotProps.data.description || 'Sin motivo' }}</p>
                                <p v-if="slotProps.data.observaciones" class="text-xs text-muted-color italic">
                                    {{ slotProps.data.observaciones }}
                                </p>
                            </div>
                        </template>
                    </Column>

                    <Column header="Asistencia" style="width: 170px">
                        <template #body="slotProps">
                            <Select
                                :modelValue="slotProps.data.estado_asistencia || (slotProps.data.ausencia ? slotProps.data.ausencia : 'programado')"
                                :options="opcionesAsistencia"
                                optionLabel="label"
                                optionValue="value"
                                class="w-full text-xs"
                                @update:modelValue="(val) => cambiarAsistenciaTurno(slotProps.data, val)"
                            />
                        </template>
                    </Column>

                    <Column header="Acciones" headerClass="text-right" bodyClass="text-right" style="width: 100px">
                        <template #body="slotProps">
                            <div class="flex justify-end gap-1">
                                <Button icon="pi pi-pencil" text rounded severity="info" title="Editar Turno" @click="abrirEditarTurno(slotProps.data)" />
                                <Button icon="pi pi-trash" text rounded severity="danger" title="Eliminar Turno" @click="confirmarEliminarTurno(slotProps.data)" />
                            </div>
                        </template>
                    </Column>
                </DataTable>
            </div>

            <template #footer>
                <Button label="Cerrar" text severity="secondary" @click="mostrarHistorialDialog = false" />
            </template>
        </Dialog>

        <!-- Sub-Dialog Editar Turno desde Historial -->
        <Dialog v-model:visible="mostrarEditarTurnoDialog" modal header="Editar Turno" :style="{ width: '450px' }" :draggable="false">
            <div class="flex flex-col gap-4 mt-2">
                <div>
                    <label class="block mb-1 font-medium text-sm">Motivo</label>
                    <InputText v-model="editMotivo" class="w-full" placeholder="Ej: Control general" />
                </div>
                <div>
                    <label class="block mb-1 font-medium text-sm">Observaciones</label>
                    <Textarea v-model="editObservaciones" rows="3" class="w-full" placeholder="Detalles u observaciones..." />
                </div>
            </div>

            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="mostrarEditarTurnoDialog = false" />
                <Button label="Guardar" icon="pi pi-check" severity="primary" :loading="guardandoEditTurno" @click="guardarEdicionTurno" />
            </template>
        </Dialog>

        <!-- Sub-Dialog Eliminar Turno desde Historial -->
        <Dialog v-model:visible="mostrarEliminarTurnoDialog" modal header="Eliminar Turno" :style="{ width: '400px' }" :draggable="false">
            <div class="flex items-center gap-3 mb-4">
                <i class="pi pi-exclamation-triangle text-status-sin-aviso-fg text-3xl"></i>
                <p class="text-sm">¿Estás seguro de que deseas eliminar este turno? Esta acción no se puede deshacer.</p>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="mostrarEliminarTurnoDialog = false" />
                <Button label="Sí, Eliminar" severity="danger" icon="pi pi-trash" @click="eliminarTurnoConfirmado" />
            </template>
        </Dialog>
    </div>
</template>
