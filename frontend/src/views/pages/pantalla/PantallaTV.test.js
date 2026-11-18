import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, enableAutoUnmount, flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';

const mock = vi.hoisted(() => ({ tv: null }));
vi.mock('@/composables/usePantallaTV', async () => {
    const { ref } = await import('vue');
    mock.tv = {
        estado: ref('iniciando'),
        codigo: ref(''),
        tarjetas: ref([]),
        reconectando: ref(false),
        sonidoActivo: ref(false),
        activarSonido: vi.fn(),
        iniciar: vi.fn(),
        detener: vi.fn()
    };
    return { usePantallaTV: () => mock.tv };
});

import PantallaTV from './PantallaTV.vue';

enableAutoUnmount(afterEach);

function montar() {
    return mount(PantallaTV, { attachTo: document.body });
}

describe('PantallaTV', () => {
    beforeEach(() => {
        mock.tv.estado.value = 'iniciando';
        mock.tv.codigo.value = '';
        mock.tv.tarjetas.value = [];
        mock.tv.reconectando.value = false;
        mock.tv.sonidoActivo.value = false;
        mock.tv.iniciar.mockClear();
        mock.tv.detener.mockClear();
    });

    it('inicia al montar y detiene al desmontar', () => {
        const w = montar();
        expect(mock.tv.iniciar).toHaveBeenCalledTimes(1);
        w.unmount();
        expect(mock.tv.detener).toHaveBeenCalledTimes(1);
    });

    it('iniciando muestra el mensaje de espera', () => {
        expect(montar().text()).toContain('Iniciando');
    });

    it('pendiente muestra la indicación y el código', () => {
        mock.tv.estado.value = 'pendiente';
        mock.tv.codigo.value = 'AB12CD';
        const w = montar();
        expect(w.text()).toContain('Pedile al director que cargue este código');
        expect(w.find('.codigo').text()).toBe('AB12CD');
    });

    it('limite pide probar en unos minutos', () => {
        mock.tv.estado.value = 'limite';
        expect(montar().text()).toContain('Probá en unos minutos');
    });

    it('vinculada muestra las tarjetas', () => {
        mock.tv.estado.value = 'vinculada';
        mock.tv.sonidoActivo.value = true;
        const w = montar();
        expect(w.text()).toContain('No hay turnos para mostrar por ahora');
        expect(w.text()).not.toContain('Reconectando');
    });

    it('vinculada y reconectando muestra el aviso de reconexión en lugar de las tarjetas', () => {
        mock.tv.estado.value = 'vinculada';
        mock.tv.sonidoActivo.value = true;
        mock.tv.reconectando.value = true;
        const w = montar();
        expect(w.text()).toContain('Reconectando');
        expect(w.text()).not.toContain('No hay turnos');
    });

    it('el botón de sonido recibe el foco cuando se vuelve visible', async () => {
        const w = montar();
        expect(w.find('.sonido').exists()).toBe(false);
        mock.tv.estado.value = 'vinculada';
        await nextTick();
        await flushPromises();
        const boton = w.find('.sonido');
        expect(boton.exists()).toBe(true);
        expect(document.activeElement).toBe(boton.element);
    });

    it('con el sonido activo no muestra el botón', () => {
        mock.tv.estado.value = 'vinculada';
        mock.tv.sonidoActivo.value = true;
        expect(montar().find('.sonido').exists()).toBe(false);
    });

    it('el reloj se actualiza cada segundo', async () => {
        vi.useFakeTimers();
        try {
            vi.setSystemTime(new Date(2026, 10, 16, 10, 0, 0));
            const w = montar();
            const antes = w.find('.reloj').text();
            vi.setSystemTime(new Date(2026, 10, 16, 10, 1, 0));
            await vi.advanceTimersByTimeAsync(1000);
            expect(w.find('.reloj').text()).not.toBe(antes);
        } finally {
            vi.useRealTimers();
        }
    });
});
