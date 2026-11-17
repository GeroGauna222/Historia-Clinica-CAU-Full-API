import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, enableAutoUnmount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PrimeVue from 'primevue/config';

vi.mock('@/service/pantallaService', () => ({
    default: {
        vistaPrevia: vi.fn(),
        listarVisibles: vi.fn(),
        actualizarVisible: vi.fn(),
        listarTelevisores: vi.fn(),
        vincularTelevisor: vi.fn(),
        desvincularTelevisor: vi.fn()
    }
}));

import pantallaService from '@/service/pantallaService';
import { useUserStore } from '@/stores/user';
import PantallaLlamados from './PantallaLlamados.vue';

enableAutoUnmount(afterEach);

// jsdom no trae ResizeObserver y TabList de PrimeVue lo usa para el desplazamiento de las pestañas.
vi.stubGlobal(
    'ResizeObserver',
    class {
        observe() {}
        unobserve() {}
        disconnect() {}
    }
);

const FILAS = [
    { tipo: 'profesional', id: 1, nombre: 'Dra. Pérez', consultorio: '3', mostrar_en_pantalla: true, tiene_turnos_hoy: true },
    { tipo: 'grupo', id: 1, nombre: 'Rehabilitación', consultorio: 'Gimnasio', mostrar_en_pantalla: false, tiene_turnos_hoy: true },
    { tipo: 'profesional', id: 2, nombre: 'Dr. Gómez', consultorio: null, mostrar_en_pantalla: false, tiene_turnos_hoy: false }
];
const TELEVISORES = [{ id: 7, nombre: 'Sala de espera', vinculada_en: '2026-11-16T09:30:00', ultimo_acceso: null }];

function montar(rol = 'director') {
    setActivePinia(createPinia());
    useUserStore().rol = rol;
    return mount(PantallaLlamados, { attachTo: document.body, global: { plugins: [[PrimeVue, { theme: 'none' }]] } });
}

const campoConsultorio = (w, nombre) => w.find(`input[aria-label="Consultorio de ${nombre}"]`);
const interruptor = (w, nombre) => w.find(`input[aria-label="Mostrar ${nombre} en la pantalla"]`);

describe('PantallaLlamados', () => {
    beforeEach(() => {
        vi.mocked(pantallaService.vistaPrevia)
            .mockReset()
            .mockResolvedValue({ data: { tarjetas: [] } });
        vi.mocked(pantallaService.listarVisibles)
            .mockReset()
            .mockResolvedValue({ data: FILAS.map((f) => ({ ...f })) });
        vi.mocked(pantallaService.listarTelevisores).mockReset().mockResolvedValue({ data: TELEVISORES });
        vi.mocked(pantallaService.actualizarVisible).mockReset();
        vi.mocked(pantallaService.vincularTelevisor)
            .mockReset()
            .mockResolvedValue({ data: { message: 'Televisor vinculado' } });
        vi.mocked(pantallaService.desvincularTelevisor)
            .mockReset()
            .mockResolvedValue({ data: { message: 'Televisor desvinculado' } });
        vi.spyOn(window, 'confirm').mockReturnValue(true);
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it('carga la vista previa, los visibles y los televisores al montar', async () => {
        const w = montar();
        await flushPromises();
        expect(pantallaService.vistaPrevia).toHaveBeenCalledTimes(1);
        expect(pantallaService.listarVisibles).toHaveBeenCalledTimes(1);
        expect(pantallaService.listarTelevisores).toHaveBeenCalledTimes(1);
        expect(w.text()).toContain('Dra. Pérez');
        expect(w.text()).toContain('Rehabilitación');
        expect(w.text()).toContain('Sala de espera');
    });

    it('el administrativo no ve la pestaña Televisores ni pide la lista', async () => {
        const w = montar('administrativo');
        await flushPromises();
        expect(w.text()).not.toContain('Televisores');
        expect(w.find('#codigo-tv').exists()).toBe(false);
        expect(pantallaService.listarTelevisores).not.toHaveBeenCalled();
        expect(pantallaService.listarVisibles).toHaveBeenCalledTimes(1);
    });

    it('el director ve la pestaña Televisores', async () => {
        const w = montar('director');
        await flushPromises();
        expect(w.text()).toContain('Televisores');
        expect(w.find('#codigo-tv').exists()).toBe(true);
    });

    it('la vista previa usa la paleta del televisor', async () => {
        const w = montar();
        await flushPromises();
        expect(w.find('.previa').classes()).toContain('pantalla-paleta');
    });

    it('cambiar el consultorio guarda { consultorio } y actualiza la vista previa', async () => {
        vi.mocked(pantallaService.actualizarVisible).mockResolvedValue({ data: { consultorio: '5', mostrar_en_pantalla: true } });
        const w = montar();
        await flushPromises();
        const campo = campoConsultorio(w, 'Dra. Pérez');
        campo.element.value = '5';
        await campo.trigger('change');
        await flushPromises();
        expect(pantallaService.actualizarVisible).toHaveBeenCalledWith('profesional', 1, { consultorio: '5' });
        expect(pantallaService.vistaPrevia).toHaveBeenCalledTimes(2);
    });

    it('el interruptor guarda { mostrar_en_pantalla } y distingue grupo de profesional con el mismo id', async () => {
        vi.mocked(pantallaService.actualizarVisible).mockResolvedValue({ data: { consultorio: 'Gimnasio', mostrar_en_pantalla: true } });
        const w = montar();
        await flushPromises();
        await interruptor(w, 'Rehabilitación').trigger('click');
        await flushPromises();
        expect(pantallaService.actualizarVisible).toHaveBeenCalledWith('grupo', 1, { mostrar_en_pantalla: true });
    });

    it('un error del PATCH con `message` se muestra, recarga los visibles y el interruptor vuelve al valor real', async () => {
        vi.mocked(pantallaService.actualizarVisible).mockRejectedValue({ response: { data: { message: 'El cuerpo de la solicitud debe ser un objeto JSON' } } });
        const w = montar();
        await flushPromises();
        const antes = vi.mocked(pantallaService.listarVisibles).mock.calls.length;
        expect(interruptor(w, 'Rehabilitación').element.checked).toBe(false);

        await interruptor(w, 'Rehabilitación').trigger('click');
        await flushPromises();

        expect(w.text()).toContain('El cuerpo de la solicitud debe ser un objeto JSON');
        expect(pantallaService.listarVisibles.mock.calls.length).toBe(antes + 1);
        expect(interruptor(w, 'Rehabilitación').element.checked).toBe(false);
    });

    it('un error del PATCH con `error` también se muestra, y el campo de consultorio recupera el valor real', async () => {
        vi.mocked(pantallaService.actualizarVisible).mockRejectedValue({ response: { data: { error: 'Un grupo necesita consultorio para estar visible en la pantalla' } } });
        const w = montar();
        await flushPromises();
        const campo = campoConsultorio(w, 'Rehabilitación');
        campo.element.value = '';
        await campo.trigger('change');
        await flushPromises();
        expect(w.text()).toContain('Un grupo necesita consultorio para estar visible en la pantalla');
        expect(campoConsultorio(w, 'Rehabilitación').element.value).toBe('Gimnasio');
    });

    it('avisa de quienes tienen turnos hoy y no se ven en la pantalla', async () => {
        const w = montar();
        await flushPromises();
        const aviso = w.text();
        expect(aviso).toContain('Tienen turnos hoy y no se ven en la pantalla: Rehabilitación');
        expect(aviso).not.toContain('pantalla: Rehabilitación, Dr. Gómez');
        expect(aviso).not.toContain('pantalla: Dr. Gómez');
    });

    it('no muestra el aviso si nadie oculto tiene turnos hoy', async () => {
        vi.mocked(pantallaService.listarVisibles).mockResolvedValue({ data: [{ ...FILAS[2] }] });
        const w = montar();
        await flushPromises();
        expect(w.text()).not.toContain('Tienen turnos hoy');
    });

    it('vincular llama al servicio, limpia los campos y recarga los televisores', async () => {
        const w = montar();
        await flushPromises();
        await w.find('#codigo-tv').setValue('AB12CD');
        await w.find('#nombre-tv').setValue('Recepción');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(pantallaService.vincularTelevisor).toHaveBeenCalledWith({ codigo: 'AB12CD', nombre: 'Recepción' });
        expect(w.find('#codigo-tv').element.value).toBe('');
        expect(w.find('#nombre-tv').element.value).toBe('');
        expect(pantallaService.listarTelevisores).toHaveBeenCalledTimes(2);
    });

    it('vincular con un código inválido muestra el error y conserva lo escrito', async () => {
        vi.mocked(pantallaService.vincularTelevisor).mockRejectedValue({ response: { data: { error: 'Código inválido o vencido' } } });
        const w = montar();
        await flushPromises();
        await w.find('#codigo-tv').setValue('ZZZZZZ');
        await w.find('#nombre-tv').setValue('Recepción');
        await w.find('form').trigger('submit');
        await flushPromises();
        expect(w.text()).toContain('Código inválido o vencido');
        expect(w.find('#codigo-tv').element.value).toBe('ZZZZZZ');
    });

    it('el botón Vincular está deshabilitado hasta completar código y nombre', async () => {
        const w = montar();
        await flushPromises();
        const boton = () => w.find('form button[type="submit"]');
        expect(boton().attributes('disabled')).toBeDefined();
        await w.find('#codigo-tv').setValue('AB12CD');
        expect(boton().attributes('disabled')).toBeDefined();
        await w.find('#nombre-tv').setValue('Recepción');
        expect(boton().attributes('disabled')).toBeUndefined();
    });

    it('desvincular pide confirmación: si se cancela no llama al servicio', async () => {
        window.confirm.mockReturnValue(false);
        const w = montar();
        await flushPromises();
        await w.find('button[aria-label="Desvincular Sala de espera"]').trigger('click');
        await flushPromises();
        expect(window.confirm).toHaveBeenCalledTimes(1);
        expect(pantallaService.desvincularTelevisor).not.toHaveBeenCalled();
    });

    it('desvincular confirmado llama al servicio y recarga', async () => {
        const w = montar();
        await flushPromises();
        await w.find('button[aria-label="Desvincular Sala de espera"]').trigger('click');
        await flushPromises();
        expect(pantallaService.desvincularTelevisor).toHaveBeenCalledWith(7);
        expect(pantallaService.listarTelevisores).toHaveBeenCalledTimes(2);
    });

    describe('vista previa', () => {
        const TARJETA = { tipo: 'profesional', id: 1, nombre: 'Dra. Pérez', consultorio: '3', en_atencion: [{ nombre: 'Juan Gómez' }], siguientes: [{ nombre: 'Ana Ruiz' }] };

        it('renderiza dentro de .previa las tarjetas que devuelve vistaPrevia', async () => {
            vi.mocked(pantallaService.vistaPrevia).mockResolvedValue({ data: { tarjetas: [TARJETA] } });
            const w = montar();
            await flushPromises();
            const previa = w.find('.previa');
            expect(previa.text()).toContain('Juan Gómez');
            expect(previa.text()).toContain('Ana Ruiz');
        });

        it('es una región con nombre accesible', async () => {
            const w = montar();
            await flushPromises();
            const previa = w.find('.previa');
            expect(previa.attributes('role')).toBe('region');
            expect(previa.attributes('aria-label')).toBe('Vista previa de la pantalla del televisor');
        });

        it('muestra "Cargando…" hasta la primera respuesta y no el aviso de que no hay turnos', async () => {
            let resolver;
            vi.mocked(pantallaService.vistaPrevia).mockReturnValue(new Promise((r) => (resolver = r)));
            const w = montar();
            await flushPromises();
            expect(w.find('.previa').text()).toContain('Cargando');
            expect(w.find('.previa').text()).not.toContain('No hay turnos para mostrar');

            resolver({ data: { tarjetas: [] } });
            await flushPromises();
            expect(w.find('.previa').text()).not.toContain('Cargando');
            expect(w.find('.previa').text()).toContain('No hay turnos para mostrar');
        });

        it('si la primera respuesta es un error deja de decir "Cargando…"', async () => {
            vi.mocked(pantallaService.vistaPrevia).mockRejectedValue({});
            const w = montar();
            await flushPromises();
            expect(w.find('.previa').text()).not.toContain('Cargando');
        });
    });

    describe('errores de carga al montar', () => {
        it('listarVisibles con mensaje del servidor', async () => {
            vi.mocked(pantallaService.listarVisibles).mockRejectedValue({ response: { data: { error: 'Sin permisos' } } });
            const w = montar();
            await flushPromises();
            expect(w.text()).toContain('Sin permisos');
        });

        it('listarVisibles sin cuerpo de error usa el texto por defecto', async () => {
            vi.mocked(pantallaService.listarVisibles).mockRejectedValue(new Error('red'));
            const w = montar();
            await flushPromises();
            expect(w.text()).toContain('No se pudo cargar la lista');
        });

        it('listarTelevisores', async () => {
            vi.mocked(pantallaService.listarTelevisores).mockRejectedValue(new Error('red'));
            const w = montar();
            await flushPromises();
            expect(w.text()).toContain('No se pudo cargar la lista de televisores');
        });

        it('vistaPrevia', async () => {
            vi.mocked(pantallaService.vistaPrevia).mockRejectedValue(new Error('red'));
            const w = montar();
            await flushPromises();
            expect(w.text()).toContain('No se pudo cargar la vista previa');
        });
    });

    describe('carreras al guardar', () => {
        it('descarta una lista tardía aunque la edición que la hizo recargar haya terminado antes de que llegue', async () => {
            let resolverLista;
            vi.mocked(pantallaService.actualizarVisible)
                .mockRejectedValueOnce({ response: { data: { error: 'Falló' } } })
                .mockResolvedValueOnce({ data: { consultorio: null, mostrar_en_pantalla: true } });
            const w = montar();
            await flushPromises();
            // a partir de acá, la recarga que dispara el error queda pendiente
            vi.mocked(pantallaService.listarVisibles).mockReturnValueOnce(new Promise((r) => (resolverLista = r)));

            await interruptor(w, 'Rehabilitación').trigger('click'); // falla y pide recargar
            await flushPromises();
            await interruptor(w, 'Dr. Gómez').trigger('click'); // empieza y termina mientras la lista sigue en vuelo
            await flushPromises();
            expect(interruptor(w, 'Dr. Gómez').element.checked).toBe(true);

            resolverLista({ data: FILAS.map((f) => ({ ...f })) }); // la lista vieja todavía dice que Dr. Gómez está oculto
            await flushPromises();
            expect(interruptor(w, 'Dr. Gómez').element.checked).toBe(true);
        });
    });

    describe('consultorio', () => {
        it('vaciar el campo envía { consultorio: "" }', async () => {
            vi.mocked(pantallaService.actualizarVisible).mockResolvedValue({ data: { consultorio: null, mostrar_en_pantalla: true } });
            const w = montar();
            await flushPromises();
            const campo = campoConsultorio(w, 'Dra. Pérez');
            await campo.setValue('');
            await campo.trigger('change');
            await flushPromises();
            expect(pantallaService.actualizarVisible).toHaveBeenCalledWith('profesional', 1, { consultorio: '' });
        });

        it('si el servidor normaliza lo escrito, el campo muestra el valor real', async () => {
            vi.mocked(pantallaService.actualizarVisible).mockResolvedValue({ data: { consultorio: null, mostrar_en_pantalla: false } });
            const w = montar();
            await flushPromises();
            const campo = campoConsultorio(w, 'Dr. Gómez'); // sin consultorio: el modelo no cambia al volver null
            await campo.setValue('   ');
            await campo.trigger('change');
            await flushPromises();
            expect(pantallaService.actualizarVisible).toHaveBeenCalledWith('profesional', 2, { consultorio: '   ' });
            expect(campoConsultorio(w, 'Dr. Gómez').element.value).toBe('');
        });
    });

    describe('televisores', () => {
        const boton = (w) => w.find('form button[type="submit"]');

        it('vincular envía código y nombre sin espacios sobrantes', async () => {
            const w = montar();
            await flushPromises();
            await w.find('#codigo-tv').setValue('  AB12CD ');
            await w.find('#nombre-tv').setValue('  Recepción  ');
            await w.find('form').trigger('submit');
            await flushPromises();
            expect(pantallaService.vincularTelevisor).toHaveBeenCalledWith({ codigo: 'AB12CD', nombre: 'Recepción' });
        });

        it('campos con solo espacios no habilitan Vincular ni envían', async () => {
            const w = montar();
            await flushPromises();
            await w.find('#codigo-tv').setValue('   ');
            await w.find('#nombre-tv').setValue('   ');
            expect(boton(w).attributes('disabled')).toBeDefined();
            await w.find('form').trigger('submit');
            await flushPromises();
            expect(pantallaService.vincularTelevisor).not.toHaveBeenCalled();
        });

        it('un segundo envío mientras el primero sigue en curso se ignora', async () => {
            let resolver;
            vi.mocked(pantallaService.vincularTelevisor).mockReturnValue(new Promise((r) => (resolver = r)));
            const w = montar();
            await flushPromises();
            await w.find('#codigo-tv').setValue('AB12CD');
            await w.find('#nombre-tv').setValue('Recepción');
            await w.find('form').trigger('submit');
            await w.find('form').trigger('submit');
            expect(pantallaService.vincularTelevisor).toHaveBeenCalledTimes(1);
            resolver({ data: {} });
            await flushPromises();
            await w.find('#codigo-tv').setValue('ZZ99ZZ');
            await w.find('#nombre-tv').setValue('Otra');
            await w.find('form').trigger('submit');
            await flushPromises();
            expect(pantallaService.vincularTelevisor).toHaveBeenCalledTimes(2);
        });

        it('tras vincular con éxito el foco vuelve al campo de código', async () => {
            const w = montar();
            await flushPromises();
            await w.find('#codigo-tv').setValue('AB12CD');
            await w.find('#nombre-tv').setValue('Recepción');
            w.find('#nombre-tv').element.focus();
            await w.find('form').trigger('submit');
            await flushPromises();
            expect(document.activeElement).toBe(w.find('#codigo-tv').element);
        });

        it('tras un error al vincular el foco no se mueve', async () => {
            vi.mocked(pantallaService.vincularTelevisor).mockRejectedValue({ response: { data: { error: 'Código inválido o vencido' } } });
            const w = montar();
            await flushPromises();
            await w.find('#codigo-tv').setValue('AB12CD');
            await w.find('#nombre-tv').setValue('Recepción');
            w.find('#nombre-tv').element.focus();
            await w.find('form').trigger('submit');
            await flushPromises();
            expect(document.activeElement).toBe(w.find('#nombre-tv').element);
        });

        it('desvincular con error lo muestra y no recarga la lista', async () => {
            vi.mocked(pantallaService.desvincularTelevisor).mockRejectedValue({ response: { data: { error: 'Televisor no encontrado' } } });
            const w = montar();
            await flushPromises();
            await w.find('button[aria-label="Desvincular Sala de espera"]').trigger('click');
            await flushPromises();
            expect(w.text()).toContain('Televisor no encontrado');
            expect(pantallaService.listarTelevisores).toHaveBeenCalledTimes(1);
        });

        it('la columna de acciones tiene encabezado accesible', async () => {
            const w = montar();
            await flushPromises();
            const encabezados = w.findAll('th').map((th) => th.text());
            expect(encabezados).toContain('Acciones');
        });
    });

    describe('refresco de la vista previa', () => {
        it('se repite cada 5 segundos y el temporizador se limpia al desmontar', async () => {
            vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
            const w = montar();
            await flushPromises();
            expect(pantallaService.vistaPrevia).toHaveBeenCalledTimes(1);
            expect(vi.getTimerCount()).toBeGreaterThan(0);

            vi.advanceTimersByTime(5000);
            await flushPromises();
            expect(pantallaService.vistaPrevia).toHaveBeenCalledTimes(2);

            w.unmount();
            expect(vi.getTimerCount()).toBe(0);
            vi.advanceTimersByTime(20000);
            expect(pantallaService.vistaPrevia).toHaveBeenCalledTimes(2);
        });

        it('saltea el tick si el pedido anterior sigue en curso', async () => {
            vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
            let resolver;
            vi.mocked(pantallaService.vistaPrevia).mockReturnValue(new Promise((r) => (resolver = r)));
            montar();
            await flushPromises();
            vi.advanceTimersByTime(15000);
            await flushPromises();
            expect(pantallaService.vistaPrevia).toHaveBeenCalledTimes(1);

            resolver({ data: { tarjetas: [] } });
            await flushPromises();
            vi.advanceTimersByTime(5000);
            await flushPromises();
            expect(pantallaService.vistaPrevia).toHaveBeenCalledTimes(2);
        });

        it('un error de refresco no reemplaza el mensaje de una acción y desaparece al recuperarse', async () => {
            vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
            vi.mocked(pantallaService.actualizarVisible).mockRejectedValue({ response: { data: { error: 'No encontrado' } } });
            const w = montar();
            await flushPromises();

            await interruptor(w, 'Dr. Gómez').trigger('click');
            await flushPromises();
            expect(w.text()).toContain('No encontrado');

            vi.mocked(pantallaService.vistaPrevia).mockRejectedValue({ response: { data: { error: 'Sin conexión' } } });
            vi.advanceTimersByTime(5000);
            await flushPromises();
            expect(w.text()).toContain('No encontrado');
            expect(w.text()).not.toContain('Sin conexión');

            // al hacer otra acción se limpia el de acción y entonces se ve el de refresco
            vi.mocked(pantallaService.actualizarVisible).mockResolvedValue({ data: { consultorio: null, mostrar_en_pantalla: true } });
            await interruptor(w, 'Dr. Gómez').trigger('click');
            await flushPromises();
            expect(w.text()).toContain('Sin conexión');

            vi.mocked(pantallaService.vistaPrevia).mockResolvedValue({ data: { tarjetas: [] } });
            vi.advanceTimersByTime(5000);
            await flushPromises();
            expect(w.text()).not.toContain('Sin conexión');
        });
    });
});
