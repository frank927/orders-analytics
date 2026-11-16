import sqlite3
from pathlib import Path

from app.load_data import DB_PATH


SQL_PATH = Path(__file__).with_name("views.sql")


def create_views() -> None:
    # mode=rw exige que la base de datos ya exista.
    database_uri = f"{DB_PATH.resolve().as_uri()}?mode=rw"

    with sqlite3.connect(database_uri, uri=True) as connection:
        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'orders'
            """
        ).fetchone()

        if table_exists is None:
            raise RuntimeError(
                "Falta la tabla orders. Ejecuta primero: python -m app.load_data"
            )

        sql = SQL_PATH.read_text(encoding="utf-8")

        # Ambas vistas se actualizan en una misma transacción.
        connection.executescript(f"BEGIN;\n{sql}\nCOMMIT;")

    print("Vistas creadas: monthly_sales y top_customers")


if __name__ == "__main__":
    create_views()