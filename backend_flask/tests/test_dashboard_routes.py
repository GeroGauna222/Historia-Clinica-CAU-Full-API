from datetime import datetime, timedelta

from conftest import FakeConnection, FakeCursor, MockUser, login_as
from app.routes import dashboard_routes


def test_dashboard_profesional_incluye_evento_y_comunicados_de_grupo(client, monkeypatch):
    inicio = datetime.now() + timedelta(hours=2)
    fin = inicio + timedelta(minutes=30)
    fake_cursor = FakeCursor(
        fetchone_results=[
            {
                "id": 10,
                "fecha_inicio": inicio,
                "fecha_fin": fin,
                "motivo": "Control",
                "paciente_id": 22,
                "paciente": "Ana",
                "apellido": "Perez",
                "profesional": "Dra Test",
            },
            None,
        ],
        fetchall_results=[
            [
                {
                    "id": 10,
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "motivo": "Control",
                    "paciente_id": 22,
                    "paciente": "Ana",
                    "apellido": "Perez",
                    "profesional": "Dra Test",
                }
            ],
            [{"id": 1, "usuario_id": 7, "dia_semana": "Viernes", "hora_inicio": "09:00", "hora_fin": "13:00", "activo": 1}],
            [],
            [{"id": 1, "origen": "institucional", "titulo": "Aviso", "contenido": "Texto", "creado_en": inicio, "autor_nombre": "Admin", "grupo_id": None, "grupo_nombre": None}],
            [{"id": 4, "origen": "grupo", "titulo": "Grupo", "contenido": "Posteo", "creado_en": fin, "autor_nombre": "Area", "grupo_id": 9, "grupo_nombre": "RHB"}],
        ],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(7, "profesional", nombre="Dra Test"))

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    assert data["resumen"]["turnos_hoy"] == 1
    assert data["proximo_evento"]["tipo"] == "Turno"
    assert data["proximo_evento"]["paciente_id"] == 22
    assert [c["origen"] for c in data["comunicados"]] == ["grupo", "institucional"]
    assert "pacientes" not in data["estadisticas"]


def test_dashboard_admin_incluye_alertas_operativas(client, monkeypatch):
    inicio = datetime.now() + timedelta(hours=1)
    fin = inicio + timedelta(minutes=30)
    fake_cursor = FakeCursor(
        fetchone_results=[None, {"id": 30, "usuario_id": 8, "fecha_inicio": inicio, "fecha_fin": fin, "motivo": "[Reunion] Equipo", "profesional": "Lic Test"}],
        fetchall_results=[
            [],
            [{"id": 2, "usuario_id": 8, "profesional": "Lic Test", "dia_semana": "Viernes", "hora_inicio": "10:00", "hora_fin": "12:00", "activo": 1}],
            [{"id": 30, "usuario_id": 8, "fecha_inicio": inicio, "fecha_fin": fin, "motivo": "[Reunion] Equipo", "profesional": "Lic Test"}],
            [
                {
                    "turno_id": 1,
                    "turno_solapado_id": 2,
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "fecha_inicio_solapada": inicio + timedelta(minutes=10),
                    "fecha_fin_solapada": fin + timedelta(minutes=10),
                    "usuario_id": 8,
                    "profesional": "Lic Test",
                    "paciente": "Ana Perez",
                    "paciente_solapado": "Luis Gomez",
                }
            ],
            [{"usuario_id": 9, "profesional": "Dra Libre", "hora_inicio": "09:00", "hora_fin": "11:00"}],
            [],
            [],
        ],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "director", nombre="Direccion"))

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    assert data["proximo_evento"]["tipo"] == "Reunion"
    assert data["proximo_evento"]["detalle"] == "Equipo"
    assert data["resumen"]["turnos_superpuestos"] == 1
    assert "agenda_vacia" not in data["resumen"]
    assert data["alertas"]["agenda_vacia"][0]["profesional"] == "Dra Libre"
    assert "ausencias_bloqueos" not in data["resumen"]
    assert data["ausencias_bloqueos"][0]["tipo_evento"] == "Reunion"


def test_dashboard_profesional_destaca_paciente_en_curso_presente(client, monkeypatch):
    hoy = datetime.now()
    inicio1 = hoy.replace(hour=9, minute=0, second=0, microsecond=0)
    fin1 = inicio1 + timedelta(minutes=30)
    inicio2 = hoy.replace(hour=9, minute=30, second=0, microsecond=0)
    fin2 = inicio2 + timedelta(minutes=30)

    fake_cursor = FakeCursor(
        fetchone_results=[
            {
                "id": 12,
                "fecha_inicio": inicio2 + timedelta(hours=1),
                "fecha_fin": fin2 + timedelta(hours=1),
                "motivo": "Control anual",
                "observaciones": "Paciente puntual",
                "estado_asistencia": "programado",
                "ausencia": None,
                "paciente_id": 25,
                "paciente": "Carlos",
                "apellido": "Lopez",
                "dni": "30111222",
                "nro_hc": "HC-0042",
                "cobertura": "OSDE 210",
                "telefono": "1123456789",
                "celular": "1198765432",
                "profesional": "Lic Gomez",
            },
            None,
        ],
        fetchall_results=[
            [
                {
                    "id": 10,
                    "fecha_inicio": inicio1,
                    "fecha_fin": fin1,
                    "motivo": "Evaluacion",
                    "observaciones": "Primera consulta",
                    "estado_asistencia": "presente",
                    "atencion_inicio": inicio1 + timedelta(minutes=5),
                    "atencion_fin": None,
                    "ahora_db": inicio1 + timedelta(minutes=10),
                    "ausencia": None,
                    "paciente_id": 20,
                    "paciente": "Maria",
                    "apellido": "Paz",
                    "dni": "28333444",
                    "nro_hc": "HC-0010",
                    "cobertura": "Swiss Medical",
                    "telefono": "1155554444",
                    "celular": "1166667777",
                    "profesional": "Lic Gomez",
                },
                {
                    "id": 11,
                    "fecha_inicio": inicio2,
                    "fecha_fin": fin2,
                    "motivo": "Seguimiento",
                    "observaciones": None,
                    "estado_asistencia": "programado",
                    "ausencia": None,
                    "paciente_id": 21,
                    "paciente": "Juan",
                    "apellido": "Rios",
                    "dni": "32444555",
                    "nro_hc": "HC-0011",
                    "cobertura": "Particular",
                    "telefono": None,
                    "celular": "1177778888",
                    "profesional": "Lic Gomez",
                }
            ],
            [{"id": 1, "usuario_id": 5, "dia_semana": "Lunes", "hora_inicio": "09:00", "hora_fin": "13:00", "activo": 1}],
            [],
            [],
            [],
        ],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(5, "profesional", nombre="Lic Gomez"))

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.get_json()

    assert data["turno_en_curso"] is not None
    assert data["turno_en_curso"]["id"] == 10
    assert data["turno_en_curso"]["paciente"] == "Maria"
    assert data["turno_en_curso"]["estado_asistencia"] == "presente"
    assert data["turno_en_curso"]["dni"] == "28333444"
    assert data["turno_en_curso"]["nro_hc"] == "HC-0010"
    assert data["turno_en_curso"]["cobertura"] == "Swiss Medical"
    assert len(data["atenciones_en_curso"]) == 1
    assert data["atenciones_en_curso"][0]["id"] == 10

    assert data["proximo_evento"]["id"] == 12
    assert data["proximo_evento"]["paciente"] == "Carlos"
    assert data["proximo_evento"]["nro_hc"] == "HC-0042"


def test_dashboard_director_retorna_multiples_atenciones_en_curso(client, monkeypatch):
    hoy = datetime.now()
    inicio1 = hoy.replace(hour=10, minute=0, second=0, microsecond=0)
    fin1 = inicio1 + timedelta(minutes=30)
    inicio2 = hoy.replace(hour=10, minute=0, second=0, microsecond=0)
    fin2 = inicio2 + timedelta(minutes=30)

    turnos_db = [
        {
            "id": 101,
            "fecha_inicio": inicio1,
            "fecha_fin": fin1,
            "motivo": "Cardiología",
            "observaciones": None,
            "estado_asistencia": "presente",
            "atencion_inicio": inicio1 + timedelta(minutes=2),
            "atencion_fin": None,
            "ahora_db": inicio1 + timedelta(minutes=10),
            "ausencia": None,
            "es_sobreturno": 0,
            "paciente_id": 1,
            "paciente": "Juan",
            "apellido": "Perez",
            "dni": "11111111",
            "nro_hc": "HC-1",
            "cobertura": "OSDE",
            "profesional": "Dr Gomez",
        },
        {
            "id": 102,
            "fecha_inicio": inicio2,
            "fecha_fin": fin2,
            "motivo": "Traumatología",
            "observaciones": None,
            "estado_asistencia": "presente",
            "atencion_inicio": inicio2 + timedelta(minutes=5),
            "atencion_fin": None,
            "ahora_db": inicio2 + timedelta(minutes=10),
            "ausencia": None,
            "es_sobreturno": 0,
            "paciente_id": 2,
            "paciente": "Ana",
            "apellido": "Lopez",
            "dni": "22222222",
            "nro_hc": "HC-2",
            "cobertura": "Swiss Medical",
            "profesional": "Dra Diaz",
        }
    ]

    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[
            turnos_db,
            [],
            [],
            [],
            [],
            [],
            [],
        ],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "director", nombre="Director General"))

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.get_json()

    assert len(data["atenciones_en_curso"]) == 2
    assert data["atenciones_en_curso"][0]["profesional"] == "Dr Gomez"
    assert data["atenciones_en_curso"][1]["profesional"] == "Dra Diaz"
    assert data["turno_en_curso"]["id"] == 102


def test_dashboard_profesional_calcula_turnos_superpuestos(client, monkeypatch):
    hoy = datetime.now()
    inicio = hoy.replace(hour=11, minute=0, second=0, microsecond=0)
    fin = inicio + timedelta(minutes=30)

    turnos_prof = [
        {
            "id": 201,
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "motivo": "Control",
            "observaciones": None,
            "estado_asistencia": "programado",
            "ausencia": None,
            "es_sobreturno": 0,
            "paciente_id": 1,
            "paciente": "Carlos",
            "apellido": "Gardel",
            "dni": "12345678",
            "nro_hc": "HC-1",
            "cobertura": "OSDE",
            "profesional": "Dr Gauna",
        },
        {
            "id": 202,
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "motivo": "Urgencia",
            "observaciones": None,
            "estado_asistencia": "programado",
            "ausencia": None,
            "es_sobreturno": 1,
            "paciente_id": 2,
            "paciente": "Marta",
            "apellido": "Sanchez",
            "dni": "87654321",
            "nro_hc": "HC-2",
            "cobertura": "PAMI",
            "profesional": "Dr Gauna",
        },
    ]

    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[
            turnos_prof,
            [],
            [],
            [],
            [],
        ],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(2, "profesional", nombre="Dr Gauna"))

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.get_json()

    assert data["resumen"]["turnos_hoy"] == 2
    assert data["resumen"]["turnos_superpuestos"] == 1
    assert len(data["alertas"]["turnos_superpuestos"]) == 1
    assert data["alertas"]["turnos_superpuestos"][0]["turno_id"] == 201
    assert data["alertas"]["turnos_superpuestos"][0]["turno_solapado_id"] == 202


def test_dashboard_director_una_atencion_por_profesional_si_hay_multiples_presentes(client, monkeypatch):
    hoy = datetime.now()
    inicio1 = hoy.replace(hour=9, minute=0, second=0, microsecond=0)
    fin1 = inicio1 + timedelta(minutes=30)
    inicio2 = hoy.replace(hour=10, minute=0, second=0, microsecond=0)
    fin2 = inicio2 + timedelta(minutes=30)

    turnos_db = [
        {
            "id": 301,
            "usuario_id": 10,
            "fecha_inicio": inicio1,
            "fecha_fin": fin1,
            "motivo": "Control inicial",
            "observaciones": None,
            "estado_asistencia": "presente",
            "atencion_inicio": inicio1 + timedelta(minutes=2),
            "atencion_fin": inicio1 + timedelta(minutes=25),
            "ahora_db": inicio2 + timedelta(minutes=10),
            "ausencia": None,
            "es_sobreturno": 0,
            "paciente_id": 1,
            "paciente": "Juan",
            "apellido": "Perez",
            "dni": "11111111",
            "nro_hc": "HC-1",
            "cobertura": "OSDE",
            "profesional": "Dr Gomez",
            "es_grupal": 0,
            "grupo_id": None,
            "grupo_nombre": None,
        },
        {
            "id": 302,
            "usuario_id": 10,
            "fecha_inicio": inicio2,
            "fecha_fin": fin2,
            "motivo": "Control siguiente",
            "observaciones": None,
            "estado_asistencia": "presente",
            "atencion_inicio": inicio2 + timedelta(minutes=3),
            "atencion_fin": None,
            "ahora_db": inicio2 + timedelta(minutes=10),
            "ausencia": None,
            "es_sobreturno": 0,
            "paciente_id": 2,
            "paciente": "Carlos",
            "apellido": "Lopez",
            "dni": "22222222",
            "nro_hc": "HC-2",
            "cobertura": "PAMI",
            "profesional": "Dr Gomez",
            "es_grupal": 0,
            "grupo_id": None,
            "grupo_nombre": None,
        },
    ]

    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[
            turnos_db,
            [],
            [],
            [],
            [],
            [],
            [],
        ],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "director", nombre="Director General"))

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.get_json()

    # Even though Dr Gomez has 2 turnos marked presente, director only gets the latest active attention for Dr Gomez
    assert len(data["atenciones_en_curso"]) == 1
    assert data["atenciones_en_curso"][0]["id"] == 302
    assert data["atenciones_en_curso"][0]["profesional"] == "Dr Gomez"
    assert data["turno_en_curso"]["id"] == 302


def test_dashboard_director_incluye_turnos_grupales(client, monkeypatch):
    hoy = datetime.now()
    inicio = hoy.replace(hour=11, minute=0, second=0, microsecond=0)
    fin = inicio + timedelta(minutes=45)

    turnos_db = [
        {
            "id": 50,
            "usuario_id": None,
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "motivo": "Taller postural",
            "observaciones": None,
            "estado_asistencia": "presente",
            "atencion_inicio": inicio + timedelta(minutes=5),
            "atencion_fin": None,
            "ahora_db": inicio + timedelta(minutes=10),
            "ausencia": None,
            "es_sobreturno": 0,
            "paciente_id": 5,
            "paciente": "Marta",
            "apellido": "Rios",
            "dni": "33333333",
            "nro_hc": "HC-5",
            "cobertura": "Particular",
            "profesional": "Grupo: Kinesiología",
            "es_grupal": 1,
            "grupo_id": 3,
            "grupo_nombre": "Kinesiología",
        }
    ]

    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[
            turnos_db,
            [],
            [],
            [],
            [],
            [],
            [],
        ],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "director", nombre="Director General"))

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.get_json()

    assert len(data["turnos"]) == 1
    turno = data["turnos"][0]
    assert turno["id"] == "grupal-50"
    assert turno["turnoId"] == 50
    assert turno["es_grupal"] is True
    assert turno["es_sobreturno"] is False
    assert turno["grupo_nombre"] == "Kinesiología"

    assert len(data["atenciones_en_curso"]) == 1
    assert data["atenciones_en_curso"][0]["id"] == "grupal-50"


def test_primer_evento_soporta_datetime_y_str():
    from app.routes.dashboard_routes import _primer_evento
    from datetime import datetime

    # Turno previamente normalizado (fecha_inicio es str)
    turno = {
        "id": 10,
        "paciente": "Juan",
        "apellido": "Perez",
        "fecha_inicio": "2026-11-06T15:00:00",
        "motivo": "Consulta general",
    }
    # Ausencia proveniente directa de MySQL (fecha_inicio es datetime)
    ausencia = {
        "id": 5,
        "usuario_id": 2,
        "fecha_inicio": datetime(2026, 11, 6, 12, 0, 0),
        "motivo": "[Congreso] Pediatria",
    }

    evento = _primer_evento(turno, ausencia)
    assert evento is not None
    # La ausencia es a las 12:00, el turno a las 15:00 -> la ausencia debe ser el primer evento
    assert evento["tipo"] == "Congreso"
    assert evento["fecha_inicio"] == "2026-11-06T12:00:00"


def test_atenciones_en_curso_solo_incluye_turnos_en_atencion_ordenados():
    turnos = [
        {"id": 1, "estado_atencion": "esperando", "atencion_inicio": None},
        {"id": 2, "estado_atencion": "en_atencion", "atencion_inicio": "2026-11-16T10:20:00"},
        {"id": 3, "estado_atencion": "atendido", "atencion_inicio": "2026-11-16T09:00:00"},
        {"id": 4, "estado_atencion": "en_atencion", "atencion_inicio": "2026-11-16T10:05:00"},
    ]
    en_curso = dashboard_routes._atenciones_en_curso(turnos)
    assert [t["id"] for t in en_curso] == [4, 2]


def test_atenciones_en_curso_vacio_si_nadie_fue_llamado():
    assert dashboard_routes._atenciones_en_curso([{"id": 1, "estado_atencion": "esperando"}]) == []
    assert dashboard_routes._atenciones_en_curso([]) == []


def _turno_fila(id_, inicio, estado, **extra):
    fila = {
        "id": id_,
        "fecha_inicio": inicio,
        "fecha_fin": inicio + timedelta(minutes=30),
        "motivo": "Control",
        "observaciones": None,
        "estado_asistencia": estado,
        "ausencia": None,
        "es_sobreturno": 0,
        "paciente_id": id_,
        "paciente": "Pac",
        "apellido": f"N{id_}",
        "dni": "1",
        "nro_hc": "HC",
        "cobertura": "OSDE",
        "profesional": "Dr Gomez",
        "es_grupal": 0,
        "grupo_id": None,
        "grupo_nombre": None,
    }
    fila.update(extra)
    return fila


def test_dashboard_profesional_presente_sin_llamar_no_tiene_turno_en_curso(client, monkeypatch):
    inicio = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    fila = _turno_fila(10, inicio, "presente", atencion_inicio=None, atencion_fin=None,
                       ahora_db=inicio + timedelta(minutes=10))
    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[[fila], [], [], [], []],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(5, "profesional", nombre="Lic Gomez"))

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    assert data["turno_en_curso"] is None
    assert data["atenciones_en_curso"] == []
    assert data["turnos"][0]["estado_atencion"] == "esperando"


def test_dashboard_profesional_turnos_llevan_estado_atencion_y_no_filtran_ahora_db(client, monkeypatch):
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    ahora = base + timedelta(hours=2)
    filas = [
        _turno_fila(1, base, "presente", atencion_inicio=base + timedelta(minutes=1),
                    atencion_fin=base + timedelta(minutes=20), ahora_db=ahora),
        _turno_fila(2, base + timedelta(minutes=30), "presente",
                    atencion_inicio=ahora - timedelta(minutes=5), atencion_fin=None, ahora_db=ahora),
        _turno_fila(3, base + timedelta(hours=1), "presente",
                    atencion_inicio=None, atencion_fin=None, ahora_db=ahora),
        _turno_fila(4, base + timedelta(hours=3), "programado",
                    atencion_inicio=None, atencion_fin=None, ahora_db=ahora),
    ]
    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[filas, [], [], [], []],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(5, "profesional", nombre="Lic Gomez"))

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    estados = {t["turnoId"]: t["estado_atencion"] for t in data["turnos"]}
    assert estados == {1: "atendido", 2: "en_atencion", 3: "esperando", 4: None}
    assert all("ahora_db" not in t for t in data["turnos"])
    assert [t["id"] for t in data["atenciones_en_curso"]] == [2]
    assert data["turno_en_curso"]["id"] == 2
    assert data["turno_en_curso"]["estado_atencion"] == "en_atencion"


def test_dashboard_director_en_curso_sale_de_turnos_en_atencion(client, monkeypatch):
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    ahora = base + timedelta(hours=2)
    filas = [
        _turno_fila(1, base, "presente", usuario_id=10, profesional="Dr Gomez",
                    atencion_inicio=base + timedelta(minutes=1),
                    atencion_fin=base + timedelta(minutes=20), ahora_db=ahora),
        _turno_fila(2, base + timedelta(minutes=30), "presente", usuario_id=11, profesional="Dra Diaz",
                    atencion_inicio=ahora - timedelta(minutes=5), atencion_fin=None, ahora_db=ahora),
        _turno_fila(3, base + timedelta(hours=1), "presente", usuario_id=10, profesional="Dr Gomez",
                    atencion_inicio=None, atencion_fin=None, ahora_db=ahora),
    ]
    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[filas, [], [], [], [], [], []],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "director", nombre="Director General"))

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    estados = {t["turnoId"]: t["estado_atencion"] for t in data["turnos"]}
    assert estados == {1: "atendido", 2: "en_atencion", 3: "esperando"}
    assert all("ahora_db" not in t for t in data["turnos"])
    assert [t["id"] for t in data["atenciones_en_curso"]] == [2]
    assert data["turno_en_curso"]["id"] == 2


def test_dashboard_director_grupal_cerrado_no_figura_en_curso(client, monkeypatch):
    inicio = datetime.now().replace(hour=11, minute=0, second=0, microsecond=0)
    fila = _turno_fila(50, inicio, "presente", usuario_id=None, profesional="Grupo: Kine",
                       es_grupal=1, grupo_id=3, grupo_nombre="Kine",
                       atencion_inicio=inicio + timedelta(minutes=5), atencion_fin=None,
                       ahora_db=inicio + timedelta(minutes=40))
    fake_cursor = FakeCursor(
        fetchone_results=[None, None],
        fetchall_results=[[fila], [], [], [], [], [], []],
    )
    monkeypatch.setattr(dashboard_routes, "get_connection", lambda: FakeConnection(fake_cursor))
    login_as(client, MockUser(1, "director", nombre="Director General"))

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    assert data["turnos"][0]["estado_atencion"] == "atendido"
    assert data["atenciones_en_curso"] == []
    assert data["turno_en_curso"] is None
