from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.llm_client import call_llm_json
from src.prompts import build_sql_repair_prompt
from src.schemas import SQLRepairResult


def repair_sql(question: str, schema_text: str, failed_sql: str, error: str) -> dict[str, Any]:
    """
    Call DeepSeek API to repair failed SQL and validate SQLRepairResult.
    """
    try:
        payload = call_llm_json(build_sql_repair_prompt(question, schema_text, failed_sql, error))
        result = SQLRepairResult(**payload)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result.dict()
    except ValidationError as exc:
        raise RuntimeError(f"LLM returned invalid SQLRepairResult JSON: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to repair SQL: {exc}") from exc
