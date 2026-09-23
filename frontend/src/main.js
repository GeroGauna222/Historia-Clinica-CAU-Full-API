import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { createPinia } from 'pinia';
import { CauPreset } from '@/theme/cauPreset';
import { useColorScheme } from '@/theme/useColorScheme';
import PrimeVue from 'primevue/config';
import ConfirmationService from 'primevue/confirmationservice';
import ToastService from 'primevue/toastservice';
import es from '@/locales/es.json';

// Componentes globales
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';

// Estilos
import 'primeicons/primeicons.css';
import '@/assets/styles.scss';
import '@/theme/status.css';

// 🧩 Importar el store del usuario
import { useUserStore } from '@/stores/user';

async function bootstrap() {
    const app = createApp(App);
    const pinia = createPinia();

    app.use(pinia);
    app.use(router);
    app.use(PrimeVue, {
        locale: es,
        theme: {
            preset: CauPreset,
            options: { darkModeSelector: '.app-dark', cssLayer: false }
        }
    });
    app.use(ToastService);
    app.use(ConfirmationService);

    app.component('Dialog', Dialog);
    app.component('Button', Button);

    // 🧠 Obtener los datos del usuario antes de montar la app
    const userStore = useUserStore();
    try {
        await userStore.fetchUser();
        console.log('✅ Usuario cargado:', userStore.nombre, '| Rol:', userStore.rol);
    } catch (err) {
        console.warn('⚠️ No se pudo cargar el usuario al iniciar:', err);
    }

    // Color scheme must be resolved before the first render.
    useColorScheme().init();

    // 🔥 Ahora que el store tiene el rol, montamos la app
    app.mount('#app');
}

bootstrap();
