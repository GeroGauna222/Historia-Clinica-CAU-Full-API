from conftest import MockUser, login_as


def test_role_protected_route_requires_login(client):
    response = client.get("/api/turnos")

    assert response.status_code == 401


def test_role_protected_route_denies_non_allowed_role(client):
    login_as(client, MockUser(user_id=99, rol="invitado"))

    response = client.get("/api/turnos")

    assert response.status_code == 403
