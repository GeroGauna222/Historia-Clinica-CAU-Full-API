import { describe, it, expect, vi, beforeEach } from 'vitest';
import { isReactive } from 'vue';

vi.mock('tippy.js', () => ({ default: vi.fn() }));

import tippy from 'tippy.js';
import { AGENDA_LOCALE, buildTooltipContent, useAgendaCalendar } from './useAgendaCalendar';

function turno(extendedProps = {}, extra = {}) {
    return {
        title: 'Ana Pérez',
        display: 'auto',
        start: new Date(2026, 8, 24, 10, 0),
        end: new Date(2026, 8, 24, 10, 20),
        extendedProps: { tipo: 'individual', paciente: 'Ana Pérez', ...extendedProps },
        ...extra
    };
}

describe('useAgendaCalendar', () => {
    beforeEach(() => {
        tippy.mockClear();
    });

    it('returns the shared base options', () => {
        const options = useAgendaCalendar();
        expect(options.plugins).toHaveLength(3);
        expect(options.initialView).toBe('timeGridWeek');
        expect(options.slotMinTime).toBe('07:00:00');
        expect(options.slotMaxTime).toBe('22:00:00');
        expect(options.allDaySlot).toBe(false);
        expect(options.height).toBe('100%');
        expect(options.eventMaxStack).toBe(2);
        expect(options.dayMaxEventRows).toBe(3);
        expect(options.headerToolbar).toEqual({ left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' });
        expect(options.eventContent).toBeUndefined();
    });

    it('uses the Spanish locale', () => {
        const options = useAgendaCalendar();
        expect(options.locale.code).toBe('es');
        expect(AGENDA_LOCALE.moreLinkText).toBe('más');
        expect(AGENDA_LOCALE.buttonText.today).toBe('Hoy');
    });

    it('merges overrides over the base options', () => {
        const dateClick = vi.fn();
        const options = useAgendaCalendar({ slotDuration: '00:30:00', initialView: 'dayGridMonth', expandRows: true, dateClick });
        expect(options.slotDuration).toBe('00:30:00');
        expect(options.initialView).toBe('dayGridMonth');
        expect(options.expandRows).toBe(true);
        expect(options.dateClick).toBe(dateClick);
        expect(options.eventMaxStack).toBe(2);
        expect(options.locale.code).toBe('es');
    });

    it('returns a reactive object so views can rebind options', () => {
        const options = useAgendaCalendar();
        expect(isReactive(options)).toBe(true);
        options.slotDuration = '00:15:00';
        expect(options.slotDuration).toBe('00:15:00');
    });

    it('delegates eventClassNames to the style helpers', () => {
        const options = useAgendaCalendar();
        expect(options.eventClassNames({ event: turno({ estado_asistencia: 'presente' }) })).toEqual(['evt', 'evt-presente']);
    });

    it('attaches a themed tippy tooltip on mount', () => {
        const options = useAgendaCalendar();
        const el = document.createElement('a');
        options.eventDidMount({ event: turno(), el });
        expect(tippy).toHaveBeenCalledWith(el, expect.objectContaining({ theme: 'agenda', allowHTML: true, placement: 'top' }));
    });

    it('skips tooltips for background events', () => {
        const options = useAgendaCalendar();
        options.eventDidMount({ event: turno({ tipo: 'ausencia_bg' }, { display: 'background' }), el: document.createElement('div') });
        expect(tippy).not.toHaveBeenCalled();
    });

    it('destroys the tooltip on unmount', () => {
        const options = useAgendaCalendar();
        const destroy = vi.fn();
        const el = document.createElement('a');
        el._tippy = { destroy };
        options.eventWillUnmount({ event: turno(), el });
        expect(destroy).toHaveBeenCalledTimes(1);
    });
});

describe('buildTooltipContent', () => {
    it('lists patient, DNI, time range, status, motivo and professional', () => {
        const html = buildTooltipContent(turno({ dni: '30111222', estado_asistencia: 'presente', description: 'Control', profesional: 'Dra. Gómez' }));
        expect(html).toContain('<strong>Ana Pérez</strong>');
        expect(html).toContain('DNI 30111222');
        expect(html).toContain('10:00 – 10:20');
        expect(html).toContain('Presente');
        expect(html).toContain('Control');
        expect(html).toContain('Dra. Gómez');
    });

    it('escapes HTML coming from the data', () => {
        const html = buildTooltipContent(turno({ paciente: '<img src=x onerror=alert(1)>' }));
        expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
        expect(html).not.toContain('<img');
    });

    it('describes an absence with its type and professional', () => {
        const html = buildTooltipContent(turno({ tipo: 'ausencia', tipoEvento: 'Reunion', profesional: 'Dra. Gómez', paciente: undefined }));
        expect(html).toContain('<strong>Reunion</strong>');
        expect(html).toContain('Dra. Gómez');
        expect(html).toContain('10:00 – 10:20');
    });

    it('shows the group line once', () => {
        const html = buildTooltipContent(turno({ tipo: 'turno_grupal', profesional: 'Grupo: Kinesio', grupoNombre: 'Kinesio' }));
        expect(html.split('Grupo: Kinesio').length - 1).toBe(1);
    });
});
