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
    },
    actualizarAusencia(id, ausencia) {
        return api.patch(`/turnos/${id}/ausencia`, { ausencia }, { withCredentials: true });
    },
    actualizarAusenciaGrupal(turnoGrupalId, ausencia) {
        return api.patch(`/turnos/grupales/${turnoGrupalId}/ausencia`, { ausencia }, { withCredentials: true });
    },
    llamar(id) {
        return api.post(`/turnos/${id}/llamar`, {}, { withCredentials: true });
    },
    finalizar(id) {
        return api.post(`/turnos/${id}/finalizar`, {}, { withCredentials: true });
    },
    llamarGrupal(turnoGrupalId) {
        return api.post(`/turnos/grupales/${turnoGrupalId}/llamar`, {}, { withCredentials: true });
    }
};
