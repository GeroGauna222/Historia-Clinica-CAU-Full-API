import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { mount } from '@vue/test-utils';

const pendientes = ref([]);
const marcarInformado = vi.fn(() => {
    pendientes.value = [];
});

vi.mock('@/layout/composables/usePacientesPresentes', () => ({
    usePacientesPresentes: () => ({ pendientes, marcarInformado })
}));

import ArrivalNoticeDialog from './ArrivalNoticeDialog.vue';

describe('ArrivalNoticeDialog', () => {
    beforeEach(() => {
        pendientes.value = [];
        marcarInformado.mockClear();
    });

    it('renders nothing visible when there are no pendientes', () => {
        mount(ArrivalNoticeDialog, { attachTo: document.body });

        expect(document.body.textContent).not.toContain('Informado');
    });

    it('renders the patient name, time, DNI and the Informado button', async () => {
        pendientes.value = [{ id: 1, paciente: 'Juan Perez', dni: '12345678', fecha_inicio: '2026-09-23T10:30:00', motivo: 'Control' }];
        mount(ArrivalNoticeDialog, { attachTo: document.body });
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(document.body.textContent).toContain('Juan Perez');
        expect(document.body.textContent).toContain('12345678');
        expect(document.body.textContent).toContain('Paciente en recepción');
        const button = Array.from(document.body.querySelectorAll('button')).find((b) => b.textContent.includes('Informado'));
        expect(button).toBeTruthy();
    });

    it('shows the plural title when there is more than one pendiente', async () => {
        pendientes.value = [
            { id: 1, paciente: 'Juan Perez', dni: '1', fecha_inicio: '2026-09-23T10:30:00' },
            { id: 2, paciente: 'Maria Gomez', dni: '2', fecha_inicio: '2026-09-23T10:45:00' }
        ];
        mount(ArrivalNoticeDialog, { attachTo: document.body });
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(document.body.textContent).toContain('2 pacientes en recepción');
    });

    it('calls marcarInformado and clears pendientes when the button is clicked', async () => {
        pendientes.value = [{ id: 1, paciente: 'Juan Perez', dni: '12345678', fecha_inicio: '2026-09-23T10:30:00' }];
        mount(ArrivalNoticeDialog, { attachTo: document.body });
        await new Promise((resolve) => setTimeout(resolve, 0));

        const button = Array.from(document.body.querySelectorAll('button')).find((b) => b.textContent.includes('Informado'));
        button.click();
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(marcarInformado).toHaveBeenCalledTimes(1);
        expect(pendientes.value).toEqual([]);
    });

    it('disables the escape/dismiss affordances on the underlying Dialog', () => {
        pendientes.value = [{ id: 1, paciente: 'Juan Perez', dni: '1', fecha_inicio: '2026-09-23T10:30:00' }];
        const wrapper = mount(ArrivalNoticeDialog, { attachTo: document.body });

        const dialog = wrapper.findComponent({ name: 'Dialog' });
        expect(dialog.exists()).toBe(true);
        expect(dialog.props('closable')).toBe(false);
        expect(dialog.props('closeOnEscape')).toBe(false);
        expect(dialog.props('dismissableMask')).toBe(false);
        expect(dialog.props('draggable')).toBe(false);
    });
});
