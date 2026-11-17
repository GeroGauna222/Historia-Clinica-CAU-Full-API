<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { ordenarTarjetas, paginar } from '@/utils/pantallaTarjetas';

const props = defineProps({
    tarjetas: { type: Array, default: () => [] },
    porPagina: { type: Number, default: 12 },
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
    <div class="tarjetas">
        <p v-if="!tarjetas.length" class="vacio">No hay turnos para mostrar por ahora</p>
        <div v-else class="grilla" :style="{ gridTemplateColumns: `repeat(${columnas}, 1fr)` }">
            <article v-for="t in visibles" :key="`${t.tipo}-${t.id}`" class="tarjeta">
                <header>
                    <span v-if="t.consultorio" class="consultorio">{{ t.consultorio }}</span>
                    <span class="profesional">{{ t.nombre }}</span>
                </header>
                <section class="bloque">
                    <h3>En atención</h3>
                    <p v-if="!(t.en_atencion || []).length" class="nadie">—</p>
                    <p v-for="p in t.en_atencion || []" :key="p.atencion_inicio + p.nombre" class="en-atencion">{{ p.nombre }}</p>
                </section>
                <section class="bloque">
                    <h3>Siguientes</h3>
                    <p v-if="!(t.siguientes || []).length" class="nadie">—</p>
                    <p v-for="(p, i) in t.siguientes || []" :key="i" class="siguiente">{{ p.nombre }}</p>
                </section>
            </article>
        </div>
        <p v-if="paginas.length > 1" class="paginas">Página {{ pagina + 1 }} de {{ paginas.length }}</p>
    </div>
</template>

<style scoped>
/* Los colores vienen de las variables --pantalla-* que define PantallaTV.vue; los valores de respaldo
   (rgb, no hexadecimal) solo se usan si el componente se monta fuera del televisor (vista previa). */
.tarjetas {
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.grilla {
    flex: 1;
    display: grid;
    grid-auto-rows: 1fr;
    gap: 1rem;
    min-height: 0;
}
.tarjeta {
    background: var(--pantalla-tarjeta, rgb(17 28 51));
    border: 2px solid var(--pantalla-borde, rgb(36 54 94));
    border-radius: 1rem;
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    overflow: hidden;
}
header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    flex-wrap: wrap;
}
.consultorio {
    font-size: clamp(2.5rem, 5vw, 5rem);
    font-weight: 800;
    line-height: 1;
    color: var(--pantalla-acento, rgb(251 191 36));
}
.profesional {
    font-size: clamp(1.1rem, 2vw, 2rem);
    color: var(--pantalla-texto-suave, rgb(159 176 208));
}
h3 {
    font-size: clamp(0.9rem, 1.4vw, 1.4rem);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--pantalla-texto-suave, rgb(159 176 208));
    margin: 0;
}
.en-atencion {
    font-size: clamp(1.8rem, 3.6vw, 3.6rem);
    font-weight: 800;
    color: var(--pantalla-ok, rgb(74 222 128));
    margin: 0;
}
.siguiente {
    font-size: clamp(1.2rem, 2.2vw, 2.2rem);
    color: var(--pantalla-texto, rgb(229 231 235));
    margin: 0;
}
.nadie {
    font-size: 1.5rem;
    color: var(--pantalla-texto-suave, rgb(159 176 208));
    margin: 0;
}
.vacio {
    margin: auto;
    font-size: 2rem;
    color: var(--pantalla-texto-suave, rgb(159 176 208));
}
.paginas {
    text-align: right;
    margin: 0;
    color: var(--pantalla-texto-suave, rgb(159 176 208));
}
</style>
