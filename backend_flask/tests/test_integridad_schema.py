from pathlib import Path

from app.migrate import split_statements


ROOT = Path(__file__).resolve().parents[2]


def test_schema_impide_borrar_paciente_con_documentos_adjuntos():
    init_sql = (ROOT / "db" / "init.sql").read_text(encoding="utf-8")
    migration_sql = (
        ROOT / "db" / "migrations" / "20260915_integridad_borrado_rectificaciones.sql"
    ).read_text(encoding="utf-8")

    assert "FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE RESTRICT" in init_sql
    assert "ON DELETE RESTRICT" in migration_sql


def test_schema_impide_versiones_duplicadas_en_una_rectificacion():
    init_sql = (ROOT / "db" / "init.sql").read_text(encoding="utf-8")
    migration_sql = (
        ROOT / "db" / "migrations" / "20260915_integridad_borrado_rectificaciones.sql"
    ).read_text(encoding="utf-8")

    unique_key = "UNIQUE KEY uq_evoluciones_padre_version (padre_id, version)"
    assert unique_key in init_sql
    assert "UNIQUE (padre_id, version)" in migration_sql


def test_migrador_puede_separar_la_migracion_de_integridad():
    migration_sql = (
        ROOT / "db" / "migrations" / "20260915_integridad_borrado_rectificaciones.sql"
    ).read_text(encoding="utf-8")

    statements = split_statements(migration_sql)

    assert len(statements) == 7
    assert any("PREPARE drop_historia_archivos_paciente_fk" in statement for statement in statements)
    assert any("UNIQUE (padre_id, version)" in statement for statement in statements)


def test_schema_pantalla_de_llamados_en_init_y_migracion():
    init_sql = (ROOT / "db" / "init.sql").read_text(encoding="utf-8")
    migration_sql = (
        ROOT / "db" / "migrations" / "20261116_pantalla_de_llamados.sql"
    ).read_text(encoding="utf-8")

    for sql in (init_sql, migration_sql):
        assert "consultorio VARCHAR(50)" in sql
        assert "mostrar_en_pantalla TINYINT(1) NOT NULL DEFAULT 0" in sql
        assert "atencion_inicio DATETIME NULL" in sql
        assert "atencion_fin DATETIME NULL" in sql
        assert "CREATE TABLE" in sql and "pantallas" in sql
        assert "clave_hash CHAR(64) NOT NULL" in sql

    statements = split_statements(migration_sql)
    # 4 ALTER (usuarios, grupos_profesionales, turnos, turnos_grupales) + 1 CREATE TABLE
    assert len(statements) == 5
