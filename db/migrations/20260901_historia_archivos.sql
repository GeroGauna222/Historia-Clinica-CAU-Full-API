-- Documentos externos y estudios adjuntos directamente a la historia clínica.
-- Son append-only: cada carga conserva usuario, fecha y hash SHA-256.

CREATE TABLE historia_archivos (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    nombre_original VARCHAR(255) NOT NULL,
    nombre_almacenado VARCHAR(255) NOT NULL,
    ruta_relativa VARCHAR(512) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    tamanio_bytes BIGINT UNSIGNED NOT NULL,
    hash_sha256 CHAR(64) NOT NULL,
    cargado_en DATETIME(6) NOT NULL,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_historia_archivos_paciente_fecha (paciente_id, cargado_en),
    INDEX idx_historia_archivos_hash (hash_sha256)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
