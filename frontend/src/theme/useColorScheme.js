import { computed, readonly, ref } from 'vue';

export const STORAGE_KEY = 'cau-color-scheme';
export const LEGACY_KEY = 'theme';
export const MODES = ['system', 'light', 'dark'];

const QUERY = '(prefers-color-scheme: dark)';

// Module-level singleton state shared by every caller.
const mode = ref('system');
const systemDark = ref(false);
let mediaQuery = null;

const isDark = computed(() => mode.value === 'dark' || (mode.value === 'system' && systemDark.value));

function readStorage(key) {
    try {
        return window.localStorage.getItem(key);
    } catch (error) {
        // Storage unavailable (private mode, blocked site data): behave as empty.
        return null;
    }
}

function writeStorage(key, value) {
    try {
        window.localStorage.setItem(key, value);
    } catch (error) {
        // Storage unavailable: the choice lives for this page load only.
    }
}

function removeStorage(key) {
    try {
        window.localStorage.removeItem(key);
    } catch (error) {
        // Storage unavailable: nothing to clean up.
    }
}

function resolveStoredMode() {
    const stored = readStorage(STORAGE_KEY);
    if (MODES.includes(stored)) {
        return stored;
    }

    const legacy = readStorage(LEGACY_KEY);
    if (legacy === 'dark' || legacy === 'light') {
        writeStorage(STORAGE_KEY, legacy);
        removeStorage(LEGACY_KEY);
        return legacy;
    }

    return 'system';
}

function apply() {
    const root = document.documentElement;
    root.classList.toggle('app-dark', isDark.value);
    root.style.colorScheme = isDark.value ? 'dark' : 'light';
}

function handleSystemChange(event) {
    systemDark.value = event.matches;
    apply();
}

function init() {
    mode.value = resolveStoredMode();

    if (!mediaQuery && typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
        mediaQuery = window.matchMedia(QUERY);
        if (typeof mediaQuery.addEventListener === 'function') {
            mediaQuery.addEventListener('change', handleSystemChange);
        } else if (typeof mediaQuery.addListener === 'function') {
            mediaQuery.addListener(handleSystemChange);
        }
    }

    systemDark.value = mediaQuery ? mediaQuery.matches : false;
    apply();
}

function setMode(next) {
    if (!MODES.includes(next)) {
        return;
    }
    mode.value = next;
    writeStorage(STORAGE_KEY, next);
    apply();
}

export function useColorScheme() {
    return {
        mode: readonly(mode),
        isDark,
        setMode,
        init,
        apply
    };
}
