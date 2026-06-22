import smtplib

import mysql.connector
from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.config import Config
from app.utils.bfa_client import get_bfa_status


bp_health = Blueprint("bp_health", __name__, url_prefix="/api/health")


@bp_health.route("/public", methods=["GET"])
def public_health():
    return jsonify({"status": "ok"}), 200


@bp_health.route("/secure", methods=["GET"])
@login_required
def secure_health():
    if getattr(current_user, "rol", None) != "director":
        return jsonify({"error": "Acceso denegado"}), 403

    status = {
        "status": "ok",
        "database": "unknown",
        "bfa_node": "unknown",
        "mail": "unknown",
    }

    try:
        conn = mysql.connector.connect(
            host=Config.DB_CONFIG["host"],
            user=Config.DB_CONFIG["user"],
            password=Config.DB_CONFIG["password"],
            database=Config.DB_CONFIG["database"],
        )
        conn.close()
        status["database"] = "connected"
    except Exception as exc:
        status["database"] = f"error: {str(exc)}"
        status["status"] = "degraded"

    try:
        bfa_status = get_bfa_status()
        status["bfa_node_detail"] = bfa_status
        if bfa_status.get("connected"):
            status["bfa_node"] = "reachable"
        else:
            status["bfa_node"] = "no response"
            status["status"] = "degraded"
    except Exception as exc:
        status["bfa_node"] = f"error: {str(exc)}"
        status["status"] = "degraded"

    try:
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=3)
        if Config.MAIL_USE_TLS:
            server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.quit()
        status["mail"] = "ready"
    except Exception as exc:
        status["mail"] = f"error: {str(exc)}"
        status["status"] = "degraded"

    return jsonify(status), (200 if status["status"] == "ok" else 503)
