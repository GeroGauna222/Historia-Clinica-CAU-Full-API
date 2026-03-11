import sys
from pathlib import Path

import pytest
from flask_login import UserMixin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app as flask_app
from app import login_manager


class MockUser(UserMixin):
    def __init__(self, user_id, rol, nombre="Test User", username="test", email="test@example.com"):
        self.id = user_id
        self.rol = rol
        self.nombre = nombre
        self.username = username
        self.email = email
        self.duracion_turno = 30
        self.foto = None


class FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None, lastrowid=1):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.lastrowid = lastrowid
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        if self._fetchone_results:
            return self._fetchone_results.pop(0)
        return None

    def fetchall(self):
        if self._fetchall_results:
            return self._fetchall_results.pop(0)
        return []

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def login_as(client, user):
    client.test_users[str(user.id)] = user
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


@pytest.fixture
def client(monkeypatch):
    test_users = {}

    monkeypatch.setattr(login_manager, "_user_callback", lambda user_id: test_users.get(str(user_id)))
    flask_app.config.update(TESTING=True)

    with flask_app.test_client() as test_client:
        test_client.test_users = test_users
        yield test_client
