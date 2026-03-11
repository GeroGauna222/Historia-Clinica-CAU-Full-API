// src/utils/fotoUrl.js

export const buildFotoURL = (filename, timestamp = null) => {
    if (!filename) return null;
    if (filename.startsWith('http')) return filename;

    const baseUrl = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

    let url = `${baseUrl}/static/fotos_usuarios/${filename}`;

    // Mantenemos el timestamp para romper el caché cuando actualizas
    if (timestamp) {
        url += `?t=${timestamp}`;
    }

    return url;
};
