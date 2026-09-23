import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const QUERY = '(prefers-color-scheme: dark)';

function mockMatchMedia(initialDark) {
    const listeners = new Set();
    const mql = {
        matches: initialDark,
        media: QUERY,
        addEventListener: (_type, cb) => listeners.add(cb),
        removeEventListener: (_type, cb) => listeners.delete(cb)
    };
    window.matchMedia = vi.fn(() => mql);
    return {
        setDark(value) {
            mql.matches = value;
            listeners.forEach((cb) => cb({ matches: value }));
        }
    };
}

async function loadFresh() {
    vi.resetModules();
    return import('./useColorScheme.js');
}

const root = () => document.documentElement;

describe('useColorScheme', () => {
    beforeEach(() => {
        window.localStorage.clear();
        root().className = '';
        root().style.colorScheme = '';
    });

    afterEach(() => {
        vi.restoreAllMocks();
        delete window.matchMedia;
    });

    it('defaults to system and follows the OS preference live', async () => {
        const media = mockMatchMedia(true);
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        scheme.init();

        expect(scheme.mode.value).toBe('system');
        expect(scheme.isDark.value).toBe(true);
        expect(root().classList.contains('app-dark')).toBe(true);
        expect(root().style.colorScheme).toBe('dark');

        media.setDark(false);

        expect(scheme.isDark.value).toBe(false);
        expect(root().classList.contains('app-dark')).toBe(false);
        expect(root().style.colorScheme).toBe('light');
    });

    it('setMode persists the choice and applies it', async () => {
        mockMatchMedia(false);
        const { useColorScheme, STORAGE_KEY } = await loadFresh();
        const scheme = useColorScheme();
        scheme.init();

        scheme.setMode('dark');
        expect(window.localStorage.getItem(STORAGE_KEY)).toBe('dark');
        expect(root().classList.contains('app-dark')).toBe(true);

        scheme.setMode('light');
        expect(window.localStorage.getItem(STORAGE_KEY)).toBe('light');
        expect(root().classList.contains('app-dark')).toBe(false);
        expect(root().style.colorScheme).toBe('light');
    });

    it('ignores unknown modes', async () => {
        mockMatchMedia(false);
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();
        scheme.init();

        scheme.setMode('sepia');

        expect(scheme.mode.value).toBe('system');
    });

    it('restores a stored mode on init', async () => {
        mockMatchMedia(false);
        window.localStorage.setItem('cau-color-scheme', 'dark');
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        scheme.init();

        expect(scheme.mode.value).toBe('dark');
        expect(root().classList.contains('app-dark')).toBe(true);
    });

    it('migrates the legacy theme key once', async () => {
        mockMatchMedia(false);
        window.localStorage.setItem('theme', 'dark');
        const { useColorScheme, STORAGE_KEY, LEGACY_KEY } = await loadFresh();
        const scheme = useColorScheme();

        scheme.init();

        expect(scheme.mode.value).toBe('dark');
        expect(window.localStorage.getItem(STORAGE_KEY)).toBe('dark');
        expect(window.localStorage.getItem(LEGACY_KEY)).toBeNull();
    });

    it('falls back to system when storage throws', async () => {
        mockMatchMedia(true);
        const denied = () => {
            throw new Error('storage denied');
        };
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(denied);
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(denied);
        vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(denied);
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        expect(() => scheme.init()).not.toThrow();
        expect(scheme.mode.value).toBe('system');
        expect(root().classList.contains('app-dark')).toBe(true);

        expect(() => scheme.setMode('light')).not.toThrow();
        expect(root().classList.contains('app-dark')).toBe(false);
    });

    it('works when matchMedia is unavailable', async () => {
        const { useColorScheme } = await loadFresh();
        const scheme = useColorScheme();

        expect(() => scheme.init()).not.toThrow();
        expect(scheme.isDark.value).toBe(false);
    });
});
