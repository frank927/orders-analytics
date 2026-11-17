class LLMError(RuntimeError):
    """El proveedor LLM no pudo generar una respuesta."""


def generate_sql(question: str) -> str:
    raise LLMError(
        "El proveedor LLM todavía no está configurado"
    )