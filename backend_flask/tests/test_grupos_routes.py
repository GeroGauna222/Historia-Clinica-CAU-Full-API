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


# ---- consultorio (pantalla de llamados) ----
def _put_grupo(client, monkeypatch, body, fetchone=None):
    login_as(client, MockUser(user_id=1, rol="director"))
    cursor = FakeCursor(fetchone_results=fetchone or [])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(grupos_routes, "get_connection", lambda: connection)
    response = client.put("/api/grupos/3", json=body)
    updates = [(q, p) for q, p in cursor.executed if q.strip().upper().startswith("UPDATE")]
    return response, cursor, connection, updates


def test_actualizar_grupo_guarda_consultorio(client, monkeypatch):
    response, cursor, connection, updates = _put_grupo(client, monkeypatch, {"consultorio": "  Gimnasio "})

    assert response.status_code == 200
    assert len(updates) == 1
    query, params = updates[0]
    assert "consultorio = %s" in query
    assert params == ("Gimnasio", 3)
    assert connection.committed is True
    assert cursor.closed is True and connection.closed is True


def test_no_se_puede_quitar_consultorio_a_grupo_visible(client, monkeypatch):
    response, cursor, connection, updates = _put_grupo(
        client, monkeypatch, {"consultorio": ""}, fetchone=[(1,)]
    )

    assert response.status_code == 400
    assert "visible" in response.get_json()["error"].lower()
    assert updates == []
    assert connection.committed is False
    assert cursor.executed[0][1] == (3,)
    assert "mostrar_en_pantalla" in cursor.executed[0][0]
    assert cursor.closed is True and connection.closed is True


def test_grupo_visible_no_aplica_otros_cambios_a_medias(client, monkeypatch):
    response, cursor, connection, updates = _put_grupo(
        client,
        monkeypatch,
        {"nombre": "Otro", "consultorio": None, "miembros": [1, 2]},
        fetchone=[(1,)],
    )

    assert response.status_code == 400
    # Solo el SELECT de visibilidad: ningun UPDATE/DELETE/INSERT ni commit.
    assert len(cursor.executed) == 1
    assert cursor.executed[0][0].strip().upper().startswith("SELECT")
    assert updates == []
    assert connection.committed is False


def test_consultorio_none_en_grupo_consulta_visibilidad_y_guarda_none(client, monkeypatch):
    response, cursor, _, updates = _put_grupo(client, monkeypatch, {"consultorio": None}, fetchone=[(0,)])

    assert response.status_code == 200
    assert "mostrar_en_pantalla" in cursor.executed[0][0]
    assert updates[0][1] == (None, 3)


def test_consultorio_numerico_en_grupo_se_guarda_como_texto(client, monkeypatch):
    response, cursor, _, updates = _put_grupo(client, monkeypatch, {"consultorio": 3})

    assert response.status_code == 200
    assert updates[0][1] == ("3", 3)
    # Con consultorio no vacio no se consulta la visibilidad.
    assert len(cursor.executed) == 1


def test_quitar_consultorio_a_grupo_inexistente_no_da_404(client, monkeypatch):
    # Comportamiento actual (sin 404 explicito): el SELECT no encuentra fila y el UPDATE no afecta nada.
    response, _, _, updates = _put_grupo(client, monkeypatch, {"consultorio": ""}, fetchone=[])

    assert response.status_code == 200
    assert updates[0][1] == (None, 3)


def test_quitar_consultorio_a_grupo_no_visible(client, monkeypatch):
    response, _, connection, updates = _put_grupo(
        client, monkeypatch, {"consultorio": "   "}, fetchone=[(0,)]
    )

    assert response.status_code == 200
    assert len(updates) == 1
    assert "consultorio = %s" in updates[0][0]
    assert updates[0][1] == (None, 3)
    assert connection.committed is True


def test_actualizar_grupo_consultorio_demasiado_largo_es_400_sin_update(client, monkeypatch):
    response, cursor, connection, updates = _put_grupo(client, monkeypatch, {"consultorio": "x" * 51})

    assert response.status_code == 400
    assert "50" in response.get_json()["error"]
    assert updates == []
    assert cursor.executed == []
    assert connection.committed is False


def test_actualizar_grupo_sin_consultorio_no_consulta_visibilidad(client, monkeypatch):
    response, cursor, _, updates = _put_grupo(client, monkeypatch, {"nombre": "Nuevo"})

    assert response.status_code == 200
    assert updates == [("UPDATE grupos_profesionales SET nombre=%s WHERE id=%s", ("Nuevo", 3))]
    assert len(cursor.executed) == 1


def test_listado_de_grupos_incluye_consultorio_y_visibilidad(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))
    cursor = FakeCursor(
        fetchall_results=[
            [
                {"id": 3, "nombre": "Rehab", "consultorio": "Gimnasio", "mostrar_en_pantalla": 1},
                {"id": 4, "nombre": "Otro", "consultorio": None, "mostrar_en_pantalla": 0},
            ],
            [],
            [],
        ]
    )
    connection = FakeConnection(cursor)
    monkeypatch.setattr(grupos_routes, "get_connection", lambda: connection)

    response = client.get("/api/grupos")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]["consultorio"] == "Gimnasio"
    assert payload[0]["mostrar_en_pantalla"] is True
    assert payload[1]["consultorio"] is None
    assert payload[1]["mostrar_en_pantalla"] is False
    assert "consultorio" in cursor.executed[0][0] and "mostrar_en_pantalla" in cursor.executed[0][0]


def test_obtener_grupo_incluye_consultorio_y_visibilidad(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))
    cursor = FakeCursor(
        fetchone_results=[{"id": 3, "nombre": "Rehab", "consultorio": "Gimnasio", "mostrar_en_pantalla": 1}],
        fetchall_results=[[]],
    )
    connection = FakeConnection(cursor)
    monkeypatch.setattr(grupos_routes, "get_connection", lambda: connection)

    response = client.get("/api/grupos/3")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["consultorio"] == "Gimnasio"
    assert payload["mostrar_en_pantalla"] is True
    assert "consultorio" in cursor.executed[0][0] and "mostrar_en_pantalla" in cursor.executed[0][0]
