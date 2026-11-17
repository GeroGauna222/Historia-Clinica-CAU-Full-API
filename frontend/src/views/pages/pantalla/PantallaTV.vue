<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import PantallaTarjetas from '@/components/pantalla/PantallaTarjetas.vue';
import { usePantallaTV } from '@/composables/usePantallaTV';

const { estado, codigo, tarjetas, reconectando, sonidoActivo, activarSonido, iniciar, detener } = usePantallaTV();

const hora = ref('');
let relojTimer = null;
function actualizarHora() {
    hora.value = new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}

onMounted(() => {
    actualizarHora();
    relojTimer = setInterval(actualizarHora, 10000);
    iniciar();
});
onBeforeUnmount(() => {
    clearInterval(relojTimer);
    detener();
});
</script>

<template>
    <main class="pantalla-tv">
        <header class="barra">
            <span class="titulo">Turnos</span>
            <span class="reloj">{{ hora }}</span>
            <button v-if="estado === 'vinculada' && !sonidoActivo" class="sonido" autofocus @click="activarSonido">Activar sonido</button>
        </header>

        <section v-if="estado === 'vinculada' && !reconectando" class="contenido">
            <PantallaTarjetas :tarjetas="tarjetas" />
        </section>
        <section v-else-if="estado === 'vinculada'" class="centro">
            <p class="mensaje">Reconectando…</p>
        </section>
        <section v-else-if="estado === 'pendiente'" class="centro">
            <p class="indicacion">Pedile al director que cargue este código en el sistema</p>
            <p class="codigo">{{ codigo }}</p>
        </section>
        <section v-else-if="estado === 'limite'" class="centro">
            <p class="mensaje">Probá en unos minutos</p>
        </section>
        <section v-else class="centro">
            <p class="mensaje">Iniciando…</p>
        </section>
    </main>
</template>

<style scoped>
/* Paleta propia del televisor: siempre oscura, independiente del tema de la app. Único lugar donde se definen
   las variables --pantalla-* (en rgb para no usar colores hexadecimales, que check:tokens rechaza). */
.pantalla-tv {
    --pantalla-fondo: rgb(11 18 32);
    --pantalla-tarjeta: rgb(17 28 51);
    --pantalla-borde: rgb(36 54 94);
    --pantalla-acento: rgb(251 191 36);
    --pantalla-ok: rgb(74 222 128);
    --pantalla-texto: rgb(229 231 235);
    --pantalla-texto-suave: rgb(159 176 208);
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    background: var(--pantalla-fondo);
    color: var(--pantalla-texto);
    font-family: system-ui, sans-serif;
    padding: 1.25rem 1.75rem;
    gap: 1rem;
    overflow: hidden;
}
.barra {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}
.titulo {
    font-size: 2rem;
    font-weight: 700;
}
.reloj {
    margin-left: auto;
    font-size: 2.5rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.sonido {
    font-size: 1.5rem;
    padding: 0.6rem 1.4rem;
    border-radius: 0.6rem;
    border: 2px solid var(--pantalla-acento);
    background: transparent;
    color: var(--pantalla-acento);
}
.contenido {
    flex: 1;
    min-height: 0;
}
.centro {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2rem;
    text-align: center;
}
.indicacion,
.mensaje {
    font-size: clamp(1.5rem, 3vw, 3rem);
    color: var(--pantalla-texto-suave);
    margin: 0;
}
.codigo {
    font-size: clamp(5rem, 14vw, 14rem);
    font-weight: 800;
    letter-spacing: 0.15em;
    color: var(--pantalla-acento);
    margin: 0;
}
</style>
