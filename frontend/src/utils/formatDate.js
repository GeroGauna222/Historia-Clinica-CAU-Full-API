// Detecta formato YYYY-MM-DD
function esFechaSimple(f) {
    return /^\d{4}-\d{2}-\d{2}$/.test(f);
}

// Detecta formato MySQL DATETIME
function esFechaDateTime(f) {
    return /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(f);
}
// ✔ Función para fechas CLÍNICAS (sin timezone)
export function fechaBonitaClinica(fecha) {
    if (!fecha) return '-';

    const f = String(fecha).trim();

    // YYYY-MM-DD
    if (esFechaSimple(f)) {
        const [y, m, d] = f.split('-');
        return `${d}/${m}/${y}`;
    }

    // YYYY-MM-DD HH:MM:SS
    if (esFechaDateTime(f)) {
        const [ymd] = f.split(' ');
        const [y, m, d] = ymd.split('-');
        return `${d}/${m}/${y}`;
    }

    // RFC822 como "Fri, 02 Jan 2026 00:00:00 GMT"
    const partes = f.split(' ');
    if (partes.length >= 4) {
        const d = partes[1];
        const mesStr = partes[2];
        const y = partes[3];

        const meses = {
            Jan: '01',
            Feb: '02',
            Mar: '03',
            Apr: '04',
            May: '05',
            Jun: '06',
            Jul: '07',
            Aug: '08',
            Sep: '09',
            Oct: '10',
            Nov: '11',
            Dec: '12'
        };

        return `${d}/${meses[mesStr]}/${y}`;
    }

    return '-';
}

// ✔ Función para el DASHBOARD (puede usar new Date sin riesgo)
export function fechaBonitaDashboard(fecha) {
    if (!fecha) return '-';

    const date = new Date(fecha);

    if (isNaN(date.getTime())) return '-';

    return date.toLocaleDateString('es-AR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}
// ✔ Función para fechas COMPLETAS (DD/MM/AAAA HH:MM)
export function fechaBonitaCompleta(fecha) {
    if (!fecha) return '-';

    // Convertimos la fecha a objeto Date
    const date = new Date(fecha);

    if (isNaN(date.getTime())) return '-';

    const dia = String(date.getDate()).padStart(2, '0');
    const mes = String(date.getMonth() + 1).padStart(2, '0');
    const año = date.getFullYear();

    const horas = String(date.getHours()).padStart(2, '0');
    const mins = String(date.getMinutes()).padStart(2, '0');

    return `${dia}/${mes}/${año} ${horas}:${mins}`;
}

// ✔ Formato: 08/12/2025 14:00 – 15:00
export function fechaRangoBonito(inicio, fin) {
    if (!inicio || !fin) return '-';

    const d1 = new Date(inicio);
    const d2 = new Date(fin);

    if (isNaN(d1.getTime()) || isNaN(d2.getTime())) return '-';

    // Extraer partes del inicio
    const dia = String(d1.getDate()).padStart(2, '0');
    const mes = String(d1.getMonth() + 1).padStart(2, '0');
    const año = d1.getFullYear();

    const h1 = String(d1.getHours()).padStart(2, '0');
    const m1 = String(d1.getMinutes()).padStart(2, '0');

    const h2 = String(d2.getHours()).padStart(2, '0');
    const m2 = String(d2.getMinutes()).padStart(2, '0');

    // Si los días son iguales → formato corto
    if (d1.getDate() === d2.getDate() && d1.getMonth() === d2.getMonth() && d1.getFullYear() === d2.getFullYear()) {
        return `${dia}/${mes}/${año} ${h1}:${m1} – ${h2}:${m2}`;
    }

    // Si los días son distintos → mostrar fechas completas
    return `${dia}/${mes}/${año} ${h1}:${m1} – ${d2.toLocaleDateString('es-AR')} ${h2}:${m2}`;
}

export function horaExacta(fecha) {
    if (!fecha) return '-';

    const d = new Date(fecha);
    if (isNaN(d.getTime())) return '-';

    // ✔ Ajuste Argentina: sumar 3 horas
    d.setHours(d.getHours() + 3);

    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');

    return `${h}:${m}`;
}
