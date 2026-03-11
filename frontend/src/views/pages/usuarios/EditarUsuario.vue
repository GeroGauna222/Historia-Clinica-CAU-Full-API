<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import usuarioService from '@/service/usuarioService';

const route = useRoute();
const userId = route.params.id;

const form = reactive({
    nombre: '',
    username: '',
    email: '',
    rol: '',
    especialidad: '',
    password: ''
});

const ROLES = ['director', 'profesional', 'administrativo'];
const showPwd = ref(false);
const loading = ref(false);
const error = ref('');
const ok = ref('');

// Cargar datos del usuario
onMounted(async () => {
    try {
        loading.value = true;
        const res = await usuarioService.getUsuario(userId);
        Object.assign(form, res.data); // cargar datos existentes
    } catch (e) {
        error.value = '❌ Error cargando usuario';
    } finally {
        loading.value = false;
    }
});

async function onSubmit() {
    error.value = '';
    ok.value = '';
    loading.value = true;

    try {
        // preparar payload (sin enviar password si está vacío)
        const payload = { ...form };
        if (!payload.password) delete payload.password;

        await usuarioService.updateUsuario(userId, payload);
        ok.value = 'Usuario actualizado ✅';
        form.password = ''; // limpiar password
    } catch (e) {
        error.value = e.response?.data?.error || e.message || 'Error al actualizar usuario';
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="flex justify-center items-start p-8">
        <div class="bg-white shadow-xl rounded-2xl p-8 w-full max-w-2xl">
            <h1 class="text-3xl font-bold text-center mb-8 text-blue-700">Editar usuario</h1>

            <form @submit.prevent="onSubmit" class="space-y-6">
                <!-- Nombre -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Nombre completo</label>
                    <input v-model.trim="form.nombre" type="text" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" :disabled="loading" required />
                </div>

                <!-- Usuario -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Usuario</label>
                    <input v-model.trim="form.username" type="text" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" :disabled="loading" required />
                </div>

                <!-- Email -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Email</label>
                    <input v-model.trim="form.email" type="email" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" :disabled="loading" required />
                </div>

                <!-- Contraseña (opcional) -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Nueva contraseña (opcional)</label>
                    <div class="flex gap-2">
                        <input v-model="form.password" :type="showPwd ? 'text' : 'password'" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" placeholder="********" :disabled="loading" />
                        <button type="button" class="px-4 py-2 border rounded-xl shadow-sm bg-gray-50 hover:bg-gray-100" @click="showPwd = !showPwd" :disabled="loading">
                            {{ showPwd ? 'Ocultar' : 'Ver' }}
                        </button>
                    </div>
                </div>

                <!-- Rol -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Rol</label>
                    <select v-model="form.rol" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" :disabled="loading" required>
                        <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
                    </select>
                </div>

                <!-- Especialidad -->
                <div v-if="form.rol === 'profesional'">
                    <label class="block mb-2 font-semibold text-gray-700">Especialidad</label>
                    <input v-model.trim="form.especialidad" type="text" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" :disabled="loading" required />
                </div>

                <!-- Mensajes -->
                <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm">
                    {{ error }}
                </div>
                <div v-if="ok" class="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">
                    {{ ok }}
                </div>

                <!-- Botón -->
                <div class="flex justify-center pt-4">
                    <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl shadow-lg transition disabled:opacity-60" :disabled="loading">
                        {{ loading ? 'Guardando…' : 'Guardar cambios' }}
                    </button>
                </div>
            </form>
        </div>
    </div>
</template>
