import { describe, expect, it } from 'vitest';
import { CauPreset } from './cauPreset.js';

describe('CauPreset', () => {
    it('anchors the light primary on cau.700 and the dark primary on cau.400', () => {
        const { light, dark } = CauPreset.semantic.colorScheme;
        expect(CauPreset.primitive.cau[700]).toBe('#0f766e');
        expect(light.primary.color).toBe('{cau.700}');
        expect(dark.primary.color).toBe('{cau.400}');
    });

    it('defines app background tokens in both schemes', () => {
        const { light, dark } = CauPreset.semantic.colorScheme;
        expect(light.app.background).toBe('{surface.50}');
        expect(dark.app.background).toBe('{surface.950}');
        expect(dark.surface[950]).toBe('#0b1220');
        expect(dark.content.background).toBe('{surface.800}');
    });

    it('sets shape and focus ring', () => {
        expect(CauPreset.semantic.content.borderRadius).toBe('10px');
        expect(CauPreset.semantic.formField.borderRadius).toBe('8px');
        expect(CauPreset.semantic.focusRing.width).toBe('2px');
    });
});
