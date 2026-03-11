from flask_login import UserMixin

from app.routes import auth_routes


class StubAuthUser(UserMixin):
    def __init__(self):
        self.id = 1
        self.nombre = "Alice"
        self.username = "alice"
        self.email = "alice@example.com"
        self.rol = "director"

    def verificar_password(self, raw_password):
        return raw_password == "secret123"


def test_login_rejects_missing_credentials(client):
    response = client.post("/api/login", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_login_success(client, monkeypatch):
    stub_user = StubAuthUser()

    monkeypatch.setattr(
        auth_routes.Usuario,
        "obtener_por_username",
        staticmethod(lambda username: stub_user if username == "alice" else None),
    )

    response = client.post(
        "/api/login",
        json={"username": "alice", "password": "secret123"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["user"]["username"] == "alice"
    assert payload["user"]["rol"] == "director"

    with client.session_transaction() as session:
        assert session.get("_user_id") == "1"
