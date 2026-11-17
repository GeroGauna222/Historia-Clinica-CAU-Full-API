<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import Tabs from 'primevue/tabs';
import TabList from 'primevue/tablist';
import Tab from 'primevue/tab';
import TabPanels from 'primevue/tabpanels';
import TabPanel from 'primevue/tabpanel';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import InputText from 'primevue/inputtext';
import ToggleSwitch from 'primevue/toggleswitch';
import Button from 'primevue/button';
import Message from 'primevue/message';
import PantallaTarjetas from '@/components/pantalla/PantallaTarjetas.vue';
import pantallaService from '@/service/pantallaService';
import { useUserStore } from '@/stores/user';

const REFRESCO_PREVIA_MS = 5000;

const userStore = useUserStore();
const esDirector = computed(() => (userStore.rol || '').toLowerCase().trim() === 'director');

const tarjetas = ref([]);
const visibles = ref([]);
const televisores = ref([]);
const codigo = ref('');
const nombreTv = ref('');
const vinculando = ref(false);

// Error de una acción del usuario (guardar, vincular, desvincular) y errores de carga/refresco, por separado:
// un refresco silencioso (cada 5 s) nunca limpia ni reemplaza el mensaje de una acción.
const errorAccion = ref('');
const erroresCarga = reactive({ previa: '', visibles: '', televisores: '' });
const errorVisible = computed(() => errorAccion.value || erroresCarga.previa || erroresCarga.visibles || erroresCarga.televisores);

// El 400 de "cuerpo inválido" del PATCH usa la clave `message`; el resto de las respuestas usa `error`.
function mensajeDe(e, defecto) {
    return e?.response?.data?.error || e?.response?.data?.message || defecto;
}

let cargandoPrevia = false;
async function cargarPrevia() {
    if (cargandoPrevia) return; // el pedido anterior sigue en curso: se saltea el tick
    cargandoPrevia = true;
    try {
        const { data } = await pantallaService.vistaPrevia();
        tarjetas.value = data.tarjetas || [];
        erroresCarga.previa = '';
    } catch (e) {
        erroresCarga.previa = mensajeDe(e, 'No se pudo cargar la vista previa');
    } finally {
        cargandoPrevia = false;
    }
}

// Cuántas ediciones están en vuelo: mientras haya alguna, una lista que llega tarde no pisa lo que el usuario acaba de cambiar.
let guardando = 0;
async function cargarVisibles() {
    try {
        const { data } = await pantallaService.listarVisibles();
        if (guardando > 0) return;
        // `clave` identifica la fila en la tabla: tipo e id solos no son únicos entre grupos y profesionales.
        visibles.value = data.map((v) => ({ ...v, clave: `${v.tipo}-${v.id}` }));
        erroresCarga.visibles = '';
    } catch (e) {
        erroresCarga.visibles = mensajeDe(e, 'No se pudo cargar la lista');
    }
}

async function cargarTelevisores() {
    if (!esDirector.value) return;
    try {
        televisores.value = (await pantallaService.listarTelevisores()).data;
        erroresCarga.televisores = '';
    } catch (e) {
        erroresCarga.televisores = mensajeDe(e, 'No se pudo cargar la lista de televisores');
    }
}

// Los campos de PrimeVue guardan su propio valor al editarlo: si el guardado falla (o el servidor normaliza el texto)
// el modelo no cambia y el campo seguiría mostrando lo escrito. Cambiar la clave de la fila los vuelve a crear con el valor real.
const versiones = reactive({});
function claveCampo(fila) {
    return `${fila.clave}-${versiones[fila.clave] || 0}`;
}
function reiniciarCampos(fila) {
    versiones[fila.clave] = (versiones[fila.clave] || 0) + 1;
}

async function guardar(fila, cambios) {
    errorAccion.value = '';
    guardando++;
    let fallo = false;
    try {
        const { data } = await pantallaService.actualizarVisible(fila.tipo, fila.id, cambios);
        // la lista pudo haberse recargado mientras tanto: se actualiza la fila vigente, no la que se editó
        const actual = visibles.value.find((v) => v.clave === fila.clave) || fila;
        actual.consultorio = data.consultorio;
        actual.mostrar_en_pantalla = data.mostrar_en_pantalla;
        if ('consultorio' in cambios && cambios.consultorio !== data.consultorio) reiniciarCampos(actual);
        cargarPrevia();
    } catch (e) {
        fallo = true;
        errorAccion.value = mensajeDe(e, 'No se pudo guardar');
        reiniciarCampos(fila);
    } finally {
        guardando--;
    }
    if (fallo) await cargarVisibles(); // vuelve al valor real
}

function alCambiarConsultorio(fila, evento) {
    guardar(fila, { consultorio: evento.target.value });
}

const ocultosConTurnos = computed(() => visibles.value.filter((v) => !v.mostrar_en_pantalla && v.tiene_turnos_hoy));
const nombresOcultos = computed(() => ocultosConTurnos.value.map((v) => v.nombre).join(', '));

async function vincular() {
    if (vinculando.value || !codigo.value || !nombreTv.value) return;
    errorAccion.value = '';
    vinculando.value = true;
    try {
        await pantallaService.vincularTelevisor({ codigo: codigo.value.trim(), nombre: nombreTv.value.trim() });
        codigo.value = '';
        nombreTv.value = '';
        await cargarTelevisores();
    } catch (e) {
        errorAccion.value = mensajeDe(e, 'No se pudo vincular el televisor');
    } finally {
        vinculando.value = false;
    }
}

async function desvincular(tv) {
    if (!window.confirm(`¿Desvincular "${tv.nombre}"? El televisor dejará de mostrar la pantalla.`)) return;
    errorAccion.value = '';
    try {
        await pantallaService.desvincularTelevisor(tv.id);
        await cargarTelevisores();
    } catch (e) {
        errorAccion.value = mensajeDe(e, 'No se pudo desvincular el televisor');
    }
}

function formatearFecha(iso) {
    return iso ? new Date(iso).toLocaleString('es-AR') : '—';
}

let timerPrevia = null;
onMounted(() => {
    cargarPrevia();
    cargarVisibles();
    cargarTelevisores();
    timerPrevia = setInterval(cargarPrevia, REFRESCO_PREVIA_MS);
});
onBeforeUnmount(() => clearInterval(timerPrevia));
</script>

<template>
    <div class="p-6 md:p-8 w-full h-full">
        <div class="bg-card shadow-xl rounded-2xl p-6 transition-colors">
            <h1 class="text-3xl font-bold text-color mb-6">Pantalla de llamados</h1>

            <Message v-if="errorVisible" severity="error" :closable="false" class="mb-4">{{ errorVisible }}</Message>

            <Tabs value="previa">
                <TabList>
                    <Tab value="previa">Vista previa</Tab>
                    <Tab value="visibles">Visibles</Tab>
                    <Tab v-if="esDirector" value="televisores">Televisores</Tab>
                </TabList>
                <TabPanels>
                    <TabPanel value="previa">
                        <!-- Así se ve en el televisor, a escala: el marco mide el ancho y la letra se fija como fracción de ese ancho -->
                        <div class="previa-marco">
                            <div class="previa pantalla-paleta">
                                <PantallaTarjetas :tarjetas="tarjetas" :porPagina="12" />
                            </div>
                        </div>
                    </TabPanel>

                    <TabPanel value="visibles">
                        <Message v-if="ocultosConTurnos.length" severity="warn" :closable="false" class="mb-4">Tienen turnos hoy y no se ven en la pantalla: {{ nombresOcultos }}</Message>
                        <div class="overflow-x-auto">
                            <DataTable :value="visibles" dataKey="clave" stripedRows class="p-datatable-sm" tableStyle="min-width: 40rem">
                                <template #empty>
                                    <div class="text-center p-6 text-muted-color">No hay profesionales ni grupos para configurar.</div>
                                </template>
                                <Column field="nombre" header="Nombre" />
                                <Column header="Tipo">
                                    <template #body="{ data }">{{ data.tipo === 'grupo' ? 'Grupo' : 'Profesional' }}</template>
                                </Column>
                                <Column header="Consultorio">
                                    <template #body="{ data }">
                                        <InputText :key="claveCampo(data)" :modelValue="data.consultorio" :aria-label="`Consultorio de ${data.nombre}`" maxlength="50" placeholder="Ej: 3 o Gimnasio" @change="alCambiarConsultorio(data, $event)" />
                                    </template>
                                </Column>
                                <Column header="Turnos hoy">
                                    <template #body="{ data }">{{ data.tiene_turnos_hoy ? 'Sí' : 'No' }}</template>
                                </Column>
                                <Column header="Visible">
                                    <template #body="{ data }">
                                        <ToggleSwitch :key="claveCampo(data)" :modelValue="data.mostrar_en_pantalla" :ariaLabel="`Mostrar ${data.nombre} en la pantalla`" @update:modelValue="(v) => guardar(data, { mostrar_en_pantalla: v })" />
                                    </template>
                                </Column>
                            </DataTable>
                        </div>
                    </TabPanel>

                    <TabPanel v-if="esDirector" value="televisores">
                        <form class="flex flex-col md:flex-row gap-4 md:items-end mb-6" @submit.prevent="vincular">
                            <div class="flex flex-col gap-2">
                                <label for="codigo-tv" class="font-semibold text-color">Código del televisor</label>
                                <InputText id="codigo-tv" v-model="codigo" maxlength="6" class="uppercase" autocomplete="off" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label for="nombre-tv" class="font-semibold text-color">Nombre</label>
                                <InputText id="nombre-tv" v-model="nombreTv" maxlength="100" placeholder="Sala de espera" autocomplete="off" />
                            </div>
                            <Button type="submit" label="Vincular" icon="pi pi-link" :disabled="!codigo || !nombreTv" :loading="vinculando" />
                        </form>

                        <div class="overflow-x-auto">
                            <DataTable :value="televisores" dataKey="id" stripedRows class="p-datatable-sm" tableStyle="min-width: 40rem">
                                <template #empty>
                                    <div class="text-center p-6 text-muted-color">Todavía no hay televisores vinculados.</div>
                                </template>
                                <Column field="nombre" header="Nombre" />
                                <Column header="Vinculado">
                                    <template #body="{ data }">{{ formatearFecha(data.vinculada_en) }}</template>
                                </Column>
                                <Column header="Último acceso">
                                    <template #body="{ data }">{{ formatearFecha(data.ultimo_acceso) }}</template>
                                </Column>
                                <Column header="">
                                    <template #body="{ data }">
                                        <Button label="Desvincular" severity="danger" text size="small" :aria-label="`Desvincular ${data.nombre}`" @click="desvincular(data)" />
                                    </template>
                                </Column>
                            </DataTable>
                        </div>
                    </TabPanel>
                </TabPanels>
            </Tabs>
        </div>
    </div>
</template>

<style scoped>
/*
 * La vista previa reproduce la pantalla del televisor (16:9) a escala reducida. PantallaTarjetas dimensiona la letra
 * con --pantalla-escala; por omisión sale del viewport (1vw / 1.7vh) y acá no sirve, así que se fija como fracción
 * del ancho del marco (container query: `cqw` se mide contra el ancestro con container-type, por eso el marco y la
 * vista previa son dos elementos distintos). 0,95cqw equivale a lo que da min(1vw, 1.7vh) en una pantalla 16:9.
 */
.previa-marco {
    container-type: inline-size;
    width: 100%;
    max-width: 64rem;
}
.previa {
    --pantalla-escala: 0.95cqw;
    aspect-ratio: 16 / 9;
    box-sizing: border-box;
    padding: 2cqw;
    overflow: hidden;
    border-radius: 0.75rem;
    background: var(--pantalla-fondo);
    color: var(--pantalla-texto);
    font-family: system-ui, sans-serif;
}
/* Navegadores sin container queries: tamaño fijo en vez de perder la escala. */
@supports not (width: 1cqw) {
    .previa {
        --pantalla-escala: 0.6rem;
        padding: 1rem;
    }
}
</style>
