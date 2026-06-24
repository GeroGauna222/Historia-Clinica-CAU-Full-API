import os
import pathlib
import time

import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "user": os.getenv("DB_USER", "hc_app"),
    "password": os.getenv("DB_PASSWORD", "hc_password"),
    "database": os.getenv("DB_NAME", "hc_bfa"),
}

MIGRATIONS_DIR = pathlib.Path(os.getenv("MIGRATIONS_DIR", "/app/migrations"))


def get_connection(retries=10, delay=3):
    for attempt in range(retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                return conn
        except Error as exc:
            print(f"Migration DB wait {attempt + 1}/{retries}: {exc}")
            time.sleep(delay)
    raise RuntimeError("No se pudo conectar a MySQL para ejecutar migraciones.")


def split_statements(sql):
    statements = []
    current = []
    in_single = False
    in_double = False

    for char in sql:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double

        if char == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def ensure_schema_migrations(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def already_applied(cursor, filename):
    cursor.execute("SELECT filename FROM schema_migrations WHERE filename = %s", (filename,))
    return cursor.fetchone() is not None


def mark_applied(cursor, filename):
    cursor.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,))


def run_migrations():
    if not MIGRATIONS_DIR.exists():
        print(f"No migrations dir at {MIGRATIONS_DIR}; skipping.")
        return

    conn = get_connection()
    # buffered=True consume cada result set al ejecutar, evitando el error 2014
    # "Commands out of sync" del conector C cuando una sentencia (p.ej. CREATE TABLE
    # IF NOT EXISTS sobre una tabla existente) deja resultados sin leer antes del
    # siguiente execute (mark_applied).
    cursor = conn.cursor(buffered=True)
    try:
        ensure_schema_migrations(cursor)
        conn.commit()

        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if already_applied(cursor, migration.name):
                print(f"Migration already applied: {migration.name}")
                continue

            print(f"Applying migration: {migration.name}")
            sql = migration.read_text(encoding="utf-8")
            for statement in split_statements(sql):
                try:
                    cursor.execute(statement)
                except Error as exc:
                    # Errores de "ya existe" -> migracion ya aplicada (idempotencia para
                    # migraciones aditivas): 1050 tabla, 1060 columna, 1061 indice/clave,
                    # 1826 foreign key duplicada. Necesario al adoptar el tracking en una DB
                    # cuyo esquema fue migrado a mano antes de existir schema_migrations.
                    if getattr(exc, "errno", None) in (1050, 1060, 1061, 1826):
                        print(f"Objeto ya existe, continuando: {exc}")
                        continue
                    raise
            mark_applied(cursor, migration.name)
            conn.commit()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migrations()
