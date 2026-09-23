<script setup>
import { useLayout } from '@/layout/composables/layout';
import UserMenu from '@/components/dashboard/UserMenu.vue';
import PacientesPresentesMenu from '@/components/dashboard/PacientesPresentesMenu.vue';
import ColorSchemeSwitcher from '@/components/ui/ColorSchemeSwitcher.vue';
import { useRouter } from 'vue-router';

const { toggleMenu } = useLayout();
const router = useRouter();

// 👉 Ir a Agenda
function irAgenda() {
    router.push('/turnos');
}
</script>

<template>
    <div class="layout-topbar">
        <!-- ◀️ Logo + menú -->
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>

            <router-link to="/" class="layout-topbar-logo flex items-center gap-2">
                <img src="@/assets/cau_icon.png" alt="Logo CAU" class="h-8 md:h-10" />
                <div class="flex flex-col leading-tight">
                    <div class="font-bold text-lg">CAU <span class="font-normal">UNSAM</span></div>
                    <div class="text-xs text-muted-color">Centro Asistencial Universitario</div>
                </div>
            </router-link>
        </div>

        <!-- ▶️ Acciones -->
        <div class="layout-topbar-actions flex items-center gap-4">
            <!-- 👥 Pacientes en recepción -->
            <PacientesPresentesMenu />

            <!-- 🧭 Agenda directo -->
            <button type="button" class="layout-topbar-action" @click="irAgenda">
                <i class="pi pi-calendar"></i>
            </button>

            <!-- Color scheme (Sistema / Claro / Oscuro) -->
            <ColorSchemeSwitcher />

            <!-- 👤 Nuevo menú de usuario (foto + perfil + logout) -->
            <UserMenu />
        </div>
    </div>
</template>

<style scoped>
.layout-topbar-logo img {
    max-height: 40px;
}
</style>
