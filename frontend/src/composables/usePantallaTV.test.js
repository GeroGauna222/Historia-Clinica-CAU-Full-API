import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@/service/pantallaService', () => ({
    default: { solicitarVinculacion: vi.fn(), obtenerLlamados: vi.fn() }
}));
vi.mock('@/utils/avisoSonoro', () => ({ reproducirAvisoSonoro: vi.fn() }));

import pantallaService from '@/service/pantallaService';
import { reproducirAvisoSonoro } from '@/utils/avisoSonoro';
import { usePantallaTV, CLAVE_STORAGE } from './usePantallaTV';

const tarjeta = (inicio) => ({ tipo: 'usuario', id: 1, nombre: 'Dra', consultorio: '3', siguientes: [], en_atencion: inicio ? [{ nombre: 'Ana G.', atencion_inicio: inicio }] : [] });
const vinculada = (...tarjetas) => ({ data: { estado: 'vinculada', tarjetas } });
const diferido = () => {
    let resolver;
    const promesa = new Promise((resolve) => {
        resolver = resolve;
    });
    return { promesa, resolver };
};

describe('usePantallaTV', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        window.localStorage.clear();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('sin clave guardada pide vinculación y muestra el código', async () => {
        pantallaService.solicitarVinculacion.mockResolvedValue({ data: { codigo: 'K7M2QX', clave: 'clave-1' } });
        pantallaService.obtenerLlamados.mockResolvedValue({ data: { estado: 'pendiente', codigo: 'K7M2QX' } });
        const tv = usePantallaTV();
        await tv.ciclo();
        expect(window.localStorage.getItem(CLAVE_STORAGE)).toBe('clave-1');
        expect(tv.estado.value).toBe('pendiente');
        expect(tv.codigo.value).toBe('K7M2QX');
    });

    it('con clave guardada no pide otra vinculación', async () => {
        window.localStorage.setItem(CLAVE_STORAGE, 'guardada');
        pantallaService.obtenerLlamados.mockResolvedValue(vinculada(tarjeta()));
        const tv = usePantallaTV();
        await tv.ciclo();
        expect(pantallaService.solicitarVinculacion).not.toHaveBeenCalled();
        expect(pantallaService.obtenerLlamados).toHaveBeenCalledWith('guardada');
        expect(tv.estado.value).toBe('vinculada');
        expect(tv.tarjetas.value).toHaveLength(1);
    });

    it('401 borra la clave y vuelve a empezar', async () => {
        window.localStorage.setItem(CLAVE_STORAGE, 'revocada');
        pantallaService.obtenerLlamados.mockRejectedValue({ response: { status: 401 } });
        const tv = usePantallaTV();
        await tv.ciclo();
        expect(window.localStorage.getItem(CLAVE_STORAGE)).toBeNull();
        expect(tv.estado.value).toBe('iniciando');
        expect(tv.tarjetas.value).toEqual([]);
    });

    it('tras un 401 el ciclo siguiente pide una vinculación nueva y muestra el código nuevo', async () => {
        window.localStorage.setItem(CLAVE_STORAGE, 'revocada');
        pantallaService.obtenerLlamados.mockRejectedValueOnce({ response: { status: 401 } });
        const tv = usePantallaTV();
        await tv.ciclo();
        expect(pantallaService.solicitarVinculacion).not.toHaveBeenCalled();

        pantallaService.solicitarVinculacion.mockResolvedValue({ data: { codigo: 'NUEVO1', clave: 'clave-2' } });
        pantallaService.obtenerLlamados.mockResolvedValue({ data: { estado: 'pendiente', codigo: 'NUEVO1' } });
        await tv.ciclo();
        expect(pantallaService.solicitarVinculacion).toHaveBeenCalledTimes(1);
        expect(pantallaService.obtenerLlamados).toHaveBeenLastCalledWith('clave-2');
        expect(window.localStorage.getItem(CLAVE_STORAGE)).toBe('clave-2');
        expect(tv.estado.value).toBe('pendiente');
        expect(tv.codigo.value).toBe('NUEVO1');
    });

    it('429 al pedir la vinculación muestra el aviso de límite', async () => {
        pantallaService.solicitarVinculacion.mockRejectedValue({ response: { status: 429 } });
        const tv = usePantallaTV();
        await tv.ciclo();
        expect(tv.estado.value).toBe('limite');
    });

    it('429 al consultar los llamados no muestra el límite: se trata como falta de respuesta', async () => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta()));
        await tv.ciclo();
        pantallaService.obtenerLlamados.mockRejectedValue({ response: { status: 429 } });

        vi.advanceTimersByTime(10000);
        await tv.ciclo();
        expect(tv.estado.value).toBe('vinculada');
        expect(tv.tarjetas.value).toHaveLength(1);
        expect(tv.reconectando.value).toBe(false);

        vi.advanceTimersByTime(25000);
        await tv.ciclo();
        expect(tv.estado.value).toBe('vinculada');
        expect(tv.reconectando.value).toBe(true);
    });

    it('suena solo con un llamado posterior a la primera carga y solo con sonido activado', async () => {
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:00:00')));
        await tv.ciclo();
        expect(reproducirAvisoSonoro).not.toHaveBeenCalled(); // primera carga

        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:05:00')));
        await tv.ciclo();
        expect(reproducirAvisoSonoro).not.toHaveBeenCalled(); // sonido sin activar

        tv.activarSonido();
        expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(1); // el tono de prueba al activar
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:09:00')));
        await tv.ciclo();
        expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(2);
    });

    it('al pasar de pendiente a vinculada la primera carga vinculada no suena', async () => {
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        tv.activarSonido();
        expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(1);

        pantallaService.obtenerLlamados.mockResolvedValueOnce({ data: { estado: 'pendiente', codigo: 'K7M2QX' } });
        await tv.ciclo();
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:00:00')));
        await tv.ciclo();
        expect(tv.estado.value).toBe('vinculada');
        expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(1);
    });

    it('un error de red no marca reconectando antes de 30 s y las tarjetas siguen visibles', async () => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta()));
        await tv.ciclo();
        pantallaService.obtenerLlamados.mockRejectedValue(new Error('network'));
        vi.advanceTimersByTime(10000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(false);
        expect(tv.tarjetas.value).toHaveLength(1); // sigue mostrando lo último
        vi.advanceTimersByTime(25000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(true);
        expect(tv.tarjetas.value).toHaveLength(1);
    });

    it('reconectando vuelve a false cuando una consulta tiene éxito', async () => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockRejectedValue(new Error('network'));
        vi.advanceTimersByTime(31000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(true);

        pantallaService.obtenerLlamados.mockResolvedValue(vinculada(tarjeta()));
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(false);
    });

    it.each([
        ['estado desconocido', { estado: 'raro', tarjetas: [] }],
        ['vinculada sin arreglo de tarjetas', { estado: 'vinculada', tarjetas: 'no soy un arreglo' }],
        ['vinculada sin tarjetas', { estado: 'vinculada' }],
        ['pendiente sin código', { estado: 'pendiente' }],
        ['sin cuerpo', undefined]
    ])('una respuesta inesperada (%s) no vacía las tarjetas y termina en reconectando', async (_nombre, data) => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta()));
        await tv.ciclo();

        pantallaService.obtenerLlamados.mockResolvedValue({ data });
        vi.advanceTimersByTime(10000);
        await tv.ciclo();
        expect(tv.tarjetas.value).toHaveLength(1);
        expect(tv.estado.value).toBe('vinculada');
        expect(tv.reconectando.value).toBe(false);

        vi.advanceTimersByTime(25000);
        await tv.ciclo();
        expect(tv.tarjetas.value).toHaveLength(1);
        expect(tv.reconectando.value).toBe(true);
    });

    it('un 401 cuenta como respuesta del servidor: apaga reconectando y reinicia la cuenta de 30 s', async () => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockRejectedValue(new Error('network'));
        vi.advanceTimersByTime(31000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(true);

        pantallaService.obtenerLlamados.mockRejectedValue({ response: { status: 401 } });
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(false);

        pantallaService.solicitarVinculacion.mockRejectedValue(new Error('network'));
        vi.advanceTimersByTime(10000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(false);
    });

    it('un 429 al vincular cuenta como respuesta del servidor: apaga reconectando y reinicia la cuenta de 30 s', async () => {
        vi.useFakeTimers();
        const tv = usePantallaTV();
        pantallaService.solicitarVinculacion.mockRejectedValue(new Error('network'));
        vi.advanceTimersByTime(31000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(true);

        pantallaService.solicitarVinculacion.mockRejectedValue({ response: { status: 429 } });
        await tv.ciclo();
        expect(tv.estado.value).toBe('limite');
        expect(tv.reconectando.value).toBe(false);

        pantallaService.solicitarVinculacion.mockRejectedValue(new Error('network'));
        vi.advanceTimersByTime(10000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(false);
    });

    it('un pedido colgado no deja el ciclo bloqueado para siempre', async () => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockReturnValueOnce(new Promise(() => {})); // nunca responde
        const colgado = tv.ciclo();
        await vi.advanceTimersByTimeAsync(20000);
        await colgado;
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta()));
        await tv.ciclo();
        expect(tv.tarjetas.value).toHaveLength(1);
    });

    it('dos ciclos simultáneos hacen un solo pedido', async () => {
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const d = diferido();
        pantallaService.obtenerLlamados.mockReturnValue(d.promesa);
        const tv = usePantallaTV();
        const a = tv.ciclo();
        const b = tv.ciclo();
        d.resolver(vinculada(tarjeta()));
        await Promise.all([a, b]);
        expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(1);
    });

    it.each([
        ['sin clave', {}],
        ['clave vacía', { clave: '' }],
        ['clave que no es texto', { clave: 5 }]
    ])('una vinculación con respuesta inesperada (%s) no guarda nada y termina en reconectando', async (_nombre, data) => {
        vi.useFakeTimers();
        pantallaService.solicitarVinculacion.mockResolvedValue({ data });
        const tv = usePantallaTV();
        await tv.ciclo();
        expect(window.localStorage.getItem(CLAVE_STORAGE)).toBeNull();
        expect(pantallaService.obtenerLlamados).not.toHaveBeenCalled();
        expect(tv.reconectando.value).toBe(false);

        vi.advanceTimersByTime(31000);
        await tv.ciclo();
        expect(window.localStorage.getItem(CLAVE_STORAGE)).toBeNull();
        expect(pantallaService.obtenerLlamados).not.toHaveBeenCalled();
        expect(tv.reconectando.value).toBe(true);
    });

    // En ambos casos el televisor se re-vincula y los llamados que ya estaban en pantalla no deben sonar como nuevos:
    // la primera carga vinculada después del reinicio es "primera carga". Se usan llamados distintos a los previos
    // porque con los mismos el resultado sería igual aunque `vistos` no se reiniciara.
    it.each([
        [
            '401',
            () => {
                pantallaService.obtenerLlamados.mockRejectedValueOnce({ response: { status: 401 } });
                pantallaService.solicitarVinculacion.mockResolvedValueOnce({ data: { codigo: 'NUEVO1', clave: 'clave-2' } });
            }
        ],
        ['pendiente', () => pantallaService.obtenerLlamados.mockResolvedValueOnce({ data: { estado: 'pendiente', codigo: 'K7M2QX' } })]
    ])('después de un %s la primera carga vinculada no suena', async (_nombre, interrumpir) => {
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        tv.activarSonido();
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:00:00')));
        await tv.ciclo(); // (a) vinculada con llamados
        interrumpir();
        await tv.ciclo(); // (b) 401 o pendiente
        pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:30:00')));
        await tv.ciclo(); // (c) vinculada con llamados (tras el 401 este ciclo antes pide una vinculación nueva)
        expect(tv.estado.value).toBe('vinculada');
        expect(tv.tarjetas.value[0].en_atencion[0].atencion_inicio).toBe('2026-11-16T10:30:00');
        expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(1); // solo el tono de prueba de activarSonido
    });

    describe('iniciar / detener', () => {
        it('consulta de inmediato y luego cada 5 s', async () => {
            vi.useFakeTimers();
            window.localStorage.setItem(CLAVE_STORAGE, 'k');
            pantallaService.obtenerLlamados.mockResolvedValue(vinculada(tarjeta()));
            const tv = usePantallaTV();
            tv.iniciar();
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(1);
            for (let i = 0; i < 3; i++) await vi.advanceTimersByTimeAsync(5000);
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(4);
            tv.detener();
        });

        it('iniciar dos veces no duplica el intervalo', async () => {
            vi.useFakeTimers();
            window.localStorage.setItem(CLAVE_STORAGE, 'k');
            pantallaService.obtenerLlamados.mockResolvedValue(vinculada(tarjeta()));
            const tv = usePantallaTV();
            tv.iniciar();
            tv.iniciar();
            await vi.advanceTimersByTimeAsync(0);
            expect(vi.getTimerCount()).toBe(1);
            await vi.advanceTimersByTimeAsync(5000);
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(2);
            tv.detener();
            expect(vi.getTimerCount()).toBe(0);
        });

        it('después de detener no hay más consultas', async () => {
            vi.useFakeTimers();
            window.localStorage.setItem(CLAVE_STORAGE, 'k');
            pantallaService.obtenerLlamados.mockResolvedValue(vinculada(tarjeta()));
            const tv = usePantallaTV();
            tv.iniciar();
            await vi.advanceTimersByTimeAsync(5000);
            tv.detener();
            const llamadas = pantallaService.obtenerLlamados.mock.calls.length;
            await vi.advanceTimersByTimeAsync(20000);
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(llamadas);
        });

        it('un ciclo en vuelo que resuelve después de detener no cambia tarjetas ni suena', async () => {
            window.localStorage.setItem(CLAVE_STORAGE, 'k');
            const tv = usePantallaTV();
            pantallaService.obtenerLlamados.mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:00:00')));
            await tv.ciclo();
            tv.activarSonido();
            expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(1);

            const d = diferido();
            pantallaService.obtenerLlamados.mockReturnValueOnce(d.promesa);
            const enVuelo = tv.ciclo();
            tv.detener();
            d.resolver(vinculada(tarjeta('2026-11-16T10:09:00')));
            await enVuelo;

            expect(tv.tarjetas.value[0].en_atencion[0].atencion_inicio).toBe('2026-11-16T10:00:00');
            expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(1);
        });

        it('se puede volver a iniciar después de detener: consulta de nuevo y el intervalo sigue activo', async () => {
            vi.useFakeTimers();
            window.localStorage.setItem(CLAVE_STORAGE, 'k');
            pantallaService.obtenerLlamados
                .mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:00:00')))
                .mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:05:00')))
                .mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:10:00')));
            const tv = usePantallaTV();
            tv.iniciar();
            await vi.advanceTimersByTimeAsync(0);
            tv.detener();
            expect(vi.getTimerCount()).toBe(0);

            tv.iniciar();
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(2);
            await vi.advanceTimersByTimeAsync(0);
            expect(tv.tarjetas.value[0].en_atencion[0].atencion_inicio).toBe('2026-11-16T10:05:00');
            expect(vi.getTimerCount()).toBe(1);

            await vi.advanceTimersByTimeAsync(5000);
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(3);
            expect(tv.tarjetas.value[0].en_atencion[0].atencion_inicio).toBe('2026-11-16T10:10:00');
            tv.detener();
        });

        // Decisión: si el pedido viejo sigue en vuelo cuando se vuelve a iniciar, `activo` ya es true y su resultado se aplica.
        // No es un problema: es una respuesta real del servidor para la misma clave, apenas unos segundos vieja, y la
        // siguiente consulta la reemplaza. Mientras el pedido viejo no termina, `enCurso` hace que el ciclo inmediato del
        // nuevo `iniciar()` salga sin consultar; el televisor se recupera en el siguiente tick de 5 s.
        it('si se reinicia con un pedido viejo en vuelo, el viejo se aplica al resolver y el siguiente tick consulta de nuevo', async () => {
            vi.useFakeTimers();
            window.localStorage.setItem(CLAVE_STORAGE, 'k');
            const viejo = diferido();
            pantallaService.obtenerLlamados.mockReturnValueOnce(viejo.promesa).mockResolvedValueOnce(vinculada(tarjeta('2026-11-16T10:10:00')));
            const tv = usePantallaTV();
            tv.iniciar();
            tv.detener();
            tv.iniciar();
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(1); // el ciclo nuevo salió por `enCurso`
            expect(vi.getTimerCount()).toBeGreaterThanOrEqual(1);

            viejo.resolver(vinculada(tarjeta('2026-11-16T10:00:00')));
            await vi.advanceTimersByTimeAsync(0);
            expect(tv.estado.value).toBe('vinculada');
            expect(tv.tarjetas.value[0].en_atencion[0].atencion_inicio).toBe('2026-11-16T10:00:00');

            await vi.advanceTimersByTimeAsync(5000);
            expect(pantallaService.obtenerLlamados).toHaveBeenCalledTimes(2);
            expect(tv.tarjetas.value[0].en_atencion[0].atencion_inicio).toBe('2026-11-16T10:10:00');
            tv.detener();
        });

        it('iniciar apaga reconectando y reinicia la cuenta de 30 s', async () => {
            vi.useFakeTimers();
            window.localStorage.setItem(CLAVE_STORAGE, 'k');
            pantallaService.obtenerLlamados.mockRejectedValue(new Error('network'));
            const tv = usePantallaTV();
            vi.advanceTimersByTime(31000);
            await tv.ciclo();
            expect(tv.reconectando.value).toBe(true);

            pantallaService.obtenerLlamados.mockReturnValue(new Promise(() => {})); // el pedido nuevo no responde (todavía)
            tv.iniciar();
            expect(tv.reconectando.value).toBe(false);
            tv.detener();
        });

        it('una vinculación en vuelo que resuelve después de detener no guarda la clave', async () => {
            const d = diferido();
            pantallaService.solicitarVinculacion.mockReturnValue(d.promesa);
            const tv = usePantallaTV();
            const enVuelo = tv.ciclo();
            tv.detener();
            d.resolver({ data: { codigo: 'K7M2QX', clave: 'clave-1' } });
            await enVuelo;
            expect(window.localStorage.getItem(CLAVE_STORAGE)).toBeNull();
            expect(pantallaService.obtenerLlamados).not.toHaveBeenCalled();
        });
    });
});
