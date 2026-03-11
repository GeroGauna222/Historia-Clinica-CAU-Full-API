// src/utils/eventBus.js

const listeners = {};

/**
 * Suscribirse a un evento
 * @param {string} event
 * @param {(payload:any) => void} callback
 * @returns {() => void} función para desuscribirse
 */
export function on(event, callback) {
    if (!listeners[event]) {
        listeners[event] = new Set();
    }
    listeners[event].add(callback);

    return () => {
        listeners[event].delete(callback);
    };
}

/**
 * Emitir un evento global
 * @param {string} event
 * @param {any} payload
 */
export function emit(event, payload) {
    if (!listeners[event]) return;
    for (const cb of listeners[event]) {
        try {
            cb(payload);
        } catch (err) {
            console.error(`Error en listener de "${event}":`, err);
        }
    }
}
