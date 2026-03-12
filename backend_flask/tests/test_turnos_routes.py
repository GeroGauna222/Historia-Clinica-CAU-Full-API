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


def test_crear_turno_rechaza_si_medico_no_disponible(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    fake_cursor = FakeCursor()
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *args, **kwargs: False)

    response = client.post(
        "/api/turnos",
        json={
            "paciente_id": 10,
            "usuario_id": 7,
            "fecha_inicio": "2026-03-20T10:00:00",
            "fecha_fin": "2026-03-20T10:30:00",
            "motivo": "Control",
        },
    )

    assert response.status_code == 400
    assert "no est" in response.get_json()["error"].lower()


def test_editar_turno_rechaza_si_medico_no_disponible(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    fake_cursor = FakeCursor(fetchone_results=[{"usuario_id": 7}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *args, **kwargs: False)

    response = client.put(
        "/api/turnos/15",
        json={
            "fecha_inicio": "2026-03-20T10:00:00",
            "fecha_fin": "2026-03-20T10:30:00",
            "motivo": "Control",
        },
    )

    assert response.status_code == 400
    assert "no est" in response.get_json()["error"].lower()


def test_medico_disponible_considera_solape_general_con_ausencias(monkeypatch):
    fake_cursor = FakeCursor(
        fetchone_results=[
            {"rol": "profesional"},
            {"ok": 1},  # disponibilidad
            {"ok": 1},  # ausencia solapada
            None,  # ocupado
        ]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)

    disponible = turnos_routes.medico_disponible(
        7,
        "2026-03-26T10:00:00",
        "2026-03-26T10:30:00",
    )

    assert disponible is False
    query_ausencias, params_ausencias = fake_cursor.executed[2]
    assert "fecha_inicio < %s" in query_ausencias
    assert "fecha_fin > %s" in query_ausencias
    assert params_ausencias == (7, "2026-03-26T10:30:00", "2026-03-26T10:00:00")
