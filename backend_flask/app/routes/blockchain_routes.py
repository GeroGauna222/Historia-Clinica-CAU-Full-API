import requests
from flask import Blueprint, current_app, jsonify
from flask_login import current_user, login_required

from app.database import get_connection
from app.utils.bfa_client import parse_permanent_rd, registrar_hash_en_bfa, verificar_hash_en_bfa
from app.utils.hashing import generar_hash, generar_hash_evolucion
from app.utils.permisos import requiere_rol


bp_blockchain = Blueprint("blockchain", __name__)


def _verificar_en_tsa(hash_local, rd):
    """
    Consulta el estado de un sellado contra la TSA de BFA.

    Devuelve (resultado, error_red):
    - resultado: dict con `estado` ('verificado' | 'pendiente' | 'error'), `valido`
      (True | None | False; None = pendiente, todavia no se puede afirmar nada),
      `hash_bfa`, `block_number`, `attestation_time`, `permanent_rd` y `mensaje`.
    - error_red: str si hubo un problema de red contra la TSA; en ese caso
      `resultado` es None.

    IMPORTANTE: el estado `pendiente` NO es una alteracion. El batch de la TSA puede
    tardar minutos en subir a la blockchain; tratarlo como invalido daria un falso
    positivo de adulteracion sobre una historia intacta.
    """
    try:
        data = verificar_hash_en_bfa(hash_local, rd)
    except requests.RequestException as exc:
        return None, str(exc)

    status = data.get("status")
    if status == "success":
        info = parse_permanent_rd(data.get("permanent_rd"))
        return {
            "estado": "verificado",
            "valido": True,
            "hash_bfa": info.get("file_hash") or hash_local,
            "block_number": info.get("block_number"),
            "attestation_time": data.get("attestation_time"),
            "permanent_rd": data.get("permanent_rd"),
            "mensaje": "Integridad verificada en blockchain",
        }, None

    if status == "pending":
        return {
            "estado": "pendiente",
            "valido": None,
            "hash_bfa": None,
            "block_number": None,
            "attestation_time": None,
            "permanent_rd": None,
            "mensaje": data.get("messages") or "Sellado pendiente de confirmacion en blockchain",
        }, None

    return {
        "estado": "error",
        "valido": False,
        "hash_bfa": None,
        "block_number": None,
        "attestation_time": None,
        "permanent_rd": None,
        "mensaje": data.get("messages") or "El hash no coincide con el sellado en BFA",
    }, None


def _fetch_historia_by_id_or_paciente(cursor, historia_id):
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
    if historia:
        return historia

    cursor.execute(
        """
        SELECT *
        FROM historias
        WHERE paciente_id = %s
        ORDER BY fecha DESC
        LIMIT 1
        """,
        (historia_id,),
    )
    return cursor.fetchone()


def _fetch_evolucion(cursor, evolucion_id):
    cursor.execute("SELECT * FROM evoluciones WHERE id = %s", (evolucion_id,))
    return cursor.fetchone()


def _marcar_historia_bfa(cursor, historia_id, hash_local, tx_hash, estado):
    cursor.execute(
        """
        UPDATE historias
        SET hash_local = %s,
            tx_hash = %s,
            fecha_anclaje_bfa = IF(%s = 'anclado', NOW(), fecha_anclaje_bfa),
            estado_bfa = %s,
            fecha = NOW()
        WHERE id = %s
        """,
        (hash_local, tx_hash, estado, estado, historia_id),
    )


def _marcar_evolucion_bfa(cursor, evolucion_id, hash_local, tx_hash, estado):
    cursor.execute(
        """
        UPDATE evoluciones
        SET hash_local = %s,
            tx_hash = %s,
            fecha_anclaje_bfa = IF(%s = 'anclado', NOW(), fecha_anclaje_bfa),
            estado_bfa = %s
        WHERE id = %s
        """,
        (hash_local, tx_hash, estado, estado, evolucion_id),
    )


@bp_blockchain.route("/api/blockchain/registrar/<int:historia_id>", methods=["POST"])
@login_required
def registrar_en_bfa(historia_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    historia = _fetch_historia_by_id_or_paciente(cursor, historia_id)

    if not historia:
        cursor.close()
        conn.close()
        return jsonify({"error": "Historia no encontrada"}), 404

    historia_id = historia["id"]
    hash_local = generar_hash(historia.get("resumen") or "")

    try:
        rd = registrar_hash_en_bfa(hash_local)
    except Exception as exc:
        cursor.close()
        conn.close()
        return jsonify({"error": f"No se pudo sellar en la BFA: {str(exc)}"}), 500

    _marcar_historia_bfa(cursor, historia_id, hash_local, rd, "anclado")
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "historia_id": historia_id,
        "hash": hash_local,
        "tx_hash": rd,
        "estado_bfa": "anclado",
        "mensaje": "Hash sellado correctamente en la TSA de BFA",
    }), 201


@bp_blockchain.route("/api/blockchain/registrar/evolucion/<int:evolucion_id>", methods=["POST"])
@login_required
def registrar_evolucion_en_bfa(evolucion_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    evolucion = _fetch_evolucion(cursor, evolucion_id)

    if not evolucion:
        cursor.close()
        conn.close()
        return jsonify({"error": "Evolucion no encontrada"}), 404

    hash_local = generar_hash_evolucion(evolucion)

    try:
        rd = registrar_hash_en_bfa(hash_local)
    except Exception as exc:
        _marcar_evolucion_bfa(cursor, evolucion_id, hash_local, evolucion.get("tx_hash"), "error")
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"error": f"No se pudo sellar en la BFA: {str(exc)}"}), 500

    _marcar_evolucion_bfa(cursor, evolucion_id, hash_local, rd, "anclado")
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "evolucion_id": evolucion_id,
        "hash": hash_local,
        "tx_hash": rd,
        "estado_bfa": "anclado",
        "mensaje": "Hash de evolucion sellado correctamente en la TSA de BFA",
    }), 201


@bp_blockchain.route("/api/blockchain/verificar/<int:historia_id>", methods=["GET"])
@login_required
def verificar_historia(historia_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    if not historia:
        return jsonify({"error": "Historia no encontrada"}), 404
    if not historia.get("tx_hash"):
        return jsonify({"error": "La historia no tiene sellado registrado en BFA"}), 400

    hash_local = generar_hash(historia.get("resumen") or "")
    resultado, error_red = _verificar_en_tsa(hash_local, historia["tx_hash"])
    if error_red:
        return jsonify({"error": f"No se pudo verificar en la TSA: {error_red}"}), 500

    if resultado["estado"] == "pendiente":
        return jsonify({
            "historia_id": historia_id,
            "hash_local": hash_local,
            "tx_hash": historia["tx_hash"],
            "valido": None,
            "estado_bfa": "pendiente",
            "mensaje": resultado["mensaje"],
        })

    valido = resultado["valido"]
    _registrar_auditoria(
        historia_id,
        hash_local,
        resultado["permanent_rd"],
        valido,
        current_user.username,
        tx_hash=historia["tx_hash"],
    )
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    _marcar_historia_bfa(cursor, historia_id, hash_local, historia["tx_hash"], resultado["estado"])
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "historia_id": historia_id,
        "hash_local": hash_local,
        "hash_bfa": resultado["hash_bfa"],
        "tx_hash": historia["tx_hash"],
        "block_number": resultado["block_number"],
        "attestation_time": resultado["attestation_time"],
        "valido": valido,
        "estado_bfa": resultado["estado"],
        "mensaje": resultado["mensaje"],
    })


@bp_blockchain.route("/api/blockchain/auditorias", methods=["GET"])
@login_required
def listar_auditorias():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM auditorias_blockchain ORDER BY fecha DESC")
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(registros)


def _registrar_auditoria(
    historia_id,
    hash_local,
    hash_bfa,
    valido,
    usuario,
    entidad_tipo="historia",
    entidad_id=None,
    evolucion_id=None,
    tx_hash=None,
):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        if historia_id:
            cursor.execute("SELECT id FROM historias WHERE id = %s", (historia_id,))
            historia = cursor.fetchone()

            if not historia:
                cursor.execute(
                    "SELECT id FROM historias WHERE paciente_id = %s ORDER BY fecha DESC LIMIT 1",
                    (historia_id,),
                )
                historia = cursor.fetchone()
                if not historia:
                    historia_id = None
                else:
                    historia_id = historia["id"]

        cursor.execute(
            """
            INSERT INTO auditorias_blockchain (
                historia_id, evolucion_id, entidad_tipo, entidad_id,
                tx_hash, hash_local, hash_bfa, valido, usuario
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                historia_id,
                evolucion_id,
                entidad_tipo,
                entidad_id or historia_id or evolucion_id,
                tx_hash,
                hash_local,
                None if hash_bfa is None else str(hash_bfa),
                int(valido),
                usuario,
            ),
        )
        conn.commit()
    except Exception:
        current_app.logger.exception("Error al registrar auditoria blockchain")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp_blockchain.route("/api/blockchain/test_tx", methods=["GET"])
@login_required
@requiere_rol("director")
def test_tx():
    if not current_app.config.get("ENABLE_BLOCKCHAIN_TEST_ENDPOINTS", False):
        return jsonify({"error": "Endpoint deshabilitado"}), 404

    hash_local = generar_hash("Prueba de conexion Flask -> TSA BFA")
    try:
        rd = registrar_hash_en_bfa(hash_local)
    except Exception as exc:
        return jsonify({"estado": "error", "detalle": str(exc)}), 500

    return jsonify({
        "estado": "ok",
        "mensaje": "Hash sellado correctamente en la TSA de BFA",
        "hash_local": hash_local,
        "tx_hash": rd,
    }), 200


@bp_blockchain.route("/api/blockchain/verificar/historia/<int:paciente_id>", methods=["GET"])
@login_required
def verificar_historia_blockchain(paciente_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, hash_local, tx_hash, fecha
        FROM historias
        WHERE paciente_id = %s
        ORDER BY fecha DESC
        LIMIT 1
        """,
        (paciente_id,),
    )
    historia = cursor.fetchone()
    cursor.close()
    conn.close()

    if not historia:
        return jsonify({"error": "No existe historia consolidada para este paciente"}), 404
    if not historia.get("tx_hash"):
        return jsonify({"error": "La historia no tiene sellado registrado en BFA"}), 400

    resultado, error_red = _verificar_en_tsa(historia["hash_local"], historia["tx_hash"])
    if error_red:
        return jsonify({"error": f"No se pudo verificar en la TSA: {error_red}"}), 500

    if resultado["estado"] == "pendiente":
        return jsonify({
            "paciente_id": paciente_id,
            "hash_local": historia["hash_local"],
            "tx_hash": historia["tx_hash"],
            "valido": None,
            "estado_bfa": "pendiente",
            "mensaje": resultado["mensaje"],
            "fecha": str(historia["fecha"]),
        })

    valido = resultado["valido"]
    _registrar_auditoria(
        historia["id"],
        historia["hash_local"],
        resultado["permanent_rd"],
        valido,
        current_user.username,
        tx_hash=historia["tx_hash"],
    )

    return jsonify({
        "paciente_id": paciente_id,
        "hash_local": historia["hash_local"],
        "hash_bfa": resultado["hash_bfa"],
        "tx_hash": historia["tx_hash"],
        "block_number": resultado["block_number"],
        "attestation_time": resultado["attestation_time"],
        "valido": valido,
        "estado_bfa": resultado["estado"],
        "mensaje": resultado["mensaje"],
        "fecha": str(historia["fecha"]),
    })


@bp_blockchain.route("/api/blockchain/verificar/evolucion/<int:evolucion_id>", methods=["GET"])
@login_required
def verificar_evolucion_blockchain(evolucion_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM evoluciones WHERE id = %s", (evolucion_id,))
    evolucion = cursor.fetchone()

    if not evolucion:
        cursor.close()
        conn.close()
        return jsonify({"error": "Evolucion no encontrada"}), 404

    tx_hash = evolucion.get("tx_hash")
    if not tx_hash:
        cursor.close()
        conn.close()
        return jsonify({"error": "La evolucion no tiene sellado registrado en BFA"}), 400

    hash_local = generar_hash_evolucion(evolucion)

    resultado, error_red = _verificar_en_tsa(hash_local, tx_hash)
    if error_red:
        cursor.close()
        conn.close()
        return jsonify({"error": f"No se pudo verificar en la TSA: {error_red}"}), 500

    if resultado["estado"] == "pendiente":
        cursor.close()
        conn.close()
        return jsonify({
            "evolucion_id": evolucion_id,
            "hash_local": hash_local,
            "tx_hash": tx_hash,
            "valido": None,
            "estado_bfa": "pendiente",
            "mensaje": resultado["mensaje"],
        })

    valido = resultado["valido"]
    cursor.execute(
        "SELECT id FROM historias WHERE paciente_id = %s ORDER BY fecha DESC LIMIT 1",
        (evolucion["paciente_id"],),
    )
    historia = cursor.fetchone()
    historia_id = historia["id"] if historia else None
    _marcar_evolucion_bfa(cursor, evolucion_id, hash_local, tx_hash, resultado["estado"])
    conn.commit()
    cursor.close()
    conn.close()

    _registrar_auditoria(
        historia_id,
        hash_local,
        resultado["permanent_rd"],
        valido,
        current_user.username,
        entidad_tipo="evolucion",
        entidad_id=evolucion_id,
        evolucion_id=evolucion_id,
        tx_hash=tx_hash,
    )

    return jsonify({
        "evolucion_id": evolucion_id,
        "hash_local": hash_local,
        "hash_bfa": resultado["hash_bfa"],
        "tx_hash": tx_hash,
        "block_number": resultado["block_number"],
        "attestation_time": resultado["attestation_time"],
        "valido": valido,
        "estado_bfa": resultado["estado"],
        "mensaje": resultado["mensaje"],
    })


@bp_blockchain.route("/api/blockchain/auditorias/<int:paciente_id>", methods=["GET"])
@login_required
def listar_auditorias_paciente(paciente_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT a.*, h.paciente_id
        FROM auditorias_blockchain a
        JOIN historias h ON a.historia_id = h.id
        WHERE h.paciente_id = %s
        ORDER BY a.fecha DESC
        """,
        (paciente_id,),
    )
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(registros)
