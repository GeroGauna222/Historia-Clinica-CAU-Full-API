// src/stores/user.js
import { defineStore } from 'pinia';
import { emit } from '@/utils/eventBus';
import usuarioService from '@/service/usuarioService';

export const useUserStore = defineStore('user', {
    state: () => ({
        id: null,
        nombre: '',
        username: '',
        rol: '',
        email: '',
        duracion_turno: 20,
        foto: null,
        especialidad: '',
        dni: '',
        sexo: '',
        telefono: '',
        matricula_tipo: '',
        matricula_numero: '',
        matricula_provincia: '',
        lugar_atencion_nombre: '',
        lugar_atencion_direccion: '',
        lugar_atencion_contacto: '',
        lugar_atencion_email: '',
        fotoVersion: Date.now(),
        loggingOut: false
    }),

    actions: {
        setUser(data) {
            this.id = data.id ?? null;
            this.nombre = data.nombre ?? '';
            this.username = data.username ?? '';
            this.rol = data.rol?.toLowerCase().trim() || ''; // Normalizamos rol
            this.email = data.email ?? '';
            this.duracion_turno = data.duracion_turno ?? this.duracion_turno;
            this.foto = data.foto ?? null;
            this.especialidad = data.especialidad ?? '';
            this.dni = data.dni ?? '';
            this.sexo = data.sexo ?? '';
            this.telefono = data.telefono ?? '';
            this.matricula_tipo = data.matricula_tipo ?? '';
            this.matricula_numero = data.matricula_numero ?? '';
            this.matricula_provincia = data.matricula_provincia ?? '';
            this.lugar_atencion_nombre = data.lugar_atencion_nombre ?? '';
            this.lugar_atencion_direccion = data.lugar_atencion_direccion ?? '';
            this.lugar_atencion_contacto = data.lugar_atencion_contacto ?? '';
            this.lugar_atencion_email = data.lugar_atencion_email ?? '';
            this.loggingOut = false;

            console.log('✅ Usuario cargado en store:', this.$state);
            emit('user:updated', { ...this.$state });
        },

        async fetchUser() {
            try {
                const res = await usuarioService.getUsuario('me');
                this.setUser(res.data);
                return res.data;
            } catch (err) {
                console.error('❌ Error cargando usuario:', err);
                throw err;
            }
        },

        recargarImagen() {
            this.fotoVersion = Date.now();
        },

        async actualizarDuracion(nuevaDuracion) {
            try {
                await usuarioService.actualizarDuracion(this.id, nuevaDuracion);
                this.duracion_turno = nuevaDuracion;
            } catch (err) {
                console.error('❌ Error actualizando duración:', err);
                throw err;
            }
        },

        startLogout() {
            this.loggingOut = true;
        },

        logout() {
            this.$reset();
            emit('user:loggedOut');
        }
    },

    getters: {
        isDirector: (state) => state.rol === 'director',
        isProfesional: (state) => state.rol === 'profesional',
        isAdministrativo: (state) => state.rol === 'administrativo'
    }
});
