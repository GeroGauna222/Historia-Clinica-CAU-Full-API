#!/usr/bin/env node
// Fails when hardcoded colors appear in .vue files outside the allowlist.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const ROOTS = ['src/views', 'src/layout', 'src/components'];

// Spec 2 (appointment calendar) files, until Spec 2 lands.
export const ALLOWLIST = new Set(['src/views/pages/historias/Turnos.vue', 'src/views/pages/turnos/CalendarioGrupo.vue', 'src/views/pages/turnos/ModuloRehabilitacion.vue']);

const CLASS_RULES = [
    { rule: 'bg-white', pattern: /(?<![\w-])bg-white(?![\w-])/g },
    { rule: 'gray-utility', pattern: /(?<![\w-])(?:text|bg|border|divide|ring|placeholder)-gray-\d{2,3}(?:\/\d+)?/g },
    { rule: 'dark-color-utility', pattern: /(?<![\w-])dark:(?:[a-z-]+:)*!?(?:bg|text|border|divide|ring|outline|from|via|to|fill|stroke|placeholder|shadow|decoration)-[\w/.[\]#-]*/g }
];

// Excludes HTML entities (&#8212;) and slot shorthands (#add>, #add="…").
const HEX_PATTERN = /(?<![&\w])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w=>-])/g;

function lineOf(content, index) {
    return content.slice(0, index).split('\n').length;
}

// Script blocks hold data (e.g. default group colors), not styling; keep newlines so line numbers stay right.
function blankScripts(content) {
    return content.replace(/<script\b[\s\S]*?<\/script>/g, (block) => block.replace(/[^\n]/g, ' '));
}

function collect(content, pattern, rule) {
    const found = [];
    for (const match of content.matchAll(pattern)) {
        found.push({ line: lineOf(content, match.index), rule, match: match[0] });
    }
    return found;
}

export function scanSource(content) {
    const violations = [];
    for (const { rule, pattern } of CLASS_RULES) {
        violations.push(...collect(content, pattern, rule));
    }
    violations.push(...collect(blankScripts(content), HEX_PATTERN, 'hex'));
    return violations.sort((a, b) => a.line - b.line);
}

function listVueFiles(dir) {
    const files = [];
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) {
            files.push(...listVueFiles(full));
        } else if (entry.name.endsWith('.vue')) {
            files.push(full);
        }
    }
    return files;
}

function main() {
    const frontendRoot = fileURLToPath(new URL('..', import.meta.url));
    let total = 0;

    for (const root of ROOTS) {
        for (const file of listVueFiles(join(frontendRoot, root))) {
            const rel = relative(frontendRoot, file).split(sep).join('/');
            if (ALLOWLIST.has(rel)) {
                continue;
            }
            for (const v of scanSource(readFileSync(file, 'utf8'))) {
                console.log(`${rel}:${v.line}  ${v.rule}  ${v.match}`);
                total += 1;
            }
        }
    }

    if (total > 0) {
        console.error(`\ncheck:tokens found ${total} hardcoded color(s). Use semantic utilities (bg-card, text-color, border-surface, ...).`);
        process.exit(1);
    }
    console.log('check:tokens OK');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    main();
}
