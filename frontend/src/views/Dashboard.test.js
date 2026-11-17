import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, enableAutoUnmount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PrimeVue from 'primevue/config';

const toastAdd = vi.fn();

vi.mock('@/api/axios', () => ({ default: { get: vi.fn(), patch: vi.fn() } }));
vi.mock('@/service/turnosService', () => ({
    default: { llamar: vi.fn(), finalizar: vi.fn(), llamarGrupal: vi.fn() }
}));
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }));

import api from '@/api/axios';
import turnosService from '@/service/turnosService';
import { useUserStore } from '@/stores/user';
import Dashboard from './Dashboard.vue';

enableAutoUnmount(afterEach);

const base = { fecha_inicio: '2026-11-17T09:00:00', fecha_fin: '2026-11-17T09:30:00', paciente_id: 1, estado_asistencia: 'presente' };
const T_ESPERANDO = { ...base, id: 1, turnoId: 1, es_grupal: false, usuario_id: 9, paciente: 'Juan', apellido: 'Pérez', estado_atencion: 'esperando' };
const T_EN_ATENCION = { ...base, id: 2, turnoId: 2, es_grupal: false, usuario_id: 9, paciente: 'Ana', apellido: 'Gómez', estado_atencion: 'en_atencion' };
const T_ATENDIDO = { ...base, id: 3, turnoId: 3, es_grupal: false, usuario_id: 9, paciente: 'Luis', apellido: 'Díaz', estado_atencion: 'atendido' };
const T_GRUPAL = { ...base, id: 'grupal-12', turnoId: 12, es_grupal: true, grupo_id: 4, usuario_id: 9, paciente: 'Eva', apellido: 'Soto', estado_atencion: 'esperando' };
const T_GRUPAL_EN_ATENCION = { ...base, id: 'grupal-13', turnoId: 13, es_grupal: true, grupo_id: 4, usuario_id: 9, paciente: 'Rita', apellido: 'Vega', estado_atencion: 'en_atencion' };
const T_AUSENTE = { ...base, id: 4, turnoId: 4, es_grupal: false, usuario_id: 9, paciente: 'Marta', apellido: 'Ruiz', estado_asistencia: 'sin_aviso', estado_atencion: null };

const payload = (turnos, extra = {}) => ({
    data: { resumen: {}, turnos, atenciones_en_curso: [], turno_en_curso: null, disponibilidad_hoy: [], comunicados: [], alertas: {}, ausencias_bloqueos: [], ...extra }
});

async function montar({ rol = 'profesional', id = 9, turnos = [T_ESPERANDO], extra = {} } = {}) {
    setActivePinia(createPinia());
    const store = useUserStore();
    store.rol = rol;
    store.id = id;
    vi.mocked(api.get).mockReset().mockResolvedValue(payload(turnos, extra));
    const wrapper = mount(Dashboard, {
        global: {
            plugins: [[PrimeVue, { theme: 'none' }]],
            directives: { tooltip: () => {} },
            stubs: { ProximoTurnoWidget: true, Dialog: true }
        }
    });
    await flushPromises();
    return wrapper;
}

const boton = (w, aria) => w.find(`button[aria-label="${aria}"]`);
const etiquetasBotones = (w) =>
    w
        .findAll('button[aria-label]')
        .map((b) => b.attributes('aria-label'))
        .filter((e) => /^(Llamar|Volver a llamar|Finalizar)/.test(e));

describe('Dashboard: atención desde la lista de turnos del día', () => {
    beforeEach(() => {
        toastAdd.mockReset();
        for (const fn of Object.values(turnosService)) vi.mocked(fn).mockReset().mockResolvedValue({ data: {} });
        localStorage.setItem('ultima_alerta_turnos_vista', new Date().toISOString().slice(0, 10));
    });

    it('muestra los botones según el estado de atención de cada fila', async () => {
        const w = await montar({ turnos: [T_ESPERANDO, T_EN_ATENCION, T_ATENDIDO, T_GRUPAL, T_GRUPAL_EN_ATENCION, T_AUSENTE] });
        const etiquetas = etiquetasBotones(w);
        expect(etiquetas).toEqual(expect.arrayContaining(['Llamar a Juan Pérez', 'Finalizar atención de Ana Gómez', 'Volver a llamar a Ana Gómez', 'Volver a llamar a Luis Díaz', 'Llamar a Eva Soto', 'Volver a llamar a Rita Vega']));
        expect(etiquetas).not.toContain('Finalizar atención de Rita Vega'); // grupal: termina sola
        expect(etiquetas.some((e) => e.includes('Marta Ruiz'))).toBe(false); // ausente
        expect(etiquetas).toHaveLength(6);
    });

    it('marca con una etiqueta la fila En atención', async () => {
        const w = await montar({ turnos: [T_ESPERANDO, T_EN_ATENCION] });
        expect(w.text().match(/En atención/g)).toHaveLength(1);
    });

    it('Llamar a un turno individual llama a llamar con el id y recarga el dashboard', async () => {
        const w = await montar();
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(turnosService.llamar).toHaveBeenCalledWith(1);
        expect(turnosService.llamarGrupal).not.toHaveBeenCalled();
        expect(api.get).toHaveBeenCalledTimes(2); // carga inicial + recarga
        expect(toastAdd).not.toHaveBeenCalled();
    });

    it('Llamar a un turno grupal usa el id real (sin el prefijo grupal-) y llamarGrupal', async () => {
        const w = await montar({ turnos: [T_GRUPAL] });
        await boton(w, 'Llamar a Eva Soto').trigger('click');
        await flushPromises();
        expect(turnosService.llamarGrupal).toHaveBeenCalledWith(12);
        expect(turnosService.llamar).not.toHaveBeenCalled();
        expect(api.get).toHaveBeenCalledTimes(2);
    });

    it('Finalizar llama a finalizar y recarga', async () => {
        const w = await montar({ turnos: [T_EN_ATENCION] });
        await boton(w, 'Finalizar atención de Ana Gómez').trigger('click');
        await flushPromises();
        expect(turnosService.finalizar).toHaveBeenCalledWith(2);
        expect(api.get).toHaveBeenCalledTimes(2);
    });

    it('Volver a llamar un atendido usa llamar', async () => {
        const w = await montar({ turnos: [T_ATENDIDO] });
        await boton(w, 'Volver a llamar a Luis Díaz').trigger('click');
        await flushPromises();
        expect(turnosService.llamar).toHaveBeenCalledWith(3);
    });

    it('ante un error muestra el aviso, no recarga y deja los botones habilitados', async () => {
        vi.mocked(turnosService.llamar).mockRejectedValue({ response: { data: { error: 'El paciente figura como ausente' } } });
        const w = await montar();
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error', summary: 'No se pudo completar la acción', detail: 'El paciente figura como ausente' }));
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(boton(w, 'Llamar a Juan Pérez').attributes('disabled')).toBeUndefined();
    });

    it('ante un error sin mensaje del servidor usa el texto por defecto', async () => {
        vi.mocked(turnosService.llamar).mockRejectedValue(new Error('Network Error'));
        const w = await montar();
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error', detail: 'Reintentá en unos segundos.' }));
    });

    it('mientras una acción está en curso bloquea los botones de las demás filas', async () => {
        let resolver;
        vi.mocked(turnosService.llamar).mockReturnValue(new Promise((r) => (resolver = r)));
        const w = await montar({ turnos: [T_ESPERANDO, T_ATENDIDO] });
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(boton(w, 'Volver a llamar a Luis Díaz').attributes('disabled')).toBeDefined();
        await boton(w, 'Volver a llamar a Luis Díaz').trigger('click');
        expect(turnosService.llamar).toHaveBeenCalledTimes(1);
        resolver({ data: {} });
        await flushPromises();
        expect(boton(w, 'Volver a llamar a Luis Díaz').attributes('disabled')).toBeUndefined();
    });

    it('director sin turnos propios no ve acciones sobre turnos de otros ni grupales', async () => {
        const ajeno = { ...T_ESPERANDO, usuario_id: 77 };
        const w = await montar({ rol: 'director', id: 100, turnos: [ajeno, { ...T_GRUPAL, usuario_id: null }] });
        expect(etiquetasBotones(w)).toEqual([]);
    });

    it('el director puede llamar sus propios turnos individuales', async () => {
        const w = await montar({ rol: 'director', id: 9, turnos: [T_ESPERANDO] });
        expect(etiquetasBotones(w)).toEqual(['Llamar a Juan Pérez']);
    });

    it('"en curso" sale solo de lo que entrega el backend: un presente sin llamar no cuenta', async () => {
        const w = await montar({ turnos: [T_ESPERANDO] });
        expect(w.text()).not.toMatch(/\d+ en atención/);
    });

    it('con atenciones en curso del backend muestra el contador', async () => {
        const w = await montar({ turnos: [T_EN_ATENCION], extra: { atenciones_en_curso: [T_EN_ATENCION], turno_en_curso: T_EN_ATENCION } });
        expect(w.text()).toContain('1 en atención');
    });
});
