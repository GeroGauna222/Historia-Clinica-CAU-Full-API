// src/service/pantallaService.js
import api from '@/api/axios';

export const CABECERA_CLAVE = 'X-Pantalla-Clave';

export default {
    // Televisor (sin sesión)
    solicitarVinculacion() {
        return api.post('/pantalla/vinculacion', {}, { withCredentials: false });
    },
    obtenerLlamados(clave) {
        return api.get('/pantalla/llamados', { headers: { [CABECERA_CLAVE]: clave }, withCredentials: false });
    },
    // Configuración (con sesión): sin withCredentials porque api/axios.js ya lo tiene en true por defecto;
    // los dos métodos del televisor lo ponen en false a propósito (ADR 0001).
    vistaPrevia() {
        return api.get('/pantalla/vista-previa');
    },
    listarVisibles() {
        return api.get('/pantalla/visibles');
    },
    actualizarVisible(tipo, id, cambios) {
        return api.patch(`/pantalla/visibles/${tipo}/${id}`, cambios);
    },
    listarTelevisores() {
        return api.get('/pantalla/televisores');
    },
    vincularTelevisor({ codigo, nombre }) {
        return api.post('/pantalla/televisores', { codigo, nombre });
    },
    desvincularTelevisor(id) {
        return api.delete(`/pantalla/televisores/${id}`);
    }
};
