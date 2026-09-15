from datetime import datetime

import pytest

from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import ausencias_routes, turnos_routes


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


def test_crear_turno_grupal_tanda_crea_multiples_turnos(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))

    class InsertAwareCursor(FakeCursor):
        def __init__(self, fetchone_results=None, fetchall_results=None):
            super().__init__(fetchone_results=fetchone_results, fetchall_results=fetchall_results, lastrowid=0)
            self._insert_counter = 0

        def execute(self, query, params=None):
            super().execute(query, params)
            if "INSERT INTO turnos_grupales" in query:
                self._insert_counter += 1
                self.lastrowid = self._insert_counter

    fake_cursor = InsertAwareCursor(
        fetchone_results=[
            {"id": 4},  # grupo existe
            {"id": 9},  # paciente existe
        ]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/turnos/grupales",
        json={
            "modo": "tanda",
            "grupo_id": 4,
            "paciente_id": 9,
            "fecha_inicio": "2026-03-20T10:00:00",
            "fecha_fin": "2026-03-20T10:20:00",
            "hora": "10:00",
            "dias_semana": [0, 2, 4],
            "cantidad": 3,
            "motivo": "Rehab",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["modo"] == "tanda"
    assert payload["cantidad_creada"] == 3
    assert len(payload["ids"]) == 3
    assert fake_connection.committed is True

    insert_queries = [q for q, _ in fake_cursor.executed if "INSERT INTO turnos_grupales" in q]
    assert len(insert_queries) == 3


def test_crear_turno_grupal_tanda_rechaza_cantidad_invalida(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))

    def _no_db():
        raise AssertionError("No deberia abrir conexion para validaciones de tanda invalidas")

    monkeypatch.setattr(turnos_routes, "get_connection", _no_db)

    response = client.post(
        "/api/turnos/grupales",
        json={
            "modo": "tanda",
            "grupo_id": 4,
            "paciente_id": 9,
            "fecha_inicio": "2026-03-20T10:00:00",
            "hora": "10:00",
            "dias_semana": [0, 2],
            "cantidad": 0,
            "motivo": "Rehab",
        },
    )

    assert response.status_code == 400
    assert "cantidad" in response.get_json()["error"].lower()


def test_listar_turnos_grupales_incluye_datos_de_cobertura(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))

    fake_cursor = FakeCursor(fetchall_results=[[{
        "id": 12,
        "grupo_id": 4,
        "grupo_nombre": "Rehabilitación",
        "color": "#00936B",
        "es_rehabilitacion": 1,
        "paciente_id": 9,
        "paciente": "Ana Pérez",
        "dni": "12345678",
        "cobertura": "IOMA",
        "nro_certificado": "AF-9087",
        "fecha_inicio": datetime(2026, 9, 16, 10, 0),
        "fecha_fin": datetime(2026, 9, 16, 10, 30),
        "motivo": "Rehabilitación",
        "creado_por": 2,
        "observaciones": None,
        "ausencia": None,
        "estado_asistencia": "programado",
        "creado_por_nombre": "Administración",
        "creado_en": datetime(2026, 9, 15, 9, 0),
    }]])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)

    response = client.get("/api/turnos/grupales")

    assert response.status_code == 200
    turno = response.get_json()[0]
    assert turno["cobertura"] == "IOMA"
    assert turno["nro_certificado"] == "AF-9087"
    assert turno["nro_cobertura"] == "AF-9087"


def test_generar_fechas_tanda_quincenal():
    from app.routes.turnos_routes import _generar_fechas_tanda

    fecha_base, fechas, err = _generar_fechas_tanda(
        fecha_inicio_raw="2026-07-06T10:00:00",
        raw_weekdays=["Monday", "Wednesday"],
        cantidad_raw=4,
        raw_hora="10:00",
        frecuencia_semanas=2
    )

    assert err is None
    assert len(fechas) == 4
    assert fechas[0].strftime("%Y-%m-%d") == "2026-07-06"
    assert fechas[1].strftime("%Y-%m-%d") == "2026-07-08"
    assert fechas[2].strftime("%Y-%m-%d") == "2026-07-20"
    assert fechas[3].strftime("%Y-%m-%d") == "2026-07-22"


def test_generar_fechas_tanda_mensual():
    from app.routes.turnos_routes import _generar_fechas_tanda

    fecha_base, fechas, err = _generar_fechas_tanda(
        fecha_inicio_raw="2026-07-06T10:00:00",
        raw_weekdays=["Monday"],
        cantidad_raw=3,
        raw_hora="10:00",
        frecuencia_semanas=4
    )

    assert err is None
    assert len(fechas) == 3
    assert fechas[0].strftime("%Y-%m-%d") == "2026-07-06"
    assert fechas[1].strftime("%Y-%m-%d") == "2026-08-03"
    assert fechas[2].strftime("%Y-%m-%d") == "2026-08-31"


def test_crear_turnos_tanda_individual_endpoint_works(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    from app.routes import turnos_routes

    fake_cursor = FakeCursor(fetchone_results=[{"duracion_turno": 20}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *args, **kwargs: True)

    response = client.post(
        "/api/turnos/tanda",
        json={
            "paciente_id": 10,
            "usuario_id": 7,
            "fecha": "2026-07-06T10:00:00",
            "cantidad": 2,
            "dias_semana": ["Lunes"],
            "frecuencia_semanas": 2,
            "motivo": "Consulta"
        }
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert "crearon 2 turnos" in payload["message"].lower()
    assert fake_connection.committed is True


def test_crear_y_editar_turno_con_observaciones(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    from app.routes import turnos_routes

    # 1. Test POST /api/turnos
    # Para POST, fetchone se usa para buscar email de paciente y nombre de profesional.
    # Así que mockeamos esas consultas.
    fake_cursor_post = FakeCursor(
        fetchone_results=[
            {"email": "test@paciente.com", "nombre": "P", "apellido": "P"},  # Paciente
            {"nombre": "Doc"},  # Profesional
        ]
    )
    fake_conn_post = FakeConnection(fake_cursor_post)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_conn_post)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *args, **kwargs: True)

    response = client.post(
        "/api/turnos",
        json={
            "paciente_id": 10,
            "usuario_id": 7,
            "fecha_inicio": "2026-07-06T10:00:00",
            "motivo": "Consulta",
            "observaciones": "Paciente necesita silla de ruedas"
        }
    )

    assert response.status_code == 201
    # Verificar que el execute insertó observaciones
    inserted_queries = [item for item in fake_cursor_post.executed if "INSERT INTO turnos" in item[0]]
    assert len(inserted_queries) == 1
    assert "observaciones" in inserted_queries[0][0]

    # 2. Test PUT /api/turnos/15
    # Para PUT, fetchone busca el turno inicial. Mockeamos eso.
    fake_cursor_put = FakeCursor(
        fetchone_results=[
            {"usuario_id": 7, "fecha_inicio": "2026-07-06T10:00:00", "fecha_fin": "2026-07-06T10:20:00", "motivo": "Consulta", "observaciones": ""}
        ]
    )
    fake_conn_put = FakeConnection(fake_cursor_put)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_conn_put)

    response = client.put(
        "/api/turnos/15",
        json={
            "fecha_inicio": "2026-07-06T10:00:00",
            "motivo": "Consulta Modificada",
            "observaciones": "Observaciones modificadas"
        }
    )

    assert response.status_code == 200
    update_queries = [item for item in fake_cursor_put.executed if "UPDATE turnos" in item[0]]
    assert len(update_queries) == 1
    assert "observaciones" in update_queries[0][0]


def test_actualizar_ausencia_y_conteo_ausencias(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    from app.routes import turnos_routes

    # 1. Test PATCH /api/turnos/15/ausencia
    fake_cursor_patch = FakeCursor(
        fetchone_results=[{"usuario_id": 7}]
    )
    fake_conn_patch = FakeConnection(fake_cursor_patch)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_conn_patch)

    response = client.patch(
        "/api/turnos/15/ausencia",
        json={"ausencia": "sin_aviso"}
    )
    assert response.status_code == 200
    update_queries = [item for item in fake_cursor_patch.executed if "UPDATE turnos SET" in item[0]]
    assert len(update_queries) == 1
    assert "ausencia" in update_queries[0][0]
    assert "estado_asistencia" in update_queries[0][0]
    assert update_queries[0][1] == ("sin_aviso", "sin_aviso", 15)

    # 2. Test PATCH /api/turnos/grupales/20/ausencia
    login_as(client, MockUser(user_id=7, rol="administrativo")) # Administrativo tiene rol para grupales
    fake_cursor_patch_grup = FakeCursor(
        fetchone_results=[{"id": 20}]
    )
    fake_conn_patch_grup = FakeConnection(fake_cursor_patch_grup)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_conn_patch_grup)

    response = client.patch(
        "/api/turnos/grupales/20/ausencia",
        json={"ausencia": "con_aviso"}
    )
    assert response.status_code == 200
    update_queries_grup = [item for item in fake_cursor_patch_grup.executed if "UPDATE turnos_grupales SET" in item[0]]
    assert len(update_queries_grup) == 1
    assert "ausencia" in update_queries_grup[0][0]
    assert "estado_asistencia" in update_queries_grup[0][0]
    assert update_queries_grup[0][1] == ("con_aviso", "con_aviso", 20)

    # 3. Test GET /api/pacientes/10/ausencias
    fake_cursor_count = FakeCursor(
        fetchone_results=[{"id": 10}],
        fetchall_results=[
            [{"ausencia": "sin_aviso", "cant": 2}, {"ausencia": "con_aviso", "cant": 1}], # indiv
            [{"ausencia": "sin_aviso", "cant": 1}] # grup
        ]
    )
    fake_conn_count = FakeConnection(fake_cursor_count)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_conn_count)

    response = client.get("/api/pacientes/10/ausencias")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 4
    assert data["sin_aviso"] == 3
    assert data["con_aviso"] == 1


def test_actualizar_ausencia_turno_ajeno_devuelve_403(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    from app.routes import turnos_routes

    # El turno 15 pertenece al profesional 99, no al usuario logueado (7)
    fake_cursor = FakeCursor(fetchone_results=[{"usuario_id": 99}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)

    response = client.patch(
        "/api/turnos/15/ausencia",
        json={"ausencia": "sin_aviso"}
    )

    assert response.status_code == 403
    update_queries = [item for item in fake_cursor.executed if "UPDATE turnos SET" in item[0]]
    assert len(update_queries) == 0


def test_actualizar_ausencia_turno_propio_devuelve_200(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    from app.routes import turnos_routes

    fake_cursor = FakeCursor(fetchone_results=[{"usuario_id": 7}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)

    response = client.patch(
        "/api/turnos/15/ausencia",
        json={"ausencia": "sin_aviso"}
    )

    assert response.status_code == 200


def test_conteo_ausencias_paciente_deniega_rol_no_reconocido(client):
    login_as(client, MockUser(user_id=1, rol="invitado"))

    response = client.get("/api/pacientes/10/ausencias")

    assert response.status_code == 403


def test_crear_turno_registra_quien_lo_cargo_y_cuando(client, monkeypatch):
    # El administrativo 42 carga un turno para el profesional 7: creado_por debe ser
    # 42 (quien lo cargo), NO 7 (el dueño de la agenda).
    login_as(client, MockUser(user_id=42, rol="administrativo"))

    fake_cursor = FakeCursor(fetchone_results=[None, None])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *args, **kwargs: True)

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

    assert response.status_code == 201
    inserts = [item for item in fake_cursor.executed if "INSERT INTO turnos" in item[0]]
    assert len(inserts) == 1
    query, params = inserts[0]
    assert "creado_por" in query
    assert "creado_en" in query
    # creado_por = usuario logueado (42), distinto del profesional del turno (7)
    assert params[6] == 42
    assert params[1] == 7
    assert isinstance(params[7], datetime)


def test_crear_ausencia_registra_quien_la_cargo_y_cuando(client, monkeypatch):
    # El administrativo 42 bloquea la agenda del profesional 7.
    login_as(client, MockUser(user_id=42, rol="administrativo"))

    fake_cursor = FakeCursor(fetchone_results=[None], lastrowid=5)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(ausencias_routes, "get_connection", lambda: fake_connection)

    response = client.post(
        "/api/ausencias",
        json={
            "usuario_id": 7,
            "fecha_inicio": "2026-03-26T09:00:00",
            "fecha_fin": "2026-03-26T12:00:00",
            "motivo": "Capacitacion",
        },
    )

    assert response.status_code == 201
    inserts = [item for item in fake_cursor.executed if "INSERT INTO ausencias" in item[0]]
    assert len(inserts) == 1
    query, params = inserts[0]
    assert "creado_en" in query
    # usuario_id = dueño de la agenda (7); creado_por = quien la bloqueo (42)
    assert params[0] == 7
    assert params[4] == 42
    assert isinstance(params[5], datetime)


def test_editar_turno_error_en_update_hace_rollback_cierra_y_retorna_500(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    fake_cursor = FakeCursor(
        fetchone_results=[{"usuario_id": 7}],
        execute_side_effects=[None, RuntimeError("update turno failed")],
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *args, **kwargs: True)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", False)

    response = client.put(
        "/api/turnos/15",
        json={
            "fecha_inicio": "2026-03-20T10:00:00",
            "fecha_fin": "2026-03-20T10:30:00",
            "motivo": "Control",
        },
    )

    assert response.status_code == 500
    assert fake_connection.rolled_back is True, "debe hacer rollback si falla el UPDATE"
    assert fake_cursor.closed is True
    assert fake_connection.closed is True, "la conexion debe cerrarse siempre, incluso con error"


def test_editar_turno_error_en_update_propaga_y_cierra_conexion(client, monkeypatch):
    login_as(client, MockUser(user_id=7, rol="profesional"))

    fake_cursor = FakeCursor(
        fetchone_results=[{"usuario_id": 7}],
        execute_side_effects=[None, RuntimeError("update turno failed")],
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(turnos_routes, "medico_disponible", lambda *args, **kwargs: True)
    monkeypatch.setitem(client.application.config, "PROPAGATE_EXCEPTIONS", True)

    with pytest.raises(RuntimeError, match="update turno failed"):
        client.put(
            "/api/turnos/15",
            json={
                "fecha_inicio": "2026-03-20T10:00:00",
                "fecha_fin": "2026-03-20T10:30:00",
                "motivo": "Control",
            },
        )

    assert fake_connection.rolled_back is True
    assert fake_cursor.closed is True
    assert fake_connection.closed is True, "la conexion debe cerrarse siempre, incluso con error"


def test_historial_turnos_paciente_devuelve_lista_unificada(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="administrativo"))

    now = datetime(2026, 8, 21, 10, 0, 0)
    fake_cursor = FakeCursor(
        fetchone_results=[{"id": 10}],  # paciente existe
        fetchall_results=[
            [
                {
                    "id": 1,
                    "tipo": "individual",
                    "start": now,
                    "end": now,
                    "description": "Control",
                    "observaciones": "Ninguna",
                    "ausencia": None,
                    "profesional": "Dr. Perez",
                    "creado_por_nombre": "Admin",
                    "creado_en": now,
                }
            ],
            [
                {
                    "id": 2,
                    "tipo": "grupal",
                    "start": now,
                    "end": now,
                    "description": "Rehab",
                    "observaciones": "Grupo 1",
                    "ausencia": "con_aviso",
                    "profesional": "Grupo: Kinesiologia",
                    "creado_por_nombre": "Admin",
                    "creado_en": now,
                }
            ],
        ],
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_connection)

    response = client.get("/api/pacientes/10/turnos")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    types = [t["tipo"] for t in data]
    assert "individual" in types
    assert "grupal" in types


def test_actualizar_asistencia_presente_y_presentes_hoy(client, monkeypatch):
    from app.routes import turnos_routes
    import datetime

    login_as(client, MockUser(user_id=7, rol="profesional"))

    # 1. Test PATCH /api/turnos/15/asistencia con estado_asistencia = presente
    fake_cursor_patch = FakeCursor(
        fetchone_results=[{"usuario_id": 7}]
    )
    fake_conn_patch = FakeConnection(fake_cursor_patch)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_conn_patch)

    response = client.patch(
        "/api/turnos/15/asistencia",
        json={"estado_asistencia": "presente"}
    )
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["estado_asistencia"] == "presente"
    assert res_data["ausencia"] is None

    update_queries = [item for item in fake_cursor_patch.executed if "UPDATE turnos SET" in item[0]]
    assert len(update_queries) == 1
    assert update_queries[0][1] == (None, "presente", 15)

    # 2. Test GET /api/turnos/presentes-hoy
    now = datetime.datetime.now()
    fake_cursor_presentes = FakeCursor(
        fetchall_results=[
            [
                {
                    "id": 15,
                    "paciente_id": 10,
                    "fecha_inicio": now,
                    "fecha_fin": now,
                    "motivo": "Control",
                    "observaciones": "Paciente en sala",
                    "estado_asistencia": "presente",
                    "ausencia": None,
                    "usuario_id": 7,
                    "paciente": "Carlos Gomez",
                    "dni": "12345678",
                    "profesional": "Dr. Perez"
                }
            ]
        ]
    )
    fake_conn_presentes = FakeConnection(fake_cursor_presentes)
    monkeypatch.setattr(turnos_routes, "get_connection", lambda: fake_conn_presentes)

    response = client.get("/api/turnos/presentes-hoy")
    assert response.status_code == 200
    presentes = response.get_json()
    assert len(presentes) == 1
    assert presentes[0]["id"] == 15
    assert presentes[0]["estado_asistencia"] == "presente"
    assert presentes[0]["paciente"] == "Carlos Gomez"

