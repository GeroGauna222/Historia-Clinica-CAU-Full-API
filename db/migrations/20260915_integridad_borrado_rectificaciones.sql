-- Preserve clinical-document traceability when deleting patients and serialize
-- the version sequence of concurrent evolution rectifications.

SET @historia_archivos_paciente_fk = (
    SELECT CONSTRAINT_NAME
    FROM information_schema.KEY_COLUMN_USAGE
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'historia_archivos'
      AND COLUMN_NAME = 'paciente_id'
      AND REFERENCED_TABLE_NAME = 'pacientes'
    LIMIT 1
);

SET @drop_historia_archivos_paciente_fk = IF(
    @historia_archivos_paciente_fk IS NULL,
    'SELECT 1',
    CONCAT(
        'ALTER TABLE historia_archivos DROP FOREIGN KEY `',
        REPLACE(@historia_archivos_paciente_fk, '`', '``'),
        '`'
    )
);

PREPARE drop_historia_archivos_paciente_fk
    FROM @drop_historia_archivos_paciente_fk;
EXECUTE drop_historia_archivos_paciente_fk;
DEALLOCATE PREPARE drop_historia_archivos_paciente_fk;

ALTER TABLE historia_archivos
    ADD CONSTRAINT fk_historia_archivos_paciente
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE RESTRICT;

ALTER TABLE evoluciones
    ADD CONSTRAINT uq_evoluciones_padre_version
    UNIQUE (padre_id, version);
