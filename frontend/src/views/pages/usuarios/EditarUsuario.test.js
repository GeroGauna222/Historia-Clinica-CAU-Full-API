import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, enableAutoUnmount, flushPromises } from '@vue/test-utils';
import PrimeVue from 'primevue/config';

const toastAdd = vi.fn();
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }));
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '5' } }) }));
vi.mock('@/service/usuarioService', () => ({
    default: {
        getUsuario: vi.fn(),
        updateUsuario: vi.fn()
    }
}));

import usuarioService from '@/service/usuarioService';
import EditarUsuario from './EditarUsuario.vue';

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

const USUARIO = { id: 5, nombre: 'Dra. Pérez', username: 'perez', email: 'p@cau.test', rol: 'profesional', especialidad: 'KINESIOLOGIA', consultorio: '3' };

async function montar(usuario) {
    vi.mocked(usuarioService.getUsuario).mockResolvedValue({ data: { ...USUARIO, ...usuario } });
    const w = mount(EditarUsuario, { global: { plugins: [[PrimeVue, { theme: 'none' }]] } });
    await flushPromises();
    return w;
}

const campo = (w) => w.find('input#consultorio');

describe('EditarUsuario - campo Consultorio', () => {
    beforeEach(() => {
        toastAdd.mockReset();
        vi.mocked(usuarioService.getUsuario).mockReset();
        vi.mocked(usuarioService.updateUsuario)
            .mockReset()
            .mockResolvedValue({ data: { message: 'ok' } });
    });

    it.each(['profesional', 'area'])('se muestra para el rol %s', async (rol) => {
        const w = await montar({ rol });
        expect(campo(w).exists()).toBe(true);
    });

    it.each(['director', 'administrativo'])('no se muestra para el rol %s', async (rol) => {
        const w = await montar({ rol, consultorio: null });
        expect(campo(w).exists()).toBe(false);
    });

    it('carga el consultorio del backend', async () => {
        const w = await montar({ consultorio: 'Gimnasio' });
        expect(campo(w).element.value).toBe('Gimnasio');
    });

    it('un consultorio null del backend se muestra vacío', async () => {
        const w = await montar({ consultorio: null });
        expect(campo(w).element.value).toBe('');
    });

    it('un consultorio ausente en la respuesta se muestra vacío', async () => {
        const w = await montar({ consultorio: undefined });
        expect(campo(w).element.value).toBe('');
    });

    it('el PUT envía el consultorio editado', async () => {
        const w = await montar({ consultorio: null });
        await campo(w).setValue('4B');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(usuarioService.updateUsuario).toHaveBeenCalledTimes(1);
        const [id, payload] = vi.mocked(usuarioService.updateUsuario).mock.calls[0];
        expect(id).toBe('5');
        expect(payload.consultorio).toBe('4B');
    });

    it('el PUT envía cadena vacía cuando se borra el consultorio (el backend la guarda como NULL)', async () => {
        const w = await montar({ consultorio: '3' });
        await campo(w).setValue('');
        await w.find('form').trigger('submit');
        await flushPromises();
        const payload = vi.mocked(usuarioService.updateUsuario).mock.calls[0][1];
        expect(payload.consultorio).toBe('');
    });

    it('al cambiar a un rol que no usa consultorio el PUT envía consultorio vacío', async () => {
        const w = await montar({ rol: 'profesional', consultorio: '3' });
        w.findComponent({ name: 'Select' }).vm.$emit('update:modelValue', 'director');
        await flushPromises();
        expect(campo(w).exists()).toBe(false);
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(vi.mocked(usuarioService.updateUsuario).mock.calls[0][1].consultorio).toBe('');
    });

    it('volver a profesional antes de guardar conserva el consultorio', async () => {
        const w = await montar({ rol: 'profesional', consultorio: '3' });
        const select = w.findComponent({ name: 'Select' });
        select.vm.$emit('update:modelValue', 'director');
        await flushPromises();
        select.vm.$emit('update:modelValue', 'profesional');
        await flushPromises();
        expect(campo(w).element.value).toBe('3');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(vi.mocked(usuarioService.updateUsuario).mock.calls[0][1].consultorio).toBe('3');
    });

    it('el consultorio tipeado con espacios se envía recortado', async () => {
        const w = await montar({ consultorio: null });
        await campo(w).setValue('  4B  ');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(vi.mocked(usuarioService.updateUsuario).mock.calls[0][1].consultorio).toBe('4B');
    });

    it('muestra el 400 del backend leyendo error o message', async () => {
        const w = await montar({});
        vi.mocked(usuarioService.updateUsuario).mockRejectedValueOnce({ response: { data: { error: 'El consultorio no puede superar los 50 caracteres' } } });
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(toastAdd).toHaveBeenLastCalledWith(expect.objectContaining({ severity: 'error', detail: 'El consultorio no puede superar los 50 caracteres' }));

        vi.mocked(usuarioService.updateUsuario).mockRejectedValueOnce({ response: { data: { message: 'Rechazado por message' } } });
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(toastAdd).toHaveBeenLastCalledWith(expect.objectContaining({ severity: 'error', detail: 'Rechazado por message' }));
    });
});
