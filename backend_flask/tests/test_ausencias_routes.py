from datetime import datetime

from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import ausencias_routes


def test_crear_ausencia_franja_valida_devuelve_201(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    fake_cursor = FakeCursor(fetchone_results=[None], lastrowid=123)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(ausencias_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/ausencias",
        json={
            "usuario_id": 999,
            "fecha_inicio": "2026-03-26T09:00:00",
            "fecha_fin": "2026-03-26T12:00:00",
            "motivo": "Capacitacion",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 123

    insert_query, insert_params = fake_cursor.executed[1]
    assert "INSERT INTO ausencias" in insert_query
    assert insert_params[0] == 5
    assert fake_connection.committed is True


def test_crear_ausencia_dia_completo_legacy_fecha_devuelve_201(client, monkeypatch):
    login_as(client, MockUser(user_id=8, rol="profesional"))

    fake_cursor = FakeCursor(fetchone_results=[None], lastrowid=44)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(ausencias_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/ausencias",
        json={
            "fecha": "2026-03-26",
            "motivo": "No asiste",
        },
    )

    assert response.status_code == 201

    _, insert_params = fake_cursor.executed[1]
    assert insert_params[0] == 8
    assert isinstance(insert_params[1], datetime)
    assert isinstance(insert_params[2], datetime)
    assert insert_params[1].hour == 0
    assert insert_params[2].hour == 23


def test_crear_ausencia_rechaza_inicio_mayor_o_igual_fin(client):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    response = client.post(
        "/api/ausencias",
        json={
            "fecha_inicio": "2026-03-26T12:00:00",
            "fecha_fin": "2026-03-26T12:00:00",
        },
    )

    assert response.status_code == 400
    assert "menor" in response.get_json()["error"].lower()


def test_crear_ausencia_rechaza_solape_devuelve_409(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    fake_cursor = FakeCursor(fetchone_results=[{"id": 1}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(ausencias_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/ausencias",
        json={
            "fecha_inicio": "2026-03-26T09:00:00",
            "fecha_fin": "2026-03-26T10:00:00",
        },
    )

    assert response.status_code == 409
    assert len(fake_cursor.executed) == 1
