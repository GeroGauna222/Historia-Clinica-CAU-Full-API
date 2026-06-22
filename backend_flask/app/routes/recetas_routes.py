from datetime import datetime
import json
from urllib.parse import quote

import requests
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.database import get_connection
from app.utils.permisos import requiere_rol


bp_recetas = Blueprint("recetas", __name__, url_prefix="/api/recetas")
DEFAULT_DIAGNOSTICO_CODIGO = "Z769"
DEFAULT_DIAGNOSTICO_TEXTO = "Z76.9 - Persona en contacto con los servicios de salud en circunstancias no especificadas"
DEFAULT_OBSERVACION = "Tratamiento prolongado"
RECETA_ENDPOINT = "/apirecipe/Receta"
PRACTICA_ENDPOINT = "/apirecipe/prescribirPractica"

CAU_LUGAR_ATENCION = {
    "nombreConsultorio": "CAU UNSAM",
    "email": "cau@unsam.edu.ar",
    "domicilio": {
        "calle": "Av. 25 de Mayo",
        "numero": "1169",
        "direccion": "Av. 25 de Mayo 1169",
        "pais": "Argentina",
    },
}


def _recipe_config():
    token = current_app.config.get("QBITOS_RECIPE_TOKEN")
    client_app_id = current_app.config.get("QBITOS_RECIPE_CLIENT_APP_ID")
    if not token or not client_app_id:
        return None, jsonify({"error": "Integracion Qbitos Recipe no configurada"}), 503

    return {
        "base_url": current_app.config["QBITOS_RECIPE_BASE_URL"],
        "token": token,
        "client_app_id": client_app_id,
        "timeout": current_app.config["QBITOS_RECIPE_TIMEOUT"],
    }, None, None


def _headers(config):
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {config['token']}",
    }


def _qbitos_request(method, path, *, params=None, json_body=None):
    config, error_response, status = _recipe_config()
    if error_response:
        return None, error_response, status

    try:
        response = requests.request(
            method,
            f"{config['base_url']}{path}",
            headers=_headers(config),
            params=params,
            json=json_body,
            timeout=config["timeout"],
        )
    except requests.RequestException as exc:
        current_app.logger.exception("Error conectando con Qbitos Recipe")
        return None, jsonify({"error": "No se pudo conectar con Qbitos Recipe", "detail": str(exc)}), 502

    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}

    if response.status_code >= 400:
        return None, jsonify({"error": "Qbitos Recipe rechazo la solicitud", "status": response.status_code, "detail": payload}), response.status_code

    return payload, None, None


def _sexo_qbitos(sexo):
    mapa = {"masculino": "M", "femenino": "F", "otro": "X", "m": "M", "f": "F", "x": "X", "o": "O"}
    return mapa.get((sexo or "").strip().lower(), "X")


def _remove_empty(value):
    if isinstance(value, dict):
        return {k: _remove_empty(v) for k, v in value.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [_remove_empty(item) for item in value if item not in (None, "", [], {})]
    return value


def _split_nombre(nombre_completo):
    partes = (nombre_completo or "").strip().split()
    if len(partes) <= 1:
        return partes[0] if partes else "", ""
    return " ".join(partes[:-1]), partes[-1]


def _fetch_usuario(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario or {}


def _build_medico(usuario):
    nombre_default, apellido_default = _split_nombre(usuario.get("nombre"))
    especialidad = usuario.get("especialidad")
    return {
        "apellido": apellido_default,
        "nombre": nombre_default,
        "tipoDoc": "DNI",
        "nroDoc": usuario.get("dni"),
        "sexo": usuario.get("sexo") or "X",
        "especialidad": especialidad,
        "email": usuario.get("email"),
        "telefono": usuario.get("telefono"),
        "matricula": {
            "tipo": usuario.get("matricula_tipo") or "MN",
            "numero": usuario.get("matricula_numero"),
            "provincia": usuario.get("matricula_provincia"),
            "especialidad": especialidad,
        },
    }


def _diagnostico(data):
    codigo = (data.get("codigoDiagnostico") or data.get("codigo_diagnostico") or DEFAULT_DIAGNOSTICO_CODIGO).strip()
    texto = (data.get("diagnostico") or DEFAULT_DIAGNOSTICO_TEXTO).strip()
    return codigo, texto


def _observaciones(data):
    return (data.get("observaciones") or DEFAULT_OBSERVACION).strip()


def _build_common_payload(data, paciente, usuario, client_app_id):
    cobertura = data.get("cobertura") or {}
    return _remove_empty({
        "clienteAppId": client_app_id,
        "paciente": {
            "apellido": paciente.get("apellido"),
            "nombre": paciente.get("nombre"),
            "tipoDoc": data.get("paciente_tipo_doc") or "DNI",
            "nroDoc": paciente.get("dni"),
            "sexo": _sexo_qbitos(paciente.get("sexo")),
            "fechaNacimiento": paciente.get("fecha_nacimiento"),
            "email": paciente.get("email"),
            "telefono": paciente.get("celular") or paciente.get("telefono"),
            "cobertura": {
                "idFinanciador": cobertura.get("idFinanciador"),
                "plan": cobertura.get("plan"),
                "planId": cobertura.get("planId"),
                "numero": cobertura.get("numero"),
                "dniTitular": cobertura.get("dniTitular"),
            },
            "domicilio": {
                "direccion": paciente.get("direccion"),
                "codigoPostal": paciente.get("codigo_postal"),
                "provincia": data.get("paciente_provincia"),
                "pais": "Argentina",
            },
        },
        "medico": _build_medico(usuario),
        "lugarAtencion": CAU_LUGAR_ATENCION,
    })


def _build_receta_payload(data, paciente, usuario, client_app_id):
    codigo_diagnostico, diagnostico = _diagnostico(data)
    payload = _build_common_payload(data, paciente, usuario, client_app_id)
    payload.update({
        "medicamentos": data.get("medicamentos") or [],
        "diagnostico": diagnostico,
        "codigoDiagnostico": codigo_diagnostico,
        "indicaciones": data.get("indicaciones"),
        "observaciones": _observaciones(data),
        "imprimirDiagnostico": data.get("imprimirDiagnostico") or "S",
    })
    return _remove_empty(payload)


def _build_practica_payload(data, paciente, usuario, client_app_id, estudio):
    payload = _build_common_payload(data, paciente, usuario, client_app_id)
    codigo_diagnostico = (estudio.get("codigoDiagnostico") or estudio.get("codigo_diagnostico") or data.get("codigoDiagnostico") or DEFAULT_DIAGNOSTICO_CODIGO).strip()
    diagnostico = (estudio.get("diagnostico") or data.get("diagnostico") or DEFAULT_DIAGNOSTICO_TEXTO).strip()
    observaciones = (estudio.get("observaciones") or data.get("observaciones") or DEFAULT_OBSERVACION).strip()
    payload.update({
        "prescripcion": [{
            "nombre": (estudio.get("texto") or estudio.get("nombre") or "").strip(),
            "diagnostico": diagnostico,
            "codigoDiagnostico": codigo_diagnostico,
            "observaciones": observaciones,
        }],
        "diagnostico": diagnostico,
        "codigoDiagnostico": codigo_diagnostico,
        "indicaciones": data.get("indicaciones"),
        "observaciones": observaciones,
        "imprimirDiagnostico": data.get("imprimirDiagnostico") or "S",
    })
    return _remove_empty(payload)


def _validate_medicamentos(medicamentos):
    if not medicamentos:
        return "Agregue al menos un medicamento."
    if len(medicamentos) > 3:
        return "Cada receta admite como maximo 3 medicamentos distintos."
    for index, medicamento in enumerate(medicamentos, start=1):
        try:
            cantidad = int(medicamento.get("cantidad") or 0)
        except (TypeError, ValueError):
            return f"La cantidad del medicamento {index} debe ser numerica."
        if cantidad < 1 or cantidad > 2:
            return f"La cantidad del medicamento {index} debe estar entre 1 y 2."
        if not (medicamento.get("regNo") or medicamento.get("nombreProducto")):
            return f"Complete el medicamento {index}."
    return None


def _validate_estudios(estudios):
    if not estudios:
        return "Agregue al menos un estudio."
    for index, estudio in enumerate(estudios, start=1):
        if not (estudio.get("texto") or estudio.get("nombre") or "").strip():
            return f"Complete el texto libre del estudio {index}."
    return None


def _validate_payload(payload):
    medico = payload.get("medico") or {}
    matricula = medico.get("matricula") or {}
    if not medico.get("nombre") or not medico.get("apellido") or not medico.get("nroDoc"):
        return "Complete nombre, apellido y DNI del profesional en el usuario."
    if not matricula.get("numero"):
        return "Complete la matricula del profesional en el usuario."

    lugar_direccion = payload.get("lugarAtencion", {}).get("domicilio", {}).get("direccion")
    if not lugar_direccion:
        return "Complete la direccion del lugar de atencion del profesional."
    return None


def _fetch_paciente(paciente_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    cursor.close()
    conn.close()

    fecha_nacimiento = paciente.get("fecha_nacimiento") if paciente else None
    if fecha_nacimiento and hasattr(fecha_nacimiento, "strftime"):
        paciente["fecha_nacimiento"] = fecha_nacimiento.strftime("%Y-%m-%d")
    return paciente


def _extract_receta_response(qbitos_response):
    recetas = qbitos_response.get("recetas") or []
    primera = recetas[0] if recetas else {}
    response = qbitos_response.get("response") or []
    estado = (response[0] or {}).get("status") if response else "emitida"
    return primera, estado


def _store_receta(paciente_id, request_payload, qbitos_response, *, tipo="receta", qbitos_endpoint=RECETA_ENDPOINT):
    primera, estado = _extract_receta_response(qbitos_response)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recetas_electronicas (
            paciente_id, usuario_id, tipo, qbitos_endpoint, qbitos_id_receta, qbitos_s3_link, qbitos_verificador,
            id_transaccion, estado, afiliado_numero, request_json, response_json,
            creado_en, actualizado_en
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            paciente_id,
            current_user.id,
            tipo,
            qbitos_endpoint,
            primera.get("idReceta") or primera.get("id"),
            primera.get("s3Link"),
            primera.get("verificador"),
            qbitos_response.get("idTransaccion"),
            estado,
            request_payload.get("paciente", {}).get("cobertura", {}).get("numero"),
            json.dumps(request_payload, ensure_ascii=False),
            json.dumps(qbitos_response, ensure_ascii=False),
            datetime.utcnow(),
            datetime.utcnow(),
        ),
    )
    conn.commit()
    receta_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return receta_id


@bp_recetas.get("/config")
@login_required
def config_recetas():
    config, error_response, status = _recipe_config()
    if error_response:
        return error_response, status
    return jsonify({"configured": True, "clientAppId": config["client_app_id"], "baseUrl": config["base_url"]})


@bp_recetas.get("/financiadores")
@login_required
def listar_financiadores():
    payload, error_response, status = _qbitos_request("GET", "/apirecipe/GetFinanciadores")
    if error_response:
        return error_response, status
    return jsonify(payload)


@bp_recetas.get("/medicamentos")
@login_required
def buscar_medicamentos():
    texto = (request.args.get("q") or "").strip()
    if len(texto) < 2:
        return jsonify({"error": "Ingrese al menos 2 caracteres"}), 400

    config, error_response, status = _recipe_config()
    if error_response:
        return error_response, status

    params = {"clienteAppId": config["client_app_id"], "numeroPagina": request.args.get("numeroPagina", 1)}
    for key in ("idFinanciador", "afiliadoDni", "afiliadoCredencial", "planid", "plan"):
        if request.args.get(key):
            params[key] = request.args.get(key)

    payload, error_response, status = _qbitos_request("GET", f"/apirecipe/GetMedicamento/{quote(texto)}", params=params)
    if error_response:
        return error_response, status
    return jsonify(payload)


@bp_recetas.get("/diagnosticos")
@login_required
def buscar_diagnosticos():
    texto = (request.args.get("q") or "").strip()
    if len(texto) < 3:
        return jsonify({"error": "Ingrese al menos 3 caracteres"}), 400

    config, error_response, status = _recipe_config()
    if error_response:
        return error_response, status

    payload, error_response, status = _qbitos_request(
        "GET",
        "/apirecipe/GetDiagnostico",
        params={"text": texto, "clienteAppId": config["client_app_id"]},
    )
    if error_response:
        return error_response, status
    return jsonify(payload)


@bp_recetas.post("")
@login_required
@requiere_rol("director", "profesional")
def emitir_receta():
    data = request.get_json(silent=True) or {}
    tipo = (data.get("tipo") or "receta").strip().lower()
    paciente_id = data.get("paciente_id")
    if not paciente_id:
        return jsonify({"error": "paciente_id es obligatorio"}), 400
    if tipo not in {"receta", "estudio"}:
        return jsonify({"error": "tipo debe ser receta o estudio"}), 400

    paciente = _fetch_paciente(paciente_id)
    if not paciente:
        return jsonify({"error": "Paciente no encontrado"}), 404

    config, error_response, status = _recipe_config()
    if error_response:
        return error_response, status

    usuario = _fetch_usuario(current_user.id)
    if tipo == "receta":
        medicamentos = data.get("medicamentos") or []
        validation_error = _validate_medicamentos(medicamentos)
        if validation_error:
            return jsonify({"error": validation_error}), 400

        payload = _build_receta_payload(data, paciente, usuario, config["client_app_id"])
        validation_error = _validate_payload(payload)
        if validation_error:
            return jsonify({"error": validation_error}), 400

        response_payload, error_response, status = _qbitos_request("POST", RECETA_ENDPOINT, json_body=payload)
        if error_response:
            return error_response, status

        local_id = _store_receta(paciente_id, payload, response_payload, tipo="receta", qbitos_endpoint=RECETA_ENDPOINT)
        return jsonify({"message": "Receta emitida correctamente", "id": local_id, "qbitos": response_payload})

    estudios = data.get("estudios") or []
    validation_error = _validate_estudios(estudios)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    resultados = []
    for index, estudio in enumerate(estudios):
        payload = _build_practica_payload(data, paciente, usuario, config["client_app_id"], estudio)
        validation_error = _validate_payload(payload)
        if validation_error:
            return jsonify({"error": validation_error, "estudioIndex": index}), 400

        response_payload, error_response, status = _qbitos_request("POST", PRACTICA_ENDPOINT, json_body=payload)
        if error_response:
            return error_response, status

        local_id = _store_receta(paciente_id, payload, response_payload, tipo="estudio", qbitos_endpoint=PRACTICA_ENDPOINT)
        resultados.append({"id": local_id, "qbitos": response_payload, "estudioIndex": index})

    return jsonify({"message": "Estudios emitidos correctamente", "resultados": resultados})
