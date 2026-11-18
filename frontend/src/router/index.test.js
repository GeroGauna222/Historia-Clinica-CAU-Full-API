import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

vi.mock('@/layout/AppLayout.vue', () => ({ default: { render: () => null } }));
vi.mock('@/views/pages/pantalla/PantallaTV.vue', () => ({ default: { render: () => null } }));
vi.mock('@/views/pages/auth/Login.vue', () => ({ default: { render: () => null } }));

import router from './index';
import { useUserStore } from '@/stores/user';

describe('guard beforeEach', () => {
    let fetchUser;

    beforeEach(async () => {
        setActivePinia(createPinia());
        fetchUser = vi.spyOn(useUserStore(), 'fetchUser').mockResolvedValue(undefined);
        await router.push('/auth/login?logged_out=1');
        fetchUser.mockClear();
    });

    it.each(['/pantalla', '/pantalla/', '/Pantalla'])('%s no consulta la sesión ni redirige al login', async (path) => {
        await router.push(path);
        expect(router.currentRoute.value.name).toBe('pantalla');
        expect(fetchUser).not.toHaveBeenCalled();
    });

    it('una ruta privada sin sesión valida contra el backend y redirige al login', async () => {
        await router.push('/turnos');
        expect(fetchUser).toHaveBeenCalled();
        expect(router.currentRoute.value.path).toBe('/auth/login');
    });

    it('la administración de la pantalla de llamados no es pública: sin sesión redirige al login', async () => {
        const ruta = router.getRoutes().find((r) => r.name === 'pantalla-llamados');
        expect(ruta.meta.publica).toBeUndefined();
        expect(ruta.meta.roles).toEqual(['director', 'administrativo']);

        await router.push('/pantalla-de-llamados');
        expect(fetchUser).toHaveBeenCalled();
        expect(router.currentRoute.value.path).toBe('/auth/login');
    });
});
