from datetime import datetime, timedelta, timezone, time
import math

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from flask_mail import Message

from app import mail
from app.database import get_connection
from app.utils.permisos import requiere_rol

bp_turnos = Blueprint("turnos", __name__)

TZ_ARG = timezone(timedelta(hours=-3))
ROLES_TURNOS = ("director", "profesional", "administrativo", "area")
ROLES_TURNOS_GRUPALES = ("director", "administrativo", "area")
GROUP_SLOT_MINUTES = 20
WEEKDAY_NAME_TO_INDEX = {
    "lunes": 0,
    "lun": 0,
    "monday": 0,
    "martes": 1,
    "mar": 1,
    "tuesday": 1,
    "miercoles": 2,
    "mie": 2,
    "wednesday": 2,
    "jueves": 3,
    "jue": 3,
    "thursday": 3,
    "viernes": 4,
    "vie": 4,
    "friday": 4,
    "sabado": 5,
    "sab": 5,
    "saturday": 5,
    "domingo": 6,
    "dom": 6,
    "sunday": 6,
}


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

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    return None


def _normalize_datetime(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(TZ_ARG).replace(tzinfo=None)


def _to_iso_arg(dt):
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_ARG)
    else:
        dt = dt.astimezone(TZ_ARG)
    return dt.isoformat()


def _to_db_iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _ceil_to_slot(inicio_dt, slot_minutes):
    midnight = inicio_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = (inicio_dt - midnight).total_seconds()
    slot_seconds = int(slot_minutes) * 60
    if slot_seconds <= 0:
        return inicio_dt.replace(second=0, microsecond=0)
    if elapsed % slot_seconds == 0:
        return inicio_dt

    next_slot = math.floor(elapsed / slot_seconds) + 1
    return midnight + timedelta(seconds=next_slot * slot_seconds)


def _build_ajuste_payload(aplicado, inicio_original, inicio_ajustado, fin_ajustado):
    if not aplicado:
        return None
    return {
        "aplicado": True,
        "inicio_original": _to_db_iso(inicio_original),
        "inicio_ajustado": _to_db_iso(inicio_ajustado),
        "fin_ajustado": _to_db_iso(fin_ajustado),
    }


def _obtener_duracion_turno(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT duracion_turno FROM usuarios WHERE id = %s", (usuario_id,))
        row = cursor.fetchone()
        if row and row.get("duracion_turno"):
            return int(row["duracion_turno"])
    finally:
        cursor.close()
        conn.close()
    return 20


def _alinear_turno_individual(usuario_id, fecha_inicio_raw):
    inicio_original = _normalize_datetime(_parse_iso_datetime(fecha_inicio_raw))
    if not inicio_original:
        return None, None, None, "Formato de fecha invalido"

    duracion = _obtener_duracion_turno(usuario_id)
    inicio_ajustado = _ceil_to_slot(inicio_original, duracion)
    fin_ajustado = inicio_ajustado + timedelta(minutes=duracion)
    ajuste = _build_ajuste_payload(inicio_ajustado != inicio_original, inicio_original, inicio_ajustado, fin_ajustado)
    return inicio_ajustado, fin_ajustado, ajuste, None


def _alinear_turno_grupal(fecha_inicio_raw, fecha_fin_raw=None, slot_minutes=GROUP_SLOT_MINUTES):
    inicio_original = _normalize_datetime(_parse_iso_datetime(fecha_inicio_raw))
    if not inicio_original:
        return None, None, None, "Formato de fecha invalido"

    fin_original = _normalize_datetime(_parse_iso_datetime(fecha_fin_raw)) if fecha_fin_raw else None
    if not fin_original or fin_original <= inicio_original:
        fin_original = inicio_original + timedelta(minutes=slot_minutes)

    inicio_ajustado = _ceil_to_slot(inicio_original, slot_minutes)
    duracion = fin_original - inicio_original
    if duracion.total_seconds() <= 0:
        duracion = timedelta(minutes=slot_minutes)
    fin_ajustado = inicio_ajustado + duracion
    ajuste = _build_ajuste_payload(inicio_ajustado != inicio_original, inicio_original, inicio_ajustado, fin_ajustado)
    return inicio_ajustado, fin_ajustado, ajuste, None


def _parse_weekdays(raw_days):
    if not isinstance(raw_days, list) or not raw_days:
        return None, "dias_semana debe ser una lista no vacia"

    days = set()
    for value in raw_days:
        idx = None
        if isinstance(value, int):
            idx = value
        elif isinstance(value, str):
            clean = value.strip().lower()
            if not clean:
                continue
            if clean in WEEKDAY_NAME_TO_INDEX:
                idx = WEEKDAY_NAME_TO_INDEX[clean]
            else:
                try:
                    parsed = int(clean)
                    if 1 <= parsed <= 7:
                        idx = 6 if parsed == 7 else parsed - 1
                    else:
                        idx = parsed
                except ValueError:
                    return None, f"Dia invalido en dias_semana: {value}"
        else:
            return None, f"Dia invalido en dias_semana: {value}"

        if idx is None or idx < 0 or idx > 6:
            return None, f"Dia invalido en dias_semana: {value}"
        days.add(idx)

    if not days:
        return None, "dias_semana debe tener al menos un dia valido"
    return sorted(days), None


def _parse_batch_time(raw_hora, fallback_dt):
    if raw_hora is None or str(raw_hora).strip() == "":
        return fallback_dt.hour, fallback_dt.minute, None

    if not isinstance(raw_hora, str):
        return None, None, "hora invalida"

    hora_txt = raw_hora.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(hora_txt, fmt)
            return parsed.hour, parsed.minute, None
        except ValueError:
            continue
    return None, None, "hora invalida, use formato HH:MM"


def _resolver_duracion_grupal(fecha_inicio_raw, fecha_fin_raw=None, slot_minutes=GROUP_SLOT_MINUTES):
    inicio_dt = _normalize_datetime(_parse_iso_datetime(fecha_inicio_raw))
    if not inicio_dt:
        return None, "Formato de fecha invalido"

    fin_dt = _normalize_datetime(_parse_iso_datetime(fecha_fin_raw)) if fecha_fin_raw else None
    if not fin_dt or fin_dt <= inicio_dt:
        return timedelta(minutes=slot_minutes), None
    return fin_dt - inicio_dt, None


def _generar_fechas_tanda(fecha_inicio_raw, raw_weekdays, cantidad_raw, raw_hora):
    fecha_base = _normalize_datetime(_parse_iso_datetime(fecha_inicio_raw))
    if not fecha_base:
        return None, None, "Formato de fecha invalido"

    try:
        cantidad = int(cantidad_raw)
    except (TypeError, ValueError):
        return None, None, "cantidad invalida"
    if cantidad <= 0 or cantidad > 500:
        return None, None, "cantidad debe estar entre 1 y 500"

    weekdays, err = _parse_weekdays(raw_weekdays)
    if err:
        return None, None, err

    hora, minuto, err = _parse_batch_time(raw_hora, fecha_base)
    if err:
        return None, None, err

    fechas = []
    cursor_day = fecha_base.date()
    max_iter = max(366, cantidad * 30)
    loops = 0
    while len(fechas) < cantidad and loops < max_iter:
        candidate = datetime.combine(cursor_day, time(hour=hora, minute=minuto))
        if candidate.weekday() in weekdays and candidate >= fecha_base:
            fechas.append(candidate)
        cursor_day += timedelta(days=1)
        loops += 1

    if len(fechas) < cantidad:
        return None, None, "No se pudieron generar fechas para la tanda con los parametros indicados"

    return fecha_base, fechas, None


def medico_disponible(usuario_id, fecha_inicio, fecha_fin, turno_excluir_id=None, permitir_solape=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
    user_data = cursor.fetchone()
    es_area = user_data and user_data["rol"] == "area"

    inicio = datetime.fromisoformat(fecha_inicio)
    fin = datetime.fromisoformat(fecha_fin)
    hora_ini = inicio.strftime("%H:%M:%S")
    hora_fin = fin.strftime("%H:%M:%S")

    dia_semana = inicio.strftime("%A")
    dias = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miercoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sabado",
        "Sunday": "Domingo",
    }
    dia_es = dias.get(dia_semana, "Lunes")

    cursor.execute(
        """
        SELECT 1 FROM disponibilidades
        WHERE usuario_id = %s
        AND dia_semana = %s
        AND %s >= hora_inicio
        AND %s <= hora_fin
        AND activo = 1
    """,
        (usuario_id, dia_es, hora_ini, hora_fin),
    )
    disponible = cursor.fetchone()

    cursor.execute(
        """
        SELECT 1 FROM ausencias
        WHERE usuario_id = %s
        AND fecha_inicio < %s
        AND fecha_fin > %s
    """,
        (usuario_id, fecha_fin, fecha_inicio),
    )
    ausente = cursor.fetchone()

    ocupado = None
    if not es_area and not permitir_solape:
        params = [usuario_id, fecha_fin, fecha_inicio, fecha_inicio, fecha_fin]
        query = """
           SELECT 1 FROM turnos
            WHERE usuario_id = %s
            AND (
                (fecha_inicio < %s AND fecha_fin > %s)
                OR
                (fecha_inicio < %s AND fecha_fin > %s)
            )
        """
        if turno_excluir_id is not None:
            query += " AND id <> %s"
            params.append(turno_excluir_id)
        cursor.execute(query, tuple(params))
        ocupado = cursor.fetchone()

    cursor.close()
    conn.close()
    return bool(disponible) and not ausente and not ocupado


@bp_turnos.route("/api/agenda/sujetos", methods=["GET"])
@login_required
def agenda_sujetos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if current_user.rol in ["director", "administrativo"]:
            cursor.execute(
                """
                SELECT id, nombre, username, rol, duracion_turno
                FROM usuarios
                WHERE activo = 1
                ORDER BY nombre ASC
            """
            )
            sujetos = cursor.fetchall()
        else:
            cursor.execute(
                """
                SELECT id, nombre, username, rol, duracion_turno
                FROM usuarios
                WHERE id = %s AND activo = 1
            """,
                (current_user.id,),
            )
            sujetos = cursor.fetchall()
        return jsonify(sujetos)
    finally:
        cursor.close()
        conn.close()


@bp_turnos.route("/api/turnos", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_TURNOS)
def api_turnos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "GET":
        if current_user.rol in ["profesional", "area"]:
            cursor.execute(
                """
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                WHERE t.usuario_id = %s
                ORDER BY t.fecha_inicio ASC
            """,
                (current_user.id,),
            )
        else:
            cursor.execute(
                """
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                ORDER BY t.fecha_inicio ASC
            """
            )

        turnos = cursor.fetchall()
        cursor.close()
        conn.close()

        eventos = [
            {
                "id": t["id"],
                "paciente": t["nombre"],
                "dni": t["dni"],
                "start": t["fecha_inicio"].replace(tzinfo=TZ_ARG).isoformat(),
                "end": t["fecha_fin"].replace(tzinfo=TZ_ARG).isoformat(),
                "description": t["motivo"],
                "profesional": t["profesional"],
            }
            for t in turnos
        ]
        return jsonify(eventos)

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    paciente_id = data.get("paciente_id")
    usuario_id = data.get("usuario_id")
    fecha_inicio_raw = data.get("fecha_inicio")
    motivo = data.get("motivo")

    if not (paciente_id and usuario_id and fecha_inicio_raw):
        return jsonify({"error": "Campos obligatorios faltantes"}), 400

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return jsonify({"error": "usuario_id invalido"}), 400

    if current_user.rol == "profesional" and usuario_id != current_user.id:
        return jsonify({"error": "No puede asignar turnos a otros profesionales"}), 403

    fecha_inicio_dt, fecha_fin_dt, ajuste, err = _alinear_turno_individual(usuario_id, fecha_inicio_raw)
    if err:
        return jsonify({"error": err}), 400

    fecha_inicio = _to_db_iso(fecha_inicio_dt)
    fecha_fin = _to_db_iso(fecha_fin_dt)

    try:
        if not medico_disponible(
            usuario_id,
            fecha_inicio,
            fecha_fin,
            permitir_solape=current_user.rol in ["administrativo", "area"],
        ):
            return jsonify({"error": "El profesional no esta disponible en esa fecha u horario"}), 400

        cursor.execute(
            """
            INSERT INTO turnos (paciente_id, usuario_id, fecha_inicio, fecha_fin, motivo)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (paciente_id, usuario_id, fecha_inicio, fecha_fin, motivo),
        )
        conn.commit()

        cursor.execute("SELECT email, nombre, apellido FROM pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()
        cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", (usuario_id,))
        profesional = cursor.fetchone()

        if paciente and paciente.get("email"):
            try:
                fecha_legible = fecha_inicio_dt.strftime("%d/%m/%Y")
                hora_legible = fecha_inicio_dt.strftime("%H:%M")
                msg = Message(
                    subject="Confirmacion de turno medico",
                    recipients=[paciente["email"]],
                    body=(
                        f"Estimado {paciente['nombre']} {paciente['apellido']},\n\n"
                        "Le confirmamos que su turno ha sido agendado correctamente.\n\n"
                        f"Profesional: {profesional['nombre']}\n"
                        f"Fecha: {fecha_legible}\n"
                        f"Hora: {hora_legible} hs\n"
                        f"Motivo: {motivo or ''}\n"
                    ),
                )
                mail.send(msg)
            except Exception as mail_error:
                print("Error enviando mail:", mail_error)

        payload = {"message": "Turno creado correctamente."}
        if ajuste:
            payload["ajuste_horario"] = ajuste
        return jsonify(payload), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@bp_turnos.route("/api/turnos/<int:id>", methods=["DELETE"])
@login_required
@requiere_rol(*ROLES_TURNOS)
def eliminar_turno(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT t.usuario_id, t.paciente_id, t.fecha_inicio, t.fecha_fin, u.nombre AS profesional
        FROM turnos t
        JOIN usuarios u ON u.id = t.usuario_id
        WHERE t.id = %s
    """,
        (id,),
    )
    turno = cursor.fetchone()

    if not turno:
        cursor.close()
        conn.close()
        return jsonify({"error": "Turno no encontrado"}), 404

    if current_user.rol == "profesional" and turno["usuario_id"] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("SELECT nombre, apellido, email FROM pacientes WHERE id=%s", (turno["paciente_id"],))
    paciente = cursor.fetchone()
    cursor.execute("DELETE FROM turnos WHERE id=%s", (id,))
    conn.commit()

    if paciente and paciente.get("email"):
        try:
            fecha_dt = turno["fecha_inicio"].replace(tzinfo=TZ_ARG)
            fecha_legible = fecha_dt.strftime("%d/%m/%Y")
            hora_legible = fecha_dt.strftime("%H:%M")
            msg = Message(
                subject="Cancelacion de turno medico",
                recipients=[paciente["email"]],
                body=(
                    f"Estimado {paciente['nombre']} {paciente['apellido']},\n\n"
                    "Le informamos que su turno ha sido cancelado.\n\n"
                    f"Profesional: {turno['profesional']}\n"
                    f"Fecha: {fecha_legible}\n"
                    f"Hora: {hora_legible} hs\n"
                ),
            )
            mail.send(msg)
        except Exception as e:
            print("Error enviando mail de cancelacion:", e)

    cursor.close()
    conn.close()
    return jsonify({"message": "Turno eliminado correctamente"})


@bp_turnos.route("/api/turnos/<int:id>", methods=["PUT"])
@login_required
@requiere_rol(*ROLES_TURNOS)
def editar_turno(id):
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT usuario_id, fecha_inicio, fecha_fin, motivo FROM turnos WHERE id=%s", (id,))
    turno = cursor.fetchone()

    if not turno:
        cursor.close()
        conn.close()
        return jsonify({"error": "Turno no encontrado"}), 404

    if current_user.rol == "profesional" and turno["usuario_id"] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    fecha_inicio_raw = data.get("fecha_inicio") or data.get("fecha")
    if not fecha_inicio_raw:
        fecha_inicio_raw = turno["fecha_inicio"].strftime("%Y-%m-%dT%H:%M:%S")

    inicio_dt, fin_dt, ajuste, err = _alinear_turno_individual(turno["usuario_id"], fecha_inicio_raw)
    if err:
        cursor.close()
        conn.close()
        return jsonify({"error": err}), 400

    fecha_inicio = _to_db_iso(inicio_dt)
    fecha_fin = _to_db_iso(fin_dt)
    motivo = data.get("motivo", turno.get("motivo"))

    if not medico_disponible(
        turno["usuario_id"],
        fecha_inicio,
        fecha_fin,
        turno_excluir_id=id,
        permitir_solape=current_user.rol in ["administrativo", "area"],
    ):
        cursor.close()
        conn.close()
        return jsonify({"error": "El profesional no esta disponible en esa fecha u horario"}), 400

    cursor.execute(
        """
        UPDATE turnos
        SET fecha_inicio=%s, fecha_fin=%s, motivo=%s
        WHERE id=%s
    """,
        (fecha_inicio, fecha_fin, motivo, id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    payload = {"message": "Turno actualizado correctamente."}
    if ajuste:
        payload["ajuste_horario"] = ajuste
    return jsonify(payload)


@bp_turnos.route("/api/turnos/tanda", methods=["POST"])
@login_required
@requiere_rol(*ROLES_TURNOS)
def crear_turnos_tanda():
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        paciente_id = data.get("paciente_id")
        usuario_id = data.get("usuario_id")
        motivo = data.get("motivo", "")
        fecha_inicial = datetime.fromisoformat(data.get("fecha"))
        cantidad = int(data.get("cantidad", 1))
        dias_semana = data.get("dias_semana", [])

        if not (paciente_id and usuario_id and fecha_inicial and dias_semana):
            return jsonify({"error": "Faltan datos requeridos"}), 400

        if current_user.rol == "profesional" and usuario_id != current_user.id:
            return jsonify({"error": "No puede asignar turnos a otros profesionales"}), 403

        cursor.execute("SELECT duracion_turno FROM usuarios WHERE id=%s", (usuario_id,))
        profesional = cursor.fetchone()
        if not profesional or not profesional["duracion_turno"]:
            return jsonify({"error": "El profesional no tiene duracion de turno configurada"}), 400

        dur = profesional["duracion_turno"]
        dias_map = {"Lunes": 0, "Martes": 1, "Miercoles": 2, "Jueves": 3, "Viernes": 4, "Sabado": 5, "Domingo": 6}
        dias_indices = [dias_map[d] for d in dias_semana if d in dias_map]
        if not dias_indices:
            return jsonify({"error": "dias_semana invalido o vacio"}), 400

        turnos_creados = 0
        fecha_actual = fecha_inicial
        while turnos_creados < cantidad:
            if fecha_actual.weekday() in dias_indices:
                fecha_fin = fecha_actual + timedelta(minutes=dur)
                if not medico_disponible(
                    usuario_id,
                    fecha_actual.isoformat(),
                    fecha_fin.isoformat(),
                    permitir_solape=current_user.rol in ["administrativo", "area"],
                ):
                    fecha_actual += timedelta(days=1)
                    continue
                cursor.execute(
                    """
                    INSERT INTO turnos (paciente_id, usuario_id, fecha_inicio, fecha_fin, motivo)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (paciente_id, usuario_id, fecha_actual, fecha_fin, motivo),
                )
                turnos_creados += 1
            fecha_actual += timedelta(days=1)

        conn.commit()
        return jsonify({"message": f"Se crearon {turnos_creados} turnos correctamente."}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        print("Error al crear tanda de turnos:", e)
        return jsonify({"error": "Error al crear tanda de turnos"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp_turnos.route("/api/turnos/profesional/<int:usuario_id>", methods=["GET"])
@login_required
def turnos_profesional(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            t.id,
            t.fecha_inicio,
            t.fecha_fin,
            t.motivo,
            p.nombre AS paciente,
            p.dni,
            u.nombre AS profesional,
            '#007AFF' AS color
        FROM turnos t
        JOIN pacientes p ON t.paciente_id = p.id
        JOIN usuarios u ON t.usuario_id = u.id
        WHERE u.id = %s
    """,
        (usuario_id,),
    )
    individuales = cursor.fetchall()

    cursor.execute("SELECT grupo_id FROM grupo_miembros WHERE usuario_id = %s", (usuario_id,))
    grupos = [g["grupo_id"] for g in cursor.fetchall()]

    grupales = []
    if grupos:
        placeholders = ",".join(["%s"] * len(grupos))
        cursor.execute(
            f"""
            SELECT
                t.id,
                t.fecha_inicio,
                t.fecha_fin,
                t.motivo,
                p.nombre AS paciente,
                p.dni,
                u.nombre AS profesional,
                gp.color
            FROM turnos t
            JOIN pacientes p ON t.paciente_id = p.id
            JOIN usuarios u ON t.usuario_id = u.id
            JOIN grupo_miembros gm ON gm.usuario_id = u.id
            JOIN grupos_profesionales gp ON gp.id = gm.grupo_id
            WHERE gm.grupo_id IN ({placeholders})
        """,
            tuple(grupos),
        )
        grupales = cursor.fetchall()

    cursor.close()
    conn.close()

    def to_event(t):
        return {
            "id": t["id"],
            "title": f"{t['paciente']} ({t['profesional']})",
            "start": t["fecha_inicio"].replace(tzinfo=TZ_ARG).isoformat(),
            "end": t["fecha_fin"].replace(tzinfo=TZ_ARG).isoformat(),
            "paciente": t["paciente"],
            "dni": t["dni"],
            "profesional": t["profesional"],
            "description": t["motivo"],
            "backgroundColor": t["color"],
            "borderColor": t["color"],
        }

    return jsonify([to_event(t) for t in individuales] + [to_event(t) for t in grupales])


@bp_turnos.route("/api/turnos/profesional/completo", methods=["GET"])
@login_required
def turnos_profesional_completo():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    requested_user_id = request.args.get("usuario_id")
    es_operador = current_user.rol in ["director", "administrativo", "area"]

    target_user_id = None
    if current_user.rol == "profesional":
        target_user_id = current_user.id
    elif es_operador and requested_user_id:
        try:
            target_user_id = int(requested_user_id)
        except (TypeError, ValueError):
            cursor.close()
            conn.close()
            return jsonify({"error": "usuario_id invalido"}), 400
    elif current_user.rol in ["administrativo", "area"] and not requested_user_id:
        target_user_id = current_user.id

    if target_user_id is None and current_user.rol == "director":
        cursor.execute(
            """
            SELECT
                t.id,
                t.fecha_inicio AS start,
                t.fecha_fin AS end,
                p.nombre AS paciente,
                p.dni,
                u.nombre AS profesional,
                t.motivo AS description,
                '#1976D2' AS color,
                'individual' AS tipo,
                NULL AS grupo_id,
                NULL AS grupo_nombre,
                1 AS editable
            FROM turnos t
            JOIN pacientes p ON p.id = t.paciente_id
            JOIN usuarios u ON u.id = t.usuario_id
            ORDER BY t.fecha_inicio ASC
        """
        )
        turnos = cursor.fetchall()
        cursor.close()
        conn.close()

        for t in turnos:
            t["start"] = _to_iso_arg(t["start"])
            t["end"] = _to_iso_arg(t["end"])
            t["turnoId"] = t["id"]
        return jsonify(turnos)

    cursor.execute(
        """
        SELECT
            t.id,
            t.fecha_inicio AS start,
            t.fecha_fin AS end,
            p.nombre AS paciente,
            p.dni,
            u.nombre AS profesional,
            t.motivo AS description,
            '#1976D2' AS color,
            'individual' AS tipo,
            NULL AS grupo_id,
            NULL AS grupo_nombre,
            1 AS editable
        FROM turnos t
        JOIN pacientes p ON p.id = t.paciente_id
        JOIN usuarios u ON u.id = t.usuario_id
        WHERE t.usuario_id = %s
        ORDER BY t.fecha_inicio ASC
    """,
        (target_user_id,),
    )
    individuales = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            tg.id,
            tg.fecha_inicio AS start,
            tg.fecha_fin AS end,
            p.nombre AS paciente,
            p.dni,
            CONCAT('Grupo: ', gp.nombre) AS profesional,
            tg.motivo AS description,
            gp.color AS color,
            'grupal' AS tipo,
            gp.id AS grupo_id,
            gp.nombre AS grupo_nombre,
            0 AS editable
        FROM turnos_grupales tg
        JOIN grupos_profesionales gp ON gp.id = tg.grupo_id
        JOIN grupo_miembros gm ON gm.grupo_id = tg.grupo_id
        JOIN pacientes p ON p.id = tg.paciente_id
        WHERE gm.usuario_id = %s
        ORDER BY tg.fecha_inicio ASC
    """,
        (target_user_id,),
    )
    grupales_proyectados = cursor.fetchall()

    cursor.close()
    conn.close()

    eventos = []
    for t in individuales:
        t["start"] = _to_iso_arg(t["start"])
        t["end"] = _to_iso_arg(t["end"])
        t["turnoId"] = t["id"]
        eventos.append(t)

    for g in grupales_proyectados:
        g["start"] = _to_iso_arg(g["start"])
        g["end"] = _to_iso_arg(g["end"])
        g["turnoId"] = g["id"]
        g["id"] = f"grupal-{g['id']}"
        eventos.append(g)
    return jsonify(eventos)


@bp_turnos.route("/api/turnos/grupo/<int:grupo_id>", methods=["GET"])
@login_required
def turnos_por_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            t.id,
            t.fecha_inicio AS start,
            t.fecha_fin AS end,
            t.motivo AS description,
            p.nombre AS paciente,
            p.dni,
            u.nombre AS profesional,
            gp.color
        FROM grupo_miembros gm
        JOIN turnos t ON gm.usuario_id = t.usuario_id
        JOIN pacientes p ON p.id = t.paciente_id
        JOIN usuarios u ON u.id = t.usuario_id
        JOIN grupos_profesionales gp ON gp.id = gm.grupo_id
        WHERE gm.grupo_id = %s
        ORDER BY t.fecha_inicio ASC
    """,
        (grupo_id,),
    )
    turnos = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(
        [
            {
                "id": t["id"],
                "paciente": t["paciente"],
                "dni": t["dni"],
                "profesional": t["profesional"],
                "description": t["description"],
                "start": _to_iso_arg(t["start"]),
                "end": _to_iso_arg(t["end"]),
                "color": t["color"],
            }
            for t in turnos
        ]
    )


@bp_turnos.route("/api/turnos/grupales", methods=["GET"])
@login_required
def listar_turnos_grupales():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    grupo_id = request.args.get("grupo_id")
    solo_rehab = str(request.args.get("solo_rehabilitacion", "0")).lower() in {"1", "true", "yes", "on"}

    where = []
    params = []
    if grupo_id:
        where.append("tg.grupo_id = %s")
        params.append(grupo_id)
    if solo_rehab:
        where.append("gp.es_rehabilitacion = 1")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    cursor.execute(
        f"""
        SELECT
            tg.id,
            tg.grupo_id,
            gp.nombre AS grupo_nombre,
            gp.color,
            gp.es_rehabilitacion,
            tg.paciente_id,
            p.nombre AS paciente,
            p.dni,
            tg.fecha_inicio,
            tg.fecha_fin,
            tg.motivo,
            tg.creado_por
        FROM turnos_grupales tg
        JOIN grupos_profesionales gp ON gp.id = tg.grupo_id
        JOIN pacientes p ON p.id = tg.paciente_id
        {where_sql}
        ORDER BY tg.fecha_inicio ASC
    """,
        tuple(params),
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    puede_editar = current_user.rol in ROLES_TURNOS_GRUPALES
    payload = []
    for row in rows:
        payload.append(
            {
                "id": row["id"],
                "grupo_id": row["grupo_id"],
                "grupo_nombre": row["grupo_nombre"],
                "color": row["color"],
                "es_rehabilitacion": bool(row["es_rehabilitacion"]),
                "paciente_id": row["paciente_id"],
                "paciente": row["paciente"],
                "dni": row["dni"],
                "start": _to_iso_arg(row["fecha_inicio"]),
                "end": _to_iso_arg(row["fecha_fin"]),
                "description": row["motivo"],
                "tipo": "grupal",
                "editable": puede_editar,
            }
        )
    return jsonify(payload)


@bp_turnos.route("/api/turnos/grupales", methods=["POST"])
@login_required
@requiere_rol(*ROLES_TURNOS_GRUPALES)
def crear_turno_grupal():
    data = request.get_json(silent=True) or {}
    grupo_id = data.get("grupo_id")
    paciente_id = data.get("paciente_id")
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    motivo = data.get("motivo", "")
    modo = str(data.get("modo", "simple")).strip().lower()
    en_tanda_flag = str(data.get("en_tanda", "0")).strip().lower() in {"1", "true", "yes", "on"}
    es_tanda = modo == "tanda" or en_tanda_flag

    if not (grupo_id and paciente_id and fecha_inicio):
        return jsonify({"error": "grupo_id, paciente_id y fecha_inicio son obligatorios"}), 400

    try:
        grupo_id = int(grupo_id)
        paciente_id = int(paciente_id)
    except (TypeError, ValueError):
        return jsonify({"error": "grupo_id y paciente_id deben ser enteros"}), 400

    inicio_dt = None
    fin_dt = None
    ajuste = None
    fechas_tanda = []
    duracion_tanda = None
    if es_tanda:
        _, fechas_tanda, err = _generar_fechas_tanda(
            fecha_inicio,
            data.get("dias_semana"),
            data.get("cantidad"),
            data.get("hora"),
        )
        if err:
            return jsonify({"error": err}), 400
        duracion_tanda, err = _resolver_duracion_grupal(fecha_inicio, fecha_fin)
        if err:
            return jsonify({"error": err}), 400
    else:
        inicio_dt, fin_dt, ajuste, err = _alinear_turno_grupal(fecha_inicio, fecha_fin)
        if err:
            return jsonify({"error": err}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM grupos_profesionales WHERE id = %s", (grupo_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Grupo no encontrado"}), 404

        cursor.execute("SELECT id FROM pacientes WHERE id = %s", (paciente_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Paciente no encontrado"}), 404

        if es_tanda:
            created_ids = []
            ajustes = []
            for inicio_base in fechas_tanda:
                fin_base = inicio_base + duracion_tanda
                inicio_item, fin_item, ajuste_item, err = _alinear_turno_grupal(inicio_base, fin_base)
                if err:
                    raise ValueError(err)
                cursor.execute(
                    """
                    INSERT INTO turnos_grupales (grupo_id, paciente_id, fecha_inicio, fecha_fin, motivo, creado_por)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (grupo_id, paciente_id, _to_db_iso(inicio_item), _to_db_iso(fin_item), motivo, current_user.id),
                )
                created_ids.append(cursor.lastrowid)
                if ajuste_item:
                    ajustes.append(ajuste_item)

            conn.commit()
            payload = {
                "message": "Tanda de turnos grupales creada correctamente",
                "modo": "tanda",
                "cantidad_solicitada": len(fechas_tanda),
                "cantidad_creada": len(created_ids),
                "ids": created_ids,
            }
            if ajustes:
                payload["ajustes_horario"] = ajustes
            return jsonify(payload), 201

        cursor.execute(
            """
            INSERT INTO turnos_grupales (grupo_id, paciente_id, fecha_inicio, fecha_fin, motivo, creado_por)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (grupo_id, paciente_id, _to_db_iso(inicio_dt), _to_db_iso(fin_dt), motivo, current_user.id),
        )
        conn.commit()
        payload = {"message": "Turno grupal creado correctamente", "id": cursor.lastrowid}
        if ajuste:
            payload["ajuste_horario"] = ajuste
        return jsonify(payload), 201
    except ValueError as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@bp_turnos.route("/api/turnos/grupales/<int:turno_grupal_id>", methods=["PUT"])
@login_required
@requiere_rol(*ROLES_TURNOS_GRUPALES)
def editar_turno_grupal(turno_grupal_id):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, grupo_id, paciente_id, fecha_inicio, fecha_fin, motivo
            FROM turnos_grupales
            WHERE id = %s
        """,
            (turno_grupal_id,),
        )
        actual = cursor.fetchone()
        if not actual:
            return jsonify({"error": "Turno grupal no encontrado"}), 404

        grupo_id = data.get("grupo_id", actual["grupo_id"])
        paciente_id = data.get("paciente_id", actual["paciente_id"])
        fecha_inicio = data.get("fecha_inicio") or actual["fecha_inicio"].strftime("%Y-%m-%dT%H:%M:%S")
        fecha_fin = data.get("fecha_fin") or actual["fecha_fin"].strftime("%Y-%m-%dT%H:%M:%S")
        motivo = data.get("motivo", actual["motivo"])

        inicio_dt, fin_dt, ajuste, err = _alinear_turno_grupal(fecha_inicio, fecha_fin)
        if err:
            return jsonify({"error": err}), 400

        cursor.execute("SELECT id FROM grupos_profesionales WHERE id = %s", (grupo_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Grupo no encontrado"}), 404

        cursor.execute(
            """
            UPDATE turnos_grupales
            SET grupo_id=%s, paciente_id=%s, fecha_inicio=%s, fecha_fin=%s, motivo=%s
            WHERE id=%s
        """,
            (grupo_id, paciente_id, _to_db_iso(inicio_dt), _to_db_iso(fin_dt), motivo, turno_grupal_id),
        )
        conn.commit()
        payload = {"message": "Turno grupal actualizado correctamente"}
        if ajuste:
            payload["ajuste_horario"] = ajuste
        return jsonify(payload)
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@bp_turnos.route("/api/turnos/grupales/<int:turno_grupal_id>", methods=["DELETE"])
@login_required
@requiere_rol(*ROLES_TURNOS_GRUPALES)
def eliminar_turno_grupal(turno_grupal_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM turnos_grupales WHERE id=%s", (turno_grupal_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Turno grupal no encontrado"}), 404
        cursor.execute("DELETE FROM turnos_grupales WHERE id=%s", (turno_grupal_id,))
        conn.commit()
        return jsonify({"message": "Turno grupal eliminado"})
    finally:
        cursor.close()
        conn.close()
