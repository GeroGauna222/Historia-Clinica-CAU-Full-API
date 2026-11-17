import { describe, it, expect } from 'vitest';
import { ordenarTarjetas, paginar, detectarLlamadosNuevos } from './pantallaTarjetas';

const t = (nombre, consultorio, extra = {}) => ({ tipo: 'usuario', id: nombre, nombre, consultorio, en_atencion: [], siguientes: [], ...extra });

describe('ordenarTarjetas', () => {
    it('numerados ascendente, luego espacios con nombre, luego sin consultorio', () => {
        const orden = ordenarTarjetas([t('Zeta', null), t('Gim', 'Gimnasio'), t('Dos', '10'), t('Uno', '2'), t('Alfa', null), t('Sala', 'Box A')]).map((x) => x.nombre);
        expect(orden).toEqual(['Uno', 'Dos', 'Sala', 'Gim', 'Alfa', 'Zeta']);
    });

    it('no modifica el arreglo original', () => {
        const original = [t('B', '2'), t('A', '1')];
        ordenarTarjetas(original);
        expect(original[0].nombre).toBe('B');
    });
});

describe('paginar', () => {
    it('divide en páginas de hasta 12', () => {
        const tarjetas = Array.from({ length: 25 }, (_, i) => t(`P${i}`, String(i)));
        const paginas = paginar(tarjetas, 12);
        expect(paginas.map((p) => p.length)).toEqual([12, 12, 1]);
    });
    it('sin tarjetas devuelve cero páginas', () => {
        expect(paginar([], 12)).toEqual([]);
    });
});

describe('detectarLlamadosNuevos', () => {
    const conLlamado = (inicio) => [t('Dra', '3', { en_atencion: [{ nombre: 'Ana G.', atencion_inicio: inicio }] })];

    it('la primera carga nunca suena', () => {
        const r = detectarLlamadosNuevos(null, conLlamado('2026-11-16T10:00:00'));
        expect(r.nuevos).toBe(false);
        expect(r.vistos.size).toBe(1);
    });
    it('mismo llamado no suena', () => {
        const a = detectarLlamadosNuevos(null, conLlamado('2026-11-16T10:00:00'));
        expect(detectarLlamadosNuevos(a.vistos, conLlamado('2026-11-16T10:00:00')).nuevos).toBe(false);
    });
    it('paciente nuevo suena', () => {
        const a = detectarLlamadosNuevos(null, []);
        expect(detectarLlamadosNuevos(a.vistos, conLlamado('2026-11-16T10:05:00')).nuevos).toBe(true);
    });
    it('volver a llamar (atencion_inicio cambió) suena', () => {
        const a = detectarLlamadosNuevos(null, conLlamado('2026-11-16T10:00:00'));
        expect(detectarLlamadosNuevos(a.vistos, conLlamado('2026-11-16T10:07:00')).nuevos).toBe(true);
    });
    it('que termine una atención no suena', () => {
        const a = detectarLlamadosNuevos(null, conLlamado('2026-11-16T10:00:00'));
        expect(detectarLlamadosNuevos(a.vistos, []).nuevos).toBe(false);
    });
});
