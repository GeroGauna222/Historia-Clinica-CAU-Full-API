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
        try {
            let clave = leerClave() || claveMemoria;
            if (!clave) {
                const { data } = await conLimite(pantallaService.solicitarVinculacion());
                clave = data.clave;
                claveMemoria = clave;
                guardarClave(clave);
            }
            const { data } = await conLimite(pantallaService.obtenerLlamados(clave));
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
            tarjetas.value = data.tarjetas || [];
            const r = detectarLlamadosNuevos(vistos, tarjetas.value);
            vistos = r.vistos;
            if (r.nuevos && sonidoActivo.value) reproducirAvisoSonoro();
        } catch (e) {
            const status = e?.response?.status;
            if (status === 401) {
                borrarClave();
                claveMemoria = null;
                reiniciarEstado(); // el próximo ciclo pide un código nuevo
            } else if (status === 429) {
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
        ultimaRespuesta = Date.now();
        ciclo();
        timer = setInterval(ciclo, INTERVALO_MS);
    }

    function detener() {
        if (timer) clearInterval(timer);
        timer = null;
    }

    return { estado, codigo, tarjetas, reconectando, sonidoActivo, ciclo, activarSonido, iniciar, detener };
}
