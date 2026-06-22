-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS hc_bfa
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE hc_bfa;

SET GLOBAL time_zone = '-3:00';
SET time_zone = '-3:00';

-- ==============================================
--  ELIMINAR TABLAS (solo para entorno de desarrollo)
-- ==============================================
DROP TABLE IF EXISTS auditorias_blockchain;
DROP TABLE IF EXISTS recetas_electronicas;
DROP TABLE IF EXISTS evolucion_archivos;
DROP TABLE IF EXISTS turnos;
DROP TABLE IF EXISTS ausencias;
DROP TABLE IF EXISTS disponibilidades;
DROP TABLE IF EXISTS turnos_grupales;
DROP TABLE IF EXISTS grupo_posteos;
DROP TABLE IF EXISTS grupo_miembros;
DROP TABLE IF EXISTS historias;
DROP TABLE IF EXISTS evoluciones;
DROP TABLE IF EXISTS comunicados;
DROP TABLE IF EXISTS pacientes;
DROP TABLE IF EXISTS grupos_profesionales;
DROP TABLE IF EXISTS usuarios;

-- ==============================================
-- TABLA DE USUARIOS
-- ==============================================
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol ENUM('director', 'profesional', 'administrativo','area') NOT NULL,
    especialidad VARCHAR(100) NULL,
    dni VARCHAR(20) DEFAULT NULL,
    sexo ENUM('F', 'M', 'X') DEFAULT NULL,
    telefono VARCHAR(50) DEFAULT NULL,
    matricula_tipo ENUM('MN', 'MP', 'OP') DEFAULT NULL,
    matricula_numero VARCHAR(50) DEFAULT NULL,
    matricula_provincia VARCHAR(100) DEFAULT NULL,
    lugar_atencion_nombre VARCHAR(150) DEFAULT NULL,
    lugar_atencion_direccion VARCHAR(255) DEFAULT NULL,
    lugar_atencion_contacto VARCHAR(150) DEFAULT NULL,
    lugar_atencion_email VARCHAR(100) DEFAULT NULL,
    duracion_turno INT NOT NULL DEFAULT 20,
    foto VARCHAR(255) DEFAULT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1 
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE PACIENTES
-- ==============================================
CREATE TABLE pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nro_hc VARCHAR(20) NOT NULL UNIQUE,
    dni VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE,
    sexo ENUM('Masculino', 'Femenino', 'Otro') DEFAULT NULL,
    nacionalidad VARCHAR(50),
    ocupacion VARCHAR(100),
    direccion VARCHAR(255),
    codigo_postal VARCHAR(20),
    telefono VARCHAR(50),
    celular VARCHAR(50),
    email VARCHAR(100),
    contacto VARCHAR(100),
    cobertura VARCHAR(100),
    cert_discapacidad ENUM('Sí', 'No') DEFAULT NULL,
    nro_certificado VARCHAR(50),
    derivado_por VARCHAR(100),
    diagnostico TEXT,
    motivo_derivacion TEXT,
    medico_cabecera VARCHAR(100),
    comentarios TEXT,
    motivo_ingreso TEXT,
    enfermedad_actual TEXT,
    antecedentes_enfermedad_actual TEXT,
    antecedentes_personales TEXT,
    antecedentes_heredofamiliares TEXT,
    registrado_por INT DEFAULT NULL,
    modificado_por INT DEFAULT NULL,
    FOREIGN KEY (registrado_por) REFERENCES usuarios(id),
    FOREIGN KEY (modificado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE HISTORIAS CLÍNICAS (actualizada para blockchain)
-- ==============================================
CREATE TABLE historias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL UNIQUE,
    usuario_id INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resumen LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    hash_local CHAR(64) DEFAULT NULL,        -- Hash SHA-256 del contenido
    tx_hash VARCHAR(512) DEFAULT NULL,       -- Recibo TSA (temporary_rd) de BFA
    fecha_anclaje_bfa DATETIME DEFAULT NULL,
    estado_bfa VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE EVOLUCIONES
-- ==============================================
CREATE TABLE evoluciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    fecha DATE NOT NULL,
    contenido TEXT NOT NULL,
    indicaciones TEXT,
    usuario_id INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash_local CHAR(64) DEFAULT NULL,
    tx_hash VARCHAR(512) DEFAULT NULL,
    fecha_anclaje_bfa DATETIME DEFAULT NULL,
    estado_bfa VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- ARCHIVOS ASOCIADOS A EVOLUCIONES
-- ==============================================
CREATE TABLE evolucion_archivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evolucion_id INT NOT NULL,
    filename VARCHAR(255),
    filepath TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- RECETAS ELECTRONICAS QBITOS
-- ==============================================
CREATE TABLE recetas_electronicas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    tipo ENUM('receta', 'estudio') NOT NULL DEFAULT 'receta',
    qbitos_endpoint VARCHAR(120) DEFAULT NULL,
    qbitos_id_receta VARCHAR(100) DEFAULT NULL,
    qbitos_s3_link TEXT DEFAULT NULL,
    qbitos_verificador TEXT DEFAULT NULL,
    id_transaccion VARCHAR(100) DEFAULT NULL,
    estado VARCHAR(50) DEFAULT NULL,
    financiador_nombre VARCHAR(150) DEFAULT NULL,
    afiliado_numero VARCHAR(40) DEFAULT NULL,
    request_json JSON NOT NULL,
    response_json JSON DEFAULT NULL,
    error_json JSON DEFAULT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash_local CHAR(64) DEFAULT NULL,
    tx_hash VARCHAR(512) DEFAULT NULL,
    fecha_anclaje_bfa DATETIME DEFAULT NULL,
    estado_bfa VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_recetas_paciente (paciente_id),
    INDEX idx_recetas_usuario (usuario_id),
    INDEX idx_recetas_tipo (tipo),
    INDEX idx_recetas_qbitos_id (qbitos_id_receta)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE TURNOS
-- ==============================================
CREATE TABLE turnos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo VARCHAR(255),
    notificado BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- AUSENCIAS PROFESIONALES
-- ==============================================
CREATE TABLE ausencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo VARCHAR(255),
    creado_por INT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- DISPONIBILIDADES DE PROFESIONALES
-- ==============================================
CREATE TABLE disponibilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    dia_semana ENUM('Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo') NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- GRUPOS PROFESIONALES
-- ==============================================
CREATE TABLE grupos_profesionales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    color VARCHAR(20) DEFAULT '#00936B',
    es_rehabilitacion TINYINT(1) NOT NULL DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE turnos_grupales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    grupo_id INT NOT NULL,
    paciente_id INT NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo VARCHAR(255),
    creado_por INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (grupo_id) REFERENCES grupos_profesionales(id) ON DELETE CASCADE,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (creado_por) REFERENCES usuarios(id),
    INDEX idx_turnos_grupales_grupo (grupo_id),
    INDEX idx_turnos_grupales_rango (fecha_inicio, fecha_fin)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE grupo_miembros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    grupo_id INT NOT NULL,
    usuario_id INT NOT NULL,
    UNIQUE KEY idx_grupo_usuario (grupo_id, usuario_id),
    FOREIGN KEY (grupo_id) REFERENCES grupos_profesionales(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE comunicados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(180) NOT NULL,
    contenido TEXT NOT NULL,
    autor_id INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (autor_id) REFERENCES usuarios(id),
    INDEX idx_comunicados_creado_en (creado_en)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE grupo_posteos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    grupo_id INT NOT NULL,
    autor_id INT NOT NULL,
    titulo VARCHAR(180) DEFAULT NULL,
    contenido TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (grupo_id) REFERENCES grupos_profesionales(id) ON DELETE CASCADE,
    FOREIGN KEY (autor_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_grupo_posteos_grupo (grupo_id),
    INDEX idx_grupo_posteos_creado (creado_en)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- AUDITORÍAS BLOCKCHAIN
-- ==============================================
CREATE TABLE auditorias_blockchain (
    id INT AUTO_INCREMENT PRIMARY KEY,
    historia_id INT NULL,
    evolucion_id INT NULL,
    entidad_tipo VARCHAR(20) NOT NULL DEFAULT 'historia',
    entidad_id INT NULL,
    tx_hash VARCHAR(512) DEFAULT NULL,
    hash_local VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    hash_bfa   VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    valido TINYINT(1) NOT NULL,
    usuario VARCHAR(100) NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (historia_id) REFERENCES historias(id) ON DELETE CASCADE,
    FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- ÍNDICES
-- ==============================================
CREATE INDEX idx_pacientes_dni ON pacientes (dni);
CREATE INDEX idx_pacientes_nombre ON pacientes (nombre);
CREATE INDEX idx_pacientes_apellido ON pacientes (apellido);

-- ==============================================
-- USUARIO ADMINISTRADOR INICIAL
-- ==============================================
INSERT INTO usuarios (nombre, username, email, password_hash, rol)
SELECT 'Admin', 'admin', 'admin@ejemplo.com',
'scrypt:32768:8:1$bdt4huruWlbjvNqs$4a236ac9509c5ee61ab5ce7103a686d272d512c2cf5f11d30b5afcb91f98832cba6ba1118114c6c4df2e4e9387f452514b05c6f9b6fc7d35a3a2e042f07fc0af',
'director'
WHERE NOT EXISTS (
    SELECT 1 FROM usuarios WHERE username = 'admin'
);

-- ==============================================
-- USUARIOS DB
-- ==============================================
-- En Docker Compose se crean con variables:
-- MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE.
-- No dejar credenciales hardcodeadas en SQL.
