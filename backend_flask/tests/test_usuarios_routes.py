import io
import os
import pytest
from PIL import Image
from conftest import FakeConnection, FakeCursor, MockUser, login_as
from app.routes import usuarios_routes

def test_actualizar_perfil_sin_foto(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol='profesional'))

    fake_cursor = FakeCursor()
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(usuarios_routes, 'get_connection', lambda: fake_connection)
    monkeypatch.setattr(usuarios_routes, '_professional_values', lambda form: {})

    response = client.post('/api/usuario/perfil', data={
        'nombre': 'Nuevo Nombre',
        'email': 'nuevo@example.com'
    })

    assert response.status_code == 200
    assert response.get_json()['message'] == 'Perfil actualizado correctamente.'
    assert fake_connection.committed is True

def test_actualizar_perfil_con_foto_valida(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=1, rol='profesional'))

    # Mock database
    fake_cursor = FakeCursor()
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(usuarios_routes, 'get_connection', lambda: fake_connection)
    monkeypatch.setattr(usuarios_routes, '_professional_values', lambda form: {})

    # Create a real small 1x1 image in memory
    img = Image.new('RGB', (1, 1), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    # We mock carpeta_fotos inside the module (wait, since it is a local variable in the function,
    # we can't monkeypatch it directly, but let's see how we can handle this or if it fails on Windows)
    response = client.post('/api/usuario/perfil', data={
        'nombre': 'Nuevo Nombre',
        'email': 'nuevo@example.com',
        'foto': (img_byte_arr, 'test.jpg')
    })

    # Let's see what status code we get and if it fails due to the hardcoded path.
    # We will check if it fails or succeeds.
    print("Response data:", response.data)
    assert response.status_code == 200


def test_actualizar_perfil_con_foto_invalida(client, monkeypatch, tmp_path):
    login_as(client, MockUser(user_id=1, rol='profesional'))

    fake_cursor = FakeCursor()
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(usuarios_routes, 'get_connection', lambda: fake_connection)
    monkeypatch.setattr(usuarios_routes, '_professional_values', lambda form: {})

    # Upload invalid image data (text file)
    invalid_data = io.BytesIO(b"this is not an image file, it is plain text")

    response = client.post('/api/usuario/perfil', data={
        'nombre': 'Nuevo Nombre',
        'email': 'nuevo@example.com',
        'foto': (invalid_data, 'test.txt')
    })

    assert response.status_code == 200

    # Let's check the size of the saved file.
    saved_path = os.path.join(usuarios_routes.app.root_path, "static", "fotos_usuarios", "user_1.txt")
    assert os.path.exists(saved_path)
    size = os.path.getsize(saved_path)
    print(f"Saved file size: {size}")
    # If it didn't call seek(0), the saved file will be 0 bytes (empty)!
    assert size > 0
    os.remove(saved_path)



# ---- consultorio (pantalla de llamados) ----
def _usuario_actual():
    return {"id": 5, "username": "dra", "email": "dra@example.com", "rol": "profesional"}


def _put_usuario(client, monkeypatch, body, fetchone=None):
    login_as(client, MockUser(user_id=1, rol="director"))
    cursor = FakeCursor(fetchone_results=fetchone if fetchone is not None else [_usuario_actual()])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(usuarios_routes, "get_connection", lambda: connection)
    response = client.put("/api/usuarios/5", json=body)
    updates = [(q, p) for q, p in cursor.executed if q.strip().upper().startswith("UPDATE USUARIOS")]
    return response, cursor, connection, updates


def test_actualizar_usuario_guarda_consultorio(client, monkeypatch):
    response, cursor, connection, updates = _put_usuario(client, monkeypatch, {"consultorio": "  3  "})

    assert response.status_code == 200
    assert len(updates) == 1
    query, params = updates[0]
    assert "consultorio = %s" in query
    assert params == ("3", 5)
    assert connection.committed is True
    assert cursor.closed is True and connection.closed is True


def test_actualizar_usuario_consultorio_vacio_guarda_none(client, monkeypatch):
    response, _, _, updates = _put_usuario(client, monkeypatch, {"consultorio": "   "})

    assert response.status_code == 200
    assert len(updates) == 1
    assert "consultorio = %s" in updates[0][0]
    assert updates[0][1] == (None, 5)


def test_actualizar_usuario_consultorio_demasiado_largo_es_400_sin_update(client, monkeypatch):
    response, cursor, connection, updates = _put_usuario(client, monkeypatch, {"consultorio": "x" * 51})

    assert response.status_code == 400
    assert "50" in response.get_json()["error"]
    assert updates == []
    assert connection.committed is False
    assert cursor.closed is True and connection.closed is True


def test_actualizar_usuario_consultorio_junto_a_otros_campos(client, monkeypatch):
    response, _, _, updates = _put_usuario(
        client, monkeypatch, {"nombre": "Dra. Perez", "consultorio": "Gimnasio"}
    )

    assert response.status_code == 200
    query, params = updates[0]
    assert "nombre=%s" in query and "consultorio = %s" in query
    assert params == ("Dra. Perez", "Gimnasio", 5)


def test_detalle_usuario_incluye_consultorio(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="director"))
    cursor = FakeCursor(fetchone_results=[{"id": 5, "nombre": "Dra", "consultorio": "3"}])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(usuarios_routes, "get_connection", lambda: connection)

    response = client.get("/api/usuarios/5")

    assert response.status_code == 200
    assert response.get_json()["consultorio"] == "3"
    assert "consultorio" in cursor.executed[0][0]


def test_listado_usuarios_incluye_consultorio_en_el_select(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol="director"))

    for url in ("/api/usuarios", "/api/usuarios?q=dra"):
        cursor = FakeCursor(fetchall_results=[[{"id": 5, "nombre": "Dra", "consultorio": "3"}]])
        connection = FakeConnection(cursor)
        monkeypatch.setattr(usuarios_routes, "get_connection", lambda c=connection: c)
        response = client.get(url)
        assert response.status_code == 200
        assert response.get_json()[0]["consultorio"] == "3"
        assert "consultorio" in cursor.executed[0][0]
