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

    it('con el mismo consultorio desempata por nombre, luego por tipo y luego por id', () => {
        const orden = ordenarTarjetas([t('B', '3', { id: 1 }), t('A', '3', { id: 9 }), t('A', '3', { id: 2, tipo: 'grupo' }), t('A', '3', { id: 10 }), t('A', '3', { id: 2 })]).map((x) => `${x.nombre}-${x.tipo}-${x.id}`);
        expect(orden).toEqual(['A-grupo-2', 'A-usuario-2', 'A-usuario-9', 'A-usuario-10', 'B-usuario-1']);
    });

    it('ignora los espacios alrededor del consultorio', () => {
        const orden = ordenarTarjetas([t('Z', ' Sala B '), t('Y', 'Sala A'), t('X', ' 2 '), t('W', '10')]).map((x) => x.nombre);
        expect(orden).toEqual(['X', 'W', 'Y', 'Z']);
        // mismo consultorio salvo espacios: decide el nombre
        expect(ordenarTarjetas([t('B', ' Box'), t('A', 'Box ')]).map((x) => x.nombre)).toEqual(['A', 'B']);
    });

    it('ordena los números dentro del texto de forma natural', () => {
        const orden = ordenarTarjetas([t('Diez', 'Box 10'), t('Dos', 'Box 2')]).map((x) => x.nombre);
        expect(orden).toEqual(['Dos', 'Diez']);
    });

    it('tolera un nombre nulo', () => {
        expect(() => ordenarTarjetas([t(null, '3'), t('A', '3'), t(null, null), t('B', null)])).not.toThrow();
        expect(ordenarTarjetas([t('A', '3'), t(null, '3')])[0].nombre).toBeNull();
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
    it.each([0, -3, NaN, 0.4])('un tamaño de página inválido (%s) no cuelga y usa páginas de 1', (porPagina) => {
        // Con 0 el bucle original no avanzaba nunca (bucle infinito): este caso no se puede correr en rojo.
        const paginas = paginar([t('A', '1'), t('B', '2'), t('C', '3')], porPagina);
        expect(paginas.map((p) => p.length)).toEqual([1, 1, 1]);
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
    it('dos pacientes con el mismo atencion_inicio cuentan por separado', () => {
        const mismoInstante = '2026-11-16T10:00:00';
        const una = [t('Dra', '3', { en_atencion: [{ nombre: 'Ana G.', atencion_inicio: mismoInstante }] })];
        const dos = [
            t('Dra', '3', {
                en_atencion: [
                    { nombre: 'Ana G.', atencion_inicio: mismoInstante },
                    { nombre: 'Luis P.', atencion_inicio: mismoInstante }
                ]
            })
        ];
        const a = detectarLlamadosNuevos(null, una);
        const r = detectarLlamadosNuevos(a.vistos, dos);
        expect(r.nuevos).toBe(true);
        expect(r.vistos.size).toBe(2);
    });
    it('tolera una tarjeta sin en_atencion', () => {
        const sinLista = [t('Dra', '3', { en_atencion: undefined })];
        expect(detectarLlamadosNuevos(null, sinLista)).toEqual({ nuevos: false, vistos: new Set() });
        const a = detectarLlamadosNuevos(new Set(), sinLista);
        expect(a.nuevos).toBe(false);
    });
});
