<script setup>
import { FilterMatchMode } from '@primevue/core/api';
import api from '@/api/axios';
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const dni = ref('');
const nombre = ref('');
const apellido = ref('');
const nroHc = ref('');
const pacientes = ref([]);
const mensaje = ref('Podés buscar con un solo campo (no hace falta llenarlos todos).');
const loading = ref(false);
const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS }
});

const router = useRouter();

const buscarPacientes = async () => {
    if (!dni.value && !nombre.value && !apellido.value && !nroHc.value) {
        mensaje.value = '⚠️ Ingresá al menos un dato para buscar.';
        pacientes.value = [];
        return;
    }

    let query = dni.value || nombre.value || apellido.value || nroHc.value;

    try {
        loading.value = true;
        mensaje.value = '';
        const res = await api.get(`/pacientes/buscar?q=${encodeURIComponent(query)}`, {
            withCredentials: true
        });
        pacientes.value = res.data.pacientes;

        if (pacientes.value.length === 0) {
            mensaje.value = 'No se encontraron pacientes.';
        }
    } catch (error) {
        console.error(error);
        mensaje.value = 'Error al buscar pacientes.';
    } finally {
        loading.value = false;
    }
};

const columns = [
    { field: 'apellido', header: 'Apellido' },
    { field: 'nombre', header: 'Nombre' },
    { field: 'dni', header: 'DNI' },
    { field: 'nro_hc', header: 'HC' }
];

const verHistoria = (id) => {
    router.push(`/pacientes/${id}/historias`);
};
</script>

<template>
    <div class="p-4">
        <h1 class="text-2xl font-bold mb-4">Buscar Pacientes</h1>

        <p class="text-sm text-gray-500 mb-2">{{ mensaje }}</p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <input v-model="dni" placeholder="DNI" class="p-2 border rounded" />
            <input v-model="nombre" placeholder="Nombre" class="p-2 border rounded" />
            <input v-model="apellido" placeholder="Apellido" class="p-2 border rounded" />
            <input v-model="nroHc" placeholder="Nro Historia Clínica" class="p-2 border rounded" />
        </div>

        <Button label="Buscar" @click="buscarPacientes" class="mb-4" :loading="loading" />
        <DataTable
            :value="pacientes"
            :paginator="true"
            :rows="5"
            dataKey="id"
            :filters="filters"
            filterDisplay="row"
            paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
            :rowsPerPageOptions="[5, 10, 25]"
            currentPageReportTemplate="Mostrando {first} a {last} de {totalRecords} pacientes"
            :loading="loading"
            @row-click="verHistoria($event.data.id)"
            class="cursor-pointer"
        >
            <Column v-for="col in columns" :key="col.field" :field="col.field" :header="col.header" sortable></Column>
        </DataTable>
    </div>
</template>
