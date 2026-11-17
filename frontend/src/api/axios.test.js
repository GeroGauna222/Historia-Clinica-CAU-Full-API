import { describe, it, expect, vi, beforeEach } from 'vitest';

const push = vi.fn();
let rutaActual = { path: '/' };
vi.mock('@/router', () => ({
    default: {
        push: (...a) => push(...a),
        currentRoute: {
            get value() {
                return rutaActual;
            }
        }
    }
}));

import api from './axios';

async function simular401(path, meta = {}) {
    rutaActual = { path, meta };
    const handler = api.interceptors.response.handlers[0].rejected;
    await handler({ response: { status: 401 } }).catch(() => {});
}

describe('interceptor 401', () => {
    beforeEach(() => push.mockClear());

    it('en una página privada redirige al login', async () => {
        await simular401('/turnos');
        expect(push).toHaveBeenCalledWith('/auth/login');
    });
    it('en una ruta que solo empieza como /pantalla pero no es pública (administración) sí redirige al login', async () => {
        await simular401('/pantalla-de-llamados');
        expect(push).toHaveBeenCalledWith('/auth/login');
    });
    it('en una ruta con meta.publica (/pantalla) no redirige al login', async () => {
        await simular401('/pantalla', { publica: true });
        expect(push).not.toHaveBeenCalled();
    });
    it('tampoco redirige con barra final o distinto caso, porque lo decide la meta de la ruta', async () => {
        await simular401('/pantalla/', { publica: true });
        await simular401('/Pantalla', { publica: true });
        expect(push).not.toHaveBeenCalled();
    });
    it('sigue sin redirigir en el login', async () => {
        await simular401('/auth/login');
        expect(push).not.toHaveBeenCalled();
    });
});
