// Servicio de Usuarios
// Maneja llamadas al backend relacionadas con usuarios.
// Usa cookies de sesión (Flask-Login) => credentials: 'include'

export async function createUsuario({ nombre, username, email, password, rol }) {
    const resp = await fetch('/api/usuarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ nombre, username, email, password, rol })
    });

    let payload = null;
    try {
        payload = await resp.json();
    } catch (_) {
        /* ignore */
    }

    if (!resp.ok) {
        const msg = payload?.error || `Error ${resp.status}`;
        throw new Error(msg);
    }

    return payload; // { message: "Usuario '...' creado con éxito ✅" }
}
