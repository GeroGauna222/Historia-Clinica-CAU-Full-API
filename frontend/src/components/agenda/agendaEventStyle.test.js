import { describe, it, expect } from 'vitest';
import { barColor, eventClassNames, eventStatus, formatTime, isBackgroundEvent, statusKey, statusLabel } from './agendaEventStyle';

function event(extendedProps = {}, extra = {}) {
    return { title: 'Ana Pérez', display: 'auto', extendedProps, ...extra };
}

describe('statusKey', () => {
    it.each([
        ['programado', 'programado'],
        ['presente', 'presente'],
        ['con_aviso', 'con-aviso'],
        ['sin_aviso', 'sin-aviso']
    ])('maps %s to %s', (estado, key) => {
        expect(statusKey(estado)).toBe(key);
    });

    it('falls back to programado for unknown or missing values', () => {
        expect(statusKey('cancelado')).toBe('programado');
        expect(statusKey(undefined)).toBe('programado');
        expect(statusKey(null)).toBe('programado');
    });
});

describe('statusLabel', () => {
    it.each([
        ['programado', 'Programado'],
        ['presente', 'Presente'],
        ['con-aviso', 'Falta con aviso'],
        ['sin-aviso', 'Falta sin aviso']
    ])('labels %s as %s', (key, label) => {
        expect(statusLabel(key)).toBe(label);
    });

    it('falls back to Programado for unknown keys', () => {
        expect(statusLabel('otro')).toBe('Programado');
    });
});

describe('eventStatus', () => {
    it('reads estado_asistencia and falls back to the legacy ausencia field', () => {
        expect(eventStatus(event({ estado_asistencia: 'presente' }))).toBe('presente');
        expect(eventStatus(event({ ausencia: 'con_aviso' }))).toBe('con-aviso');
        expect(eventStatus(event({}))).toBe('programado');
    });
});

describe('eventClassNames', () => {
    it('returns the base and status classes for an individual turno', () => {
        expect(eventClassNames(event({ tipo: 'individual', estado_asistencia: 'presente' }))).toEqual(['evt', 'evt-presente']);
    });

    it('adds evt-grupal for grupal turnos in Turnos', () => {
        expect(eventClassNames(event({ tipo: 'grupal', estado_asistencia: 'sin_aviso' }))).toEqual(['evt', 'evt-sin-aviso', 'evt-grupal']);
    });

    it('adds evt-grupal for turno_grupal in CalendarioGrupo', () => {
        expect(eventClassNames(event({ tipo: 'turno_grupal' }))).toEqual(['evt', 'evt-programado', 'evt-grupal']);
    });

    it('uses programado for an unknown status', () => {
        expect(eventClassNames(event({ estado_asistencia: 'raro' }))).toEqual(['evt', 'evt-programado']);
    });

    it('returns the absence card classes', () => {
        expect(eventClassNames(event({ tipo: 'ausencia' }))).toEqual(['evt', 'evt-ausencia']);
    });

    it('returns the unavailable hatch classes', () => {
        expect(eventClassNames(event({ tipo: 'indisponible_bg' }, { display: 'background' }))).toEqual(['bg-hatch', 'bg-hatch-unavailable']);
    });

    it('returns the absence hatch classes', () => {
        expect(eventClassNames(event({ tipo: 'ausencia_bg' }, { display: 'background' }))).toEqual(['bg-hatch', 'bg-hatch-absence']);
    });
});

describe('barColor', () => {
    it('returns the group color when present', () => {
        expect(barColor(event({ grupoColor: '#7C3AED' }))).toBe('#7C3AED');
    });

    it('returns null without a group color', () => {
        expect(barColor(event({}))).toBeNull();
    });

    it('returns null for values that are not hex colors', () => {
        expect(barColor(event({ grupoColor: 'red; background: url(x)' }))).toBeNull();
    });
});

describe('formatTime', () => {
    it('formats a date as HH:mm in local time', () => {
        expect(formatTime(new Date(2026, 8, 24, 9, 5))).toBe('09:05');
    });

    it('returns an empty string for missing or invalid dates', () => {
        expect(formatTime(null)).toBe('');
        expect(formatTime(new Date('nope'))).toBe('');
    });
});

describe('isBackgroundEvent', () => {
    it('detects background events by display or tipo', () => {
        expect(isBackgroundEvent(event({}, { display: 'background' }))).toBe(true);
        expect(isBackgroundEvent(event({ tipo: 'ausencia_bg' }))).toBe(true);
        expect(isBackgroundEvent(event({ tipo: 'individual' }))).toBe(false);
    });
});
