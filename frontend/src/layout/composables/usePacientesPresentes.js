import { ref, computed } from 'vue';
import api from '@/api/axios';
import { reproducirAvisoSonoro } from '@/utils/avisoSonoro';
import { useUserStore } from '@/stores/user';
import turnosService from '@/service/turnosService';

const STORAGE_KEY = 'cau-arrival-acks';

const presentes = ref([]);
const pendientes = ref([]);
const cargando = ref(false);
const informados = new Set();
let usuarioEstadoId = null;
let timer = null;
let initialized = false;

// Un paciente ya llamado o atendido no es una llegada nueva. Lista de exclusión (no se exige
// 'esperando'): un estado ausente, null o desconocido se trata como esperando, igual que en el menú de presentes.
const ESTADOS_NO_ESPERANDO = ['en_atencion', 'atendido'];
const estaEsperando = (t) => !ESTADOS_NO_ESPERANDO.includes(t.estado_atencion);

function fechaLocalHoy() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function cargarInformadosGuardados(usuarioId) {
    informados.clear();
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const data = JSON.parse(raw);
        if (!data || data.userId !== usuarioId || data.date !== fechaLocalHoy()) return;
        for (const id of data.ids || []) {
            informados.add(id);
        }
    } catch {
        // Sin acceso a localStorage: seguimos solo con el estado en memoria
    }
}

function guardarInformados(usuarioId) {
    try {
        window.localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({
                userId: usuarioId,
                date: fechaLocalHoy(),
                ids: Array.from(informados)
            })
        );
    } catch {
        // Sin acceso a localStorage: la confirmación queda solo en memoria
    }
}

export function usePacientesPresentes() {
    const userStore = useUserStore();

    const cantidadPresentes = computed(() => presentes.value.length);

    async function cargarPresentes(silencioso = false) {
        const rol = (userStore.rol || '').toLowerCase().trim();
        if (!userStore.id || !['profesional', 'director', 'administrativo', 'area'].includes(rol)) {
            presentes.value = [];
            pendientes.value = [];
            informados.clear();
            usuarioEstadoId = null;
            return;
        }

        const usuarioId = userStore.id;
        if (usuarioEstadoId !== usuarioId) {
            pendientes.value = [];
            cargarInformadosGuardados(usuarioId);
            usuarioEstadoId = usuarioId;
        }

        try {
            cargando.value = true;
            const res = await api.get('/turnos/presentes-hoy', { withCredentials: true });
            if (userStore.id !== usuarioId) return;
            const data = res.data || [];
            presentes.value = data;

            const idsPresentes = new Set(data.map((t) => t.id));
            const idsEsperando = new Set(data.filter(estaEsperando).map((t) => t.id));
            for (const id of informados) {
                if (!idsPresentes.has(id)) informados.delete(id);
            }
            // Un pendiente que dejó de estar esperando (lo llamaron, p. ej. desde la lista del Dashboard) sale del aviso.
            pendientes.value = pendientes.value.filter((t) => idsEsperando.has(t.id));

            if (rol === 'profesional' && !silencioso) {
                const idsPendientes = new Set(pendientes.value.map((t) => t.id));
                const nuevos = data.filter((t) => estaEsperando(t) && !informados.has(t.id) && !idsPendientes.has(t.id));
                if (nuevos.length > 0) {
                    pendientes.value = [...pendientes.value, ...nuevos];
                    reproducirAvisoSonoro();
                }
            }
        } catch (e) {
            console.error('Error al cargar pacientes presentes:', e);
        } finally {
            cargando.value = false;
        }
    }

    function marcarInformado() {
        for (const t of pendientes.value) {
            informados.add(t.id);
        }
        pendientes.value = [];
        if (usuarioEstadoId != null) {
            guardarInformados(usuarioEstadoId);
        }
    }

    // Llama a un paciente y, solo a ese paciente, lo da por informado.
    // Si el backend rechaza el llamado la promesa se rechaza y el estado queda intacto.
    async function llamarYMarcar(turno) {
        const usuarioAlLlamar = usuarioEstadoId;
        if (turno.es_grupal) await turnosService.llamarGrupal(turno.turnoId);
        else await turnosService.llamar(turno.turnoId);

        // Desde acá el llamado está confirmado: lo que falle después (recarga) no lo deshace.
        // Si mientras tanto cambió el usuario (cierre de sesión), no se toca el estado de otro.
        if (usuarioEstadoId === usuarioAlLlamar) {
            informados.add(turno.id);
            pendientes.value = pendientes.value.filter((t) => t.id !== turno.id);
            if (usuarioEstadoId != null) guardarInformados(usuarioEstadoId);
        }

        try {
            await cargarPresentes(true);
        } catch {
            // La recarga es solo para refrescar la lista; el llamado ya se hizo.
        }
    }

    function iniciarPolling(intervaloMs = 20000) {
        if (initialized) return;
        initialized = true;

        cargarPresentes(false);

        timer = setInterval(() => {
            cargarPresentes(false);
        }, intervaloMs);
    }

    function detenerPolling() {
        if (timer) {
            clearInterval(timer);
            timer = null;
            initialized = false;
        }
        presentes.value = [];
        pendientes.value = [];
        informados.clear();
        usuarioEstadoId = null;
    }

    return {
        presentes,
        pendientes,
        cantidadPresentes,
        cargando,
        cargarPresentes,
        marcarInformado,
        llamarYMarcar,
        iniciarPolling,
        detenerPolling
    };
}
