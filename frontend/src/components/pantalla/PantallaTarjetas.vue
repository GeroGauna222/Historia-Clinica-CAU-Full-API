<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { ordenarTarjetas, paginar } from '@/utils/pantallaTarjetas';
import '@/assets/pantalla.css';

const props = defineProps({
    tarjetas: { type: Array, default: () => [] },
    porPagina: { type: Number, default: 12 },
    // Se lee una sola vez al montar: cambiarla después no reinicia la rotación.
    rotacionMs: { type: Number, default: 10000 }
});

const pagina = ref(0);
const paginas = computed(() => paginar(ordenarTarjetas(props.tarjetas), props.porPagina));
const visibles = computed(() => paginas.value[pagina.value] || []);
const columnas = computed(() => {
    const n = visibles.value.length;
    if (n <= 1) return 1;
    if (n <= 4) return 2;
    if (n <= 9) return 3;
    return 4;
});
// Con 10 o más tarjetas por página la letra se achica; con 4 o menos se agranda (ver .densa y .grande).
const clasesEscala = computed(() => ({ densa: visibles.value.length >= 10, grande: visibles.value.length <= 4 }));

// El temporizador se crea una sola vez al montar: que llegue un arreglo `tarjetas` nuevo (cada consulta)
// no lo reinicia ni cambia la página actual.
let timer = null;
onMounted(() => {
    timer = setInterval(() => {
        if (paginas.value.length > 1) pagina.value = (pagina.value + 1) % paginas.value.length;
    }, props.rotacionMs);
});
onBeforeUnmount(() => clearInterval(timer));
watch(
    () => paginas.value.length,
    (n) => {
        if (pagina.value >= n) pagina.value = 0;
    }
);
</script>

<template>
    <div class="tarjetas" :class="clasesEscala">
        <p v-if="!tarjetas.length" class="vacio">No hay turnos para mostrar por ahora</p>
        <div v-else class="grilla" :style="{ gridTemplateColumns: `repeat(${columnas}, minmax(0, 1fr))` }">
            <article v-for="t in visibles" :key="`${t.tipo}-${t.id}`" class="tarjeta">
                <div class="cabecera">
                    <span v-if="t.consultorio" class="consultorio">{{ t.consultorio }}</span>
                    <span class="profesional">{{ t.nombre }}</span>
                </div>
                <section class="bloque">
                    <p class="rotulo">En atención</p>
                    <p v-if="!(t.en_atencion || []).length" class="nadie">—</p>
                    <p v-for="(p, i) in t.en_atencion || []" :key="i" class="en-atencion">{{ p.nombre }}</p>
                </section>
                <section class="bloque">
                    <p class="rotulo">Siguientes</p>
                    <p v-if="!(t.siguientes || []).length" class="nadie">—</p>
                    <p v-for="(p, i) in t.siguientes || []" :key="i" class="siguiente">{{ p.nombre }}</p>
                </section>
            </article>
        </div>
        <p v-if="paginas.length > 1" class="paginas">Página {{ pagina + 1 }} de {{ paginas.length }}</p>
    </div>
</template>

<style scoped>
/*
 * Colores: variables --pantalla-* de assets/pantalla.css; el contenedor debe tener la clase .pantalla-paleta
 * (el televisor la aplica en su raíz y la vista previa de administración, en su contenedor).
 *
 * Tamaños: todo está en `em` a partir de una escala base. Por omisión depende del ancho Y del alto del viewport
 * (min(1vw, 1.7vh)); un contenedor que no ocupe la pantalla (vista previa) puede fijarla con
 * `--pantalla-escala: 8px` (cualquier longitud) y no depender del viewport.
 */
.tarjetas {
    --escala-base: var(--pantalla-escala, min(1vw, 1.7vh));
    --factor: 1;
    font-size: calc(var(--escala-base) * var(--factor));
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.5em;
}
.tarjetas.grande {
    --factor: 1.4;
}
.tarjetas.densa {
    --factor: 0.85;
}
.grilla {
    flex: 1;
    display: grid;
    grid-auto-rows: 1fr;
    gap: 1em;
    min-height: 0;
}
.densa .grilla {
    gap: 0.75em;
}
.tarjeta {
    background: var(--pantalla-tarjeta);
    border: 2px solid var(--pantalla-borde);
    border-radius: 1em;
    padding: 0.7em 0.9em;
    display: flex;
    flex-direction: column;
    gap: 0.3em;
    overflow: hidden;
    min-width: 0;
}
.densa .tarjeta {
    padding: 0.5em 0.7em;
    gap: 0.2em;
}
.cabecera {
    display: flex;
    align-items: baseline;
    gap: 0.5em;
    flex-wrap: wrap;
}
.consultorio {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 3em;
    font-weight: 800;
    line-height: 1;
    color: var(--pantalla-acento);
}
.profesional {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 1.3em;
    color: var(--pantalla-texto-suave);
}
.rotulo {
    font-size: 0.9em;
    line-height: 1.2;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--pantalla-texto-suave);
    margin: 0;
}
.en-atencion {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 2.2em;
    line-height: 1.1;
    font-weight: 800;
    color: var(--pantalla-ok);
    margin: 0;
}
.siguiente {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 1.4em;
    line-height: 1.2;
    color: var(--pantalla-texto);
    margin: 0;
}
.nadie {
    font-size: 1.4em;
    line-height: 1.2;
    color: var(--pantalla-texto-suave);
    margin: 0;
}
.vacio {
    margin: auto;
    font-size: 3em;
    color: var(--pantalla-texto-suave);
}
.paginas {
    text-align: right;
    font-size: 1em;
    line-height: 1.2;
    margin: 0;
    color: var(--pantalla-texto-suave);
}
</style>
