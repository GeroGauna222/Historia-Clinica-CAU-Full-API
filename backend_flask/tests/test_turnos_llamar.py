from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import turnos_routes


def preparar(monkeypatch, fetchone):
    cursor = FakeCursor(fetchone_results=fetchone)
    conn = FakeConnection(cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: conn)
    return cursor, conn


def turno(**kw):
    base = {"id": 10, "usuario_id": 7, "estado_asistencia": "programado", "es_hoy": 1}
    base.update(kw)
    return base


def test_llamar_abre_atencion_y_cierra_la_anterior(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, conn = preparar(monkeypatch, [turno()])

    r = client.post("/api/turnos/10/llamar")

    assert r.status_code == 200
    sqls = [q for q, _ in cursor.executed]
    assert any("SET atencion_fin = NOW()" in q and "id <> %s" in q for q in sqls)
    abrir = [q for q in sqls if "atencion_inicio = NOW()" in q][0]
    assert "atencion_fin = NULL" in abrir and "estado_asistencia = 'presente'" in abrir
    assert conn.committed and cursor.closed and conn.closed


def test_llamar_turno_ajeno_devuelve_403(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, conn = preparar(monkeypatch, [turno(usuario_id=99)])
    assert client.post("/api/turnos/10/llamar").status_code == 403
    assert not conn.committed


def test_director_no_llama_en_nombre_de_otro(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="director"))
    preparar(monkeypatch, [turno(usuario_id=7)])
    assert client.post("/api/turnos/10/llamar").status_code == 403


def test_llamar_turno_inexistente_devuelve_404(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    preparar(monkeypatch, [None])
    assert client.post("/api/turnos/10/llamar").status_code == 404


def test_llamar_ausente_devuelve_409_sin_cambios(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, conn = preparar(monkeypatch, [turno(estado_asistencia="sin_aviso")])
    r = client.post("/api/turnos/10/llamar")
    assert r.status_code == 409
    assert "ausente" in r.get_json()["error"].lower()
    assert not conn.committed


def test_llamar_turno_de_otro_dia_devuelve_409(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, conn = preparar(monkeypatch, [turno(es_hoy=0)])
    assert client.post("/api/turnos/10/llamar").status_code == 409
    assert not conn.committed


def test_llamar_sin_sesion_devuelve_401(client):
    assert client.post("/api/turnos/10/llamar").status_code == 401


def test_llamar_turno_ya_presente_o_atendido_lo_reabre(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, conn = preparar(monkeypatch, [turno(estado_asistencia="presente")])
    assert client.post("/api/turnos/10/llamar").status_code == 200
    assert conn.committed


def test_finalizar_cierra_la_atencion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, conn = preparar(
        monkeypatch,
        [{"id": 10, "usuario_id": 7, "atencion_inicio": "x", "atencion_fin": None}],
    )
    r = client.post("/api/turnos/10/finalizar")
    assert r.status_code == 200
    assert any("SET atencion_fin = NOW()" in q for q, _ in cursor.executed)
    assert conn.committed


def test_finalizar_turno_ajeno_devuelve_403(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    preparar(monkeypatch, [{"id": 10, "usuario_id": 99, "atencion_inicio": "x", "atencion_fin": None}])
    assert client.post("/api/turnos/10/finalizar").status_code == 403


def test_finalizar_turno_que_no_esta_en_atencion_devuelve_409(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    preparar(monkeypatch, [{"id": 10, "usuario_id": 7, "atencion_inicio": None, "atencion_fin": None}])
    assert client.post("/api/turnos/10/finalizar").status_code == 409


def grupal(**kw):
    base = {"id": 5, "grupo_id": 3, "estado_asistencia": "programado", "es_hoy": 1}
    base.update(kw)
    return base


def test_llamar_grupal_miembro_abre_atencion_sin_cerrar_otras(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, conn = preparar(monkeypatch, [grupal(), {"1": 1}])

    r = client.post("/api/turnos/grupales/5/llamar")

    assert r.status_code == 200
    sqls = [q for q, _ in cursor.executed]
    assert any("FROM grupo_miembros" in q for q in sqls)
    assert not any("SET atencion_fin" in q for q in sqls)
    abrir = [q for q in sqls if "UPDATE turnos_grupales" in q][0]
    assert "atencion_inicio = NOW()" in abrir and "atencion_fin = NULL" in abrir
    assert conn.committed


def test_llamar_grupal_no_miembro_devuelve_403(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="administrativo"))
    cursor, conn = preparar(monkeypatch, [grupal(), None])
    assert client.post("/api/turnos/grupales/5/llamar").status_code == 403
    assert not conn.committed


def test_llamar_grupal_inexistente_devuelve_404(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    preparar(monkeypatch, [None])
    assert client.post("/api/turnos/grupales/5/llamar").status_code == 404


def test_llamar_grupal_ausente_devuelve_409(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, conn = preparar(monkeypatch, [grupal(estado_asistencia="con_aviso"), {"1": 1}])
    assert client.post("/api/turnos/grupales/5/llamar").status_code == 409
    assert not conn.committed
