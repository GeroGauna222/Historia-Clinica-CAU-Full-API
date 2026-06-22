import os
import base64

import requests


# La integridad se ancla en BFA usando su API oficial de Timestamp Authority (TSA),
# en lugar de un nodo Geth local. No requiere web3 ni cuentas/keystore.
TSA_BASE_URL = os.getenv("BFA_TSA_URL", "https://tsaapi.bfa.ar/api/tsa").rstrip("/")
TIMEOUT = 30


def _normalize_hash(hash_hex):
    """Normaliza el hash a hex sin prefijo 0x. Sella exactamente el hash recibido."""
    if not isinstance(hash_hex, str):
        raise ValueError("hash_hex debe ser str")
    return hash_hex[2:] if hash_hex.startswith("0x") else hash_hex


def parse_permanent_rd(permanent_rd):
    """
    Decodifica el `permanent_rd` que devuelve la TSA tras verificar con exito.
    Formato (tras base64-decode): `1x-{file_hash}-{nonce}-{0xleaf}-{block_number}`.
    Devuelve dict con los campos utiles para auditoria; {} si no parsea.
    """
    if not permanent_rd:
        return {}
    try:
        raw = base64.b64decode(permanent_rd).decode("utf-8")
        parts = raw.split("-")
        if len(parts) < 5:
            return {}
        return {
            "file_hash": parts[1],
            "block_number": int(parts[-1]),
            "raw": raw,
        }
    except Exception:
        return {}


def registrar_hash_en_bfa(hash_hex):
    """
    Sella un hash SHA-256 en BFA usando la API oficial TSA.
    Devuelve el `temporary_rd` (recibo) que identifica el sellado; se persiste y
    luego se usa para verificar.
    """
    file_hash = _normalize_hash(hash_hex)
    resp = requests.post(
        f"{TSA_BASE_URL}/stamp/",
        json={"file_hash": file_hash},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError(f"TSA stamp rechazado: {data.get('messages')}")
    return data["temporary_rd"]


def verificar_hash_en_bfa(hash_hex, rd):
    """
    Consulta el estado de un sellado contra la TSA de BFA y devuelve el cuerpo de la
    respuesta tal cual, que tiene tres estados posibles:

    - status == "success": el hash esta confirmado en blockchain. Incluye
      `attestation_time` y `permanent_rd` (con el numero de bloque).
    - status == "pending": el sellado existe pero el batch aun no subio a la
      blockchain. NO significa alteracion; puede tardar minutos. Reintentar mas tarde.
    - status == "failure": el hash no coincide con lo sellado (posible alteracion) o
      el recibo es invalido.

    No se hace backoff bloqueante porque la confirmacion del batch puede tardar
    minutos: bloquear un worker de Flask no aporta. El caller decide como tratar el
    estado `pending`. Las excepciones de red (requests) se propagan.
    """
    if not rd:
        raise ValueError("rd requerido para verificar")
    file_hash = _normalize_hash(hash_hex)
    resp = requests.post(
        f"{TSA_BASE_URL}/verify/",
        json={"file_hash": file_hash, "rd": rd},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_bfa_status():
    """
    Chequeo de disponibilidad de la TSA para el endpoint de health.
    `connected` es True si la API responde (cualquier codigo HTTP).
    """
    status = {
        "tsa_url": TSA_BASE_URL,
        "connected": False,
        "status_code": None,
    }
    try:
        resp = requests.get(TSA_BASE_URL, timeout=5)
        status["connected"] = True
        status["status_code"] = resp.status_code
    except requests.RequestException as exc:
        status["error"] = str(exc)
    return status
