from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.database import get_connection
from app.utils.pantalla import (
    abreviar_pacientes,
    anotar_estado_atencion,
    normalizar_consultorio,
)
from app.utils.permisos import requiere_rol

bp_pantalla = Blueprint("pantalla", __name__)

ROLES_CONFIG_PANTALLA = ("director", "administrativo")
MAX_SIGUIENTES = 3
TABLAS_VISIBLES = {"usuario": "usuarios", "grupo": "grupos_profesionales"}

SQL_ENTIDADES_VISIBLES = """
    SELECT 'usuario' AS tipo, u.id, u.nombre, u.consultorio
    FROM usuarios u
    WHERE u.mostrar_en_pantalla = 1 AND u.activo = 1 AND u.rol IN ('profesional', 'area')
    UNION ALL
    SELECT 'grupo' AS tipo, g.id, g.nombre, g.consultorio
    FROM grupos_profesionales g
    WHERE g.mostrar_en_pantalla = 1 AND g.consultorio IS NOT NULL AND g.consultorio <> ''
"""

SQL_TURNOS_HOY = """
    SELECT 'usuario' AS tipo, t.usuario_id AS entidad_id, t.id, t.fecha_inicio, t.fecha_fin,
           t.estado_asistencia, t.atencion_inicio, t.atencion_fin, 0 AS es_grupal,
           p.id AS paciente_id, p.nombre AS paciente_nombre, p.apellido AS paciente_apellido,
           NOW() AS ahora_db
    FROM turnos t
    JOIN pacientes p ON p.id = t.paciente_id
    WHERE t.fecha_inicio >= CURDATE() AND t.fecha_inicio < CURDATE() + INTERVAL 1 DAY
    UNION ALL
    SELECT 'grupo' AS tipo, tg.grupo_id AS entidad_id, tg.id, tg.fecha_inicio, tg.fecha_fin,
           tg.estado_asistencia, tg.atencion_inicio, tg.atencion_fin, 1 AS es_grupal,
           p.id AS paciente_id, p.nombre AS paciente_nombre, p.apellido AS paciente_apellido,
           NOW() AS ahora_db
    FROM turnos_grupales tg
    JOIN pacientes p ON p.id = tg.paciente_id
    WHERE tg.fecha_inicio >= CURDATE() AND tg.fecha_inicio < CURDATE() + INTERVAL 1 DAY
"""

SQL_VISIBLES = """
    SELECT 'usuario' AS tipo, u.id, u.nombre, u.consultorio, u.mostrar_en_pantalla,
           EXISTS(SELECT 1 FROM turnos t WHERE t.usuario_id = u.id AND t.fecha_inicio >= CURDATE() AND t.fecha_inicio < CURDATE() + INTERVAL 1 DAY) AS tiene_turnos_hoy
    FROM usuarios u
    WHERE u.activo = 1 AND u.rol IN ('profesional', 'area')
    UNION ALL
    SELECT 'grupo' AS tipo, g.id, g.nombre, g.consultorio, g.mostrar_en_pantalla,
           EXISTS(SELECT 1 FROM turnos_grupales tg WHERE tg.grupo_id = g.id AND tg.fecha_inicio >= CURDATE() AND tg.fecha_inicio < CURDATE() + INTERVAL 1 DAY) AS tiene_turnos_hoy
    FROM grupos_profesionales g
    ORDER BY tipo, nombre
"""


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if dt else None


def _inicio_atencion(turno):
    # Por el contrato de estado_atencion un turno en_atencion siempre tiene atencion_inicio;
    # el respaldo evita un TypeError al ordenar si alguna vez faltara.
    return turno["atencion_inicio"] or turno["fecha_inicio"]


def construir_tarjetas(cursor):
    """Función única que usan el televisor y la vista previa. Solo devuelve Nombre abreviado."""
    cursor.execute(SQL_ENTIDADES_VISIBLES)
    entidades = cursor.fetchall()
    cursor.execute(SQL_TURNOS_HOY)
    turnos = cursor.fetchall()
    anotar_estado_atencion(turnos)

    por_entidad = {}
    for t in turnos:
        por_entidad.setdefault((t["tipo"], t["entidad_id"]), []).append(t)

    crudas = []
    mostrados = []
    for e in sorted(entidades, key=lambda e: (e["tipo"], e["id"])):
        del_dia = por_entidad.get((e["tipo"], e["id"]))
        if not del_dia:
            continue  # de los visibles, solo aparecen los que tienen turnos hoy
        en_atencion = sorted(
            (t for t in del_dia if t["estado_atencion"] == "en_atencion"), key=lambda t: (_inicio_atencion(t), t["id"])
        )
        siguientes = sorted(
            (t for t in del_dia if t["estado_atencion"] == "esperando"), key=lambda t: (t["fecha_inicio"], t["id"])
        )[:MAX_SIGUIENTES]
        crudas.append((e, en_atencion, siguientes))
        mostrados.extend(en_atencion + siguientes)

    nombres = abreviar_pacientes(
        [{"id": t["paciente_id"], "nombre": t["paciente_nombre"], "apellido": t["paciente_apellido"]} for t in mostrados]
    )
    return [
        {
            "tipo": e["tipo"],
            "id": e["id"],
            "consultorio": e["consultorio"] or None,
            "nombre": e["nombre"],
            "en_atencion": [
                {"nombre": nombres[t["paciente_id"]], "atencion_inicio": _iso(t["atencion_inicio"])} for t in en_atencion
            ],
            "siguientes": [{"nombre": nombres[t["paciente_id"]]} for t in siguientes],
        }
        for e, en_atencion, siguientes in crudas
    ]


@bp_pantalla.route("/api/pantalla/vista-previa", methods=["GET"])
@login_required
@requiere_rol(*ROLES_CONFIG_PANTALLA)
def vista_previa():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        return jsonify({"tarjetas": construir_tarjetas(cursor)})
    finally:
        cursor.close()
        conn.close()


@bp_pantalla.route("/api/pantalla/visibles", methods=["GET"])
@login_required
@requiere_rol(*ROLES_CONFIG_PANTALLA)
def listar_visibles():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(SQL_VISIBLES)
        return jsonify(
            [
                {
                    "tipo": r["tipo"],
                    "id": r["id"],
                    "nombre": r["nombre"],
                    "consultorio": r["consultorio"],
                    "mostrar_en_pantalla": bool(r["mostrar_en_pantalla"]),
                    "tiene_turnos_hoy": bool(r["tiene_turnos_hoy"]),
                }
                for r in cursor.fetchall()
            ]
        )
    finally:
        cursor.close()
        conn.close()


@bp_pantalla.route("/api/pantalla/visibles/<tipo>/<int:entidad_id>", methods=["PATCH"])
@login_required
@requiere_rol(*ROLES_CONFIG_PANTALLA)
def actualizar_visible(tipo, entidad_id):
    tabla = TABLAS_VISIBLES.get(tipo)
    if not tabla:
        return jsonify({"error": "Tipo inválido"}), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "El cuerpo de la solicitud debe ser un objeto JSON"}), 400
    if "mostrar_en_pantalla" in data and not isinstance(data["mostrar_en_pantalla"], bool):
        return jsonify({"error": "mostrar_en_pantalla debe ser verdadero o falso"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # FOR UPDATE: evita carreras con el PUT de grupos que también toca estas columnas.
        cursor.execute(
            f"SELECT id, consultorio, mostrar_en_pantalla FROM {tabla} WHERE id = %s FOR UPDATE", (entidad_id,)
        )
        actual = cursor.fetchone()
        if not actual:
            return jsonify({"error": "No encontrado"}), 404

        consultorio = actual["consultorio"]
        if "consultorio" in data:
            consultorio, err = normalizar_consultorio(data["consultorio"])
            if err:
                return jsonify({"error": err}), 400
        visible = bool(actual["mostrar_en_pantalla"])
        if "mostrar_en_pantalla" in data:
            visible = data["mostrar_en_pantalla"]

        if tipo == "grupo" and visible and not consultorio:
            return jsonify({"error": "Un grupo necesita consultorio para estar visible en la pantalla"}), 400

        cursor.execute(
            f"UPDATE {tabla} SET consultorio = %s, mostrar_en_pantalla = %s WHERE id = %s",
            (consultorio, 1 if visible else 0, entidad_id),
        )
        conn.commit()
        return jsonify({"consultorio": consultorio, "mostrar_en_pantalla": visible})
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
