from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol

bp_comunicados = Blueprint("comunicados", __name__)
ROLES_PUBLICADORES = ("director", "administrativo")


@bp_comunicados.route("/api/comunicados", methods=["GET"])
@login_required
def listar_comunicados():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                c.id,
                c.titulo,
                c.contenido,
                c.autor_id,
                c.creado_en,
                c.actualizado_en,
                u.nombre AS autor_nombre,
                u.rol AS autor_rol
            FROM comunicados c
            JOIN usuarios u ON u.id = c.autor_id
            ORDER BY c.creado_en DESC
            """
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    es_publicador = current_user.rol in ROLES_PUBLICADORES
    for row in rows:
        row["puede_eliminar"] = es_publicador

    return jsonify(rows)


@bp_comunicados.route("/api/comunicados", methods=["POST"])
@login_required
@requiere_rol(*ROLES_PUBLICADORES)
def crear_comunicado():
    data = request.get_json(silent=True) or {}
    titulo = (data.get("titulo") or "").strip()
    contenido = (data.get("contenido") or "").strip()

    if not titulo:
        return jsonify({"error": "Titulo obligatorio"}), 400
    if not contenido:
        return jsonify({"error": "Contenido obligatorio"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO comunicados (titulo, contenido, autor_id)
            VALUES (%s, %s, %s)
            """,
            (titulo, contenido, current_user.id),
        )
        conn.commit()
        comunicado_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "Comunicado publicado", "id": comunicado_id}), 201


@bp_comunicados.route("/api/comunicados/<int:comunicado_id>", methods=["DELETE"])
@login_required
@requiere_rol(*ROLES_PUBLICADORES)
def eliminar_comunicado(comunicado_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM comunicados WHERE id = %s", (comunicado_id,))
        comunicado = cursor.fetchone()
        if not comunicado:
            return jsonify({"error": "Comunicado no encontrado"}), 404

        cursor.execute("DELETE FROM comunicados WHERE id = %s", (comunicado_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "Comunicado eliminado"})
