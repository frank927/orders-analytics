import sqlite3
from contextlib import closing
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.llm import LLMError
from app.main import (
    app,
    get_database_path,
    get_sql_generator,
)


@pytest.fixture
def api_context(tmp_path):
    database_path = tmp_path / "api_test.db"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            "CREATE TABLE orders (order_id INTEGER PRIMARY KEY)"
        )
        connection.executemany(
            "INSERT INTO orders (order_id) VALUES (?)",
            [(1,), (2,), (3,)],
        )
        connection.commit()

    fake_llm = Mock(
        return_value="SELECT COUNT(*) AS total FROM orders"
    )

    app.dependency_overrides[get_sql_generator] = lambda: fake_llm
    app.dependency_overrides[get_database_path] = lambda: database_path

    try:
        with TestClient(app) as client:
            yield client, fake_llm
    finally:
        app.dependency_overrides.clear()


def test_ask_returns_query_result(api_context):
    client, fake_llm = api_context

    response = client.post(
        "/ask",
        json={"question": "Cuantos pedidos hay?"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["question"] == "Cuantos pedidos hay?"
    assert body["rows"] == [{"total": 3}]
    assert body["row_count"] == 1
    assert body["truncated"] is False

    fake_llm.assert_called_once_with("Cuantos pedidos hay?")


def test_ask_rejects_unsafe_sql_and_preserves_data(api_context):
    client, fake_llm = api_context
    fake_llm.return_value = "DELETE FROM orders"

    response = client.post(
        "/ask",
        json={"question": "Borra los pedidos"},
    )

    assert response.status_code == 422
    assert "no permitida" in response.json()["detail"]

    # Una segunda petición comprueba que los pedidos siguen ahí.
    fake_llm.return_value = "SELECT COUNT(*) AS total FROM orders"

    response = client.post(
        "/ask",
        json={"question": "Cuantos pedidos quedan?"},
    )

    assert response.status_code == 200
    assert response.json()["rows"] == [{"total": 3}]


def test_ask_handles_llm_failure(api_context):
    client, fake_llm = api_context
    fake_llm.side_effect = LLMError("El servicio LLM no responde")

    response = client.post(
        "/ask",
        json={"question": "Cuantos pedidos hay?"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "El servicio LLM no responde"


def test_ask_handles_invalid_column(api_context):
    client, fake_llm = api_context
    fake_llm.return_value = "SELECT nonexistent_column FROM orders"

    response = client.post(
        "/ask",
        json={"question": "Consulta una columna inexistente"},
    )

    assert response.status_code == 422
    assert "No se pudo ejecutar" in response.json()["detail"]


@pytest.mark.parametrize("question", ["", "   ", "x" * 1001])
def test_ask_rejects_invalid_question(api_context, question):
    client, fake_llm = api_context

    response = client.post(
        "/ask",
        json={"question": question},
    )

    assert response.status_code == 422
    fake_llm.assert_not_called()


def test_ask_requires_question(api_context):
    client, fake_llm = api_context

    response = client.post("/ask", json={})

    assert response.status_code == 422
    fake_llm.assert_not_called()