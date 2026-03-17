<script setup>
import DatePicker from 'primevue/datepicker';
import { ref, watch } from 'vue';
import pacienteService from '@/service/pacienteService';

// Props
const props = defineProps({
    paciente: {
        type: Object,
        default: () => ({})
    },
    onSubmit: {
        type: Function,
        required: false
    },
    submitText: {
        type: String,
        default: 'Registrar'
    }
});

const paciente = ref({ ...props.paciente }); // copiamos para mantener reactividad
const mensaje = ref('');
const tipoMensaje = ref('');
const intentadoEnviar = ref(false);

// Si las props cambian (por ejemplo, al montar EditarPaciente.vue), actualizamos los campos
watch(
    () => props.paciente,
    (nuevo) => {
        paciente.value = { ...nuevo };
    },
    { deep: true }
);

function normalizarFechaISO(fecha) {
    if (!fecha) return null;

    // Caso 1: Si es un objeto Date (lo que devuelve PrimeVue)
    if (fecha instanceof Date) {
        const year = fecha.getFullYear();
        const month = String(fecha.getMonth() + 1).padStart(2, '0');
        const day = String(fecha.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`; // → "2000-08-29"
    }

    // Caso 2: Si viene como string ISO con zona horaria
    if (typeof fecha === 'string' && fecha.includes('T')) {
        return fecha.split('T')[0];
    }

    // Caso 3: Si viene como dd/mm/yyyy
    if (typeof fecha === 'string' && fecha.includes('/')) {
        const [dia, mes, ano] = fecha.split('/');
        return `${ano}-${mes}-${dia}`;
    }

    return fecha;
}

// Función principal: o registrar o actualizar
const registrar = async () => {
    intentadoEnviar.value = true;

    if (
        !paciente.value.nro_hc ||
        !paciente.value.nombre ||
        !paciente.value.apellido ||
        !paciente.value.dni ||
        !paciente.value.fecha_nacimiento ||
        !paciente.value.sexo ||
        !paciente.value.email ||
        (!paciente.value.telefono && !paciente.value.celular)
    ) {
        mensaje.value = '⚠️ Completá todos los campos obligatorios.';
        tipoMensaje.value = 'error';
        return;
    }

    try {
        // Normalizar fecha antes de enviar al backend
        paciente.value.fecha_nacimiento = normalizarFechaISO(paciente.value.fecha_nacimiento);

        const formData = new FormData();
        for (const key in paciente.value) {
            formData.append(key, paciente.value[key]);
        }

        // Si hay función onSubmit, la usamos (caso editar)
        if (props.onSubmit) {
            await props.onSubmit(paciente.value);
            mensaje.value = '✅ Paciente actualizado correctamente.';
            tipoMensaje.value = 'success';
        } else {
            // Si no hay onSubmit, registramos nuevo paciente
            const response = await pacienteService.crearPaciente(formData);

            if (response.data && response.data.message) {
                mensaje.value = response.data.message;
                tipoMensaje.value = 'success';
                paciente.value = {};
                intentadoEnviar.value = false;
            } else if (response.data && response.data.error) {
                mensaje.value = response.data.error;
                tipoMensaje.value = 'error';
            } else {
                mensaje.value = '⚠️ Error inesperado al registrar paciente.';
                tipoMensaje.value = 'error';
            }
        }
    } catch (error) {
        console.error(error);
        mensaje.value = '❌ Error de red o servidor.';
        tipoMensaje.value = 'error';
    }
};
</script>

<template>
    <div class="p-4">
        <h1 class="text-2xl font-bold mb-4">Registrar Paciente</h1>
        <form @submit.prevent="registrar">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- N° de H.C. -->
                <div>
                    <label class="block mb-1">Nº de H.C. <span class="text-red-500">*</span></label>
                    <input v-model="paciente.nro_hc" type="text" class="p-inputtext p-component w-full h-12" />
                    <span v-if="intentadoEnviar && !paciente.nro_hc" class="text-red-500 text-sm">Campo obligatorio</span>
                </div>
                <!-- Nombre -->
                <div>
                    <label class="block mb-1">Nombre <span class="text-red-500">*</span></label>
                    <input v-model="paciente.nombre" type="text" class="p-inputtext p-component w-full h-12" />
                    <span v-if="intentadoEnviar && !paciente.nombre" class="text-red-500 text-sm">Campo obligatorio</span>
                </div>
                <!-- Apellido -->
                <div>
                    <label class="block mb-1">Apellido <span class="text-red-500">*</span></label>
                    <input v-model="paciente.apellido" type="text" class="p-inputtext p-component w-full h-12" />
                    <span v-if="intentadoEnviar && !paciente.apellido" class="text-red-500 text-sm">Campo obligatorio</span>
                </div>
                <!-- DNI -->
                <div>
                    <label class="block mb-1">N° de Documento <span class="text-red-500">*</span></label>
                    <input v-model="paciente.dni" type="text" class="p-inputtext p-component w-full h-12" />
                    <span v-if="intentadoEnviar && !paciente.dni" class="text-red-500 text-sm">Campo obligatorio</span>
                </div>
                <!-- Fecha de nacimiento -->
                <div>
                    <label class="block mb-1">Fecha de Nacimiento <span class="text-red-500">*</span></label>
                    <DatePicker v-model="paciente.fecha_nacimiento" dateFormat="dd/mm/yy" :showIcon="true" class="p-inputtext p-component w-full h-12" />
                    <span v-if="intentadoEnviar && !paciente.fecha_nacimiento" class="text-red-500 text-sm">Campo obligatorio</span>
                </div>
                <!-- Sexo -->
                <div>
                    <label class="block mb-1">Sexo <span class="text-red-500">*</span></label>
                    <select v-model="paciente.sexo" class="p-inputtext p-component w-full h-12">
                        <option value="">Seleccionar</option>
                        <option>Femenino</option>
                        <option>Masculino</option>
                        <option>Otro</option>
                    </select>
                    <span v-if="intentadoEnviar && !paciente.sexo" class="text-red-500 text-sm">Campo obligatorio</span>
                </div>
                <!-- Ocupación -->
                <div>
                    <label class="block mb-1">Ocupación</label>
                    <input v-model="paciente.ocupacion" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Nacionalidad -->
                <div>
                    <label class="block mb-1">Nacionalidad</label>
                    <input v-model="paciente.nacionalidad" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Dirección -->
                <div>
                    <label class="block mb-1">Dirección (Calle, CP, Ciudad)</label>
                    <input v-model="paciente.direccion" type="text" class="p-inputtext p-component w-full h-12" placeholder="Ej: Savio 1683, CP 1650, San Martín" />
                </div>
                <!-- Código postal -->
                <div>
                    <label class="block mb-1">Código Postal</label>
                    <input v-model="paciente.codigo_postal" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Teléfono -->
                <div>
                    <label class="block mb-1">Teléfono <span class="text-red-500">*</span> o Celular</label>
                    <input v-model="paciente.telefono" type="text" class="p-inputtext p-component w-full h-12" />
                    <span v-if="intentadoEnviar && !paciente.telefono && !paciente.celular" class="text-red-500 text-sm">Ingresar al menos uno</span>
                </div>
                <!-- Celular -->
                <div>
                    <label class="block mb-1">Celular</label>
                    <input v-model="paciente.celular" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Email -->
                <div>
                    <label class="block mb-1">Mail <span class="text-red-500">*</span></label>
                    <input v-model="paciente.email" type="email" class="p-inputtext p-component w-full h-12" />
                    <span v-if="intentadoEnviar && !paciente.email" class="text-red-500 text-sm">Campo obligatorio</span>
                </div>
                <!-- Contacto -->
                <div>
                    <label class="block mb-1">Contacto</label>
                    <input v-model="paciente.contacto" type="text" class="p-inputtext p-component w-full h-12" placeholder="Ej: Hija Natalia" />
                </div>
                <!-- Cobertura -->
                <div>
                    <label class="block mb-1">Cobertura</label>
                    <input v-model="paciente.cobertura" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Certificado discapacidad -->
                <div>
                    <label class="block mb-1">Certificado de Discapacidad</label>
                    <select v-model="paciente.cert_discapacidad" class="p-inputtext p-component w-full h-12">
                        <option value="">Seleccionar</option>
                        <option value="Si">Si</option>
                        <option value="No">No</option>
                    </select>
                </div>
                <!-- Nº Certificado -->
                <div>
                    <label class="block mb-1">Nº Certificado</label>
                    <input v-model="paciente.nro_certificado" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Derivado por -->
                <div>
                    <label class="block mb-1">Derivado por</label>
                    <input v-model="paciente.derivado_por" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Diagnóstico -->
                <div>
                    <label class="block mb-1">Diagnóstico</label>
                    <input v-model="paciente.diagnostico" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Motivo derivación -->
                <div>
                    <label class="block mb-1">Motivo de derivación</label>
                    <input v-model="paciente.motivo_derivacion" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
                <!-- Médico cabecera -->
                <div>
                    <label class="block mb-1">Médico de cabecera</label>
                    <input v-model="paciente.medico_cabecera" type="text" class="p-inputtext p-component w-full h-12" />
                </div>
            </div>
            <!-- Motivo de ingreso -->
            <div class="mt-6">
                <label class="block mb-1">Motivo de Ingreso</label>
                <textarea v-model="paciente.motivo_ingreso" rows="3" class="p-inputtext p-component w-full"></textarea>
            </div>
            <!-- Enfermedad actual -->
            <div class="mt-6">
                <label class="block mb-1">Enfermedad Actual</label>
                <textarea v-model="paciente.enfermedad_actual" rows="3" class="p-inputtext p-component w-full"></textarea>
            </div>
            <!-- Antecedentes de la enfermedad actual -->
            <div class="mt-6">
                <label class="block mb-1">Antecedentes de la Enfermedad Actual</label>
                <textarea v-model="paciente.antecedentes_enfermedad_actual" rows="3" class="p-inputtext p-component w-full"></textarea>
            </div>
            <!-- Antecedentes personales -->
            <div class="mt-6">
                <label class="block mb-1">Antecedentes Personales</label>
                <textarea v-model="paciente.antecedentes_personales" rows="3" class="p-inputtext p-component w-full"></textarea>
            </div>
            <!-- Antecedentes Heredo-Familiares -->
            <div class="mt-6">
                <label class="block mb-1">Antecedentes Heredo-Familiares</label>
                <textarea v-model="paciente.antecedentes_heredofamiliares" rows="3" class="p-inputtext p-component w-full"></textarea>
            </div>
            <!-- Comentarios -->
            <div class="mt-6">
                <label class="block mb-1">Comentarios</label>
                <textarea v-model="paciente.comentarios" rows="4" class="p-inputtext p-component w-full"></textarea>
            </div>

            <!--  <button type="submit" class="p-button p-component mt-6 bg-green-500 text-white">Registrar</button> -->

            <Button type="submit" :label="submitText" class="mt-6 w-auto" />
        </form>

        <!-- Mensaje -->
        <p v-if="mensaje" :class="tipoMensaje === 'success' ? 'text-green-600' : 'text-red-600'" class="mt-4">
            {{ mensaje }}
        </p>
    </div>
</template>

<style scoped></style>
