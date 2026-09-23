/** @type {import('tailwindcss').Config} */
import PrimeUI from 'tailwindcss-primeui';

// Maps a CSS variable to a Tailwind color that still supports opacity modifiers (e.g. bg-line/60).
const token = (variable) => `color-mix(in srgb, var(${variable}) calc(100% * <alpha-value>), transparent)`;

const status = (name) => ({
    fg: token(`--cau-status-${name}-fg`),
    bg: token(`--cau-status-${name}-bg`),
    border: token(`--cau-status-${name}-border`)
});

export default {
    darkMode: ['class', '[class*="app-dark"]'],

    content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],

    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                heading: ['Figtree', 'sans-serif']
            },
            colors: {
                // PrimeVue keeps surface-0 white in dark mode; these follow the active scheme.
                card: token('--p-content-background'),
                ground: token('--p-app-background'),
                subtle: token('--p-app-subtle-background'),
                line: token('--p-content-border-color'),
                status: {
                    programado: status('programado'),
                    presente: status('presente'),
                    'con-aviso': status('con-aviso'),
                    'sin-aviso': status('sin-aviso')
                }
            }
        },

        screens: {
            sm: '576px',
            md: '768px',
            lg: '992px',
            xl: '1200px',
            '2xl': '1920px'
        }
    },

    plugins: [PrimeUI]
};
