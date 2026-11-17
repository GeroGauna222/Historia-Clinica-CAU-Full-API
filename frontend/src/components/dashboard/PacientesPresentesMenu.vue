<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { usePacientesPresentes } from '@/layout/composables/usePacientesPresentes';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();
const { presentes, cantidadPresentes, iniciarPolling, detenerPolling, llamarYMarcar } = usePacientesPresentes();

// Un presente sin estado_atencion (o con un valor desconocido) se trata como "Esperando":
// nunca desaparece del menú.
const grupos = computed(() => ({
    esperando: presentes.value.filter((t) => t.estado_atencion !== 'en_atencion' && t.estado_atencion !== 'atendido'),
    enAtencion: presentes.value.filter((t) => t.estado_atencion === 'en_atencion'),
    atendidos: presentes.value.filter((t) => t.estado_atencion === 'atendido')
}));

const secciones = computed(() =>
    [
        { clave: 'esperando', titulo: 'Esperando', items: grupos.value.esperando, llamable: true },
        { clave: 'en-atencion', titulo: 'En atención', items: grupos.value.enAtencion, llamable: false },
        { clave: 'atendidos', titulo: 'Atendidos', items: grupos.value.atendidos, llamable: false }
    ].filter((s) => s.items.length > 0)
);

// El backend solo deja llamar al dueño del turno (o a un miembro del grupo): el profesional recibe
// solo lo suyo; el resto de los roles ve todos los presentes y llama solo a sus propios turnos.
const puedeLlamar = (p) => (userStore.rol || '').toLowerCase().trim() === 'profesional' || (p.usuario_id != null && p.usuario_id === userStore.id);

const llamandoId = ref(null);
const errorLlamado = ref('');

// Solo las filas de "Esperando" se pueden llamar; un atendido no se vuelve a llamar desde acá.
async function llamar(p) {
    errorLlamado.value = '';
    llamandoId.value = p.id;
    try {
        await llamarYMarcar(p);
    } catch (e) {
        errorLlamado.value = e?.response?.data?.error || e?.response?.data?.message || 'No se pudo llamar al paciente. Reintentá.';
    } finally {
        llamandoId.value = null;
    }
}

const menuActive = ref(false);
const menuRef = ref(null);

onMounted(() => {
    iniciarPolling();
    document.addEventListener('click', onOutsideClick);
});

onBeforeUnmount(() => {
    detenerPolling();
    document.removeEventListener('click', onOutsideClick);
});

const toggleMenu = () => {
    errorLlamado.value = '';
    menuActive.value = !menuActive.value;
};

const closeMenu = () => {
    errorLlamado.value = '';
    menuActive.value = false;
};

const onOutsideClick = (event) => {
    if (menuRef.value && !menuRef.value.contains(event.target)) {
        closeMenu();
    }
};

const irAgenda = () => {
    closeMenu();
    router.push('/turnos');
};

function formatoHora(isoString) {
    if (!isoString) return '';
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
}
</script>

<template>
    <div class="relative" ref="menuRef">
        <button
            type="button"
            class="layout-topbar-action relative flex items-center justify-center p-2 rounded-lg hover:bg-emphasis transition focus:outline-none border-none bg-transparent cursor-pointer"
            :class="{ '!text-emerald-600': cantidadPresentes > 0 }"
            title="Pacientes en recepción"
            @click="toggleMenu"
        >
            <i class="pi pi-user-check text-lg"></i>
            <span v-if="cantidadPresentes > 0" class="absolute -top-1 -right-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[11px] font-bold text-white shadow-sm ring-2 ring-card animate-pulse">
                {{ cantidadPresentes }}
            </span>
        </button>

        <transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
        >
            <div v-if="menuActive" class="absolute right-0 mt-2 w-80 max-w-[90vw] origin-top-right bg-card rounded-xl shadow-xl ring-1 ring-line z-50 overflow-hidden">
                <div class="px-4 py-3 border-b border-surface bg-subtle flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <i class="pi pi-building text-status-presente-fg"></i>
                        <span class="font-semibold text-sm text-color">Recepción / Sala de Espera</span>
                    </div>
                    <span v-if="cantidadPresentes > 0" class="text-xs bg-status-presente-bg text-status-presente-fg font-semibold px-2 py-0.5 rounded-full"> {{ cantidadPresentes }} presente{{ cantidadPresentes > 1 ? 's' : '' }} </span>
                </div>

                <p v-if="errorLlamado" class="px-4 py-2 text-xs text-status-sin-aviso-fg border-b border-surface" role="alert">{{ errorLlamado }}</p>

                <div class="max-h-72 overflow-y-auto divide-y divide-line">
                    <div v-if="cantidadPresentes === 0" class="p-5 text-center text-sm text-muted-color">
                        <i class="pi pi-check-circle text-2xl text-muted-color block mb-2"></i>
                        No hay pacientes esperando en recepción.
                    </div>

                    <section v-for="seccion in secciones" :key="seccion.clave" :data-seccion="seccion.clave" class="divide-y divide-line">
                        <h3 class="px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-color bg-subtle">{{ seccion.titulo }}</h3>

                        <div v-for="p in seccion.items" :key="p.id" class="p-3 hover:bg-emphasis transition cursor-pointer" @click="irAgenda">
                            <div class="flex items-start justify-between gap-2">
                                <div>
                                    <p class="text-sm font-semibold text-color leading-tight">{{ p.paciente }}</p>
                                    <p v-if="p.dni" class="text-xs text-muted-color">DNI: {{ p.dni }}</p>
                                </div>
                                <span class="text-xs font-mono font-medium text-status-presente-fg bg-status-presente-bg px-1.5 py-0.5 rounded">
                                    {{ formatoHora(p.start) }}
                                </span>
                            </div>
                            <p v-if="p.motivo" class="text-xs text-muted-color mt-1 truncate"><span class="font-medium text-muted-color">Motivo:</span> {{ p.motivo }}</p>
                            <button
                                v-if="seccion.llamable && puedeLlamar(p)"
                                type="button"
                                class="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline focus-visible:underline cursor-pointer border-none bg-transparent p-0 disabled:opacity-50 disabled:cursor-not-allowed"
                                :aria-label="`Llamar a ${p.paciente}`"
                                :disabled="llamandoId !== null"
                                @click.stop="llamar(p)"
                            >
                                <i :class="llamandoId === p.id ? 'pi pi-spin pi-spinner' : 'pi pi-megaphone'"></i>
                                Llamar
                            </button>
                        </div>
                    </section>
                </div>

                <div class="p-2 border-t border-surface bg-subtle text-center">
                    <button type="button" class="w-full text-xs font-semibold text-primary hover:underline py-1.5 focus:outline-none cursor-pointer border-none bg-transparent" @click="irAgenda">Ver agenda de turnos &rarr;</button>
                </div>
            </div>
        </transition>
    </div>
</template>
