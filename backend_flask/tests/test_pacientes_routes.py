from conftest import FakeConnection, FakeCursor, MockUser, login_as
from app.routes import pacientes_routes
from mysql.connector import IntegrityError
import pytest


def test_proximo_nro_hc_sugiere_siguiente_numero(client, monkeypatch):
    fake_cursor = FakeCursor(fetchone_results=[{"max_hc": 2567}])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "administrativo"))

    response = client.get("/api/pacientes/proximo-nro-hc")

    assert response.status_code == 200
    assert response.get_json() == {"proximo_nro_hc": "2568"}


def test_proximo_nro_hc_default_uno_si_no_hay_pacientes(client, monkeypatch):
    fake_cursor = FakeCursor(fetchone_results=[{"max_hc": None}])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "administrativo"))

    response = client.get("/api/pacientes/proximo-nro-hc")

    assert response.status_code == 200
    assert response.get_json() == {"proximo_nro_hc": "1"}


def test_proximo_nro_hc_requiere_login(client):
    response = client.get("/api/pacientes/proximo-nro-hc")

    assert response.status_code in (302, 401)


def test_crear_paciente_permite_los_4_roles(client, monkeypatch):
    for rol in ("director", "profesional", "administrativo", "area"):
        fake_cursor = FakeCursor(fetchone_results=[None])
        monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
        login_as(client, MockUser(1, rol))

        response = client.post("/api/pacientes", data={"dni": "1", "nro_hc": "1"})

        assert response.status_code == 200, f"rol {rol} deberia poder crear pacientes"


def test_crear_paciente_deniega_rol_no_reconocido(client, monkeypatch):
    fake_cursor = FakeCursor(fetchone_results=[None])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(99, "invitado"))

    response = client.post("/api/pacientes", data={"dni": "1", "nro_hc": "1"})

    assert response.status_code == 403


def test_crear_paciente_nro_hc_duplicado_devuelve_400_no_500(client, monkeypatch):
    # DNI libre (fetchone #1 -> None) pero nro_hc ya existe (fetchone #2 -> row):
    # debe responder 400 con mensaje claro, no romper con 500 por la constraint UNIQUE.
    fake_cursor = FakeCursor(fetchone_results=[None, {"id": 7}])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "administrativo"))

    response = client.post("/api/pacientes", data={"dni": "44547652", "nro_hc": "2567"})

    assert response.status_code == 409
    assert "nro_hc" in response.get_json()["error"].lower() or "hc" in response.get_json()["error"].lower()


def test_eliminar_paciente_con_evoluciones_devuelve_400_no_500_y_hace_rollback(client, monkeypatch):
    # Reproduce el incidente real de prod: DELETE sobre un paciente que tiene
    # evoluciones/turnos/recetas asociadas choca con la FK (esas tablas no tienen
    # ON DELETE CASCADE). Sin manejo de la excepcion, la conexion queda abierta
    # con la transaccion sin rollback -> conexion "colgada" en MySQL indefinidamente.
    fake_cursor = FakeCursor(
        fetchone_results=[
            {"id": 2},  # SELECT id ... -> paciente existe
            None,  # no tiene documentos generales adjuntos
        ],
        execute_side_effects=[
            None,  # SELECT id FROM pacientes
            None,  # SELECT historia_archivos
            IntegrityError("Cannot delete or update a parent row: a foreign key constraint fails"),  # DELETE
        ],
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    login_as(client, MockUser(1, "director"))

    response = client.delete("/api/pacientes/2")

    assert response.status_code == 400
    assert "error" in response.get_json()
    assert fake_connection.rolled_back is True, "debe hacer rollback en vez de dejar la transaccion abierta"
    assert fake_cursor.closed is True
    assert fake_connection.closed is True, "la conexion debe cerrarse siempre, incluso con error"


def test_crear_paciente_error_db_generico_hace_rollback_y_cierra_recursos(client, monkeypatch):
    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        execute_side_effects=[
            None,
            None,
            RuntimeError("database insert failed"),
        ],
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", False)
    login_as(client, MockUser(1, "administrativo"))

    response = client.post("/api/pacientes", data={"dni": "44547652", "nro_hc": "2567"})

    assert response.status_code == 500
    assert fake_connection.rolled_back is True, "debe hacer rollback ante errores DB no IntegrityError"
    assert fake_cursor.closed is True
    assert fake_connection.closed is True, "la conexion debe cerrarse siempre, incluso con error"


def test_eliminar_paciente_con_documentos_adjuntos_no_borra_paciente(client, monkeypatch):
    fake_cursor = FakeCursor(fetchone_results=[{"id": 2}, {"id": 91}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    login_as(client, MockUser(1, "director"))

    response = client.delete("/api/pacientes/2")

    assert response.status_code == 400
    assert "documentos adjuntos" in response.get_json()["error"].lower()
    assert all("DELETE FROM pacientes" not in query for query, _ in fake_cursor.executed)
    assert fake_connection.committed is False


def test_crear_paciente_error_generico_en_precheck_hace_rollback_cierra_y_propaga(client, monkeypatch):
    fake_cursor = FakeCursor(
        execute_side_effects=[
            RuntimeError("database select failed"),
        ],
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", True)
    login_as(client, MockUser(1, "administrativo"))

    with pytest.raises(RuntimeError, match="database select failed"):
        client.post("/api/pacientes", data={"dni": "44547652", "nro_hc": "2567"})

    assert fake_connection.rolled_back is True, "debe hacer rollback si falla el precheck SELECT"
    assert fake_cursor.closed is True
    assert fake_connection.closed is True, "la conexion debe cerrarse siempre, incluso con error"


def test_crear_paciente_error_db_loguea_contexto_seguro_sin_payload_clinico(client, monkeypatch):
    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        execute_side_effects=[
            None,
            None,
            RuntimeError("database insert failed"),
        ],
    )
    fake_connection = FakeConnection(fake_cursor, connection_id=9876)
    log_calls = []

    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", False)
    monkeypatch.setattr(
        client.application.logger,
        "exception",
        lambda message, *args, **kwargs: log_calls.append((message, args, kwargs)),
    )
    login_as(client, MockUser(42, "administrativo"))

    response = client.post(
        "/api/pacientes",
        data={
            "dni": "44547652",
            "nro_hc": "2567",
            "apellido": "DatoClinico",
            "nombre": "Paciente",
            "diagnostico": "No debe loguearse",
        },
        headers={"X-Request-ID": "req-test-1"},
    )

    assert response.status_code == 500
    assert log_calls, "debe registrar contexto operativo del error"
    rendered_log = " ".join(str(part) for call in log_calls for part in (call[0], *call[1]))
    assert "api_crear_paciente" in rendered_log
    assert "POST" in rendered_log
    assert "42" in rendered_log
    assert "9876" in rendered_log
    assert "req-test-1" in rendered_log
    assert "44547652" not in rendered_log
    assert "DatoClinico" not in rendered_log
    assert "No debe loguearse" not in rendered_log


def test_modificar_paciente_error_db_hace_rollback_loguea_y_cierra(client, monkeypatch):
    fake_cursor = FakeCursor(
        execute_side_effects=[RuntimeError("database update failed")]
    )
    fake_connection = FakeConnection(fake_cursor, connection_id=5555)
    log_calls = []

    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", True)
    monkeypatch.setattr(
        client.application.logger,
        "exception",
        lambda message, *args, **kwargs: log_calls.append((message, args, kwargs)),
    )
    login_as(client, MockUser(77, "administrativo"))

    with pytest.raises(RuntimeError, match="database update failed"):
        client.put("/api/pacientes/9", data={"apellido": "DatoClinico"})

    assert fake_connection.rolled_back is True
    assert fake_cursor.closed is True
    assert fake_connection.closed is True
    rendered_log = " ".join(str(part) for call in log_calls for part in (call[0], *call[1]))
    assert "api_modificar_paciente" in rendered_log
    assert "PUT" in rendered_log
    assert "77" in rendered_log
    assert "5555" in rendered_log
    assert "DatoClinico" not in rendered_log


def test_agregar_evolucion_error_db_hace_rollback_loguea_y_cierra(client, monkeypatch):
    fake_cursor = FakeCursor(
        execute_side_effects=[RuntimeError("database evolution insert failed")]
    )
    fake_connection = FakeConnection(fake_cursor, connection_id=6666)
    log_calls = []

    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", True)
    monkeypatch.setattr(
        client.application.logger,
        "exception",
        lambda message, *args, **kwargs: log_calls.append((message, args, kwargs)),
    )
    login_as(client, MockUser(88, "profesional"))

    with pytest.raises(RuntimeError, match="database evolution insert failed"):
        client.post(
            "/api/pacientes/9/evolucion",
            data={
                "fecha": "2026-07-03",
                "contenido": "No debe loguearse",
                "confirmar_firma": "true",
            },
        )

    assert fake_connection.rolled_back is True
    assert fake_cursor.closed is True
    assert fake_connection.closed is True
    rendered_log = " ".join(str(part) for call in log_calls for part in (call[0], *call[1]))
    assert "agregar_evolucion" in rendered_log
    assert "POST" in rendered_log
    assert "88" in rendered_log
    assert "6666" in rendered_log
    assert "No debe loguearse" not in rendered_log


def test_get_evoluciones_error_db_hace_rollback_loguea_y_cierra(client, monkeypatch):
    fake_cursor = FakeCursor(
        execute_side_effects=[RuntimeError("database evolutions read failed")]
    )
    fake_connection = FakeConnection(fake_cursor, connection_id=7777)
    log_calls = []

    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", True)
    monkeypatch.setattr(
        client.application.logger,
        "exception",
        lambda message, *args, **kwargs: log_calls.append((message, args, kwargs)),
    )
    login_as(client, MockUser(99, "profesional"))

    with pytest.raises(RuntimeError, match="database evolutions read failed"):
        client.get("/api/pacientes/9/evoluciones")

    assert fake_connection.rolled_back is True
    assert fake_cursor.closed is True
    assert fake_connection.closed is True
    rendered_log = " ".join(str(part) for call in log_calls for part in (call[0], *call[1]))
    assert "get_evoluciones" in rendered_log
    assert "GET" in rendered_log
    assert "99" in rendered_log
    assert "7777" in rendered_log


def test_modificar_paciente_dni_duplicado_devuelve_409(client, monkeypatch):
    fake_cursor = FakeCursor(fetchone_results=[{"id": 20}])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "administrativo"))

    response = client.put("/api/pacientes/5", data={"dni": "12345678"})

    assert response.status_code == 409
    assert "DNI 12345678" in response.get_json()["error"]


def test_modificar_paciente_nro_hc_duplicado_devuelve_409(client, monkeypatch):
    fake_cursor = FakeCursor(fetchone_results=[{"id": 30}])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "administrativo"))

    response = client.put("/api/pacientes/5", data={"nro_hc": "9999"})

    assert response.status_code == 409
    assert "N° HC 9999" in response.get_json()["error"]


def test_modificar_paciente_campo_requerido_vacio_devuelve_400(client, monkeypatch):
    fake_cursor = FakeCursor(fetchone_results=[None])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "administrativo"))

    response = client.put("/api/pacientes/5", data={"nombre": "   "})

    assert response.status_code == 400
    assert "Nombre" in response.get_json()["error"]


def test_modificar_paciente_sin_cambios_devuelve_200(client, monkeypatch):
    fake_cursor = FakeCursor()
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "administrativo"))

    response = client.put("/api/pacientes/5", json={})

    assert response.status_code == 200
    assert response.get_json().get("sin_cambios") is True
