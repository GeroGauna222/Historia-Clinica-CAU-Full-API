from flask import Blueprint, request, jsonify, session, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import Usuario
from werkzeug.security import generate_password_hash
import secrets
from app import mail
from flask_mail import Message
from app.database import get_connection
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.utils.validacion import password_valida, validar_email

bp_auth = Blueprint("auth", __name__)

def get_serializer():
    return URLSafeTimedSerializer(current_app.secret_key)

# =====================================================
# 1️⃣ LOGIN
# =====================================================
@bp_auth.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    # validación mínima
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña son obligatorios'}), 400

    user = Usuario.obtener_por_username(username)

    if user and user.verificar_password(password):
        login_user(user)
        session.permanent = True
        return jsonify({
            'message': 'Login exitoso ✅',
            'user': {
                'id': user.id,
                'nombre': user.nombre,
                'username': user.username,
                'email': user.email,
                'rol': user.rol
            }
        })
    return jsonify({'error': 'Credenciales incorrectas ❌'}), 401


# =====================================================
# 2️⃣ LOGOUT
# =====================================================
@bp_auth.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'message': 'Logout exitoso ✅'})


# =====================================================
# 3️⃣ USUARIO LOGUEADO
# =====================================================
@bp_auth.route('/api/user', methods=['GET'])
@login_required
def api_user():
    return jsonify({
        "id": current_user.id,
        "nombre": current_user.nombre,
        "username": current_user.username,
        "email": current_user.email,
        "rol": current_user.rol,
        "duracion_turno": current_user.duracion_turno,
        "foto": current_user.foto
    })


# =====================================================
# 4️⃣ ENVIAR ENLACE DE RECUPERACIÓN
# =====================================================
@bp_auth.route('/api/recover', methods=['POST'])
def api_recover():
    s = get_serializer()
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    generic_msg = 'Si el correo existe, se envio un enlace para restablecer la contrasena.'

    if not validar_email(email):
        return jsonify({'error': 'Email inválido'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    if usuario:
        token = s.dumps(email, salt='reset-password')
        reset_url = f"{current_app.config['FRONTEND_URL']}/reset/{token}"
        msg = Message("Recuperación de contraseña - Historia Clínica CAU", recipients=[email])
        msg.body = (
            f"Hola {usuario['nombre']},\n\n"
            f"Para restablecer tu contraseña ingresá al siguiente enlace:\n\n"
            f"{reset_url}\n\n"
            f"Este enlace expira en 1 hora."
        )
        mail.send(msg)

    return jsonify({'message': generic_msg}), 200


# =====================================================
# 5️⃣ RESTABLECER CONTRASEÑA
# =====================================================
@bp_auth.route('/api/reset/<token>', methods=['POST'])
def api_reset_password(token):
    s = get_serializer()

    try:
        email = s.loads(token, salt='reset-password', max_age=3600)
    except SignatureExpired:
        return jsonify({'error': 'El enlace expiró'}), 400
    except BadSignature:
        return jsonify({'error': 'Token inválido'}), 400

    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not new_password or not confirm_password:
        return jsonify({'error': 'Debes completar ambos campos'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    #  Validar contraseña fuerte
    if not password_valida(new_password):
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres y contener mayúscula, minúscula, número y símbolo.'}), 400

    #  Hash seguro
    password_hash = generate_password_hash(new_password, method="scrypt")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET password_hash = %s WHERE email = %s", (password_hash, email))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Contraseña actualizada correctamente ✅'}), 200
