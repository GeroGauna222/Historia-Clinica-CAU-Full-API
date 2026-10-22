-- Migración: es_sobreturno en tabla turnos
-- Fecha: 2026-10-22

ALTER TABLE turnos
    ADD COLUMN es_sobreturno TINYINT(1) NOT NULL DEFAULT 0;
