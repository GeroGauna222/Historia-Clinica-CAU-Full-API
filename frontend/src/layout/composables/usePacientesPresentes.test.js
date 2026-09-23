import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

const mockGet = vi.fn();

vi.mock('@/api/axios', () => ({
    default: { get: (...args) => mockGet(...args) }
}));

const STORAGE_KEY = 'cau-arrival-acks';

function todayLocal() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function turno(id, overrides = {}) {
    return {
        id,
        paciente: `Paciente ${id}`,
        dni: '12345678',
        fecha_inicio: '2026-09-23T10:00:00',
        motivo: 'Control',
        ...overrides
    };
}

async function loadFresh() {
    vi.resetModules();
    return import('./usePacientesPresentes.js');
}

async function setupProfesional(userId = 7) {
    const { usePacientesPresentes } = await loadFresh();
    const { useUserStore } = await import('@/stores/user');
    const store = useUserStore();
    store.id = userId;
    store.rol = 'profesional';
    return { composable: usePacientesPresentes(), store };
}

describe('usePacientesPresentes', () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        mockGet.mockReset();
        try {
            window.localStorage.clear();
        } catch {
            // ignore
        }
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('adds a new present turno to pendientes for a profesional', async () => {
        mockGet.mockResolvedValue({ data: [turno(1)] });
        const { composable } = await setupProfesional();

        await composable.cargarPresentes();

        expect(composable.pendientes.value.map((t) => t.id)).toEqual([1]);
    });

    it('does not populate pendientes for non-profesional roles', async () => {
        mockGet.mockResolvedValue({ data: [turno(1)] });
        const { usePacientesPresentes } = await loadFresh();
        const { useUserStore } = await import('@/stores/user');
        const store = useUserStore();
        store.id = 5;
        store.rol = 'administrativo';
        const composable = usePacientesPresentes();

        await composable.cargarPresentes();

        expect(composable.pendientes.value).toEqual([]);
        expect(composable.presentes.value.map((t) => t.id)).toEqual([1]);
    });

    it('marcarInformado empties pendientes and persists the ids', async () => {
        mockGet.mockResolvedValue({ data: [turno(1), turno(2)] });
        const { composable } = await setupProfesional(9);
        await composable.cargarPresentes();

        composable.marcarInformado();

        expect(composable.pendientes.value).toEqual([]);
        const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY));
        expect(stored.userId).toBe(9);
        expect(stored.date).toBe(todayLocal());
        expect([...stored.ids].sort()).toEqual([1, 2]);
    });

    it('does not re-show an acknowledged turno after a simulated reload, but does show a new one', async () => {
        mockGet.mockResolvedValue({ data: [turno(1), turno(2)] });
        const { composable } = await setupProfesional(7);
        await composable.cargarPresentes();
        composable.marcarInformado();

        mockGet.mockResolvedValue({ data: [turno(1), turno(2), turno(3)] });
        const { composable: composable2 } = await setupProfesional(7);
        await composable2.cargarPresentes();

        expect(composable2.pendientes.value.map((t) => t.id)).toEqual([3]);
    });

    it('ignores stored acks recorded for a different date', async () => {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ userId: 7, date: '2000-01-01', ids: [1] }));
        mockGet.mockResolvedValue({ data: [turno(1)] });
        const { composable } = await setupProfesional(7);

        await composable.cargarPresentes();

        expect(composable.pendientes.value.map((t) => t.id)).toEqual([1]);
    });

    it('ignores stored acks recorded for a different user', async () => {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ userId: 999, date: todayLocal(), ids: [1] }));
        mockGet.mockResolvedValue({ data: [turno(1)] });
        const { composable } = await setupProfesional(7);

        await composable.cargarPresentes();

        expect(composable.pendientes.value.map((t) => t.id)).toEqual([1]);
    });

    it('falls back to in-memory behavior and never crashes when localStorage throws', async () => {
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
            throw new Error('denied');
        });
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
            throw new Error('denied');
        });
        mockGet.mockResolvedValue({ data: [turno(1)] });
        const { composable } = await setupProfesional(3);

        await expect(composable.cargarPresentes()).resolves.not.toThrow();
        expect(composable.pendientes.value.map((t) => t.id)).toEqual([1]);
        expect(() => composable.marcarInformado()).not.toThrow();
        expect(composable.pendientes.value).toEqual([]);
    });

    it('drops a pending turno that is no longer present', async () => {
        mockGet.mockResolvedValueOnce({ data: [turno(1)] });
        const { composable } = await setupProfesional(4);
        await composable.cargarPresentes();
        expect(composable.pendientes.value.map((t) => t.id)).toEqual([1]);

        mockGet.mockResolvedValueOnce({ data: [] });
        await composable.cargarPresentes();

        expect(composable.pendientes.value).toEqual([]);
    });

    it('detenerPolling clears pendientes', async () => {
        mockGet.mockResolvedValue({ data: [turno(1)] });
        const { composable } = await setupProfesional(2);
        await composable.cargarPresentes();
        expect(composable.pendientes.value.length).toBe(1);

        composable.detenerPolling();

        expect(composable.pendientes.value).toEqual([]);
    });
});
