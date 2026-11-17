import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError


ALLOWED_TABLES = frozenset(
    {"orders", "monthly_sales", "top_customers"}
)

# Lista explícita de estructuras admitidas.
# Las construcciones desconocidas se rechazan por defecto.
ALLOWED_NODES = frozenset(
    {
        "select", "from", "table", "identifier", "column",
        "star", "literal", "alias", "where",
        "and", "or", "not",
        "eq", "neq", "gt", "gte", "lt", "lte",
        "between", "in", "is", "null", "boolean", "paren",
        "add", "sub", "mul", "div", "neg",
        "order", "ordered", "group", "having",
        "limit", "offset", "distinct",
        "sum", "count", "avg", "min", "max", "round", "coalesce",
    }
)

MAX_SQL_LENGTH = 5_000


class InvalidQueryError(ValueError):
    """La consulta incumple la política SQL del proyecto."""


def validate_sql(sql: str) -> str:
    if not isinstance(sql, str) or not sql.strip():
        raise InvalidQueryError("El LLM no devolvió una consulta SQL")

    if len(sql) > MAX_SQL_LENGTH:
        raise InvalidQueryError("La consulta supera la longitud permitida")

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except SqlglotError as exc:
        raise InvalidQueryError("No se pudo interpretar la consulta SQL") from exc

    if len(statements) != 1 or statements[0] is None:
        raise InvalidQueryError("Se permite exactamente una sentencia SQL")

    query = statements[0]

    if not isinstance(query, exp.Select):
        raise InvalidQueryError("Solo se permiten consultas SELECT")

    for node in query.walk():
        if node.key not in ALLOWED_NODES:
            raise InvalidQueryError(
                f"Construcción SQL no permitida: {node.key}"
            )

    tables = list(query.find_all(exp.Table))

    if len(tables) != 1:
        raise InvalidQueryError(
            "La consulta debe acceder a una sola tabla o vista"
        )

    table = tables[0]

    if not isinstance(table.this, exp.Identifier):
        raise InvalidQueryError("La fuente debe ser una tabla o vista permitida")

    if table.db or table.catalog:
        raise InvalidQueryError(
            "No se permiten referencias a otras bases de datos"
        )

    if table.name.lower() not in ALLOWED_TABLES:
        raise InvalidQueryError(
            f"Tabla o vista no permitida: {table.name}"
        )

    # El ejecutor deberá utilizar esta versión validada.
    return query.sql(dialect="sqlite")