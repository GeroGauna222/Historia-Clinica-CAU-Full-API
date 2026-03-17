-- Migration manual para entornos existentes (no limpia tablas).
-- Fecha: 2026-03-14

USE hc_bfa;

ALTER TABLE grupos_profesionales
ADD COLUMN IF NOT EXISTS es_rehabilitacion TINYINT(1) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS turnos_grupales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    grupo_id INT NOT NULL,
    paciente_id INT NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo VARCHAR(255),
    creado_por INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (grupo_id) REFERENCES grupos_profesionales(id) ON DELETE CASCADE,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (creado_por) REFERENCES usuarios(id),
    INDEX idx_turnos_grupales_grupo (grupo_id),
    INDEX idx_turnos_grupales_rango (fecha_inicio, fecha_fin)
);
