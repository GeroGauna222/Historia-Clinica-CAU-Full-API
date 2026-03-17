from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol
from datetime import datetime, time, timedelta, timezone

bp_ausencias = Blueprint("ausencias", __name__)
TZ_ARG = timezone(timedelta(hours=-3))


def _parse_iso_datetime(value):
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    return None


def _es_dia_completo(fecha_inicio, fecha_fin):
    return (
        fecha_inicio.date() == fecha_fin.date()
        and fecha_inicio.time() == time(0, 0, 0)
        and fecha_fin.hour == 23
        and fecha_fin.minute == 59
        and fecha_fin.second >= 59
    )


def _to_iso_arg(dt):
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_ARG)
        else:
            dt = dt.astimezone(TZ_ARG)
        return dt.isoformat()
    return dt


def _normalize_datetime(dt):
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(TZ_ARG).replace(tzinfo=None)


# ============================================================
#  Crear una ausencia (bloqueo de agenda)
# ============================================================
@bp_ausencias.route("/api/ausencias", methods=["POST"])
@login_required
@requiere_rol("director", "profesional", "administrativo", "area")
def crear_ausencia():
    data = request.get_json(silent=True) or {}

    # Compatibilidad: payload antiguo con "fecha" (dia completo).
    fecha_simple = data.get("fecha")
    if fecha_simple and not data.get("fecha_inicio") and not data.get("fecha_fin"):
        fecha_base = _parse_iso_datetime(fecha_simple)
        if fecha_base:
            data["fecha_inicio"] = datetime.combine(fecha_base.date(), time(0, 0, 0)).isoformat()
            data["fecha_fin"] = datetime.combine(fecha_base.date(), time(23, 59, 59)).isoformat()

    # Si es profesional/area, forzamos su ID. Si es director/admin, puede elegir.
    if current_user.rol in ["profesional", "area"]:
        usuario_id = current_user.id
    else:
        usuario_id = data.get("usuario_id") or current_user.id

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return jsonify({"error": "usuario_id invalido"}), 400

    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    motivo = data.get("motivo", "")

    if not fecha_inicio or not fecha_fin:
        return jsonify({"error": "Se requieren fecha_inicio y fecha_fin"}), 400

    fecha_inicio_dt = _parse_iso_datetime(fecha_inicio)
    fecha_fin_dt = _parse_iso_datetime(fecha_fin)

    if not fecha_inicio_dt or not fecha_fin_dt:
        return jsonify({"error": "Formato de fecha invalido"}), 400

    fecha_inicio_dt = _normalize_datetime(fecha_inicio_dt)
    fecha_fin_dt = _normalize_datetime(fecha_fin_dt)

    if fecha_inicio_dt >= fecha_fin_dt:
        return jsonify({"error": "fecha_inicio debe ser menor a fecha_fin"}), 400

    # Restriccion extra de seguridad
    if current_user.rol in ["profesional", "area"] and usuario_id != current_user.id:
        return jsonify({"error": "No puede bloquear agenda de otros profesionales"}), 403

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id
            FROM ausencias
            WHERE usuario_id = %s
              AND fecha_inicio < %s
              AND fecha_fin > %s
            LIMIT 1
            """,
            (usuario_id, fecha_fin_dt, fecha_inicio_dt),
        )
        ausencia_solapada = cursor.fetchone()
        if ausencia_solapada:
            return jsonify({"error": "Ya existe un bloqueo que se superpone con ese rango"}), 409

        cursor.execute(
            """
            INSERT INTO ausencias (usuario_id, fecha_inicio, fecha_fin, motivo, creado_por)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (usuario_id, fecha_inicio_dt, fecha_fin_dt, motivo, current_user.id),
        )
        conn.commit()

        return jsonify({"message": "Ausencia registrada", "id": cursor.lastrowid}), 201
    finally:
        cursor.close()
        conn.close()


# ============================================================
#  Listar ausencias
# ============================================================
@bp_ausencias.route("/api/ausencias", methods=["GET"])
@login_required
@requiere_rol("director", "profesional", "administrativo", "area")
def listar_ausencias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    filtro_usuario = request.args.get("usuario_id")

    # profesional/area solo ven lo propio
    if current_user.rol in ["profesional", "area"]:
        if filtro_usuario and str(filtro_usuario) != str(current_user.id):
            cursor.close()
            conn.close()
            return jsonify({"error": "No autorizado"}), 403

        usuario_id = current_user.id
        cursor.execute(
            """
            SELECT a.*, u.nombre AS nombre_usuario
            FROM ausencias a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.usuario_id = %s
            ORDER BY fecha_inicio
            """,
            (usuario_id,),
        )
    else:
        # director/admin ven todo
        if filtro_usuario:
            cursor.execute(
                """
                SELECT a.*, u.nombre AS nombre_usuario
                FROM ausencias a
                JOIN usuarios u ON a.usuario_id = u.id
                WHERE a.usuario_id = %s
                ORDER BY fecha_inicio
                """,
                (filtro_usuario,),
            )
        else:
            cursor.execute(
                """
                SELECT a.*, u.nombre AS nombre_usuario
                FROM ausencias a
                JOIN usuarios u ON a.usuario_id = u.id
                ORDER BY fecha_inicio
                """
            )

    ausencias = cursor.fetchall()
    cursor.close()
    conn.close()

    for a in ausencias:
        fecha_inicio = a.get("fecha_inicio")
        fecha_fin = a.get("fecha_fin")

        if isinstance(fecha_inicio, datetime) and isinstance(fecha_fin, datetime):
            a["es_dia_completo"] = _es_dia_completo(fecha_inicio, fecha_fin)
        else:
            a["es_dia_completo"] = False

        a["fecha_inicio"] = _to_iso_arg(fecha_inicio)
        a["fecha_fin"] = _to_iso_arg(fecha_fin)

    return jsonify(ausencias)


# ============================================================
#  Eliminar una ausencia
# ============================================================
@bp_ausencias.route("/api/ausencias/<int:ausencia_id>", methods=["DELETE"])
@login_required
@requiere_rol("director", "profesional", "administrativo", "area")
def eliminar_ausencia(ausencia_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM ausencias WHERE id=%s", (ausencia_id,))
    ausencia = cursor.fetchone()
    if not ausencia:
        cursor.close()
        conn.close()
        return jsonify({"error": "Ausencia no encontrada"}), 404

    # Restriccion: profesional/area solo pueden eliminar sus propias ausencias
    if current_user.rol in ["profesional", "area"] and ausencia["usuario_id"] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM ausencias WHERE id=%s", (ausencia_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Ausencia eliminada"})
