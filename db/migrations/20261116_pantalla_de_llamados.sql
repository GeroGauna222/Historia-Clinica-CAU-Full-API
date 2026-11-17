-- Pantalla de llamados: consultorio y visibilidad en profesionales y grupos,
-- atencion en turnos, y registro de televisores vinculados.
-- Fecha: 2026-11-16

ALTER TABLE usuarios
    ADD COLUMN consultorio VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
    ADD COLUMN mostrar_en_pantalla TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE grupos_profesionales
    ADD COLUMN consultorio VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
    ADD COLUMN mostrar_en_pantalla TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE turnos
    ADD COLUMN atencion_inicio DATETIME NULL,
    ADD COLUMN atencion_fin DATETIME NULL;

ALTER TABLE turnos_grupales
    ADD COLUMN atencion_inicio DATETIME NULL,
    ADD COLUMN atencion_fin DATETIME NULL;

CREATE TABLE pantallas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NULL,
    codigo VARCHAR(6) NULL,
    codigo_expira DATETIME NULL,
    clave_hash CHAR(64) NOT NULL,
    vinculada_en DATETIME NULL,
    vinculada_por INT NULL,
    revocada_en DATETIME NULL,
    ultimo_acceso DATETIME NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_pantallas_codigo (codigo),
    UNIQUE KEY uq_pantallas_clave_hash (clave_hash),
    FOREIGN KEY (vinculada_por) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
