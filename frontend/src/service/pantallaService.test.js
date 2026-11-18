import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/api/axios', () => ({
    default: {
        get: (...args) => mockGet(...args),
        post: (...args) => mockPost(...args),
        patch: (...args) => mockPatch(...args),
        delete: (...args) => mockDelete(...args)
    }
}));

import pantallaService, { CABECERA_CLAVE } from './pantallaService';

describe('pantallaService', () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockPost.mockReset();
        mockPatch.mockReset();
        mockDelete.mockReset();
    });

    it('obtenerLlamados envia la clave en la cabecera y sin credenciales', () => {
        pantallaService.obtenerLlamados('clave-123');
        expect(CABECERA_CLAVE).toBe('X-Pantalla-Clave');
        expect(mockGet).toHaveBeenCalledWith('/pantalla/llamados', {
            headers: { 'X-Pantalla-Clave': 'clave-123' },
            withCredentials: false
        });
    });

    it('solicitarVinculacion hace POST sin credenciales', () => {
        pantallaService.solicitarVinculacion();
        expect(mockPost).toHaveBeenCalledWith('/pantalla/vinculacion', {}, { withCredentials: false });
    });

    it('vistaPrevia hace GET a /pantalla/vista-previa', () => {
        pantallaService.vistaPrevia();
        expect(mockGet).toHaveBeenCalledWith('/pantalla/vista-previa');
    });

    it('listarVisibles hace GET a /pantalla/visibles', () => {
        pantallaService.listarVisibles();
        expect(mockGet).toHaveBeenCalledWith('/pantalla/visibles');
    });

    it('actualizarVisible hace PATCH para un usuario', () => {
        const cambios = { mostrar_en_pantalla: false, consultorio: 'Consultorio 1' };
        pantallaService.actualizarVisible('usuario', 5, cambios);
        expect(mockPatch).toHaveBeenCalledWith('/pantalla/visibles/usuario/5', cambios);
    });

    it('actualizarVisible hace PATCH para un grupo', () => {
        const cambios = { mostrar_en_pantalla: true, consultorio: 'Consultorio 2' };
        pantallaService.actualizarVisible('grupo', 7, cambios);
        expect(mockPatch).toHaveBeenCalledWith('/pantalla/visibles/grupo/7', cambios);
    });

    it('listarTelevisores hace GET a /pantalla/televisores', () => {
        pantallaService.listarTelevisores();
        expect(mockGet).toHaveBeenCalledWith('/pantalla/televisores');
    });

    it('vincularTelevisor hace POST con codigo y nombre', () => {
        pantallaService.vincularTelevisor({ codigo: 'K7M2PQ', nombre: 'Sala 1' });
        expect(mockPost).toHaveBeenCalledWith('/pantalla/televisores', { codigo: 'K7M2PQ', nombre: 'Sala 1' });
    });

    it('desvincularTelevisor hace DELETE a /pantalla/televisores/:id', () => {
        pantallaService.desvincularTelevisor(9);
        expect(mockDelete).toHaveBeenCalledWith('/pantalla/televisores/9');
    });
});
