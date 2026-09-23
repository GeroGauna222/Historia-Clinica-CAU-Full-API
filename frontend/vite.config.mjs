import { fileURLToPath, URL } from 'node:url';

import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
    optimizeDeps: {
        noDiscovery: true
    },
    plugins: [
        vue(),
        Components({
            resolvers: [PrimeVueResolver()]
        })
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    test: {
        environment: 'jsdom',
        include: ['src/**/*.test.js', 'scripts/**/*.test.mjs']
    },
    server: {
        host: '0.0.0.0', // 🔹 Necesario para exponer el servidor dentro del contenedor
        port: 5173,
        proxy: {
            '/api': {
                //target: 'http://web:5000', // 🔁 Cambiamos localhost → nombre del servicio del backend en Docker
                target: 'http://localhost:5000',
                changeOrigin: true,
                secure: false
            }
        }
    }
});
