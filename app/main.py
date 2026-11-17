from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.llm import LLMError, generate_sql
from app.load_data import DB_PATH
from app.query_executor import QueryExecutionError, execute_query
from app.sql_validation import InvalidQueryError


app = FastAPI(title="Orders Analytics API")

SQLGenerator = Callable[[str], str]


class QuestionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=1_000)


def get_sql_generator() -> SQLGenerator:
    return generate_sql


def get_database_path() -> Path:
    return DB_PATH


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(
    request: QuestionRequest,
    sql_generator: Annotated[
        SQLGenerator, Depends(get_sql_generator)
    ],
    database_path: Annotated[
        Path, Depends(get_database_path)
    ],
):
    try:
        sql = sql_generator(request.question)
    except LLMError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    try:
        result = execute_query(sql, db_path=database_path)
    except InvalidQueryError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Consulta generada no permitida: {exc}",
        ) from exc
    except QueryExecutionError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "question": request.question,
        **result,
    }