import { ref } from 'vue';
import pantallaService from '@/service/pantallaService';
import { detectarLlamadosNuevos } from '@/utils/pantallaTarjetas';
import { reproducirAvisoSonoro } from '@/utils/avisoSonoro';

export const CLAVE_STORAGE = 'cau-pantalla-clave';
export const INTERVALO_MS = 5000;
export const SIN_RESPUESTA_MS = 30000;
export const TIMEOUT_PEDIDO_MS = 15000;

function leerClave() {
    try {
        return window.localStorage.getItem(CLAVE_STORAGE);
    } catch {
        return null;
    }
}
function guardarClave(clave) {
    try {
        window.localStorage.setItem(CLAVE_STORAGE, clave);
    } catch {
        // sin localStorage: la clave queda solo en memoria hasta recargar
    }
}
function borrarClave() {
    try {
        window.localStorage.removeItem(CLAVE_STORAGE);
    } catch {
        // nada que borrar
    }
}

// axios no tiene timeout configurado: sin esto, un pedido colgado dejaría `enCurso`
// en true para siempre y el televisor dejaría de actualizarse sin avisar.
function conLimite(promesa, ms = TIMEOUT_PEDIDO_MS) {
    let temporizador;
    const limite = new Promise((_, reject) => {
        temporizador = setTimeout(() => reject(new Error('sin respuesta')), ms);
    });
    return Promise.race([promesa, limite]).finally(() => clearTimeout(temporizador));
}

export function usePantallaTV() {
    const estado = ref('iniciando'); // iniciando | pendiente | vinculada | limite
    const codigo = ref('');
    const tarjetas = ref([]);
    const reconectando = ref(false);
    const sonidoActivo = ref(false);

    let claveMemoria = null;
    let vistos = null;
    let ultimaRespuesta = Date.now();
    let timer = null;
    let enCurso = false;
    // Arranca en true para poder llamar a `ciclo()` sin `iniciar()`; `detener()` lo apaga y un ciclo en vuelo
    // que resuelve después ya no toca estado, clave ni sonido.
    let activo = true;

    function reiniciarEstado() {
        estado.value = 'iniciando';
        codigo.value = '';
        tarjetas.value = [];
        vistos = null;
    }

    // Nunca se loguea el error: el de axios incluye `config.headers` con la clave del televisor.
    async function ciclo() {
        if (enCurso) return;
        enCurso = true;
        let pidiendoVinculacion = false;
        try {
            let clave = leerClave() || claveMemoria;
            if (!clave) {
                pidiendoVinculacion = true;
                const { data } = await conLimite(pantallaService.solicitarVinculacion());
                if (!activo) return;
                if (typeof data?.clave !== 'string' || !data.clave) throw new Error('respuesta inesperada');
                clave = data.clave;
                claveMemoria = clave;
                guardarClave(clave);
                pidiendoVinculacion = false;
            }
            const { data } = await conLimite(pantallaService.obtenerLlamados(clave));
            if (!activo) return;
            // Una respuesta con forma inesperada cuenta como "sin respuesta": no toca las tarjetas y
            // alimenta el aviso de reconexión a los 30 s (el error no trae `response`, así que no es 401/429).
            const ok = (data?.estado === 'pendiente' && typeof data.codigo === 'string') || (data?.estado === 'vinculada' && Array.isArray(data.tarjetas));
            if (!ok) throw new Error('respuesta inesperada');
            ultimaRespuesta = Date.now();
            reconectando.value = false;

            if (data.estado === 'pendiente') {
                estado.value = 'pendiente';
                codigo.value = data.codigo;
                tarjetas.value = [];
                vistos = null;
                return;
            }
            estado.value = 'vinculada';
            codigo.value = '';
            tarjetas.value = data.tarjetas;
            const r = detectarLlamadosNuevos(vistos, tarjetas.value);
            vistos = r.vistos;
            if (r.nuevos && sonidoActivo.value) reproducirAvisoSonoro();
        } catch (e) {
            if (!activo) return;
            const status = e?.response?.status;
            if (status === 401) {
                // El servidor respondió: no es un corte de red.
                ultimaRespuesta = Date.now();
                reconectando.value = false;
                borrarClave();
                claveMemoria = null;
                reiniciarEstado(); // el próximo ciclo pide un código nuevo
            } else if (status === 429 && pidiendoVinculacion) {
                // Solo el límite de vinculaciones muestra el aviso; un 429 al consultar es un fallo transitorio.
                ultimaRespuesta = Date.now();
                reconectando.value = false;
                estado.value = 'limite';
            } else if (Date.now() - ultimaRespuesta > SIN_RESPUESTA_MS) {
                reconectando.value = true;
            }
        } finally {
            enCurso = false;
        }
    }

    function activarSonido() {
        sonidoActivo.value = true;
        reproducirAvisoSonoro(); // tono de prueba: confirma que se escucha
    }

    function iniciar() {
        if (timer) return; // ya iniciado: evita un setInterval huérfano
        activo = true;
        ultimaRespuesta = Date.now();
        reconectando.value = false;
        ciclo();
        timer = setInterval(ciclo, INTERVALO_MS);
    }

    function detener() {
        activo = false;
        if (timer) clearInterval(timer);
        timer = null;
    }

    return { estado, codigo, tarjetas, reconectando, sonidoActivo, ciclo, activarSonido, iniciar, detener };
}
