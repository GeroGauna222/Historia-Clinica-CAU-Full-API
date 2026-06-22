ALTER TABLE recetas_electronicas ADD COLUMN tipo ENUM('receta', 'estudio') NOT NULL DEFAULT 'receta' AFTER usuario_id;
ALTER TABLE recetas_electronicas ADD COLUMN qbitos_endpoint VARCHAR(120) DEFAULT NULL AFTER tipo;
CREATE INDEX idx_recetas_tipo ON recetas_electronicas (tipo);
