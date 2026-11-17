import { describe, it, expect } from 'vitest';
import { claveTurno, puedeLlamar, accionesAtencion } from './atencionTurnos';

const propio = { id: 5, turnoId: 5, es_grupal: false, usuario_id: 9, paciente: 'Juan', apellido: 'Pérez', estado_asistencia: 'presente', estado_atencion: 'esperando' };
const grupal = { id: 'grupal-12', turnoId: 12, es_grupal: true, usuario_id: null, paciente: 'Ana', apellido: 'Gómez', estado_asistencia: 'presente', estado_atencion: 'esperando' };

const prof = { esAdmin: false, userId: 9 };
const admin = { esAdmin: true, userId: 9 };

describe('claveTurno', () => {
    it('distingue turnos individuales de grupales con el mismo número', () => {
        expect(claveTurno({ es_grupal: false, turnoId: 12, id: 12 })).toBe('i-12');
        expect(claveTurno({ es_grupal: true, turnoId: 12, id: 'grupal-12' })).toBe('g-12');
    });

    it('usa id si no hay turnoId', () => {
        expect(claveTurno({ es_grupal: false, id: 3 })).toBe('i-3');
    });
});

describe('puedeLlamar', () => {
    it('el profesional puede llamar sus turnos individuales y los de sus grupos', () => {
        expect(puedeLlamar(propio, prof)).toBe(true);
        expect(puedeLlamar(grupal, prof)).toBe(true);
    });

    it('un turno programado (aún no presente) se puede llamar', () => {
        expect(puedeLlamar({ ...propio, estado_asistencia: 'programado', estado_atencion: null }, prof)).toBe(true);
    });

    it('no se puede llamar a un ausente con aviso ni sin aviso', () => {
        expect(puedeLlamar({ ...propio, estado_asistencia: 'con_aviso' }, prof)).toBe(false);
        expect(puedeLlamar({ ...propio, estado_asistencia: 'sin_aviso' }, prof)).toBe(false);
        expect(puedeLlamar({ ...grupal, estado_asistencia: 'sin_aviso' }, prof)).toBe(false);
    });

    it('director y administrativo solo pueden llamar turnos individuales propios', () => {
        expect(puedeLlamar(propio, admin)).toBe(true);
        expect(puedeLlamar({ ...propio, usuario_id: 77 }, admin)).toBe(false);
        expect(puedeLlamar(grupal, admin)).toBe(false);
    });

    it('un administrativo no puede llamar ningún turno (no tiene agenda propia)', () => {
        expect(puedeLlamar(propio, { esAdmin: true, userId: 100 })).toBe(false);
    });

    it('sin usuario identificado no se puede llamar como admin', () => {
        expect(puedeLlamar({ ...propio, usuario_id: null }, { esAdmin: true, userId: null })).toBe(false);
    });
});

describe('accionesAtencion', () => {
    const resumen = (t, ctx = prof) => accionesAtencion(t, ctx).map((a) => `${a.accion}:${a.label}`);

    it('esperando: solo Llamar', () => {
        expect(resumen(propio)).toEqual(['llamar:Llamar']);
        expect(resumen({ ...propio, estado_atencion: null, estado_asistencia: 'programado' })).toEqual(['llamar:Llamar']);
    });

    it('en atención: Finalizar y Volver a llamar', () => {
        expect(resumen({ ...propio, estado_atencion: 'en_atencion' })).toEqual(['finalizar:Finalizar', 'llamar:Volver a llamar']);
    });

    it('en atención grupal: sin Finalizar (termina sola)', () => {
        expect(resumen({ ...grupal, estado_atencion: 'en_atencion' })).toEqual(['llamar:Volver a llamar']);
    });

    it('atendido: Volver a llamar', () => {
        expect(resumen({ ...propio, estado_atencion: 'atendido' })).toEqual(['llamar:Volver a llamar']);
        expect(resumen({ ...grupal, estado_atencion: 'atendido' })).toEqual(['llamar:Volver a llamar']);
    });

    it('sin permiso o ausente: ninguna acción', () => {
        expect(resumen(grupal, admin)).toEqual([]);
        expect(resumen({ ...propio, estado_asistencia: 'con_aviso', estado_atencion: null })).toEqual([]);
    });

    it('cada acción lleva aria-label con el paciente', () => {
        const acciones = accionesAtencion({ ...propio, estado_atencion: 'en_atencion' }, prof);
        expect(acciones.map((a) => a.ariaLabel)).toEqual(['Finalizar atención de Juan Pérez', 'Volver a llamar a Juan Pérez']);
        expect(accionesAtencion(propio, prof)[0].ariaLabel).toBe('Llamar a Juan Pérez');
    });

    it('el aria-label funciona sin apellido', () => {
        expect(accionesAtencion({ ...propio, apellido: undefined }, prof)[0].ariaLabel).toBe('Llamar a Juan');
    });
});
