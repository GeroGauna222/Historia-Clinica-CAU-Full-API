-- Migración: estado_asistencia en turnos y turnos_grupales
-- Fecha: 2026-09-15
-- Propósito: Implementar máquina de estados de asistencia (programado, presente, con_aviso, sin_aviso)

ALTER TABLE turnos
    ADD COLUMN estado_asistencia ENUM('programado', 'presente', 'con_aviso', 'sin_aviso') NOT NULL DEFAULT 'programado';

ALTER TABLE turnos_grupales
    ADD COLUMN estado_asistencia ENUM('programado', 'presente', 'con_aviso', 'sin_aviso') NOT NULL DEFAULT 'programado';

-- Sincronizar datos históricos existentes basados en ausencia
UPDATE turnos SET estado_asistencia = CASE
    WHEN ausencia = 'con_aviso' THEN 'con_aviso'
    WHEN ausencia = 'sin_aviso' THEN 'sin_aviso'
    ELSE 'programado'
END;

UPDATE turnos_grupales SET estado_asistencia = CASE
    WHEN ausencia = 'con_aviso' THEN 'con_aviso'
    WHEN ausencia = 'sin_aviso' THEN 'sin_aviso'
    ELSE 'programado'
END;
