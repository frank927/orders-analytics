import sqlite3
from contextlib import closing

from app.query_executor import execute_query


def test_counts_rows_with_authorizer_enabled(tmp_path):
    database_path = tmp_path / "test_orders.db"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            "CREATE TABLE orders (order_id INTEGER PRIMARY KEY)"
        )
        connection.executemany(
            "INSERT INTO orders (order_id) VALUES (?)",
            [(1,), (2,), (3,)],
        )
        connection.commit()

    result = execute_query(
        "SELECT COUNT(*) AS total FROM orders",
        db_path=database_path,
    )

    assert result["rows"] == [{"total": 3}]
    assert result["row_count"] == 1
    assert result["truncated"] is False