import { describe, it, expect, vi, beforeEach } from 'vitest';

const push = vi.fn();
let rutaActual = '/';
vi.mock('@/router', () => ({
    default: {
        push: (...a) => push(...a),
        currentRoute: {
            get value() {
                return { path: rutaActual };
            }
        }
    }
}));

import api from './axios';

async function simular401(path) {
    rutaActual = path;
    const handler = api.interceptors.response.handlers[0].rejected;
    await handler({ response: { status: 401 } }).catch(() => {});
}

describe('interceptor 401', () => {
    beforeEach(() => push.mockClear());

    it('en una página privada redirige al login', async () => {
        await simular401('/turnos');
        expect(push).toHaveBeenCalledWith('/auth/login');
    });
    it('en una ruta que solo empieza como /pantalla (administración) sí redirige al login', async () => {
        await simular401('/pantalla-de-llamados');
        expect(push).toHaveBeenCalledWith('/auth/login');
    });
    it('en /pantalla no redirige al login', async () => {
        await simular401('/pantalla');
        expect(push).not.toHaveBeenCalled();
    });
});
