from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.llm_client import call_llm_json
from src.prompts import build_judge_prompt
from src.schemas import JudgeResult


def judge_output(
    question: str,
    schema_text: str,
    sql: str,
    execution_result: dict,
    final_answer: dict,
    gold_sql: str | None = None,
    gold_result: dict | None = None,
) -> dict[str, Any]:
    """
    Use LLM-as-a-Judge to evaluate SQL Agent output quality.
    """
    try:
        payload = call_llm_json(
            build_judge_prompt(
                question=question,
                schema_text=schema_text,
                sql=sql,
                execution_result=execution_result,
                final_answer=final_answer,
                gold_sql=gold_sql,
                gold_result=gold_result,
            )
        )
        result = JudgeResult(**payload)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result.dict()
    except ValidationError as exc:
        raise RuntimeError(f"LLM returned invalid JudgeResult JSON: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to judge output: {exc}") from exc


def judge_answer(question: str, sql: str, result: dict[str, Any]) -> JudgeResult:
    if result.get("error"):
        return JudgeResult(
            question_sql_alignment=1,
            answer_faithfulness=1,
            explanation_quality=1,
            result_usefulness=1,
            error_analysis_quality=3,
            has_hallucination=False,
            issues=[result["error"]],
            overall_judge_score=1.0,
            judge_reason=result["error"],
        )
    if not question.strip() or not sql.strip():
        return JudgeResult(
            question_sql_alignment=1,
            answer_faithfulness=1,
            explanation_quality=1,
            result_usefulness=1,
            error_analysis_quality=2,
            has_hallucination=False,
            issues=["Missing question or SQL"],
            overall_judge_score=1.0,
            judge_reason="Missing question or SQL",
        )
    return JudgeResult(
        question_sql_alignment=5,
        answer_faithfulness=5,
        explanation_quality=3,
        result_usefulness=4,
        error_analysis_quality=3,
        has_hallucination=False,
        issues=[],
        overall_judge_score=4.0,
        judge_reason="Offline placeholder judge",
    )
