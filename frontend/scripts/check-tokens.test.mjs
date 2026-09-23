import { describe, expect, it } from 'vitest';
import { ALLOWLIST, scanSource } from './check-tokens.mjs';

const rules = (content) => scanSource(content).map((v) => v.rule);

describe('scanSource', () => {
    it('flags bg-white and gray utilities', () => {
        expect(rules('<div class="bg-white p-4"></div>')).toEqual(['bg-white']);
        expect(rules('<p class="text-gray-500"></p>')).toEqual(['gray-utility']);
        expect(rules('<p class="hover:bg-gray-50/50 border-gray-200"></p>')).toEqual(['gray-utility', 'gray-utility']);
    });

    it('flags dark: color utilities, including stacked variants', () => {
        expect(rules('<div class="dark:bg-surface-900"></div>')).toEqual(['dark-color-utility']);
        expect(rules('<div class="dark:hover:text-red-400"></div>')).toEqual(['dark-color-utility']);
    });

    it('ignores non-color dark variants and semantic utilities', () => {
        expect(rules('<div class="dark:hidden bg-card text-color border-surface"></div>')).toEqual([]);
    });

    it('flags hex colors in templates and styles', () => {
        const source = '<template><div style="color: #fff"></div></template>\n<style>\n.a { background: #d1d5db; }\n</style>';
        const found = scanSource(source);
        expect(found.map((v) => v.rule)).toEqual(['hex', 'hex']);
        expect(found[1].line).toBe(3);
    });

    it('ignores hex inside script blocks, slot shorthands and HTML entities', () => {
        const source = ["<script setup>\nconst color = '#3B82F6';\n</script>", '<template>', '<Column><template #add>x</template></Column>', '<span>&#8212;</span>', '</template>'].join('\n');
        expect(scanSource(source)).toEqual([]);
    });

    it('reports the correct line after a script block', () => {
        const source = '<script setup>\nconst a = \'#fff\';\nconst b = 1;\n</script>\n<template>\n<div class="bg-white"></div>\n</template>';
        expect(scanSource(source)).toEqual([{ line: 6, rule: 'bg-white', match: 'bg-white' }]);
    });

    it('allowlists the Spec 2 calendar views', () => {
        expect(ALLOWLIST.has('src/views/pages/historias/Turnos.vue')).toBe(true);
        expect(ALLOWLIST.has('src/views/pages/turnos/CalendarioGrupo.vue')).toBe(true);
        expect(ALLOWLIST.has('src/views/pages/turnos/ModuloRehabilitacion.vue')).toBe(true);
    });
});
