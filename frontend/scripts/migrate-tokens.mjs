#!/usr/bin/env node
// One-shot codemod: rewrites palette/dark: utilities in .vue files to preset-backed semantic utilities.
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const muted = 'text-muted-color';
const border = 'border-surface';

export const TOKEN_MAP = {
    // Surfaces
    'bg-white': 'bg-card',
    'bg-surface-0': 'bg-card',
    'bg-surface-50': 'bg-subtle',
    'bg-surface-100': 'bg-subtle',
    'bg-gray-50': 'bg-subtle',
    'bg-slate-50': 'bg-subtle',
    'bg-gray-200': 'bg-emphasis',
    'bg-gray-300/60': 'bg-line/60',
    'hover:bg-surface-50': 'hover:bg-emphasis',
    'hover:bg-surface-100': 'hover:bg-emphasis',
    'hover:bg-surface-200': 'hover:bg-emphasis',
    'hover:bg-gray-300': 'hover:bg-emphasis',
    'hover:bg-gray-50/50': 'hover:bg-emphasis',
    // Text
    'text-gray-900': 'text-color',
    'text-gray-800': 'text-color',
    'text-gray-700': 'text-color',
    'text-surface-900': 'text-color',
    'text-gray-600': muted,
    'text-gray-500': muted,
    'text-gray-400': muted,
    'text-gray-300': muted,
    'text-surface-400': muted,
    'text-surface-500': muted,
    'text-surface-600': muted,
    // Borders, dividers, rings
    'border-surface-200': border,
    'border-surface-300': border,
    'border-surface-400': border,
    'border-gray-100': border,
    'border-gray-200': border,
    'border-gray-300': border,
    'border-cyan-100': border,
    'border-blue-100': border,
    'border-blue-200': border,
    'border-blue-300': border,
    'border-primary-100': border,
    'border-indigo-200': border,
    'divide-gray-100': 'divide-line',
    'divide-surface-100': 'divide-line',
    'ring-surface-200': 'ring-line',
    'ring-white': 'ring-card',
    // Brand accents
    'bg-blue-50': 'bg-highlight',
    'bg-blue-100': 'bg-highlight',
    'bg-primary-50': 'bg-highlight',
    'bg-indigo-50': 'bg-highlight',
    'hover:bg-blue-50': 'hover:bg-highlight',
    'hover:bg-blue-100': 'hover:bg-highlight',
    'ring-blue-500': 'ring-primary',
    'border-blue-500': 'border-primary',
    'text-blue-500': 'text-primary',
    'text-blue-600': 'text-primary',
    'text-blue-700': 'text-primary',
    'text-primary-500': 'text-primary',
    'text-primary-600': 'text-primary',
    'text-primary-700': 'text-primary',
    'text-indigo-700': 'text-primary',
    'hover:text-blue-800': 'hover:text-primary-emphasis',
    'hover:text-primary-600': 'hover:text-primary-emphasis',
    'hover:text-primary-800': 'hover:text-primary-emphasis',
    'hover:border-primary-300': 'hover:border-primary',
    // Feedback -> status tokens
    'bg-green-50': 'bg-status-presente-bg',
    'bg-green-100': 'bg-status-presente-bg',
    'bg-emerald-50': 'bg-status-presente-bg',
    'bg-emerald-100': 'bg-status-presente-bg',
    'text-green-600': 'text-status-presente-fg',
    'text-green-700': 'text-status-presente-fg',
    'text-emerald-600': 'text-status-presente-fg',
    'text-emerald-700': 'text-status-presente-fg',
    'border-green-200': 'border-status-presente-border',
    'border-green-300': 'border-status-presente-border',
    'border-emerald-200': 'border-status-presente-border',
    'bg-amber-50': 'bg-status-con-aviso-bg',
    'text-amber-500': 'text-status-con-aviso-fg',
    'text-amber-700': 'text-status-con-aviso-fg',
    'text-amber-800': 'text-status-con-aviso-fg',
    'border-amber-200': 'border-status-con-aviso-border',
    'border-amber-300': 'border-status-con-aviso-border',
    'bg-red-50': 'bg-status-sin-aviso-bg',
    'bg-red-100': 'bg-status-sin-aviso-bg',
    'hover:bg-red-50': 'hover:bg-status-sin-aviso-bg',
    'text-red-500': 'text-status-sin-aviso-fg',
    'text-red-600': 'text-status-sin-aviso-fg',
    'text-red-700': 'text-status-sin-aviso-fg',
    'text-red-800': 'text-status-sin-aviso-fg',
    'border-red-200': 'border-status-sin-aviso-border',
    'border-red-300': 'border-status-sin-aviso-border'
};

const escape = (value) => value.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');

// A token is delimited by whitespace, quotes, backticks, braces or line edges.
const BEFORE = '(?<=^|[\\s"\'`{(])';
const AFTER = '(?=$|[\\s"\'`}):,])';

const GROUND_PAIRS = [new RegExp(`${BEFORE}bg-surface-50(\\s+)dark:bg-surface-950${AFTER}`, 'gm'), new RegExp(`${BEFORE}dark:bg-surface-950(\\s+)bg-surface-50${AFTER}`, 'gm')];

const DARK_COLOR = new RegExp(`${BEFORE}dark:(?:[a-z-]+:)*!?(?:bg|text|border|divide|ring|outline|from|via|to|fill|stroke|placeholder|shadow|decoration)-[^\\s"'\`]*[ \\t]*`, 'gm');

const MAP_PATTERNS = Object.entries(TOKEN_MAP).map(([from, to]) => [new RegExp(`${BEFORE}${escape(from)}${AFTER}`, 'gm'), to]);

export function migrateSource(content) {
    let out = content;
    for (const pair of GROUND_PAIRS) {
        out = out.replace(pair, 'bg-ground');
    }
    out = out.replace(DARK_COLOR, '');
    for (const [pattern, to] of MAP_PATTERNS) {
        out = out.replace(pattern, to);
    }
    // Tidy whitespace left by removed tokens.
    // Only static class attributes are trimmed; quoted strings in bindings are left alone
    // (a generic quote-trim would corrupt ternaries such as `' : '`).
    out = out.replace(/class="\s+/g, 'class="').replace(/(class="[^"]*?)\s+"/g, '$1"');
    return out;
}

function main(files) {
    for (const file of files) {
        const before = readFileSync(file, 'utf8');
        const after = migrateSource(before);
        if (after !== before) {
            writeFileSync(file, after);
            console.log(`migrated ${file}`);
        }
    }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    main(process.argv.slice(2));
}
