-- Migración: Swiss Medical (SMG) - IVA, Asistencia Adicional y Catálogo de Prácticas
-- Fecha: 2026-11-05

ALTER TABLE facturacion_registros
    ADD COLUMN iva VARCHAR(20) NOT NULL DEFAULT 'OBLIGATORIO',
    ADD COLUMN es_asistencia_adicional TINYINT(1) NOT NULL DEFAULT 0;

-- Catálogo de prácticas iniciales Swiss Medical (Valores Septiembre 2026)
INSERT INTO facturacion_practicas (financiador, categoria, codigo, descripcion, importe, requiere_autorizacion) VALUES
('swiss_medical', 'Discapacidad', '25040101', 'Kinesiología para DISCAPACIDAD', 19972.09, 1),
('swiss_medical', 'Discapacidad', '25040104', 'Terapia Ocupacional DISCAPACIDAD', 19972.09, 1),
('swiss_medical', 'Discapacidad', '25040110', 'Rehabilitación - Modulo Integral Simple (semanal)', 105701.06, 1),
('swiss_medical', 'Discapacidad', '25040112', 'Rehabilitación - Hosp de Día Jornada Simple (mensual)', 631882.70, 1),
('swiss_medical', 'Discapacidad', '45020101', 'Fonoaudiología para DISCAPACIDAD', 19972.08, 1),
('swiss_medical', 'Discapacidad', '45030101', 'Psicoterapia para DISCAPACIDAD', 19972.08, 1),
('swiss_medical', 'Discapacidad', '45030102', 'Psicopedagogía para DISCAPACIDAD', 19972.08, 1),
('swiss_medical', 'Prestaciones CAU', '43330102', 'Hospital de día Jornada Simple (+ de 2 veces por semana)', 12071.46, 1),
('swiss_medical', 'Prestaciones CAU', '12180101', 'Infiltración con Toxina Botulinica', 33213.85, 1),
('swiss_medical', 'Consultas', '42011200', 'Consulta Traumatología', 8720.09, 1),
('swiss_medical', 'Consultas', '42012500', 'Consulta Fisiatría', 8720.09, 1),
('swiss_medical', 'Consultas', '42012900', 'Consulta Neuropediatría', 8720.09, 1),
('swiss_medical', 'Consultas', '42013000', 'Consulta Oftalmología', 8720.09, 1),
('swiss_medical', 'Consultas', '42011700', 'Consulta Cardiología', 13259.56, 1),
('swiss_medical', 'Consultas', '42012201', 'Consulta Ginecología', 13564.20, 1),
('swiss_medical', 'Prácticas', '25010212', 'Módulo Fisio-Kinesio-Laser-Magnetoterapia', 5651.99, 1),
('swiss_medical', 'Prácticas', '25010230', 'Técnicas de corrección postural', 9899.46, 1),
('swiss_medical', 'Prácticas', '150106', 'Citologia exfoliativa oncologica.', 5093.26, 1),
('swiss_medical', 'Prácticas', '170101', 'Electrocardiograma en consultorio -con o sin prueba de esfuerzo-.', 6314.12, 1),
('swiss_medical', 'Prácticas', '17011801', 'Holter de presión o Presurometría', 18188.66, 1),
('swiss_medical', 'Prácticas', '17011805', 'Holter 3 canales', 20967.65, 1),
('swiss_medical', 'Prácticas', '18010303', 'Ecodoppler color', 37884.55, 1);
