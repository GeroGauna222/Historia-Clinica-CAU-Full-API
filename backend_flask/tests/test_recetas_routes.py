from datetime import date

from app.routes import recetas_routes
from conftest import FakeConnection, FakeCursor, MockUser, login_as


PACIENTE = {
    "id": 7,
    "apellido": "Perez",
    "nombre": "Ana",
    "dni": "30111222",
    "sexo": "Femenino",
    "fecha_nacimiento": date(1990, 5, 20),
    "email": "ana@example.com",
    "celular": "111",
    "telefono": "222",
}

USUARIO = {
    "id": 3,
    "nombre": "Juan Castro",
    "email": "juan@example.com",
    "dni": "20111222",
    "sexo": "M",
    "telefono": "333",
    "especialidad": "Kinesiologia",
    "matricula_tipo": "MN",
    "matricula_numero": "12345",
    "matricula_provincia": "",
}


def _setup_config(client):
    client.application.config.update(
        QBITOS_RECIPE_TOKEN="token",
        QBITOS_RECIPE_CLIENT_APP_ID=142,
        QBITOS_RECIPE_BASE_URL="https://qbitos.example",
        QBITOS_RECIPE_TIMEOUT=3,
    )


def _patch_connections(monkeypatch, store_count=1):
    cursors = [
        FakeCursor(fetchone_results=[PACIENTE.copy()]),
        FakeCursor(fetchone_results=[USUARIO.copy()]),
    ]
    cursors.extend(FakeCursor(lastrowid=index + 10) for index in range(store_count))
    connections = [FakeConnection(cursor) for cursor in cursors]

    def fake_get_connection():
        return connections.pop(0)

    monkeypatch.setattr(recetas_routes, "get_connection", fake_get_connection)
    return cursors


def _patch_qbitos(monkeypatch):
    calls = []

    def fake_qbitos_request(method, path, *, params=None, json_body=None):
        calls.append({"method": method, "path": path, "params": params, "json": json_body})
        return {
            "recetas": [{"idReceta": f"RX-{len(calls)}", "s3Link": "https://pdf.example"}],
            "response": [{"status": "emitida"}],
            "idTransaccion": f"TX-{len(calls)}",
        }, None, None

    monkeypatch.setattr(recetas_routes, "_qbitos_request", fake_qbitos_request)
    return calls


def test_receta_rechaza_mas_de_tres_medicamentos(client, monkeypatch):
    _setup_config(client)
    _patch_connections(monkeypatch)
    calls = _patch_qbitos(monkeypatch)
    login_as(client, MockUser(3, "profesional"))

    response = client.post("/api/recetas", json={
        "paciente_id": 7,
        "medicamentos": [{"nombreProducto": f"Med {index}", "cantidad": 1} for index in range(4)],
    })

    assert response.status_code == 400
    assert "maximo 3" in response.get_json()["error"]
    assert calls == []


def test_receta_rechaza_cantidad_mayor_a_dos(client, monkeypatch):
    _setup_config(client)
    _patch_connections(monkeypatch)
    calls = _patch_qbitos(monkeypatch)
    login_as(client, MockUser(3, "profesional"))

    response = client.post("/api/recetas", json={
        "paciente_id": 7,
        "medicamentos": [{"nombreProducto": "Ibuprofeno", "cantidad": 3}],
    })

    assert response.status_code == 400
    assert "entre 1 y 2" in response.get_json()["error"]
    assert calls == []


def test_receta_usa_profesional_desde_usuario(client, monkeypatch):
    _setup_config(client)
    _patch_connections(monkeypatch)
    calls = _patch_qbitos(monkeypatch)
    login_as(client, MockUser(3, "profesional"))

    response = client.post("/api/recetas", json={
        "paciente_id": 7,
        "medico": {"nombre": "No", "apellido": "Cliente", "nroDoc": "999"},
        "medicamentos": [{"nombreProducto": "Ibuprofeno", "cantidad": 1}],
    })

    assert response.status_code == 200
    assert calls[0]["json"]["medico"]["nombre"] == "Juan"
    assert calls[0]["json"]["medico"]["apellido"] == "Castro"
    assert calls[0]["json"]["medico"]["nroDoc"] == "20111222"


def test_estudio_genera_una_llamada_por_bloque(client, monkeypatch):
    _setup_config(client)
    _patch_connections(monkeypatch, store_count=2)
    calls = _patch_qbitos(monkeypatch)
    login_as(client, MockUser(3, "profesional"))

    response = client.post("/api/recetas", json={
        "tipo": "estudio",
        "paciente_id": 7,
        "estudios": [
            {"texto": "Radiografia de torax"},
            {"texto": "Ecografia abdominal"},
        ],
    })

    assert response.status_code == 200
    body = response.get_json()
    assert [item["estudioIndex"] for item in body["resultados"]] == [0, 1]
    assert [call["path"] for call in calls] == [recetas_routes.PRACTICA_ENDPOINT, recetas_routes.PRACTICA_ENDPOINT]


def test_estudio_texto_libre_usa_nombre_sin_id(client, monkeypatch):
    _setup_config(client)
    _patch_connections(monkeypatch)
    calls = _patch_qbitos(monkeypatch)
    login_as(client, MockUser(3, "profesional"))

    response = client.post("/api/recetas", json={
        "tipo": "estudio",
        "paciente_id": 7,
        "estudios": [{"texto": "Ecodoppler transcraneal"}],
    })

    assert response.status_code == 200
    prescripcion = calls[0]["json"]["prescripcion"][0]
    assert prescripcion["nombre"] == "Ecodoppler transcraneal"
    assert "id" not in prescripcion


def test_diagnostico_default_z769(client, monkeypatch):
    _setup_config(client)
    _patch_connections(monkeypatch)
    calls = _patch_qbitos(monkeypatch)
    login_as(client, MockUser(3, "profesional"))

    response = client.post("/api/recetas", json={
        "paciente_id": 7,
        "medicamentos": [{"nombreProducto": "Ibuprofeno", "cantidad": 1}],
    })

    assert response.status_code == 200
    payload = calls[0]["json"]
    assert payload["codigoDiagnostico"] == "Z769"
    assert payload["observaciones"] == "Tratamiento prolongado"
