import { describe, it, expect, afterEach, vi } from 'vitest';
import { enableAutoUnmount, mount } from '@vue/test-utils';
import PantallaTarjetas from './PantallaTarjetas.vue';

enableAutoUnmount(afterEach);

function tarjeta(n, extra = {}) {
    return { tipo: 'profesional', id: n, nombre: `Profesional ${n}`, consultorio: String(n), en_atencion: [], siguientes: [], ...extra };
}
const lista = (n) => Array.from({ length: n }, (_, i) => tarjeta(i + 1));

describe('PantallaTarjetas', () => {
    afterEach(() => vi.useRealTimers());

    it('sin tarjetas muestra el mensaje de vacío', () => {
        const w = mount(PantallaTarjetas, { props: { tarjetas: [] } });
        expect(w.text()).toContain('No hay turnos para mostrar por ahora');
    });

    it('muestra consultorio, profesional y nombres abreviados', () => {
        const w = mount(PantallaTarjetas, {
            props: {
                tarjetas: [
                    tarjeta(3, {
                        nombre: 'Dra. Pérez',
                        en_atencion: [{ nombre: 'Juan P.', atencion_inicio: '2026-11-16 10:00:00' }],
                        siguientes: [{ nombre: 'Ana G.' }, { nombre: 'Luis M.' }]
                    })
                ]
            }
        });
        const texto = w.text();
        expect(texto).toContain('Dra. Pérez');
        expect(w.find('.consultorio').text()).toBe('3');
        expect(texto).toContain('En atención');
        expect(texto).toContain('Siguientes');
        expect(w.find('.en-atencion').text()).toBe('Juan P.');
        expect(w.findAll('.siguiente').map((e) => e.text())).toEqual(['Ana G.', 'Luis M.']);
    });

    it('muestra a dos pacientes en atención con el mismo nombre', () => {
        const w = mount(PantallaTarjetas, {
            props: {
                tarjetas: [
                    tarjeta(1, {
                        en_atencion: [
                            { nombre: 'Ana G.', atencion_inicio: 'a' },
                            { nombre: 'Ana G.', atencion_inicio: 'a' }
                        ]
                    })
                ]
            }
        });
        expect(w.findAll('.en-atencion')).toHaveLength(2);
    });

    it('tolera una tarjeta sin en_atencion ni siguientes', () => {
        const w = mount(PantallaTarjetas, { props: { tarjetas: [{ tipo: 'area', id: 1, nombre: 'Área X' }] } });
        expect(w.text()).toContain('Área X');
        expect(w.findAll('.nadie')).toHaveLength(2);
    });

    it('con 13 tarjetas pagina en dos páginas', () => {
        const w = mount(PantallaTarjetas, { props: { tarjetas: lista(13) } });
        expect(w.text()).toContain('Página 1 de 2');
        expect(w.findAll('.tarjeta')).toHaveLength(12);
    });

    it('rota de página, vuelve a la primera y no salta al llegar un arreglo nuevo', async () => {
        vi.useFakeTimers();
        const w = mount(PantallaTarjetas, { props: { tarjetas: lista(13), rotacionMs: 1000 } });
        await vi.advanceTimersByTimeAsync(1000);
        expect(w.text()).toContain('Página 2 de 2');
        await w.setProps({ tarjetas: lista(13) });
        expect(w.text()).toContain('Página 2 de 2');
        await vi.advanceTimersByTimeAsync(1000);
        expect(w.text()).toContain('Página 1 de 2');
    });

    it('limpia el temporizador al desmontar', () => {
        vi.useFakeTimers();
        const w = mount(PantallaTarjetas, { props: { tarjetas: lista(13), rotacionMs: 1000 } });
        expect(vi.getTimerCount()).toBe(1);
        w.unmount();
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each([
        [1, 'repeat(1,'],
        [4, 'repeat(2,'],
        [9, 'repeat(3,'],
        [12, 'repeat(4,']
    ])('con %i tarjetas arma la grilla con %s', (n, esperado) => {
        const w = mount(PantallaTarjetas, { props: { tarjetas: lista(n) } });
        expect(w.find('.grilla').attributes('style')).toContain(esperado);
    });

    it('ajusta la escala según la cantidad de tarjetas visibles', () => {
        const clases = (n) =>
            mount(PantallaTarjetas, { props: { tarjetas: lista(n) } })
                .find('.tarjetas')
                .classes();
        expect(clases(3)).toContain('grande');
        expect(clases(7)).not.toContain('grande');
        expect(clases(7)).not.toContain('densa');
        expect(clases(10)).toContain('densa');
        expect(clases(12)).toContain('densa');
    });
});
