"""Primitives for the electronic signature of clinical evolutions.

The signature implemented here is an electronic signature under Argentine law:
it binds an authenticated CAU account and verified professional registration to
the exact clinical payload that was accepted by the application. It is not a
cryptographic digital signature backed by a personal certificate authority.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta

from flask import request, session
from flask_login import current_user


PAYLOAD_VERSION = "evolucion-v1"
ARGENTINA_TZ = timezone(timedelta(hours=-3))


class FirmaElectronicaError(ValueError):
    """Expected validation failure while attempting to sign an evolution."""

    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def ahora_argentina_sin_tz():
    """Return a naive Argentina datetime suitable for MySQL DATETIME(6)."""
    return datetime.now(timezone.utc).astimezone(ARGENTINA_TZ).replace(tzinfo=None)


def validar_profesional_firmante(user=None):
    """Validate role, registration data and CAU's explicit verification flag."""
    user = user or current_user
    if getattr(user, "rol", None) not in ("director", "profesional"):
        raise FirmaElectronicaError(
            "Solo un director o profesional puede registrar una evolución clínica.",
            403,
        )

    required = {
        "matricula_tipo": getattr(user, "matricula_tipo", None),
        "matricula_numero": getattr(user, "matricula_numero", None),
    }
    missing = [name for name, value in required.items() if not str(value or "").strip()]
    if missing:
        raise FirmaElectronicaError(
            "La cuenta debe tener matrícula profesional cargada antes de firmar una evolución.",
            422,
        )

    verificada = getattr(user, "matricula_verificada", False)
    if not (verificada is True or verificada in (1, "1", "true", "True")):
        raise FirmaElectronicaError(
            "La matrícula profesional todavía no fue validada por CAU.",
            422,
        )


def require_confirmation():
    """Require the explicit UI confirmation that makes the signing intent clear."""
    confirmation = request.form.get("confirmar_firma")
    if confirmation is None and request.is_json:
        confirmation = (request.get_json(silent=True) or {}).get("confirmar_firma")
    if str(confirmation).strip().lower() not in ("1", "true", "si", "sí"):
        raise FirmaElectronicaError(
            "Debe confirmar expresamente la firma de la evolución antes de guardarla.",
            422,
        )


def auth_event_id():
    event_id = session.get("auth_event_id")
    if not event_id:
        raise FirmaElectronicaError(
            "La sesión no tiene un evento de autenticación válido. Inicie sesión nuevamente.",
            401,
        )
    return str(event_id)


def request_context():
    return {
        "ip": (request.remote_addr or "")[:45] or None,
        "user_agent": (request.user_agent.string or "")[:512] or None,
    }


def payload_evolucion_firmable(evolucion, user=None):
    user = user or current_user

    def user_value(name):
        return user.get(name) if isinstance(user, dict) else getattr(user, name, None)

    return {
        "payload_version": PAYLOAD_VERSION,
        "evolucion_id": evolucion.get("id"),
        "paciente_id": evolucion.get("paciente_id"),
        "fecha": _iso(evolucion.get("fecha")),
        "contenido": evolucion.get("contenido") or "",
        "indicaciones": evolucion.get("indicaciones") or "",
        "usuario_id": evolucion.get("usuario_id"),
        "rol": user_value("rol"),
        "matricula_tipo": user_value("matricula_tipo"),
        "matricula_numero": user_value("matricula_numero"),
        "matricula_provincia": user_value("matricula_provincia"),
        "version": evolucion.get("version", 1),
        "padre_id": evolucion.get("padre_id"),
        "motivo_rectificacion": evolucion.get("motivo_rectificacion") or None,
    }


def hash_payload(payload):
    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def nuevo_id_evento_autenticacion():
    """Generate an opaque identifier for a persisted authentication event."""
    return str(uuid.uuid4())


def registrar_firma_y_auditoria(cursor, evolucion, accion, user=None):
    """Insert the immutable signature and its clinical audit record.

    The caller owns the surrounding transaction. No commit is performed here,
    so the evolution, attachments, signature and audit row succeed or fail as
    one unit.
    """
    user = user or current_user
    validar_profesional_firmante(user)
    evento_id = auth_event_id()
    firmado_en = ahora_argentina_sin_tz()
    contexto = request_context()
    payload = payload_evolucion_firmable(evolucion, user)
    payload_hash = hash_payload(payload)

    cursor.execute(
        """
        INSERT INTO firmas_electronicas (
            evolucion_id, usuario_id, autenticacion_evento_id, rol,
            matricula_tipo, matricula_numero, matricula_provincia, tipo,
            algoritmo, payload_version, payload_hash, firmado_en, ip, user_agent
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'electronica', 'SHA-256', %s, %s, %s, %s, %s)
        """,
        (
            evolucion["id"],
            user.id,
            evento_id,
            user.rol,
            user.matricula_tipo,
            user.matricula_numero,
            user.matricula_provincia,
            PAYLOAD_VERSION,
            payload_hash,
            firmado_en,
            contexto["ip"],
            contexto["user_agent"],
        ),
    )
    cursor.execute(
        """
        INSERT INTO auditorias_clinicas
            (evolucion_id, usuario_id, accion, version, detalle_json, creado_en)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            evolucion["id"],
            user.id,
            accion,
            evolucion.get("version", 1),
            json.dumps(
                {
                    "payload_version": PAYLOAD_VERSION,
                    "payload_hash": payload_hash,
                    "autenticacion_evento_id": evento_id,
                    "motivo_rectificacion": evolucion.get("motivo_rectificacion") or None,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            firmado_en,
        ),
    )
    return payload_hash, firmado_en
