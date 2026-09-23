import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

const slate = {
    0: '#ffffff',
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617'
};

export const CauPreset = definePreset(Aura, {
    primitive: {
        cau: {
            50: '#f0fdfa',
            100: '#ccfbf1',
            200: '#99f6e4',
            300: '#5eead4',
            400: '#2dd4bf',
            500: '#14b8a6',
            600: '#0d9488',
            700: '#0f766e',
            800: '#115e59',
            900: '#134e4a',
            950: '#042f2e'
        }
    },
    semantic: {
        primary: {
            50: '{cau.50}',
            100: '{cau.100}',
            200: '{cau.200}',
            300: '{cau.300}',
            400: '{cau.400}',
            500: '{cau.500}',
            600: '{cau.600}',
            700: '{cau.700}',
            800: '{cau.800}',
            900: '{cau.900}',
            950: '{cau.950}'
        },
        focusRing: {
            width: '2px',
            style: 'solid',
            color: '{primary.color}',
            offset: '2px',
            shadow: 'none'
        },
        formField: {
            borderRadius: '8px'
        },
        content: {
            borderRadius: '10px'
        },
        colorScheme: {
            light: {
                surface: slate,
                primary: {
                    color: '{cau.700}',
                    contrastColor: '#ffffff',
                    hoverColor: '{cau.800}',
                    activeColor: '{cau.900}'
                },
                highlight: {
                    background: '{cau.50}',
                    focusBackground: '{cau.100}',
                    color: '{cau.800}',
                    focusColor: '{cau.900}'
                },
                text: {
                    color: '{surface.900}',
                    hoverColor: '{surface.950}',
                    mutedColor: '{surface.500}',
                    hoverMutedColor: '{surface.600}'
                },
                app: {
                    background: '{surface.50}',
                    subtleBackground: '{surface.50}'
                }
            },
            dark: {
                surface: {
                    ...slate,
                    700: '#1e293b',
                    800: '#131c2e',
                    900: '#0f172a',
                    950: '#0b1220'
                },
                primary: {
                    color: '{cau.400}',
                    contrastColor: '#042f2e',
                    hoverColor: '{cau.300}',
                    activeColor: '{cau.200}'
                },
                highlight: {
                    background: 'rgba(45, 212, 191, 0.12)',
                    focusBackground: 'rgba(45, 212, 191, 0.2)',
                    color: '#5eead4',
                    focusColor: '{cau.200}'
                },
                text: {
                    color: '{surface.200}',
                    hoverColor: '{surface.0}',
                    mutedColor: '{surface.400}',
                    hoverMutedColor: '{surface.300}'
                },
                content: {
                    background: '{surface.800}',
                    hoverBackground: '{surface.700}',
                    borderColor: '{surface.700}'
                },
                overlay: {
                    select: { background: '{surface.800}', borderColor: '{surface.700}' },
                    popover: { background: '{surface.800}', borderColor: '{surface.700}' },
                    modal: { background: '{surface.800}', borderColor: '{surface.700}' }
                },
                formField: {
                    background: '{surface.900}'
                },
                app: {
                    background: '{surface.950}',
                    subtleBackground: '{surface.900}'
                }
            }
        }
    }
});
