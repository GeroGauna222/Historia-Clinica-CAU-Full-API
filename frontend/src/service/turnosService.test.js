import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockPost = vi.fn();

vi.mock('@/api/axios', () => ({
    default: { post: (...args) => mockPost(...args) }
}));

import turnosService from './turnosService';

describe('turnosService (llamados)', () => {
    beforeEach(() => {
        mockPost.mockReset();
    });

    it('llamar hace POST a /turnos/:id/llamar', () => {
        turnosService.llamar(12);
        expect(mockPost).toHaveBeenCalledWith('/turnos/12/llamar', {}, { withCredentials: true });
    });

    it('finalizar hace POST a /turnos/:id/finalizar', () => {
        turnosService.finalizar(12);
        expect(mockPost).toHaveBeenCalledWith('/turnos/12/finalizar', {}, { withCredentials: true });
    });

    it('llamarGrupal hace POST a /turnos/grupales/:id/llamar', () => {
        turnosService.llamarGrupal(3);
        expect(mockPost).toHaveBeenCalledWith('/turnos/grupales/3/llamar', {}, { withCredentials: true });
    });
});
