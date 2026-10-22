<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';
import facturacionService from '@/service/facturacionService';
import pacienteService from '@/service/pacienteService';

const toast = useToast();

const FINANCIADORES = [
    {
        key: 'medicus',
        nombre: 'Medicus (OSUNSAM)',
        subtitulo: 'Planilla de homologación de 28 columnas · Efector E171513',
        badge: 'Código Homologado + Efector'
    },
    {
        key: 'ospoce',
        nombre: 'OSPOCE',
        subtitulo: 'Planilla con Fecha, Afiliado, N° Afiliado, Práctica, Autorización e Importe',
        badge: 'Práctica + Autorización'
    },
    {
        key: 'corporacion',
        nombre: 'Corporación',
        subtitulo: 'Planilla con Fecha, Paciente, N° Afiliado, Razón, Sesiones, CUD e Importe',
        badge: 'Razón + Sesiones + CUD'
    }
];

const financiadorActivo = ref('medicus');
const infoFinanciador = computed(() => FINANCIADORES.find((f) => f.key === financiadorActivo.value) || FINANCIADORES[0]);

// Datos maestros
const pacientes = ref([]);
const practicas = ref([]);
const prestadores = ref([]);
const registros = ref([]);
const resumen = ref({ total_registros: 0, total_sesiones: 0, total_importe: 0 });

const loadingRegistros = ref(false);
const guardandoCarga = ref(false);
const exportando = ref(false);

// Filtros de visualización y exportación
function mesActualISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

const filtro = reactive({
    modoFecha: 'mes', // 'mes' | 'rango' | 'todos'
    mes: mesActualISO(),
    fecha_desde: '',
    fecha_hasta: '',
    busqueda: '',
    practica_id: ''
});

// Selección múltiple en tabla
const seleccionados = ref([]);
const todosSeleccionados = computed({
    get() {
        return registros.value.length > 0 && seleccionados.value.length === registros.value.length;
    },
    set(val) {
        seleccionados.value = val ? registros.value.map((r) => r.id) : [];
    }
});

// Prácticas y prestadores filtrados por financiador activo
const practicasFinanciador = computed(() => practicas.value.filter((p) => p.financiador === financiadorActivo.value && p.activo));

const prestadoresFinanciador = computed(() => prestadores.value.filter((p) => p.financiador === financiadorActivo.value && p.activo));

// Autocompletado de paciente en el formulario de carga
const pacienteQuery = ref('');
const mostrarSugerenciasPaciente = ref(false);

const pacientesSugeridos = computed(() => {
    const q = (pacienteQuery.value || '').trim().toLowerCase();
    if (!q) return pacientes.value.slice(0, 12);
    return pacientes.value
        .filter((p) => {
            const apeNom = `${p.apellido || ''} ${p.nombre || ''}`.toLowerCase();
            const dni = String(p.dni || '').toLowerCase();
            const afi = String(p.nro_certificado || '').toLowerCase();
            const hc = String(p.nro_hc || '').toLowerCase();
            return apeNom.includes(q) || dni.includes(q) || afi.includes(q) || hc.includes(q);
        })
        .slice(0, 15);
});

function hoyISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// Formulario de nueva carga (admite 1 o múltiples fechas para el mismo paciente y práctica)
const formCarga = reactive({
    paciente_id: null,
    paciente_nombre: '',
    nro_afiliado: '',
    cud: 'NO',
    practica_id: '',
    practica_codigo: '',
    practica_descripcion: '',
    importe: '',
    prestador_id: '',
    contexto: 'A',
    lugar_realizacion_efector: 'E171513',
    tipo_matricula: 'P',
    nro_matricula: '441983',
    observaciones: '',
    items: [{ fecha_realizacion: hoyISO(), autorizacion: '', cantidad: 1 }]
});

function seleccionarPrestadorDefault() {
    const lista = prestadoresFinanciador.value;
    const def = lista.find((p) => p.es_predeterminado) || lista[0];
    if (def) {
        formCarga.prestador_id = def.id;
        formCarga.contexto = def.contexto || 'A';
        formCarga.lugar_realizacion_efector = def.lugar_realizacion_efector || 'E171513';
        formCarga.tipo_matricula = def.tipo_matricula || 'P';
        formCarga.nro_matricula = def.nro_matricula || '441983';
    }
}

function onChangePrestadorCarga() {
    const sel = prestadores.value.find((p) => p.id === Number(formCarga.prestador_id));
    if (sel) {
        formCarga.contexto = sel.contexto || 'A';
        formCarga.lugar_realizacion_efector = sel.lugar_realizacion_efector || '';
        formCarga.tipo_matricula = sel.tipo_matricula || 'P';
        formCarga.nro_matricula = sel.nro_matricula || '';
    }
}

function onChangePracticaCarga() {
    const sel = practicas.value.find((p) => p.id === Number(formCarga.practica_id));
    if (sel) {
        formCarga.practica_codigo = sel.codigo;
        formCarga.practica_descripcion = sel.descripcion;
        formCarga.importe = Number(sel.importe || 0).toFixed(2);
    }
}

function elegirPaciente(p) {
    formCarga.paciente_id = p.id;
    formCarga.paciente_nombre = `${p.apellido || ''} ${p.nombre || ''}`.trim().toUpperCase();
    formCarga.nro_afiliado = (p.nro_certificado || '').trim();
    const certRaw = String(p.cert_discapacidad || '').toLowerCase();
    formCarga.cud = certRaw === 'sí' || certRaw === 'si' ? 'SI' : 'NO';
    pacienteQuery.value = `${formCarga.paciente_nombre} ${formCarga.nro_afiliado ? `(${formCarga.nro_afiliado})` : `(DNI ${p.dni})`}`;
    mostrarSugerenciasPaciente.value = false;
}

function ocultarSugerenciasConDelay() {
    setTimeout(() => {
        mostrarSugerenciasPaciente.value = false;
    }, 180);
}

function agregarFilaFecha() {
    const ultimaFecha = formCarga.items[formCarga.items.length - 1]?.fecha_realizacion || hoyISO();
    formCarga.items.push({
        fecha_realizacion: ultimaFecha,
        autorizacion: '',
        cantidad: 1
    });
}

function quitarFilaFecha(index) {
    if (formCarga.items.length <= 1) return;
    formCarga.items.splice(index, 1);
}

function limpiarFormularioCarga() {
    formCarga.paciente_id = null;
    formCarga.paciente_nombre = '';
    formCarga.nro_afiliado = '';
    formCarga.cud = 'NO';
    formCarga.practica_id = '';
    formCarga.practica_codigo = '';
    formCarga.practica_descripcion = '';
    formCarga.importe = '';
    formCarga.observaciones = '';
    formCarga.items = [{ fecha_realizacion: hoyISO(), autorizacion: '', cantidad: 1 }];
    pacienteQuery.value = '';
    seleccionarPrestadorDefault();
}

function formatearMoneda(valor) {
    const num = Number(valor || 0);
    return num.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatearFechaCorta(iso) {
    if (!iso) return '';
    const partes = String(iso).slice(0, 10).split('-');
    if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`;
    return iso;
}

function construirParamsFiltro() {
    const params = { financiador: financiadorActivo.value };
    if (filtro.modoFecha === 'mes' && filtro.mes) {
        params.mes = filtro.mes;
    } else if (filtro.modoFecha === 'rango') {
        if (filtro.fecha_desde) params.fecha_desde = filtro.fecha_desde;
        if (filtro.fecha_hasta) params.fecha_hasta = filtro.fecha_hasta;
    }
    if (filtro.busqueda.trim()) params.busqueda = filtro.busqueda.trim();
    if (filtro.practica_id) params.practica_id = filtro.practica_id;
    return params;
}

async function cargarCatalogos() {
    try {
        const [resPrac, resPrest] = await Promise.all([facturacionService.getPracticas({ incluir_inactivas: 1 }), facturacionService.getPrestadores({ incluir_inactivos: 1 })]);
        practicas.value = Array.isArray(resPrac.data) ? resPrac.data : [];
        prestadores.value = Array.isArray(resPrest.data) ? resPrest.data : [];
        seleccionarPrestadorDefault();
    } catch (err) {
        console.error('Error cargando catálogos de facturación:', err);
        toast.add({
            severity: 'error',
            summary: 'Catálogos',
            detail: 'No se pudieron cargar los catálogos de prácticas y prestadores.',
            life: 4000
        });
    }
}

async function cargarPacientesPadron() {
    try {
        const res = await pacienteService.getPacientes();
        pacientes.value = Array.isArray(res.data) ? res.data : res.data?.pacientes || [];
    } catch (err) {
        console.error('Error cargando padrón de pacientes:', err);
    }
}

async function cargarRegistros() {
    loadingRegistros.value = true;
    seleccionados.value = [];
    try {
        const params = construirParamsFiltro();
        const res = await facturacionService.getRegistros(params);
        registros.value = res.data?.registros || [];
        resumen.value = res.data?.resumen || { total_registros: 0, total_sesiones: 0, total_importe: 0 };
    } catch (err) {
        console.error('Error cargando registros de facturación:', err);
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No se pudieron obtener las entradas de facturación.',
            life: 4000
        });
    } finally {
        loadingRegistros.value = false;
    }
}

async function guardarNuevaCarga() {
    if (!formCarga.nro_afiliado.trim()) {
        toast.add({ severity: 'warn', summary: 'Falta N° Afiliado', detail: 'Ingresá o seleccioná el N° de cobertura/afiliado del paciente.', life: 3500 });
        return;
    }
    if (financiadorActivo.value !== 'medicus' && !formCarga.paciente_nombre.trim()) {
        toast.add({ severity: 'warn', summary: 'Falta Paciente', detail: 'Ingresá el Apellido y Nombre del paciente.', life: 3500 });
        return;
    }
    if (!formCarga.practica_codigo.trim()) {
        toast.add({ severity: 'warn', summary: 'Falta Práctica', detail: 'Seleccioná una práctica del catálogo.', life: 3500 });
        return;
    }

    guardandoCarga.value = true;
    try {
        const payload = {
            financiador: financiadorActivo.value,
            paciente_id: formCarga.paciente_id,
            paciente_nombre: formCarga.paciente_nombre.trim() || formCarga.nro_afiliado.trim(),
            nro_afiliado: formCarga.nro_afiliado.trim(),
            cud: formCarga.cud,
            practica_id: formCarga.practica_id || null,
            practica_codigo: formCarga.practica_codigo.trim(),
            practica_descripcion: formCarga.practica_descripcion.trim() || formCarga.practica_codigo.trim(),
            importe: formCarga.importe,
            prestador_id: formCarga.prestador_id || null,
            contexto: formCarga.contexto,
            lugar_realizacion_efector: formCarga.lugar_realizacion_efector,
            tipo_matricula: formCarga.tipo_matricula,
            nro_matricula: formCarga.nro_matricula,
            observaciones: formCarga.observaciones,
            items: formCarga.items
        };

        const res = await facturacionService.crearRegistros(payload);
        toast.add({
            severity: 'success',
            summary: 'Prestación registrada',
            detail: res.data?.message || 'Se guardó correctamente.',
            life: 3000
        });

        // Si la primera fecha cargada pertenece a otro mes cuando está filtrado por mes, sincronizar el filtro para verla
        const primeraFecha = formCarga.items[0]?.fecha_realizacion || '';
        if (filtro.modoFecha === 'mes' && primeraFecha.length >= 7 && filtro.mes !== primeraFecha.slice(0, 7)) {
            filtro.mes = primeraFecha.slice(0, 7);
        }

        // Mantener el paciente o limpiar las fechas para seguir cargando ágilmente
        formCarga.items = [{ fecha_realizacion: primeraFecha || hoyISO(), autorizacion: '', cantidad: 1 }];
        await cargarRegistros();
    } catch (err) {
        const detail = err?.response?.data?.error || 'No se pudo registrar la prestación.';
        toast.add({ severity: 'error', summary: 'Error al guardar', detail, life: 4000 });
    } finally {
        guardandoCarga.value = false;
    }
}

// Duplicar una fila existente en el formulario de carga para agregarle otra fecha rápido
function precargarDesdeFila(reg) {
    formCarga.paciente_id = reg.paciente_id;
    formCarga.paciente_nombre = reg.paciente_nombre;
    formCarga.nro_afiliado = reg.nro_afiliado;
    formCarga.cud = reg.cud || 'NO';
    formCarga.practica_id = reg.practica_id || '';
    formCarga.practica_codigo = reg.practica_codigo;
    formCarga.practica_descripcion = reg.practica_descripcion;
    formCarga.importe = Number(reg.importe || 0).toFixed(2);
    if (reg.prestador_id) formCarga.prestador_id = reg.prestador_id;
    formCarga.contexto = reg.contexto || 'A';
    formCarga.lugar_realizacion_efector = reg.lugar_realizacion_efector || 'E171513';
    formCarga.tipo_matricula = reg.tipo_matricula || 'P';
    formCarga.nro_matricula = reg.nro_matricula || '441983';
    pacienteQuery.value = `${reg.paciente_nombre} (${reg.nro_afiliado})`;
    formCarga.items = [{ fecha_realizacion: reg.fecha_realizacion || hoyISO(), autorizacion: '', cantidad: reg.cantidad || 1 }];
    toast.add({
        severity: 'info',
        summary: 'Datos copiados al formulario',
        detail: 'Cambiá la fecha o autorización y presioná Guardar.',
        life: 2500
    });
}

// Edición de registro individual
const modalEditarRegistro = ref(false);
const editRegistroForm = reactive({
    id: null,
    fecha_realizacion: '',
    paciente_nombre: '',
    nro_afiliado: '',
    cud: 'NO',
    cantidad: 1,
    practica_id: '',
    practica_codigo: '',
    practica_descripcion: '',
    importe: 0,
    autorizacion: '',
    contexto: 'A',
    lugar_realizacion_efector: '',
    tipo_matricula: 'P',
    nro_matricula: ''
});

function abrirEditarRegistro(reg) {
    Object.assign(editRegistroForm, {
        id: reg.id,
        fecha_realizacion: reg.fecha_realizacion,
        paciente_nombre: reg.paciente_nombre,
        nro_afiliado: reg.nro_afiliado,
        cud: reg.cud || 'NO',
        cantidad: reg.cantidad || 1,
        practica_id: reg.practica_id || '',
        practica_codigo: reg.practica_codigo,
        practica_descripcion: reg.practica_descripcion,
        importe: Number(reg.importe || 0).toFixed(2),
        autorizacion: reg.autorizacion || '',
        contexto: reg.contexto || 'A',
        lugar_realizacion_efector: reg.lugar_realizacion_efector || 'E171513',
        tipo_matricula: reg.tipo_matricula || 'P',
        nro_matricula: reg.nro_matricula || '441983'
    });
    modalEditarRegistro.value = true;
}

function onChangePracticaEdit() {
    const sel = practicas.value.find((p) => p.id === Number(editRegistroForm.practica_id));
    if (sel) {
        editRegistroForm.practica_codigo = sel.codigo;
        editRegistroForm.practica_descripcion = sel.descripcion;
        editRegistroForm.importe = Number(sel.importe || 0).toFixed(2);
    }
}

async function guardarEdicionRegistro() {
    try {
        await facturacionService.actualizarRegistro(editRegistroForm.id, { ...editRegistroForm });
        modalEditarRegistro.value = false;
        toast.add({ severity: 'success', summary: 'Actualizado', detail: 'Registro actualizado correctamente.', life: 2800 });
        await cargarRegistros();
    } catch (err) {
        const detail = err?.response?.data?.error || 'No se pudo actualizar el registro.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    }
}

async function borrarRegistro(reg) {
    if (!confirm(`¿Eliminar la prestación del ${formatearFechaCorta(reg.fecha_realizacion)} de ${reg.paciente_nombre || reg.nro_afiliado}?`)) return;
    try {
        await facturacionService.eliminarRegistro(reg.id);
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Entrada eliminada.', life: 2500 });
        await cargarRegistros();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar la entrada.', life: 3500 });
    }
}

async function borrarSeleccionados() {
    if (!seleccionados.value.length) return;
    if (!confirm(`¿Eliminar las ${seleccionados.value.length} entradas seleccionadas?`)) return;
    try {
        await facturacionService.eliminarRegistrosLote(seleccionados.value);
        toast.add({ severity: 'success', summary: 'Eliminados', detail: 'Se eliminaron las entradas seleccionadas.', life: 3000 });
        await cargarRegistros();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudieron eliminar las entradas.', life: 3500 });
    }
}

async function recalcularPreciosDelPeriodo() {
    if (!registros.value.length) return;
    if (!confirm('¿Actualizar los importes de las entradas listadas en este período con los valores actuales del catálogo?')) return;
    try {
        const params = construirParamsFiltro();
        const res = await facturacionService.recalcularPreciosPeriodo(params);
        toast.add({ severity: 'success', summary: 'Precios actualizados', detail: res.data?.message, life: 3500 });
        await cargarRegistros();
    } catch (err) {
        const detail = err?.response?.data?.error || 'No se pudieron recalcular los importes.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    }
}

async function descargarExportacion(formato) {
    exportando.value = true;
    try {
        const params = { ...construirParamsFiltro(), formato };
        const response = await facturacionService.exportarFacturacion(params);
        const blob = new Blob([response.data], {
            type: formato === 'xlsx' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv;charset=utf-8;'
        });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        const sufijo = filtro.modoFecha === 'mes' && filtro.mes ? filtro.mes : filtro.modoFecha === 'rango' ? `${filtro.fecha_desde || 'inicio'}_a_${filtro.fecha_hasta || 'fin'}` : 'completo';
        a.href = url;
        a.download = `facturacion_${financiadorActivo.value}_${sufijo}.${formato}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        toast.add({
            severity: 'success',
            summary: 'Archivo descargado',
            detail: `Exportación ${formato.toUpperCase()} generada correctamente.`,
            life: 3000
        });
    } catch (err) {
        console.error('Error exportando facturación:', err);
        toast.add({ severity: 'error', summary: 'Error al exportar', detail: 'No se pudo descargar el archivo.', life: 4000 });
    } finally {
        exportando.value = false;
    }
}

// ==========================================================
// 📋 GESTIÓN DE CATÁLOGO DE PRÁCTICAS (MODAL)
// ==========================================================
const modalCatalogoPracticas = ref(false);
const filtroCatalogoTexto = ref('');
const porcentajeAumento = ref('');

const nuevaPractica = reactive({
    id: null,
    categoria: 'Consulta',
    codigo: '',
    descripcion: '',
    importe: '',
    requiere_autorizacion: true
});

const practicasCatalogoModal = computed(() => {
    const q = (filtroCatalogoTexto.value || '').trim().toLowerCase();
    return practicas.value.filter((p) => p.financiador === financiadorActivo.value).filter((p) => !q || p.codigo.toLowerCase().includes(q) || p.descripcion.toLowerCase().includes(q) || (p.categoria || '').toLowerCase().includes(q));
});

function resetNuevaPractica() {
    nuevaPractica.id = null;
    nuevaPractica.categoria = 'Consulta';
    nuevaPractica.codigo = '';
    nuevaPractica.descripcion = '';
    nuevaPractica.importe = '';
    nuevaPractica.requiere_autorizacion = financiadorActivo.value !== 'corporacion';
}

function editarPracticaEnModal(p) {
    nuevaPractica.id = p.id;
    nuevaPractica.categoria = p.categoria || 'General';
    nuevaPractica.codigo = p.codigo;
    nuevaPractica.descripcion = p.descripcion;
    nuevaPractica.importe = Number(p.importe || 0).toFixed(2);
    nuevaPractica.requiere_autorizacion = p.requiere_autorizacion;
}

async function guardarPracticaCatalogo() {
    if (!nuevaPractica.codigo.trim()) {
        toast.add({ severity: 'warn', summary: 'Campo obligatorio', detail: 'Ingresá el código o nombre de la práctica.', life: 3000 });
        return;
    }
    try {
        const payload = {
            financiador: financiadorActivo.value,
            categoria: nuevaPractica.categoria || 'General',
            codigo: nuevaPractica.codigo.trim(),
            descripcion: (nuevaPractica.descripcion || nuevaPractica.codigo).trim(),
            importe: nuevaPractica.importe || 0,
            requiere_autorizacion: nuevaPractica.requiere_autorizacion,
            activo: true
        };
        if (nuevaPractica.id) {
            await facturacionService.actualizarPractica(nuevaPractica.id, payload);
            toast.add({ severity: 'success', summary: 'Práctica actualizada', detail: 'Se actualizó en el catálogo.', life: 2800 });
        } else {
            await facturacionService.crearPractica(payload);
            toast.add({ severity: 'success', summary: 'Práctica añadida', detail: 'Nueva práctica incorporada al catálogo.', life: 2800 });
        }
        resetNuevaPractica();
        await cargarCatalogos();
    } catch (err) {
        const detail = err?.response?.data?.error || 'No se pudo guardar la práctica.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    }
}

async function eliminarPracticaCatalogo(p) {
    if (!confirm(`¿Eliminar la práctica "${p.codigo} - ${p.descripcion}" del catálogo?`)) return;
    try {
        await facturacionService.eliminarPractica(p.id);
        toast.add({ severity: 'success', summary: 'Eliminada', detail: 'Práctica quitada del catálogo.', life: 2500 });
        await cargarCatalogos();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar la práctica.', life: 3500 });
    }
}

async function aplicarAumentoPorcentual() {
    const porc = String(porcentajeAumento.value || '').trim();
    if (!porc) {
        toast.add({ severity: 'warn', summary: 'Porcentaje requerido', detail: 'Ingresá un porcentaje (ej. 3.8).', life: 3000 });
        return;
    }
    if (!confirm(`¿Aplicar un aumento del ${porc}% a todas las prácticas de ${infoFinanciador.value.nombre}?`)) return;
    try {
        const res = await facturacionService.aumentoMasivoPracticas({
            financiador: financiadorActivo.value,
            porcentaje: porc
        });
        porcentajeAumento.value = '';
        toast.add({ severity: 'success', summary: 'Catálogo actualizado', detail: res.data?.message, life: 3500 });
        await cargarCatalogos();
    } catch (err) {
        const detail = err?.response?.data?.error || 'No se pudo aplicar el aumento.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    }
}

// ==========================================================
// 🏥 GESTIÓN DE PRESTADORES / EFECTORES (MODAL)
// ==========================================================
const modalPrestadores = ref(false);
const nuevoPrestador = reactive({
    id: null,
    nombre: '',
    contexto: 'A',
    lugar_realizacion_efector: '',
    tipo_matricula: 'P',
    nro_matricula: '',
    es_predeterminado: false
});

function resetNuevoPrestador() {
    nuevoPrestador.id = null;
    nuevoPrestador.nombre = '';
    nuevoPrestador.contexto = 'A';
    nuevoPrestador.lugar_realizacion_efector = '';
    nuevoPrestador.tipo_matricula = 'P';
    nuevoPrestador.nro_matricula = '';
    nuevoPrestador.es_predeterminado = false;
}

function editarPrestadorEnModal(pr) {
    nuevoPrestador.id = pr.id;
    nuevoPrestador.nombre = pr.nombre;
    nuevoPrestador.contexto = pr.contexto || 'A';
    nuevoPrestador.lugar_realizacion_efector = pr.lugar_realizacion_efector;
    nuevoPrestador.tipo_matricula = pr.tipo_matricula || 'P';
    nuevoPrestador.nro_matricula = pr.nro_matricula;
    nuevoPrestador.es_predeterminado = pr.es_predeterminado;
}

async function guardarPrestadorCatalogo() {
    if (!nuevoPrestador.nombre.trim() || !nuevoPrestador.lugar_realizacion_efector.trim() || !nuevoPrestador.nro_matricula.trim()) {
        toast.add({ severity: 'warn', summary: 'Datos incompletos', detail: 'Completá nombre, código efector y matrícula.', life: 3500 });
        return;
    }
    try {
        const payload = {
            financiador: 'medicus',
            nombre: nuevoPrestador.nombre.trim(),
            contexto: nuevoPrestador.contexto || 'A',
            lugar_realizacion_efector: nuevoPrestador.lugar_realizacion_efector.trim(),
            tipo_matricula: nuevoPrestador.tipo_matricula || 'P',
            nro_matricula: nuevoPrestador.nro_matricula.trim(),
            es_predeterminado: nuevoPrestador.es_predeterminado,
            activo: true
        };
        if (nuevoPrestador.id) {
            await facturacionService.actualizarPrestador(nuevoPrestador.id, payload);
            toast.add({ severity: 'success', summary: 'Prestador actualizado', detail: 'Datos guardados.', life: 2800 });
        } else {
            await facturacionService.crearPrestador(payload);
            toast.add({ severity: 'success', summary: 'Prestador añadido', detail: 'Se agregó al listado de prestadores.', life: 2800 });
        }
        resetNuevoPrestador();
        await cargarCatalogos();
    } catch (err) {
        const detail = err?.response?.data?.error || 'No se pudo guardar el prestador.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4000 });
    }
}

async function eliminarPrestadorCatalogo(pr) {
    if (!confirm(`¿Eliminar el prestador "${pr.nombre}"?`)) return;
    try {
        await facturacionService.eliminarPrestador(pr.id);
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Prestador quitado del listado.', life: 2500 });
        await cargarCatalogos();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar el prestador.', life: 3500 });
    }
}

watch(financiadorActivo, async () => {
    filtro.practica_id = '';
    formCarga.practica_id = '';
    formCarga.practica_codigo = '';
    formCarga.practica_descripcion = '';
    formCarga.importe = '';
    seleccionarPrestadorDefault();
    await cargarRegistros();
});

onMounted(async () => {
    await Promise.all([cargarCatalogos(), cargarPacientesPadron()]);
    await cargarRegistros();
});
</script>

<template>
    <div class="space-y-6">
        <Toast />

        <!-- Encabezado y Selector de Obra Social / Financiador -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <div class="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <div class="flex items-center gap-2">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-[#ccfbf1] text-[#0f766e]"> Administración & Dirección </span>
                        <span class="text-xs text-slate-500 font-mono">· Liquidación y Exportación de Prestaciones</span>
                    </div>
                    <h1 class="text-2xl font-black tracking-tight text-slate-900 dark:text-white mt-1">Facturación de Prestaciones</h1>
                    <p class="text-xs text-slate-500 mt-0.5">{{ infoFinanciador.subtitulo }}</p>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                    <Button label="Catálogo de Prácticas" icon="pi pi-list" severity="secondary" outlined size="small" @click="modalCatalogoPracticas = true" />
                    <Button v-if="financiadorActivo === 'medicus'" label="Datos de Prestadores" icon="pi pi-building" severity="secondary" outlined size="small" @click="modalPrestadores = true" />
                    <Button label="Exportar CSV" icon="pi pi-file" severity="secondary" size="small" :loading="exportando" @click="descargarExportacion('csv')" />
                    <Button label="Exportar Excel (.xlsx)" icon="pi pi-file-excel" severity="success" size="small" :loading="exportando" @click="descargarExportacion('xlsx')" />
                </div>
            </div>

            <!-- Pestañas de Obra Social -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
                <button
                    v-for="fin in FINANCIADORES"
                    :key="fin.key"
                    type="button"
                    @click="financiadorActivo = fin.key"
                    class="text-left p-3.5 rounded-xl border transition-all flex items-center justify-between"
                    :class="financiadorActivo === fin.key ? 'border-teal-600 bg-teal-50/70 dark:bg-teal-950/40 shadow-sm' : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 bg-slate-50/50 dark:bg-slate-800/40'"
                >
                    <div>
                        <div class="font-bold text-sm text-slate-900 dark:text-white">{{ fin.nombre }}</div>
                        <div class="text-xs text-slate-500 mt-0.5">{{ fin.badge }}</div>
                    </div>
                    <i class="pi text-lg" :class="financiadorActivo === fin.key ? 'pi-check-circle text-teal-600' : 'pi-circle text-slate-300'"></i>
                </button>
            </div>
        </div>

        <!-- Formulario de Carga Manual de Prestaciones -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
                <div>
                    <h2 class="text-base font-bold text-slate-900 dark:text-white">Cargar Prestaciones — {{ infoFinanciador.nombre }}</h2>
                    <p class="text-xs text-slate-500">Buscá al paciente en el padrón para autocompletar su N° de Cobertura y CUD, o completalo manualmente.</p>
                </div>
                <Button label="Limpiar formulario" icon="pi pi-refresh" text size="small" severity="secondary" @click="limpiarFormularioCarga" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                <!-- Buscador de Paciente -->
                <div class="md:col-span-4 relative">
                    <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Buscar Paciente en Padrón</label>
                    <InputText v-model="pacienteQuery" placeholder="Apellido, Nombre, DNI o N° Afiliado..." class="w-full" @focus="mostrarSugerenciasPaciente = true" @blur="ocultarSugerenciasConDelay" />
                    <div v-if="mostrarSugerenciasPaciente && pacientesSugeridos.length" class="absolute z-30 left-0 right-0 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                        <button
                            v-for="p in pacientesSugeridos"
                            :key="p.id"
                            type="button"
                            class="w-full text-left px-3 py-2 text-xs hover:bg-teal-50 dark:hover:bg-slate-700 border-b border-slate-100 dark:border-slate-700/50 last:border-0 flex items-center justify-between"
                            @mousedown.prevent="elegirPaciente(p)"
                        >
                            <div>
                                <span class="font-bold text-slate-800 dark:text-white">{{ p.apellido }}, {{ p.nombre }}</span>
                                <span class="text-slate-500 ml-2">DNI {{ p.dni }}</span>
                            </div>
                            <div class="text-right">
                                <span v-if="p.nro_certificado" class="font-mono text-teal-700 dark:text-teal-400 font-semibold">{{ p.nro_certificado }}</span>
                                <span v-else class="text-amber-600">Sin N° cobertura</span>
                            </div>
                        </button>
                    </div>
                </div>

                <!-- Nombre del Afiliado/Paciente -->
                <div class="md:col-span-4">
                    <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1"> Apellido y Nombre del Paciente <span v-if="financiadorActivo !== 'medicus'" class="text-red-500">*</span> </label>
                    <InputText v-model="formCarga.paciente_nombre" placeholder="Ej: NYGARD DAIANA" class="w-full uppercase" />
                </div>

                <!-- N° de Afiliado / Cobertura -->
                <div class="md:col-span-3">
                    <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">N° de Afiliado / Cobertura <span class="text-red-500">*</span></label>
                    <InputText v-model="formCarga.nro_afiliado" placeholder="Ej: 11197918006 o 110718/00" class="w-full font-mono" />
                </div>

                <!-- CUD -->
                <div class="md:col-span-1">
                    <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">CUD</label>
                    <select v-model="formCarga.cud" class="p-inputtext p-component w-full h-10 text-sm">
                        <option value="NO">NO</option>
                        <option value="SI">SI</option>
                    </select>
                </div>

                <!-- Práctica del Catálogo -->
                <div class="md:col-span-6">
                    <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Práctica / Prestación (Catálogo) <span class="text-red-500">*</span></label>
                    <select v-model="formCarga.practica_id" @change="onChangePracticaCarga" class="p-inputtext p-component w-full h-10 text-sm">
                        <option value="">— Seleccionar práctica de {{ infoFinanciador.nombre }} —</option>
                        <option v-for="pr in practicasFinanciador" :key="pr.id" :value="pr.id">{{ pr.financiador === 'medicus' ? `${pr.codigo} — ${pr.descripcion}` : pr.descripcion }} ($ {{ formatearMoneda(pr.importe) }})</option>
                    </select>
                </div>

                <!-- Código / Texto a exportar -->
                <div class="md:col-span-3">
                    <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        {{ financiadorActivo === 'medicus' ? 'Código a Homologar' : financiadorActivo === 'ospoce' ? 'Práctica a Exportar' : 'Razón a Exportar' }}
                    </label>
                    <InputText v-model="formCarga.practica_codigo" placeholder="Código o práctica" class="w-full font-mono" />
                </div>

                <!-- Importe / Honorarios -->
                <div class="md:col-span-3">
                    <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1"> {{ financiadorActivo === 'medicus' ? 'Honorarios ($)' : 'Importe ($)' }} <span class="text-red-500">*</span> </label>
                    <InputText v-model="formCarga.importe" type="number" step="0.01" placeholder="0.00" class="w-full font-mono" />
                </div>

                <!-- Datos de Prestador / Efector (Medicus) -->
                <template v-if="financiadorActivo === 'medicus'">
                    <div class="md:col-span-5">
                        <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Prestador / Efector (Listado)</label>
                        <select v-model="formCarga.prestador_id" @change="onChangePrestadorCarga" class="p-inputtext p-component w-full h-10 text-sm">
                            <option v-for="prest in prestadoresFinanciador" :key="prest.id" :value="prest.id">{{ prest.nombre }} ({{ prest.lugar_realizacion_efector }} · Mat. {{ prest.tipo_matricula }} {{ prest.nro_matricula }})</option>
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Contexto</label>
                        <InputText v-model="formCarga.contexto" class="w-full font-mono uppercase" />
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Lugar Efector</label>
                        <InputText v-model="formCarga.lugar_realizacion_efector" class="w-full font-mono" />
                    </div>
                    <div class="md:col-span-1">
                        <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Tipo Mat.</label>
                        <InputText v-model="formCarga.tipo_matricula" class="w-full font-mono uppercase" />
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">N° Matrícula</label>
                        <InputText v-model="formCarga.nro_matricula" class="w-full font-mono" />
                    </div>
                </template>
            </div>

            <!-- Fechas y Autorizaciones (Permite cargar 1 o varias sesiones de una vez) -->
            <div class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-bold text-slate-700 dark:text-slate-300"> Fecha(s) de Realización y Autorización ({{ formCarga.items.length }} sesión/es a cargar) </span>
                    <Button label="+ Agregar otra fecha para este paciente" icon="pi pi-calendar-plus" size="small" text @click="agregarFilaFecha" />
                </div>

                <div class="space-y-2">
                    <div v-for="(item, idx) in formCarga.items" :key="idx" class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-lg">
                        <div class="sm:col-span-4">
                            <label class="block text-[11px] text-slate-500 mb-0.5">Fecha de Prestación #{{ idx + 1 }}</label>
                            <input v-model="item.fecha_realizacion" type="date" class="p-inputtext p-component w-full h-9 text-sm" />
                        </div>
                        <div class="sm:col-span-5">
                            <label class="block text-[11px] text-slate-500 mb-0.5">
                                {{ financiadorActivo === 'medicus' ? 'ID Conectividad (Dato Adicional 5 - Opcional)' : financiadorActivo === 'ospoce' ? 'N° de Autorización' : 'N° de Autorización / Ref. (Opcional)' }}
                            </label>
                            <InputText v-model="item.autorizacion" placeholder="Ej: 38367745 o 764998" class="w-full h-9 text-sm font-mono" />
                        </div>
                        <div class="sm:col-span-2">
                            <label class="block text-[11px] text-slate-500 mb-0.5">{{ financiadorActivo === 'corporacion' ? 'Sesiones' : 'Cantidad' }}</label>
                            <input v-model.number="item.cantidad" type="number" min="1" class="p-inputtext p-component w-full h-9 text-sm font-mono" />
                        </div>
                        <div class="sm:col-span-1 flex justify-end pt-4">
                            <Button v-if="formCarga.items.length > 1" icon="pi pi-trash" severity="danger" text rounded size="small" @click="quitarFilaFecha(idx)" />
                        </div>
                    </div>
                </div>

                <div class="mt-4 flex justify-end">
                    <Button :label="formCarga.items.length > 1 ? `Guardar ${formCarga.items.length} Prestaciones` : 'Guardar Prestación'" icon="pi pi-check" :loading="guardandoCarga" @click="guardarNuevaCarga" />
                </div>
            </div>
        </div>

        <!-- Filtros de Período (Mes o Rango de Fechas) y Resumen -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div class="flex flex-wrap items-end justify-between gap-4">
                <div class="flex flex-wrap items-end gap-3">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Filtrar / Exportar por</label>
                        <select v-model="filtro.modoFecha" @change="cargarRegistros" class="p-inputtext p-component h-10 text-sm">
                            <option value="mes">Mes completo</option>
                            <option value="rango">Rango de fechas (Desde — Hasta)</option>
                            <option value="todos">Todas las fechas</option>
                        </select>
                    </div>

                    <div v-if="filtro.modoFecha === 'mes'">
                        <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Mes y Año</label>
                        <input v-model="filtro.mes" type="month" @change="cargarRegistros" class="p-inputtext p-component h-10 text-sm" />
                    </div>

                    <template v-if="filtro.modoFecha === 'rango'">
                        <div>
                            <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Desde fecha</label>
                            <input v-model="filtro.fecha_desde" type="date" @change="cargarRegistros" class="p-inputtext p-component h-10 text-sm" />
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Hasta fecha</label>
                            <input v-model="filtro.fecha_hasta" type="date" @change="cargarRegistros" class="p-inputtext p-component h-10 text-sm" />
                        </div>
                    </template>

                    <div>
                        <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Práctica</label>
                        <select v-model="filtro.practica_id" @change="cargarRegistros" class="p-inputtext p-component h-10 text-sm max-w-xs">
                            <option value="">Todas las prácticas</option>
                            <option v-for="pr in practicasFinanciador" :key="pr.id" :value="pr.id">
                                {{ pr.financiador === 'medicus' ? `${pr.codigo} - ${pr.descripcion}` : pr.descripcion }}
                            </option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Buscar en tabla</label>
                        <InputText v-model="filtro.busqueda" placeholder="Paciente, afiliado o autorización..." class="h-10 text-sm" @keyup.enter="cargarRegistros" />
                    </div>

                    <Button icon="pi pi-search" label="Filtrar" size="small" severity="secondary" @click="cargarRegistros" />
                </div>

                <!-- Resumen rápido del período filtrado -->
                <div class="flex flex-wrap items-center gap-4 bg-slate-50 dark:bg-slate-800/70 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div>
                        <div class="text-[11px] uppercase tracking-wider text-slate-500">Entradas</div>
                        <div class="text-base font-black text-slate-900 dark:text-white">{{ resumen.total_registros }}</div>
                    </div>
                    <div class="h-7 w-px bg-slate-200 dark:bg-slate-700"></div>
                    <div>
                        <div class="text-[11px] uppercase tracking-wider text-slate-500">Total Período</div>
                        <div class="text-base font-black text-teal-700 dark:text-teal-400 font-mono">$ {{ formatearMoneda(resumen.total_importe) }}</div>
                    </div>
                </div>
            </div>

            <!-- Acciones sobre los registros listados -->
            <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <div class="flex items-center gap-2">
                    <Button v-if="seleccionados.length > 0" :label="`Eliminar seleccionados (${seleccionados.length})`" icon="pi pi-trash" severity="danger" size="small" outlined @click="borrarSeleccionados" />
                    <Button v-if="registros.length > 0" label="Actualizar importes del período según catálogo actual" icon="pi pi-sync" severity="secondary" size="small" text @click="recalcularPreciosDelPeriodo" />
                </div>
                <div class="text-xs text-slate-500">
                    Al hacer clic en <strong>Exportar CSV</strong> o <strong>Exportar Excel</strong> se descargarán las <strong>{{ registros.length }}</strong> entradas filtradas.
                </div>
            </div>

            <!-- Tabla de Entradas -->
            <div class="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-xl">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs uppercase">
                            <th class="p-3 w-10">
                                <input type="checkbox" v-model="todosSeleccionados" />
                            </th>
                            <th class="p-3">Fecha</th>
                            <th class="p-3">Paciente</th>
                            <th class="p-3">N° Afiliado</th>
                            <th class="p-3">{{ financiadorActivo === 'medicus' ? 'Prestación (Código + Descripción)' : financiadorActivo === 'ospoce' ? 'Práctica' : 'Razón' }}</th>
                            <th v-if="financiadorActivo === 'medicus'" class="p-3">Efector / Matrícula</th>
                            <th v-if="financiadorActivo !== 'corporacion'" class="p-3">{{ financiadorActivo === 'medicus' ? 'ID Conectividad' : 'Autorización' }}</th>
                            <th v-if="financiadorActivo === 'corporacion'" class="p-3 text-center">Sesiones</th>
                            <th v-if="financiadorActivo === 'corporacion'" class="p-3 text-center">CUD</th>
                            <th class="p-3 text-right">{{ financiadorActivo === 'medicus' ? 'Honorarios' : 'Importe' }}</th>
                            <th class="p-3 text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-200 dark:divide-slate-800">
                        <tr v-if="loadingRegistros">
                            <td colspan="10" class="p-8 text-center text-slate-500">Cargando prestaciones...</td>
                        </tr>
                        <tr v-else-if="registros.length === 0">
                            <td colspan="10" class="p-8 text-center text-slate-500">No hay prestaciones cargadas para {{ infoFinanciador.nombre }} en el período seleccionado.</td>
                        </tr>
                        <tr v-for="reg in registros" :key="reg.id" class="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                            <td class="p-3">
                                <input type="checkbox" :value="reg.id" v-model="seleccionados" />
                            </td>
                            <td class="p-3 font-mono text-xs whitespace-nowrap">{{ reg.fecha_realizacion }}</td>
                            <td class="p-3 font-medium text-slate-900 dark:text-white">{{ reg.paciente_nombre }}</td>
                            <td class="p-3 font-mono text-xs">{{ reg.nro_afiliado }}</td>
                            <td class="p-3">
                                <span v-if="financiadorActivo === 'medicus'" class="font-mono font-bold text-teal-700 dark:text-teal-400 mr-1.5">{{ reg.practica_codigo }}</span>
                                <span class="text-xs text-slate-700 dark:text-slate-300">{{ financiadorActivo === 'medicus' ? reg.practica_descripcion : reg.practica_codigo }}</span>
                            </td>
                            <td v-if="financiadorActivo === 'medicus'" class="p-3 font-mono text-xs text-slate-600 dark:text-slate-400">
                                {{ reg.lugar_realizacion_efector || 'E171513' }} · {{ reg.tipo_matricula || 'P' }}-{{ reg.nro_matricula || '441983' }}
                            </td>
                            <td v-if="financiadorActivo !== 'corporacion'" class="p-3 font-mono text-xs">
                                {{ reg.autorizacion || '—' }}
                            </td>
                            <td v-if="financiadorActivo === 'corporacion'" class="p-3 text-center font-mono text-xs">
                                {{ reg.cantidad }}
                            </td>
                            <td v-if="financiadorActivo === 'corporacion'" class="p-3 text-center">
                                <span class="px-2 py-0.5 rounded text-xs font-bold" :class="reg.cud === 'SI' ? 'bg-teal-100 text-teal-800' : 'bg-slate-100 text-slate-700'">
                                    {{ reg.cud }}
                                </span>
                            </td>
                            <td class="p-3 text-right font-mono font-semibold text-slate-900 dark:text-white whitespace-nowrap">$ {{ formatearMoneda(reg.importe) }}</td>
                            <td class="p-3 text-right whitespace-nowrap">
                                <Button icon="pi pi-copy" text rounded size="small" severity="secondary" title="Copiar paciente y práctica para otra fecha" @click="precargarDesdeFila(reg)" />
                                <Button icon="pi pi-pencil" text rounded size="small" severity="info" title="Editar fila" @click="abrirEditarRegistro(reg)" />
                                <Button icon="pi pi-trash" text rounded size="small" severity="danger" title="Eliminar fila" @click="borrarRegistro(reg)" />
                            </td>
                        </tr>
                    </tbody>
                    <tfoot v-if="registros.length > 0">
                        <tr class="bg-slate-50 dark:bg-slate-800/80 font-bold">
                            <td :colspan="financiadorActivo === 'medicus' ? 7 : financiadorActivo === 'corporacion' ? 7 : 6" class="p-3 text-right uppercase text-xs text-slate-500">Total ({{ resumen.total_registros }} prestaciones):</td>
                            <td class="p-3 text-right font-mono text-base text-teal-700 dark:text-teal-400 whitespace-nowrap">$ {{ formatearMoneda(resumen.total_importe) }}</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        <!-- MODAL: Editar Registro Individual -->
        <Dialog v-model:visible="modalEditarRegistro" modal header="Editar Entrada de Facturación" :style="{ width: '38rem' }">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div>
                    <label class="block text-xs font-semibold mb-1">Fecha de Realización</label>
                    <input v-model="editRegistroForm.fecha_realizacion" type="date" class="p-inputtext p-component w-full h-10 text-sm" />
                </div>
                <div>
                    <label class="block text-xs font-semibold mb-1">N° de Afiliado</label>
                    <InputText v-model="editRegistroForm.nro_afiliado" class="w-full font-mono" />
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-xs font-semibold mb-1">Paciente (Apellido y Nombre)</label>
                    <InputText v-model="editRegistroForm.paciente_nombre" class="w-full uppercase" />
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-xs font-semibold mb-1">Cambiar Práctica del Catálogo</label>
                    <select v-model="editRegistroForm.practica_id" @change="onChangePracticaEdit" class="p-inputtext p-component w-full h-10 text-sm">
                        <option value="">— Mantener actual —</option>
                        <option v-for="pr in practicasFinanciador" :key="pr.id" :value="pr.id">{{ pr.codigo }} — {{ pr.descripcion }} ($ {{ formatearMoneda(pr.importe) }})</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-semibold mb-1">Código / Práctica a Exportar</label>
                    <InputText v-model="editRegistroForm.practica_codigo" class="w-full font-mono" />
                </div>
                <div>
                    <label class="block text-xs font-semibold mb-1">Importe / Honorarios ($)</label>
                    <InputText v-model="editRegistroForm.importe" type="number" step="0.01" class="w-full font-mono" />
                </div>
                <div>
                    <label class="block text-xs font-semibold mb-1">N° Autorización / ID Conectividad</label>
                    <InputText v-model="editRegistroForm.autorizacion" class="w-full font-mono" />
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block text-xs font-semibold mb-1">Cant./Sesiones</label>
                        <input v-model.number="editRegistroForm.cantidad" type="number" min="1" class="p-inputtext p-component w-full h-10 text-sm font-mono" />
                    </div>
                    <div>
                        <label class="block text-xs font-semibold mb-1">CUD</label>
                        <select v-model="editRegistroForm.cud" class="p-inputtext p-component w-full h-10 text-sm">
                            <option value="NO">NO</option>
                            <option value="SI">SI</option>
                        </select>
                    </div>
                </div>
                <template v-if="financiadorActivo === 'medicus'">
                    <div>
                        <label class="block text-xs font-semibold mb-1">Lugar Efector</label>
                        <InputText v-model="editRegistroForm.lugar_realizacion_efector" class="w-full font-mono" />
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <label class="block text-xs font-semibold mb-1">Tipo Mat.</label>
                            <InputText v-model="editRegistroForm.tipo_matricula" class="w-full font-mono" />
                        </div>
                        <div>
                            <label class="block text-xs font-semibold mb-1">N° Matrícula</label>
                            <InputText v-model="editRegistroForm.nro_matricula" class="w-full font-mono" />
                        </div>
                    </div>
                </template>
            </div>
            <template #footer>
                <Button label="Cancelar" text severity="secondary" @click="modalEditarRegistro = false" />
                <Button label="Guardar Cambios" icon="pi pi-check" @click="guardarEdicionRegistro" />
            </template>
        </Dialog>

        <!-- MODAL: Catálogo de Prácticas y Aranceles -->
        <Dialog v-model:visible="modalCatalogoPracticas" modal :header="`Catálogo de Prácticas — ${infoFinanciador.nombre}`" :style="{ width: '60rem' }">
            <div class="space-y-4">
                <!-- Formulario para Añadir o Editar Práctica -->
                <div class="bg-slate-50 dark:bg-slate-800/60 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div class="text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-3">
                        {{ nuevaPractica.id ? 'Editar Práctica Seleccionada' : `Añadir Nueva Práctica a ${infoFinanciador.nombre}` }}
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                        <div class="sm:col-span-3">
                            <label class="block text-xs font-semibold mb-1">Categoría</label>
                            <InputText v-model="nuevaPractica.categoria" placeholder="Ej: Consulta, Rehabilitación" class="w-full text-sm" />
                        </div>
                        <div class="sm:col-span-3">
                            <label class="block text-xs font-semibold mb-1">
                                {{ financiadorActivo === 'medicus' ? 'Código Medicus' : 'Nombre a Exportar' }}
                            </label>
                            <InputText v-model="nuevaPractica.codigo" placeholder="Ej: 2420101 o FKT" class="w-full text-sm font-mono" />
                        </div>
                        <div class="sm:col-span-4">
                            <label class="block text-xs font-semibold mb-1">Descripción en Pantalla</label>
                            <InputText v-model="nuevaPractica.descripcion" placeholder="Descripción clara para elegir" class="w-full text-sm" />
                        </div>
                        <div class="sm:col-span-2">
                            <label class="block text-xs font-semibold mb-1">Importe ($)</label>
                            <InputText v-model="nuevaPractica.importe" type="number" step="0.01" placeholder="0.00" class="w-full text-sm font-mono" />
                        </div>
                    </div>
                    <div class="flex justify-end gap-2 mt-3">
                        <Button v-if="nuevaPractica.id" label="Cancelar edición" text size="small" severity="secondary" @click="resetNuevaPractica" />
                        <Button :label="nuevaPractica.id ? 'Actualizar Práctica' : 'Añadir al Catálogo'" icon="pi pi-plus" size="small" @click="guardarPracticaCatalogo" />
                    </div>
                </div>

                <!-- Barra de Búsqueda y Aumento Porcentual Masivo -->
                <div class="flex flex-wrap items-center justify-between gap-3">
                    <InputText v-model="filtroCatalogoTexto" placeholder="Buscar por código o descripción..." class="w-64 text-sm" />
                    <div class="flex items-center gap-2 bg-teal-50 dark:bg-teal-950/40 px-3 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800">
                        <span class="text-xs font-semibold text-teal-900 dark:text-teal-200">Aumento masivo (%):</span>
                        <InputText v-model="porcentajeAumento" type="number" step="0.1" placeholder="Ej: 3.8" class="w-24 h-8 text-sm font-mono" />
                        <Button label="Aplicar %" size="small" severity="success" @click="aplicarAumentoPorcentual" />
                    </div>
                </div>

                <!-- Tabla del Catálogo -->
                <div class="max-h-96 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg">
                    <table class="w-full text-left border-collapse text-sm">
                        <thead class="bg-slate-100 dark:bg-slate-800 text-xs uppercase sticky top-0">
                            <tr>
                                <th class="p-2.5">Categoría</th>
                                <th class="p-2.5">Código Exportación</th>
                                <th class="p-2.5">Descripción</th>
                                <th class="p-2.5 text-right">Valor Vigente</th>
                                <th class="p-2.5 text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
                            <tr v-for="p in practicasCatalogoModal" :key="p.id" class="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                                <td class="p-2.5 text-xs text-slate-500">{{ p.categoria }}</td>
                                <td class="p-2.5 font-mono font-bold text-xs">{{ p.codigo }}</td>
                                <td class="p-2.5 text-xs">{{ p.descripcion }}</td>
                                <td class="p-2.5 text-right font-mono font-semibold">$ {{ formatearMoneda(p.importe) }}</td>
                                <td class="p-2.5 text-right whitespace-nowrap">
                                    <Button icon="pi pi-pencil" text rounded size="small" severity="info" @click="editarPracticaEnModal(p)" />
                                    <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="eliminarPracticaCatalogo(p)" />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </Dialog>

        <!-- MODAL: Catálogo de Prestadores / Efectores -->
        <Dialog v-model:visible="modalPrestadores" modal header="Listado de Prestadores / Efectores (Medicus)" :style="{ width: '50rem' }">
            <div class="space-y-4">
                <div class="bg-slate-50 dark:bg-slate-800/60 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div class="text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-3">
                        {{ nuevoPrestador.id ? 'Editar Prestador' : 'Añadir Nuevo Prestador / Efector' }}
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                        <div class="sm:col-span-5">
                            <label class="block text-xs font-semibold mb-1">Nombre Identificatorio</label>
                            <InputText v-model="nuevoPrestador.nombre" placeholder="Ej: CAU OSUNSAM" class="w-full text-sm" />
                        </div>
                        <div class="sm:col-span-1">
                            <label class="block text-xs font-semibold mb-1">Ctx.</label>
                            <InputText v-model="nuevoPrestador.contexto" class="w-full text-sm font-mono" />
                        </div>
                        <div class="sm:col-span-2">
                            <label class="block text-xs font-semibold mb-1">Lugar Efector</label>
                            <InputText v-model="nuevoPrestador.lugar_realizacion_efector" placeholder="E171513" class="w-full text-sm font-mono" />
                        </div>
                        <div class="sm:col-span-1">
                            <label class="block text-xs font-semibold mb-1">Tipo</label>
                            <InputText v-model="nuevoPrestador.tipo_matricula" placeholder="P" class="w-full text-sm font-mono" />
                        </div>
                        <div class="sm:col-span-3">
                            <label class="block text-xs font-semibold mb-1">N° Matrícula</label>
                            <InputText v-model="nuevoPrestador.nro_matricula" placeholder="441983" class="w-full text-sm font-mono" />
                        </div>
                    </div>
                    <div class="flex items-center justify-between mt-3">
                        <label class="inline-flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                            <input type="checkbox" v-model="nuevoPrestador.es_predeterminado" />
                            Usar como prestador predeterminado al abrir Facturación
                        </label>
                        <div class="flex gap-2">
                            <Button v-if="nuevoPrestador.id" label="Cancelar" text size="small" severity="secondary" @click="resetNuevoPrestador" />
                            <Button :label="nuevoPrestador.id ? 'Actualizar Prestador' : 'Añadir Prestador'" icon="pi pi-plus" size="small" @click="guardarPrestadorCatalogo" />
                        </div>
                    </div>
                </div>

                <div class="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                    <table class="w-full text-left border-collapse text-sm">
                        <thead class="bg-slate-100 dark:bg-slate-800 text-xs uppercase">
                            <tr>
                                <th class="p-2.5">Nombre</th>
                                <th class="p-2.5">Contexto</th>
                                <th class="p-2.5">Lugar Efector</th>
                                <th class="p-2.5">Matrícula</th>
                                <th class="p-2.5 text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
                            <tr v-for="pr in prestadores" :key="pr.id">
                                <td class="p-2.5 font-medium">
                                    {{ pr.nombre }}
                                    <span v-if="pr.es_predeterminado" class="ml-2 px-1.5 py-0.5 text-[10px] bg-teal-100 text-teal-800 rounded font-bold">Predeterminado</span>
                                </td>
                                <td class="p-2.5 font-mono text-xs">{{ pr.contexto }}</td>
                                <td class="p-2.5 font-mono text-xs font-bold">{{ pr.lugar_realizacion_efector }}</td>
                                <td class="p-2.5 font-mono text-xs">{{ pr.tipo_matricula }} — {{ pr.nro_matricula }}</td>
                                <td class="p-2.5 text-right">
                                    <Button icon="pi pi-pencil" text rounded size="small" severity="info" @click="editarPrestadorEnModal(pr)" />
                                    <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="eliminarPrestadorCatalogo(pr)" />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </Dialog>
    </div>
</template>
