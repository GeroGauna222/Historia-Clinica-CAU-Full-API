const ES_NUMERICO = /^\d+$/;

function grupoDe(t) {
    const c = (t.consultorio || '').trim();
    if (!c) return 2;
    return ES_NUMERICO.test(c) ? 0 : 1;
}

export function ordenarTarjetas(tarjetas) {
    return [...tarjetas].sort((a, b) => {
        const ga = grupoDe(a);
        const gb = grupoDe(b);
        if (ga !== gb) return ga - gb;
        if (ga === 0) return Number(a.consultorio) - Number(b.consultorio) || a.nombre.localeCompare(b.nombre, 'es');
        const ka = ga === 1 ? a.consultorio : a.nombre;
        const kb = gb === 1 ? b.consultorio : b.nombre;
        return ka.localeCompare(kb, 'es', { sensitivity: 'base' });
    });
}

export function paginar(tarjetas, porPagina = 12) {
    const paginas = [];
    for (let i = 0; i < tarjetas.length; i += porPagina) {
        paginas.push(tarjetas.slice(i, i + porPagina));
    }
    return paginas;
}

/** `previos` es null en la primera carga (no suena). Devuelve { nuevos, vistos }. */
export function detectarLlamadosNuevos(previos, tarjetas) {
    const vistos = new Set();
    for (const t of tarjetas) {
        for (const p of t.en_atencion || []) {
            vistos.add(`${t.tipo}-${t.id}|${p.atencion_inicio}`);
        }
    }
    if (previos === null) return { nuevos: false, vistos };
    let nuevos = false;
    for (const clave of vistos) {
        if (!previos.has(clave)) nuevos = true;
    }
    return { nuevos, vistos };
}
