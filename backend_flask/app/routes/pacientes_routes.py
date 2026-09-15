from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol
from mysql.connector import IntegrityError
from werkzeug.utils import secure_filename
from io import BytesIO
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from datetime import datetime, timezone, timedelta
from app.routes.historias_routes import actualizar_hash_evolucion, actualizar_historia
from app.utils.firma_electronica import (
    FirmaElectronicaError,
    hash_payload,
    payload_evolucion_firmable,
    registrar_firma_y_auditoria,
    require_confirmation,
    auth_event_id,
    ahora_argentina_sin_tz,
    validar_profesional_firmante,
)
import hashlib
import os
import uuid
from reportlab.lib.colors import Color
from reportlab.lib import colors
from xml.sax.saxutils import escape

# Registrar fuente compatible con UTF-8 (caracteres acentuados, español)
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))

bp_pacientes = Blueprint("pacientes", __name__)

TZ_ARG = timezone(timedelta(hours=-3))


def _to_iso_arg(dt):
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_ARG)
    else:
        dt = dt.astimezone(TZ_ARG)
    return dt.isoformat()


def _safe_current_user_id():
    try:
        return current_user.id if current_user.is_authenticated else None
    except Exception:
        return None


def _request_id():
    return request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")


def _mysql_connection_id(conn):
    return getattr(conn, "connection_id", None)


def _format_pdf_datetime(value):
    if not value:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M:%S")
    return str(value)


def _format_pdf_date(value):
    if not value:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    raw = str(value)[:10]
    try:
        year, month, day = raw.split("-")
        return f"{day}/{month}/{year}"
    except ValueError:
        return raw


def _pdf_multiline(value):
    return escape(str(value)).replace("\n", "<br/>")


def _pdf_value_present(value):
    return value is not None and str(value).strip() != ""


HISTORIA_ARCHIVO_MAX_BYTES = 10 * 1024 * 1024
HISTORIA_ARCHIVO_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
HISTORIA_ARCHIVO_EXTENSION_MIMES = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
}


def _historia_archivos_root(paciente_id):
    return os.path.join(_uploads_root(), "pacientes", str(paciente_id))


def _uploads_root():
    configured = current_app.config.get("UPLOAD_FOLDER")
    # Existing tests intentionally isolate uploads in their temporary cwd;
    # production uses the configured Docker volume (/app/uploads).
    if current_app.testing and (not configured or configured == "/app/uploads"):
        return os.path.join(os.getcwd(), "uploads")
    return configured or os.path.join(os.getcwd(), "uploads")


def _evolucion_archivos_root(evolucion_id):
    return os.path.join(_uploads_root(), "evoluciones", str(evolucion_id))


def _historia_archivo_path(paciente_id, relative_path):
    root = os.path.abspath(_historia_archivos_root(paciente_id))
    candidate = os.path.abspath(os.path.join(root, relative_path))
    if os.path.commonpath([root, candidate]) != root:
        raise ValueError("Ruta de archivo inválida")
    return candidate


def _historia_archivo_payload(row):
    return {
        "id": row.get("id"),
        "nombre": row.get("nombre_original"),
        "mime_type": row.get("mime_type"),
        "tamanio_bytes": row.get("tamanio_bytes"),
        "hash_sha256": row.get("hash_sha256"),
        "cargado_en": _to_iso_arg(row.get("cargado_en")),
        "cargado_por": row.get("cargado_por"),
        "url": f"/api/pacientes/{row.get('paciente_id')}/adjuntos/{row.get('id')}",
    }


def _historia_archivo_contenido_valido(extension, contenido):
    """Reject renamed executables while accepting only the advertised formats."""
    signatures = {
        '.pdf': contenido.startswith(b'%PDF-'),
        '.jpg': contenido.startswith(b'\xff\xd8\xff'),
        '.jpeg': contenido.startswith(b'\xff\xd8\xff'),
        '.png': contenido.startswith(b'\x89PNG\r\n\x1a\n'),
    }
    return signatures.get(extension, False)


def _log_db_error(message, conn=None):
    # Operative context only: never log payloads, patient names, DNI, diagnosis, or clinical content.
    current_app.logger.exception(
        "%s endpoint=%s method=%s user_id=%s mysql_connection_id=%s request_id=%s",
        message,
        request.endpoint,
        request.method,
        _safe_current_user_id(),
        _mysql_connection_id(conn),
        _request_id(),
    )


_PACIENTE_BUSCAR_CONDITIONS = {
    'dni': 'dni LIKE %s',
    'nombre': 'nombre LIKE %s',
    'apellido': 'apellido LIKE %s',
    'nro_hc': 'nro_hc LIKE %s',
}
_PACIENTE_BUSCAR_DEFAULT_CONDITION = (
    'dni LIKE %s OR nombre LIKE %s OR apellido LIKE %s OR nro_hc LIKE %s'
)
_SQL_COUNT_PACIENTES = 'SELECT COUNT(*) as total FROM pacientes WHERE '
_SQL_SELECT_PACIENTES_BUSCAR = (
    'SELECT id, nro_hc, dni, nombre, apellido FROM pacientes WHERE '
)
_SQL_PACIENTES_BUSCAR_TAIL = ' ORDER BY apellido, nombre LIMIT %s OFFSET %s'


def _paciente_buscar_condition_and_params(term, dni, nombre, apellido, nro_hc):
    """Return a whitelisted WHERE fragment and bound parameters for patient search."""
    if dni:
        return _PACIENTE_BUSCAR_CONDITIONS['dni'], (f'%{dni}%',)
    if nombre:
        return _PACIENTE_BUSCAR_CONDITIONS['nombre'], (f'%{nombre}%',)
    if apellido:
        return _PACIENTE_BUSCAR_CONDITIONS['apellido'], (f'%{apellido}%',)
    if nro_hc:
        return _PACIENTE_BUSCAR_CONDITIONS['nro_hc'], (f'%{nro_hc}%',)
    like_term = f'%{term}%'
    return _PACIENTE_BUSCAR_DEFAULT_CONDITION, (like_term, like_term, like_term, like_term)

# ==========================================================
# 📁 CRUD de Pacientes
# ==========================================================

@bp_pacientes.route('/api/pacientes', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_crear_paciente():
    """Crea un nuevo paciente."""
    # 🧩 Soporta tanto JSON como form-data
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        dni = data.get('dni')
        nro_hc = data.get('nro_hc')

        # Verificar duplicado por DNI
        cursor.execute("SELECT id FROM pacientes WHERE dni = %s", (dni,))
        if cursor.fetchone():
            return jsonify({'error': f"⚠️ Ya existe un paciente con DNI {dni}"}), 400

        # Verificar duplicado por N° de Historia Clinica (nro_hc es UNIQUE en la DB).
        cursor.execute("SELECT id FROM pacientes WHERE nro_hc = %s", (nro_hc,))
        if cursor.fetchone():
            return jsonify({'error': f"⚠️ Ya existe un paciente con N° HC {nro_hc}"}), 409

        # Normalizar campo discapacidad.
        cert_discapacidad_raw = data.get('cert_discapacidad') or ''
        if str(cert_discapacidad_raw).lower() in ('si', 'sí'):
            cert_discapacidad = 'Sí'
        elif str(cert_discapacidad_raw).lower() == 'no':
            cert_discapacidad = 'No'
        else:
            cert_discapacidad = None

        usuario_id = current_user.id if current_user.is_authenticated else None

        cursor.execute("""
            INSERT INTO pacientes (
                nro_hc, dni, apellido, nombre, fecha_nacimiento, sexo, nacionalidad,
                ocupacion, direccion, codigo_postal, telefono, celular, email, contacto,
                cobertura, cert_discapacidad, nro_certificado, derivado_por, diagnostico,
                motivo_derivacion, medico_cabecera, comentarios, motivo_ingreso, enfermedad_actual, antecedentes_enfermedad_actual,
                antecedentes_personales, antecedentes_heredofamiliares, registrado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s
            )
        """, (
            data.get('nro_hc'),
            data.get('dni'),
            data.get('apellido', '').upper() if data.get('apellido') else None,
            data.get('nombre', '').upper() if data.get('nombre') else None,
            data.get('fecha_nacimiento'),
            data.get('sexo'),
            data.get('nacionalidad'),
            data.get('ocupacion'),
            data.get('direccion'),
            data.get('codigo_postal'),
            data.get('telefono'),
            data.get('celular'),
            data.get('email'),
            data.get('contacto'),
            data.get('cobertura'),
            cert_discapacidad,
            data.get('nro_certificado'),
            data.get('derivado_por'),
            data.get('diagnostico'),
            data.get('motivo_derivacion'),
            data.get('medico_cabecera'),
            data.get('comentarios'),
            data.get('motivo_ingreso'),
            data.get('enfermedad_actual'),
            data.get('antecedentes_enfermedad_actual'),
            data.get('antecedentes_personales'),
            data.get('antecedentes_heredofamiliares'),
            usuario_id
        ))
        conn.commit()
    except IntegrityError:
        conn.rollback()
        _log_db_error("Patient creation integrity error", conn)
        return jsonify({'error': '⚠️ Ya existe un paciente con ese DNI o N° HC'}), 409
    except Exception:
        conn.rollback()
        _log_db_error("Patient creation database error", conn)
        raise
    finally:
        cursor.close(); conn.close()

    return jsonify({'message': 'Paciente registrado correctamente ✅'})

@bp_pacientes.route('/api/pacientes/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_modificar_paciente(id):
    """Modifica los datos de un paciente existente."""
    data = (request.get_json(silent=True) or {}) if request.is_json else request.form.to_dict()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Pre-check duplicidad DNI contra otros pacientes
        new_dni = data.get('dni')
        if new_dni and str(new_dni).strip():
            cursor.execute("SELECT id FROM pacientes WHERE dni = %s AND id != %s", (new_dni, id))
            if cursor.fetchone():
                return jsonify({'error': f"⚠️ Ya existe otro paciente registrado con el DNI {new_dni}"}), 409

        # Pre-check duplicidad N° HC contra otros pacientes
        new_nro_hc = data.get('nro_hc')
        if new_nro_hc and str(new_nro_hc).strip():
            cursor.execute("SELECT id FROM pacientes WHERE nro_hc = %s AND id != %s", (new_nro_hc, id))
            if cursor.fetchone():
                return jsonify({'error': f"⚠️ Ya existe otro paciente registrado con el N° HC {new_nro_hc}"}), 409

        # Validaciones de campos obligatorios en edicion si son enviados vacios
        if 'dni' in data and (data.get('dni') is None or not str(data.get('dni')).strip()):
            return jsonify({'error': '⚠️ El N° de Documento (DNI) no puede quedar vacío.'}), 400
        if 'nro_hc' in data and (data.get('nro_hc') is None or not str(data.get('nro_hc')).strip()):
            return jsonify({'error': '⚠️ El N° de Historia Clínica no puede quedar vacío.'}), 400
        if 'nombre' in data and (data.get('nombre') is None or not str(data.get('nombre')).strip()):
            return jsonify({'error': '⚠️ El Nombre no puede quedar vacío.'}), 400
        if 'apellido' in data and (data.get('apellido') is None or not str(data.get('apellido')).strip()):
            return jsonify({'error': '⚠️ El Apellido no puede quedar vacío.'}), 400

        cert_discapacidad_raw = data.get('cert_discapacidad') or ''
        if str(cert_discapacidad_raw).lower() in ('si', 'sí'):
            cert_discapacidad = 'Sí'
        elif str(cert_discapacidad_raw).lower() == 'no':
            cert_discapacidad = 'No'
        else:
            cert_discapacidad = None

        usuario_id = current_user.id if current_user.is_authenticated else None

        campos_validos = {
            'nro_hc': data.get('nro_hc'),
            'dni': data.get('dni'),
            'apellido': data.get('apellido', '').upper() if data.get('apellido') else None,
            'nombre': data.get('nombre', '').upper() if data.get('nombre') else None,
            'fecha_nacimiento': data.get('fecha_nacimiento'),
            'sexo': data.get('sexo'),
            'nacionalidad': data.get('nacionalidad'),
            'ocupacion': data.get('ocupacion'),
            'direccion': data.get('direccion'),
            'codigo_postal': data.get('codigo_postal'),
            'telefono': data.get('telefono'),
            'celular': data.get('celular'),
            'email': data.get('email'),
            'contacto': data.get('contacto'),
            'cobertura': data.get('cobertura'),
            'cert_discapacidad': cert_discapacidad,
            'nro_certificado': data.get('nro_certificado'),
            'derivado_por': data.get('derivado_por'),
            'diagnostico': data.get('diagnostico'),
            'motivo_derivacion': data.get('motivo_derivacion'),
            'medico_cabecera': data.get('medico_cabecera'),
            'comentarios': data.get('comentarios'),
            'motivo_ingreso': data.get('motivo_ingreso'),
            'enfermedad_actual': data.get('enfermedad_actual'),
            'antecedentes_enfermedad_actual': data.get('antecedentes_enfermedad_actual'),
            'antecedentes_personales': data.get('antecedentes_personales'),
            'antecedentes_heredofamiliares': data.get('antecedentes_heredofamiliares'),
        }

        # Solo actualizar campos enviados
        campos_no_vacios = {k: v for k, v in campos_validos.items() if v is not None}
        if not campos_no_vacios:
            return jsonify({'message': 'No se realizaron cambios.', 'sin_cambios': True}), 200

        set_clause = ", ".join([f"{campo}=%s" for campo in campos_no_vacios.keys()])
        values = list(campos_no_vacios.values()) + [usuario_id, id]

        query = f"UPDATE pacientes SET {set_clause}, modificado_por=%s WHERE id=%s"
        cursor.execute(query, values)
        conn.commit()
        return jsonify({'message': 'Paciente modificado correctamente ✅'})
    except IntegrityError:
        conn.rollback()
        _log_db_error("Patient update integrity error", conn)
        return jsonify({'error': '⚠️ Ya existe un paciente con ese DNI o N° HC'}), 409
    except Exception:
        conn.rollback()
        _log_db_error("Patient update database error", conn)
        raise
    finally:
        cursor.close(); conn.close()


@bp_pacientes.route('/api/pacientes', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_listar_pacientes():
    """Devuelve el listado completo de pacientes."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, nro_hc, dni, nombre, apellido, fecha_nacimiento, sexo, telefono, email
            FROM pacientes
            ORDER BY apellido, nombre
        """)
        pacientes = cursor.fetchall()
        return jsonify(pacientes)
    except Exception:
        conn.rollback()
        _log_db_error("Patient list database error", conn)
        return jsonify({"error": "Error al listar pacientes"}), 500
    finally:
        cursor.close(); conn.close()


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_get_paciente(id):
    """Obtiene los datos de un paciente por ID."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
        paciente = cursor.fetchone()

        if not paciente:
            return jsonify({'error': 'Paciente no encontrado'}), 404

        if paciente.get('fecha_nacimiento'):
            try:
                paciente['fecha_nacimiento'] = paciente['fecha_nacimiento'].strftime('%Y-%m-%d')
            except Exception:
                pass

        return jsonify(paciente)
    except Exception:
        conn.rollback()
        _log_db_error("Patient read database error", conn)
        raise
    finally:
        cursor.close(); conn.close()


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_eliminar_paciente(id):
    """Elimina un paciente."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM pacientes WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Paciente no encontrado'}), 404

        try:
            cursor.execute("DELETE FROM pacientes WHERE id = %s", (id,))
            conn.commit()
        except IntegrityError:
            # El paciente tiene evoluciones/turnos/recetas asociadas (esas tablas
            # no tienen ON DELETE CASCADE hacia pacientes) -> el DELETE choca con
            # la FK. Sin este rollback, la transaccion queda abierta y la conexion
            # se "cuelga" en MySQL en vez de liberarse (visto en produccion via
            # SHOW FULL PROCESSLIST + SHOW ENGINE INNODB STATUS).
            conn.rollback()
            _log_db_error("Patient delete integrity error", conn)
            return jsonify({'error': '⚠️ No se puede eliminar: el paciente tiene historia clinica, turnos o recetas asociadas'}), 400

        return jsonify({'message': 'Paciente eliminado correctamente ✅'})
    except Exception:
        conn.rollback()
        _log_db_error("Patient delete database error", conn)
        raise
    finally:
        cursor.close()
        conn.close()


@bp_pacientes.route('/api/pacientes/proximo-nro-hc', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def proximo_nro_hc():
    """Sugiere el proximo numero de historia clinica disponible (max numerico + 1)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT MAX(CAST(nro_hc AS UNSIGNED)) AS max_hc
            FROM pacientes
            WHERE nro_hc REGEXP '^[0-9]+$'
        """)
        fila = cursor.fetchone()
        max_hc = fila.get('max_hc') if fila else None
        return jsonify({'proximo_nro_hc': str((max_hc or 0) + 1)})
    except Exception:
        conn.rollback()
        _log_db_error("Next patient history number database error", conn)
        raise
    finally:
        cursor.close(); conn.close()


@bp_pacientes.route('/api/pacientes/buscar', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def buscar_pacientes():
    """Busca pacientes por nombre, apellido, DNI o N° de historia clínica."""
    term = request.args.get('q', '')
    dni = request.args.get('dni', '')
    nombre = request.args.get('nombre', '')
    apellido = request.args.get('apellido', '')
    nro_hc = request.args.get('nro_hc', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        condition, params = _paciente_buscar_condition_and_params(
            term, dni, nombre, apellido, nro_hc
        )

        # Contar total
        cursor.execute(_SQL_COUNT_PACIENTES + condition, params)
        total = cursor.fetchone()['total']

        offset = (page - 1) * per_page
        query_params = params + (per_page, offset)
        cursor.execute(
            _SQL_SELECT_PACIENTES_BUSCAR + condition + _SQL_PACIENTES_BUSCAR_TAIL,
            query_params,
        )
        results = cursor.fetchall()

        return jsonify({
            'pacientes': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total // per_page) + (1 if total % per_page else 0)
        })
    except Exception:
        conn.rollback()
        _log_db_error("Patient search database error", conn)
        raise
    finally:
        cursor.close(); conn.close()



# ==========================================================
# 🩺 Evoluciones
# ==========================================================


def _validar_intencion_de_firma(exigir_confirmacion=True):
    """Validate the signing contract before opening a clinical transaction."""
    try:
        validar_profesional_firmante()
        if exigir_confirmacion:
            require_confirmation()
        auth_event_id()
    except FirmaElectronicaError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    return None

@bp_pacientes.route('/api/pacientes/<int:id>/evolucion', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional')
def agregar_evolucion(id):
    """Create and electronically sign a new clinical evolution atomically."""
    validation_error = _validar_intencion_de_firma()
    if validation_error:
        return validation_error

    fecha = request.form.get('fecha')
    contenido = request.form.get('contenido')
    indicaciones = request.form.get('indicaciones')  
    archivos = request.files.getlist('archivos')

    if not fecha or not contenido or not contenido.strip():
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    upload_dir = None

    try:
        cursor.execute("""
            INSERT INTO evoluciones (
                paciente_id, fecha, contenido, indicaciones, usuario_id,
                estado_firma, firmado_en
            ) VALUES (%s, %s, %s, %s, %s, 'pendiente', NULL)
        """, (id, fecha, contenido, indicaciones, current_user.id))
        evolucion_id = cursor.lastrowid

        upload_dir = _evolucion_archivos_root(evolucion_id)
        os.makedirs(upload_dir, exist_ok=True)

        for archivo in archivos:
            if archivo.filename:
                filename = secure_filename(archivo.filename)
                if not filename:
                    continue
                archivo.save(os.path.join(upload_dir, filename))
                cursor.execute("""
                    INSERT INTO evolucion_archivos (evolucion_id, filename)
                    VALUES (%s, %s)
                """, (evolucion_id, filename))

        evolucion = {
            'id': evolucion_id,
            'paciente_id': id,
            'fecha': fecha,
            'contenido': contenido,
            'indicaciones': indicaciones,
            'usuario_id': current_user.id,
            'version': 1,
            'padre_id': None,
            'motivo_rectificacion': None,
        }
        hash_evolucion, firmado_en = registrar_firma_y_auditoria(
            cursor, evolucion, 'firma'
        )
        cursor.execute(
            """
            UPDATE evoluciones
            SET hash_local = %s, estado_firma = 'firmada', firmado_en = %s
            WHERE id = %s
            """,
            (hash_evolucion, firmado_en, evolucion_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        if upload_dir and os.path.isdir(upload_dir):
            import shutil
            shutil.rmtree(upload_dir, ignore_errors=True)
        _log_db_error("Patient evolution creation database error", conn)
        raise
    finally:
        cursor.close()
        conn.close()

    # 🔁 Actualizar historia consolidada automáticamente
    try:
        hash_local = actualizar_historia(id, current_user.id)
        partes = []
        if hash_evolucion:
            partes.append(f"evolucion hash {hash_evolucion[:10]}...")
        if hash_local:
            partes.append(f"historia hash {hash_local[:10]}...")
        msg_extra = f" ({', '.join(partes)})" if partes else ""
    except Exception as e:
        print(f"⚠️ Error actualizando historia consolidada: {e}")
        msg_extra = " (⚠️ No se pudo actualizar historia)"

    return jsonify({
        'message': f'Evolución guardada y firmada correctamente ✅{msg_extra}',
        'id': evolucion_id,
        'hash_local': hash_evolucion,
        'estado_firma': 'firmada',
    })

@bp_pacientes.route('/api/pacientes/<int:id>/evoluciones', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def get_evoluciones(id):
    """Obtiene las evoluciones de un paciente, mostrando tambi?n el m?dico y su especialidad."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                e.id,
                e.fecha,
                e.contenido,
                e.indicaciones,
                e.creado_en,
                e.version,
                e.usuario_id,
                e.hash_local,
                e.tx_hash,
                e.fecha_anclaje_bfa,
                e.estado_bfa,
                e.estado_firma,
                e.firmado_en,
                e.motivo_rectificacion,
                f.payload_version AS firma_payload_version,
                f.payload_hash AS firma_payload_hash,
                f.algoritmo AS firma_algoritmo,
                f.firmado_en AS firma_firmado_en,
                f.rol AS firma_rol,
                f.matricula_tipo AS firma_matricula_tipo,
                f.matricula_numero AS firma_matricula_numero,
                f.matricula_provincia AS firma_matricula_provincia,
                u.nombre AS nombre_usuario,
                CASE
                    WHEN u.rol = 'director' THEN 'Director'
                    ELSE COALESCE(u.especialidad, 'Sin especificar')
                END AS especialidad_usuario
            FROM evoluciones e
            JOIN usuarios u ON e.usuario_id = u.id
            LEFT JOIN firmas_electronicas f ON f.evolucion_id = e.id
            WHERE e.paciente_id = %s AND e.activo = 1
            ORDER BY e.fecha DESC
        """, (id,))

        evoluciones = cursor.fetchall()

        # Adjuntar archivos de cada evoluci?n
        for evo in evoluciones:
            cursor.execute("""
                SELECT filename
                FROM evolucion_archivos
                WHERE evolucion_id = %s
            """, (evo['id'],))
            archivos = cursor.fetchall()
            evo['archivos'] = [{
                'nombre': a['filename'],
                'url': f"/api/uploads/evoluciones/{evo['id']}/{a['filename']}"
            } for a in archivos]
            evo['creado_en'] = _to_iso_arg(evo.get('creado_en'))
            evo['firmado_en'] = _to_iso_arg(evo.get('firmado_en'))
            evo['firma_firmado_en'] = _to_iso_arg(evo.get('firma_firmado_en'))

        return jsonify(evoluciones)
    except Exception:
        conn.rollback()
        _log_db_error("Patient evolutions read database error", conn)
        raise
    finally:
        cursor.close()
        conn.close()


@bp_pacientes.route('/api/uploads/evoluciones/<int:evo_id>/<filename>')
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def uploaded_file(evo_id, filename):
    """Sirve los archivos adjuntos de evoluciones."""
    folder = _evolucion_archivos_root(evo_id)
    return send_from_directory(folder, filename)


@bp_pacientes.route('/api/pacientes/<int:paciente_id>/adjuntos', methods=['GET', 'POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_adjuntos_historia(paciente_id):
    """List or append documents attached directly to a patient's history.

    These files are not evolutions. They are append-only source documents
    (external studies, prior records or consents) with uploader, timestamp and
    SHA-256 evidence. There is intentionally no overwrite/delete operation.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    created_paths = []

    try:
        cursor.execute("SELECT id FROM pacientes WHERE id = %s", (paciente_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Paciente no encontrado'}), 404

        if request.method == 'GET':
            cursor.execute(
                """
                SELECT h.id, h.paciente_id, h.nombre_original, h.mime_type,
                       h.tamanio_bytes, h.hash_sha256, h.cargado_en,
                       u.nombre AS cargado_por
                FROM historia_archivos h
                JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.paciente_id = %s
                ORDER BY h.cargado_en DESC, h.id DESC
                """,
                (paciente_id,),
            )
            return jsonify([_historia_archivo_payload(row) for row in cursor.fetchall()])

        archivos = [archivo for archivo in request.files.getlist('archivos') if archivo and archivo.filename]
        if not archivos:
            return jsonify({'error': 'Debe seleccionar al menos un archivo'}), 400

        root = _historia_archivos_root(paciente_id)
        prepared = []
        respuesta = []

        for archivo in archivos:
            nombre_original = archivo.filename.strip()
            nombre_seguro = secure_filename(nombre_original)
            extension = os.path.splitext(nombre_seguro)[1].lower()
            mime_type = (archivo.mimetype or '').lower()

            if not nombre_seguro or extension not in {'.pdf', '.jpg', '.jpeg', '.png'}:
                return jsonify({'error': f'Formato no permitido para {nombre_original}'}), 415
            if mime_type not in HISTORIA_ARCHIVO_MIMES and mime_type != 'application/octet-stream':
                return jsonify({'error': f'Tipo MIME no permitido para {nombre_original}'}), 415

            contenido = archivo.read()
            if not contenido:
                return jsonify({'error': f'El archivo {nombre_original} está vacío'}), 422
            if len(contenido) > HISTORIA_ARCHIVO_MAX_BYTES:
                return jsonify({'error': f'{nombre_original} supera el límite de 10 MB'}), 413
            if not _historia_archivo_contenido_valido(extension, contenido):
                return jsonify({'error': f'El contenido de {nombre_original} no coincide con su formato'}), 415

            mime_type = HISTORIA_ARCHIVO_EXTENSION_MIMES[extension] if mime_type == 'application/octet-stream' else mime_type
            prepared.append((nombre_original, nombre_seguro, mime_type, contenido))

        os.makedirs(root, exist_ok=True)
        for nombre_original, nombre_seguro, mime_type, contenido in prepared:

            # El nombre público nunca se usa como ruta: se antepone un UUID y
            # se guarda sólo dentro del directorio aislado del paciente.
            nombre_almacenado = f"{uuid.uuid4().hex}_{nombre_seguro}"
            ruta_relativa = nombre_almacenado
            path = _historia_archivo_path(paciente_id, ruta_relativa)
            with open(path, 'wb') as destino:
                destino.write(contenido)
            created_paths.append(path)

            cargado_en = ahora_argentina_sin_tz()
            hash_sha256 = hashlib.sha256(contenido).hexdigest()
            cursor.execute(
                """
                INSERT INTO historia_archivos
                    (paciente_id, usuario_id, nombre_original, nombre_almacenado,
                     ruta_relativa, mime_type, tamanio_bytes, hash_sha256, cargado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    paciente_id,
                    current_user.id,
                    nombre_original[:255],
                    nombre_almacenado[:255],
                    ruta_relativa,
                    mime_type,
                    len(contenido),
                    hash_sha256,
                    cargado_en,
                ),
            )
            respuesta.append({
                'id': cursor.lastrowid,
                'paciente_id': paciente_id,
                'nombre': nombre_original,
                'mime_type': mime_type,
                'tamanio_bytes': len(contenido),
                'hash_sha256': hash_sha256,
                'cargado_en': _to_iso_arg(cargado_en),
                'cargado_por': current_user.nombre,
                'url': f"/api/pacientes/{paciente_id}/adjuntos/{cursor.lastrowid}",
            })

        conn.commit()
        return jsonify({'archivos': respuesta}), 201
    except Exception:
        conn.rollback()
        for path in created_paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                current_app.logger.exception("Could not clean failed history attachment")
        _log_db_error("Patient history attachment database error", conn)
        raise
    finally:
        cursor.close()
        conn.close()


@bp_pacientes.route('/api/pacientes/<int:paciente_id>/adjuntos/<int:archivo_id>', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def descargar_adjunto_historia(paciente_id, archivo_id):
    """Serve a history document only after authenticated patient-scoped lookup."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, paciente_id, nombre_original, ruta_relativa, mime_type
            FROM historia_archivos
            WHERE id = %s AND paciente_id = %s
            LIMIT 1
            """,
            (archivo_id, paciente_id),
        )
        archivo = cursor.fetchone()
        if not archivo:
            return jsonify({'error': 'Archivo no encontrado'}), 404

        try:
            path = _historia_archivo_path(paciente_id, archivo['ruta_relativa'])
        except ValueError:
            current_app.logger.error("Invalid history attachment path id=%s", archivo_id)
            return jsonify({'error': 'Archivo no disponible'}), 404
        if not os.path.isfile(path):
            return jsonify({'error': 'Archivo no disponible'}), 404

        return send_file(
            path,
            mimetype=archivo['mime_type'],
            as_attachment=True,
            download_name=archivo['nombre_original'],
            conditional=True,
        )
    finally:
        cursor.close()
        conn.close()


@bp_pacientes.route('/api/pacientes/<int:paciente_id>/evolucion/<int:evo_id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional')
def api_editar_evolucion(paciente_id, evo_id):
    """
    Registra una edición de evolución agregando un nuevo registro Append-Only.
    Solo el creador original o el rol director pueden realizar la edición.
    """
    validation_error = _validar_intencion_de_firma(exigir_confirmacion=False)
    if validation_error:
        return validation_error

    fecha = request.form.get('fecha')
    contenido = request.form.get('contenido')
    indicaciones = request.form.get('indicaciones')
    motivo_rectificacion = (request.form.get('motivo_rectificacion') or '').strip()
    archivos = request.files.getlist('archivos')

    if not fecha or not contenido or not contenido.strip():
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    upload_dir = None

    try:
        # 1. Obtener la evolucion a editar
        cursor.execute("SELECT * FROM evoluciones WHERE id = %s AND paciente_id = %s", (evo_id, paciente_id))
        evolucion_actual = cursor.fetchone()
        
        if not evolucion_actual:
            return jsonify({'error': 'Evolución no encontrada'}), 404

        # 2. Control de accesos (Solo el creador original o director)
        is_owner = (evolucion_actual['usuario_id'] == current_user.id)
        is_director = (current_user.rol == 'director')
        if not is_owner and not is_director:
            return jsonify({'error': 'No tenés permisos para editar esta evolución'}), 403
        if not motivo_rectificacion:
            return jsonify({'error': 'Debe indicar el motivo de la rectificación'}), 422

        try:
            require_confirmation()
        except FirmaElectronicaError as exc:
            return jsonify({'error': exc.message}), exc.status_code

        # 3. Determinar padre_id (si la actual ya tiene padre, heredamos el mismo padre)
        padre_id = evolucion_actual['padre_id'] if evolucion_actual['padre_id'] is not None else evolucion_actual['id']

        # 4. Obtener la version mas alta actual para el arbol
        cursor.execute("SELECT MAX(version) AS max_v FROM evoluciones WHERE id = %s OR padre_id = %s", (padre_id, padre_id))
        res_v = cursor.fetchone()
        max_version = res_v['max_v'] if res_v and res_v['max_v'] is not None else 1
        nueva_version = max_version + 1

        # 5. Insertar la nueva evolucion de edicion
        cursor.execute("""
            INSERT INTO evoluciones (
                paciente_id, fecha, contenido, indicaciones, usuario_id,
                padre_id, version, activo, motivo_rectificacion,
                estado_firma, firmado_en
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, 'pendiente', NULL)
        """, (
            paciente_id, fecha, contenido, indicaciones, current_user.id,
            padre_id, nueva_version, motivo_rectificacion,
        ))
        
        nueva_evo_id = cursor.lastrowid

        # 6. Desactivar las versiones anteriores del mismo arbol
        cursor.execute("""
            UPDATE evoluciones 
            SET activo = 0 
            WHERE (id = %s OR padre_id = %s) AND id <> %s
        """, (padre_id, padre_id, nueva_evo_id))

        # 7. Manejo de archivos adjuntos (se copian los del padre y se agregan los nuevos)
        cursor.execute("SELECT filename FROM evolucion_archivos WHERE evolucion_id = %s", (evo_id,))
        adjuntos_viejos = cursor.fetchall()
        
        upload_dir = _evolucion_archivos_root(nueva_evo_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        for adj in adjuntos_viejos:
            filename = adj['filename']
            cursor.execute("""
                INSERT INTO evolucion_archivos (evolucion_id, filename)
                VALUES (%s, %s)
            """, (nueva_evo_id, filename))
            
            ruta_origen = os.path.join(_evolucion_archivos_root(evo_id), filename)
            ruta_destino = os.path.join(upload_dir, filename)
            if os.path.exists(ruta_origen):
                import shutil
                shutil.copy2(ruta_origen, ruta_destino)

        for archivo in archivos:
            if archivo.filename:
                filename = secure_filename(archivo.filename)
                if not filename:
                    continue
                archivo.save(os.path.join(upload_dir, filename))
                cursor.execute("""
                    INSERT INTO evolucion_archivos (evolucion_id, filename)
                    VALUES (%s, %s)
                """, (nueva_evo_id, filename))

        evolucion = {
            'id': nueva_evo_id,
            'paciente_id': paciente_id,
            'fecha': fecha,
            'contenido': contenido,
            'indicaciones': indicaciones,
            'usuario_id': current_user.id,
            'version': nueva_version,
            'padre_id': padre_id,
            'motivo_rectificacion': motivo_rectificacion,
        }
        hash_evolucion, firmado_en = registrar_firma_y_auditoria(
            cursor, evolucion, 'rectificacion'
        )
        cursor.execute(
            """
            UPDATE evoluciones
            SET hash_local = %s, estado_firma = 'firmada', firmado_en = %s
            WHERE id = %s
            """,
            (hash_evolucion, firmado_en, nueva_evo_id),
        )
        conn.commit()

    except Exception:
        conn.rollback()
        if upload_dir and os.path.isdir(upload_dir):
            import shutil
            shutil.rmtree(upload_dir, ignore_errors=True)
        _log_db_error("Patient evolution edit database error", conn)
        raise
    finally:
        cursor.close()
        conn.close()

    # 8. Consolidar historia clínica luego de cerrar la transacción firmada.
    try:
        hash_local = actualizar_historia(paciente_id, current_user.id)
        partes = []
        if hash_evolucion:
            partes.append(f"evolucion hash {hash_evolucion[:10]}...")
        if hash_local:
            partes.append(f"historia hash {hash_local[:10]}...")
        msg_extra = f" ({', '.join(partes)})" if partes else ""
    except Exception as e:
        print(f"⚠️ Error actualizando historia consolidada tras edicion: {e}")
        msg_extra = " (⚠️ No se pudo actualizar historia)"

    return jsonify({
        'message': f'Evolución editada (rectificación) y firmada como versión {nueva_version} ✅{msg_extra}',
        'id': nueva_evo_id,
        'hash_local': hash_evolucion,
        'estado_firma': 'firmada',
        'version': nueva_version,
    })


@bp_pacientes.route('/api/pacientes/<int:paciente_id>/evolucion/<int:evo_id>/historial', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_get_historial_evolucion(paciente_id, evo_id):
    """
    Retorna la lista de todas las versiones (historial de cambios) de una evolucion.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, padre_id FROM evoluciones WHERE id = %s AND paciente_id = %s", (evo_id, paciente_id))
        evolucion = cursor.fetchone()
        
        if not evolucion:
            return jsonify({'error': 'Evolución no encontrada'}), 404

        padre_id = evolucion['padre_id'] if evolucion['padre_id'] is not None else evolucion['id']

        cursor.execute("""
            SELECT e.id, e.fecha, e.contenido, e.indicaciones, e.creado_en, e.version, e.activo,
                   e.estado_firma, e.firmado_en, e.motivo_rectificacion,
                   f.payload_version AS firma_payload_version,
                   f.payload_hash AS firma_payload_hash,
                   f.algoritmo AS firma_algoritmo,
                   f.firmado_en AS firma_firmado_en,
                   f.rol AS firma_rol,
                   f.matricula_tipo AS firma_matricula_tipo,
                   f.matricula_numero AS firma_matricula_numero,
                   f.matricula_provincia AS firma_matricula_provincia,
                   u.nombre AS nombre_usuario,
                   CASE
                       WHEN u.rol = 'director' THEN 'Director'
                       ELSE COALESCE(u.especialidad, 'Sin especificar')
                   END AS especialidad_usuario
            FROM evoluciones e
            JOIN usuarios u ON e.usuario_id = u.id
            LEFT JOIN firmas_electronicas f ON f.evolucion_id = e.id
            WHERE (e.id = %s OR e.padre_id = %s)
            ORDER BY e.version ASC
        """, (padre_id, padre_id))
        
        historial = cursor.fetchall()
        
        for item in historial:
            cursor.execute("SELECT filename FROM evolucion_archivos WHERE evolucion_id = %s", (item['id'],))
            archivos = cursor.fetchall()
            item['archivos'] = [{
                'nombre': a['filename'],
                'url': f"/api/uploads/evoluciones/{item['id']}/{a['filename']}"
            } for a in archivos]
            item['creado_en'] = _to_iso_arg(item.get('creado_en'))
            item['firmado_en'] = _to_iso_arg(item.get('firmado_en'))
            item['firma_firmado_en'] = _to_iso_arg(item.get('firma_firmado_en'))

        return jsonify(historial)

    except Exception:
        _log_db_error("Patient evolution history read database error", conn)
        raise
    finally:
        cursor.close()
        conn.close()


@bp_pacientes.route('/api/pacientes/<int:paciente_id>/evolucion/<int:evo_id>/firma', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def api_verificar_firma_evolucion(paciente_id, evo_id):
    """Verify the local electronic-signature payload without contacting BFA."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT e.*, f.payload_version AS firma_payload_version,
                   f.payload_hash AS firma_payload_hash,
                   f.algoritmo AS firma_algoritmo,
                   f.firmado_en AS firma_firmado_en,
                   u.nombre AS firmante_nombre,
                   COALESCE(f.rol, u.rol) AS firmante_rol,
                   COALESCE(f.matricula_tipo, u.matricula_tipo) AS firmante_matricula_tipo,
                   COALESCE(f.matricula_numero, u.matricula_numero) AS firmante_matricula_numero,
                   COALESCE(f.matricula_provincia, u.matricula_provincia) AS firmante_matricula_provincia
            FROM evoluciones e
            JOIN usuarios u ON u.id = e.usuario_id
            LEFT JOIN firmas_electronicas f ON f.evolucion_id = e.id
            WHERE e.id = %s AND e.paciente_id = %s
            LIMIT 1
            """,
            (evo_id, paciente_id),
        )
        evolucion = cursor.fetchone()
        if not evolucion:
            return jsonify({'error': 'Evolución no encontrada'}), 404

        firma_hash = evolucion.get('firma_payload_hash')
        signer = {
            'rol': evolucion.get('firmante_rol'),
            'matricula_tipo': evolucion.get('firmante_matricula_tipo'),
            'matricula_numero': evolucion.get('firmante_matricula_numero'),
            'matricula_provincia': evolucion.get('firmante_matricula_provincia'),
        }
        calculado = hash_payload(payload_evolucion_firmable(evolucion, signer))
        valida = bool(
            firma_hash
            and evolucion.get('estado_firma') == 'firmada'
            and evolucion.get('hash_local') == calculado
            and firma_hash == calculado
        )

        return jsonify({
            'evolucion_id': evo_id,
            'firmada': bool(firma_hash),
            'valida': valida,
            'estado_firma': evolucion.get('estado_firma') or 'pendiente',
            'hash_local': evolucion.get('hash_local'),
            'payload_hash': firma_hash,
            'algoritmo': evolucion.get('firma_algoritmo'),
            'payload_version': evolucion.get('firma_payload_version'),
            'firmado_en': _to_iso_arg(evolucion.get('firma_firmado_en') or evolucion.get('firmado_en')),
            'firmante': {
                'nombre': evolucion.get('firmante_nombre'),
                'rol': evolucion.get('firmante_rol'),
                'matricula_tipo': evolucion.get('firmante_matricula_tipo'),
                'matricula_numero': evolucion.get('firmante_matricula_numero'),
                'matricula_provincia': evolucion.get('firmante_matricula_provincia'),
            },
        })
    except Exception:
        conn.rollback()
        _log_db_error("Evolution electronic signature verification database error", conn)
        raise
    finally:
        cursor.close()
        conn.close()


# ==========================================================
# 📄 Exportar Historia Clínica en PDF (versión institucional)
# ==========================================================
@bp_pacientes.route('/api/pacientes/<int:id>/historia/pdf', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def exportar_historia_pdf(id):
    """Genera un PDF con toda la historia clínica del paciente, incluyendo adjuntos (imágenes y enlaces)."""
    from flask import current_app
    from PIL import Image as PILImage

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Paciente
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
    paciente = cursor.fetchone()
    if not paciente:
        cursor.close(); conn.close()
        return jsonify({'error': 'Paciente no encontrado'}), 404

    # Evoluciones
    cursor.execute("""
        SELECT 
            e.id,
            e.fecha,
            e.contenido,
            e.indicaciones,
            e.creado_en,
            e.version,
            e.estado_firma,
            e.firmado_en,
            e.motivo_rectificacion,
            f.payload_version AS firma_payload_version,
            f.payload_hash AS firma_payload_hash,
            f.algoritmo AS firma_algoritmo,
            f.firmado_en AS firma_firmado_en,
            f.rol AS firma_rol,
            f.matricula_tipo AS firma_matricula_tipo,
            f.matricula_numero AS firma_matricula_numero,
            f.matricula_provincia AS firma_matricula_provincia,
            u.nombre AS medico,
            u.matricula_tipo,
            u.matricula_numero,
            u.matricula_provincia,
            CASE 
                WHEN u.rol = 'director' THEN 'Director'
                ELSE COALESCE(u.especialidad, 'Sin especificar')
            END AS especialidad
        FROM evoluciones e
        JOIN usuarios u ON e.usuario_id = u.id
        LEFT JOIN firmas_electronicas f ON f.evolucion_id = e.id
        WHERE e.paciente_id = %s AND e.activo = 1
        ORDER BY e.fecha DESC
    """, (id,))

    evoluciones = cursor.fetchall()

    cursor.execute(
        """
        SELECT h.id, h.paciente_id, h.nombre_original, h.mime_type,
               h.tamanio_bytes, h.hash_sha256, h.cargado_en,
               u.nombre AS cargado_por
        FROM historia_archivos h
        JOIN usuarios u ON u.id = h.usuario_id
        WHERE h.paciente_id = %s
        ORDER BY h.cargado_en ASC, h.id ASC
        """,
        (id,),
    )
    historia_archivos = cursor.fetchall()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Right", alignment=TA_RIGHT, fontSize=9, textColor="#666666"))

    style_box = TableStyle([
        ('BOX', (0,0), (-1,-1), 0.6, colors.lightgrey),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ])

    elements = []
    # -------------------------------------------------------
    # 🔹 ENCABEZADO con logo y título
    # -------------------------------------------------------
    logo_path = os.path.join(current_app.root_path, "static", "img", "logo_cau_unsam2.png")

    if os.path.exists(logo_path):
        # 🔸 Logo apenas más grande
        logo = Image(logo_path, width=5*cm, height=2*cm)
    else:
        logo = Paragraph("<b>CAU UNSAM</b>", styles["Normal"])

    titulo = Paragraph("<b>Centro Asistencial Universitario </b>", styles["Title"])

    # Tabla de dos columnas: título (izquierda) y logo (derecha)
    encabezado = Table([[titulo, logo]], colWidths=[11*cm, 5*cm])
    encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(encabezado)
    elements.append(Spacer(1, 0.1*cm))

    # -------------------------------------------------------
    # 🔹 TÍTULO PRINCIPAL Y DATOS DEL PACIENTE
    # -------------------------------------------------------
    elements.append(Paragraph("<b>Historia Clínica</b>", styles["Heading1"]))
    elements.append(Spacer(1, 0.3*cm))

    datos_paciente = "<br/>".join(
        f"<b>{label}:</b> {_pdf_multiline(value)}"
        for label, value in [
            ("Paciente", f"{paciente.get('apellido', '').upper()} {paciente.get('nombre', '').upper()}".strip()),
            ("DNI", paciente.get("dni")),
            ("Cobertura", paciente.get("cobertura")),
            ("N° HC", paciente.get("nro_hc")),
            ("Fecha de nacimiento", paciente.get("fecha_nacimiento")),
            ("Sexo", paciente.get("sexo")),
        ]
        if _pdf_value_present(value)
    )
    elements.append(Paragraph(datos_paciente, styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    # Datos clínicos de ingreso: sólo se incorporan campos con contenido.
    campos_clinicos = [
        ("Diagnóstico", paciente.get("diagnostico")),
        ("Motivo de ingreso", paciente.get("motivo_ingreso")),
        ("Enfermedad actual", paciente.get("enfermedad_actual")),
        ("Antecedentes de la enfermedad actual", paciente.get("antecedentes_enfermedad_actual")),
        ("Antecedentes personales", paciente.get("antecedentes_personales")),
        ("Antecedentes heredofamiliares", paciente.get("antecedentes_heredofamiliares")),
    ]
    campos_clinicos = [(label, value) for label, value in campos_clinicos if _pdf_value_present(value)]
    if campos_clinicos:
        elements.append(Paragraph("<b>Información clínica inicial</b>", styles["Heading2"]))
        for label, value in campos_clinicos:
            elements.append(Paragraph(f"<b>{label}:</b> {_pdf_multiline(value)}", styles["Normal"]))
        elements.append(Spacer(1, 0.3*cm))

    if historia_archivos:
        elements.append(Paragraph("<b>Documentación adjunta a la historia</b>", styles["Heading2"]))
        elements.append(Paragraph(
            "Los originales se conservan en el sistema. Se informa la huella de cada archivo para verificar su integridad.",
            styles["Normal"],
        ))
        for archivo in historia_archivos:
            cargado = _format_pdf_date(archivo.get("cargado_en")) or "-"
            cargado_por = escape(str(archivo.get("cargado_por") or "-"))
            nombre = escape(str(archivo.get("nombre_original") or "-"))
            huella = escape(str(archivo.get("hash_sha256") or "-"))
            elements.append(Paragraph(
                f"<b>{nombre}</b> — cargado el {cargado} por {cargado_por}<br/>"
                f"SHA-256: {huella}",
                styles["Normal"],
            ))
        elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph("<b>Evoluciones:</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.3*cm))

    # -------------------------------------------------------
    # 🔹 EVOLUCIONES CON ARCHIVOS ADJUNTOS
    # -------------------------------------------------------
    if not evoluciones:
        elements.append(Paragraph("No hay evoluciones registradas.", styles["Normal"]))
    else:
        for evo in evoluciones:
            fecha_str = evo["fecha"].strftime("%d/%m/%Y") if hasattr(evo["fecha"], "strftime") else str(evo["fecha"])
            medico = evo["medico"]
            especialidad = "Director" if evo["especialidad"] == "director" else evo["especialidad"].capitalize()

            firmado_en = evo.get("firma_firmado_en") or evo.get("firmado_en") or evo.get("creado_en")
            firmado_str = _format_pdf_date(firmado_en)

            fila_superior = Table([
                [
                    Paragraph(f"<b>Fecha:</b> {fecha_str}", styles["Normal"]),
                    Paragraph(f"<font size='9' color='gray'>Actuación: {firmado_str or '-'} </font>", styles["Right"])
                ]
            ], colWidths=[8*cm, 8*cm])

            fila_superior.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))

            matricula_tipo = evo.get("firma_matricula_tipo") or evo.get("matricula_tipo")
            matricula_numero = evo.get("firma_matricula_numero") or evo.get("matricula_numero")
            matricula_provincia = evo.get("firma_matricula_provincia") or evo.get("matricula_provincia")
            matricula = " ".join(filter(None, [matricula_tipo, matricula_numero]))
            if matricula_provincia:
                matricula = f"{matricula} ({matricula_provincia})"
            matricula_html = f" — Matrícula: {escape(matricula)}" if matricula else ""
            fila_medico = Paragraph(f"<b>Profesional:</b> {escape(str(medico))} ({escape(str(especialidad))}){matricula_html}", styles["Normal"])

            fila_contenido = Paragraph(_pdf_multiline(evo["contenido"]), styles["Normal"])

            if evo.get("indicaciones"):
                indicaciones_html = _pdf_multiline(evo["indicaciones"])
                fila_indicaciones = Paragraph(f"<b>Indicaciones:</b> {indicaciones_html}", styles["Normal"])
            else:
                fila_indicaciones = Paragraph("", styles["Normal"])

            # --- ARMADO DEL BLOQUE FINAL ---
            filas = [
                [fila_superior],
                [fila_medico],
                [fila_contenido], 
            ]

            if evo.get("indicaciones"):
                filas.append([fila_indicaciones])

            if evo.get("estado_firma") == "firmada" and evo.get("firma_payload_hash"):
                fila_firma = Paragraph(
                    f"<b>Firma electrónica:</b> {escape(str(evo.get('firma_algoritmo') or 'SHA-256'))} "
                    f"— huella {escape(str(evo['firma_payload_hash']))}",
                    styles["Normal"],
                )
            else:
                fila_firma = Paragraph("<b>Firma electrónica:</b> pendiente", styles["Normal"])
            filas.append([fila_firma])

            bloque = Table(filas, colWidths=[16.5*cm])
            bloque.setStyle(style_box)

            elements.append(bloque)
            elements.append(Spacer(1, 0.4*cm))
            elements.append(Spacer(1, 0.1*cm))

            # 🔸 Buscar archivos adjuntos
            cursor.execute("""
                SELECT filename
                FROM evolucion_archivos
                WHERE evolucion_id = %s
            """, (evo["id"],))
            archivos = cursor.fetchall()

            if archivos:
                elements.append(Paragraph("<b>Archivos adjuntos:</b>", styles["Heading3"]))
                for a in archivos:
                    filename = a["filename"]
                    ext = filename.lower().split(".")[-1]
                    file_path = os.path.join(_evolucion_archivos_root(evo["id"]), filename)

                    if os.path.exists(file_path):
                        if ext in ["jpg", "jpeg", "png"]:
                            try:
                                with PILImage.open(file_path) as im:
                                    width, height = im.size
                                    aspect = height / float(width)
                                    new_width = 12 * cm
                                    new_height = new_width * aspect
                                    img = Image(file_path, width=new_width, height=new_height)
                                    img.hAlign = 'CENTER'
                                    elements.append(img)
                                    elements.append(Spacer(1, 0.3*cm))
                            except Exception as e:
                                elements.append(Paragraph(f"⚠️ No se pudo mostrar {filename}", styles["Normal"]))
                        else:
                            base_url = request.host_url.rstrip('/')
                            url = f"{base_url}/api/uploads/evoluciones/{evo['id']}/{filename}"

                            elements.append(Paragraph(
                                f"• <b>{filename}</b> — "
                                f"<a href='{url}' color='blue'>Haga clic aquí para descargar</a>",
                                styles['Normal']
                            ))

                            elements.append(Spacer(1, 0.5*cm))

                        # Salto de página cada 4 evoluciones aprox.
                        if evoluciones.index(evo) % 4 == 3:
                            elements.append(PageBreak())

    # -------------------------------------------------------
    # 🔹 PIE DE PÁGINA
    # -------------------------------------------------------
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColorRGB(0.4, 0.4, 0.4)

        # Texto institucional
        texto = "Documento emitido por el Sistema de Historia Clínica – Centro Asistencial Universitario UNSAM"
        canvas.drawString(2 * cm, 1.4 * cm, texto)

        # Fecha y hora de emisión
        fecha_hora = datetime.now().strftime("%d/%m/%Y - %H:%M")
        canvas.drawRightString(19 * cm, 1.4 * cm, f"Emitido: {fecha_hora}")

        # Número de página
        numero_pagina = canvas.getPageNumber()
        canvas.drawRightString(19 * cm, 1.0 * cm, f"Página {numero_pagina}")

        canvas.restoreState()

    # -------------------------------------------------------
    # 🔹 Páginas con marca de agua + footer
    # -------------------------------------------------------
    def first_page(canvas, doc):
        dibujar_marca_agua(canvas, doc)
        footer(canvas, doc)

    def later_pages(canvas, doc):
        dibujar_marca_agua(canvas, doc)
        footer(canvas, doc)

    # -------------------------------------------------------
    # 🔹 CONSTRUCCIÓN FINAL
    # -------------------------------------------------------
    doc.build(elements, onFirstPage=first_page, onLaterPages=later_pages )
    buffer.seek(0)
    cursor.close(); conn.close()

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"historia_paciente_{id}.pdf",
        mimetype="application/pdf"
    )


# ==========================================================
# 📄 Exportar Evolución individual en PDF
# ==========================================================
@bp_pacientes.route('/api/pacientes/<int:paciente_id>/evolucion/<int:evo_id>/pdf', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def exportar_evolucion_pdf(paciente_id, evo_id):
    """Genera un PDF institucional con una sola evolución clínica."""

    from flask import current_app
    from PIL import Image as PILImage

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # ==========================================================
    #  1) DATOS DEL PACIENTE
    # ==========================================================
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        cursor.close(); conn.close()
        return jsonify({'error': 'Paciente no encontrado'}), 404

    # ==========================================================
    #  2) DATOS DE LA EVOLUCIÓN
    # ==========================================================
    cursor.execute("""
        SELECT e.id, e.fecha, e.contenido, e.indicaciones, e.creado_en, e.version,
               e.estado_firma, e.firmado_en, e.motivo_rectificacion,
               f.payload_version AS firma_payload_version,
               f.payload_hash AS firma_payload_hash,
               f.algoritmo AS firma_algoritmo,
               f.firmado_en AS firma_firmado_en,
               f.rol AS firma_rol,
               f.matricula_tipo AS firma_matricula_tipo,
               f.matricula_numero AS firma_matricula_numero,
               f.matricula_provincia AS firma_matricula_provincia,
               u.nombre AS medico,
               u.matricula_tipo,
               u.matricula_numero,
               u.matricula_provincia,
               CASE WHEN u.rol = 'director' THEN 'Director'
                    ELSE COALESCE(u.especialidad, 'Sin especificar')
               END AS especialidad
        FROM evoluciones e
        JOIN usuarios u ON e.usuario_id = u.id
        LEFT JOIN firmas_electronicas f ON f.evolucion_id = e.id
        WHERE e.paciente_id = %s AND e.id = %s
        LIMIT 1
    """, (paciente_id, evo_id))
    evolucion = cursor.fetchone()

    if not evolucion:
        cursor.close(); conn.close()
        return jsonify({'error': 'Evolución no encontrada'}), 404

    # ==========================================================
    #  3) ARCHIVOS ADJUNTOS
    # ==========================================================
    cursor.execute("SELECT filename FROM evolucion_archivos WHERE evolucion_id = %s", (evo_id,))
    archivos = cursor.fetchall()

    cursor.close(); conn.close()

    # ==========================================================
    #  4) PDF – Construcción principal
    # ==========================================================
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Right", alignment=TA_RIGHT, fontSize=9, textColor="#666666"))

    elements = []

    # ----------------------------------------------------------
    # 🔹 ENCABEZADO CON LOGO Y TÍTULO
    # ----------------------------------------------------------
    logo_path = os.path.join(current_app.root_path, "static", "img", "logo_cau_unsam2.png")

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5*cm, height=2*cm)
    else:
        logo = Paragraph("<b>CAU UNSAM</b>", styles["Normal"])

    titulo = Paragraph("<b>Centro Asistencial Universitario UNSAM</b>", styles["Title"])

    encabezado = Table([[titulo, logo]], colWidths=[11*cm, 5*cm])
    encabezado.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0)
    ]))

    elements.append(encabezado)
    elements.append(Spacer(1, 0.3*cm))

    # Fecha de generación
    fecha_actual = datetime.now().strftime("%d/%m/%Y - %H:%M")
    elements.append(Paragraph(f"<i>Fecha de generación: {fecha_actual}</i>", styles["Right"]))
    elements.append(Spacer(1, 0.5*cm))

    # ----------------------------------------------------------
    # 🔹 DATOS DEL PACIENTE
    # ----------------------------------------------------------
    datos_paciente = "<br/>".join(
        f"<b>{label}:</b> {_pdf_multiline(value)}"
        for label, value in [
            ("Paciente", f"{paciente.get('apellido', '')} {paciente.get('nombre', '')}".strip()),
            ("DNI", paciente.get("dni")),
            ("N° HC", paciente.get("nro_hc")),
            ("Cobertura", paciente.get("cobertura")),
        ]
        if _pdf_value_present(value)
    )
    elements.append(Paragraph(datos_paciente, styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    campos_clinicos = [
        ("Diagnóstico", paciente.get("diagnostico")),
        ("Motivo de ingreso", paciente.get("motivo_ingreso")),
        ("Enfermedad actual", paciente.get("enfermedad_actual")),
        ("Antecedentes de la enfermedad actual", paciente.get("antecedentes_enfermedad_actual")),
        ("Antecedentes personales", paciente.get("antecedentes_personales")),
        ("Antecedentes heredofamiliares", paciente.get("antecedentes_heredofamiliares")),
    ]
    campos_clinicos = [(label, value) for label, value in campos_clinicos if _pdf_value_present(value)]
    for label, value in campos_clinicos:
        elements.append(Paragraph(f"<b>{label}:</b> {_pdf_multiline(value)}", styles["Normal"]))
    if campos_clinicos:
        elements.append(Spacer(1, 0.3*cm))

    # ----------------------------------------------------------
    # INFORMACIÓN DE LA EVOLUCIÓN
    # ----------------------------------------------------------
    fecha_evo = evolucion["fecha"].strftime("%d/%m/%Y")

    elements.append(Paragraph(f"<b>Fecha:</b> {fecha_evo}", styles["Normal"]))
    elements.append(Spacer(1, 0.1*cm))
    matricula_tipo = evolucion.get("firma_matricula_tipo") or evolucion.get("matricula_tipo")
    matricula_numero = evolucion.get("firma_matricula_numero") or evolucion.get("matricula_numero")
    matricula_provincia = evolucion.get("firma_matricula_provincia") or evolucion.get("matricula_provincia")
    matricula = " ".join(filter(None, [matricula_tipo, matricula_numero]))
    if matricula_provincia:
        matricula = f"{matricula} ({matricula_provincia})"
    matricula_html = f" — Matrícula: {escape(matricula)}" if matricula else ""
    elements.append(Paragraph(
        f"<b>Profesional:</b> {escape(str(evolucion['medico']))} "
        f"({escape(str(evolucion['especialidad']))}){matricula_html}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 0.1*cm))
    firmado_en = evolucion.get("firma_firmado_en") or evolucion.get("firmado_en") or evolucion.get("creado_en")
    elements.append(Paragraph(
        f"<b>Actuación profesional:</b> {_format_pdf_date(firmado_en) or '-'}",
        styles["Normal"],
    ))
    if evolucion.get("estado_firma") == "firmada" and evolucion.get("firma_payload_hash"):
        elements.append(Paragraph(
            f"<b>Firma electrónica:</b> {escape(str(evolucion.get('firma_algoritmo') or 'SHA-256'))} "
            f"— huella {escape(str(evolucion['firma_payload_hash']))}",
            styles["Normal"],
        ))
    else:
        elements.append(Paragraph("<b>Firma electrónica:</b> pendiente", styles["Normal"]))
    elements.append(Spacer(1, 0.25*cm))

    # --- CONTENIDO DE LA EVOLUCIÓN ---
    elements.append(Paragraph("<b>Evolución:</b>", styles["Normal"]))
    elements.append(Paragraph(_pdf_multiline(evolucion["contenido"]), styles["Normal"]))
    elements.append(Spacer(1, 0.3*cm))

    # --- INDICACIONES (OPCIONAL) ---
    if evolucion.get("indicaciones"):
        elements.append(Paragraph("<b>Indicaciones:</b>", styles["Normal"]))
        elements.append(Paragraph(_pdf_multiline(evolucion["indicaciones"]), styles["Normal"]))
        elements.append(Spacer(1, 0.3*cm))

    # ----------------------------------------------------------
    # ARCHIVOS ADJUNTOS (IMÁGENES + LINKS)
    # ----------------------------------------------------------
    if archivos:
        elements.append(Paragraph("<b>Archivos adjuntos:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.1*cm))

        for a in archivos:
            nombre = a["filename"]
            file_path = os.path.join(_evolucion_archivos_root(evo_id), nombre)
            ext = nombre.lower().split(".")[-1]

            # IMÁGENES
            if ext in ["jpg", "jpeg", "png"]:
                try:
                    with PILImage.open(file_path) as im:
                        w, h = im.size
                        aspect = h / w
                        new_width = 12 * cm
                        new_height = new_width * aspect

                        img = Image(file_path, width=new_width, height=new_height)
                        img.hAlign = "CENTER"
                        elements.append(img)
                        elements.append(Spacer(1, 0.3*cm))
                except:
                    elements.append(Paragraph(f"⚠️ No se pudo mostrar {nombre}", styles["Normal"]))
            else:
                # LINK CLICKEABLE
                url = f"{request.host_url.rstrip('/')}/api/uploads/evoluciones/{evo_id}/{nombre}"
                elements.append(Paragraph(f"• <a href='{url}' color='blue'>{nombre}</a>", styles["Normal"]))
                elements.append(Spacer(1, 0.1*cm))

    else:
        elements.append(Paragraph("<i>Sin archivos adjuntos</i>", styles["Normal"]))

    # ----------------------------------------------------------
    #  FOOTER + MARCA DE AGUA
    # ----------------------------------------------------------
    def footer(canvas, doc):
        dibujar_marca_agua(canvas, doc)
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(2 * cm, 1.5 * cm,
            "Documento emitido por el Sistema de Historia Clínica – CAU UNSAM")
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"evolucion_{evo_id}.pdf",
        mimetype="application/pdf"
    )


def dibujar_marca_agua(canvas, doc):
    """
    Dibuja una marca de agua diagonal suave en cada página.
    """
    canvas.saveState()

    canvas.setFont("Helvetica-Bold", 50)
    canvas.setFillColor(Color(0.6, 0.6, 0.6, alpha=0.12))  # gris suave transparente

    # Mover al centro de página
    width, height = A4
    canvas.translate(width / 2, height / 2)

    # Rotar texto 45 grados
    canvas.rotate(35)

    # Dibujar texto centrado
    texto = "DOCUMENTO CONFIDENCIAL – CAU UNSAM"
    canvas.drawCentredString(0, 0, texto)

    canvas.restoreState()
