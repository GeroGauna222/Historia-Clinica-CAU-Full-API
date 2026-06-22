ALTER TABLE historias
    ADD COLUMN fecha_anclaje_bfa DATETIME DEFAULT NULL,
    ADD COLUMN estado_bfa VARCHAR(20) NOT NULL DEFAULT 'pendiente';

ALTER TABLE evoluciones
    ADD COLUMN hash_local CHAR(64) DEFAULT NULL,
    ADD COLUMN tx_hash VARCHAR(100) DEFAULT NULL,
    ADD COLUMN fecha_anclaje_bfa DATETIME DEFAULT NULL,
    ADD COLUMN estado_bfa VARCHAR(20) NOT NULL DEFAULT 'pendiente';

ALTER TABLE auditorias_blockchain
    MODIFY historia_id INT NULL,
    ADD COLUMN evolucion_id INT NULL,
    ADD COLUMN entidad_tipo VARCHAR(20) NOT NULL DEFAULT 'historia',
    ADD COLUMN entidad_id INT NULL,
    ADD COLUMN tx_hash VARCHAR(100) DEFAULT NULL,
    ADD CONSTRAINT fk_auditorias_blockchain_evolucion
        FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id) ON DELETE CASCADE;
