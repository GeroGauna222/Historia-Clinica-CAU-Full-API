import { describe, expect, it } from 'vitest';
import { migrateSource } from './migrate-tokens.mjs';

describe('migrateSource', () => {
    it('maps page backgrounds to ground', () => {
        expect(migrateSource('<div class="bg-surface-50 dark:bg-surface-950 min-h-screen">')).toBe('<div class="bg-ground min-h-screen">');
        expect(migrateSource('<div class="dark:bg-surface-950 bg-surface-50">')).toBe('<div class="bg-ground">');
    });

    it('maps card surfaces and drops dark variants', () => {
        expect(migrateSource('<div class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 p-5">')).toBe('<div class="bg-card border border-surface p-5">');
        expect(migrateSource('<div class="bg-white dark:bg-slate-900 rounded-2xl">')).toBe('<div class="bg-card rounded-2xl">');
    });

    it('maps text colors', () => {
        expect(migrateSource('<h1 class="text-3xl text-gray-800 dark:text-white">')).toBe('<h1 class="text-3xl text-color">');
        expect(migrateSource('<p class="text-gray-500 dark:text-gray-400 mt-1">')).toBe('<p class="text-muted-color mt-1">');
    });

    it('maps feedback colors to status tokens', () => {
        expect(migrateSource('<div class="bg-red-50 border border-red-200 text-red-700 dark:bg-red-900/20">')).toBe('<div class="bg-status-sin-aviso-bg border border-status-sin-aviso-border text-status-sin-aviso-fg">');
        expect(migrateSource('<div class="bg-green-100 text-green-700">')).toBe('<div class="bg-status-presente-bg text-status-presente-fg">');
    });

    it('keeps solid action colors and non-color dark variants', () => {
        const input = '<button class="bg-blue-600 hover:bg-blue-700 text-white dark:hidden">';
        expect(migrateSource(input)).toBe(input);
    });

    it('does not touch longer tokens that share a prefix', () => {
        expect(migrateSource('<i class="bg-surface-500 text-gray-5000x">')).toBe('<i class="bg-surface-500 text-gray-5000x">');
    });

    it('migrates dynamic class strings in bindings and scripts', () => {
        expect(migrateSource(":class=\"active ? 'bg-primary text-primary-contrast' : 'bg-gray-200 dark:bg-gray-700 text-gray-600'\"")).toBe(":class=\"active ? 'bg-primary text-primary-contrast' : 'bg-emphasis text-muted-color'\"");
    });

    it('maps hover states to emphasis', () => {
        expect(migrateSource('<tr class="hover:bg-surface-100 dark:hover:bg-surface-800">')).toBe('<tr class="hover:bg-emphasis">');
    });
});
