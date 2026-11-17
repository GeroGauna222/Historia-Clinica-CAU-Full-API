import { describe, it, expect, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import PantallaTarjetas from './PantallaTarjetas.vue';

function tarjeta(n, extra = {}) {
    return { tipo: 'profesional', id: n, nombre: `Profesional ${n}`, consultorio: String(n), en_atencion: [], siguientes: [], ...extra };
}

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

    it('tolera una tarjeta sin en_atencion ni siguientes', () => {
        const w = mount(PantallaTarjetas, { props: { tarjetas: [{ tipo: 'area', id: 1, nombre: 'Área X' }] } });
        expect(w.text()).toContain('Área X');
        expect(w.findAll('.nadie')).toHaveLength(2);
    });

    it('con 13 tarjetas pagina en dos páginas', () => {
        const w = mount(PantallaTarjetas, { props: { tarjetas: Array.from({ length: 13 }, (_, i) => tarjeta(i + 1)) } });
        expect(w.text()).toContain('Página 1 de 2');
        expect(w.findAll('.tarjeta')).toHaveLength(12);
    });

    it('rota de página y no salta al llegar un arreglo nuevo', async () => {
        vi.useFakeTimers();
        const lista = () => Array.from({ length: 13 }, (_, i) => tarjeta(i + 1));
        const w = mount(PantallaTarjetas, { props: { tarjetas: lista(), rotacionMs: 1000 } });
        await vi.advanceTimersByTimeAsync(1000);
        expect(w.text()).toContain('Página 2 de 2');
        await w.setProps({ tarjetas: lista() });
        expect(w.text()).toContain('Página 2 de 2');
        w.unmount();
    });
});
