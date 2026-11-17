import json
import re
from datetime import datetime, timedelta

import pytest
from mysql.connector import IntegrityError

from conftest import FakeConnection, FakeCursor, MockUser, login_as

from app.routes import pantalla_routes
from app.utils.pantalla import MAX_CODIGOS_PENDIENTES, MINUTOS_VIGENCIA_CODIGO, hash_clave

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
        # Datos que el SQL real no trae, pero que jamás deben llegar a la pantalla aunque algún día lo hicieran.
        "dni": "30111222", "motivo": "dolor lumbar cronico", "observaciones": "alergia a la penicilina",
    }


ENTIDADES = [
    {"tipo": "usuario", "id": 7, "nombre": "Dra. Pérez", "consultorio": "3"},
    {"tipo": "grupo", "id": 2, "nombre": "Rehabilitación", "consultorio": "Gimnasio"},
    {"tipo": "usuario", "id": 8, "nombre": "Dr. Sin Turnos", "consultorio": "4"},
]


def norm(consulta):
    return " ".join(consulta.split())


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

    # Sin turnos hoy -> no aparece. Orden determinista por (tipo, id): grupo antes que usuario.
    assert [t["nombre"] for t in tarjetas] == ["Rehabilitación", "Dra. Pérez"]
    assert tarjetas == [
        {
            "tipo": "grupo", "id": 2, "consultorio": "Gimnasio", "nombre": "Rehabilitación",
            "en_atencion": [{"nombre": "Luis D.", "atencion_inicio": "2026-11-16T10:20:00"}],
            "siguientes": [],
        },
        {
            "tipo": "usuario", "id": 7, "consultorio": "3", "nombre": "Dra. Pérez",
            "en_atencion": [{"nombre": "María G.", "atencion_inicio": "2026-11-16T10:35:00"}],
            "siguientes": [{"nombre": "Juan P."}],  # el programado (no presente) no aparece
        },
    ]


def test_construir_tarjetas_ejecuta_primero_entidades_y_luego_turnos_de_hoy():
    cursor = FakeCursor(fetchall_results=[ENTIDADES, []])
    pantalla_routes.construir_tarjetas(cursor)
    consultas = [norm(q) for q, _ in cursor.executed]
    assert len(consultas) == 2
    entidades, turnos = consultas
    assert "FROM usuarios u" in entidades and "FROM grupos_profesionales g" in entidades
    assert "FROM turnos t" in turnos and "FROM turnos_grupales tg" in turnos
    assert all(p is None for _, p in cursor.executed)


# ---------------------------------------------------------------- contrato SQL <-> Python

def test_sql_turnos_hoy_trae_todos_los_alias_que_lee_el_codigo():
    sql = norm(pantalla_routes.SQL_TURNOS_HOY)
    for alias in ("entidad_id", "ahora_db", "es_grupal", "paciente_id", "paciente_nombre", "paciente_apellido", "tipo"):
        assert f"AS {alias}" in sql, alias
    for columna in ("t.id", "tg.id", "t.fecha_inicio", "t.fecha_fin", "t.estado_asistencia", "t.atencion_inicio",
                    "t.atencion_fin", "tg.fecha_inicio", "tg.fecha_fin", "tg.estado_asistencia",
                    "tg.atencion_inicio", "tg.atencion_fin"):
        assert columna in sql, columna
    assert "t.usuario_id AS entidad_id" in sql and "tg.grupo_id AS entidad_id" in sql
    assert "'usuario' AS tipo" in sql and "'grupo' AS tipo" in sql
    assert "0 AS es_grupal" in sql and "1 AS es_grupal" in sql
    assert sql.count("NOW() AS ahora_db") == 2


def test_sql_turnos_hoy_filtra_por_hoy_con_condicion_sargable():
    sql = norm(pantalla_routes.SQL_TURNOS_HOY)
    assert not re.search(r"\bDATE\(", sql)  # \b: CURDATE( no cuenta
    assert sql.count("t.fecha_inicio >= CURDATE() AND t.fecha_inicio < CURDATE() + INTERVAL 1 DAY") == 1
    assert sql.count("tg.fecha_inicio >= CURDATE() AND tg.fecha_inicio < CURDATE() + INTERVAL 1 DAY") == 1


def test_sql_turnos_hoy_no_trae_datos_sensibles_del_paciente():
    sql = norm(pantalla_routes.SQL_TURNOS_HOY).lower()
    for prohibido in ("dni", "motivo", "observaciones", "especialidad", "p.*", "select *"):
        assert prohibido not in sql, prohibido


def test_sql_entidades_visibles_trae_alias_y_filtros_esperados():
    sql = norm(pantalla_routes.SQL_ENTIDADES_VISIBLES)
    for fragmento in ("'usuario' AS tipo", "'grupo' AS tipo", "u.id", "u.nombre", "u.consultorio",
                      "g.id", "g.nombre", "g.consultorio"):
        assert fragmento in sql, fragmento
    assert "u.mostrar_en_pantalla = 1" in sql
    assert "u.activo = 1" in sql
    assert "u.rol IN ('profesional', 'area')" in sql
    assert "g.mostrar_en_pantalla = 1" in sql
    assert "g.consultorio IS NOT NULL AND g.consultorio <> ''" in sql


def test_sql_visibles_trae_alias_y_filtra_por_hoy_con_condicion_sargable():
    sql = norm(pantalla_routes.SQL_VISIBLES)
    for fragmento in ("'usuario' AS tipo", "'grupo' AS tipo", "u.mostrar_en_pantalla", "g.mostrar_en_pantalla",
                      "AS tiene_turnos_hoy", "u.activo = 1", "u.rol IN ('profesional', 'area')",
                      "ORDER BY tipo, nombre"):
        assert fragmento in sql, fragmento
    assert not re.search(r"\bDATE\(", sql)
    assert "t.fecha_inicio >= CURDATE() AND t.fecha_inicio < CURDATE() + INTERVAL 1 DAY" in sql
    assert "tg.fecha_inicio >= CURDATE() AND tg.fecha_inicio < CURDATE() + INTERVAL 1 DAY" in sql
    assert "t.usuario_id = u.id" in sql and "tg.grupo_id = g.id" in sql


def test_siguientes_son_maximo_tres_ordenados_por_horario():
    turnos = [turno_fila("usuario", 7, i, 20 + i, f"Paciente{i}", "Zeta", hora=(10 + i, 0)) for i in (4, 2, 3, 1)]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    assert [s["nombre"] for s in tarjetas[0]["siguientes"]] == ["Paciente1 Z.", "Paciente2 Z.", "Paciente3 Z."]


def test_siguientes_con_mismo_horario_se_recortan_de_forma_estable_por_id():
    # 5 presentes con el mismo fecha_inicio: el recorte a 3 no depende del orden de las filas del cursor.
    def armar():
        return [turno_fila("usuario", 7, i, 100 + i, f"P{i}", "Zeta", hora=(10, 0)) for i in (4, 1, 5, 2, 3)]

    esperado = [{"nombre": "P1 Z."}, {"nombre": "P2 Z."}, {"nombre": "P3 Z."}]
    for orden in (armar(), list(reversed(armar())), sorted(armar(), key=lambda t: t["id"] % 3)):
        cursor = FakeCursor(fetchall_results=[ENTIDADES, orden])
        assert pantalla_routes.construir_tarjetas(cursor)[0]["siguientes"] == esperado


def test_en_atencion_con_mismo_atencion_inicio_se_ordena_por_id():
    inicio = datetime(2026, 11, 16, 10, 30)
    filas = [
        turno_fila("usuario", 7, 5, 15, "Cinco", "Uno", atencion_inicio=inicio),
        turno_fila("usuario", 7, 3, 13, "Tres", "Dos", atencion_inicio=inicio),
        turno_fila("usuario", 7, 4, 14, "Cuatro", "Tres", atencion_inicio=inicio),
    ]
    for orden in (filas, list(reversed(filas))):
        cursor = FakeCursor(fetchall_results=[ENTIDADES, [dict(f) for f in orden]])
        nombres = [e["nombre"] for e in pantalla_routes.construir_tarjetas(cursor)[0]["en_atencion"]]
        assert nombres == ["Tres D.", "Cuatro T.", "Cinco U."]


def test_tarjetas_se_ordenan_por_tipo_e_id_sin_depender_del_orden_de_entidades():
    entidades = [
        {"tipo": "usuario", "id": 8, "nombre": "Dr. Ocho", "consultorio": "8"},
        {"tipo": "grupo", "id": 5, "nombre": "Grupo Cinco", "consultorio": "G5"},
        {"tipo": "usuario", "id": 7, "nombre": "Dra. Siete", "consultorio": "7"},
        {"tipo": "grupo", "id": 2, "nombre": "Grupo Dos", "consultorio": "G2"},
    ]
    turnos = [
        turno_fila("usuario", 8, 1, 11, "Ana", "Ríos"),
        turno_fila("grupo", 5, 2, 12, "Beto", "Sosa", grupal=1),
        turno_fila("usuario", 7, 3, 13, "Carla", "Vega"),
        turno_fila("grupo", 2, 4, 14, "Dante", "Paz", grupal=1),
    ]
    cursor = FakeCursor(fetchall_results=[entidades, turnos])
    tarjetas = pantalla_routes.construir_tarjetas(cursor)
    assert [(t["tipo"], t["id"]) for t in tarjetas] == [("grupo", 2), ("grupo", 5), ("usuario", 7), ("usuario", 8)]


@pytest.mark.parametrize(
    "nombre, apellido",
    [(None, None), ("", ""), ("   ", "  "), (None, "Gómez"), ("María", None), ("María", "")],
)
def test_paciente_sin_nombre_o_apellido_no_rompe_las_tarjetas(nombre, apellido):
    turnos = [
        turno_fila("usuario", 7, 1, 11, nombre, apellido, atencion_inicio=datetime(2026, 11, 16, 10, 35)),
        turno_fila("usuario", 7, 2, 12, nombre, apellido, hora=(10, 30)),
    ]
    cursor = FakeCursor(fetchall_results=[ENTIDADES, turnos])
    tarjeta = pantalla_routes.construir_tarjetas(cursor)[0]
    assert len(tarjeta["en_atencion"]) == 1 and len(tarjeta["siguientes"]) == 1
    assert isinstance(tarjeta["en_atencion"][0]["nombre"], str) and tarjeta["en_atencion"][0]["nombre"]
    assert isinstance(tarjeta["siguientes"][0]["nombre"], str) and tarjeta["siguientes"][0]["nombre"]


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
    # Valores inyectados por turno_fila: si el código copiara la fila entera, estos asserts fallarían.
    assert "30111222" not in texto and "lumbar" not in texto and "penicilina" not in texto
    assert "observaciones" not in texto
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
    assert len(cursor.executed) == 1
    sql = norm(cursor.executed[0][0])
    assert "AS tiene_turnos_hoy" in sql and "FROM usuarios u" in sql and "FROM grupos_profesionales g" in sql
    assert "CURDATE()" in sql and "ORDER BY tipo, nombre" in sql
    assert cursor.executed[0][1] is None
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


@pytest.mark.parametrize(
    "kwargs",
    [
        {"json": "texto"},
        {"json": 5},
        {"json": [{"mostrar_en_pantalla": True}]},
        {"json": []},
        {},  # sin body
        {"data": "no es json", "content_type": "application/json"},
    ],
    ids=["string", "numero", "lista", "lista-vacia", "ausente", "json-invalido"],
)
def test_patch_body_que_no_es_objeto_devuelve_400_sin_abrir_transaccion(client, monkeypatch, kwargs):
    llamadas = []
    cursor = FakeCursor(fetchone_results=[{"id": 7, "consultorio": None, "mostrar_en_pantalla": 0}])
    conn = FakeConnection(cursor)
    monkeypatch.setattr(pantalla_routes, "get_connection", lambda: llamadas.append(1) or conn)
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.patch("/api/pantalla/visibles/usuario/7", **kwargs)
    assert r.status_code == 400
    assert isinstance(r.get_json()["message"], str) and r.get_json()["message"]
    assert llamadas == []  # ni siquiera se pidió conexión
    assert cursor.executed == [] and not conn.committed


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


# ---------------------------------------------------------------- vinculación y llamados (ADR 0001)

CLAVE_TV = "clave-secreta-del-televisor"
HEADERS_TV = {"X-Pantalla-Clave": CLAVE_TV}

SQL_LIMPIAR_VENCIDOS = "DELETE FROM pantallas WHERE vinculada_en IS NULL AND codigo_expira < NOW()"
SQL_CONTAR_PENDIENTES = "SELECT COUNT(*) AS n FROM pantallas WHERE vinculada_en IS NULL AND codigo_expira >= NOW()"
SQL_INSERTAR_PANTALLA = (
    "INSERT INTO pantallas (codigo, codigo_expira, clave_hash) "
    "VALUES (%s, DATE_ADD(NOW(), INTERVAL %s MINUTE), %s)"
)
SQL_BUSCAR_POR_CLAVE = (
    "SELECT id, codigo, vinculada_en, revocada_en, TIMESTAMPDIFF(SECOND, NOW(), codigo_expira) AS segundos_restantes "
    "FROM pantallas WHERE clave_hash = %s"
)
SQL_REGISTRAR_ACCESO = (
    "UPDATE pantallas SET ultimo_acceso = NOW() "
    "WHERE id = %s AND (ultimo_acceso IS NULL OR ultimo_acceso < NOW() - INTERVAL 1 MINUTE)"
)
SQL_VINCULAR = (
    "UPDATE pantallas SET nombre = %s, vinculada_en = NOW(), vinculada_por = %s, codigo = NULL, codigo_expira = NULL "
    "WHERE codigo = %s AND vinculada_en IS NULL AND revocada_en IS NULL AND codigo_expira >= NOW()"
)
SQL_DESVINCULAR = (
    "UPDATE pantallas SET revocada_en = NOW() "
    "WHERE id = %s AND vinculada_en IS NOT NULL AND revocada_en IS NULL"
)
SQL_LISTAR_TELEVISORES = (
    "SELECT id, nombre, vinculada_en, ultimo_acceso FROM pantallas "
    "WHERE vinculada_en IS NOT NULL AND revocada_en IS NULL ORDER BY vinculada_en DESC, id DESC"
)

BODIES_QUE_NO_SON_OBJETO = [
    {"json": "texto"},
    {"json": 5},
    {"json": [{"codigo": "K7M2QX", "nombre": "Sala"}]},
    {"json": []},
    {},  # sin body
    {"data": "no es json", "content_type": "application/json"},
]
IDS_BODIES = ["string", "numero", "lista", "lista-vacia", "ausente", "json-invalido"]


def sql_ejecutado(cursor):
    """[(SQL normalizado, params)] de lo que realmente se mandó a la base."""
    return [(norm(q), p) for q, p in cursor.executed]


def sin_conexion(monkeypatch):
    """Falla si la ruta pide conexión: sirve para probar validaciones previas a la base."""
    llamadas = []
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    monkeypatch.setattr(pantalla_routes, "get_connection", lambda: llamadas.append(1) or conn)
    return llamadas, cursor, conn


def fila_pantalla(**cambios):
    fila = {"id": 1, "codigo": None, "vinculada_en": AHORA, "revocada_en": None, "segundos_restantes": None}
    fila.update(cambios)
    return fila


# ---------- POST /api/pantalla/vinculacion (sin sesión)

def test_vinculacion_crea_codigo_y_clave_sin_sesion(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"n": 0}])
    r = client.post("/api/pantalla/vinculacion")  # sin login_as: es público
    assert r.status_code == 201
    body = r.get_json()
    assert set(body) == {"codigo", "clave", "expira_en_segundos"}
    assert len(body["codigo"]) == 6 and len(body["clave"]) >= 32
    assert body["expira_en_segundos"] == MINUTOS_VIGENCIA_CODIGO * 60
    assert sql_ejecutado(cursor) == [
        (SQL_LIMPIAR_VENCIDOS, None),
        (SQL_CONTAR_PENDIENTES, None),
        (SQL_INSERTAR_PANTALLA, (body["codigo"], MINUTOS_VIGENCIA_CODIGO, hash_clave(body["clave"]))),
    ]
    assert body["clave"] not in str(cursor.executed)  # se guarda el hash, nunca la clave
    assert conn.committed and not conn.rolled_back
    assert cursor.closed and conn.closed


def test_vinculacion_ignora_el_body(client, monkeypatch):
    preparar(monkeypatch, fetchone=[{"n": 0}])
    assert client.post("/api/pantalla/vinculacion", json="cualquier cosa").status_code == 201


def test_vinculacion_con_el_maximo_de_pendientes_devuelve_429(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[{"n": MAX_CODIGOS_PENDIENTES}])
    r = client.post("/api/pantalla/vinculacion")
    assert r.status_code == 429
    assert set(r.get_json()) == {"error"}
    assert sql_ejecutado(cursor) == [(SQL_LIMPIAR_VENCIDOS, None), (SQL_CONTAR_PENDIENTES, None)]  # no inserta
    assert conn.committed  # la limpieza de vencidos no queda a medias
    assert cursor.closed and conn.closed


def test_vinculacion_con_uno_menos_que_el_maximo_todavia_crea(client, monkeypatch):
    cursor, _ = preparar(monkeypatch, fetchone=[{"n": MAX_CODIGOS_PENDIENTES - 1}])
    assert client.post("/api/pantalla/vinculacion").status_code == 201
    assert len(executed_que_empiezan(cursor, "INSERT INTO pantallas")) == 1


def test_vinculacion_reintenta_con_otro_codigo_si_el_primero_ya_existe(client, monkeypatch):
    codigos = iter(["AAAAAA", "BBBBBB"])
    monkeypatch.setattr(pantalla_routes, "generar_codigo", lambda: next(codigos))
    cursor = FakeCursor(fetchone_results=[{"n": 0}], execute_side_effects=[None, None, IntegrityError("dup")])
    conn = FakeConnection(cursor)
    monkeypatch.setattr(pantalla_routes, "get_connection", lambda: conn)

    r = client.post("/api/pantalla/vinculacion")

    assert r.status_code == 201 and r.get_json()["codigo"] == "BBBBBB"
    inserts = [p for q, p in sql_ejecutado(cursor) if q == SQL_INSERTAR_PANTALLA]
    assert [p[0] for p in inserts] == ["AAAAAA", "BBBBBB"]
    assert inserts[0][2] == inserts[1][2] == hash_clave(r.get_json()["clave"])  # misma clave en ambos intentos
    assert conn.committed and not conn.rolled_back
    assert cursor.closed and conn.closed


def test_vinculacion_sin_codigo_libre_tras_5_intentos_devuelve_503_con_rollback(client, monkeypatch):
    cursor = FakeCursor(fetchone_results=[{"n": 0}], execute_side_effects=[None, None] + [IntegrityError("dup")] * 5)
    conn = FakeConnection(cursor)
    monkeypatch.setattr(pantalla_routes, "get_connection", lambda: conn)
    r = client.post("/api/pantalla/vinculacion")
    assert r.status_code == 503 and "clave" not in r.get_json()
    assert len(executed_que_empiezan(cursor, "INSERT INTO pantallas")) == 5
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


def test_vinculacion_hace_rollback_y_cierra_si_falla_la_base(client, monkeypatch):
    cursor = FakeCursor(fetchone_results=[{"n": 0}], execute_side_effects=[None, None, RuntimeError("boom")])
    conn = FakeConnection(cursor)
    monkeypatch.setattr(pantalla_routes, "get_connection", lambda: conn)
    with pytest.raises(RuntimeError):
        client.post("/api/pantalla/vinculacion")
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


# ---------- GET /api/pantalla/llamados (sin sesión, clave en cabecera)

@pytest.mark.parametrize("headers", [{}, {"X-Pantalla-Clave": ""}, {"X-Pantalla-Clave": "   "}], ids=["ausente", "vacia", "blancos"])
def test_llamados_sin_clave_devuelve_401_sin_tocar_la_base(client, monkeypatch, headers):
    llamadas, cursor, _ = sin_conexion(monkeypatch)
    r = client.get("/api/pantalla/llamados", headers=headers)
    assert r.status_code == 401 and set(r.get_json()) == {"error"}
    assert llamadas == [] and cursor.executed == []


def test_llamados_clave_desconocida_devuelve_401(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[None])
    r = client.get("/api/pantalla/llamados", headers=HEADERS_TV)
    assert r.status_code == 401 and set(r.get_json()) == {"error"}
    assert sql_ejecutado(cursor) == [(SQL_BUSCAR_POR_CLAVE, (hash_clave(CLAVE_TV),))]
    assert not conn.committed
    assert cursor.closed and conn.closed


def test_llamados_401_de_clave_desconocida_y_de_revocada_son_identicos(client, monkeypatch):
    # El cuerpo no debe permitir distinguir una clave que no existe de una revocada.
    preparar(monkeypatch, fetchone=[None])
    desconocida = client.get("/api/pantalla/llamados", headers=HEADERS_TV)
    preparar(monkeypatch, fetchone=[fila_pantalla(revocada_en=AHORA)])
    revocada = client.get("/api/pantalla/llamados", headers=HEADERS_TV)
    assert desconocida.status_code == revocada.status_code == 401
    assert desconocida.get_data() == revocada.get_data()
    assert desconocida.get_json() == revocada.get_json()


def test_llamados_busca_por_hash_y_nunca_manda_la_clave_a_la_base(client, monkeypatch):
    cursor, _ = preparar(monkeypatch, fetchone=[None])
    client.get("/api/pantalla/llamados", headers={"X-Pantalla-Clave": f"  {CLAVE_TV}  "})
    assert cursor.executed[0][1] == (hash_clave(CLAVE_TV),)  # la cabecera se recorta antes de hashear
    assert CLAVE_TV not in str(cursor.executed)


def test_llamados_revocada_devuelve_401_aunque_este_vinculada(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, fetchone=[fila_pantalla(revocada_en=AHORA)])
    r = client.get("/api/pantalla/llamados", headers=HEADERS_TV)
    assert r.status_code == 401 and set(r.get_json()) == {"error"}
    assert len(cursor.executed) == 1 and not conn.committed  # ni registra acceso ni lee tarjetas
    assert cursor.closed and conn.closed


@pytest.mark.parametrize("segundos", [-5, 0, None])
def test_llamados_codigo_vencido_devuelve_401(client, monkeypatch, segundos):
    fila = fila_pantalla(codigo="K7M2QX", vinculada_en=None, segundos_restantes=segundos)
    cursor, conn = preparar(monkeypatch, fetchone=[fila])
    r = client.get("/api/pantalla/llamados", headers=HEADERS_TV)
    assert r.status_code == 401 and "K7M2QX" not in r.get_data(as_text=True)
    assert len(cursor.executed) == 1 and not conn.committed
    assert cursor.closed and conn.closed


def test_llamados_pendiente_devuelve_solo_el_codigo(client, monkeypatch):
    fila = fila_pantalla(codigo="K7M2QX", vinculada_en=None, segundos_restantes=400)
    cursor, conn = preparar(monkeypatch, fetchone=[fila])
    r = client.get("/api/pantalla/llamados", headers=HEADERS_TV)  # sin login_as: es público
    assert r.status_code == 200
    assert r.get_json() == {"estado": "pendiente", "codigo": "K7M2QX", "expira_en_segundos": 400}
    assert len(cursor.executed) == 1  # no lee tarjetas ni registra acceso
    assert not conn.committed
    assert cursor.closed and conn.closed


def test_llamados_vinculada_devuelve_tarjetas_y_registra_acceso(client, monkeypatch):
    turnos = [
        turno_fila("usuario", 7, 1, 11, "María", "Gómez", atencion_inicio=datetime(2026, 11, 16, 10, 35)),
        turno_fila("usuario", 7, 2, 12, "Juan", "Pérez", hora=(10, 30)),
    ]
    cursor, conn = preparar(monkeypatch, fetchone=[fila_pantalla(id=9)], fetchall=[ENTIDADES, turnos])
    r = client.get("/api/pantalla/llamados", headers=HEADERS_TV)  # sin login_as: es público
    assert r.status_code == 200
    assert r.get_json() == {
        "estado": "vinculada",
        "tarjetas": [
            {
                "tipo": "usuario", "id": 7, "consultorio": "3", "nombre": "Dra. Pérez",
                "en_atencion": [{"nombre": "María G.", "atencion_inicio": "2026-11-16T10:35:00"}],
                "siguientes": [{"nombre": "Juan P."}],
            }
        ],
    }
    consultas = sql_ejecutado(cursor)
    assert len(consultas) == 4
    assert consultas[0] == (SQL_BUSCAR_POR_CLAVE, (hash_clave(CLAVE_TV),))
    assert consultas[1] == (SQL_REGISTRAR_ACCESO, (9,))
    assert "FROM usuarios u" in consultas[2][0] and "FROM turnos t" in consultas[3][0]
    assert conn.committed and not conn.rolled_back
    assert cursor.closed and conn.closed


def test_llamados_no_expone_clave_hash_ni_datos_del_paciente(client, monkeypatch):
    turnos = [turno_fila("usuario", 7, 1, 11, "María", "Gómez", atencion_inicio=datetime(2026, 11, 16, 10, 35))]
    fila = fila_pantalla(codigo="K7M2QX", nombre="Sala principal", clave_hash=hash_clave(CLAVE_TV))
    preparar(monkeypatch, fetchone=[fila], fetchall=[ENTIDADES, turnos])
    texto = client.get("/api/pantalla/llamados", headers=HEADERS_TV).get_data(as_text=True)
    for prohibido in (CLAVE_TV, hash_clave(CLAVE_TV), "K7M2QX", "Sala principal", "Gómez",
                      "30111222", "lumbar", "penicilina", "dni", "motivo", "paciente_id"):
        assert prohibido not in texto, prohibido


def test_llamados_hace_rollback_y_cierra_si_falla_el_registro_de_acceso(client, monkeypatch):
    cursor, conn = preparar(
        monkeypatch, fetchone=[fila_pantalla()], execute_side_effects=[None, RuntimeError("boom")]
    )
    with pytest.raises(RuntimeError):
        client.get("/api/pantalla/llamados", headers=HEADERS_TV)
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


def test_llamados_cierra_cursor_y_conexion_si_fallan_las_tarjetas(client, monkeypatch):
    cursor, conn = preparar(
        monkeypatch, fetchone=[fila_pantalla()], execute_side_effects=[None, None, RuntimeError("boom")]
    )
    with pytest.raises(RuntimeError):
        client.get("/api/pantalla/llamados", headers=HEADERS_TV)
    assert cursor.closed and conn.closed


# ---------- Cache-Control: no-store

def test_vinculacion_201_con_la_clave_no_se_cachea(client, monkeypatch):
    preparar(monkeypatch, fetchone=[{"n": 0}])
    r = client.post("/api/pantalla/vinculacion")
    assert r.status_code == 201 and "clave" in r.get_json()
    assert r.headers["Cache-Control"] == "no-store"


def test_vinculacion_429_no_se_cachea(client, monkeypatch):
    preparar(monkeypatch, fetchone=[{"n": MAX_CODIGOS_PENDIENTES}])
    r = client.post("/api/pantalla/vinculacion")
    assert r.status_code == 429 and r.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "fila, headers, estado",
    [
        (fila_pantalla(), HEADERS_TV, 200),
        (fila_pantalla(codigo="K7M2QX", vinculada_en=None, segundos_restantes=400), HEADERS_TV, 200),
        (fila_pantalla(codigo="K7M2QX", vinculada_en=None, segundos_restantes=-5), HEADERS_TV, 401),
        (fila_pantalla(revocada_en=AHORA), HEADERS_TV, 401),
        (None, HEADERS_TV, 401),
        (None, {}, 401),
    ],
    ids=["vinculada", "pendiente", "vencido", "revocada", "desconocida", "sin-clave"],
)
def test_llamados_nunca_se_cachea(client, monkeypatch, fila, headers, estado):
    preparar(monkeypatch, fetchone=[fila], fetchall=[ENTIDADES, []])
    r = client.get("/api/pantalla/llamados", headers=headers)
    assert r.status_code == estado
    assert r.headers["Cache-Control"] == "no-store"


# ---------- /api/pantalla/televisores (solo director)

@pytest.mark.parametrize("rol", ["administrativo", "profesional", "area"])
@pytest.mark.parametrize(
    "metodo, url, kwargs",
    [
        ("get", "/api/pantalla/televisores", {}),
        ("post", "/api/pantalla/televisores", {"json": {"codigo": "K7M2QX", "nombre": "Sala"}}),
        ("delete", "/api/pantalla/televisores/4", {}),
    ],
    ids=["listar", "vincular", "desvincular"],
)
def test_televisores_solo_el_director_gestiona(client, monkeypatch, rol, metodo, url, kwargs):
    llamadas, cursor, conn = sin_conexion(monkeypatch)
    login_as(client, MockUser(user_id=3, rol=rol))
    assert getattr(client, metodo)(url, **kwargs).status_code == 403
    assert llamadas == [] and cursor.executed == [] and not conn.committed


@pytest.mark.parametrize(
    "metodo, url, kwargs",
    [
        ("get", "/api/pantalla/televisores", {}),
        ("post", "/api/pantalla/televisores", {"json": {"codigo": "K7M2QX", "nombre": "Sala"}}),
        ("delete", "/api/pantalla/televisores/4", {}),
    ],
    ids=["listar", "vincular", "desvincular"],
)
def test_televisores_sin_sesion_devuelve_401(client, monkeypatch, metodo, url, kwargs):
    llamadas, cursor, conn = sin_conexion(monkeypatch)
    assert getattr(client, metodo)(url, **kwargs).status_code == 401
    assert llamadas == [] and cursor.executed == [] and not conn.committed


def test_vincular_televisor_ok(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, rowcount=1)
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.post("/api/pantalla/televisores", json={"codigo": " k7m2qx ", "nombre": "  Sala principal "})
    assert r.status_code == 200 and r.get_json() == {"message": "Televisor vinculado"}
    # Código normalizado a mayúsculas, nombre recortado y vinculado por el director logueado.
    assert sql_ejecutado(cursor) == [(SQL_VINCULAR, ("Sala principal", 3, "K7M2QX"))]
    assert conn.committed and not conn.rolled_back
    assert cursor.closed and conn.closed


def test_vincular_codigo_invalido_o_vencido_devuelve_400(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, rowcount=0)
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.post("/api/pantalla/televisores", json={"codigo": "ZZZZZZ", "nombre": "Sala"})
    assert r.status_code == 400 and "inválido" in r.get_json()["error"].lower()
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


@pytest.mark.parametrize("kwargs", BODIES_QUE_NO_SON_OBJETO, ids=IDS_BODIES)
def test_vincular_body_que_no_es_objeto_devuelve_400_sin_pedir_conexion(client, monkeypatch, kwargs):
    llamadas, cursor, conn = sin_conexion(monkeypatch)
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.post("/api/pantalla/televisores", **kwargs)
    assert r.status_code == 400
    assert isinstance(r.get_json()["error"], str) and r.get_json()["error"]
    assert llamadas == [] and cursor.executed == [] and not conn.committed


@pytest.mark.parametrize(
    "body",
    [
        {"codigo": "K7M2QX"},
        {"nombre": "Sala"},
        {},
        {"codigo": "K7M2QX", "nombre": "   "},
        {"codigo": "   ", "nombre": "Sala"},
        {"codigo": None, "nombre": "Sala"},
        {"codigo": 123456, "nombre": "Sala"},
        {"codigo": ["K7M2QX"], "nombre": "Sala"},
        {"codigo": "K7M2QX", "nombre": 5},
        {"codigo": "K7M2QX", "nombre": {"a": 1}},
    ],
)
def test_vincular_exige_codigo_y_nombre_de_texto(client, monkeypatch, body):
    llamadas, cursor, conn = sin_conexion(monkeypatch)
    login_as(client, MockUser(user_id=3, rol="director"))
    assert client.post("/api/pantalla/televisores", json=body).status_code == 400
    assert llamadas == [] and cursor.executed == []


def test_vincular_nombre_demasiado_largo_devuelve_400(client, monkeypatch):
    llamadas, cursor, _ = sin_conexion(monkeypatch)
    login_as(client, MockUser(user_id=3, rol="director"))
    assert client.post("/api/pantalla/televisores", json={"codigo": "K7M2QX", "nombre": "x" * 101}).status_code == 400
    assert llamadas == [] and cursor.executed == []


def test_vincular_nombre_de_100_caracteres_es_valido(client, monkeypatch):
    cursor, _ = preparar(monkeypatch, rowcount=1)
    login_as(client, MockUser(user_id=3, rol="director"))
    assert client.post("/api/pantalla/televisores", json={"codigo": "K7M2QX", "nombre": "x" * 100}).status_code == 200
    assert cursor.executed[0][1][0] == "x" * 100


def test_vincular_hace_rollback_y_cierra_si_falla_la_base(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, execute_side_effects=[RuntimeError("boom")])
    login_as(client, MockUser(user_id=3, rol="director"))
    with pytest.raises(RuntimeError):
        client.post("/api/pantalla/televisores", json={"codigo": "K7M2QX", "nombre": "Sala"})
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


def test_listar_televisores_devuelve_solo_campos_publicos_y_nunca_la_clave(client, monkeypatch):
    filas = [
        {"id": 4, "nombre": "Sala", "vinculada_en": AHORA, "ultimo_acceso": AHORA,
         # Columnas que el SQL real no trae, pero que jamás deben salir aunque algún día lo hicieran.
         "clave": CLAVE_TV, "clave_hash": hash_clave(CLAVE_TV), "codigo": "K7M2QX"},
        {"id": 3, "nombre": "Pasillo", "vinculada_en": AHORA, "ultimo_acceso": None},
    ]
    cursor, conn = preparar(monkeypatch, fetchall=[filas])
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.get("/api/pantalla/televisores")
    assert r.status_code == 200
    assert r.get_json() == [
        {"id": 4, "nombre": "Sala", "vinculada_en": "2026-11-16T10:40:00", "ultimo_acceso": "2026-11-16T10:40:00"},
        {"id": 3, "nombre": "Pasillo", "vinculada_en": "2026-11-16T10:40:00", "ultimo_acceso": None},
    ]
    texto = r.get_data(as_text=True)
    for prohibido in ("clave", CLAVE_TV, hash_clave(CLAVE_TV), "K7M2QX"):
        assert prohibido not in texto, prohibido
    consulta, params = sql_ejecutado(cursor)[0]
    assert (consulta, params) == (SQL_LISTAR_TELEVISORES, None)  # determinista; ni selecciona la clave
    assert "clave" not in consulta
    assert cursor.closed and conn.closed


def test_desvincular_televisor(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, rowcount=1)
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.delete("/api/pantalla/televisores/4")
    assert r.status_code == 200 and r.get_json() == {"message": "Televisor desvinculado"}
    assert sql_ejecutado(cursor) == [(SQL_DESVINCULAR, (4,))]
    assert conn.committed and not conn.rolled_back
    assert cursor.closed and conn.closed


def test_desvincular_inexistente_devuelve_404(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, rowcount=0)
    login_as(client, MockUser(user_id=3, rol="director"))
    r = client.delete("/api/pantalla/televisores/4")
    assert r.status_code == 404 and set(r.get_json()) == {"error"}
    assert sql_ejecutado(cursor) == [(SQL_DESVINCULAR, (4,))]
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed


def test_desvincular_hace_rollback_y_cierra_si_falla_la_base(client, monkeypatch):
    cursor, conn = preparar(monkeypatch, execute_side_effects=[RuntimeError("boom")])
    login_as(client, MockUser(user_id=3, rol="director"))
    with pytest.raises(RuntimeError):
        client.delete("/api/pantalla/televisores/4")
    assert conn.rolled_back and not conn.committed
    assert cursor.closed and conn.closed
