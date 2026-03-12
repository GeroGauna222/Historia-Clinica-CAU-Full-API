from datetime import datetime

from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import grupos_routes


def test_obtener_ausencias_grupo_incluye_nombre_usuario(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))

    fake_cursor = FakeCursor(
        fetchall_results=[
            [
                {
                    "id": 10,
                    "usuario_id": 4,
                    "nombre_usuario": "Dra. Perez",
                    "fecha_inicio": datetime(2026, 3, 26, 0, 0, 0),
                    "fecha_fin": datetime(2026, 3, 26, 23, 59, 59),
                    "motivo": "No asiste",
                }
            ]
        ]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(grupos_routes, "get_connection", lambda: fake_connection)

    response = client.get("/api/grupos/3/ausencias")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]["nombre_usuario"] == "Dra. Perez"
    assert "T" in payload[0]["fecha_inicio"]
    assert payload[0]["usuario_id"] == 4
