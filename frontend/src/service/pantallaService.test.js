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

    it('los metodos con sesion usan las rutas correctas', () => {
        pantallaService.vistaPrevia();
        expect(mockGet).toHaveBeenCalledWith('/pantalla/vista-previa');

        pantallaService.listarVisibles();
        expect(mockGet).toHaveBeenCalledWith('/pantalla/visibles');

        pantallaService.actualizarVisible('consultorio', 5, { visible: false });
        expect(mockPatch).toHaveBeenCalledWith('/pantalla/visibles/consultorio/5', { visible: false });

        pantallaService.listarTelevisores();
        expect(mockGet).toHaveBeenCalledWith('/pantalla/televisores');

        pantallaService.vincularTelevisor({ codigo: 'ABC123', nombre: 'Sala 1' });
        expect(mockPost).toHaveBeenCalledWith('/pantalla/televisores', { codigo: 'ABC123', nombre: 'Sala 1' });

        pantallaService.desvincularTelevisor(9);
        expect(mockDelete).toHaveBeenCalledWith('/pantalla/televisores/9');
    });
});
