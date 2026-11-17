import { describe, it, expect } from 'vitest';
import { esRutaPublica, requiereSesion } from './accesoRutas';

describe('accesoRutas', () => {
    it('las páginas de acceso son públicas', () => {
        for (const path of ['/auth/login', '/recuperar', '/logout', '/reset/abc123']) {
            expect(esRutaPublica({ path, meta: {} })).toBe(true);
        }
    });
    it('una ruta con meta.publica es pública sin importar cómo se escriba la dirección', () => {
        for (const path of ['/pantalla', '/pantalla/', '/Pantalla']) {
            expect(requiereSesion({ path, meta: { publica: true } })).toBe(false);
        }
    });
    it('una ruta sin la meta requiere sesión, aunque su dirección se parezca a una pública', () => {
        expect(requiereSesion({ path: '/pantalla-de-llamados', meta: {} })).toBe(true);
        expect(requiereSesion({ path: '/turnos', meta: {} })).toBe(true);
        expect(requiereSesion({ path: '/turnos' })).toBe(true);
    });
});
