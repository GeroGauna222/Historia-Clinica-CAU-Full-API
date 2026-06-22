import hashlib
import json


def _normalizar_valor(valor):
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor

def generar_hash(contenido: str) -> str:
    """
    Genera un hash SHA-256 a partir de un string (UTF-8).
    Ignora valores None y limpia espacios.
    """
    if not contenido:
        contenido = ""
    return hashlib.sha256(contenido.strip().encode('utf-8')).hexdigest()


def generar_hash_json(data: dict) -> str:
    """
    Genera un hash SHA-256 estable para datos estructurados.
    """
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def payload_evolucion(evolucion: dict) -> dict:
    """
    Datos clinicos y de autoria que quedan sellados para una evolucion.
    """
    return {
        "id": evolucion.get("id"),
        "paciente_id": evolucion.get("paciente_id"),
        "fecha": _normalizar_valor(evolucion.get("fecha")),
        "contenido": evolucion.get("contenido") or "",
        "indicaciones": evolucion.get("indicaciones") or "",
        "usuario_id": evolucion.get("usuario_id"),
    }


def generar_hash_evolucion(evolucion: dict) -> str:
    return generar_hash_json(payload_evolucion(evolucion))


def validar_integridad(contenido: str, hash_guardado: str) -> bool:
    """
    Verifica si el contenido actual coincide con el hash almacenado.
    Retorna True si ambos hashes coinciden, False si difieren.
    """
    hash_actual = generar_hash(contenido)
    return hash_actual == hash_guardado
