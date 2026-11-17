"""Lógica pura de la Pantalla de llamados (sin acceso a base de datos)."""
import hashlib
import secrets
from datetime import datetime

# Sin 0, O, 1, I, L (se confunden al leerlos en un televisor).
ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 6
MINUTOS_VIGENCIA_CODIGO = 10
MAX_CODIGOS_PENDIENTES = 20


def generar_codigo():
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LARGO_CODIGO))


def generar_clave():
    return secrets.token_urlsafe(32)


def hash_clave(clave):
    # La clave tiene 256 bits de entropía: SHA-256 alcanza (no es una contraseña elegida por una persona).
    return hashlib.sha256((clave or "").encode("utf-8")).hexdigest()


def cierre_grupal(fecha_inicio, fecha_fin, atencion_inicio):
    """Hora a la que se cierra sola la atención de un turno grupal."""
    if atencion_inicio <= fecha_fin:
        return fecha_fin
    return atencion_inicio + (fecha_fin - fecha_inicio)


def estado_atencion(turno, ahora):
    """'esperando' | 'en_atencion' | 'atendido' | None (si el paciente no está presente)."""
    if turno.get("estado_asistencia") != "presente":
        return None
    inicio = turno.get("atencion_inicio")
    if inicio is None:
        return "esperando"
    if turno.get("atencion_fin") is not None:
        return "atendido"
    if inicio.date() != ahora.date():
        return "atendido"
    if turno.get("es_grupal"):
        fecha_inicio, fecha_fin = turno.get("fecha_inicio"), turno.get("fecha_fin")
        if fecha_inicio and fecha_fin and ahora >= cierre_grupal(fecha_inicio, fecha_fin, inicio):
            return "atendido"
    return "en_atencion"


def ahora_de(rows):
    """Reloj de MySQL tomado de la columna `ahora_db` de la primera fila; si no hay, el del servidor web."""
    for row in rows or []:
        valor = row.get("ahora_db") if hasattr(row, "get") else None
        if valor:
            return valor
    return datetime.now()


def anotar_estado_atencion(rows, quitar_tiempos=False, grupal=None):
    """Agrega `estado_atencion` a cada fila (dict con datetimes). Quita `ahora_db`; con
    `quitar_tiempos` quita además `atencion_inicio`/`atencion_fin` (para respuestas JSON directas).
    `grupal`: si no es None, fuerza el tipo de todas las filas (sin necesitar la clave `es_grupal`);
    si es None se usa la clave `es_grupal` de cada fila."""
    ahora = ahora_de(rows)
    for row in rows or []:
        fuente = row if grupal is None else {**row, "es_grupal": 1 if grupal else 0}
        row["estado_atencion"] = estado_atencion(fuente, ahora)
        row.pop("ahora_db", None)
        if quitar_tiempos:
            row.pop("atencion_inicio", None)
            row.pop("atencion_fin", None)
    return rows


def _primera_palabra(texto):
    partes = (texto or "").split()
    return partes[0] if partes else ""


def _abreviado(nombre, apellido, letras):
    n = _primera_palabra(nombre).capitalize()
    a = _primera_palabra(apellido)
    if not a:
        return n or "Paciente"
    return f"{n} {a[:letras].capitalize()}.".strip()


def abreviar_pacientes(pacientes):
    """{paciente_id: Nombre abreviado}. Si dos pacientes distintos coinciden, suma una letra del apellido."""
    unicos = {p["id"]: p for p in pacientes}
    letras = {pid: 1 for pid in unicos}
    for _ in range(30):
        grupos = {}
        for pid, p in unicos.items():
            grupos.setdefault(_abreviado(p["nombre"], p["apellido"], letras[pid]), []).append(pid)
        avanzo = False
        for pids in grupos.values():
            if len(pids) < 2:
                continue
            for pid in pids:
                if letras[pid] < len(_primera_palabra(unicos[pid]["apellido"])):
                    letras[pid] += 1
                    avanzo = True
        if not avanzo:
            break
    return {pid: _abreviado(p["nombre"], p["apellido"], letras[pid]) for pid, p in unicos.items()}
