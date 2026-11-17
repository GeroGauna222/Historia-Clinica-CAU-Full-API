import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, reactive, ref } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';

const presentes = ref([]);
const llamarYMarcar = vi.fn();
const push = vi.fn();
const userStore = reactive({ id: null, rol: '' });

vi.mock('@/stores/user', () => ({
    useUserStore: () => userStore
}));

vi.mock('vue-router', () => ({
    useRouter: () => ({ push })
}));

vi.mock('@/layout/composables/usePacientesPresentes', () => ({
    usePacientesPresentes: () => ({
        presentes,
        cantidadPresentes: computed(() => presentes.value.length),
        iniciarPolling: vi.fn(),
        detenerPolling: vi.fn(),
        llamarYMarcar
    })
}));

import PacientesPresentesMenu from './PacientesPresentesMenu.vue';

function fila(id, estado, extra = {}) {
    const f = { id, turnoId: id, es_grupal: 0, usuario_id: 7, paciente: `Paciente ${id}`, dni: `${id}000`, start: '2026-11-16T10:30:00', motivo: `Motivo ${id}`, ...extra };
    if (estado !== undefined) f.estado_atencion = estado;
    return f;
}

async function montarAbierto(lista, { rol = 'profesional', userId = 7 } = {}) {
    presentes.value = lista;
    userStore.id = userId;
    userStore.rol = rol;
    const wrapper = mount(PacientesPresentesMenu);
    await wrapper.find('button[title="Pacientes en recepción"]').trigger('click');
    return wrapper;
}

const seccion = (wrapper, clave) => wrapper.find(`[data-seccion="${clave}"]`);
const botonesLlamar = (wrapper) => wrapper.findAll('button').filter((b) => b.text() === 'Llamar');

describe('PacientesPresentesMenu', () => {
    beforeEach(() => {
        presentes.value = [];
        llamarYMarcar.mockReset();
        push.mockReset();
    });

    it('agrupa los presentes en Esperando, En atención y Atendidos conservando el contenido de la fila', async () => {
        const wrapper = await montarAbierto([fila(1, 'esperando'), fila(2, 'en_atencion'), fila(3, 'atendido')]);

        expect(seccion(wrapper, 'esperando').text()).toContain('Esperando');
        expect(seccion(wrapper, 'esperando').text()).toContain('Paciente 1');
        expect(seccion(wrapper, 'esperando').text()).toContain('DNI: 1000');
        expect(seccion(wrapper, 'esperando').text()).toContain('10:30');
        expect(seccion(wrapper, 'esperando').text()).toContain('Motivo 1');
        expect(seccion(wrapper, 'en-atencion').text()).toContain('En atención');
        expect(seccion(wrapper, 'en-atencion').text()).toContain('Paciente 2');
        expect(seccion(wrapper, 'atendidos').text()).toContain('Atendidos');
        expect(seccion(wrapper, 'atendidos').text()).toContain('Paciente 3');
    });

    it('un presente sin estado_atencion, null o desconocido se muestra en Esperando', async () => {
        const wrapper = await montarAbierto([fila(1), fila(2, null), fila(3, 'raro')]);

        const esperando = seccion(wrapper, 'esperando');
        expect(esperando.text()).toContain('Paciente 1');
        expect(esperando.text()).toContain('Paciente 2');
        expect(esperando.text()).toContain('Paciente 3');
        expect(botonesLlamar(wrapper)).toHaveLength(3);
    });

    it('solo las filas de Esperando llevan el botón Llamar', async () => {
        const wrapper = await montarAbierto([fila(1, 'esperando'), fila(2, 'en_atencion'), fila(3, 'atendido')]);

        expect(botonesLlamar(wrapper)).toHaveLength(1);
        expect(
            seccion(wrapper, 'esperando')
                .findAll('button')
                .some((b) => b.text() === 'Llamar')
        ).toBe(true);
        expect(seccion(wrapper, 'en-atencion').findAll('button')).toHaveLength(0);
        expect(seccion(wrapper, 'atendidos').findAll('button')).toHaveLength(0);
    });

    it('Llamar llama a ese paciente sin disparar irAgenda (click.stop)', async () => {
        llamarYMarcar.mockResolvedValue();
        const wrapper = await montarAbierto([fila('grupal-9', 'esperando', { turnoId: 9, es_grupal: 1 })]);

        await botonesLlamar(wrapper)[0].trigger('click');
        await flushPromises();

        expect(llamarYMarcar).toHaveBeenCalledWith(expect.objectContaining({ turnoId: 9 }));
        expect(push).not.toHaveBeenCalled();
    });

    it('si llamar falla muestra el error y deja disponible el botón', async () => {
        llamarYMarcar.mockRejectedValue({ response: { data: { error: 'El paciente figura como ausente' } } });
        const wrapper = await montarAbierto([fila(1, 'esperando')]);

        await botonesLlamar(wrapper)[0].trigger('click');
        await flushPromises();

        expect(wrapper.find('[role="alert"]').text()).toContain('El paciente figura como ausente');
        expect(botonesLlamar(wrapper)[0].attributes('disabled')).toBeUndefined();
    });

    it('hacer click en la fila sigue llevando a la agenda', async () => {
        const wrapper = await montarAbierto([fila(1, 'esperando')]);

        await seccion(wrapper, 'esperando').find('p').trigger('click');

        expect(push).toHaveBeenCalledWith('/turnos');
    });

    it('un rol que ve todos los presentes solo puede llamar a sus propios turnos', async () => {
        const wrapper = await montarAbierto([fila(1, 'esperando', { usuario_id: 7 }), fila(2, 'esperando', { usuario_id: 8 }), fila(3, 'esperando', { usuario_id: null })], { rol: 'administrativo', userId: 5 });
        expect(botonesLlamar(wrapper)).toHaveLength(0);

        const propio = await montarAbierto([fila(1, 'esperando', { usuario_id: 5 }), fila(2, 'esperando', { usuario_id: 8 })], { rol: 'area', userId: 5 });
        expect(botonesLlamar(propio)).toHaveLength(1);
    });
});
