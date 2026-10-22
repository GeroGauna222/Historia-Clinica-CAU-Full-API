import api from '@/api/axios';

export default {
    // Catálogo de Prácticas
    getPracticas(params = {}) {
        return api.get('/facturacion/practicas', { params, withCredentials: true });
    },
    crearPractica(data) {
        return api.post('/facturacion/practicas', data, { withCredentials: true });
    },
    actualizarPractica(id, data) {
        return api.put(`/facturacion/practicas/${id}`, data, { withCredentials: true });
    },
    eliminarPractica(id) {
        return api.delete(`/facturacion/practicas/${id}`, { withCredentials: true });
    },
    aumentoMasivoPracticas(data) {
        return api.post('/facturacion/practicas/aumento-masivo', data, { withCredentials: true });
    },

    // Catálogo de Prestadores / Efectores
    getPrestadores(params = {}) {
        return api.get('/facturacion/prestadores', { params, withCredentials: true });
    },
    crearPrestador(data) {
        return api.post('/facturacion/prestadores', data, { withCredentials: true });
    },
    actualizarPrestador(id, data) {
        return api.put(`/facturacion/prestadores/${id}`, data, { withCredentials: true });
    },
    eliminarPrestador(id) {
        return api.delete(`/facturacion/prestadores/${id}`, { withCredentials: true });
    },

    // Registros de Facturación
    getRegistros(params = {}) {
        return api.get('/facturacion/registros', { params, withCredentials: true });
    },
    crearRegistros(data) {
        return api.post('/facturacion/registros', data, { withCredentials: true });
    },
    actualizarRegistro(id, data) {
        return api.put(`/facturacion/registros/${id}`, data, { withCredentials: true });
    },
    eliminarRegistro(id) {
        return api.delete(`/facturacion/registros/${id}`, { withCredentials: true });
    },
    eliminarRegistrosLote(ids) {
        return api.post('/facturacion/registros/eliminar-lote', { ids }, { withCredentials: true });
    },
    recalcularPreciosPeriodo(data) {
        return api.post('/facturacion/registros/recalcular-precios', data, { withCredentials: true });
    },

    // Exportación CSV / XLSX
    exportarFacturacion(params = {}) {
        return api.get('/facturacion/exportar', {
            params,
            responseType: 'blob',
            withCredentials: true
        });
    }
};
