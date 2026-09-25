// calendar-theme.css is plain CSS (no JS export), so these tests assert on its source text
// directly, the same way scripts/check-tokens.mjs scans CSS/markup as text.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'calendar-theme.css'), 'utf8');

function ruleBody(selector) {
    const pattern = new RegExp(`${selector.replace(/[.[\]]/g, '\\$&')}\\s*\\{([^}]*)\\}`);
    return css.match(pattern)?.[1] || '';
}

describe('calendar-theme.css', () => {
    it('the month-view dot uses a dedicated status variable, not the group bar color', () => {
        // --evt-bar is overridden inline with the group color in Rehab (see barColor() /
        // agendaEventStyle.js), so the dot must read a separate variable to stay on the
        // status color regardless of that override.
        expect(ruleBody('.evt-dot')).toMatch(/background:\s*var\(--evt-dot\)/);
        expect(ruleBody('.evt-dot')).not.toMatch(/var\(--evt-bar\)/);
    });

    it('.evt-ausencia still gets its own (red) dot, independent of the default status color', () => {
        expect(ruleBody('.evt-ausencia')).toMatch(/--evt-dot:\s*var\(--cau-status-sin-aviso-border\)/);
    });

    it('does not set a global background-event opacity that would apply to untyped background events', () => {
        expect(css).not.toMatch(/--fc-bg-event-opacity/);
    });

    it('scopes full opacity to the typed background layers (bg-hatch)', () => {
        expect(ruleBody('.fc .fc-bg-event.bg-hatch')).toMatch(/opacity:\s*1/);
    });

    it('popover and tooltip shadows are built from a neutral base, not the theme text color', () => {
        expect(css).not.toMatch(/box-shadow:[^;]*var\(--p-text-color\)/);
    });

    it('popover and tooltip shadows are softened under dark mode', () => {
        expect(css).toMatch(/:root\.app-dark \.fc \.fc-popover\s*\{[^}]*box-shadow/);
        expect(css).toMatch(/:root\.app-dark \.tippy-box\[data-theme~='agenda'\]\s*\{[^}]*box-shadow/);
    });
});
