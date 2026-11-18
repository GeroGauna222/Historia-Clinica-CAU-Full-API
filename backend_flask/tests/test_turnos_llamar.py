from datetime import datetime

import pytest

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
    cierre = [(q, p) for q, p in cursor.executed if "SET atencion_fin = NOW()" in q][0]
    assert "id <> %s" in cierre[0] and "usuario_id = %s" in cierre[0]
    assert cierre[1] == (7, 10)
    abrir_q, abrir_p = [(q, p) for q, p in cursor.executed if "atencion_inicio = NOW()" in q][0]
    assert "atencion_fin = NULL" in abrir_q and "estado_asistencia = 'presente'" in abrir_q
    assert abrir_p == (10,)
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
    cursor, conn = preparar(monkeypatch, [grupal(grupo_id=3), {"1": 1}])

    r = client.post("/api/turnos/grupales/5/llamar")

    assert r.status_code == 200
    q_miembro = [(q, p) for q, p in cursor.executed if "FROM grupo_miembros" in q]
    assert q_miembro and q_miembro[0][1] == (3, 7)  # (turno["grupo_id"], current_user.id)
    # Un unico UPDATE: llamar a un paciente no cierra las demas atenciones del grupo.
    assert len([q for q, _ in cursor.executed if q.lstrip().startswith("UPDATE")]) == 1
    abrir_q, abrir_p = [(q, p) for q, p in cursor.executed if "UPDATE turnos_grupales" in q][0]
    assert "atencion_inicio = NOW()" in abrir_q and "atencion_fin = NULL" in abrir_q
    assert "estado_asistencia = 'presente'" in abrir_q
    assert abrir_p == (5,)
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


def test_llamar_grupal_de_otro_dia_devuelve_409(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, conn = preparar(monkeypatch, [grupal(es_hoy=0), {"1": 1}])
    assert client.post("/api/turnos/grupales/5/llamar").status_code == 409
    assert not conn.committed


# --- Limpieza de la atencion al cambiar la asistencia o reprogramar ---------

LIMPIEZA = "SET atencion_inicio = NULL"


def _limpiezas(cursor):
    """UPDATEs de limpieza ejecutados, como (sql, params)."""
    return [(q, p) for q, p in cursor.executed if LIMPIEZA in q]


def _indice(cursor, fragmento):
    """Posicion (unica) en cursor.executed de la consulta que contiene `fragmento`."""
    idx = [i for i, (q, _) in enumerate(cursor.executed) if fragmento in q]
    assert len(idx) == 1, f"se esperaba una sola consulta con {fragmento!r}: {idx}"
    return idx[0]


@pytest.mark.parametrize("estado", ["sin_aviso", "con_aviso", "programado"])
def test_cambiar_asistencia_a_no_presente_borra_la_atencion(client, monkeypatch, estado):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, conn = preparar(monkeypatch, [{"usuario_id": 7}])

    r = client.patch("/api/turnos/10/asistencia", json={"estado_asistencia": estado})

    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1
    sql, params = limpiezas[0]
    assert sql.startswith("UPDATE turnos ") and "atencion_fin = NULL" in sql
    assert "estado_asistencia" not in sql  # no vuelve a programado: solo limpia
    assert params == (10,)
    # La limpieza va despues del UPDATE de asistencia y antes del commit.
    assert _indice(cursor, LIMPIEZA) > _indice(cursor, "UPDATE turnos SET ausencia")
    assert conn.committed


def test_marcar_ausente_por_alias_ausencia_borra_la_atencion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, _ = preparar(monkeypatch, [{"usuario_id": 7}])
    r = client.patch("/api/turnos/10/ausencia", json={"ausencia": "sin_aviso"})
    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1 and limpiezas[0][1] == (10,)


def test_marcar_presente_no_borra_la_atencion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, _ = preparar(monkeypatch, [{"usuario_id": 7}])
    r = client.patch("/api/turnos/10/asistencia", json={"estado_asistencia": "presente"})
    assert r.status_code == 200
    assert _limpiezas(cursor) == []


def test_asistencia_turno_ajeno_no_borra_la_atencion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, _ = preparar(monkeypatch, [{"usuario_id": 99}])
    r = client.patch("/api/turnos/10/asistencia", json={"estado_asistencia": "sin_aviso"})
    assert r.status_code == 403
    assert _limpiezas(cursor) == []


def test_asistencia_en_turno_grupal_via_ruta_individual_borra_la_atencion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    # No existe en turnos: cae al fallback de turnos_grupales.
    cursor, _ = preparar(monkeypatch, [None, {"id": 10}])
    r = client.patch("/api/turnos/10/asistencia", json={"estado_asistencia": "sin_aviso"})
    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1
    sql, params = limpiezas[0]
    assert sql.startswith("UPDATE turnos_grupales ") and params == (10,)
    assert _indice(cursor, LIMPIEZA) > _indice(cursor, "UPDATE turnos_grupales SET ausencia")


def test_asistencia_en_turno_grupal_via_ruta_individual_presente_no_borra(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    cursor, _ = preparar(monkeypatch, [None, {"id": 10}])
    r = client.patch("/api/turnos/10/asistencia", json={"estado_asistencia": "presente"})
    assert r.status_code == 200
    assert _limpiezas(cursor) == []


@pytest.mark.parametrize("ruta", ["asistencia", "ausencia"])
def test_patch_grupal_ausente_borra_la_atencion(client, monkeypatch, ruta):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, conn = preparar(monkeypatch, [{"id": 5}])
    body = {"estado_asistencia": "con_aviso"} if ruta == "asistencia" else {"ausencia": "con_aviso"}

    r = client.patch(f"/api/turnos/grupales/5/{ruta}", json=body)

    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1
    sql, params = limpiezas[0]
    assert sql.startswith("UPDATE turnos_grupales ") and params == (5,)
    assert _indice(cursor, LIMPIEZA) > _indice(cursor, "UPDATE turnos_grupales SET ausencia")
    assert conn.committed


def test_patch_grupal_presente_no_borra_la_atencion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, _ = preparar(monkeypatch, [{"id": 5}])
    r = client.patch("/api/turnos/grupales/5/asistencia", json={"estado_asistencia": "presente"})
    assert r.status_code == 200
    assert _limpiezas(cursor) == []


def test_patch_grupal_volver_a_programado_borra_la_atencion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, _ = preparar(monkeypatch, [{"id": 5}])
    r = client.patch("/api/turnos/grupales/5/asistencia", json={"estado_asistencia": "programado"})
    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1 and limpiezas[0][1] == (5,)


def test_falla_la_limpieza_en_patch_hace_rollback_y_no_confirma(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))
    # execute #0 SELECT, #1 UPDATE de asistencia, #2 UPDATE de limpieza (falla)
    cursor = FakeCursor(
        fetchone_results=[{"usuario_id": 7}],
        execute_side_effects=[None, None, RuntimeError("limpieza fallo")],
    )
    conn = FakeConnection(cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: conn)

    r = client.patch("/api/turnos/10/asistencia", json={"estado_asistencia": "sin_aviso"})

    assert r.status_code == 500
    assert LIMPIEZA in cursor.executed[2][0]
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


# PUT individual (reprogramar) ------------------------------------------------


def _put_turno(client, monkeypatch, body, fecha_fin=datetime(2026, 3, 20, 10, 20)):
    login_as(client, MockUser(user_id=7, rol="area"))
    cursor, conn = preparar(
        monkeypatch,
        [
            {
                "usuario_id": 7,
                "fecha_inicio": datetime(2026, 3, 20, 10, 0),
                "fecha_fin": fecha_fin,  # 10:20 = inicio + duracion por defecto (20 min)
                "motivo": "Control",
                "observaciones": "",
                "es_sobreturno": 0,
            }
        ],
    )
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *a, **k: True)
    r = client.put("/api/turnos/15", json=body)
    return r, cursor, conn


def test_reprogramar_turno_mismo_dia_borra_la_atencion_sin_volver_a_programado(client, monkeypatch):
    r, cursor, conn = _put_turno(client, monkeypatch, {"fecha_inicio": "2026-03-20T11:00:00"})
    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1
    sql, params = limpiezas[0]
    assert sql.startswith("UPDATE turnos ") and params == (15,)
    assert "estado_asistencia" not in sql and "ausencia" not in sql
    assert _indice(cursor, LIMPIEZA) > _indice(cursor, "SET fecha_inicio=%s")
    assert conn.committed


def test_reprogramar_turno_otro_dia_vuelve_a_programado(client, monkeypatch):
    r, cursor, _ = _put_turno(client, monkeypatch, {"fecha_inicio": "2026-03-21T10:00:00"})
    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1
    sql, params = limpiezas[0]
    assert sql.startswith("UPDATE turnos ") and params == (15,)
    assert "estado_asistencia = 'programado'" in sql and "ausencia = NULL" in sql
    assert _indice(cursor, LIMPIEZA) > _indice(cursor, "SET fecha_inicio=%s")


def test_editar_solo_motivo_no_borra_la_atencion(client, monkeypatch):
    r, cursor, _ = _put_turno(client, monkeypatch, {"motivo": "Otro motivo"})
    assert r.status_code == 200
    assert _limpiezas(cursor) == []


def test_editar_turno_misma_hora_explicita_no_borra_la_atencion(client, monkeypatch):
    r, cursor, _ = _put_turno(client, monkeypatch, {"fecha_inicio": "2026-03-20T10:00:00", "motivo": "x"})
    assert r.status_code == 200
    assert _limpiezas(cursor) == []


def test_editar_motivo_con_fecha_fin_guardada_distinta_de_la_recalculada_no_borra_la_atencion(client, monkeypatch):
    # fecha_fin guardada 10:45 (la duracion del profesional cambio despues); se recalcula a 10:20.
    # El inicio no cambia, asi que una atencion en curso no debe borrarse.
    r, cursor, conn = _put_turno(
        client, monkeypatch, {"motivo": "Otro motivo"}, fecha_fin=datetime(2026, 3, 20, 10, 45)
    )
    assert r.status_code == 200
    assert _limpiezas(cursor) == []
    assert conn.committed


def test_falla_la_limpieza_en_put_hace_rollback_y_no_confirma(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="area"))
    # execute #0 SELECT turno, #1 duracion, #2 solape, #3 UPDATE principal, #4 limpieza (falla)
    cursor = FakeCursor(
        fetchone_results=[
            {
                "usuario_id": 7,
                "fecha_inicio": datetime(2026, 3, 20, 10, 0),
                "fecha_fin": datetime(2026, 3, 20, 10, 20),
                "motivo": "Control",
                "observaciones": "",
                "es_sobreturno": 0,
            }
        ],
        execute_side_effects=[None, None, None, None, RuntimeError("limpieza fallo")],
    )
    conn = FakeConnection(cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: conn)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *a, **k: True)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", True)

    with pytest.raises(RuntimeError, match="limpieza fallo"):
        client.put("/api/turnos/15", json={"fecha_inicio": "2026-03-20T11:00:00"})

    assert LIMPIEZA in cursor.executed[4][0]
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


# PUT grupal (reprogramar) ----------------------------------------------------


def _put_grupal(client, monkeypatch, body):
    login_as(client, MockUser(user_id=7, rol="area"))
    actual = {
        "id": 5,
        "grupo_id": 3,
        "paciente_id": 9,
        "fecha_inicio": datetime(2026, 3, 20, 10, 0),
        "fecha_fin": datetime(2026, 3, 20, 10, 30),
        "motivo": "Taller",
        "observaciones": "",
    }
    cursor, conn = preparar(monkeypatch, [actual, {"id": 3}])
    r = client.put("/api/turnos/grupales/5", json=body)
    return r, cursor, conn


def test_reprogramar_grupal_mismo_dia_borra_la_atencion_sin_volver_a_programado(client, monkeypatch):
    r, cursor, conn = _put_grupal(
        client, monkeypatch, {"fecha_inicio": "2026-03-20T11:00:00", "fecha_fin": "2026-03-20T11:30:00"}
    )
    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1
    sql, params = limpiezas[0]
    assert sql.startswith("UPDATE turnos_grupales ") and params == (5,)
    assert "estado_asistencia" not in sql and "ausencia" not in sql
    assert _indice(cursor, LIMPIEZA) > _indice(cursor, "SET grupo_id=%s")
    assert conn.committed


def test_reprogramar_grupal_otro_dia_vuelve_a_programado(client, monkeypatch):
    r, cursor, _ = _put_grupal(
        client, monkeypatch, {"fecha_inicio": "2026-03-21T10:00:00", "fecha_fin": "2026-03-21T10:30:00"}
    )
    assert r.status_code == 200
    limpiezas = _limpiezas(cursor)
    assert len(limpiezas) == 1
    sql, params = limpiezas[0]
    assert sql.startswith("UPDATE turnos_grupales ") and params == (5,)
    assert "estado_asistencia = 'programado'" in sql and "ausencia = NULL" in sql
    assert _indice(cursor, LIMPIEZA) > _indice(cursor, "SET grupo_id=%s")


def test_editar_grupal_solo_motivo_no_borra_la_atencion(client, monkeypatch):
    r, cursor, _ = _put_grupal(client, monkeypatch, {"motivo": "Otro"})
    assert r.status_code == 200
    assert _limpiezas(cursor) == []
