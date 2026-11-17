import pytest

from app.sql_validation import InvalidQueryError, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM orders",
        """
        SELECT total_sales_eur
        FROM monthly_sales
        WHERE country = 'España' AND month = '2025-03'
        """,
        """
        SELECT customer, total_sales_eur
        FROM top_customers
        ORDER BY total_sales_cents DESC, customer ASC
        LIMIT 10
        """,
        """
        SELECT country, SUM(amount_cents) AS total
        FROM orders
        WHERE status = 'completed'
        GROUP BY country
        """,
        # Una palabra SQL dentro de un dato no debe provocar un rechazo.
        "SELECT * FROM orders WHERE customer = 'DROP TABLE orders'",
    ],
)
def test_accepts_allowed_queries(sql):
    validated = validate_sql(sql)

    assert isinstance(validated, str)
    assert validated.startswith("SELECT")


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "Esto no es una consulta SQL",
        "DELETE FROM orders",
        "UPDATE orders SET amount_cents = 0",
        "DROP TABLE orders",
        "SELECT * FROM orders; DELETE FROM orders",
        "SELECT * FROM users",
        "SELECT * FROM sqlite_master",
        "SELECT * FROM other_database.orders",
        "PRAGMA table_info(orders)",
        "ATTACH DATABASE 'other.db' AS other",
        "SELECT load_extension('example') FROM orders",
        "SELECT readfile('secret.txt') FROM orders",
        "SELECT * FROM orders WHERE order_id IN (SELECT id FROM users)",
        "WITH x AS (SELECT * FROM orders) SELECT * FROM x",
        "SELECT * FROM orders JOIN top_customers USING (customer)",
        "SELECT * FROM orders UNION SELECT * FROM orders",
        "SELECT 1",
    ],
)
def test_rejects_disallowed_queries(sql):
    with pytest.raises(InvalidQueryError):
        validate_sql(sql)