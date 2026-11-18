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

    it('ante un error HTTP muestra el aviso y recarga en silencio (la fila quedó con botones obsoletos)', async () => {
        vi.mocked(turnosService.llamar).mockRejectedValue({ response: { status: 409, data: { error: 'El paciente figura como ausente' } } });
        const w = await montar();
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(toastAdd).toHaveBeenCalledTimes(1);
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error', summary: 'No se pudo completar la acción', detail: 'El paciente figura como ausente' }));
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(boton(w, 'Llamar a Juan Pérez').attributes('disabled')).toBeUndefined();
    });

    it('lee el detalle del error también de `message`', async () => {
        vi.mocked(turnosService.llamar).mockRejectedValue({ response: { status: 403, data: { message: 'Sin permiso' } } });
        const w = await montar();
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ detail: 'Sin permiso' }));
    });

    it('ante un error de red (sin respuesta) avisa con el texto por defecto y NO recarga', async () => {
        vi.mocked(turnosService.llamar).mockRejectedValue(new Error('Network Error'));
        const w = await montar();
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error', summary: 'No se pudo completar la acción', detail: 'Reintentá en unos segundos.' }));
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(boton(w, 'Llamar a Juan Pérez').attributes('disabled')).toBeUndefined();
    });

    it('un error de finalizar muestra el aviso', async () => {
        vi.mocked(turnosService.finalizar).mockRejectedValue({ response: { status: 409, data: { error: 'El turno no está en atención' } } });
        const w = await montar({ turnos: [T_EN_ATENCION] });
        await boton(w, 'Finalizar atención de Ana Gómez').trigger('click');
        await flushPromises();
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error', detail: 'El turno no está en atención' }));
    });

    it('un error de llamarGrupal muestra el aviso', async () => {
        vi.mocked(turnosService.llamarGrupal).mockRejectedValue({ response: { status: 403, data: { error: 'Solo los miembros del grupo pueden llamar al paciente' } } });
        const w = await montar({ turnos: [T_GRUPAL] });
        await boton(w, 'Llamar a Eva Soto').trigger('click');
        await flushPromises();
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error', detail: 'Solo los miembros del grupo pueden llamar al paciente' }));
    });

    it('acción exitosa pero falla la recarga: conserva la tabla y avisa con una advertencia', async () => {
        const w = await montar();
        vi.mocked(api.get).mockRejectedValueOnce(new Error('Network Error'));
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(turnosService.llamar).toHaveBeenCalledWith(1);
        expect(w.text()).not.toContain('No se pudo cargar el inicio.');
        expect(boton(w, 'Llamar a Juan Pérez').exists()).toBe(true);
        expect(toastAdd).toHaveBeenCalledTimes(1);
        expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'warn', detail: expect.stringContaining('Se completó la acción, pero no se pudo actualizar la lista') }));
        expect(toastAdd).not.toHaveBeenCalledWith(expect.objectContaining({ summary: 'No se pudo completar la acción' }));
    });

    it('la carga inicial fallida sí muestra el banner de error', async () => {
        setActivePinia(createPinia());
        vi.mocked(api.get).mockReset().mockRejectedValue(new Error('Network Error'));
        const w = mount(Dashboard, { global: { plugins: [[PrimeVue, { theme: 'none' }]], directives: { tooltip: () => {} }, stubs: { ProximoTurnoWidget: true, Dialog: true } } });
        await flushPromises();
        expect(w.text()).toContain('No se pudo cargar el inicio.');
        expect(toastAdd).not.toHaveBeenCalled();
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

    it('dos clics síncronos sobre el mismo botón disparan una sola llamada (guard de reentrada)', async () => {
        let resolver;
        vi.mocked(turnosService.llamar).mockReturnValue(new Promise((r) => (resolver = r)));
        const w = await montar();
        const b = boton(w, 'Llamar a Juan Pérez');
        b.trigger('click');
        b.trigger('click'); // antes de cualquier re-render: el atributo disabled todavía no cambió
        await flushPromises();
        expect(turnosService.llamar).toHaveBeenCalledTimes(1);
        resolver({ data: {} });
        await flushPromises();
    });

    it('el spinner aparece solo en el botón activo', async () => {
        let resolver;
        vi.mocked(turnosService.llamar).mockReturnValue(new Promise((r) => (resolver = r)));
        const w = await montar({ turnos: [T_ESPERANDO, T_ATENDIDO] });
        await boton(w, 'Llamar a Juan Pérez').trigger('click');
        await flushPromises();
        expect(boton(w, 'Llamar a Juan Pérez').classes()).toContain('p-button-loading');
        expect(boton(w, 'Volver a llamar a Luis Díaz').classes()).not.toContain('p-button-loading');
        resolver({ data: {} });
        await flushPromises();
        expect(boton(w, 'Llamar a Juan Pérez').classes()).not.toContain('p-button-loading');
    });

    it('un turno individual y uno grupal con el mismo número no se confunden: spinner solo en el correcto', async () => {
        let resolver;
        vi.mocked(turnosService.llamarGrupal).mockReturnValue(new Promise((r) => (resolver = r)));
        const grupalMismoNumero = { ...T_GRUPAL, id: 'grupal-1', turnoId: 1 };
        const w = await montar({ turnos: [T_ESPERANDO, grupalMismoNumero] });
        await boton(w, 'Llamar a Eva Soto').trigger('click');
        await flushPromises();
        expect(turnosService.llamarGrupal).toHaveBeenCalledWith(1);
        expect(boton(w, 'Llamar a Eva Soto').classes()).toContain('p-button-loading');
        expect(boton(w, 'Llamar a Juan Pérez').classes()).not.toContain('p-button-loading');
        resolver({ data: {} });
        await flushPromises();
    });

    it('la etiqueta En atención está en la fila correcta', async () => {
        const w = await montar({ turnos: [T_ESPERANDO, T_EN_ATENCION] });
        const fila = (nombre) => w.findAll('tbody tr').find((tr) => tr.text().includes(nombre));
        expect(fila('Ana Gómez').text()).toContain('En atención');
        expect(fila('Juan Pérez').text()).not.toContain('En atención');
    });

    it('administrativo no ve botones de atención en ninguna fila', async () => {
        const w = await montar({ rol: 'administrativo', id: 50, turnos: [T_ESPERANDO, T_EN_ATENCION, T_GRUPAL] });
        expect(etiquetasBotones(w)).toEqual([]);
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
