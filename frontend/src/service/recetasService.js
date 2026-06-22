import api from '@/api/axios';

export default {
    config() {
        return api.get('/recetas/config', { withCredentials: true });
    },
    getFinanciadores() {
        return api.get('/recetas/financiadores', { withCredentials: true });
    },
    buscarMedicamentos(params) {
        return api.get('/recetas/medicamentos', { params, withCredentials: true });
    },
    buscarDiagnosticos(q) {
        return api.get('/recetas/diagnosticos', { params: { q }, withCredentials: true });
    },
    emitir(payload) {
        return api.post('/recetas', payload, { withCredentials: true });
    }
};
