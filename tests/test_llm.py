import json
from unittest.mock import patch

import httpx
import pytest

from app.llm import LLMError, generate_sql


@pytest.fixture
def ollama_post(monkeypatch):
    monkeypatch.setenv(
        "OLLAMA_BASE_URL",
        "http://127.0.0.1:11434",
    )
    monkeypatch.setenv(
        "OLLAMA_MODEL",
        "qwen2.5-coder:1.5b",
    )

    with patch("app.llm.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        yield client.post


def make_response(content):
    return httpx.Response(
        200,
        request=httpx.Request(
            "POST",
            "http://127.0.0.1:11434/api/chat",
        ),
        json={
            "done": True,
            "message": {"content": content},
        },
    )


def test_extracts_sql_from_model_response(ollama_post):
    expected_sql = "SELECT COUNT(*) AS total FROM orders"

    ollama_post.return_value = make_response(
        json.dumps({"sql": expected_sql, "error": None})
    )

    result = generate_sql("Cuantos pedidos hay?")

    assert result == expected_sql


def test_rejects_malformed_model_response(ollama_post):
    ollama_post.return_value = make_response(
        "Esta respuesta no es JSON"
    )

    with pytest.raises(LLMError, match="formato inválido"):
        generate_sql("Cuantos pedidos hay?")


def test_handles_model_timeout(ollama_post):
    ollama_post.side_effect = httpx.ReadTimeout(
        "Tiempo de espera agotado"
    )

    with pytest.raises(LLMError, match="tiempo de espera"):
        generate_sql("Cuantos pedidos hay?")