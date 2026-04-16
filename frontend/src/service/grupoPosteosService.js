import api from '@/api/axios';

export default {
    listar(grupoId) {
        return api.get(`/grupos/${grupoId}/posteos`, { withCredentials: true });
    },
    crear(grupoId, data) {
        return api.post(`/grupos/${grupoId}/posteos`, data, { withCredentials: true });
    },
    eliminar(grupoId, posteoId) {
        return api.delete(`/grupos/${grupoId}/posteos/${posteoId}`, { withCredentials: true });
    }
};
