import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import PrimeVue from 'primevue/config';
import ColorSchemeSwitcher from './ColorSchemeSwitcher.vue';
import { useColorScheme } from '@/theme/useColorScheme';

function mountSwitcher() {
    return mount(ColorSchemeSwitcher, {
        attachTo: document.body,
        global: { plugins: [[PrimeVue, { theme: 'none' }]] }
    });
}

describe('ColorSchemeSwitcher', () => {
    afterEach(() => {
        useColorScheme().setMode('system');
        document.body.innerHTML = '';
    });

    it('labels the trigger with the active mode', async () => {
        const wrapper = mountSwitcher();
        const trigger = wrapper.get('button[aria-controls="color-scheme-menu"]');

        expect(trigger.attributes('aria-label')).toBe('Tema: Sistema');
        expect(trigger.attributes('aria-haspopup')).toBe('true');

        useColorScheme().setMode('dark');
        await nextTick();

        expect(trigger.attributes('aria-label')).toBe('Tema: Oscuro');
        expect(trigger.find('.pi-moon').exists()).toBe(true);
        wrapper.unmount();
    });
});
