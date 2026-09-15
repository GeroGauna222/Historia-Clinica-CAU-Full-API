import { ref, computed } from 'vue';
import api from '@/api/axios';
import { useToast } from 'primevue/usetoast';
import { useUserStore } from '@/stores/user';

const presentes = ref([]);
const cargando = ref(false);
const notificados = new Set();
let timer = null;
let initialized = false;

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
    const toast = useToast();
    const userStore = useUserStore();

    const cantidadPresentes = computed(() => presentes.value.length);

    async function cargarPresentes(silencioso = false) {
        const rol = (userStore.rol || '').toLowerCase().trim();
        if (!userStore.id || !['profesional', 'director', 'administrativo', 'area'].includes(rol)) {
            return;
        }

        try {
            cargando.value = true;
            const res = await api.get('/turnos/presentes-hoy', { withCredentials: true });
            const data = res.data || [];
            presentes.value = data;

            if (rol === 'profesional') {
                for (const t of data) {
                    if (!notificados.has(t.id)) {
                        notificados.add(t.id);
                        if (!silencioso) {
                            toast.add({
                                severity: 'info',
                                summary: 'Paciente en recepción',
                                detail: `${t.paciente || 'Un paciente'} está en recepción.`,
                                life: 8000
                            });
                            reproducirAvisoSonoro();
                        }
                    }
                }
            }
        } catch (e) {
            console.error('Error al cargar pacientes presentes:', e);
        } finally {
            cargando.value = false;
        }
    }

    function iniciarPolling(intervaloMs = 20000) {
        if (initialized) return;
        initialized = true;

        cargarPresentes(true);

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
    }

    return {
        presentes,
        cantidadPresentes,
        cargando,
        cargarPresentes,
        iniciarPolling,
        detenerPolling
    };
}
