import api from '@/api/axios';

export default {
    listar() {
        return api.get('/comunicados', { withCredentials: true });
    },
    crear(data) {
        return api.post('/comunicados', data, { withCredentials: true });
    },
    eliminar(id) {
        return api.delete(`/comunicados/${id}`, { withCredentials: true });
    }
};
