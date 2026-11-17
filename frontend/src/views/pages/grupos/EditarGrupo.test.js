import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, enableAutoUnmount, flushPromises } from '@vue/test-utils';
import PrimeVue from 'primevue/config';

vi.mock('vue-router', () => ({
    useRoute: () => ({ params: { id: '9' } }),
    useRouter: () => ({ push: vi.fn() })
}));
vi.mock('@/api/axios', () => ({
    default: { get: vi.fn(), put: vi.fn(), post: vi.fn(), delete: vi.fn() }
}));

import api from '@/api/axios';
import EditarGrupo from './EditarGrupo.vue';

enableAutoUnmount(afterEach);

// jsdom no trae matchMedia ni ResizeObserver y los componentes de PrimeVue (Select, MultiSelect) los usan al montarse.
vi.stubGlobal('matchMedia', (query) => ({ matches: false, media: query, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }));
vi.stubGlobal(
    'ResizeObserver',
    class {
        observe() {}
        unobserve() {}
        disconnect() {}
    }
);

const GRUPO = { id: 9, nombre: 'Rehabilitación', descripcion: 'x', color: '#00936B', es_rehabilitacion: 1, consultorio: 'Gimnasio', mostrar_en_pantalla: 0 };

function responder(grupo) {
    vi.mocked(api.get).mockImplementation((url) => {
        if (url === '/usuarios') return Promise.resolve({ data: [] });
        if (url === '/grupos/9') return Promise.resolve({ data: { ...GRUPO, ...grupo } });
        if (url === '/grupos/9/miembros') return Promise.resolve({ data: [] });
        return Promise.reject(new Error(`URL inesperada ${url}`));
    });
}

async function montar(grupo = {}) {
    responder(grupo);
    const w = mount(EditarGrupo, { global: { plugins: [[PrimeVue, { theme: 'none' }]] } });
    await flushPromises();
    return w;
}

const campo = (w) => w.find('input#consultorio');

describe('EditarGrupo - campo Consultorio', () => {
    beforeEach(() => {
        vi.mocked(api.get).mockReset();
        vi.mocked(api.put)
            .mockReset()
            .mockResolvedValue({ data: { message: 'ok' } });
    });

    it('carga el consultorio del grupo', async () => {
        const w = await montar();
        expect(campo(w).element.value).toBe('Gimnasio');
    });

    it('un consultorio null se muestra vacío', async () => {
        const w = await montar({ consultorio: null });
        expect(campo(w).element.value).toBe('');
    });

    it('el aviso aparece solo si el grupo está visible en la pantalla', async () => {
        const oculto = await montar({ mostrar_en_pantalla: 0 });
        expect(oculto.text()).not.toContain('visible en la pantalla de llamados');
        const visible = await montar({ mostrar_en_pantalla: 1 });
        expect(visible.text()).toContain('visible en la pantalla de llamados');
    });

    it('el PUT envía el consultorio editado', async () => {
        const w = await montar();
        await campo(w).setValue('Sala 2');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(api.put).toHaveBeenCalledTimes(1);
        const [url, payload] = vi.mocked(api.put).mock.calls[0];
        expect(url).toBe('/grupos/9');
        expect(payload.consultorio).toBe('Sala 2');
    });

    it('el PUT envía cadena vacía al quitar el consultorio (el backend la guarda como NULL)', async () => {
        const w = await montar({ consultorio: 'Gimnasio' });
        await campo(w).setValue('');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(vi.mocked(api.put).mock.calls[0][1].consultorio).toBe('');
    });

    it('un grupo sin consultorio (null) se guarda enviando cadena vacía', async () => {
        const w = await montar({ consultorio: null });
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(vi.mocked(api.put).mock.calls[0][1].consultorio).toBe('');
    });

    it('el input referencia el aviso con aria-describedby solo si el grupo está visible', async () => {
        const oculto = await montar({ mostrar_en_pantalla: 0 });
        expect(campo(oculto).attributes('aria-describedby')).toBeUndefined();
        const visible = await montar({ mostrar_en_pantalla: 1 });
        expect(campo(visible).attributes('aria-describedby')).toBe('consultorio-ayuda');
        expect(visible.find('#consultorio-ayuda').text()).toContain('visible en la pantalla de llamados');
    });

    it('el recuadro de error tiene role alert', async () => {
        const w = await montar();
        vi.mocked(api.put).mockRejectedValueOnce({ response: { data: { error: 'Falla' } } });
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(w.find('[role="alert"]').text()).toContain('Falla');
    });

    it('muestra el 400 del backend con error', async () => {
        const w = await montar({ mostrar_en_pantalla: 1 });
        vi.mocked(api.put).mockRejectedValueOnce({ response: { data: { error: 'El grupo está visible en la pantalla de llamados: ocultalo antes de quitarle el consultorio' } } });
        await campo(w).setValue('');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(w.text()).toContain('ocultalo antes de quitarle el consultorio');
    });

    it('muestra el 400 del backend con message', async () => {
        const w = await montar();
        vi.mocked(api.put).mockRejectedValueOnce({ response: { data: { message: 'Rechazado por message' } } });
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(w.text()).toContain('Rechazado por message');
    });
});
