-- Migracion a BFA TSA API.
-- Los recibos de la TSA (temporary_rd / permanent_rd) son cadenas Base64 extensas,
-- mucho mas largas que un tx hash de 66 caracteres. Ampliamos las columnas que los
-- guardan a VARCHAR(512).

ALTER TABLE historias
    MODIFY tx_hash VARCHAR(512) DEFAULT NULL;

ALTER TABLE evoluciones
    MODIFY tx_hash VARCHAR(512) DEFAULT NULL;

-- Nota: recetas_electronicas NO se ancla en BFA (solo historias y evoluciones),
-- y en DBs migradas la tabla no tiene columna tx_hash. No la tocamos.

ALTER TABLE auditorias_blockchain
    MODIFY tx_hash VARCHAR(512) DEFAULT NULL,
    MODIFY hash_bfa VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL;
