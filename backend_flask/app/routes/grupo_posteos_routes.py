from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.database import get_connection

bp_grupo_posteos = Blueprint("grupo_posteos", __name__)
ROLES_GESTION = ("director", "administrativo")


def _es_miembro_grupo(cursor, grupo_id, usuario_id):
    cursor.execute(
        """
        SELECT 1
        FROM grupo_miembros
        WHERE grupo_id = %s AND usuario_id = %s
        LIMIT 1
        """,
        (grupo_id, usuario_id),
    )
    return bool(cursor.fetchone())


def _grupo_existe(cursor, grupo_id):
    cursor.execute("SELECT id FROM grupos_profesionales WHERE id = %s", (grupo_id,))
    return bool(cursor.fetchone())


def _puede_acceder_grupo(cursor, grupo_id):
    if current_user.rol in ROLES_GESTION:
        return True
    return _es_miembro_grupo(cursor, grupo_id, current_user.id)


@bp_grupo_posteos.route("/api/grupos/<int:grupo_id>/posteos", methods=["GET"])
@login_required
def listar_posteos_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if not _grupo_existe(cursor, grupo_id):
            return jsonify({"error": "Grupo no encontrado"}), 404

        if not _puede_acceder_grupo(cursor, grupo_id):
            return jsonify({"error": "Acceso denegado"}), 403

        cursor.execute(
            """
            SELECT
                gp.id,
                gp.grupo_id,
                gp.titulo,
                gp.contenido,
                gp.autor_id,
                gp.creado_en,
                gp.actualizado_en,
                u.nombre AS autor_nombre,
                u.rol AS autor_rol
            FROM grupo_posteos gp
            JOIN usuarios u ON u.id = gp.autor_id
            WHERE gp.grupo_id = %s
            ORDER BY gp.creado_en DESC
            """,
            (grupo_id,),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    for row in rows:
        row["puede_eliminar"] = (
            current_user.rol in ROLES_GESTION or int(row.get("autor_id") or 0) == int(current_user.id)
        )

    return jsonify(rows)


@bp_grupo_posteos.route("/api/grupos/<int:grupo_id>/posteos", methods=["POST"])
@login_required
def crear_posteo_grupo(grupo_id):
    data = request.get_json(silent=True) or {}
    titulo = (data.get("titulo") or "").strip()
    contenido = (data.get("contenido") or "").strip()

    if not contenido:
        return jsonify({"error": "Contenido obligatorio"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if not _grupo_existe(cursor, grupo_id):
            return jsonify({"error": "Grupo no encontrado"}), 404

        if not _puede_acceder_grupo(cursor, grupo_id):
            return jsonify({"error": "Acceso denegado"}), 403

        cursor.execute(
            """
            INSERT INTO grupo_posteos (grupo_id, autor_id, titulo, contenido)
            VALUES (%s, %s, %s, %s)
            """,
            (grupo_id, current_user.id, titulo or None, contenido),
        )
        conn.commit()
        posteo_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "Posteo publicado", "id": posteo_id}), 201


@bp_grupo_posteos.route("/api/grupos/<int:grupo_id>/posteos/<int:posteo_id>", methods=["DELETE"])
@login_required
def eliminar_posteo_grupo(grupo_id, posteo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if not _grupo_existe(cursor, grupo_id):
            return jsonify({"error": "Grupo no encontrado"}), 404

        cursor.execute(
            """
            SELECT id, autor_id
            FROM grupo_posteos
            WHERE id = %s AND grupo_id = %s
            """,
            (posteo_id, grupo_id),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Posteo no encontrado"}), 404

        puede_eliminar = current_user.rol in ROLES_GESTION or int(row["autor_id"]) == int(current_user.id)
        if not puede_eliminar:
            return jsonify({"error": "Acceso denegado"}), 403

        cursor.execute("DELETE FROM grupo_posteos WHERE id = %s", (posteo_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "Posteo eliminado"})
