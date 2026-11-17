import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@/service/pantallaService', () => ({
    default: { solicitarVinculacion: vi.fn(), obtenerLlamados: vi.fn() }
}));
vi.mock('@/utils/avisoSonoro', () => ({ reproducirAvisoSonoro: vi.fn() }));

import pantallaService from '@/service/pantallaService';
import { reproducirAvisoSonoro } from '@/utils/avisoSonoro';
import { usePantallaTV, CLAVE_STORAGE } from './usePantallaTV';

const tarjeta = (inicio) => ({ tipo: 'usuario', id: 1, nombre: 'Dra', consultorio: '3', siguientes: [], en_atencion: inicio ? [{ nombre: 'Ana G.', atencion_inicio: inicio }] : [] });

describe('usePantallaTV', () => {
    beforeEach(() => {
        vi.clearAllMocks();
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
        pantallaService.obtenerLlamados.mockResolvedValue({ data: { estado: 'vinculada', tarjetas: [tarjeta()] } });
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

    it('429 muestra el aviso de límite', async () => {
        pantallaService.solicitarVinculacion.mockRejectedValue({ response: { status: 429 } });
        const tv = usePantallaTV();
        await tv.ciclo();
        expect(tv.estado.value).toBe('limite');
    });

    it('suena solo con un llamado posterior a la primera carga y solo con sonido activado', async () => {
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockResolvedValueOnce({ data: { estado: 'vinculada', tarjetas: [tarjeta('2026-11-16T10:00:00')] } });
        await tv.ciclo();
        expect(reproducirAvisoSonoro).not.toHaveBeenCalled(); // primera carga

        pantallaService.obtenerLlamados.mockResolvedValueOnce({ data: { estado: 'vinculada', tarjetas: [tarjeta('2026-11-16T10:05:00')] } });
        await tv.ciclo();
        expect(reproducirAvisoSonoro).not.toHaveBeenCalled(); // sonido sin activar

        tv.activarSonido();
        expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(1); // el tono de prueba al activar
        pantallaService.obtenerLlamados.mockResolvedValueOnce({ data: { estado: 'vinculada', tarjetas: [tarjeta('2026-11-16T10:09:00')] } });
        await tv.ciclo();
        expect(reproducirAvisoSonoro).toHaveBeenCalledTimes(2);
    });

    it('un error de red solo oculta las tarjetas después de 30 s sin respuesta', async () => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockResolvedValueOnce({ data: { estado: 'vinculada', tarjetas: [tarjeta()] } });
        await tv.ciclo();
        pantallaService.obtenerLlamados.mockRejectedValue(new Error('network'));
        vi.advanceTimersByTime(10000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(false);
        expect(tv.tarjetas.value).toHaveLength(1); // sigue mostrando lo último
        vi.advanceTimersByTime(25000);
        await tv.ciclo();
        expect(tv.reconectando.value).toBe(true);
    });

    it('un pedido colgado no deja el ciclo bloqueado para siempre', async () => {
        vi.useFakeTimers();
        window.localStorage.setItem(CLAVE_STORAGE, 'k');
        const tv = usePantallaTV();
        pantallaService.obtenerLlamados.mockReturnValueOnce(new Promise(() => {})); // nunca responde
        const colgado = tv.ciclo();
        await vi.advanceTimersByTimeAsync(20000);
        await colgado;
        pantallaService.obtenerLlamados.mockResolvedValueOnce({ data: { estado: 'vinculada', tarjetas: [tarjeta()] } });
        await tv.ciclo();
        expect(tv.tarjetas.value).toHaveLength(1);
    });
});
