from datetime import datetime, timedelta

from app.utils.pantalla import (
    ALFABETO_CODIGO,
    abreviar_pacientes,
    anotar_estado_atencion,
    ahora_de,
    cierre_grupal,
    estado_atencion,
    generar_codigo,
    hash_clave,
    normalizar_consultorio,
)

AHORA = datetime(2026, 11, 16, 10, 40)


def turno(**kw):
    base = {
        "estado_asistencia": "presente",
        "atencion_inicio": None,
        "atencion_fin": None,
        "es_grupal": 0,
        "fecha_inicio": datetime(2026, 11, 16, 10, 0),
        "fecha_fin": datetime(2026, 11, 16, 10, 30),
    }
    base.update(kw)
    return base


# ---- estado de atención ----

def test_presente_sin_llamar_esta_esperando():
    assert estado_atencion(turno(), AHORA) == "esperando"


def test_no_presente_no_tiene_estado():
    assert estado_atencion(turno(estado_asistencia="programado"), AHORA) is None
    assert estado_atencion(turno(estado_asistencia="con_aviso"), AHORA) is None


def test_individual_llamado_esta_en_atencion():
    t = turno(atencion_inicio=datetime(2026, 11, 16, 10, 35))
    assert estado_atencion(t, AHORA) == "en_atencion"


def test_individual_con_atencion_fin_esta_atendido():
    t = turno(atencion_inicio=datetime(2026, 11, 16, 10, 5), atencion_fin=datetime(2026, 11, 16, 10, 20))
    assert estado_atencion(t, AHORA) == "atendido"


def test_atencion_de_otro_dia_esta_atendida():
    t = turno(atencion_inicio=datetime(2026, 11, 15, 10, 5))
    assert estado_atencion(t, AHORA) == "atendido"


def test_grupal_cierra_a_la_hora_de_fin():
    t = turno(es_grupal=1, atencion_inicio=datetime(2026, 11, 16, 10, 5))
    assert estado_atencion(t, datetime(2026, 11, 16, 10, 29)) == "en_atencion"
    assert estado_atencion(t, datetime(2026, 11, 16, 10, 30)) == "atendido"


def test_grupal_llamado_tarde_cierra_con_la_duracion_desde_el_llamado():
    # turno 10:00-10:30, llamado 10:35 -> cierra 11:05
    t = turno(es_grupal=1, atencion_inicio=datetime(2026, 11, 16, 10, 35))
    assert cierre_grupal(t["fecha_inicio"], t["fecha_fin"], t["atencion_inicio"]) == datetime(2026, 11, 16, 11, 5)
    assert estado_atencion(t, datetime(2026, 11, 16, 11, 4)) == "en_atencion"
    assert estado_atencion(t, datetime(2026, 11, 16, 11, 5)) == "atendido"


def test_individual_no_cierra_solo_por_hora():
    t = turno(atencion_inicio=datetime(2026, 11, 16, 10, 5))
    assert estado_atencion(t, datetime(2026, 11, 16, 18, 0)) == "en_atencion"


def test_anotar_estado_atencion_usa_ahora_db_y_la_quita():
    fila = turno(atencion_inicio=datetime(2026, 11, 16, 10, 35), ahora_db=AHORA)
    filas = [fila]
    anotar_estado_atencion(filas)
    assert fila["estado_atencion"] == "en_atencion"
    assert "ahora_db" not in fila
    assert "atencion_inicio" in fila


def test_anotar_quita_tiempos_si_se_pide():
    fila = turno(atencion_inicio=datetime(2026, 11, 16, 10, 35), ahora_db=AHORA)
    anotar_estado_atencion([fila], quitar_tiempos=True)
    assert "atencion_inicio" not in fila and "atencion_fin" not in fila


def test_presente_de_un_dia_anterior_sin_llamar_sigue_esperando():
    # Intencional: sin atencion_inicio no hay nada que "cerrar"; la UI solo usa este
    # estado para los turnos del dia actual (presentes-hoy), asi que no se compara la fecha.
    t = turno(fecha_inicio=datetime(2026, 11, 15, 10, 0), fecha_fin=datetime(2026, 11, 15, 10, 30))
    assert estado_atencion(t, AHORA) == "esperando"


def test_anotar_grupal_true_no_necesita_la_clave_es_grupal():
    fila = turno(atencion_inicio=datetime(2026, 11, 16, 10, 5), ahora_db=AHORA)
    del fila["es_grupal"]
    anotar_estado_atencion([fila], grupal=True)
    assert fila["estado_atencion"] == "atendido"  # el grupo cerro a las 10:30


def test_anotar_grupal_none_usa_la_clave_de_la_fila():
    individual = turno(atencion_inicio=datetime(2026, 11, 16, 10, 5), ahora_db=AHORA)
    grupal = turno(es_grupal=1, atencion_inicio=datetime(2026, 11, 16, 10, 5), ahora_db=AHORA)
    anotar_estado_atencion([individual, grupal])
    assert individual["estado_atencion"] == "en_atencion"
    assert grupal["estado_atencion"] == "atendido"


def test_ahora_de_cae_a_datetime_now_si_no_hay_ahora_db():
    antes = datetime.now() - timedelta(seconds=1)
    assert ahora_de([{"id": 1}]) >= antes
    assert ahora_de([]) >= antes
    assert ahora_de([{"ahora_db": AHORA}]) == AHORA


# ---- Nombre abreviado ----

def pac(i, nombre, apellido):
    return {"id": i, "nombre": nombre, "apellido": apellido}


def test_nombre_abreviado_basico():
    assert abreviar_pacientes([pac(1, "maría", "gómez")]) == {1: "María G."}


def test_nombre_abreviado_compuestos_usa_primera_palabra():
    r = abreviar_pacientes([pac(1, "Juan Carlos", "Pérez Díaz")])
    assert r == {1: "Juan P."}


def test_nombre_abreviado_coincidencia_agrega_letras():
    r = abreviar_pacientes([pac(1, "María", "Gómez"), pac(2, "María", "García")])
    assert r[1] == "María Gó."
    assert r[2] == "María Ga."


def test_nombre_abreviado_mismo_paciente_dos_veces_no_es_coincidencia():
    r = abreviar_pacientes([pac(1, "María", "Gómez"), pac(1, "María", "Gómez")])
    assert r == {1: "María G."}


def test_nombre_abreviado_sin_apellido():
    assert abreviar_pacientes([pac(1, "Ana", "")]) == {1: "Ana"}


# ---- códigos y claves ----

def test_codigo_tiene_6_caracteres_sin_confundibles():
    for _ in range(200):
        codigo = generar_codigo()
        assert len(codigo) == 6
        assert not set(codigo) & set("0O1IL")
        assert set(codigo) <= set(ALFABETO_CODIGO)


def test_hash_clave_es_sha256_hex_estable():
    assert len(hash_clave("abc")) == 64
    assert hash_clave("abc") == hash_clave("abc")
    assert hash_clave("abc") != hash_clave("abd")


# ---- consultorio ----
def test_normalizar_consultorio_recorta():
    assert normalizar_consultorio("  3 ") == ("3", None)


def test_normalizar_consultorio_vacio_o_none():
    assert normalizar_consultorio("   ") == (None, None)
    assert normalizar_consultorio(None) == (None, None)


def test_normalizar_consultorio_acepta_numero():
    assert normalizar_consultorio(3) == ("3", None)


def test_normalizar_consultorio_limite_de_50():
    assert normalizar_consultorio("x" * 50) == ("x" * 50, None)
    valor, error = normalizar_consultorio("x" * 51)
    assert valor is None
    assert error
