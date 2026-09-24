import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import AgendaEvent from './AgendaEvent.vue';

function makeArg(extendedProps = {}, { viewType = 'timeGridWeek', display = 'auto', title = 'Ana Pérez' } = {}) {
    return {
        view: { type: viewType },
        event: {
            title,
            display,
            start: new Date(2026, 8, 24, 10, 0),
            end: new Date(2026, 8, 24, 10, 20),
            extendedProps: { tipo: 'individual', paciente: 'Ana Pérez', description: 'Control', estado_asistencia: 'programado', ...extendedProps }
        }
    };
}

function mountEvent(...args) {
    return mount(AgendaEvent, { props: { arg: makeArg(...args) } });
}

describe('AgendaEvent', () => {
    it('renders time, patient and motivo in the timeGrid card', () => {
        const wrapper = mountEvent();
        expect(wrapper.find('.evt-time').text()).toBe('10:00');
        expect(wrapper.find('.evt-name').text()).toBe('Ana Pérez');
        expect(wrapper.find('.evt-detail').text()).toBe('Control');
    });

    it('renders a single-line variant in month view', () => {
        const wrapper = mountEvent({}, { viewType: 'dayGridMonth' });
        expect(wrapper.find('.evt-card--month').exists()).toBe(true);
        expect(wrapper.find('.evt-dot').exists()).toBe(true);
        expect(wrapper.find('.evt-detail').exists()).toBe(false);
        expect(wrapper.text()).toContain('10:00');
        expect(wrapper.text()).toContain('Ana Pérez');
    });

    it('shows the group icon and the group name for grupal turnos', () => {
        const wrapper = mountEvent({ tipo: 'grupal', grupoNombre: 'Kinesiología' });
        expect(wrapper.find('.pi-users').exists()).toBe(true);
        expect(wrapper.find('.evt-detail').text()).toBe('Kinesiología');
    });

    it('includes the status label in the aria-label', () => {
        const wrapper = mountEvent({ estado_asistencia: 'presente' });
        const label = wrapper.find('.evt-card').attributes('aria-label');
        expect(label).toContain('Presente');
        expect(label).toContain('Ana Pérez');
        expect(label).toContain('10:00');
    });

    it('strikes the patient name for sin_aviso', () => {
        const wrapper = mountEvent({ estado_asistencia: 'sin_aviso' });
        expect(wrapper.find('.evt-name').classes()).toContain('evt-name--struck');
        expect(wrapper.find('.evt-card').attributes('aria-label')).toContain('Falta sin aviso');
    });

    it('sets --evt-bar inline when the event has a group color', () => {
        const wrapper = mountEvent({ grupoColor: '#7c3aed' });
        expect(wrapper.find('.evt-card').element.style.getPropertyValue('--evt-bar')).toBe('#7c3aed');
    });

    it('does not set --evt-bar without a group color', () => {
        const wrapper = mountEvent();
        expect(wrapper.find('.evt-card').element.style.getPropertyValue('--evt-bar')).toBe('');
    });

    it('renders an absence with its type and professional', () => {
        const wrapper = mountEvent({ tipo: 'ausencia', tipoEvento: 'Reunion', profesional: 'Dra. Gómez', paciente: undefined, estado_asistencia: undefined });
        expect(wrapper.find('.evt-name').text()).toBe('Reunion');
        expect(wrapper.find('.evt-detail').text()).toBe('Dra. Gómez');
        expect(wrapper.find('.evt-card').attributes('aria-label')).toContain('Ausencia');
    });

    it('renders only the Ausencia label for a full-day absence background', () => {
        const wrapper = mountEvent({ tipo: 'ausencia_bg' }, { display: 'background', title: '' });
        expect(wrapper.find('.evt-card').exists()).toBe(false);
        expect(wrapper.find('.bg-hatch-label').text()).toBe('Ausencia');
    });
});
