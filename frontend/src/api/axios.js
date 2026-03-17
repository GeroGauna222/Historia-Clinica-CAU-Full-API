import axios from 'axios';
import router from '@/router';

const baseURL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
    baseURL,
    withCredentials: true
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            const currentPath = router.currentRoute?.value?.path || '';
            const publicPaths = ['/auth/login', '/recuperar', '/logout'];
            const isPublic = publicPaths.some((p) => currentPath.startsWith(p)) || currentPath.startsWith('/reset/');

            if (!isPublic) {
                router.push('/auth/login');
            }
        }
        return Promise.reject(error);
    }
);

export default api;
