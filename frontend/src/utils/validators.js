// ------------------------------
//  VALIDACIÓN DE CONTRASEÑA
//  (igual que el backend Flask)
// ------------------------------
export function validarPasswordFuerte(pw) {
    if (!pw) return 'La contraseña es obligatoria';
    if (pw.length < 8) return 'Debe tener al menos 8 caracteres';
    if (!/[A-Z]/.test(pw)) return 'Debe contener una mayúscula';
    if (!/[a-z]/.test(pw)) return 'Debe contener una minúscula';
    if (!/[0-9]/.test(pw)) return 'Debe contener un número';
    if (!/[^A-Za-z0-9]/.test(pw)) return 'Debe contener un símbolo (!@#$%&*)';

    return ''; // válida
}

// ------------------------------
// VALIDACIÓN DE EMAIL
// ------------------------------
export function validarEmail(email) {
    const patron = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return patron.test(email);
}
