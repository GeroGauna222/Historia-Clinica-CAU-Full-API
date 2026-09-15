from io import BytesIO

from conftest import FakeConnection, FakeCursor, MockUser, login_as
from app.routes import pacientes_routes


def test_agregar_evolucion_rechaza_roles_no_clinicos(client, monkeypatch):
    login_as(client, MockUser(user_id=2, rol="administrativo"))
    response = client.post(
        "/api/pacientes/1/evolucion",
        data={"fecha": "2026-07-16", "contenido": "No debe guardarse", "confirmar_firma": "true"},
    )

    assert response.status_code == 403


def test_agregar_evolucion_permite_matricula_cargada_aunque_no_este_verificada(client, monkeypatch, tmp_path):
    user = MockUser(user_id=5, rol="profesional")
    user.matricula_verificada = False
    login_as(client, user)
    monkeypatch.chdir(tmp_path)
    fake_cursor = FakeCursor(lastrowid=77)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(pacientes_routes, "actualizar_historia", lambda paciente_id, usuario_id: "historia-hash")

    response = client.post(
        "/api/pacientes/1/evolucion",
        data={"fecha": "2026-07-16", "contenido": "Debe guardarse", "confirmar_firma": "true"},
    )

    assert response.status_code == 200
    assert response.get_json()["estado_firma"] == "firmada"


def test_agregar_evolucion_rechaza_profesional_sin_matricula(client):
    user = MockUser(user_id=5, rol="profesional")
    user.matricula_tipo = None
    user.matricula_numero = None
    login_as(client, user)

    response = client.post(
        "/api/pacientes/1/evolucion",
        data={"fecha": "2026-07-16", "contenido": "No debe guardarse", "confirmar_firma": "true"},
    )

    assert response.status_code == 422
    assert "matrícula" in response.get_json()["error"].lower()


def test_agregar_evolucion_firma_y_auditoria_en_una_transaccion(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=5, rol="profesional"))
    monkeypatch.chdir(tmp_path)
    fake_cursor = FakeCursor(lastrowid=77)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(pacientes_routes, "actualizar_historia", lambda paciente_id, usuario_id: "historia-hash")

    response = client.post(
        "/api/pacientes/1/evolucion",
        data={
            "fecha": "2026-07-16",
            "contenido": "Evolución firmada",
            "indicaciones": "Continuar control",
            "confirmar_firma": "true",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["estado_firma"] == "firmada"
    assert len(payload["hash_local"]) == 64
    assert fake_connection.committed is True
    queries = [query for query, _ in fake_cursor.executed]
    assert any("INSERT INTO firmas_electronicas" in query for query in queries)
    assert any("INSERT INTO auditorias_clinicas" in query for query in queries)
    assert any("estado_firma = 'firmada'" in query for query in queries)


def test_agregar_evolucion_rechaza_html_antes_de_abrir_transaccion(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    def fail_if_database_is_opened():
        raise AssertionError("an invalid attachment must be rejected before opening a transaction")

    monkeypatch.setattr(pacientes_routes, "get_connection", fail_if_database_is_opened)

    response = client.post(
        "/api/pacientes/1/evolucion",
        data={
            "fecha": "2026-07-16",
            "contenido": "Evolucion con adjunto inseguro",
            "confirmar_firma": "true",
            "archivos": (BytesIO(b"<script>alert(document.cookie)</script>"), "informe.html"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert "formato no permitido" in response.get_json()["error"].lower()


def test_agregar_evolucion_rechaza_html_disfrazado_de_pdf(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    def fail_if_database_is_opened():
        raise AssertionError("an invalid attachment must be rejected before opening a transaction")

    monkeypatch.setattr(pacientes_routes, "get_connection", fail_if_database_is_opened)

    response = client.post(
        "/api/pacientes/1/evolucion",
        data={
            "fecha": "2026-07-16",
            "contenido": "Evolucion con adjunto inseguro",
            "confirmar_firma": "true",
            "archivos": (BytesIO(b"<script>alert(1)</script>"), "informe.pdf", "application/pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert "no coincide con su formato" in response.get_json()["error"].lower()


def test_agregar_evolucion_rechaza_mime_incompatible_con_extension(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    def fail_if_database_is_opened():
        raise AssertionError("an invalid attachment must be rejected before opening a transaction")

    monkeypatch.setattr(pacientes_routes, "get_connection", fail_if_database_is_opened)

    response = client.post(
        "/api/pacientes/1/evolucion",
        data={
            "fecha": "2026-07-16",
            "contenido": "Evolucion con adjunto inconsistente",
            "confirmar_firma": "true",
            "archivos": (BytesIO(b"%PDF-1.7\ncontenido\n%%EOF"), "informe.pdf", "text/html"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert "tipo mime" in response.get_json()["error"].lower()


def test_agregar_evolucion_acepta_pdf_valido(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=5, rol="profesional"))
    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    fake_cursor = FakeCursor(lastrowid=77)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    monkeypatch.setattr(pacientes_routes, "actualizar_historia", lambda paciente_id, usuario_id: "historia-hash")

    response = client.post(
        "/api/pacientes/1/evolucion",
        data={
            "fecha": "2026-07-16",
            "contenido": "Evolucion con PDF valido",
            "confirmar_firma": "true",
            "archivos": (BytesIO(b"%PDF-1.7\ncontenido\n%%EOF"), "informe.pdf", "application/pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert (tmp_path / "uploads" / "evoluciones" / "77" / "informe.pdf").read_bytes().startswith(b"%PDF-")


def test_rectificacion_rechaza_svg_antes_de_abrir_transaccion(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    def fail_if_database_is_opened():
        raise AssertionError("an invalid attachment must be rejected before opening a transaction")

    monkeypatch.setattr(pacientes_routes, "get_connection", fail_if_database_is_opened)

    response = client.put(
        "/api/pacientes/1/evolucion/50",
        data={
            "fecha": "2026-07-16",
            "contenido": "Rectificacion",
            "motivo_rectificacion": "Correccion clinica",
            "archivos": (BytesIO(b"<svg onload='alert(1)'/>"), "placa.svg", "image/svg+xml"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert "formato no permitido" in response.get_json()["error"].lower()


def test_descarga_adjunto_legacy_fuerza_descarga_y_bloquea_sniffing(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=2, rol="administrativo"))
    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    upload_dir = tmp_path / "uploads" / "evoluciones" / "77"
    upload_dir.mkdir(parents=True)
    (upload_dir / "legacy.html").write_text("<script>alert(1)</script>", encoding="utf-8")

    response = client.get("/api/uploads/evoluciones/77/legacy.html")

    assert response.status_code == 200
    assert response.headers["Content-Disposition"].startswith("attachment;")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "sandbox" in response.headers["Content-Security-Policy"]

def test_editar_evolucion_sin_permisos_devuelve_403(client, monkeypatch):
    # Intentar editar con un profesional que no es el autor
    login_as(client, MockUser(user_id=9, rol="profesional"))

    # Mock de evolucion original: paciente_id=1, id=50, usuario_id=5 (otro profesional)
    evo_original = {
        'id': 50,
        'paciente_id': 1,
        'fecha': '2026-07-10',
        'contenido': 'Evolucion inicial',
        'indicaciones': 'Reposo',
        'usuario_id': 5,
        'padre_id': None,
        'version': 1,
        'activo': 1
    }

    # Fetchone devuelve la evolucion original
    fake_cursor = FakeCursor(fetchone_results=[evo_original])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)

    response = client.put(
        "/api/pacientes/1/evolucion/50",
        data={
            "fecha": "2026-07-16",
            "contenido": "Contenido editado",
            "indicaciones": "Nuevas indicaciones"
        }
    )

    assert response.status_code == 403
    assert "permisos" in response.get_json()["error"].lower()


def test_editar_evolucion_autor_ok_devuelve_200(client, monkeypatch):
    # Loguearse como el autor (user_id=5)
    login_as(client, MockUser(user_id=5, rol="profesional"))

    evo_original = {
        'id': 50,
        'paciente_id': 1,
        'fecha': '2026-07-10',
        'contenido': 'Evolucion inicial',
        'indicaciones': 'Reposo',
        'usuario_id': 5,
        'padre_id': None,
        'version': 1,
        'activo': 1
    }

    # fetchone_results:
    # 1. SELECT de la evolucion actual
    # 2. SELECT de la raiz bloqueada
    # 3. SELECT MAX(version)
    fake_cursor = FakeCursor(
        fetchone_results=[
            evo_original,
            {'id': 50},
            {'max_v': 1}
        ],
        fetchall_results=[[]] # No hay archivos adjuntos anteriores
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)
    
    # Mockear las funciones de hashing/blockchain para evitar fallos de conexion
    monkeypatch.setattr(pacientes_routes, "actualizar_hash_evolucion", lambda x: "hash-falso")
    monkeypatch.setattr(pacientes_routes, "actualizar_historia", lambda x, y: "hash-consolidado")

    response = client.put(
        "/api/pacientes/1/evolucion/50",
        data={
            "fecha": "2026-07-16",
            "contenido": "Contenido editado por el autor",
            "indicaciones": "Nuevas indicaciones del autor",
            "motivo_rectificacion": "Corrección de evolución",
            "confirmar_firma": "true",
        }
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "editada" in payload["message"].lower()
    assert fake_connection.committed is True

    # Verificar que se inserto el nuevo registro con version 2
    queries = [q for q, p in fake_cursor.executed]
    insert_query = [q for q in queries if "INSERT INTO evoluciones" in q][0]
    update_query = [q for q in queries if "UPDATE evoluciones" in q][0]

    assert insert_query is not None
    assert update_query is not None

    lock_index = next(i for i, query in enumerate(queries) if "FOR UPDATE" in query)
    max_version_index = next(i for i, query in enumerate(queries) if "MAX(version)" in query)
    assert lock_index < max_version_index
    assert "FOR UPDATE" in queries[max_version_index]


def test_editar_evolucion_director_ok_devuelve_200(client, monkeypatch):
    # Loguearse como Director (user_id=10, rol=director)
    login_as(client, MockUser(user_id=10, rol="director"))

    evo_original = {
        'id': 50,
        'paciente_id': 1,
        'fecha': '2026-07-10',
        'contenido': 'Evolucion inicial',
        'indicaciones': 'Reposo',
        'usuario_id': 5, # Escrita por otro profesional
        'padre_id': None,
        'version': 1,
        'activo': 1
    }

    fake_cursor = FakeCursor(
        fetchone_results=[
            evo_original,
            {'id': 50},
            {'max_v': 1}
        ],
        fetchall_results=[[]]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)

    # Mockear hashing
    monkeypatch.setattr(pacientes_routes, "actualizar_hash_evolucion", lambda x: "hash-falso")
    monkeypatch.setattr(pacientes_routes, "actualizar_historia", lambda x, y: "hash-consolidado")

    response = client.put(
        "/api/pacientes/1/evolucion/50",
        data={
            "fecha": "2026-07-16",
            "contenido": "Contenido editado por director",
            "indicaciones": "Nuevas indicaciones del director",
            "motivo_rectificacion": "Aclaración clínica",
            "confirmar_firma": "true",
        }
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "editada" in payload["message"].lower()
    assert fake_connection.committed is True


def test_get_historial_evolucion_retorna_secuencia(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol="profesional"))

    evo_original = {
        'id': 50,
        'padre_id': None
    }

    # Query de historial
    historial_versiones = [
        {
            'id': 50, 'fecha': '2026-07-10', 'contenido': 'Original', 'indicaciones': '',
            'creado_en': '2026-07-10 10:00:00', 'version': 1, 'activo': 0, 'nombre_usuario': 'Juan', 'especialidad_usuario': 'Cardiologo'
        },
        {
            'id': 51, 'fecha': '2026-07-16', 'contenido': 'Editado', 'indicaciones': '',
            'creado_en': '2026-07-16 10:00:00', 'version': 2, 'activo': 1, 'nombre_usuario': 'Juan', 'especialidad_usuario': 'Cardiologo'
        }
    ]

    fake_cursor = FakeCursor(
        fetchone_results=[evo_original],
        fetchall_results=[
            historial_versiones,
            [], # Archivos adjuntos para version 1
            []  # Archivos adjuntos para version 2
        ]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(pacientes_routes, "get_connection", lambda: fake_connection)

    response = client.get("/api/pacientes/1/evolucion/50/historial")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 2
    assert payload[0]['version'] == 1
    assert payload[1]['version'] == 2
    assert payload[0]['activo'] == 0
    assert payload[1]['activo'] == 1
