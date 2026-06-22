from flask_login import UserMixin
from werkzeug.security import check_password_hash
from .database import get_connection

class Usuario(UserMixin):
    def __init__(self, id, nombre, username, email, password_hash, rol, duracion_turno, foto=None, **extra):
        self.id = id
        self.nombre = nombre
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.rol = rol
        self.duracion_turno = duracion_turno
        self.foto = foto
        self.dni = extra.get("dni")
        self.sexo = extra.get("sexo")
        self.telefono = extra.get("telefono")
        self.especialidad = extra.get("especialidad")
        self.matricula_tipo = extra.get("matricula_tipo")
        self.matricula_numero = extra.get("matricula_numero")
        self.matricula_provincia = extra.get("matricula_provincia")
        self.lugar_atencion_nombre = extra.get("lugar_atencion_nombre")
        self.lugar_atencion_direccion = extra.get("lugar_atencion_direccion")
        self.lugar_atencion_contacto = extra.get("lugar_atencion_contacto")
        self.lugar_atencion_email = extra.get("lugar_atencion_email")

    @staticmethod
    def obtener_por_username(username):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM usuarios WHERE username = %s AND activo = 1",
            (username,)
        )
        data = cursor.fetchone()
        conn.close()

        if data:
            return Usuario(
                id=data['id'],
                nombre=data['nombre'],
                username=data['username'],
                email=data['email'],                
                password_hash=data['password_hash'],
                rol=data['rol'],
                duracion_turno=data.get('duracion_turno'),
                foto=data.get('foto'),
                dni=data.get("dni"),
                sexo=data.get("sexo"),
                telefono=data.get("telefono"),
                especialidad=data.get("especialidad"),
                matricula_tipo=data.get("matricula_tipo"),
                matricula_numero=data.get("matricula_numero"),
                matricula_provincia=data.get("matricula_provincia"),
                lugar_atencion_nombre=data.get("lugar_atencion_nombre"),
                lugar_atencion_direccion=data.get("lugar_atencion_direccion"),
                lugar_atencion_contacto=data.get("lugar_atencion_contacto"),
                lugar_atencion_email=data.get("lugar_atencion_email")
            )
        return None

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)
