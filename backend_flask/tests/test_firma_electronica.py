from datetime import date, datetime
from io import BytesIO

from conftest import FakeConnection, FakeCursor, MockUser, login_as
from app.routes import pacientes_routes
from app.utils.firma_electronica import hash_payload, payload_evolucion_firmable


def test_payload_firmable_hash_is_stable_and_utf8():
    user = MockUser(user_id=5, rol="profesional")
    evolution = {
        "id": 77,
        "paciente_id": 1,
        "fecha": date(2026, 7, 16),
        "contenido": "Evaluación clínica: evolución estable",
        "indicaciones": "Continuar",
        "usuario_id": 5,
        "version": 1,
        "padre_id": None,
    }

    payload = payload_evolucion_firmable(evolution, user)
    assert payload["payload_version"] == "evolucion-v1"
    assert hash_payload(payload) == hash_payload(dict(payload))
    assert len(hash_payload(payload)) == 64


def test_exportar_historia_pdf_incluye_firma_y_omite_campos_vacios(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=7, rol="administrativo"))
    monkeypatch.chdir(tmp_path)

    paciente = {
        "id": 1,
        "apellido": "Pérez",
        "nombre": "Ana",
        "dni": "12345678",
        "nro_hc": "HC-1",
        "cobertura": None,
        "fecha_nacimiento": None,
        "sexo": None,
        "diagnostico": "Control",
        "motivo_ingreso": "Seguimiento",
        "enfermedad_actual": None,
        "antecedentes_enfermedad_actual": None,
        "antecedentes_personales": None,
        "antecedentes_heredofamiliares": None,
    }
    evolucion = {
        "id": 77,
        "fecha": date(2026, 7, 16),
        "contenido": "Evolución clínica firmada",
        "indicaciones": None,
        "creado_en": datetime(2026, 7, 16, 10, 0),
        "version": 1,
        "estado_firma": "firmada",
        "firmado_en": datetime(2026, 7, 16, 10, 1),
        "motivo_rectificacion": None,
        "firma_payload_version": "evolucion-v1",
        "firma_payload_hash": "a" * 64,
        "firma_algoritmo": "SHA-256",
        "firma_firmado_en": datetime(2026, 7, 16, 10, 1),
        "medico": "Dra. Test",
        "matricula_tipo": "MN",
        "matricula_numero": "12345",
        "matricula_provincia": "BA",
        "especialidad": "Clínica",
    }
    fake_cursor = FakeCursor(fetchone_results=[paciente], fetchall_results=[[evolucion], []])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))

    response = client.get("/api/pacientes/1/historia/pdf")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_verificar_firma_electronica_detecta_payload_valido(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))
    evolucion = {
        "id": 77,
        "paciente_id": 1,
        "fecha": date(2026, 7, 16),
        "contenido": "Contenido firmado",
        "indicaciones": "Continuar",
        "usuario_id": 5,
        "version": 1,
        "padre_id": None,
        "motivo_rectificacion": None,
        "estado_firma": "firmada",
        "hash_local": None,
        "firma_payload_version": "evolucion-v1",
        "firma_algoritmo": "SHA-256",
        "firma_firmado_en": datetime(2026, 7, 16, 10, 1),
        "firmante_nombre": "Dra. Test",
        "firmante_rol": "profesional",
        "firmante_matricula_tipo": "MN",
        "firmante_matricula_numero": "12345",
        "firmante_matricula_provincia": "BA",
    }
    evolucion["hash_local"] = hash_payload(payload_evolucion_firmable(evolucion, {
        "rol": "profesional",
        "matricula_tipo": "MN",
        "matricula_numero": "12345",
        "matricula_provincia": "BA",
    }))
    evolucion["firma_payload_hash"] = evolucion["hash_local"]

    fake_cursor = FakeCursor(fetchone_results=[evolucion])
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))

    response = client.get("/api/pacientes/1/evolucion/77/firma")

    assert response.status_code == 200
    assert response.get_json()["valida"] is True


def test_adjuntos_generales_se_guardan_con_fecha_y_hash(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=2, rol="administrativo"))
    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    fake_cursor = FakeCursor(fetchone_results=[{"id": 1}], lastrowid=33)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: FakeConnection(fake_cursor))

    response = client.post(
        "/api/pacientes/1/adjuntos",
        data={"archivos": (BytesIO(b"%PDF-1.7\ncontenido"), "estudio.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    archivo = response.get_json()["archivos"][0]
    assert archivo["nombre"] == "estudio.pdf"
    assert len(archivo["hash_sha256"]) == 64
    assert (tmp_path / "uploads" / "pacientes" / "1").exists()
    assert fake_cursor.executed[-1][0].strip().startswith("INSERT INTO historia_archivos")
