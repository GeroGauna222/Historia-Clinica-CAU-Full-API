<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import Toast from 'primevue/toast';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Select from 'primevue/select';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import recetaService from '@/service/recetasService';
import historiaService from '@/service/historiaService';
import pacienteService from '@/service/pacienteService';
import { useUserStore } from '@/stores/user';

const DEFAULT_DIAGNOSTICO_CODIGO = 'Z769';
const DEFAULT_DIAGNOSTICO_TEXTO = 'Z76.9 - Persona en contacto con los servicios de salud en circunstancias no especificadas';
const DEFAULT_OBSERVACION = 'Tratamiento prolongado';

const toast = useToast();
const userStore = useUserStore();
const loading = ref(false);
const modo = ref('receta');
const pacientes = ref([]);
const pacienteSeleccionado = ref(null);
const busquedaPaciente = ref('');
const financiadores = ref([]);
const medicamentos = ref([]);
const diagnosticos = ref([]);
const medicamentoBusqueda = ref('');
const diagnosticoBusqueda = ref(`${DEFAULT_DIAGNOSTICO_CODIGO} - ${DEFAULT_DIAGNOSTICO_TEXTO}`);
const medicamentoActivo = ref(0);
const emitida = ref(null);

const modoOptions = [
    { label: 'Recetas', value: 'receta' },
    { label: 'Estudios', value: 'estudio' }
];
const sexoOptions = [
    { label: 'Femenino', value: 'F' },
    { label: 'Masculino', value: 'M' },
    { label: 'Otro', value: 'X' }
];
const matriculaOptions = ['MN', 'MP', 'OP'];
const lugarAtencionFijo = {
    nombreConsultorio: 'CAU UNSAM',
    email: 'cau@unsam.edu.ar',
    domicilio: {
        calle: 'Av. 25 de Mayo',
        numero: '1169',
        direccion: 'Av. 25 de Mayo 1169'
    }
};

function nuevoMedicamento() {
    return {
        nombreProducto: '',
        nombreDroga: '',
        presentacion: '',
        regNo: '',
        cantidad: 1,
        posologia: '',
        tratamiento: 0,
        permiteSustitucion: ''
    };
}

function nuevoEstudio() {
    return {
        texto: '',
        codigoDiagnostico: DEFAULT_DIAGNOSTICO_CODIGO,
        diagnostico: DEFAULT_DIAGNOSTICO_TEXTO,
        observaciones: DEFAULT_OBSERVACION
    };
}

const form = reactive({
    financiador: null,
    afiliado: '',
    planId: null,
    planNombre: '',
    medico: {
        apellido: '',
        nombre: '',
        tipoDoc: 'DNI',
        nroDoc: '',
        sexo: 'X',
        especialidad: '',
        email: '',
        telefono: '',
        matricula: { tipo: 'MN', numero: '', provincia: '' }
    },
    medicamentos: [nuevoMedicamento()],
    codigoDiagnostico: DEFAULT_DIAGNOSTICO_CODIGO,
    diagnostico: DEFAULT_DIAGNOSTICO_TEXTO,
    indicaciones: '',
    observaciones: DEFAULT_OBSERVACION,
    estudios: [nuevoEstudio()],
    lugarAtencion: {
        ...lugarAtencionFijo,
        domicilio: { ...lugarAtencionFijo.domicilio }
    }
});

const planesFinanciador = computed(() => form.financiador?.planes || []);
const profesionalCompleto = computed(() => form.medico.apellido && form.medico.nombre && form.medico.nroDoc && form.medico.matricula.numero);
const medicamentosValidos = computed(
    () => form.medicamentos.length > 0 && form.medicamentos.length <= 3 && form.medicamentos.every((medicamento) => Number(medicamento.cantidad) >= 1 && Number(medicamento.cantidad) <= 2 && (medicamento.regNo || medicamento.nombreProducto))
);
const estudiosValidos = computed(() => form.estudios.length > 0 && form.estudios.every((estudio) => estudio.texto.trim()));
const puedeEmitir = computed(() => pacienteSeleccionado.value && profesionalCompleto.value && (modo.value === 'receta' ? medicamentosValidos.value : estudiosValidos.value));

function dividirNombreUsuario(nombreCompleto) {
    const partes = (nombreCompleto || '').trim().split(/\s+/).filter(Boolean);
    if (partes.length <= 1) return { nombre: partes[0] || '', apellido: '' };
    return { nombre: partes.slice(0, -1).join(' '), apellido: partes.at(-1) };
}

async function buscarPacientes() {
    if (busquedaPaciente.value.trim().length < 2) {
        pacientes.value = [];
        return;
    }
    const { data } = await historiaService.buscarPacientes(busquedaPaciente.value.trim());
    pacientes.value = data.pacientes || [];
}

async function seleccionarPaciente(paciente) {
    const { data } = await pacienteService.getPaciente(paciente.id);
    pacienteSeleccionado.value = data;
    pacientes.value = [];
    busquedaPaciente.value = `${data.apellido}, ${data.nombre} - DNI ${data.dni}`;
}

async function buscarMedicamentos(index = medicamentoActivo.value) {
    medicamentoActivo.value = index;
    if (medicamentoBusqueda.value.trim().length < 2) return;
    const { data } = await recetaService.buscarMedicamentos({
        q: medicamentoBusqueda.value.trim(),
        idFinanciador: form.financiador?.idfinanciador,
        afiliadoDni: pacienteSeleccionado.value?.dni,
        afiliadoCredencial: form.afiliado,
        planid: form.planId
    });
    medicamentos.value = data.medicamentos || [];
}

function seleccionarMedicamento(medicamento) {
    const destino = form.medicamentos[medicamentoActivo.value];
    destino.nombreProducto = medicamento.nombreProducto || '';
    destino.nombreDroga = medicamento.nombreDroga || '';
    destino.presentacion = medicamento.presentacion || '';
    destino.regNo = medicamento.regNo || '';
    medicamentos.value = [];
    medicamentoBusqueda.value = `${destino.nombreProducto} ${destino.presentacion}`.trim();
}

function agregarMedicamento() {
    if (form.medicamentos.length >= 3) return;
    form.medicamentos.push(nuevoMedicamento());
    medicamentoActivo.value = form.medicamentos.length - 1;
    medicamentoBusqueda.value = '';
}

function quitarMedicamento(index) {
    if (form.medicamentos.length === 1) return;
    form.medicamentos.splice(index, 1);
    medicamentoActivo.value = 0;
}

async function buscarDiagnosticos() {
    if (diagnosticoBusqueda.value.trim().length < 3) return;
    const { data } = await recetaService.buscarDiagnosticos(diagnosticoBusqueda.value.trim());
    diagnosticos.value = data.diagnosticos || [];
}

function seleccionarDiagnostico(diagnostico) {
    form.codigoDiagnostico = diagnostico.coddiagnostico || DEFAULT_DIAGNOSTICO_CODIGO;
    form.diagnostico = diagnostico.descdiagnostico || DEFAULT_DIAGNOSTICO_TEXTO;
    diagnosticoBusqueda.value = `${form.codigoDiagnostico} - ${form.diagnostico}`;
    diagnosticos.value = [];
}

function agregarEstudio() {
    form.estudios.push(nuevoEstudio());
}

function quitarEstudio(index) {
    if (form.estudios.length === 1) return;
    form.estudios.splice(index, 1);
}

async function cargarFinanciadores() {
    try {
        const { data } = await recetaService.getFinanciadores();
        financiadores.value = data.financiadores || [];
    } catch (error) {
        toast.add({ severity: 'warn', summary: 'Qbitos', detail: error.response?.data?.error || 'No se pudieron cargar financiadores', life: 4500 });
    }
}

function coberturaPayload() {
    if (!form.financiador) return null;
    const planSeleccionado = planesFinanciador.value.find((plan) => plan.id === form.planId);
    return {
        idFinanciador: String(form.financiador.idfinanciador),
        planId: form.planId || null,
        plan: form.planNombre || planSeleccionado?.nombre || null,
        numero: form.afiliado || null
    };
}

function payloadBase() {
    return {
        paciente_id: pacienteSeleccionado.value.id,
        tipo: modo.value,
        cobertura: coberturaPayload(),
        codigoDiagnostico: form.codigoDiagnostico,
        diagnostico: form.diagnostico,
        indicaciones: form.indicaciones,
        observaciones: form.observaciones,
        lugarAtencion: form.lugarAtencion
    };
}

function armarPayload() {
    const base = payloadBase();
    if (modo.value === 'receta') {
        return {
            ...base,
            medicamentos: form.medicamentos.map((medicamento) => ({
                ...medicamento,
                cantidad: Number(medicamento.cantidad || 1),
                tratamiento: Number(medicamento.tratamiento || 0)
            }))
        };
    }
    return {
        ...base,
        estudios: form.estudios.map((estudio) => ({
            texto: estudio.texto,
            codigoDiagnostico: estudio.codigoDiagnostico || form.codigoDiagnostico,
            diagnostico: estudio.diagnostico || form.diagnostico,
            observaciones: estudio.observaciones || form.observaciones
        }))
    };
}

async function emitir() {
    if (!puedeEmitir.value) {
        toast.add({ severity: 'warn', summary: 'Datos incompletos', detail: 'Completa paciente, profesional y los items a emitir.', life: 4000 });
        return;
    }
    loading.value = true;
    emitida.value = null;
    try {
        const { data } = await recetaService.emitir(armarPayload());
        emitida.value = data;
        toast.add({ severity: 'success', summary: modo.value === 'receta' ? 'Receta emitida' : 'Estudios emitidos', detail: data.message, life: 4500 });
    } catch (error) {
        const detail = error.response?.data?.detail?.mensaje || error.response?.data?.detail?.error || error.response?.data?.error || 'No se pudo emitir la solicitud.';
        toast.add({ severity: 'error', summary: 'Error de emision', detail, life: 7000 });
    } finally {
        loading.value = false;
    }
}

onMounted(async () => {
    await userStore.fetchUser();
    const nombre = dividirNombreUsuario(userStore.nombre);
    form.medico.nombre = nombre.nombre;
    form.medico.apellido = nombre.apellido;
    form.medico.nroDoc = userStore.dni || '';
    form.medico.sexo = userStore.sexo || 'X';
    form.medico.telefono = userStore.telefono || '';
    form.medico.email = userStore.email || '';
    form.medico.especialidad = userStore.especialidad || '';
    form.medico.matricula.tipo = userStore.matricula_tipo || 'MN';
    form.medico.matricula.numero = userStore.matricula_numero || '';
    form.medico.matricula.provincia = userStore.matricula_provincia || '';
    cargarFinanciadores();
});
</script>

<template>
    <Toast />
    <div class="space-y-6">
        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
                <h1 class="text-3xl font-bold text-color m-0">Recetas electronicas</h1>
                <p class="text-color-secondary m-0">Emision de medicamentos y estudios por Qbitos Recipe.</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
                <Select v-model="modo" :options="modoOptions" optionLabel="label" optionValue="value" class="w-48" />
                <Button label="Emitir" icon="pi pi-send" :loading="loading" :disabled="!puedeEmitir" @click="emitir" />
            </div>
        </div>

        <section class="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-4">
                <h2 class="text-lg font-semibold m-0 mb-4">Paciente</h2>
                <InputText v-model="busquedaPaciente" class="w-full" placeholder="Buscar por DNI o nombre" @input="buscarPacientes" />
                <div v-if="pacientes.length" class="mt-2 border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
                    <button v-for="paciente in pacientes" :key="paciente.id" type="button" class="w-full text-left p-3 border-0 bg-transparent hover:bg-surface-100 dark:hover:bg-surface-800 cursor-pointer" @click="seleccionarPaciente(paciente)">
                        <span class="font-medium">{{ paciente.apellido }}, {{ paciente.nombre }}</span>
                        <span class="block text-sm text-color-secondary">DNI {{ paciente.dni }} - HC {{ paciente.nro_hc }}</span>
                    </button>
                </div>
                <div v-if="pacienteSeleccionado" class="mt-4 text-sm text-color-secondary">
                    <p class="m-0">
                        <b>{{ pacienteSeleccionado.apellido }}, {{ pacienteSeleccionado.nombre }}</b>
                    </p>
                    <p class="m-0">DNI {{ pacienteSeleccionado.dni }} - {{ pacienteSeleccionado.fecha_nacimiento || 'Sin fecha de nacimiento' }}</p>
                </div>
            </div>

            <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-4 xl:col-span-2">
                <h2 class="text-lg font-semibold m-0 mb-4">Cobertura</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Select v-model="form.financiador" :options="financiadores" optionLabel="nombreComercial" filter showClear placeholder="Particular / sin financiador" class="w-full" />
                    <InputText v-model="form.afiliado" placeholder="Numero de afiliado" class="w-full" :disabled="!form.financiador" />
                    <Select v-model="form.planId" :options="planesFinanciador" optionLabel="nombre" optionValue="id" showClear placeholder="Plan" class="w-full" :disabled="!planesFinanciador.length" />
                    <InputText v-if="form.financiador && !planesFinanciador.length" v-model="form.planNombre" placeholder="Plan (si corresponde)" class="w-full md:col-span-3" />
                </div>
            </div>
        </section>

        <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-4">
            <h2 class="text-lg font-semibold m-0 mb-4">Profesional</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                <InputText v-model="form.medico.apellido" placeholder="Apellido" class="w-full" disabled />
                <InputText v-model="form.medico.nombre" placeholder="Nombre" class="w-full" disabled />
                <InputText v-model="form.medico.tipoDoc" class="w-full" disabled />
                <InputText v-model="form.medico.nroDoc" placeholder="Documento" class="w-full" disabled />
                <Select v-model="form.medico.sexo" :options="sexoOptions" optionLabel="label" optionValue="value" class="w-full" disabled />
                <InputText v-model="form.medico.especialidad" placeholder="Especialidad" class="w-full" disabled />
                <Select v-model="form.medico.matricula.tipo" :options="matriculaOptions" class="w-full" disabled />
                <InputText v-model="form.medico.matricula.numero" placeholder="Matricula" class="w-full" disabled />
                <InputText v-if="form.medico.matricula.tipo === 'MP'" v-model="form.medico.matricula.provincia" placeholder="Provincia matricula" class="w-full" disabled />
            </div>
        </section>

        <section class="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-4 xl:col-span-2">
                <div v-if="modo === 'receta'">
                    <div class="flex items-center justify-between gap-3 mb-4">
                        <h2 class="text-lg font-semibold m-0">Medicamentos</h2>
                        <Button label="Agregar" icon="pi pi-plus" text :disabled="form.medicamentos.length >= 3" @click="agregarMedicamento" />
                    </div>
                    <div class="flex gap-2">
                        <InputText v-model="medicamentoBusqueda" class="w-full" placeholder="Buscar medicamento" @keyup.enter="buscarMedicamentos()" />
                        <Button icon="pi pi-search" text rounded @click="buscarMedicamentos()" />
                    </div>
                    <DataTable v-if="medicamentos.length" :value="medicamentos" size="small" class="mt-3" :rows="5">
                        <Column field="nombreProducto" header="Producto" />
                        <Column field="presentacion" header="Presentacion" />
                        <Column field="nombreDroga" header="Droga" />
                        <Column header="Accion" bodyClass="text-right">
                            <template #body="{ data }">
                                <Button icon="pi pi-check" text rounded @click="seleccionarMedicamento(data)" />
                            </template>
                        </Column>
                    </DataTable>

                    <div v-for="(medicamento, index) in form.medicamentos" :key="index" class="mt-4 border border-surface-200 dark:border-surface-700 rounded-lg p-3">
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <span class="font-medium">Medicamento {{ index + 1 }}</span>
                            <div class="flex gap-1">
                                <Button icon="pi pi-search" text rounded @click="medicamentoActivo = index" />
                                <Button icon="pi pi-trash" text rounded severity="danger" :disabled="form.medicamentos.length === 1" @click="quitarMedicamento(index)" />
                            </div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                            <InputText v-model="medicamento.nombreProducto" placeholder="Producto" class="w-full md:col-span-2" @focus="medicamentoActivo = index" />
                            <InputText v-model="medicamento.presentacion" placeholder="Presentacion" class="w-full md:col-span-2" />
                            <InputText v-model="medicamento.nombreDroga" placeholder="Droga" class="w-full md:col-span-2" />
                            <InputText v-model="medicamento.regNo" placeholder="RegNo" class="w-full" />
                            <InputText v-model.number="medicamento.cantidad" type="number" min="1" max="2" placeholder="Cantidad" class="w-full" />
                            <Textarea v-model="medicamento.posologia" rows="3" autoResize placeholder="Posologia" class="w-full md:col-span-4" />
                        </div>
                    </div>
                </div>

                <div v-else>
                    <div class="flex items-center justify-between gap-3 mb-4">
                        <h2 class="text-lg font-semibold m-0">Estudios</h2>
                        <Button label="Agregar" icon="pi pi-plus" text @click="agregarEstudio" />
                    </div>
                    <div v-for="(estudio, index) in form.estudios" :key="index" class="mb-4 border border-surface-200 dark:border-surface-700 rounded-lg p-3">
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <span class="font-medium">Estudio {{ index + 1 }}</span>
                            <Button icon="pi pi-trash" text rounded severity="danger" :disabled="form.estudios.length === 1" @click="quitarEstudio(index)" />
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                            <Textarea v-model="estudio.texto" rows="3" autoResize placeholder="Texto libre de practica" class="w-full md:col-span-4" />
                            <InputText v-model="estudio.codigoDiagnostico" placeholder="Codigo diagnostico" class="w-full" />
                            <InputText v-model="estudio.diagnostico" placeholder="Diagnostico" class="w-full md:col-span-2" />
                            <InputText v-model="estudio.observaciones" placeholder="Observaciones" class="w-full" />
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-4">
                <h2 class="text-lg font-semibold m-0 mb-4">Diagnostico general</h2>
                <div class="flex gap-2">
                    <InputText v-model="diagnosticoBusqueda" class="w-full" placeholder="Buscar CIE-10" @keyup.enter="buscarDiagnosticos" />
                    <Button icon="pi pi-search" text rounded @click="buscarDiagnosticos" />
                </div>
                <div v-if="diagnosticos.length" class="mt-2 border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden max-h-56 overflow-y-auto">
                    <button
                        v-for="diagnostico in diagnosticos"
                        :key="diagnostico.iddiagnostico"
                        type="button"
                        class="w-full text-left p-3 border-0 bg-transparent hover:bg-surface-100 dark:hover:bg-surface-800 cursor-pointer"
                        @click="seleccionarDiagnostico(diagnostico)"
                    >
                        <span class="font-medium">{{ diagnostico.coddiagnostico }}</span>
                        <span class="block text-sm text-color-secondary">{{ diagnostico.descdiagnostico }}</span>
                    </button>
                </div>
                <InputText v-model="form.codigoDiagnostico" placeholder="Codigo diagnostico" class="w-full mt-3" />
                <InputText v-model="form.diagnostico" placeholder="Diagnostico" class="w-full mt-3" />
                <Textarea v-model="form.indicaciones" rows="3" autoResize placeholder="Indicaciones generales" class="w-full mt-3" />
                <Textarea v-model="form.observaciones" rows="3" autoResize placeholder="Observaciones" class="w-full mt-3" />
            </div>
        </section>

        <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-4">
            <h2 class="text-lg font-semibold m-0 mb-4">Lugar de atencion</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                <InputText v-model="form.lugarAtencion.nombreConsultorio" class="w-full" disabled />
                <InputText v-model="form.lugarAtencion.domicilio.calle" class="w-full" disabled />
                <InputText v-model="form.lugarAtencion.domicilio.numero" class="w-full" disabled />
                <InputText v-model="form.lugarAtencion.email" class="w-full" disabled />
            </div>
        </section>

        <section v-if="emitida" class="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <h2 class="text-lg font-semibold m-0 mb-3">Resultado</h2>
            <div v-if="emitida.qbitos" class="space-y-2">
                <div v-for="receta in emitida.qbitos.recetas || []" :key="receta.idReceta || receta.id" class="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                    <span>ID receta: {{ receta.idReceta || receta.id }}</span>
                    <a v-if="receta.s3Link" :href="receta.s3Link" target="_blank" rel="noopener" class="text-primary-600 font-medium">Abrir PDF</a>
                </div>
            </div>
            <div v-else class="space-y-2">
                <div v-for="resultado in emitida.resultados || []" :key="resultado.estudioIndex" class="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                    <span>Estudio {{ resultado.estudioIndex + 1 }} emitido</span>
                    <a v-for="receta in (resultado.qbitos.recetas || []).filter((item) => item.s3Link)" :key="receta.idReceta || receta.id" :href="receta.s3Link" target="_blank" rel="noopener" class="text-primary-600 font-medium">Abrir PDF</a>
                </div>
            </div>
        </section>
    </div>
</template>
