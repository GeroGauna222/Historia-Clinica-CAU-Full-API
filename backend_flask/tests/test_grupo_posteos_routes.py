from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import grupo_posteos_routes


def test_listar_posteos_grupo_rechaza_no_miembro(client, monkeypatch):
    login_as(client, MockUser(user_id=5, rol='profesional'))

    fake_cursor = FakeCursor(fetchone_results=[{'id': 3}, None])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(grupo_posteos_routes, 'get_connection', lambda: fake_connection)

    response = client.get('/api/grupos/3/posteos')

    assert response.status_code == 403


def test_crear_posteo_grupo_permite_miembro(client, monkeypatch):
    login_as(client, MockUser(user_id=8, rol='profesional'))

    fake_cursor = FakeCursor(fetchone_results=[{'id': 4}, {'ok': 1}], lastrowid=77)
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(grupo_posteos_routes, 'get_connection', lambda: fake_connection)

    response = client.post('/api/grupos/4/posteos', json={'titulo': 'Info', 'contenido': 'Se mueve la reunion'})

    assert response.status_code == 201
    assert response.get_json()['id'] == 77
    assert fake_connection.committed is True


def test_eliminar_posteo_grupo_rechaza_si_no_es_autor_ni_gestion(client, monkeypatch):
    login_as(client, MockUser(user_id=9, rol='profesional'))

    fake_cursor = FakeCursor(fetchone_results=[{'id': 5}, {'id': 11, 'autor_id': 2}])
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(grupo_posteos_routes, 'get_connection', lambda: fake_connection)

    response = client.delete('/api/grupos/5/posteos/11')

    assert response.status_code == 403
