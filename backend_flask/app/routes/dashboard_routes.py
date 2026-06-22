from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.database import get_connection

bp_dashboard = Blueprint("dashboard", __name__)

ROLES_ADMIN = ("director", "administrativo")
ROLES_PERSONALES = ("profesional", "area")

DIAS_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miercoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sabado",
    6: "Domingo",
}


def _to_json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return value


def _normalizar_row(row):
    if not row:
        return row
    return {key: _to_json_value(value) for key, value in row.items()}


def _normalizar_rows(rows):
    return [_normalizar_row(row) for row in rows or []]


def _tipo_evento_ausencia(motivo):
    texto = (motivo or "").strip()
    if texto.startswith("[") and "]" in texto:
        tipo, detalle = texto[1:].split("]", 1)
        return (tipo.strip() or "Bloqueo"), detalle.strip()
    return "Bloqueo", texto


def _enriquecer_ausencias(rows):
    enriquecidas = []
    for row in rows or []:
        item = dict(row)
        tipo, detalle = _tipo_evento_ausencia(item.get("motivo"))
        item["tipo_evento"] = tipo
        item["detalle"] = detalle
        enriquecidas.append(_normalizar_row(item))
    return enriquecidas


def _primer_evento(turno, ausencia):
    eventos = []
    if turno:
        eventos.append({
            **turno,
            "tipo": "Turno",
            "titulo": f"{turno.get('paciente', '')} {turno.get('apellido', '')}".strip(),
            "detalle": turno.get("motivo") or "",
        })
    if ausencia:
        tipo, detalle = _tipo_evento_ausencia(ausencia.get("motivo"))
        eventos.append({
            **ausencia,
            "tipo": tipo,
            "titulo": tipo,
            "detalle": detalle,
            "paciente_id": None,
        })
    if not eventos:
        return None
    eventos.sort(key=lambda evento: evento.get("fecha_inicio"))
    return _normalizar_row(eventos[0])


def _payload_base(rol):
    return {
        "rol": rol,
        "resumen": {},
        "turnos_hoy": 0,
        "turnos": [],
        "proximo_turno": None,
        "proximo_evento": None,
        "disponibilidad_hoy": [],
        "ausencias": [],
        "ausencias_bloqueos": [],
        "alertas": {
            "turnos_superpuestos": [],
            "disponibilidad_hoy": [],
            "agenda_vacia": [],
        },
        "comunicados": [],
        "estadisticas": {},
    }


def _agregar_comunicados(cursor, data, rol, user_id):
    cursor.execute("""
        SELECT
            c.id,
            'institucional' AS origen,
            c.titulo,
            c.contenido,
            c.creado_en,
            u.nombre AS autor_nombre,
            NULL AS grupo_id,
            NULL AS grupo_nombre
        FROM comunicados c
        JOIN usuarios u ON u.id = c.autor_id
        ORDER BY c.creado_en DESC
        LIMIT 5
    """)
    comunicados = _normalizar_rows(cursor.fetchall())

    if rol in ROLES_ADMIN:
        cursor.execute("""
            SELECT
                gp.id,
                'grupo' AS origen,
                COALESCE(NULLIF(gp.titulo, ''), gp.contenido) AS titulo,
                gp.contenido,
                gp.creado_en,
                u.nombre AS autor_nombre,
                g.id AS grupo_id,
                g.nombre AS grupo_nombre
            FROM grupo_posteos gp
            JOIN grupos_profesionales g ON g.id = gp.grupo_id
            JOIN usuarios u ON u.id = gp.autor_id
            ORDER BY gp.creado_en DESC
            LIMIT 5
        """)
    else:
        cursor.execute("""
            SELECT
                gp.id,
                'grupo' AS origen,
                COALESCE(NULLIF(gp.titulo, ''), gp.contenido) AS titulo,
                gp.contenido,
                gp.creado_en,
                u.nombre AS autor_nombre,
                g.id AS grupo_id,
                g.nombre AS grupo_nombre
            FROM grupo_posteos gp
            JOIN grupos_profesionales g ON g.id = gp.grupo_id
            JOIN grupo_miembros gm ON gm.grupo_id = g.id
            JOIN usuarios u ON u.id = gp.autor_id
            WHERE gm.usuario_id = %s
            ORDER BY gp.creado_en DESC
            LIMIT 5
        """, (user_id,))

    comunicados.extend(_normalizar_rows(cursor.fetchall()))
    comunicados.sort(key=lambda item: item.get("creado_en") or "", reverse=True)
    data["comunicados"] = comunicados[:8]


@bp_dashboard.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    rol = current_user.rol
    user_id = current_user.id
    hoy = date.today()
    dia_hoy = DIAS_ES[hoy.weekday()]
    data = _payload_base(rol)

    try:
        if rol in ROLES_PERSONALES:
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha_inicio) = %s
                  AND t.usuario_id = %s
                ORDER BY t.fecha_inicio ASC
            """, (hoy, user_id))
            data["turnos"] = _normalizar_rows(cursor.fetchall())
            data["turnos_hoy"] = len(data["turnos"])

            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE t.usuario_id = %s
                  AND t.fecha_inicio > NOW()
                ORDER BY t.fecha_inicio ASC
                LIMIT 1
            """, (user_id,))
            proximo_turno = cursor.fetchone()

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.usuario_id = %s
                  AND a.fecha_inicio > NOW()
                ORDER BY a.fecha_inicio ASC
                LIMIT 1
            """, (user_id,))
            proxima_ausencia = cursor.fetchone()

            data["proximo_turno"] = _normalizar_row(proximo_turno)
            data["proximo_evento"] = _primer_evento(proximo_turno, proxima_ausencia)

            cursor.execute("""
                SELECT id, usuario_id, dia_semana, hora_inicio, hora_fin, activo
                FROM disponibilidades
                WHERE usuario_id = %s
                  AND dia_semana = %s
                  AND activo = 1
                ORDER BY hora_inicio ASC
            """, (user_id, dia_hoy))
            data["disponibilidad_hoy"] = _normalizar_rows(cursor.fetchall())

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.usuario_id = %s
                  AND a.fecha_fin >= %s
                ORDER BY a.fecha_inicio ASC
                LIMIT 5
            """, (user_id, hoy))
            data["ausencias"] = _enriquecer_ausencias(cursor.fetchall())

            data["resumen"] = {
                "turnos_hoy": len(data["turnos"]),
                "disponibilidad_hoy": len(data["disponibilidad_hoy"]),
            }

        elif rol in ROLES_ADMIN:
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha_inicio) = %s
                ORDER BY t.fecha_inicio ASC
            """, (hoy,))
            data["turnos"] = _normalizar_rows(cursor.fetchall())
            data["turnos_hoy"] = len(data["turnos"])

            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE t.fecha_inicio > NOW()
                ORDER BY t.fecha_inicio ASC
                LIMIT 1
            """)
            proximo_turno = cursor.fetchone()

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.fecha_inicio > NOW()
                ORDER BY a.fecha_inicio ASC
                LIMIT 1
            """)
            proxima_ausencia = cursor.fetchone()

            data["proximo_turno"] = _normalizar_row(proximo_turno)
            data["proximo_evento"] = _primer_evento(proximo_turno, proxima_ausencia)

            cursor.execute("""
                SELECT d.id, d.usuario_id, u.nombre AS profesional,
                       d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
                FROM disponibilidades d
                JOIN usuarios u ON u.id = d.usuario_id
                WHERE d.dia_semana = %s
                  AND d.activo = 1
                  AND u.activo = 1
                ORDER BY u.nombre ASC, d.hora_inicio ASC
            """, (dia_hoy,))
            disponibilidad_hoy = _normalizar_rows(cursor.fetchall())
            data["disponibilidad_hoy"] = disponibilidad_hoy
            data["alertas"]["disponibilidad_hoy"] = disponibilidad_hoy

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.fecha_inicio < DATE_ADD(%s, INTERVAL 1 DAY)
                  AND a.fecha_fin >= %s
                ORDER BY a.fecha_inicio ASC
                LIMIT 8
            """, (hoy, hoy))
            data["ausencias"] = _enriquecer_ausencias(cursor.fetchall())
            data["ausencias_bloqueos"] = data["ausencias"]

            cursor.execute("""
                SELECT
                    t1.id AS turno_id,
                    t2.id AS turno_solapado_id,
                    t1.fecha_inicio,
                    t1.fecha_fin,
                    t2.fecha_inicio AS fecha_inicio_solapada,
                    t2.fecha_fin AS fecha_fin_solapada,
                    u.id AS usuario_id,
                    u.nombre AS profesional,
                    CONCAT(p1.nombre, ' ', p1.apellido) AS paciente,
                    CONCAT(p2.nombre, ' ', p2.apellido) AS paciente_solapado
                FROM turnos t1
                JOIN turnos t2
                  ON t1.usuario_id = t2.usuario_id
                 AND t1.id < t2.id
                 AND t1.fecha_inicio < t2.fecha_fin
                 AND t1.fecha_fin > t2.fecha_inicio
                JOIN usuarios u ON u.id = t1.usuario_id
                JOIN pacientes p1 ON p1.id = t1.paciente_id
                JOIN pacientes p2 ON p2.id = t2.paciente_id
                WHERE DATE(t1.fecha_inicio) = %s
                  AND DATE(t2.fecha_inicio) = %s
                ORDER BY u.nombre ASC, t1.fecha_inicio ASC
            """, (hoy, hoy))
            data["alertas"]["turnos_superpuestos"] = _normalizar_rows(cursor.fetchall())

            cursor.execute("""
                SELECT u.id AS usuario_id, u.nombre AS profesional,
                       d.hora_inicio, d.hora_fin
                FROM usuarios u
                JOIN disponibilidades d ON d.usuario_id = u.id
                LEFT JOIN turnos t
                  ON t.usuario_id = u.id
                 AND DATE(t.fecha_inicio) = %s
                WHERE u.activo = 1
                  AND u.rol IN ('profesional', 'area')
                  AND d.dia_semana = %s
                  AND d.activo = 1
                  AND t.id IS NULL
                ORDER BY u.nombre ASC
            """, (hoy, dia_hoy))
            data["alertas"]["agenda_vacia"] = _normalizar_rows(cursor.fetchall())

            data["resumen"] = {
                "turnos_hoy": len(data["turnos"]),
                "disponibilidad_hoy": len(data["disponibilidad_hoy"]),
                "turnos_superpuestos": len(data["alertas"]["turnos_superpuestos"]),
            }

        else:
            return jsonify({"error": "Rol no reconocido"}), 403

        _agregar_comunicados(cursor, data, rol, user_id)
        data["estadisticas"] = data["resumen"]
        return jsonify(data)

    except Exception as e:
        print("Error en /api/dashboard:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@bp_dashboard.route("/api/dashboard/semanal", methods=["GET"])
@login_required
def get_dashboard_semanal():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    rol = current_user.rol
    user_id = current_user.id

    hoy = date.today()
    hasta_7_dias = hoy + timedelta(days=6)

    try:
        if rol in ["profesional", "area"]:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM turnos
                WHERE usuario_id = %s
                AND DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (user_id, hoy, hasta_7_dias))
        else:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM turnos
                WHERE DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (hoy, hasta_7_dias))

        turnos = cursor.fetchall()

        if rol in ["profesional", "area"]:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM ausencias
                WHERE usuario_id = %s
                AND DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (user_id, hoy, hasta_7_dias))
        else:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM ausencias
                WHERE DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (hoy, hasta_7_dias))

        ausencias = cursor.fetchall()

        labels = []
        valores_turnos = []
        valores_ausencias = []

        for i in range(7):
            dia = hoy + timedelta(days=i)
            labels.append(dia.strftime("%d/%m"))

            turno = next((t["total"] for t in turnos if t["dia"] == dia), 0)
            ausencia = next((a["total"] for a in ausencias if a["dia"] == dia), 0)

            valores_turnos.append(turno)
            valores_ausencias.append(ausencia)

        return jsonify({
            "labels": labels,
            "turnos": valores_turnos,
            "ausencias": valores_ausencias
        })

    except Exception as e:
        print("Error en /api/dashboard/semanal:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
