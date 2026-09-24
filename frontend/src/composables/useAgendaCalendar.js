// Shared FullCalendar setup for the agenda views (Turnos, CalendarioGrupo, ModuloRehabilitacion).
// Event markup comes from the view's #eventContent slot (AgendaEvent); do not set eventContent here,
// because an explicit option would override the slot.
import { reactive } from 'vue';
// FullCalendar plugins throw unless the core VDOM is loaded first.
import '@fullcalendar/core/vdom';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import '@/assets/calendar-theme.css';
import { eventClassNames, eventStatus, formatTime, isAusencia, isBackgroundEvent, statusLabel } from '@/components/agenda/agendaEventStyle';

export const AGENDA_LOCALE = {
    code: 'es',
    week: { dow: 1, doy: 4 },
    buttonText: { prev: 'Ant', next: 'Sig', today: 'Hoy', month: 'Mes', week: 'Semana', day: 'Día', list: 'Agenda' },
    weekText: 'Sm',
    allDayText: 'Todo el día',
    moreLinkText: 'más',
    noEventsText: 'No hay eventos para mostrar'
};

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => HTML_ESCAPES[ch]);
}

function muted(text) {
    return text ? `<span class="agenda-tip-muted">${escapeHtml(text)}</span>` : '';
}

function timeRange(event) {
    const start = formatTime(event.start);
    const end = formatTime(event.end);
    return end ? `${start} – ${end}` : start;
}

export function buildTooltipContent(event) {
    const p = event.extendedProps || {};

    if (isAusencia(event)) {
        return [`<strong>${escapeHtml(p.tipoEvento || 'Ausencia')}</strong>`, escapeHtml(p.profesional || 'Profesional'), timeRange(event), muted(p.description)].filter(Boolean).join('<br>');
    }

    const key = eventStatus(event);
    const grupoLine = p.grupoNombre ? `Grupo: ${p.grupoNombre}` : '';
    const profesional = p.profesional && p.profesional !== grupoLine ? p.profesional : '';

    return [
        `<strong>${escapeHtml(p.paciente || event.title)}</strong>`,
        p.dni ? `DNI ${escapeHtml(p.dni)}` : '',
        `${timeRange(event)} · <span class="agenda-tip-status agenda-tip-status--${key}">${statusLabel(key)}</span>`,
        muted(p.description),
        escapeHtml(profesional),
        escapeHtml(grupoLine)
    ]
        .filter(Boolean)
        .join('<br>');
}

function attachTooltip(info) {
    if (isBackgroundEvent(info.event)) return;
    tippy(info.el, {
        content: buildTooltipContent(info.event),
        allowHTML: true,
        placement: 'top',
        theme: 'agenda'
    });
}

function detachTooltip(info) {
    info.el?._tippy?.destroy();
}

function baseOptions() {
    return {
        plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
        initialView: 'timeGridWeek',
        locale: AGENDA_LOCALE,
        headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' },
        slotMinTime: '07:00:00',
        slotMaxTime: '22:00:00',
        allDaySlot: false,
        height: '100%',
        eventMaxStack: 2,
        dayMaxEventRows: 3,
        eventClassNames: (arg) => eventClassNames(arg.event),
        eventDidMount: attachTooltip,
        eventWillUnmount: detachTooltip
    };
}

// Overrides are shallow-merged: a view's key replaces the base key entirely.
export function useAgendaCalendar(overrides = {}) {
    return reactive({ ...baseOptions(), ...overrides });
}
