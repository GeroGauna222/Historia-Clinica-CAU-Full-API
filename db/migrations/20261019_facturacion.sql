CREATE TABLE IF NOT EXISTS facturacion_practicas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    financiador VARCHAR(50) NOT NULL,
    categoria VARCHAR(100) DEFAULT 'General',
    codigo VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    importe DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    requiere_autorizacion TINYINT(1) NOT NULL DEFAULT 1,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_facturacion_practicas_financiador (financiador, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS facturacion_prestadores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    financiador VARCHAR(50) NOT NULL DEFAULT 'medicus',
    nombre VARCHAR(150) NOT NULL,
    contexto VARCHAR(10) NOT NULL DEFAULT 'A',
    lugar_realizacion_efector VARCHAR(50) NOT NULL,
    tipo_matricula VARCHAR(10) NOT NULL DEFAULT 'P',
    nro_matricula VARCHAR(50) NOT NULL,
    profe_interior_codigo VARCHAR(50) DEFAULT NULL,
    profe_interior_nombre VARCHAR(150) DEFAULT NULL,
    es_predeterminado TINYINT(1) NOT NULL DEFAULT 0,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_facturacion_prestadores_financiador (financiador, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS facturacion_registros (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    financiador VARCHAR(50) NOT NULL,
    fecha_realizacion DATE NOT NULL,
    paciente_id INT DEFAULT NULL,
    paciente_nombre VARCHAR(200) NOT NULL,
    nro_afiliado VARCHAR(100) NOT NULL,
    tipo_doc_afiliado VARCHAR(20) DEFAULT NULL,
    nro_doc_afiliado VARCHAR(30) DEFAULT NULL,
    cud ENUM('SI', 'NO') NOT NULL DEFAULT 'NO',
    cantidad INT NOT NULL DEFAULT 1,
    practica_id INT DEFAULT NULL,
    practica_codigo VARCHAR(100) NOT NULL,
    practica_descripcion VARCHAR(255) NOT NULL,
    importe DECIMAL(12, 2) NOT NULL,
    gastos DECIMAL(12, 2) DEFAULT NULL,
    autorizacion VARCHAR(100) DEFAULT NULL,
    prestador_id INT DEFAULT NULL,
    contexto VARCHAR(10) DEFAULT 'A',
    internacion VARCHAR(50) DEFAULT NULL,
    orden VARCHAR(50) DEFAULT NULL,
    grupo VARCHAR(50) DEFAULT NULL,
    lugar_realizacion_efector VARCHAR(50) DEFAULT NULL,
    tipo_matricula VARCHAR(10) DEFAULT NULL,
    nro_matricula VARCHAR(50) DEFAULT NULL,
    observaciones VARCHAR(255) DEFAULT NULL,
    creado_por INT DEFAULT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE SET NULL,
    FOREIGN KEY (practica_id) REFERENCES facturacion_practicas(id) ON DELETE SET NULL,
    FOREIGN KEY (prestador_id) REFERENCES facturacion_prestadores(id) ON DELETE SET NULL,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_facturacion_registros_fin_fecha (financiador, fecha_realizacion),
    INDEX idx_facturacion_registros_paciente (paciente_id),
    INDEX idx_facturacion_registros_practica (practica_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO facturacion_prestadores (financiador, nombre, contexto, lugar_realizacion_efector, tipo_matricula, nro_matricula, es_predeterminado)
SELECT 'medicus', 'CENTRO ASISTENCIAL UNIVERSITARIO (OSUNSAM)', 'A', 'E171513', 'P', '441983', 1
WHERE NOT EXISTS (SELECT 1 FROM facturacion_prestadores LIMIT 1);

INSERT INTO facturacion_practicas (financiador, categoria, codigo, descripcion, importe, requiere_autorizacion)
SELECT * FROM (
    SELECT 'medicus' AS financiador, 'Consulta' AS categoria, '2420101' AS codigo, 'CONSULTA MEDICA' AS descripcion, 7915.62 AS importe, 1 AS requiere_autorizacion
    UNION ALL SELECT 'medicus', 'Consulta', '2421001', 'CONSULTA MEDICA (2421001)', 7915.62, 1
    UNION ALL SELECT 'medicus', 'Consulta', '9042500200', 'CONSULTA COMPLETA OFTALMOLOGICA', 8905.07, 1
    UNION ALL SELECT 'medicus', 'Consulta', '12420106', 'CONSULTA NEUROLOGICA INFANTIL', 9894.52, 1
    UNION ALL SELECT 'medicus', 'Consulta', '12420109', 'CONSULTA CLINICA/PEDIATRICA', 9894.52, 1
    UNION ALL SELECT 'medicus', 'Consulta', '1242500200', 'CONSULTA CARDIOLOGIA', 15724.63, 1
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '1243010164', '1/2 HOSPITAL DE DIA REHABILITACION', 24756.83, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '12860616', 'MODULO 1 REHABILITACION COMPLEJA (CON CERTIFICADO DE DISCAPACIDAD)', 24756.83, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '12255074', 'MODULO 1 REHABILITACION COMPLEJA (SIN CERTIFICADO DE DISCAPACIDAD)', 24756.83, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '12420178', 'MODULO 2 - CONSULTORIO DE ATENCION INMEDIATA (DISCAPACIDAD)', 24756.83, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', 'SIN CODIGO', 'MODULO 2 (CONSULTORIO ATENCION INMEDIATA)', 24756.83, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '12860605', 'MODULO 3 DE REHABILITACION: CLINICA DE COMUNICACION AUMENTATIVA-ALTERNATIVA (CON CUD)', 11426.23, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', 'SIN CODIGO', 'MODULO 3 DE REHABILITACION: CLINICA DE COMUNICACION AUMENTATIVA-ALTERNATIVA (SIN CUD)', 11426.23, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '12860606', 'MODULO 5 DE REHABILITACION: CLINICA DE ESPASTICIDAD (CON CUD)', 11426.23, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', 'SIN CODIGO', 'MODULO 5 DE REHABILITACION: CLINICA DE ESPASTICIDAD (SIN CUD)', 11426.23, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '12860607', 'MODULO 6 DE REHABILITACION: (C/CERTIFICADO DE DISCAPACIDAD) ENCEFALOPATIA CRONICA NO EVOLUTIVA', 28565.57, 0
    UNION ALL SELECT 'medicus', 'Módulos de rehabilitación', '12250161', 'MODULO 6-B REHABILITACION COMPLEJA (SIN CERTIFICADO DE DISCAPACIDAD) ENCEFALOPATIA CRONICA', 28565.57, 0
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', 'Cap. 12.19', 'YESOS NN x', 341224.42, 1
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', '1130104', 'ESCISION LOCAL DE LESION DE PIEL O GLANDULA DE PIEL CICATRIZ NN x', 341224.42, 1
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', '1130204', 'CIERRE PLASTICO DE HERIDA POR COLGAJO NN x', 341224.42, 1
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', '02250103', 'TERAPIA OCUPACIONAL. POR SESION Y POR BENEFICIARIO', 3332.65, 1
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', '02250104', 'REHABILITACION DEL LENGUAJE. POR SESION Y POR BENEFICIARIO', 3332.65, 1
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', '12170150', 'PRESUROMETRIA', 29113.24, 1
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', '1218015001', 'ECODOPPLER CARDIACO', 43404.82, 1
    UNION ALL SELECT 'medicus', 'Prácticas Nomencladas', '12175004', 'HOLTER 3 CANALES', 28797.41, 1
    UNION ALL SELECT 'medicus', 'Prácticas No Nomencladas', '11121801', 'INFILTRACIONES MUSCULARES, PERIARTICULARES, TENDINOSAS, DE FASCIAS, DE GANG. PARA REINTEGROS', 4284.84, 1
    UNION ALL SELECT 'medicus', 'Prácticas No Nomencladas', '1225010201', 'HIDROTERAPIA', 12378.41, 1
    UNION ALL SELECT 'medicus', 'Prácticas No Nomencladas', '12255002', 'MODULO DE KINESIOLOGIA EN CONSULTORIO PARA LOS EQUIPOS (02250101-02250102-12257001-12257002)', 4284.84, 1
    UNION ALL SELECT 'medicus', 'Prácticas No Nomencladas', '12255015', 'TECNICAS DE EJERCICIOS POSTURALES', 7141.39, 1
    UNION ALL SELECT 'medicus', 'Prácticas No Nomencladas', '1229506000', 'APLICACION DE TOXINA BOTULINICA', 32374.31, 1
    UNION ALL SELECT 'ospoce', 'Consulta', 'CLINICA MEDICA', 'CLINICA MEDICA', 7561.73, 1
    UNION ALL SELECT 'ospoce', 'Consulta', 'TRAUMATOLOGIA', 'TRAUMATOLOGIA', 7561.73, 1
    UNION ALL SELECT 'ospoce', 'Rehabilitación', 'FKT', 'FKT (FISIO-KINESIOTERAPIA)', 4093.28, 1
    UNION ALL SELECT 'corporacion', 'Consulta', 'CONSULTA CARDIOLOGICA', 'CONSULTA CARDIOLOGICA', 6365.40, 0
    UNION ALL SELECT 'corporacion', 'Consulta', 'CONSULTA TRAUMATOLOGIA', 'CONSULTA TRAUMATOLOGIA', 6365.40, 0
    UNION ALL SELECT 'corporacion', 'Rehabilitación', 'TECNICAS DE EJERCICIOS POSTURALES', 'TECNICAS DE EJERCICIOS POSTURALES', 6365.40, 0
    UNION ALL SELECT 'corporacion', 'Módulos de rehabilitación', 'HOSPITAL DE DIA JORNADA SIMPLE', 'HOSPITAL DE DIA JORNADA SIMPLE', 22278.90, 0
) AS seed_data
WHERE NOT EXISTS (SELECT 1 FROM facturacion_practicas LIMIT 1);
