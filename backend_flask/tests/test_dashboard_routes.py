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
