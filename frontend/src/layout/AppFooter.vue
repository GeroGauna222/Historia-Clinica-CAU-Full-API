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
    border-top: 1px solid var(--p-content-border-color);
    background-color: var(--p-content-background);
    color: var(--p-text-muted-color);
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
    color: var(--p-primary-color);
    font-weight: 600;
}

.author {
    color: var(--p-primary-color);
    font-weight: 600;
}
</style>
