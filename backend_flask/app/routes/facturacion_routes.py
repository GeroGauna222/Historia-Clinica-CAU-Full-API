import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO, StringIO
from xml.sax.saxutils import escape
import zipfile

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user, login_required

from app.database import get_connection
from app.utils.permisos import requiere_rol


bp_facturacion = Blueprint("facturacion", __name__, url_prefix="/api/facturacion")

FINANCIADORES_VALIDOS = {"medicus", "ospoce", "corporacion"}

MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

MEDICUS_CSV_HEADERS = [
    "AFILIADO",
    "FECHA REALIZACION",
    "CONTEXTO",
    "INTERNACION",
    "ORDEN",
    "CANTIDAD",
    "PRESTACION A HOMOLOGAR",
    "GRUPO",
    "LUGAR REALIZACION EFECTOR",
    "HONORARIOS",
    "GASTOS",
    "TIPO MATRICULA",
    "Nª MATRICULA",
    "TDAP CODIGO DATO ADICIONAL 1 (PROFE INTERIOR)",
    "VALOR DATO ADICIONAL 1 (APELLIDO Y NOMBRES PARA PROFESIONALES DEL INTERIOR)",
    "TDAP CODIGO DATO ADICIONAL 2 (REFER PRESTAD)",
    "VALOR DATO ADICIONAL 2 (CODIGO DE REFERENCIA HISTORIA CLINICA)",
    "TDAP CODIGO DATO ADICIONAL 3",
    "VALOR DATO ADICIONAL 3",
    "TDAP CODIGO DATO ADICIONAL 4 (DES PRESTAC PRE)",
    "VALOR DATO ADICIONAL  4 (DESCRIPCION DE PRESTACION)",
    "TDAP CODIGO DATO ADICIONAL 5 (ID CONECTIVIDAD )",
    "VALOR DATO ADICIONAL 5 (Colocar ID CONECTIVIDAD)",
    "TIPO DOC AFILIADO",
    "NRO DOC AFILIADO",
    "GUARDIA",
    "ALERTA_1",
    "ALERTA_2",
]

OSPOCE_CSV_HEADERS = [
    "FECHA DE PRESTACION",
    "AFILIADO",
    "N° AFILIADO",
    "PRACTICA",
    "AUTORIZACION ",
    "IMPORTE",
]

CORPORACION_CSV_HEADERS = [
    "FECHA DE PRESTACION",
    "PACIENTE",
    "N° AFILIADO",
    "RAZON",
    "SESIONES",
    "CUD",
    "IMPORTE",
]

_SCHEMA_ENSURED = False

INITIAL_PRACTICAS_SEED = [
    ("medicus", "Consulta", "2420101", "CONSULTA MEDICA", "7915.62", 1),
    ("medicus", "Consulta", "2421001", "CONSULTA MEDICA (2421001)", "7915.62", 1),
    ("medicus", "Consulta", "9042500200", "CONSULTA COMPLETA OFTALMOLOGICA", "8905.07", 1),
    ("medicus", "Consulta", "12420106", "CONSULTA NEUROLOGICA INFANTIL", "9894.52", 1),
    ("medicus", "Consulta", "12420109", "CONSULTA CLINICA/PEDIATRICA", "9894.52", 1),
    ("medicus", "Consulta", "1242500200", "CONSULTA CARDIOLOGIA", "15724.63", 1),
    ("medicus", "Módulos de rehabilitación", "1243010164", "1/2 HOSPITAL DE DIA REHABILITACION", "24756.83", 0),
    ("medicus", "Módulos de rehabilitación", "12860616", "MODULO 1 REHABILITACION COMPLEJA (CON CERTIFICADO DE DISCAPACIDAD)", "24756.83", 0),
    ("medicus", "Módulos de rehabilitación", "12255074", "MODULO 1 REHABILITACION COMPLEJA (SIN CERTIFICADO DE DISCAPACIDAD)", "24756.83", 0),
    ("medicus", "Módulos de rehabilitación", "12420178", "MODULO 2 - CONSULTORIO DE ATENCION INMEDIATA (DISCAPACIDAD)", "24756.83", 0),
    ("medicus", "Módulos de rehabilitación", "SIN CODIGO", "MODULO 2 (CONSULTORIO ATENCION INMEDIATA)", "24756.83", 0),
    ("medicus", "Módulos de rehabilitación", "12860605", "MODULO 3 DE REHABILITACION: CLINICA DE COMUNICACION AUMENTATIVA-ALTERNATIVA (CON CUD)", "11426.23", 0),
    ("medicus", "Módulos de rehabilitación", "SIN CODIGO", "MODULO 3 DE REHABILITACION: CLINICA DE COMUNICACION AUMENTATIVA-ALTERNATIVA (SIN CUD)", "11426.23", 0),
    ("medicus", "Módulos de rehabilitación", "12860606", "MODULO 5 DE REHABILITACION: CLINICA DE ESPASTICIDAD (CON CUD)", "11426.23", 0),
    ("medicus", "Módulos de rehabilitación", "SIN CODIGO", "MODULO 5 DE REHABILITACION: CLINICA DE ESPASTICIDAD (SIN CUD)", "11426.23", 0),
    ("medicus", "Módulos de rehabilitación", "12860607", "MODULO 6 DE REHABILITACION: (C/CERTIFICADO DE DISCAPACIDAD) ENCEFALOPATIA CRONICA NO EVOLUTIVA", "28565.57", 0),
    ("medicus", "Módulos de rehabilitación", "12250161", "MODULO 6-B REHABILITACION COMPLEJA (SIN CERTIFICADO DE DISCAPACIDAD) ENCEFALOPATIA CRONICA", "28565.57", 0),
    ("medicus", "Prácticas Nomencladas", "Cap. 12.19", "YESOS NN x", "341224.42", 1),
    ("medicus", "Prácticas Nomencladas", "1130104", "ESCISION LOCAL DE LESION DE PIEL O GLANDULA DE PIEL CICATRIZ NN x", "341224.42", 1),
    ("medicus", "Prácticas Nomencladas", "1130204", "CIERRE PLASTICO DE HERIDA POR COLGAJO NN x", "341224.42", 1),
    ("medicus", "Prácticas Nomencladas", "02250103", "TERAPIA OCUPACIONAL. POR SESION Y POR BENEFICIARIO", "3332.65", 1),
    ("medicus", "Prácticas Nomencladas", "02250104", "REHABILITACION DEL LENGUAJE. POR SESION Y POR BENEFICIARIO", "3332.65", 1),
    ("medicus", "Prácticas Nomencladas", "12170150", "PRESUROMETRIA", "29113.24", 1),
    ("medicus", "Prácticas Nomencladas", "1218015001", "ECODOPPLER CARDIACO", "43404.82", 1),
    ("medicus", "Prácticas Nomencladas", "12175004", "HOLTER 3 CANALES", "28797.41", 1),
    ("medicus", "Prácticas No Nomencladas", "11121801", "INFILTRACIONES MUSCULARES, PERIARTICULARES, TENDINOSAS, DE FASCIAS, DE GANG. PARA REINTEGROS", "4284.84", 1),
    ("medicus", "Prácticas No Nomencladas", "1225010201", "HIDROTERAPIA", "12378.41", 1),
    ("medicus", "Prácticas No Nomencladas", "12255002", "MODULO DE KINESIOLOGIA EN CONSULTORIO PARA LOS EQUIPOS (02250101-02250102-12257001-12257002)", "4284.84", 1),
    ("medicus", "Prácticas No Nomencladas", "12255015", "TECNICAS DE EJERCICIOS POSTURALES", "7141.39", 1),
    ("medicus", "Prácticas No Nomencladas", "1229506000", "APLICACION DE TOXINA BOTULINICA", "32374.31", 1),
    ("ospoce", "Consulta", "CLINICA MEDICA", "CLINICA MEDICA", "7561.73", 1),
    ("ospoce", "Consulta", "TRAUMATOLOGIA", "TRAUMATOLOGIA", "7561.73", 1),
    ("ospoce", "Rehabilitación", "FKT", "FKT (FISIO-KINESIOTERAPIA)", "4093.28", 1),
    ("corporacion", "Consulta", "CONSULTA CARDIOLOGICA", "CONSULTA CARDIOLOGICA", "6365.40", 0),
    ("corporacion", "Consulta", "CONSULTA TRAUMATOLOGIA", "CONSULTA TRAUMATOLOGIA", "6365.40", 0),
    ("corporacion", "Rehabilitación", "TECNICAS DE EJERCICIOS POSTURALES", "TECNICAS DE EJERCICIOS POSTURALES", "6365.40", 0),
    ("corporacion", "Módulos de rehabilitación", "HOSPITAL DE DIA JORNADA SIMPLE", "HOSPITAL DE DIA JORNADA SIMPLE", "22278.90", 0),
]


def _ensure_facturacion_schema(conn):
    """Idempotent table & seed check in case container hot-reloaded without running migrate.py."""
    global _SCHEMA_ENSURED
    if _SCHEMA_ENSURED:
        return

    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute(
            """
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute("SELECT COUNT(*) FROM facturacion_prestadores")
        if (cursor.fetchone() or [0])[0] == 0:
            cursor.execute(
                """
                INSERT INTO facturacion_prestadores
                    (financiador, nombre, contexto, lugar_realizacion_efector, tipo_matricula, nro_matricula, es_predeterminado)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                ("medicus", "CENTRO ASISTENCIAL UNIVERSITARIO (OSUNSAM)", "A", "E171513", "P", "441983", 1),
            )

        cursor.execute("SELECT COUNT(*) FROM facturacion_practicas")
        if (cursor.fetchone() or [0])[0] == 0:
            cursor.executemany(
                """
                INSERT INTO facturacion_practicas
                    (financiador, categoria, codigo, descripcion, importe, requiere_autorizacion)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                INITIAL_PRACTICAS_SEED,
            )

        conn.commit()
        _SCHEMA_ENSURED = True
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error asegurando esquema de facturacion")
        raise
    finally:
        cursor.close()


def _parse_decimal(value, default=None):
    if value is None or str(value).strip() == "":
        return default
    raw = str(value).strip().replace(",", ".")
    try:
        return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    raw = str(value).strip()
    if "T" in raw:
        raw = raw.split("T", 1)[0]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return None


def _normalize_cud(value):
    if not value:
        return "NO"
    s = str(value).strip().upper()
    if s in ("SI", "SÍ", "S", "1", "TRUE"):
        return "SI"
    return "NO"


def _serialize_practica(row):
    return {
        "id": row["id"],
        "financiador": row["financiador"],
        "categoria": row.get("categoria") or "General",
        "codigo": row["codigo"],
        "descripcion": row["descripcion"],
        "importe": float(row["importe"]) if row.get("importe") is not None else 0.0,
        "requiere_autorizacion": bool(row.get("requiere_autorizacion", 1)),
        "activo": bool(row.get("activo", 1)),
    }


def _serialize_prestador(row):
    return {
        "id": row["id"],
        "financiador": row["financiador"],
        "nombre": row["nombre"],
        "contexto": row.get("contexto") or "A",
        "lugar_realizacion_efector": row.get("lugar_realizacion_efector") or "",
        "tipo_matricula": row.get("tipo_matricula") or "P",
        "nro_matricula": row.get("nro_matricula") or "",
        "profe_interior_codigo": row.get("profe_interior_codigo") or "",
        "profe_interior_nombre": row.get("profe_interior_nombre") or "",
        "es_predeterminado": bool(row.get("es_predeterminado", 0)),
        "activo": bool(row.get("activo", 1)),
    }


def _serialize_registro(row):
    fecha = row.get("fecha_realizacion")
    if hasattr(fecha, "strftime"):
        fecha = fecha.strftime("%Y-%m-%d")
    return {
        "id": row["id"],
        "financiador": row["financiador"],
        "fecha_realizacion": fecha,
        "paciente_id": row.get("paciente_id"),
        "paciente_nombre": row.get("paciente_nombre") or "",
        "nro_afiliado": row.get("nro_afiliado") or "",
        "tipo_doc_afiliado": row.get("tipo_doc_afiliado") or "",
        "nro_doc_afiliado": row.get("nro_doc_afiliado") or "",
        "cud": row.get("cud") or "NO",
        "cantidad": int(row.get("cantidad") or 1),
        "practica_id": row.get("practica_id"),
        "practica_codigo": row.get("practica_codigo") or "",
        "practica_descripcion": row.get("practica_descripcion") or "",
        "importe": float(row["importe"]) if row.get("importe") is not None else 0.0,
        "gastos": float(row["gastos"]) if row.get("gastos") is not None else None,
        "autorizacion": row.get("autorizacion") or "",
        "prestador_id": row.get("prestador_id"),
        "contexto": row.get("contexto") or "A",
        "internacion": row.get("internacion") or "",
        "orden": row.get("orden") or "",
        "grupo": row.get("grupo") or "",
        "lugar_realizacion_efector": row.get("lugar_realizacion_efector") or "",
        "tipo_matricula": row.get("tipo_matricula") or "",
        "nro_matricula": row.get("nro_matricula") or "",
        "observaciones": row.get("observaciones") or "",
    }


# ==========================================================
# 📋 CATÁLOGO DE PRÁCTICAS
# ==========================================================

@bp_facturacion.route("/practicas", methods=["GET"])
@login_required
@requiere_rol("director", "administrativo")
def listar_practicas():
    financiador = (request.args.get("financiador") or "").strip().lower()
    incluir_inactivas = request.args.get("incluir_inactivas") in ("1", "true", "si")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        where_clauses = []
        params = []

        if financiador:
            where_clauses.append("financiador = %s")
            params.append(financiador)
        if not incluir_inactivas:
            where_clauses.append("activo = 1")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        cursor.execute(
            f"""
            SELECT * FROM facturacion_practicas
            {where_sql}
            ORDER BY financiador, categoria, descripcion, codigo
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        return jsonify([_serialize_practica(r) for r in rows])
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/practicas", methods=["POST"])
@login_required
@requiere_rol("director", "administrativo")
def crear_practica():
    data = request.get_json(silent=True) or {}
    financiador = (data.get("financiador") or "").strip().lower()
    categoria = (data.get("categoria") or "General").strip() or "General"
    codigo = (data.get("codigo") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()
    importe = _parse_decimal(data.get("importe"), Decimal("0.00"))
    requiere_autorizacion = 1 if data.get("requiere_autorizacion", True) else 0

    if financiador not in FINANCIADORES_VALIDOS:
        return jsonify({"error": "Financiador inválido."}), 400
    if not codigo:
        return jsonify({"error": "El código o nombre de práctica es obligatorio."}), 400
    if not descripcion:
        descripcion = codigo
    if importe is None or importe < 0:
        return jsonify({"error": "El importe debe ser un valor numérico válido."}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute(
            """
            INSERT INTO facturacion_practicas
                (financiador, categoria, codigo, descripcion, importe, requiere_autorizacion, activo)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            """,
            (financiador, categoria, codigo, descripcion, str(importe), requiere_autorizacion),
        )
        new_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM facturacion_practicas WHERE id = %s", (new_id,))
        created = cursor.fetchone()
        return jsonify(_serialize_practica(created)), 201
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error creando practica de facturacion")
        return jsonify({"error": "No se pudo guardar la práctica."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/practicas/<int:practica_id>", methods=["PUT"])
@login_required
@requiere_rol("director", "administrativo")
def actualizar_practica(practica_id):
    data = request.get_json(silent=True) or {}

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute("SELECT * FROM facturacion_practicas WHERE id = %s", (practica_id,))
        actual = cursor.fetchone()
        if not actual:
            return jsonify({"error": "Práctica no encontrada."}), 404

        financiador = (data.get("financiador") or actual["financiador"]).strip().lower()
        categoria = (data.get("categoria") if "categoria" in data else actual.get("categoria") or "General").strip() or "General"
        codigo = (data.get("codigo") if "codigo" in data else actual["codigo"]).strip()
        descripcion = (data.get("descripcion") if "descripcion" in data else actual["descripcion"]).strip()
        importe = _parse_decimal(data.get("importe"), Decimal(str(actual["importe"]))) if "importe" in data else Decimal(str(actual["importe"]))
        requiere_autorizacion = (
            (1 if data.get("requiere_autorizacion") else 0)
            if "requiere_autorizacion" in data
            else actual.get("requiere_autorizacion", 1)
        )
        activo = (1 if data.get("activo") else 0) if "activo" in data else actual.get("activo", 1)

        if not codigo:
            return jsonify({"error": "El código no puede quedar vacío."}), 400
        if not descripcion:
            descripcion = codigo
        if importe is None or importe < 0:
            return jsonify({"error": "Importe inválido."}), 400

        cursor.execute(
            """
            UPDATE facturacion_practicas
            SET financiador = %s,
                categoria = %s,
                codigo = %s,
                descripcion = %s,
                importe = %s,
                requiere_autorizacion = %s,
                activo = %s
            WHERE id = %s
            """,
            (financiador, categoria, codigo, descripcion, str(importe), requiere_autorizacion, activo, practica_id),
        )
        conn.commit()
        cursor.execute("SELECT * FROM facturacion_practicas WHERE id = %s", (practica_id,))
        updated = cursor.fetchone()
        return jsonify(_serialize_practica(updated))
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error actualizando practica de facturacion")
        return jsonify({"error": "No se pudo actualizar la práctica."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/practicas/<int:practica_id>", methods=["DELETE"])
@login_required
@requiere_rol("director", "administrativo")
def eliminar_practica(practica_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute("DELETE FROM facturacion_practicas WHERE id = %s", (practica_id,))
        conn.commit()
        return jsonify({"message": "Práctica eliminada correctamente."})
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error eliminando practica")
        return jsonify({"error": "No se pudo eliminar la práctica."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/practicas/aumento-masivo", methods=["POST"])
@login_required
@requiere_rol("director", "administrativo")
def aumento_masivo_practicas():
    """Aplica un aumento porcentual (ej. 3.8%) a todas las prácticas de un financiador."""
    data = request.get_json(silent=True) or {}
    financiador = (data.get("financiador") or "").strip().lower()
    categoria = (data.get("categoria") or "").strip()
    porcentaje = _parse_decimal(data.get("porcentaje"))

    if financiador not in FINANCIADORES_VALIDOS:
        return jsonify({"error": "Seleccione un financiador válido."}), 400
    if porcentaje is None or porcentaje == 0:
        return jsonify({"error": "Ingrese un porcentaje válido distinto de 0."}), 400

    multiplicador = Decimal("1") + (Decimal(str(data.get("porcentaje")).replace(",", ".")) / Decimal("100"))
    if multiplicador <= 0:
        return jsonify({"error": "El porcentaje resultante no es válido."}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        where_sql = "WHERE financiador = %s AND activo = 1"
        params = [financiador]
        if categoria:
            where_sql += " AND categoria = %s"
            params.append(categoria)

        cursor.execute(f"SELECT id, importe FROM facturacion_practicas {where_sql}", tuple(params))
        rows = cursor.fetchall()

        actualizadas = 0
        for r in rows:
            actual_imp = Decimal(str(r["importe"] or 0))
            nuevo_imp = (actual_imp * multiplicador).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cursor.execute(
                "UPDATE facturacion_practicas SET importe = %s WHERE id = %s",
                (str(nuevo_imp), r["id"]),
            )
            actualizadas += 1

        conn.commit()
        return jsonify({
            "message": f"Se actualizaron {actualizadas} prácticas con un {porcentaje}%.",
            "actualizadas": actualizadas,
        })
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error en aumento masivo de practicas")
        return jsonify({"error": "No se pudo aplicar el aumento masivo."}), 500
    finally:
        cursor.close()
        conn.close()


# ==========================================================
# 🏥 CATÁLOGO DE PRESTADORES / EFECTORES
# ==========================================================

@bp_facturacion.route("/prestadores", methods=["GET"])
@login_required
@requiere_rol("director", "administrativo")
def listar_prestadores():
    financiador = (request.args.get("financiador") or "").strip().lower()
    incluir_inactivos = request.args.get("incluir_inactivos") in ("1", "true", "si")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        where_clauses = []
        params = []
        if financiador:
            where_clauses.append("financiador = %s")
            params.append(financiador)
        if not incluir_inactivos:
            where_clauses.append("activo = 1")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        cursor.execute(
            f"""
            SELECT * FROM facturacion_prestadores
            {where_sql}
            ORDER BY es_predeterminado DESC, nombre ASC
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        return jsonify([_serialize_prestador(r) for r in rows])
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/prestadores", methods=["POST"])
@login_required
@requiere_rol("director", "administrativo")
def crear_prestador():
    data = request.get_json(silent=True) or {}
    financiador = (data.get("financiador") or "medicus").strip().lower()
    nombre = (data.get("nombre") or "").strip()
    contexto = (data.get("contexto") or "A").strip().upper() or "A"
    lugar_efector = (data.get("lugar_realizacion_efector") or "").strip()
    tipo_matricula = (data.get("tipo_matricula") or "P").strip().upper() or "P"
    nro_matricula = (data.get("nro_matricula") or "").strip()
    profe_interior_codigo = (data.get("profe_interior_codigo") or "").strip() or None
    profe_interior_nombre = (data.get("profe_interior_nombre") or "").strip() or None
    es_predeterminado = 1 if data.get("es_predeterminado") else 0

    if not nombre or not lugar_efector or not nro_matricula:
        return jsonify({"error": "Complete nombre, código de lugar efector y número de matrícula."}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        if es_predeterminado:
            cursor.execute(
                "UPDATE facturacion_prestadores SET es_predeterminado = 0 WHERE financiador = %s",
                (financiador,),
            )

        cursor.execute(
            """
            INSERT INTO facturacion_prestadores
                (financiador, nombre, contexto, lugar_realizacion_efector, tipo_matricula, nro_matricula,
                 profe_interior_codigo, profe_interior_nombre, es_predeterminado, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """,
            (
                financiador,
                nombre,
                contexto,
                lugar_efector,
                tipo_matricula,
                nro_matricula,
                profe_interior_codigo,
                profe_interior_nombre,
                es_predeterminado,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM facturacion_prestadores WHERE id = %s", (new_id,))
        return jsonify(_serialize_prestador(cursor.fetchone())), 201
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error creando prestador de facturacion")
        return jsonify({"error": "No se pudo guardar el prestador."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/prestadores/<int:prestador_id>", methods=["PUT"])
@login_required
@requiere_rol("director", "administrativo")
def actualizar_prestador(prestador_id):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute("SELECT * FROM facturacion_prestadores WHERE id = %s", (prestador_id,))
        actual = cursor.fetchone()
        if not actual:
            return jsonify({"error": "Prestador no encontrado."}), 404

        financiador = (data.get("financiador") or actual["financiador"]).strip().lower()
        nombre = (data.get("nombre") if "nombre" in data else actual["nombre"]).strip()
        contexto = (data.get("contexto") if "contexto" in data else actual.get("contexto") or "A").strip().upper()
        lugar_efector = (
            data.get("lugar_realizacion_efector")
            if "lugar_realizacion_efector" in data
            else actual["lugar_realizacion_efector"]
        ).strip()
        tipo_matricula = (
            data.get("tipo_matricula") if "tipo_matricula" in data else actual.get("tipo_matricula") or "P"
        ).strip().upper()
        nro_matricula = (data.get("nro_matricula") if "nro_matricula" in data else actual["nro_matricula"]).strip()
        profe_interior_codigo = (
            (data.get("profe_interior_codigo") or "").strip() or None
            if "profe_interior_codigo" in data
            else actual.get("profe_interior_codigo")
        )
        profe_interior_nombre = (
            (data.get("profe_interior_nombre") or "").strip() or None
            if "profe_interior_nombre" in data
            else actual.get("profe_interior_nombre")
        )
        es_predeterminado = (
            (1 if data.get("es_predeterminado") else 0)
            if "es_predeterminado" in data
            else actual.get("es_predeterminado", 0)
        )
        activo = (1 if data.get("activo") else 0) if "activo" in data else actual.get("activo", 1)

        if not nombre or not lugar_efector or not nro_matricula:
            return jsonify({"error": "Nombre, lugar efector y matrícula son obligatorios."}), 400

        if es_predeterminado:
            cursor.execute(
                "UPDATE facturacion_prestadores SET es_predeterminado = 0 WHERE financiador = %s AND id != %s",
                (financiador, prestador_id),
            )

        cursor.execute(
            """
            UPDATE facturacion_prestadores
            SET financiador = %s,
                nombre = %s,
                contexto = %s,
                lugar_realizacion_efector = %s,
                tipo_matricula = %s,
                nro_matricula = %s,
                profe_interior_codigo = %s,
                profe_interior_nombre = %s,
                es_predeterminado = %s,
                activo = %s
            WHERE id = %s
            """,
            (
                financiador,
                nombre,
                contexto,
                lugar_efector,
                tipo_matricula,
                nro_matricula,
                profe_interior_codigo,
                profe_interior_nombre,
                es_predeterminado,
                activo,
                prestador_id,
            ),
        )
        conn.commit()
        cursor.execute("SELECT * FROM facturacion_prestadores WHERE id = %s", (prestador_id,))
        return jsonify(_serialize_prestador(cursor.fetchone()))
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error actualizando prestador de facturacion")
        return jsonify({"error": "No se pudo actualizar el prestador."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/prestadores/<int:prestador_id>", methods=["DELETE"])
@login_required
@requiere_rol("director", "administrativo")
def eliminar_prestador(prestador_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute("DELETE FROM facturacion_prestadores WHERE id = %s", (prestador_id,))
        conn.commit()
        return jsonify({"message": "Prestador eliminado correctamente."})
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error eliminando prestador")
        return jsonify({"error": "No se pudo eliminar el prestador."}), 500
    finally:
        cursor.close()
        conn.close()


# ==========================================================
# 🧾 REGISTROS DE FACTURACIÓN (CARGA Y FILTRADO)
# ==========================================================

def _build_registros_filter(args):
    financiador = (args.get("financiador") or "").strip().lower()
    mes = (args.get("mes") or "").strip()
    fecha_desde = _parse_date(args.get("fecha_desde"))
    fecha_hasta = _parse_date(args.get("fecha_hasta"))
    paciente_id = args.get("paciente_id")
    practica_id = args.get("practica_id")
    busqueda = (args.get("busqueda") or "").strip()

    where_clauses = []
    params = []

    if financiador:
        where_clauses.append("financiador = %s")
        params.append(financiador)

    if fecha_desde and fecha_hasta:
        where_clauses.append("fecha_realizacion BETWEEN %s AND %s")
        params.extend([fecha_desde, fecha_hasta])
    elif fecha_desde:
        where_clauses.append("fecha_realizacion >= %s")
        params.append(fecha_desde)
    elif fecha_hasta:
        where_clauses.append("fecha_realizacion <= %s")
        params.append(fecha_hasta)
    elif mes and len(mes) == 7 and "-" in mes:
        where_clauses.append("DATE_FORMAT(fecha_realizacion, '%Y-%m') = %s")
        params.append(mes)

    if paciente_id and str(paciente_id).isdigit():
        where_clauses.append("paciente_id = %s")
        params.append(int(paciente_id))

    if practica_id and str(practica_id).isdigit():
        where_clauses.append("practica_id = %s")
        params.append(int(practica_id))

    if busqueda:
        like_val = f"%{busqueda}%"
        where_clauses.append(
            "(paciente_nombre LIKE %s OR nro_afiliado LIKE %s OR autorizacion LIKE %s OR practica_codigo LIKE %s OR practica_descripcion LIKE %s)"
        )
        params.extend([like_val, like_val, like_val, like_val, like_val])

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return where_sql, params


@bp_facturacion.route("/registros", methods=["GET"])
@login_required
@requiere_rol("director", "administrativo")
def listar_registros():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        where_sql, params = _build_registros_filter(request.args)
        cursor.execute(
            f"""
            SELECT * FROM facturacion_registros
            {where_sql}
            ORDER BY fecha_realizacion ASC, id ASC
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        registros = [_serialize_registro(r) for r in rows]

        total_importe = sum((Decimal(str(r["importe"] or 0)) for r in rows), Decimal("0.00"))
        total_sesiones = sum((int(r.get("cantidad") or 1) for r in rows), 0)

        return jsonify({
            "registros": registros,
            "resumen": {
                "total_registros": len(registros),
                "total_sesiones": total_sesiones,
                "total_importe": float(total_importe.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            },
        })
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/registros", methods=["POST"])
@login_required
@requiere_rol("director", "administrativo")
def crear_registros():
    """Crea una o múltiples entradas de facturación en un solo envío."""
    data = request.get_json(silent=True) or {}
    financiador = (data.get("financiador") or "").strip().lower()
    if financiador not in FINANCIADORES_VALIDOS:
        return jsonify({"error": "Seleccione un financiador válido (Medicus, OSPOCE o Corporación)."}), 400

    paciente_id = data.get("paciente_id")
    if paciente_id is not None and str(paciente_id).strip() != "":
        try:
            paciente_id = int(paciente_id)
        except (TypeError, ValueError):
            paciente_id = None
    else:
        paciente_id = None

    paciente_nombre = (data.get("paciente_nombre") or "").strip().upper()
    nro_afiliado = (data.get("nro_afiliado") or "").strip()
    tipo_doc_afiliado = (data.get("tipo_doc_afiliado") or "").strip() or None
    nro_doc_afiliado = (data.get("nro_doc_afiliado") or "").strip() or None
    cud = _normalize_cud(data.get("cud"))

    practica_id = data.get("practica_id")
    if practica_id is not None and str(practica_id).strip() != "":
        try:
            practica_id = int(practica_id)
        except (TypeError, ValueError):
            practica_id = None
    else:
        practica_id = None

    practica_codigo = (data.get("practica_codigo") or "").strip()
    practica_descripcion = (data.get("practica_descripcion") or practica_codigo).strip()
    importe_base = _parse_decimal(data.get("importe"))
    gastos = _parse_decimal(data.get("gastos"))

    prestador_id = data.get("prestador_id")
    if prestador_id is not None and str(prestador_id).strip() != "":
        try:
            prestador_id = int(prestador_id)
        except (TypeError, ValueError):
            prestador_id = None
    else:
        prestador_id = None

    contexto = (data.get("contexto") or "A").strip().upper() or "A"
    internacion = (data.get("internacion") or "").strip() or None
    orden = (data.get("orden") or "").strip() or None
    grupo = (data.get("grupo") or "").strip() or None
    lugar_efector = (data.get("lugar_realizacion_efector") or "").strip() or None
    tipo_matricula = (data.get("tipo_matricula") or "").strip().upper() or None
    nro_matricula = (data.get("nro_matricula") or "").strip() or None
    observaciones = (data.get("observaciones") or "").strip() or None

    if not nro_afiliado:
        return jsonify({"error": "El N° de Afiliado / Cobertura es obligatorio."}), 400
    if financiador in ("ospoce", "corporacion") and not paciente_nombre:
        return jsonify({"error": "El nombre del paciente es obligatorio."}), 400
    if not practica_codigo:
        return jsonify({"error": "Seleccione una práctica del catálogo."}), 400
    if importe_base is None or importe_base < 0:
        return jsonify({"error": "El importe es inválido."}), 400

    # Soportar envío único o lista de sesiones (items)
    items_raw = data.get("items")
    if not isinstance(items_raw, list) or not items_raw:
        items_raw = [
            {
                "fecha_realizacion": data.get("fecha_realizacion"),
                "autorizacion": data.get("autorizacion"),
                "cantidad": data.get("cantidad", 1),
                "importe": data.get("importe"),
            }
        ]

    filas_a_insertar = []
    usuario_id = getattr(current_user, "id", None)

    for idx, item in enumerate(items_raw, start=1):
        fecha_norm = _parse_date(item.get("fecha_realizacion"))
        if not fecha_norm:
            return jsonify({"error": f"La fecha de la sesión #{idx} es inválida o está vacía."}), 400
        try:
            cantidad = int(item.get("cantidad") or data.get("cantidad") or 1)
            if cantidad < 1:
                cantidad = 1
        except (TypeError, ValueError):
            cantidad = 1

        imp_item = _parse_decimal(item.get("importe"), importe_base)
        if imp_item is None or imp_item < 0:
            imp_item = importe_base

        autorizacion = (item.get("autorizacion") if "autorizacion" in item else data.get("autorizacion")) or ""
        autorizacion = str(autorizacion).strip() or None

        filas_a_insertar.append(
            (
                financiador,
                fecha_norm,
                paciente_id,
                paciente_nombre or nro_afiliado,
                nro_afiliado,
                tipo_doc_afiliado,
                nro_doc_afiliado,
                cud,
                cantidad,
                practica_id,
                practica_codigo,
                practica_descripcion,
                str(imp_item),
                str(gastos) if gastos is not None else None,
                autorizacion,
                prestador_id,
                contexto,
                internacion,
                orden,
                grupo,
                lugar_efector,
                tipo_matricula,
                nro_matricula,
                observaciones,
                usuario_id,
            )
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.executemany(
            """
            INSERT INTO facturacion_registros (
                financiador, fecha_realizacion, paciente_id, paciente_nombre, nro_afiliado,
                tipo_doc_afiliado, nro_doc_afiliado, cud, cantidad, practica_id,
                practica_codigo, practica_descripcion, importe, gastos, autorizacion,
                prestador_id, contexto, internacion, orden, grupo,
                lugar_realizacion_efector, tipo_matricula, nro_matricula, observaciones, creado_por
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            """,
            filas_a_insertar,
        )
        conn.commit()
        return jsonify({
            "message": f"Se registraron {len(filas_a_insertar)} prestación(es) correctamente.",
            "insertados": len(filas_a_insertar),
        }), 201
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error insertando registros de facturacion")
        return jsonify({"error": "No se pudieron guardar los registros de facturación."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/registros/<int:registro_id>", methods=["PUT"])
@login_required
@requiere_rol("director", "administrativo")
def actualizar_registro(registro_id):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute("SELECT * FROM facturacion_registros WHERE id = %s", (registro_id,))
        actual = cursor.fetchone()
        if not actual:
            return jsonify({"error": "Registro no encontrado."}), 404

        fecha_norm = _parse_date(data.get("fecha_realizacion")) if "fecha_realizacion" in data else _parse_date(actual["fecha_realizacion"])
        if not fecha_norm:
            return jsonify({"error": "Fecha de realización inválida."}), 400

        paciente_id = data.get("paciente_id", actual.get("paciente_id"))
        if paciente_id is not None and str(paciente_id).strip() != "":
            try:
                paciente_id = int(paciente_id)
            except (TypeError, ValueError):
                paciente_id = None
        else:
            paciente_id = None

        paciente_nombre = (
            (data.get("paciente_nombre") or "").strip().upper()
            if "paciente_nombre" in data
            else actual.get("paciente_nombre") or ""
        )
        nro_afiliado = (
            (data.get("nro_afiliado") or "").strip()
            if "nro_afiliado" in data
            else actual.get("nro_afiliado") or ""
        )
        if not nro_afiliado:
            return jsonify({"error": "El N° de Afiliado no puede quedar vacío."}), 400

        cud = _normalize_cud(data.get("cud")) if "cud" in data else (actual.get("cud") or "NO")
        try:
            cantidad = int(data.get("cantidad", actual.get("cantidad") or 1))
            if cantidad < 1:
                cantidad = 1
        except (TypeError, ValueError):
            cantidad = 1

        practica_id = data.get("practica_id", actual.get("practica_id"))
        if practica_id is not None and str(practica_id).strip() != "":
            try:
                practica_id = int(practica_id)
            except (TypeError, ValueError):
                practica_id = None
        else:
            practica_id = None

        practica_codigo = (
            (data.get("practica_codigo") or "").strip()
            if "practica_codigo" in data
            else actual.get("practica_codigo") or ""
        )
        practica_descripcion = (
            (data.get("practica_descripcion") or practica_codigo).strip()
            if "practica_descripcion" in data
            else actual.get("practica_descripcion") or practica_codigo
        )
        importe = (
            _parse_decimal(data.get("importe"))
            if "importe" in data
            else Decimal(str(actual.get("importe") or 0))
        )
        if importe is None or importe < 0:
            return jsonify({"error": "Importe inválido."}), 400

        autorizacion = (
            (str(data.get("autorizacion") or "").strip() or None)
            if "autorizacion" in data
            else actual.get("autorizacion")
        )
        prestador_id = data.get("prestador_id", actual.get("prestador_id"))
        contexto = (data.get("contexto") if "contexto" in data else actual.get("contexto") or "A") or "A"
        lugar_efector = (
            (data.get("lugar_realizacion_efector") or "").strip() or None
            if "lugar_realizacion_efector" in data
            else actual.get("lugar_realizacion_efector")
        )
        tipo_matricula = (
            (data.get("tipo_matricula") or "").strip().upper() or None
            if "tipo_matricula" in data
            else actual.get("tipo_matricula")
        )
        nro_matricula = (
            (data.get("nro_matricula") or "").strip() or None
            if "nro_matricula" in data
            else actual.get("nro_matricula")
        )
        observaciones = (
            (data.get("observaciones") or "").strip() or None
            if "observaciones" in data
            else actual.get("observaciones")
        )

        cursor.execute(
            """
            UPDATE facturacion_registros
            SET fecha_realizacion = %s,
                paciente_id = %s,
                paciente_nombre = %s,
                nro_afiliado = %s,
                cud = %s,
                cantidad = %s,
                practica_id = %s,
                practica_codigo = %s,
                practica_descripcion = %s,
                importe = %s,
                autorizacion = %s,
                prestador_id = %s,
                contexto = %s,
                lugar_realizacion_efector = %s,
                tipo_matricula = %s,
                nro_matricula = %s,
                observaciones = %s
            WHERE id = %s
            """,
            (
                fecha_norm,
                paciente_id,
                paciente_nombre or nro_afiliado,
                nro_afiliado,
                cud,
                cantidad,
                practica_id,
                practica_codigo,
                practica_descripcion,
                str(importe),
                autorizacion,
                prestador_id,
                contexto,
                lugar_efector,
                tipo_matricula,
                nro_matricula,
                observaciones,
                registro_id,
            ),
        )
        conn.commit()
        cursor.execute("SELECT * FROM facturacion_registros WHERE id = %s", (registro_id,))
        return jsonify(_serialize_registro(cursor.fetchone()))
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error actualizando registro de facturacion")
        return jsonify({"error": "No se pudo actualizar el registro."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/registros/<int:registro_id>", methods=["DELETE"])
@login_required
@requiere_rol("director", "administrativo")
def eliminar_registro(registro_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute("DELETE FROM facturacion_registros WHERE id = %s", (registro_id,))
        conn.commit()
        return jsonify({"message": "Registro eliminado correctamente."})
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error eliminando registro de facturacion")
        return jsonify({"error": "No se pudo eliminar el registro."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/registros/eliminar-lote", methods=["POST"])
@login_required
@requiere_rol("director", "administrativo")
def eliminar_registros_lote():
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "Seleccione al menos un registro para eliminar."}), 400

    placeholders = ", ".join(["%s"] * len(ids))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        cursor.execute(f"DELETE FROM facturacion_registros WHERE id IN ({placeholders})", tuple(ids))
        eliminados = cursor.rowcount
        conn.commit()
        return jsonify({"message": f"Se eliminaron {eliminados} registro(s).", "eliminados": eliminados})
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error eliminando lote de registros")
        return jsonify({"error": "No se pudieron eliminar los registros seleccionados."}), 500
    finally:
        cursor.close()
        conn.close()


@bp_facturacion.route("/registros/recalcular-precios", methods=["POST"])
@login_required
@requiere_rol("director", "administrativo")
def recalcular_precios_periodo():
    """Actualiza el importe de los registros del período filtrado tomando los valores vigentes del catálogo."""
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        where_sql, params = _build_registros_filter(data)
        if not where_sql:
            return jsonify({"error": "Indique un financiador y período para recalcular precios."}), 400

        cursor.execute(f"SELECT id, financiador, practica_id, practica_codigo FROM facturacion_registros {where_sql}", tuple(params))
        registros = cursor.fetchall()
        if not registros:
            return jsonify({"message": "No hay registros en el período seleccionado.", "actualizados": 0})

        cursor.execute("SELECT id, financiador, codigo, importe FROM facturacion_practicas")
        practicas = cursor.fetchall()
        por_id = {p["id"]: p["importe"] for p in practicas}
        por_codigo = {(p["financiador"], p["codigo"]): p["importe"] for p in practicas}

        actualizados = 0
        for reg in registros:
            nuevo_importe = None
            if reg.get("practica_id") and reg["practica_id"] in por_id:
                nuevo_importe = por_id[reg["practica_id"]]
            elif (reg["financiador"], reg["practica_codigo"]) in por_codigo:
                nuevo_importe = por_codigo[(reg["financiador"], reg["practica_codigo"])]

            if nuevo_importe is not None:
                cursor.execute(
                    "UPDATE facturacion_registros SET importe = %s WHERE id = %s",
                    (str(nuevo_importe), reg["id"]),
                )
                actualizados += 1

        conn.commit()
        return jsonify({
            "message": f"Se actualizaron los importes de {actualizados} registro(s) según el catálogo vigente.",
            "actualizados": actualizados,
        })
    except Exception:
        conn.rollback()
        current_app.logger.exception("Error recalculando precios del periodo")
        return jsonify({"error": "No se pudieron recalcular los importes."}), 500
    finally:
        cursor.close()
        conn.close()


# ==========================================================
# 📤 EXPORTACIÓN CSV Y EXCEL (.XLSX) POR PERÍODO
# ==========================================================

def _format_periodo_label(args):
    mes = (args.get("mes") or "").strip()
    fecha_desde = _parse_date(args.get("fecha_desde"))
    fecha_hasta = _parse_date(args.get("fecha_hasta"))

    if fecha_desde and fecha_hasta:
        # Si coinciden con el mismo mes y año, mostramos el nombre del mes
        if fecha_desde[:7] == fecha_hasta[:7] and fecha_desde.endswith("-01"):
            yyyy, mm = fecha_desde[:7].split("-")
            nombre_mes = MESES_ES.get(int(mm), mm)
            return f"{nombre_mes} {yyyy}"
        d1 = datetime.strptime(fecha_desde, "%Y-%m-%d").strftime("%d/%m/%Y")
        d2 = datetime.strptime(fecha_hasta, "%Y-%m-%d").strftime("%d/%m/%Y")
        return f"{d1} al {d2}"

    if mes and len(mes) == 7 and "-" in mes:
        yyyy, mm = mes.split("-")
        nombre_mes = MESES_ES.get(int(mm), mm)
        return f"{nombre_mes} {yyyy}"

    hoy = datetime.now()
    return f"{MESES_ES.get(hoy.month, '')} {hoy.year}"


def _format_decimal_export(val):
    if val is None or val == "":
        return ""
    d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Quitar ceros finales innecesarios si termina en .00 o .X0 solo cuando corresponde,
    # o mantener formato limpio tipo 24756.83 / 6365.4
    s = f"{d:.2f}"
    if s.endswith(".00"):
        return s[:-3]
    if s.endswith("0"):
        return s[:-1]
    return s


def _build_export_matrix(financiador, registros, periodo_label):
    """
    Construye la matriz de filas (cada celda es (valor, tipo_celda))
    donde tipo_celda in ('str', 'num', 'header', 'title', 'total').
    """
    rows = []

    if financiador == "medicus":
        rows.append([(h, "header") for h in MEDICUS_CSV_HEADERS])
        for r in registros:
            fecha_str = r["fecha_realizacion"]
            if hasattr(fecha_str, "strftime"):
                fecha_str = fecha_str.strftime("%Y-%m-%d")

            imp_num = float(Decimal(str(r.get("importe") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            gastos_val = (
                float(Decimal(str(r["gastos"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                if r.get("gastos") is not None
                else ""
            )

            fila = [
                (r.get("nro_afiliado") or "", "str"),
                (fecha_str or "", "str"),
                (r.get("contexto") or "A", "str"),
                (r.get("internacion") or "", "str"),
                (r.get("orden") or "", "str"),
                (int(r.get("cantidad") or 1), "num"),
                (r.get("practica_codigo") or "", "str"),
                (r.get("grupo") or "", "str"),
                (r.get("lugar_realizacion_efector") or "E171513", "str"),
                (imp_num, "num"),
                (gastos_val, "num" if gastos_val != "" else "str"),
                (r.get("tipo_matricula") or "P", "str"),
                (r.get("nro_matricula") or "441983", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
                (r.get("autorizacion") or "", "str"),
                (r.get("tipo_doc_afiliado") or "", "str"),
                (r.get("nro_doc_afiliado") or "", "str"),
                ("", "str"),
                ("", "str"),
                ("", "str"),
            ]
            rows.append(fila)

    elif financiador == "ospoce":
        rows.append([(f"FACTURACION {periodo_label.upper()}.", "title")] + [("", "str")] * 5)
        rows.append([("", "str")] * 6)
        rows.append([(h, "header") for h in OSPOCE_CSV_HEADERS])

        total = Decimal("0.00")
        for r in registros:
            fecha_str = r["fecha_realizacion"]
            if hasattr(fecha_str, "strftime"):
                fecha_str = fecha_str.strftime("%Y-%m-%d")
            imp_dec = Decimal(str(r.get("importe") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += imp_dec
            rows.append([
                (fecha_str or "", "str"),
                (r.get("paciente_nombre") or "", "str"),
                (r.get("nro_afiliado") or "", "str"),
                (r.get("practica_codigo") or "", "str"),
                (r.get("autorizacion") or "", "str"),
                (float(imp_dec), "num"),
            ])

        rows.append([
            ("", "str"),
            ("", "str"),
            ("", "str"),
            ("", "str"),
            ("TOTAL", "total"),
            (float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "total_num"),
        ])

    elif financiador == "corporacion":
        rows.append([(f"Facturación {periodo_label} ", "title")] + [("", "str")] * 6)
        rows.append([("", "str")] * 7)
        rows.append([(h, "header") for h in CORPORACION_CSV_HEADERS])

        total = Decimal("0.00")
        for r in registros:
            fecha_str = r["fecha_realizacion"]
            if hasattr(fecha_str, "strftime"):
                fecha_str = fecha_str.strftime("%Y-%m-%d")
            imp_dec = Decimal(str(r.get("importe") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += imp_dec
            rows.append([
                (fecha_str or "", "str"),
                (r.get("paciente_nombre") or "", "str"),
                (r.get("nro_afiliado") or "", "str"),
                (r.get("practica_codigo") or "", "str"),
                (int(r.get("cantidad") or 1), "num"),
                (r.get("cud") or "NO", "str"),
                (float(imp_dec), "num"),
            ])

        rows.append([
            ("", "str"),
            ("", "str"),
            ("", "str"),
            ("", "str"),
            ("", "str"),
            ("TOTAL", "total"),
            (float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "total_num"),
        ])

    return rows


def _col_letter(col_idx_1_based):
    result = ""
    n = col_idx_1_based
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _generate_xlsx_bytes(matrix, sheet_name="Facturacion"):
    """Genera un archivo .xlsx OpenXML nativo sin requerir paquetes externos."""
    sheet_rows_xml = []
    max_cols = max((len(r) for r in matrix), default=1)
    col_widths = [14] * max_cols

    for r_idx, row in enumerate(matrix, start=1):
        cells_xml = []
        for c_idx, (val, c_type) in enumerate(row, start=1):
            col_ref = f"{_col_letter(c_idx)}{r_idx}"
            text_len = len(str(val or ""))
            if text_len + 3 > col_widths[c_idx - 1]:
                col_widths[c_idx - 1] = min(48, text_len + 3)

            style_idx = 0
            if c_type == "header":
                style_idx = 1
            elif c_type in ("title", "total"):
                style_idx = 2
            elif c_type == "num":
                style_idx = 3
            elif c_type == "total_num":
                style_idx = 4

            if c_type in ("num", "total_num") and val != "" and val is not None:
                # Si es entero exacto (ej. cantidad=1), escribir entero sin decimales
                if isinstance(val, int):
                    cells_xml.append(f'<c r="{col_ref}"><v>{val}</v></c>')
                else:
                    cells_xml.append(f'<c r="{col_ref}" s="{style_idx}"><v>{val}</v></c>')
            else:
                escaped = escape(str(val if val is not None else ""))
                cells_xml.append(
                    f'<c r="{col_ref}" s="{style_idx}" t="inlineStr"><is><t xml:space="preserve">{escaped}</t></is></c>'
                )

        sheet_rows_xml.append(f'<row r="{r_idx}">{"".join(cells_xml)}</row>')

    cols_xml = "".join(
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(col_widths, start=1)
    )

    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<cols>{cols_xml}</cols>"
        f'<sheetData>{"".join(sheet_rows_xml)}</sheetData>'
        "</worksheet>"
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="1">'
        '<numFmt numFmtId="164" formatCode="#,##0.00"/>'
        "</numFmts>"
        '<fonts count="3">'
        '<font><sz val="10"/><name val="Calibri"/></font>'
        '<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        "</fonts>"
        '<fills count="3">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF0F766E"/></patternFill></fill>'
        "</fills>"
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="5">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
        '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="164" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyNumberFormat="1"/>'
        "</cellXfs>"
        "</styleSheet>"
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(sheet_name[:31])}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )

    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )

    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/styles.xml", styles_xml)
        zf.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    buf.seek(0)
    return buf


@bp_facturacion.route("/exportar", methods=["GET"])
@login_required
@requiere_rol("director", "administrativo")
def exportar_facturacion():
    financiador = (request.args.get("financiador") or "medicus").strip().lower()
    if financiador not in FINANCIADORES_VALIDOS:
        return jsonify({"error": "Financiador inválido."}), 400

    formato = (request.args.get("formato") or "csv").strip().lower()
    if formato not in ("csv", "xlsx"):
        formato = "csv"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_facturacion_schema(conn)
        where_sql, params = _build_registros_filter(request.args)
        cursor.execute(
            f"""
            SELECT * FROM facturacion_registros
            {where_sql}
            ORDER BY fecha_realizacion ASC, id ASC
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        registros = [_serialize_registro(r) for r in rows]
        periodo_label = _format_periodo_label(request.args)
        matrix = _build_export_matrix(financiador, registros, periodo_label)

        safe_period = (
            request.args.get("mes")
            or f"{request.args.get('fecha_desde', '')}_{request.args.get('fecha_hasta', '')}".strip("_")
            or datetime.now().strftime("%Y-%m")
        )
        filename_base = f"facturacion_{financiador}_{safe_period}"

        if formato == "xlsx":
            xlsx_stream = _generate_xlsx_bytes(matrix, sheet_name=f"{financiador.capitalize()} {safe_period}")
            return send_file(
                xlsx_stream,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=f"{filename_base}.xlsx",
            )

        # CSV export (con BOM UTF-8 para que Excel en Windows abra tildes y N° / Nª perfectamente)
        sio = StringIO()
        writer = csv.writer(sio, lineterminator="\r\n")
        for row in matrix:
            csv_row = []
            for val, c_type in row:
                if c_type in ("num", "total_num") and val != "" and not isinstance(val, int):
                    csv_row.append(_format_decimal_export(val))
                else:
                    csv_row.append(val if val is not None else "")
            writer.writerow(csv_row)

        csv_bytes = BytesIO(("\ufeff" + sio.getvalue()).encode("utf-8"))
        csv_bytes.seek(0)
        return send_file(
            csv_bytes,
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=f"{filename_base}.csv",
        )
    finally:
        cursor.close()
        conn.close()
