// Criterio de acceso del guard global, aparte del router para poder probarlo sin cargar toda la app.
export const PAGINAS_PUBLICAS = ['/auth/login', '/recuperar', '/logout'];

/** Pública si la ruta lo declara con `meta.publica` (no depende de cómo se escriba la dirección) o es una página de acceso. */
export function esRutaPublica(to) {
    return to.meta?.publica === true || PAGINAS_PUBLICAS.includes(to.path) || to.path.startsWith('/reset/');
}

export function requiereSesion(to) {
    return !esRutaPublica(to);
}
