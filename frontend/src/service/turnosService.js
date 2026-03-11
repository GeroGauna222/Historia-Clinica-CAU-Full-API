// src/service/turnosService.js
import api from '@/api/axios';

export default {
    listar() {
        return api.get('/turnos', { withCredentials: true });
    },
    crear(data) {
        return api.post('/turnos', data, { withCredentials: true });
    },
    actualizar(id, data) {
        return api.put(`/turnos/${id}`, data, { withCredentials: true });
    },
    eliminar(id) {
        return api.delete(`/turnos/${id}`, { withCredentials: true });
    }
};
