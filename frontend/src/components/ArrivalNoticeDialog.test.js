import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';

const pendientes = ref([]);
const marcarInformado = vi.fn(() => {
    pendientes.value = [];
});

const llamarYMarcar = vi.fn();

vi.mock('@/layout/composables/usePacientesPresentes', () => ({
    usePacientesPresentes: () => ({ pendientes, marcarInformado, llamarYMarcar })
}));

import ArrivalNoticeDialog from './ArrivalNoticeDialog.vue';

describe('ArrivalNoticeDialog', () => {
    beforeEach(() => {
        pendientes.value = [];
        marcarInformado.mockClear();
        llamarYMarcar.mockReset();
    });

    // Dialog stub: el Dialog real teletransporta al body y findAll no lo vería.
    function montar(lista) {
        pendientes.value = lista;
        return mount(ArrivalNoticeDialog, {
            global: { stubs: { Dialog: { template: '<div><slot /></div>' } } }
        });
    }

    const botonesLlamar = (wrapper) => wrapper.findAll('button').filter((b) => b.text() === 'Llamar');

    it('renders nothing visible when there are no pendientes', () => {
        mount(ArrivalNoticeDialog, { attachTo: document.body });

        expect(document.body.textContent).not.toContain('Informado');
    });

    it('renders the patient name, time, DNI and the Informado button', async () => {
        pendientes.value = [{ id: 1, paciente: 'Juan Perez', dni: '12345678', start: '2026-09-23T10:30:00', motivo: 'Control' }];
        mount(ArrivalNoticeDialog, { attachTo: document.body });
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(document.body.textContent).toContain('Juan Perez');
        expect(document.body.textContent).toContain('12345678');
        expect(document.body.textContent).toContain('10:30');
        expect(document.body.textContent).toContain('Paciente en recepción');
        const button = Array.from(document.body.querySelectorAll('button')).find((b) => b.textContent.includes('Informado'));
        expect(button).toBeTruthy();
    });

    it('shows the plural title when there is more than one pendiente', async () => {
        pendientes.value = [
            { id: 1, paciente: 'Juan Perez', dni: '1', start: '2026-09-23T10:30:00' },
            { id: 2, paciente: 'Maria Gomez', dni: '2', start: '2026-09-23T10:45:00' }
        ];
        mount(ArrivalNoticeDialog, { attachTo: document.body });
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(document.body.textContent).toContain('2 pacientes en recepción');
    });

    it('calls marcarInformado and clears pendientes when the button is clicked', async () => {
        pendientes.value = [{ id: 1, paciente: 'Juan Perez', dni: '12345678', start: '2026-09-23T10:30:00' }];
        mount(ArrivalNoticeDialog, { attachTo: document.body });
        await new Promise((resolve) => setTimeout(resolve, 0));

        const button = Array.from(document.body.querySelectorAll('button')).find((b) => b.textContent.includes('Informado'));
        button.click();
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(marcarInformado).toHaveBeenCalledTimes(1);
        expect(pendientes.value).toEqual([]);
    });

    it('disables the escape/dismiss affordances on the underlying Dialog', () => {
        pendientes.value = [{ id: 1, paciente: 'Juan Perez', dni: '1', start: '2026-09-23T10:30:00' }];
        const wrapper = mount(ArrivalNoticeDialog, { attachTo: document.body });

        const dialog = wrapper.findComponent({ name: 'Dialog' });
        expect(dialog.exists()).toBe(true);
        expect(dialog.props('closable')).toBe(false);
        expect(dialog.props('closeOnEscape')).toBe(false);
        expect(dialog.props('dismissableMask')).toBe(false);
        expect(dialog.props('draggable')).toBe(false);
    });

    it('muestra un botón Llamar por paciente y llama a ese paciente', async () => {
        llamarYMarcar.mockResolvedValue();
        const wrapper = montar([{ id: 'grupal-9', turnoId: 9, es_grupal: 1, paciente: 'Ana Gomez', dni: '1', start: '2026-11-16T10:30:00' }]);
        const botones = wrapper.findAll('button').filter((b) => b.text() === 'Llamar');
        expect(botones).toHaveLength(1);
        expect(botones[0].attributes('aria-label')).toBe('Llamar a Ana Gomez');
        await botones[0].trigger('click');
        expect(llamarYMarcar).toHaveBeenCalledWith(expect.objectContaining({ turnoId: 9 }));
    });

    it('si llamar falla, muestra el error y deja disponible el botón', async () => {
        llamarYMarcar.mockRejectedValue({ response: { data: { error: 'El paciente figura como ausente' } } });
        const wrapper = montar([{ id: 1, turnoId: 1, es_grupal: 0, paciente: 'Ana Gomez' }]);
        await wrapper
            .findAll('button')
            .find((b) => b.text() === 'Llamar')
            .trigger('click');
        await flushPromises();
        expect(wrapper.text()).toContain('El paciente figura como ausente');
        expect(wrapper.find('[role="alert"]').text()).toBe('Ana Gomez: El paciente figura como ausente');
        const boton = botonesLlamar(wrapper)[0];
        expect(boton.attributes('disabled')).toBeUndefined();
    });

    it('usa un mensaje genérico si el error no trae detalle', async () => {
        llamarYMarcar.mockRejectedValue(new Error('Network Error'));
        const wrapper = montar([{ id: 1, turnoId: 1, es_grupal: 0, paciente: 'Ana Gomez' }]);
        await botonesLlamar(wrapper)[0].trigger('click');
        await flushPromises();
        expect(wrapper.text()).toContain('No se pudo llamar al paciente');
    });

    it('mientras se llama a un paciente deshabilita los demás Llamar y luego los libera', async () => {
        let resolver;
        llamarYMarcar.mockReturnValue(new Promise((resolve) => (resolver = resolve)));
        const wrapper = montar([
            { id: 1, turnoId: 1, es_grupal: 0, paciente: 'Ana Gomez' },
            { id: 2, turnoId: 2, es_grupal: 0, paciente: 'Luis Paz' }
        ]);
        await botonesLlamar(wrapper)[0].trigger('click');
        const durante = wrapper.findAll('button').filter((b) => b.attributes('aria-label')?.startsWith('Llamar a'));
        expect(durante[1].attributes('disabled')).toBeDefined();

        resolver();
        await flushPromises();
        const despues = wrapper.findAll('button').filter((b) => b.attributes('aria-label')?.startsWith('Llamar a'));
        expect(despues.every((b) => b.attributes('disabled') === undefined)).toBe(true);
    });

    it('limpia el error anterior al reintentar y deja intacto el botón Informado', async () => {
        llamarYMarcar.mockRejectedValueOnce({ response: { data: { error: 'Falla' } } }).mockResolvedValueOnce();
        const wrapper = montar([{ id: 1, turnoId: 1, es_grupal: 0, paciente: 'Ana Gomez' }]);
        await botonesLlamar(wrapper)[0].trigger('click');
        await flushPromises();
        expect(wrapper.text()).toContain('Falla');

        await botonesLlamar(wrapper)[0].trigger('click');
        await flushPromises();
        expect(wrapper.text()).not.toContain('Falla');

        await wrapper
            .findAll('button')
            .find((b) => b.text() === 'Informado')
            .trigger('click');
        expect(marcarInformado).toHaveBeenCalledTimes(1);
        expect(llamarYMarcar).toHaveBeenCalledTimes(2);
    });

    it('el error no queda pegado: al cerrarse el diálogo y reabrirse no aparece el alert viejo', async () => {
        llamarYMarcar.mockRejectedValue({ response: { data: { error: 'Falla' } } });
        const wrapper = montar([{ id: 1, turnoId: 1, es_grupal: 0, paciente: 'Ana Gomez' }]);
        await botonesLlamar(wrapper)[0].trigger('click');
        await flushPromises();
        expect(wrapper.find('[role="alert"]').exists()).toBe(true);

        pendientes.value = [];
        await flushPromises();
        pendientes.value = [{ id: 2, turnoId: 2, es_grupal: 0, paciente: 'Luis Paz' }];
        await flushPromises();

        expect(wrapper.find('[role="alert"]').exists()).toBe(false);
        expect(wrapper.text()).not.toContain('Falla');
    });
});
