from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from app.utils.permisos import requiere_rol
from datetime import datetime, timedelta

bp_disponibilidades = Blueprint("disponibilidades", __name__)

# ==========================================================
# 📅 CRUD de Disponibilidades de los Médicos
# ==========================================================

DIAS_ORDENADOS = [
    "Lunes", "Martes", "Miercoles",
    "Jueves", "Viernes", "Sabado", "Domingo"
]
orden_sql = ",".join([f"'{d}'" for d in DIAS_ORDENADOS])


def normalizar_dia(dia):
    mapa = {
        "lunes": "Lunes",
        "martes": "Martes",
        "miercoles": "Miercoles",
        "miércoles": "Miercoles",
        "jueves": "Jueves",
        "viernes": "Viernes",
        "sabado": "Sabado",
        "sábado": "Sabado",
        "domingo": "Domingo"
    }
    if not dia:
        return None
    return mapa.get(dia.lower().strip())


# ==========================================================
# GET — Listar disponibilidades
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def listar_disponibilidades():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 👇 CAMBIO: 'area' se comporta como 'profesional' (ve solo lo suyo)
    if current_user.rol in ['profesional', 'area']:
        cursor.execute(f"""
            SELECT id, usuario_id, dia_semana, hora_inicio, hora_fin, activo
            FROM disponibilidades
            WHERE usuario_id = %s
            ORDER BY FIELD(dia_semana, {orden_sql})
        """, (current_user.id,))
    else:
        # Directores y administrativos ven las de todos
        # Agregamos filtro opcional por usuario_id si viene en la URL (?usuario_id=5)
        filtro_usuario = request.args.get('usuario_id')
        
        if filtro_usuario:
            cursor.execute(f"""
                SELECT d.id, d.usuario_id, u.nombre AS profesional,
                       d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
                FROM disponibilidades d
                JOIN usuarios u ON d.usuario_id = u.id
                WHERE d.usuario_id = %s
                ORDER BY u.nombre ASC, FIELD(d.dia_semana, {orden_sql})
            """, (filtro_usuario,))
        else:
            cursor.execute(f"""
                SELECT d.id, d.usuario_id, u.nombre AS profesional,
                       d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
                FROM disponibilidades d
                JOIN usuarios u ON d.usuario_id = u.id
                ORDER BY u.nombre ASC, FIELD(d.dia_semana, {orden_sql})
            """)

    disponibilidades = cursor.fetchall()
    cursor.close()
    conn.close()

    # 🟢 Normalizar resultados
    for d in disponibilidades:
        # Canonicalizar para mantener siempre el mismo formato
        d["dia_semana"] = normalizar_dia(d["dia_semana"]) or d["dia_semana"]

        # convertir TIME → string
        if isinstance(d.get("hora_inicio"), timedelta):
            d["hora_inicio"] = (datetime.min + d["hora_inicio"]).time().strftime("%H:%M")
        if isinstance(d.get("hora_fin"), timedelta):
            d["hora_fin"] = (datetime.min + d["hora_fin"]).time().strftime("%H:%M")

    return jsonify(disponibilidades)


# ==========================================================
# POST — Crear disponibilidad
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'area')
def crear_disponibilidad():

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    # Lógica para asignar usuario
    # Si es Director, permitimos que venga "usuario_id" en el JSON
    # Si es Profesional o Area, forzamos que sea su propio ID
    if current_user.rol in ['profesional', 'area']:
        usuario_id = current_user.id
    else:
        usuario_id = data.get("usuario_id") or current_user.id

    dia_semana = normalizar_dia(data.get("dia_semana", ""))
    hora_inicio = data.get("hora_inicio")
    hora_fin = data.get("hora_fin")
    activo = data.get("activo", True)

    if not dia_semana:
        return jsonify({"error": "Día inválido"}), 400
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            INSERT INTO disponibilidades (usuario_id, dia_semana, hora_inicio, hora_fin, activo)
            VALUES (%s, %s, %s, %s, %s)
        """, (usuario_id, dia_semana, hora_inicio, hora_fin, activo))

        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({"id": new_id, "message": "Disponibilidad creada correctamente"}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
        
    finally:
        cursor.close()
        conn.close()


# ==========================================================
# PUT — Actualizar disponibilidad (solo horas y activo)
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional', 'area')
def editar_disponibilidad(id):

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM disponibilidades WHERE id=%s", (id,))
    disp = cursor.fetchone()
    if not disp:
        cursor.close(); conn.close()
        return jsonify({"error": "Disponibilidad no encontrada"}), 404

    # Si es profesional/area, solo puede editar lo suyo. 
    # Si es director, puede editar lo de cualquiera.
    if current_user.rol in ['profesional', 'area'] and disp["usuario_id"] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    hora_inicio = data.get("hora_inicio")
    hora_fin = data.get("hora_fin")
    activo = data.get("activo")

    cursor.execute("""
        UPDATE disponibilidades
        SET hora_inicio=%s, hora_fin=%s, activo=%s
        WHERE id=%s
    """, (hora_inicio, hora_fin, activo, id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Disponibilidad actualizada correctamente"})


# ==========================================================
# DELETE
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional', 'area')
def eliminar_disponibilidad(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM disponibilidades WHERE id=%s", (id,))
    disp = cursor.fetchone()

    if not disp:
        cursor.close(); conn.close()
        return jsonify({"error": "Disponibilidad no encontrada"}), 404

    # Validación de permiso
    if current_user.rol in ['profesional', 'area'] and disp["usuario_id"] != current_user.id:
        cursor.close(); conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM disponibilidades WHERE id=%s", (id,))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({"message": "Disponibilidad eliminada correctamente"})
