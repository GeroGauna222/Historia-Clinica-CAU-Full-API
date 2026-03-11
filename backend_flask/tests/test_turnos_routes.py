from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import turnos_routes


def test_editar_turno_allows_overlap_for_area_role(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))

    fake_cursor = FakeCursor(fetchone_results=[{"usuario_id": 7}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)

    called = {}

    def fake_medico_disponible(usuario_id, fecha_inicio, fecha_fin, turno_excluir_id=None, permitir_solape=False):
        called["usuario_id"] = usuario_id
        called["turno_excluir_id"] = turno_excluir_id
        called["permitir_solape"] = permitir_solape
        return True

    monkeypatch.setattr(turnos_routes, "medico_disponible", fake_medico_disponible)

    response = client.put(
        "/api/turnos/15",
        json={
            "fecha_inicio": "2026-03-20T10:00:00",
            "fecha_fin": "2026-03-20T10:30:00",
            "motivo": "Control",
        },
    )

    assert response.status_code == 200
    assert called["usuario_id"] == 7
    assert called["turno_excluir_id"] == 15
    assert called["permitir_solape"] is True
    assert fake_connection.committed is True
