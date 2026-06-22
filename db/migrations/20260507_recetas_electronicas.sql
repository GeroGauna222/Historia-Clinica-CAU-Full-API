CREATE TABLE IF NOT EXISTS recetas_electronicas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    qbitos_id_receta VARCHAR(100) DEFAULT NULL,
    qbitos_s3_link TEXT DEFAULT NULL,
    qbitos_verificador TEXT DEFAULT NULL,
    id_transaccion VARCHAR(100) DEFAULT NULL,
    estado VARCHAR(50) DEFAULT NULL,
    financiador_nombre VARCHAR(150) DEFAULT NULL,
    afiliado_numero VARCHAR(40) DEFAULT NULL,
    request_json JSON NOT NULL,
    response_json JSON DEFAULT NULL,
    error_json JSON DEFAULT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_recetas_paciente (paciente_id),
    INDEX idx_recetas_usuario (usuario_id),
    INDEX idx_recetas_qbitos_id (qbitos_id_receta)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
