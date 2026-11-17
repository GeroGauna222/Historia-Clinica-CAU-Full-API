const ES_NUMERICO = /^\d+$/;

function consultorioDe(t) {
    return (t.consultorio || '').trim();
}

function grupoDe(t) {
    const c = consultorioDe(t);
    if (!c) return 2;
    return ES_NUMERICO.test(c) ? 0 : 1;
}

// Comparación de texto única: sin distinguir mayúsculas/acentos y con números en orden natural ("Box 2" < "Box 10").
function comparar(a, b) {
    return String(a).localeCompare(String(b), 'es', { sensitivity: 'base', numeric: true });
}

/**
 * Orden: consultorios numéricos ascendente, luego espacios con nombre (alfabético), luego tarjetas sin consultorio
 * (por nombre). El desempate final (nombre, tipo, id) es determinista para que la grilla no salte entre consultas.
 */
export function ordenarTarjetas(tarjetas) {
    return [...tarjetas].sort((a, b) => {
        const ga = grupoDe(a);
        const gb = grupoDe(b);
        if (ga !== gb) return ga - gb;
        const porConsultorio = ga === 2 ? 0 : comparar(consultorioDe(a), consultorioDe(b));
        return porConsultorio || comparar(a.nombre || '', b.nombre || '') || comparar(a.tipo, b.tipo) || Number(a.id) - Number(b.id) || 0;
    });
}

export function paginar(tarjetas, porPagina = 12) {
    const n = Math.max(1, Math.floor(porPagina) || 1);
    const paginas = [];
    for (let i = 0; i < tarjetas.length; i += n) {
        paginas.push(tarjetas.slice(i, i + n));
    }
    return paginas;
}

/** `previos` es null en la primera carga (no suena). Devuelve { nuevos, vistos }. */
export function detectarLlamadosNuevos(previos, tarjetas) {
    const vistos = new Set();
    for (const t of tarjetas) {
        for (const p of t.en_atencion || []) {
            vistos.add(`${t.tipo}-${t.id}|${p.atencion_inicio}|${p.nombre}`);
        }
    }
    if (previos === null) return { nuevos: false, vistos };
    let nuevos = false;
    for (const clave of vistos) {
        if (!previos.has(clave)) nuevos = true;
    }
    return { nuevos, vistos };
}
