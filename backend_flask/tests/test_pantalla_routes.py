import json
from datetime import datetime, timedelta

import pytest

from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import pantalla_routes

AHORA = datetime(2026, 11, 16, 10, 40)

CLAVES_TARJETA = {"tipo", "id", "consultorio", "nombre", "en_atencion", "siguientes"}
CLAVES_EN_ATENCION = {"nombre", "atencion_inicio"}
CLAVES_SIGUIENTE = {"nombre"}

SELECT_USUARIO = "SELECT id, consultorio, mostrar_en_pantalla FROM usuarios WHERE id = %s FOR UPDATE"
SELECT_GRUPO = "SELECT id, consultorio, mostrar_en_pantalla FROM grupos_profesionales WHERE id = %s FOR UPDATE"
UPDATE_USUARIO = "UPDATE usuarios SET consultorio = %s, mostrar_en_pantalla = %s WHERE id = %s"
UPDATE_GRUPO = "UPDATE grupos_profesionales SET consultorio = %s, mostrar_en_pantalla = %s WHERE id = %s"


def preparar(monkeypatch, fetchone=None, fetchall=None, rowcount=1, execute_side_effects=None):
    cursor = FakeCursor(
        fetchone_results=fetchone,
        fetchall_results=fetchall,
        rowcount=rowcount,
        execute_side_effects=execute_side_effects,
    )
    conn = FakeConnection(cursor)
    monkeypatch.setattr(pantalla_routes, "get_connection", lambda: conn)
    return cursor, conn


def turno_fila(tipo, entidad_id, tid, paciente_id, nombre, apellido, estado="presente",
               atencion_inicio=None, atencion_fin=None, grupal=0, hora=(10, 0)):
    inicio = datetime(2026, 11, 16, *hora)
    return {
        "tipo": tipo, "entidad_id": entidad_id, "id": tid,
        "fecha_inicio": inicio, "fecha_fin": inicio + timedelta(minutes=30),
        "estado_asistencia": estado, "atencion_inicio": atencion_inicio, "atencion_fin": atencion_fin,
        "es_grupal": grupal, "paciente_id": paciente_id,
        "paciente_nombre": nombre, "paciente_apellido": apellido, "ahora_db": AHORA,
    }


ENTIDADES = [
    {"tipo": "usuario", "id": 7, "nombre": "Dra. Pérez", "consultorio": "3"},
    {"tipo": "grupo", "id": 2, "nombre": "Rehabilitación", "consultorio": "Gimnasio"},
    {"tipo": "usuario", "id": 8, "nombre": "Dr. Sin Turnos", "consultorio": "4"},
]


def executed_que_empiezan(cursor, prefijo):
    return [(q.strip(), p) for q, p in cursor.executed if q.strip().startswith(prefijo)]


# ---------------------------------------------------------------- construir_tarjetas

def test_construir_tarjetas_separa_en_atencion_y_siguientes_con_nombre_abreviado():
    turnos = [
        turno_fila("usuario", 7, 1, 11, "María Elena", "Gómez", atencion_inicio=datetime(2026, 11, 16, 10, 35)),
        turno_fila("usuario", 7, 2, 12, "Juan", "Pérez", hora=(10, 30)),
        turno_fila("usuario", 7, 3, 13, "Ana", "López", estado="programado", hora=(11, 0)),
        turno_fila("grupo", 2, 4, 14, "Luis", "Díaz", grupal=1, atencion_inicio=datetime(2026, 11, 16, 10, 20), hora=(10, 15)),
    ]  # grupal 10:15-10:45: a las 10:40 sigue abierto
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])

    tarjetas = pantalla_routes.construir_tarjetas(cursor)

    assert [t["nombre"] for t in tarjetas] == ["Dra. Pérez", "Rehabilitación"]  # sin turnos hoy -> no aparece
    assert tarjetas == [
        {
            "tipo": "usuario", "id": 7, "consultorio": "3", "nombre": "Dra. Pérez",
            "en_atencion": [{"nombre": "María G.", "atencion_inicio": "2026-11-16T10:35:00"}],
            "siguientes": [{"nombre": "Juan P."}],  # el programado (no presente) no aparece
        },
        {
            "tipo": "grupo", "id": 2, "consultorio": "Gimnasio", "nombre": "Rehabilitación",
            "en_atencion": [{"nombre": "Luis D.", "atencion_inicio": "2026-11-16T10:20:00"}],
            "siguientes": [],
        },
    ]


def test_construir_tarjetas_ejecuta_primero_entidades_y_luego_turnos_de_hoy():
    cursor = FakeCursor(fetchall_results=[ENTIDADES, []])
    pantalla_routes.construir_tarjetas(cursor)
    assert [q for q, _ in cursor.executed] == [
        pantalla_routes.SQL_ENTIDADES_VISIBLES,
        pantalla_routes.SQL_TURNOS_HOY,
    ]


def test_siguientes_son_maximo_tres_ordenados_por_horario():
    turnos = [turno_fila("usuario", 7, i, 20 + i, f"Paciente{i}", "Zeta", hora=(10 + i, 0)) for i in (4, 2, 3, 1)]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    assert [s["nombre"] for s in tarjetas[0]["siguientes"]] == ["Paciente1 Z.", "Paciente2 Z.", "Paciente3 Z."]


def test_en_atencion_se_ordena_por_inicio_de_atencion():
    turnos = [
        turno_fila("usuario", 7, 1, 11, "Tardío", "Uno", atencion_inicio=datetime(2026, 11, 16, 10, 38), hora=(10, 0)),
        turno_fila("usuario", 7, 2, 12, "Temprano", "Dos", atencion_inicio=datetime(2026, 11, 16, 10, 31), hora=(11, 0)),
    ]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    assert [e["nombre"] for e in tarjetas[0]["en_atencion"]] == ["Temprano D.", "Tardío U."]


def test_tarjeta_y_items_tienen_exactamente_las_claves_publicas():
    turnos = [
        turno_fila("usuario", 7, 1, 11, "María", "Gómez", atencion_inicio=datetime(2026, 11, 16, 10, 35)),
        turno_fila("usuario", 7, 2, 12, "Juan", "Pérez", hora=(10, 30)),
    ]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    assert len(tarjetas) == 1
    assert set(tarjetas[0]) == CLAVES_TARJETA
    assert all(set(e) == CLAVES_EN_ATENCION for e in tarjetas[0]["en_atencion"])
    assert all(set(s) == CLAVES_SIGUIENTE for s in tarjetas[0]["siguientes"])
    assert tarjetas[0]["en_atencion"] and tarjetas[0]["siguientes"]


def test_tarjetas_no_exponen_datos_del_paciente():
    turnos = [
        turno_fila("usuario", 7, 1, 11, "María", "Gómez", atencion_inicio=datetime(2026, 11, 16, 10, 35)),
        turno_fila("usuario", 7, 2, 12, "Juan", "Pérez", hora=(10, 30)),
    ]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    texto = json.dumps(pantalla_routes.construir_tarjetas(cursor), ensure_ascii=False)
    assert "Gómez" not in texto and "paciente_id" not in texto and "dni" not in texto.lower()
    assert "motivo" not in texto and "especialidad" not in texto
    assert "ahora_db" not in texto and "estado_atencion" not in texto and "estado_asistencia" not in texto
    assert "María" in texto and "Juan P." in texto  # solo nombre + inicial


def test_pacientes_con_igual_abreviatura_se_desambiguan_con_mas_letras():
    turnos = [
        turno_fila("usuario", 7, 1, 11, "Juan", "Perez", hora=(10, 0)),
        turno_fila("usuario", 7, 2, 12, "Juan", "Pedraza", hora=(10, 30)),
    ]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    siguientes = pantalla_routes.construir_tarjetas(cursor)[0]["siguientes"]
    assert siguientes == [{"nombre": "Juan Per."}, {"nombre": "Juan Ped."}]


def test_turno_de_grupo_no_se_mezcla_con_usuario_del_mismo_id_numerico():
    entidades = [
        {"tipo": "usuario", "id": 2, "nombre": "Dr. Dos", "consultorio": "9"},
        {"tipo": "grupo", "id": 2, "nombre": "Grupo Dos", "consultorio": "Sala"},
    ]
    turnos = [turno_fila("grupo", 2, 1, 11, "Luis", "Díaz", grupal=1)]
    cursor = FakeCursor(fetchall_results=[entidades, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    assert [(t["tipo"], t["id"]) for t in tarjetas] == [("grupo", 2)]
    assert tarjetas[0]["siguientes"] == [{"nombre": "Luis D."}]


def test_turno_de_usuario_no_se_mezcla_con_grupo_del_mismo_id_numerico():
    entidades = [
        {"tipo": "usuario", "id": 2, "nombre": "Dr. Dos", "consultorio": "9"},
        {"tipo": "grupo", "id": 2, "nombre": "Grupo Dos", "consultorio": "Sala"},
    ]
    turnos = [turno_fila("usuario", 2, 1, 11, "Ana", "Ríos")]
    cursor = FakeCursor(fetchall_results=[entidades, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    assert [(t["tipo"], t["id"]) for t in tarjetas] == [("usuario", 2)]
    assert tarjetas[0]["siguientes"] == [{"nombre": "Ana R."}]


def test_turno_grupal_ya_cerrado_no_aparece_en_atencion_ni_siguientes():
    # Inicio de atención 10:00, el turno terminaba 10:30 y ahora son las 10:40 -> 'atendido'.
    turnos = [
        turno_fila("grupo", 2, 4, 14, "Luis", "Díaz", grupal=1, atencion_inicio=datetime(2026, 11, 16, 10, 0)),
        turno_fila("usuario", 7, 1, 11, "María", "Gómez", atencion_inicio=datetime(2026, 11, 16, 10, 35)),
    ]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    grupo = [t for t in tarjetas if t["tipo"] == "grupo"]
    assert len(grupo) == 1
    assert grupo[0]["en_atencion"] == [] and grupo[0]["siguientes"] == []
    assert "Luis" not in json.dumps(tarjetas)


def test_turno_atendido_con_atencion_fin_no_aparece():
    turnos = [
        turno_fila(
            "usuario", 7, 1, 11, "María", "Gómez",
            atencion_inicio=datetime(2026, 11, 16, 10, 0), atencion_fin=datetime(2026, 11, 16, 10, 20),
        )
    ]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    tarjeta = pantalla_routes.construir_tarjetas(cursor)[0]
    assert tarjeta["en_atencion"] == [] and tarjeta["siguientes"] == []


def test_en_atencion_expone_atencion_inicio_como_iso_string():
    turnos = [turno_fila("usuario", 7, 1, 11, "María", "Gómez", atencion_inicio=datetime(2026, 11, 16, 9, 5, 7))]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    item = pantalla_routes.construir_tarjetas(cursor)[0]["en_atencion"][0]
    assert item["atencion_inicio"] == "2026-11-16T09:05:07"
    assert isinstance(item["atencion_inicio"], str)


@pytest.mark.parametrize("consultorio_db", ["", None])
def test_consultorio_vacio_se_devuelve_como_none(consultorio_db):
    entidades = [{"tipo": "usuario", "id": 7, "nombre": "Dra. Pérez", "consultorio": consultorio_db}]
    turnos = [turno_fila("usuario", 7, 1, 11, "María", "Gómez")]
    cursor = FakeCursor(fetchall_results=[entidades, turnos])
    assert pantalla_routes.construir_tarjetas(cursor)[0]["consultorio"] is None


def test_sin_entidades_ni_turnos_devuelve_lista_vacia():
    cursor = FakeCursor(fetchall_results=[[], []])
    assert pantalla_routes.construir_tarjetas(cursor) == []


# ---------------------------------------------------------------- GET vista-previa

def test_vista_previa_requiere_director_o_administrativo(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchall=[[], []])
    login_as(client, MockUser(user_id=3, rol="profesional"))
    assert client.get("/api/pantalla/vista-previa").status_code == 403
    assert cursor.executed == []


def test_vista_previa_prohibida_para_area(client, monkeypatch):
    cursor, _ = preparar(monkeypatch, fetchall=[[], []])
    login_as(client, MockUser(user_id=3, rol="area"))
    assert client.get("/api/pantalla/vista-previa").status_code == 403
    assert cursor.executed == []


def test_vista_previa_para_administrativo(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchall=[ENTIDADES, []])
    login_as(client, MockUser(user_id=3, rol="administrativo"))
    r = client.get("/api/pantalla/vista-previa")
    assert r.status_code == 200 and r.get_json() == {"tarjetas": []}
    assert cursor.closed and conn.closed


def test_vista_previa_para_director_devuelve_tarjetas_y_nada_mas(client, monkeypatch):
    turnos = [turno_fila("usuario", 7, 1, 11, "María", "Gómez", atencion_inicio=datetime(2026, 11, 16, 10, 35))]
    cursor, conn = preparar(monkeypatch, fetchall=[ENTIDADES, turnos])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.get("/api/pantalla/vista-previa")
    assert r.status_code == 200
    assert r.get_json() == {
        "tarjetas": [
            {
                "tipo": "usuario", "id": 7, "consultorio": "3", "nombre": "Dra. Pérez",
                "en_atencion": [{"nombre": "María G.", "atencion_inicio": "2026-11-16T10:35:00"}],
                "siguientes": [],
            }
        ]
    }
    assert cursor.closed and conn.closed


def test_vista_previa_cierra_cursor_y_conexion_si_falla(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, execute_side_effects=[RuntimeError("boom")])
    login_as(client, MockUser(user_id=3, rol="director"))
    with pytest.raises(RuntimeError):
        client.get("/api/pantalla/vista-previa")
    assert cursor.closed and conn.closed


# ---------------------------------------------------------------- GET visibles

def test_visibles_lista_con_flag_de_turnos_hoy(client, monkeypatch):
    filas = [
        {"tipo": "usuario", "id": 7, "nombre": "Dra. Pérez", "consultorio": "3", "mostrar_en_pantalla": 1, "tiene_turnos_hoy": 1},
        {"tipo": "grupo", "id": 2, "nombre": "Rehab", "consultorio": None, "mostrar_en_pantalla": 0, "tiene_turnos_hoy": 0},
    ]
    cursor, conn = preparar(monkeypatch, fetchall=[filas])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.get("/api/pantalla/visibles")
    assert r.status_code == 200
    assert r.get_json() == [
        {"tipo": "usuario", "id": 7, "nombre": "Dra. Pérez", "consultorio": "3",
         "mostrar_en_pantalla": True, "tiene_turnos_hoy": True},
        {"tipo": "grupo", "id": 2, "nombre": "Rehab", "consultorio": None,
         "mostrar_en_pantalla": False, "tiene_turnos_hoy": False},
    ]
    assert [q for q, _ in cursor.executed] == [pantalla_routes.SQL_VISIBLES]
    assert cursor.closed and conn.closed


def test_visibles_permitido_para_administrativo(client, monkeypatch):
    preparar(monkeypatch, fetchall=[[]])
    login_as(client, MockUser(user_id=3, rol="administrativo"))
    r = client.get("/api/pantalla/visibles")
    assert r.status_code == 200 and r.get_json() == []


@pytest.mark.parametrize("rol", ["profesional", "area"])
def test_visibles_prohibido_para_profesional_y_area(client, monkeypatch, rol):
    cursor, _ = preparar(monkeypatch, fetchall=[[]])
    login_as(client, MockUser(user_id=3, rol=rol))
    assert client.get("/api/pantalla/visibles").status_code == 403
    assert cursor.executed == []


# ---------------------------------------------------------------- PATCH visibles

def test_patch_visible_activa_usuario(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 7, "consultorio": None, "mostrar_en_pantalla": 0}])
    login_as(client, MockUser(user_id=3, rol="administrativo"))
    r = client.patch("/api/pantalla/visibles/usuario/7", json={"mostrar_en_pantalla": True, "consultorio": " 3 "})
    assert r.status_code == 200 and conn.committed
    assert r.get_json() == {"consultorio": "3", "mostrar_en_pantalla": True}
    assert [(" ".join(q.split()), p) for q, p in cursor.executed] == [
        (SELECT_USUARIO, (7,)),
        (UPDATE_USUARIO, ("3", 1, 7)),
    ]
    assert cursor.closed and conn.closed


def test_patch_grupo_con_consultorio_valido_y_visible_a_la_vez(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 2, "consultorio": None, "mostrar_en_pantalla": 0}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/grupo/2", json={"mostrar_en_pantalla": True, "consultorio": "Gimnasio"})
    assert r.status_code == 200 and conn.committed
    assert r.get_json() == {"consultorio": "Gimnasio", "mostrar_en_pantalla": True}
    assert [(" ".join(q.split()), p) for q, p in cursor.executed] == [
        (SELECT_GRUPO, (2,)),
        (UPDATE_GRUPO, ("Gimnasio", 1, 2)),
    ]


def test_patch_usuario_sin_consultorio_puede_ser_visible(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 7, "consultorio": None, "mostrar_en_pantalla": 0}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/usuario/7", json={"mostrar_en_pantalla": True})
    assert r.status_code == 200 and conn.committed
    assert r.get_json() == {"consultorio": None, "mostrar_en_pantalla": True}
    assert executed_que_empiezan(cursor, "UPDATE usuarios") == [(UPDATE_USUARIO, (None, 1, 7))]


def test_patch_oculta_usuario_conservando_consultorio(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 7, "consultorio": "3", "mostrar_en_pantalla": 1}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/usuario/7", json={"mostrar_en_pantalla": False})
    assert r.status_code == 200 and conn.committed
    assert r.get_json() == {"consultorio": "3", "mostrar_en_pantalla": False}
    assert executed_que_empiezan(cursor, "UPDATE usuarios") == [(UPDATE_USUARIO, ("3", 0, 7))]


def test_patch_solo_consultorio_conserva_visibilidad(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 2, "consultorio": "Gimnasio", "mostrar_en_pantalla": 1}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/grupo/2", json={"consultorio": "Sala 2"})
    assert r.status_code == 200 and conn.committed
    assert r.get_json() == {"consultorio": "Sala 2", "mostrar_en_pantalla": True}
    assert executed_que_empiezan(cursor, "UPDATE grupos_profesionales") == [(UPDATE_GRUPO, ("Sala 2", 1, 2))]


def test_patch_grupo_quitar_consultorio_y_ocultar_a_la_vez_es_valido(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 2, "consultorio": "Gimnasio", "mostrar_en_pantalla": 1}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/grupo/2", json={"consultorio": "", "mostrar_en_pantalla": False})
    assert r.status_code == 200 and conn.committed
    assert r.get_json() == {"consultorio": None, "mostrar_en_pantalla": False}
    assert executed_que_empiezan(cursor, "UPDATE grupos_profesionales") == [(UPDATE_GRUPO, (None, 0, 2))]


def test_patch_grupo_visible_sin_consultorio_se_rechaza(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 2, "consultorio": None, "mostrar_en_pantalla": 0}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/grupo/2", json={"mostrar_en_pantalla": True})
    assert r.status_code == 400 and not conn.committed
    assert executed_que_empiezan(cursor, "UPDATE") == []
    assert cursor.closed and conn.closed


def test_patch_quitar_consultorio_a_grupo_visible_se_rechaza(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 2, "consultorio": "Gimnasio", "mostrar_en_pantalla": 1}])
    login_as(client, MockUser(user_id=3, rol="director"))
    assert client.patch("/api/pantalla/visibles/grupo/2", json={"consultorio": ""}).status_code == 400
    assert not conn.committed
    assert executed_que_empiezan(cursor, "UPDATE") == []


def test_patch_consultorio_demasiado_largo_se_rechaza(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 7, "consultorio": None, "mostrar_en_pantalla": 0}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/usuario/7", json={"consultorio": "x" * 51})
    assert r.status_code == 400 and not conn.committed
    assert executed_que_empiezan(cursor, "UPDATE") == []


@pytest.mark.parametrize("valor", ["false", "true", 1, 0, None, "no"])
def test_patch_mostrar_en_pantalla_debe_ser_booleano(client, monkeypatch, valor):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 7, "consultorio": "3", "mostrar_en_pantalla": 1}])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/usuario/7", json={"mostrar_en_pantalla": valor})
    assert r.status_code == 400 and not conn.committed
    assert executed_que_empiezan(cursor, "UPDATE") == []


@pytest.mark.parametrize("tipo, select", [("usuario", SELECT_USUARIO), ("grupo", SELECT_GRUPO)])
def test_patch_entidad_inexistente_devuelve_404(client, monkeypatch, tipo, select):
    cursor, conn = preparar(monkeypatch, fetchone=[])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch(f"/api/pantalla/visibles/{tipo}/99", json={"mostrar_en_pantalla": True})
    assert r.status_code == 404 and not conn.committed
    assert [(" ".join(q.split()), p) for q, p in cursor.executed] == [(select, (99,))]
    assert cursor.closed and conn.closed


def test_patch_tipo_invalido_devuelve_404(client, monkeypatch):
    cursor, conn = preparar(monkeypatch)
    login_as(client, MockUser(user_id=3, rol="director"))
    assert client.patch("/api/pantalla/visibles/otro/2", json={"mostrar_en_pantalla": True}).status_code == 404
    assert cursor.executed == [] and not conn.committed


def test_patch_hace_rollback_y_cierra_si_falla_el_update(client, monkeypatch):
    cursor, conn = preparar(
        monkeypatch,
        fetchone=[{"id": 7, "consultorio": None, "mostrar_en_pantalla": 0}],
        execute_side_effects=[None, RuntimeError("boom")],
    )
    login_as(client, MockUser(user_id=3, rol="director"))
    with pytest.raises(RuntimeError):
        client.patch("/api/pantalla/visibles/usuario/7", json={"mostrar_en_pantalla": True})
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


@pytest.mark.parametrize("rol", ["profesional", "area"])
def test_patch_visible_prohibido_para_profesional_y_area(client, monkeypatch, rol):
    cursor, conn = preparar(monkeypatch)
    login_as(client, MockUser(user_id=3, rol=rol))
    assert client.patch("/api/pantalla/visibles/usuario/7", json={"mostrar_en_pantalla": True}).status_code == 403
    assert cursor.executed == [] and not conn.committed


# ---------------------------------------------------------------- sin sesión

@pytest.mark.parametrize(
    "metodo, url",
    [
        ("get", "/api/pantalla/vista-previa"),
        ("get", "/api/pantalla/visibles"),
        ("patch", "/api/pantalla/visibles/usuario/7"),
    ],
)
def test_endpoints_sin_sesion_devuelven_401(client, monkeypatch, metodo, url):
    cursor, conn = preparar(monkeypatch, fetchone=[{"id": 7, "consultorio": None, "mostrar_en_pantalla": 0}])
    kwargs = {"json": {"mostrar_en_pantalla": True}} if metodo == "patch" else {}
    assert getattr(client, metodo)(url, **kwargs).status_code == 401
    assert cursor.executed == [] and not conn.committed
