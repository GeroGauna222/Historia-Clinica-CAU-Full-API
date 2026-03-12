from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol
import traceback
from datetime import datetime, timedelta, timezone

bp_grupos = Blueprint("grupos", __name__)
TZ_ARG = timezone(timedelta(hours=-3))

# 🛠️ Función auxiliar vital para evitar el Error 500
def extraer_ids_limpios(lista_miembros):
    ids_limpios = []
    for item in lista_miembros:
        try:
            if isinstance(item, dict):
                ids_limpios.append(int(item.get('id')))
            else:
                ids_limpios.append(int(item))
        except (ValueError, TypeError):
            continue
    return ids_limpios


def _to_iso_arg(dt):
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_ARG)
        else:
            dt = dt.astimezone(TZ_ARG)
        return dt.isoformat()
    return dt

# =====================================================
# 📋 Obtener todos los grupos
# =====================================================
@bp_grupos.route("/api/grupos", methods=["GET"])
@login_required
def obtener_grupos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, nombre, descripcion, color FROM grupos_profesionales ORDER BY nombre ASC")
        grupos = cursor.fetchall()

        for g in grupos:
            cursor.execute("""
                SELECT u.id, u.nombre, u.rol
                FROM grupo_miembros gm
                JOIN usuarios u ON gm.usuario_id = u.id
                WHERE gm.grupo_id = %s
            """, (g["id"],))
            g["miembros"] = cursor.fetchall()
            
        return jsonify(grupos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); conn.close()

# =====================================================
# 🔹 Obtener un grupo por ID
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>", methods=["GET"])
@login_required
def obtener_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, nombre, descripcion, color FROM grupos_profesionales WHERE id = %s", (grupo_id,))
        grupo = cursor.fetchone()

        if not grupo:
            return jsonify({"error": "Grupo no encontrado"}), 404

        cursor.execute("""
            SELECT u.id, u.nombre, u.rol
            FROM grupo_miembros gm
            JOIN usuarios u ON gm.usuario_id = u.id
            WHERE gm.grupo_id = %s
        """, (grupo_id,))
        grupo["miembros"] = cursor.fetchall()

        return jsonify(grupo)
    finally:
        cursor.close(); conn.close()

# =====================================================
# ➕ Crear un nuevo grupo
# =====================================================
@bp_grupos.route("/api/grupos", methods=["POST"])
@login_required
@requiere_rol("director")
def crear_grupo():
    data = request.get_json(silent=True) or {}
    if not data: return jsonify({"error": "JSON inválido"}), 400

    nombre = data.get("nombre")
    descripcion = data.get("descripcion", "")
    color = data.get("color", "#00936B")
    miembros_raw = data.get("miembros", []) 

    if not nombre: return jsonify({"error": "Nombre obligatorio"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO grupos_profesionales (nombre, descripcion, color) VALUES (%s, %s, %s)", (nombre, descripcion, color))
        grupo_id = cursor.lastrowid

        ids_limpios = extraer_ids_limpios(miembros_raw)
        if ids_limpios:
            # 🔓 SIN RESTRICCIONES DE ROL
            ids_str = ','.join(str(uid) for uid in ids_limpios)
            cursor.execute(f"SELECT id FROM usuarios WHERE id IN ({ids_str})")
            usuarios_db = cursor.fetchall()
            
            values = [(grupo_id, u[0]) for u in usuarios_db]
            if values:
                cursor.executemany("INSERT INTO grupo_miembros (grupo_id, usuario_id) VALUES (%s, %s)", values)

        conn.commit()
        return jsonify({"message": "Grupo creado", "id": grupo_id}), 201
    except Exception as e:
        conn.rollback()
        print(f"❌ Error CREAR: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); conn.close()

# =====================================================
# 📝 Editar grupo
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>", methods=["PUT"])
@login_required
@requiere_rol("director")
def editar_grupo(grupo_id):
    data = request.get_json(silent=True) or {}
    if not data: return jsonify({"error": "JSON inválido"}), 400

    nombre = data.get("nombre")
    descripcion = data.get("descripcion")
    color = data.get("color")
    miembros_raw = data.get("miembros") 

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if nombre: cursor.execute("UPDATE grupos_profesionales SET nombre=%s WHERE id=%s", (nombre, grupo_id))
        if descripcion is not None: cursor.execute("UPDATE grupos_profesionales SET descripcion=%s WHERE id=%s", (descripcion, grupo_id))
        if color: cursor.execute("UPDATE grupos_profesionales SET color=%s WHERE id=%s", (color, grupo_id))

        if miembros_raw is not None:
            cursor.execute("DELETE FROM grupo_miembros WHERE grupo_id=%s", (grupo_id,))
            ids_limpios = extraer_ids_limpios(miembros_raw)
            
            if ids_limpios:
                # 🔓 SIN RESTRICCIONES DE ROL
                ids_str = ','.join(str(x) for x in ids_limpios)
                cursor.execute(f"SELECT id FROM usuarios WHERE id IN ({ids_str})")
                usuarios_db = cursor.fetchall()
                
                values = [(grupo_id, u[0]) for u in usuarios_db]
                if values:
                    cursor.executemany("INSERT INTO grupo_miembros (grupo_id, usuario_id) VALUES (%s, %s)", values)

        conn.commit()
        return jsonify({"message": "Grupo actualizado"})
    except Exception as e:
        conn.rollback()
        print(f"❌ Error EDITAR: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); conn.close()

# =====================================================
# ❌ Eliminar grupo
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>", methods=["DELETE"])
@login_required
@requiere_rol("director")
def eliminar_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM grupo_miembros WHERE grupo_id = %s", (grupo_id,))
        cursor.execute("DELETE FROM grupos_profesionales WHERE id = %s", (grupo_id,))
        conn.commit()
        return jsonify({"message": "Eliminado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); conn.close()

# =====================================================
# 👤 Agregar un miembro (Individual)
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>/miembros", methods=["POST"])
@login_required
@requiere_rol("director")
def agregar_miembro(grupo_id):
    data = request.get_json(silent=True) or {}
    usuario_id = data.get("usuario_id")
    if not usuario_id: return jsonify({"error": "Falta usuario_id"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 🔓 YA NO VERIFICAMOS EL ROL, SOLO QUE EXISTA
        cursor.execute("SELECT id FROM usuarios WHERE id = %s", (usuario_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        cursor.execute("""
            INSERT INTO grupo_miembros (grupo_id, usuario_id) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE usuario_id = usuario_id
        """, (grupo_id, usuario_id))
        
        conn.commit()
        return jsonify({"message": "Miembro agregado"}), 201
    except Exception as e:
        conn.rollback()
        print(f"❌ Error AGREGAR MIEMBRO: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); conn.close()

# =====================================================
# ❌ Quitar un miembro
# =====================================================
@bp_grupos.route("/api/grupos/<int:grupo_id>/miembros/<int:usuario_id>", methods=["DELETE"])
@login_required
@requiere_rol("director")
def quitar_miembro(grupo_id, usuario_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM grupo_miembros WHERE grupo_id = %s AND usuario_id = %s", (grupo_id, usuario_id))
        conn.commit()
        return jsonify({"message": "Miembro eliminado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); conn.close()

@bp_grupos.route("/api/grupos/<int:grupo_id>/miembros", methods=["GET"])
@login_required
def obtener_miembros(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.nombre, u.rol
        FROM grupo_miembros gm
        JOIN usuarios u ON gm.usuario_id = u.id
        WHERE gm.grupo_id = %s
    """, (grupo_id,))
    miembros = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(miembros)


@bp_grupos.route("/api/grupos/<int:grupo_id>/ausencias", methods=["GET"])
@login_required
def obtener_ausencias_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                a.id,
                a.usuario_id,
                u.nombre AS nombre_usuario,
                a.fecha_inicio,
                a.fecha_fin,
                a.motivo
            FROM grupo_miembros gm
            JOIN ausencias a ON a.usuario_id = gm.usuario_id
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE gm.grupo_id = %s
            ORDER BY a.fecha_inicio ASC
            """,
            (grupo_id,),
        )
        ausencias = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    for a in ausencias:
        a["fecha_inicio"] = _to_iso_arg(a.get("fecha_inicio"))
        a["fecha_fin"] = _to_iso_arg(a.get("fecha_fin"))

    return jsonify(ausencias)
