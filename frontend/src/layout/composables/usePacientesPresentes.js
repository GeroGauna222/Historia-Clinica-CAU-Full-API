import { ref, computed } from 'vue';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';

const STORAGE_KEY = 'cau-arrival-acks';

const presentes = ref([]);
const pendientes = ref([]);
const cargando = ref(false);
const informados = new Set();
let usuarioEstadoId = null;
let timer = null;
let initialized = false;

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

function reproducirAvisoSonoro() {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        const now = ctx.currentTime;

        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(659.25, now);
        gain1.gain.setValueAtTime(0.12, now);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc1.connect(gain1);
        gain1.connect(ctx.destination);
        osc1.start(now);
        osc1.stop(now + 0.35);

        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(880, now + 0.18);
        gain2.gain.setValueAtTime(0.15, now + 0.18);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.65);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start(now + 0.18);
        osc2.stop(now + 0.65);
    } catch {
        // Ignorar restricciones de audio del navegador sin interacción de usuario
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
            for (const id of informados) {
                if (!idsPresentes.has(id)) informados.delete(id);
            }
            pendientes.value = pendientes.value.filter((t) => idsPresentes.has(t.id));

            if (rol === 'profesional' && !silencioso) {
                const idsPendientes = new Set(pendientes.value.map((t) => t.id));
                const nuevos = data.filter((t) => !informados.has(t.id) && !idsPendientes.has(t.id));
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
        iniciarPolling,
        detenerPolling
    };
}
