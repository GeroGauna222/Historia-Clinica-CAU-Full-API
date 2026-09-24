// Pure helpers that map a FullCalendar event to agenda card styling.
// They accept FullCalendar EventApi objects or plain objects with the same shape.

const STATUS_KEYS = {
    programado: 'programado',
    presente: 'presente',
    con_aviso: 'con-aviso',
    sin_aviso: 'sin-aviso'
};

const STATUS_LABELS = {
    programado: 'Programado',
    presente: 'Presente',
    'con-aviso': 'Falta con aviso',
    'sin-aviso': 'Falta sin aviso'
};

const GRUPAL_TIPOS = new Set(['grupal', 'turno_grupal']);
const BACKGROUND_TIPOS = new Set(['ausencia_bg', 'indisponible_bg']);
const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

function props(event) {
    return event?.extendedProps || {};
}

function pad(n) {
    return String(n).padStart(2, '0');
}

export function statusKey(estado) {
    return STATUS_KEYS[estado] || 'programado';
}

export function statusLabel(key) {
    return STATUS_LABELS[key] || STATUS_LABELS.programado;
}

export function eventStatus(event) {
    const p = props(event);
    return statusKey(p.estado_asistencia || p.ausencia);
}

export function isGrupal(event) {
    return GRUPAL_TIPOS.has(props(event).tipo);
}

export function isAusencia(event) {
    return props(event).tipo === 'ausencia';
}

export function isBackgroundEvent(event) {
    return event?.display === 'background' || BACKGROUND_TIPOS.has(props(event).tipo);
}

export function eventClassNames(event) {
    const tipo = props(event).tipo;
    if (tipo === 'indisponible_bg') return ['bg-hatch', 'bg-hatch-unavailable'];
    if (tipo === 'ausencia_bg') return ['bg-hatch', 'bg-hatch-absence'];
    if (tipo === 'ausencia') return ['evt', 'evt-ausencia'];

    const classes = ['evt', `evt-${eventStatus(event)}`];
    if (isGrupal(event)) classes.push('evt-grupal');
    return classes;
}

// Group color for the left bar (Rehab); null means "use the status color".
export function barColor(event) {
    const color = props(event).grupoColor;
    return typeof color === 'string' && HEX_COLOR.test(color) ? color : null;
}

export function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
