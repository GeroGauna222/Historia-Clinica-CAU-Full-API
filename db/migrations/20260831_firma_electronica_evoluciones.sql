-- Firma electrónica y trazabilidad de actuaciones clínicas.
-- Las matrículas existentes quedan pendientes de validación explícita por CAU
-- (matricula_verificada = 0) para evitar firmar con datos no comprobados.

ALTER TABLE usuarios
    ADD COLUMN matricula_verificada TINYINT(1) NOT NULL DEFAULT 0 AFTER matricula_provincia,
    ADD COLUMN matricula_verificada_en DATETIME(6) DEFAULT NULL AFTER matricula_verificada,
    ADD COLUMN matricula_verificada_por INT DEFAULT NULL AFTER matricula_verificada_en;

ALTER TABLE evoluciones
    ADD COLUMN estado_firma ENUM('pendiente', 'firmada') NOT NULL DEFAULT 'pendiente' AFTER estado_bfa,
    ADD COLUMN firmado_en DATETIME(6) DEFAULT NULL AFTER estado_firma,
    ADD COLUMN motivo_rectificacion TEXT DEFAULT NULL AFTER firmado_en;

CREATE TABLE autenticacion_eventos (
    id CHAR(36) PRIMARY KEY,
    usuario_id INT NOT NULL,
    autenticado_en DATETIME(6) NOT NULL,
    ip VARCHAR(45) DEFAULT NULL,
    user_agent VARCHAR(512) DEFAULT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_autenticacion_usuario_fecha (usuario_id, autenticado_en)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE firmas_electronicas (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    evolucion_id INT NOT NULL UNIQUE,
    usuario_id INT NOT NULL,
    autenticacion_evento_id CHAR(36) NOT NULL,
    rol VARCHAR(30) NOT NULL,
    matricula_tipo VARCHAR(10) NOT NULL,
    matricula_numero VARCHAR(50) NOT NULL,
    matricula_provincia VARCHAR(100) DEFAULT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'electronica',
    algoritmo VARCHAR(30) NOT NULL DEFAULT 'SHA-256',
    payload_version VARCHAR(20) NOT NULL DEFAULT 'evolucion-v1',
    payload_hash CHAR(64) NOT NULL,
    firmado_en DATETIME(6) NOT NULL,
    ip VARCHAR(45) DEFAULT NULL,
    user_agent VARCHAR(512) DEFAULT NULL,
    FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (autenticacion_evento_id) REFERENCES autenticacion_eventos(id),
    INDEX idx_firmas_usuario_fecha (usuario_id, firmado_en),
    INDEX idx_firmas_hash (payload_hash)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE auditorias_clinicas (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    evolucion_id INT NOT NULL,
    usuario_id INT NOT NULL,
    accion ENUM('firma', 'rectificacion') NOT NULL,
    version INT NOT NULL,
    detalle_json JSON DEFAULT NULL,
    creado_en DATETIME(6) NOT NULL,
    FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_auditoria_clinica_evolucion (evolucion_id, creado_en),
    INDEX idx_auditoria_clinica_usuario (usuario_id, creado_en)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
