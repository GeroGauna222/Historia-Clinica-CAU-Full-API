-- Correct the corrupted positive ENUM label restored from historical backups.
-- The application already writes the correct UTF-8 value `Sí`.
ALTER TABLE pacientes
    MODIFY COLUMN cert_discapacidad ENUM('Sí', 'No')
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL;
