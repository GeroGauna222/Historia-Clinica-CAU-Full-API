// src/service/ausenciasService.js
import api from '@/api/axios';

export default {
    listar() {
        return api.get('/ausencias', { withCredentials: true });
    },
    listarPorGrupo(grupoId) {
        return api.get(`/grupos/${grupoId}/ausencias`, { withCredentials: true });
    },
    crear(data) {
        return api.post('/ausencias', data, { withCredentials: true });
    },
    eliminar(id) {
        return api.delete(`/ausencias/${id}`, { withCredentials: true });
    }
};
