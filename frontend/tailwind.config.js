/** @type {import('tailwindcss').Config} */
import PrimeUI from 'tailwindcss-primeui';

export default {
    // Habilita dark mode por clase, y también respeta el prefijo que usa PrimeVue
    darkMode: ['class', '[class*="app-dark"]'],

    content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],

    theme: {
        extend: {
            fontFamily: {
                sans: ['Noto Sans', 'sans-serif'],
                heading: ['Figtree', 'sans-serif']
            },
            colors: {
                primary: {
                    DEFAULT: '#00BFA5', // verde institucional CAU
                    50: '#E0F2F1',
                    100: '#B2DFDB',
                    200: '#80CBC4',
                    300: '#4DB6AC',
                    400: '#26A69A',
                    500: '#009688',
                    600: '#00897B',
                    700: '#00796B',
                    800: '#00695C',
                    900: '#004D40'
                },
                surface: {
                    0: '#FFFFFF',
                    50: '#F9FAFB',
                    100: '#F4F4F5',
                    900: '#1E1E1E',
                    950: '#121212'
                },
                textcolor: {
                    light: '#1E1E1E',
                    dark: '#E5E5E5'
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
