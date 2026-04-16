from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import comunicados_routes


def test_listar_comunicados_marca_permiso_eliminar_por_rol(client, monkeypatch):
    login_as(client, MockUser(user_id=1, rol='director'))

    fake_cursor = FakeCursor(
        fetchall_results=[
            [
                {
                    'id': 10,
                    'titulo': 'Corte programado',
                    'contenido': 'Manana no habra atencion',
                    'autor_id': 1,
                    'autor_nombre': 'Direccion',
                    'autor_rol': 'director',
                }
            ]
        ]
    )
    fake_connection = FakeConnection(fake_cursor)
    monkeypatch.setattr(comunicados_routes, 'get_connection', lambda: fake_connection)

    response = client.get('/api/comunicados')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]['puede_eliminar'] is True


def test_crear_comunicado_rechaza_profesional(client):
    login_as(client, MockUser(user_id=2, rol='profesional'))

    response = client.post('/api/comunicados', json={'titulo': 'Aviso', 'contenido': 'Texto'})

    assert response.status_code == 403
