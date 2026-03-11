from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import disponibilidades_routes


def test_crear_disponibilidad_area_uses_own_user_and_normalizes_day(client, monkeypatch):
    login_as(client, MockUser(user_id=42, rol="area"))

    fake_cursor = FakeCursor(lastrowid=321)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(disponibilidades_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/disponibilidades",
        json={
            "usuario_id": 999,
            "dia_semana": "Miércoles",
            "hora_inicio": "09:00",
            "hora_fin": "12:00",
            "activo": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["id"] == 321

    query, params = fake_cursor.executed[0]
    assert "INSERT INTO disponibilidades" in query
    assert params[0] == 42
    assert params[1] == "Miercoles"
    assert fake_connection.committed is True
