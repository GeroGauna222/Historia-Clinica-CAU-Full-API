import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import ProximoTurnoWidget from './ProximoTurnoWidget.vue';

const globalStubs = {
    Tag: {
        template: '<span class="p-tag"><slot>{{ value }}</slot></span>',
        props: ['value', 'severity']
    },
    Avatar: {
        template: '<div class="p-avatar">{{ label }}</div>',
        props: ['label']
    },
    Button: {
        template: '<button @click="$emit(\'click\')">{{ label }}<slot /></button>',
        props: ['label', 'icon', 'severity', 'disabled']
    }
};

const directives = {
    tooltip: () => {}
};

describe('ProximoTurnoWidget', () => {
    it('muestra el paciente en atención destacado cuando turnoEnCurso está presente', () => {
        const turnoEnCurso = {
            id: 10,
            paciente_id: 42,
            paciente: 'Carlos',
            apellido: 'Gardel',
            dni: '12345678',
            nro_hc: 'HC-99',
            cobertura: 'OSDE',
            nro_afiliado: 'AF-123456/01',
            fecha_inicio: '2026-10-14T09:00:00',
            fecha_fin: '2026-10-14T09:30:00',
            motivo: 'Control foniatrico',
            observaciones: 'Voz cansada',
            celular: '1155667788'
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso, proximoEvento: null, esAdmin: false },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Atención en Curso');
        expect(wrapper.text()).toContain('En atención ahora');
        expect(wrapper.text()).toContain('Carlos Gardel');
        expect(wrapper.text()).toContain('HC: HC-99');
        expect(wrapper.text()).toContain('DNI: 12345678');
        expect(wrapper.text()).toContain('OSDE');
        expect(wrapper.text()).toContain('Afiliado: AF-123456/01');
        expect(wrapper.text()).toContain('Control foniatrico');
        expect(wrapper.text()).toContain('Notas: Voz cansada');
        expect(wrapper.text()).not.toContain('WhatsApp');
        // No debe tener botones de con aviso / sin aviso en atención en curso
        expect(wrapper.text()).not.toContain('Con aviso');
        expect(wrapper.text()).not.toContain('Sin aviso');
    });

    it('emite verHistoria al hacer clic en Abrir Historia Clínica', async () => {
        const turnoEnCurso = {
            id: 10,
            paciente_id: 42,
            paciente: 'Carlos',
            apellido: 'Gardel',
            fecha_inicio: '2026-10-14T09:00:00',
            fecha_fin: '2026-10-14T09:30:00'
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso },
            global: { stubs: globalStubs, directives }
        });

        const btnHistoria = wrapper.findAll('button').find((b) => b.text().includes('Abrir Historia'));
        expect(btnHistoria).toBeTruthy();
        await btnHistoria.trigger('click');

        expect(wrapper.emitted('verHistoria')).toBeTruthy();
        expect(wrapper.emitted('verHistoria')[0][0]).toEqual(turnoEnCurso);
    });

    it('permite cambiar asistencia en proximoEvento (con aviso)', async () => {
        const proximoEvento = {
            id: 25,
            tipo: 'Turno',
            paciente_id: 42,
            paciente: 'Carlos',
            apellido: 'Gardel'
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso: null, proximoEvento, esAdmin: false },
            global: { stubs: globalStubs, directives }
        });

        const btnConAviso = wrapper.findAll('button').find((b) => b.text().includes('Con aviso'));
        expect(btnConAviso).toBeTruthy();
        await btnConAviso.trigger('click');

        expect(wrapper.emitted('cambiarAsistencia')).toBeTruthy();
        expect(wrapper.emitted('cambiarAsistencia')[0][0]).toEqual({
            turnoId: 25,
            estado: 'con_aviso'
        });
    });

    it('muestra el próximo turno programado con botón Marcar Presente cuando no hay paciente en curso', async () => {
        const proximoEvento = {
            id: 20,
            tipo: 'Turno',
            paciente_id: 50,
            paciente: 'Marta',
            apellido: 'Sanchez',
            dni: '23456789',
            nro_hc: 'HC-101',
            cobertura: 'Swiss Medical',
            fecha_inicio: '2026-10-14T11:00:00',
            fecha_fin: '2026-10-14T11:30:00',
            motivo: 'Evaluacion inicial'
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso: null, proximoEvento, esAdmin: false },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Próximo Turno en Agenda');
        expect(wrapper.text()).toContain('Marta Sanchez');
        expect(wrapper.text()).toContain('HC: HC-101');
        expect(wrapper.text()).toContain('Evaluacion inicial');

        const btnPresente = wrapper.findAll('button').find((b) => b.text().includes('Marcar Presente'));
        expect(btnPresente).toBeTruthy();
        await btnPresente.trigger('click');

        expect(wrapper.emitted('cambiarAsistencia')).toBeTruthy();
        expect(wrapper.emitted('cambiarAsistencia')[0][0]).toEqual({
            turnoId: 20,
            estado: 'presente'
        });
    });

    it('muestra estado vacío cuando no hay turnos ni eventos', async () => {
        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso: null, proximoEvento: null },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Sin turnos pendientes hoy');

        const btnAgenda = wrapper.findAll('button').find((b) => b.text().includes('Abrir agenda'));
        expect(btnAgenda).toBeTruthy();
        await btnAgenda.trigger('click');

        expect(wrapper.emitted('verAgenda')).toBeTruthy();
    });

    it('muestra eventos no-turno (reuniones/ausencias) correctamente', () => {
        const proximoEvento = {
            tipo: 'Reunion',
            titulo: 'Reunion de Area',
            detalle: 'Revision de casos clinicos',
            fecha_inicio: '2026-10-14T15:00:00',
            fecha_fin: '2026-10-14T16:00:00'
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso: null, proximoEvento },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Próximo Evento de Agenda');
        expect(wrapper.text()).toContain('Reunion de Area');
        expect(wrapper.text()).toContain('Revision de casos clinicos');
    });

    it('muestra la insignia de Sobreturno si turnoEnCurso es sobreturno', () => {
        const turnoEnCurso = {
            id: 10,
            paciente_id: 42,
            paciente: 'Carlos',
            apellido: 'Gardel',
            es_sobreturno: true
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso, proximoEvento: null, esAdmin: false },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Sobreturno');
    });

    it('muestra la insignia de Sobreturno si proximoEvento es sobreturno', () => {
        const proximoEvento = {
            id: 25,
            tipo: 'Turno',
            paciente_id: 42,
            paciente: 'Carlos',
            apellido: 'Gardel',
            es_sobreturno: true
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: { turnoEnCurso: null, proximoEvento, esAdmin: false },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Sobreturno');
    });

    it('muestra Atenciones en Curso para perfil director con consultas activas y profesional asignado', async () => {
        const atencionesEnCurso = [
            {
                id: 101,
                paciente_id: 42,
                paciente: 'Carlos',
                apellido: 'Gardel',
                dni: '12345678',
                nro_hc: 'HC-99',
                cobertura: 'OSDE',
                nro_afiliado: 'AF-123456/01',
                fecha_inicio: '2026-10-16T10:00:00',
                fecha_fin: '2026-10-16T10:30:00',
                motivo: 'Control cardiológico',
                profesional: 'Dr. Geronimo Gauna'
            },
            {
                id: 102,
                paciente_id: 43,
                paciente: 'Marta',
                apellido: 'Sanchez',
                dni: '87654321',
                nro_hc: 'HC-100',
                cobertura: 'Swiss Medical',
                fecha_inicio: '2026-10-16T10:00:00',
                fecha_fin: '2026-10-16T10:30:00',
                motivo: 'Evaluación fonoaudiológica',
                profesional: 'Lic. Diaz'
            }
        ];

        const wrapper = mount(ProximoTurnoWidget, {
            props: {
                turnoEnCurso: null,
                atencionesEnCurso,
                proximoEvento: null,
                esAdmin: true,
                esDirector: true
            },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Atenciones en Curso');
        expect(wrapper.text()).not.toContain('Atención en Curso');
        expect(wrapper.text()).toContain('Dr. Geronimo Gauna');
        expect(wrapper.text()).toContain('Lic. Diaz');
        expect(wrapper.text()).toContain('Carlos Gardel');
        expect(wrapper.text()).toContain('Marta Sanchez');
        expect(wrapper.text()).toContain('2 en atención');

        const btnHistorias = wrapper.findAll('button').filter((b) => b.text().includes('Abrir Historia'));
        expect(btnHistorias.length).toBe(2);
        await btnHistorias[0].trigger('click');

        expect(wrapper.emitted('verHistoria')).toBeTruthy();
        expect(wrapper.emitted('verHistoria')[0][0]).toEqual(atencionesEnCurso[0]);
    });

    it('muestra Atenciones en Curso con estado sin atenciones para director cuando no hay pacientes en curso', () => {
        const proximoEvento = {
            id: 105,
            tipo: 'Turno',
            paciente: 'Roberto',
            apellido: 'Perez',
            fecha_inicio: '2026-10-16T11:00:00',
            fecha_fin: '2026-10-16T11:20:00',
            profesional: 'Dr. Gauna'
        };

        const wrapper = mount(ProximoTurnoWidget, {
            props: {
                turnoEnCurso: null,
                atencionesEnCurso: [],
                proximoEvento,
                esAdmin: true,
                esDirector: true
            },
            global: { stubs: globalStubs, directives }
        });

        expect(wrapper.text()).toContain('Atenciones en Curso');
        expect(wrapper.text()).not.toContain('Atención en Curso');
        expect(wrapper.text()).toContain('Sin atenciones activas');
        expect(wrapper.text()).toContain('Sin atenciones simultáneas en curso');
        expect(wrapper.text()).toContain('Próximo turno en institución');
        expect(wrapper.text()).toContain('Roberto Perez');
        expect(wrapper.text()).toContain('Dr. Gauna');
    });
});
