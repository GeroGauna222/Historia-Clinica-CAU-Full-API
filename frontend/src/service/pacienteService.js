import api from '@/api/axios';

export default {
    getPacientes() {
        return api.get('/pacientes', { withCredentials: true });
    },
    crearPaciente(data) {
        return api.post('/pacientes', data, { withCredentials: true });
    },
    updatePaciente(id, data) {
        return api.put(`/pacientes/${id}`, data, { withCredentials: true });
    },
    getPaciente(id) {
        return api.get(`/pacientes/${id}`, { withCredentials: true });
    },
    deletePaciente(id) {
        return api.delete(`/pacientes/${id}`, { withCredentials: true });
    },
    getProximoNroHc() {
        return api.get('/pacientes/proximo-nro-hc', { withCredentials: true });
    },
    getAusencias(id) {
        return api.get(`/pacientes/${id}/ausencias`, { withCredentials: true });
    },
    getTurnos(id) {
        return api.get(`/pacientes/${id}/turnos`, { withCredentials: true });
    }
};
