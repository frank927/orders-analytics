import sqlite3
from contextlib import closing
from pathlib import Path
from time import monotonic

from app.load_data import DB_PATH
from app.sql_validation import ALLOWED_TABLES, validate_sql


MAX_ROWS = 100
QUERY_TIMEOUT_SECONDS = 2.0

ALLOWED_FUNCTIONS = frozenset(
    {
        "sum", "count", "avg", "min", "max",
        "round", "coalesce", "substr",
    }
)


class QueryExecutionError(RuntimeError):
    """No se pudo ejecutar la consulta sobre los datos disponibles."""


def authorize_operation(
    action,
    argument_1,
    argument_2,
    database_name,
    source,
):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK

    if action == sqlite3.SQLITE_READ:
        table_name = (argument_1 or "").lower()

        # Algunas lecturas sin columnas, como COUNT(*), reciben
        # database_name=None y un nombre de columna vacío.
        is_columnless_read = (
            database_name is None
            and argument_2 == ""
        )

        if (
            table_name in ALLOWED_TABLES
            and (database_name == "main" or is_columnless_read)
        ):
            return sqlite3.SQLITE_OK

    if action == sqlite3.SQLITE_FUNCTION:
        function_name = (argument_2 or "").lower()

        if function_name in ALLOWED_FUNCTIONS:
            return sqlite3.SQLITE_OK

    return sqlite3.SQLITE_DENY


def execute_query(
    sql: str,
    db_path: Path = DB_PATH,
) -> dict:
    validated_sql = validate_sql(sql)
    database_uri = f"{db_path.resolve().as_uri()}?mode=ro"

    deadline = monotonic() + QUERY_TIMEOUT_SECONDS
    timed_out = False

    def check_deadline() -> int:
        nonlocal timed_out

        if monotonic() >= deadline:
            timed_out = True
            return 1

        return 0

    try:
        with closing(
            sqlite3.connect(database_uri, uri=True, timeout=1.0)
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.set_authorizer(authorize_operation)
            connection.set_progress_handler(check_deadline, 1_000)

            cursor = connection.execute(validated_sql)

            # Leemos una fila adicional para detectar si hay más resultados.
            rows = cursor.fetchmany(MAX_ROWS + 1)

            column_names = [
                description[0]
                for description in cursor.description
            ]

            if len(column_names) != len(set(column_names)):
                raise QueryExecutionError(
                    "La consulta devuelve columnas con nombres repetidos; "
                    "utiliza alias distintos"
                )

            return {
                "sql": validated_sql,
                "rows": [dict(row) for row in rows[:MAX_ROWS]],
                "row_count": min(len(rows), MAX_ROWS),
                "truncated": len(rows) > MAX_ROWS,
            }

    except sqlite3.Error as exc:
        if timed_out:
            raise QueryExecutionError(
                "La consulta superó el tiempo de ejecución permitido"
            ) from exc

        raise QueryExecutionError(
            "No se pudo ejecutar la consulta. Comprueba que la base de "
            "datos esté preparada y que las tablas y columnas sean válidas"
        ) from exc