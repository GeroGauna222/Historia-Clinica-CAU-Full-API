// src/service/historiaService.js
import api from '@/api/axios';

export default {
    buscarPacientes(query) {
        return api.get(`/pacientes/buscar?q=${encodeURIComponent(query)}`, { withCredentials: true });
    },
    getHistorias(pacienteId) {
        return api.get(`/pacientes/${pacienteId}/historias`, { withCredentials: true });
    },
    crearHistoria(pacienteId, data) {
        return api.post(`/pacientes/${pacienteId}/historias`, data, { withCredentials: true });
    },
    descargarPDF(pacienteId) {
        return api.get(`/pacientes/${pacienteId}/historias/pdf`, {
            responseType: 'blob',
            withCredentials: true
        });
    }
};
