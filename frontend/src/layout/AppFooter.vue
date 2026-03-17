<script setup>
// Footer simple — sin lógica adicional
</script>

<template>
    <footer class="app-footer">
        <div class="footer-content">
            © 2025
            <span class="brand">Historia Clínica CAU</span> — Desarrollado por <span class="author">Héctor Venero</span> con aporte de <span class="author">Gerónimo Gauna</span> | Universidad Nacional de San Martín (UNSAM)
        </div>
    </footer>
</template>

<style scoped>
.app-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 40px;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 13px;
    z-index: 100;
    border-top: 1px solid var(--footer-border);
    background-color: var(--footer-bg);
    color: var(--footer-text);
    transition:
        background-color 0.3s ease,
        color 0.3s ease;
}

.footer-content {
    text-align: center;
    line-height: 1.5;
}

/* Colores institucionales */
.brand {
    color: var(--footer-brand);
    font-weight: 600;
}

.author {
    color: var(--footer-author);
    font-weight: 600;
}

/* ====== 🎨 Tema claro ====== */
:root {
    --footer-bg: #f9fafb;
    --footer-border: #e5e7eb;
    --footer-text: #6b7280;
    --footer-brand: #003b70;
    --footer-author: #00936b;
}

/* ====== 🌙 Tema oscuro ====== */
.app-dark .app-footer,
html.dark .app-footer {
    --footer-bg: #1a1a1a;
    --footer-border: #2e2e2e;
    --footer-text: #e0e0e0;
    --footer-brand: #3db5e6; /* celeste institucional */
    --footer-author: #00bfa5; /* verde turquesa */
}
</style>
