import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import PageHeader from './PageHeader.vue';
import StatTile from './StatTile.vue';
import EmptyState from './EmptyState.vue';
import StatusTag from './StatusTag.vue';

describe('PageHeader', () => {
    it('renders title, subtitle and actions', () => {
        const wrapper = mount(PageHeader, {
            props: { title: 'Pacientes', subtitle: 'Listado general' },
            slots: { actions: '<button>Nuevo</button>' }
        });
        expect(wrapper.get('h1').text()).toBe('Pacientes');
        expect(wrapper.text()).toContain('Listado general');
        expect(wrapper.get('button').text()).toBe('Nuevo');
    });

    it('omits the subtitle paragraph when empty', () => {
        const wrapper = mount(PageHeader, { props: { title: 'Inicio' } });
        expect(wrapper.find('p').exists()).toBe(false);
    });
});

describe('StatTile', () => {
    it('renders label, value and hint', () => {
        const wrapper = mount(StatTile, { props: { label: 'Turnos hoy', value: 12, icon: 'pi pi-calendar', hint: '3 presentes' } });
        expect(wrapper.text()).toContain('Turnos hoy');
        expect(wrapper.text()).toContain('12');
        expect(wrapper.text()).toContain('3 presentes');
        expect(wrapper.find('.pi-calendar').exists()).toBe(true);
    });
});

describe('EmptyState', () => {
    it('announces itself and renders the action slot', () => {
        const wrapper = mount(EmptyState, {
            props: { title: 'Sin resultados', message: 'Probá otra búsqueda' },
            slots: { action: '<button>Limpiar</button>' }
        });
        expect(wrapper.attributes('role')).toBe('status');
        expect(wrapper.find('.pi-inbox').exists()).toBe(true);
        expect(wrapper.text()).toContain('Sin resultados');
        expect(wrapper.get('button').text()).toBe('Limpiar');
    });
});

describe('StatusTag', () => {
    it.each([
        ['programado', 'programado', 'Programado'],
        ['presente', 'presente', 'Presente'],
        ['con_aviso', 'con-aviso', 'Ausente con aviso'],
        ['sin_aviso', 'sin-aviso', 'Ausente sin aviso'],
        ['firmada', 'presente', 'Firmada'],
        ['pendiente', 'con-aviso', 'Firma pendiente']
    ])('maps %s to the %s token', (status, token, label) => {
        const wrapper = mount(StatusTag, { props: { status } });
        expect(wrapper.attributes('data-status')).toBe(token);
        expect(wrapper.text()).toBe(label);
    });

    it('falls back to programado styling and the raw value for unknown statuses', () => {
        const wrapper = mount(StatusTag, { props: { status: 'reprogramado' } });
        expect(wrapper.attributes('data-status')).toBe('programado');
        expect(wrapper.text()).toBe('reprogramado');
    });

    it('prefers an explicit label and supports the small size', () => {
        const wrapper = mount(StatusTag, { props: { status: 'presente', label: 'En sala', size: 'sm' } });
        expect(wrapper.text()).toBe('En sala');
        expect(wrapper.classes()).toContain('text-xs');
    });
});
