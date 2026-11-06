-- Unifica collation de turnos_grupales a utf8mb4_unicode_ci para permitir
-- UNION ALL transparente con la tabla turnos en consultas de agenda y dashboard.
ALTER TABLE turnos_grupales CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
