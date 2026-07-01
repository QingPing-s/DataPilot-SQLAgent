from __future__ import annotations

from typing import Any

from src.schemas import VerificationResult
from src.sql_executor import execute_sql, is_safe_select


def normalize_sql(sql: str) -> str:
    """
    Remove extra whitespace, trailing semicolon, and lowercase SQL.
    """
    return " ".join(sql.strip().rstrip(";").lower().split())


def exact_match_sql(pred_sql: str, gold_sql: str) -> bool:
    """
    Simple exact match after normalization.
    """
    return normalize_sql(pred_sql) == normalize_sql(gold_sql)


def compare_execution_results(pred_result: dict[str, Any], gold_result: dict[str, Any]) -> bool:
    """
    Strictly compare result columns and rows.
    """
    if not pred_result.get("success") or not gold_result.get("success"):
        return False
    return (
        pred_result.get("columns") == gold_result.get("columns")
        and pred_result.get("rows") == gold_result.get("rows")
    )


def verify_sql_against_gold(db_path: str, pred_sql: str, gold_sql: str) -> dict[str, Any]:
    """
    Execute predicted and gold SQL, then compare normalized SQL and execution results.
    """
    pred_result = execute_sql(db_path, pred_sql)
    gold_result = execute_sql(db_path, gold_sql)
    sql_valid = bool(pred_result.get("success"))
    execution_correct = compare_execution_results(pred_result, gold_result)

    error = None
    if pred_result.get("error"):
        error = pred_result["error"]
    elif gold_result.get("error"):
        error = f"Gold SQL failed: {gold_result['error']}"

    return {
        "sql_valid": sql_valid,
        "execution_correct": execution_correct,
        "exact_match": exact_match_sql(pred_sql, gold_sql),
        "pred_result": pred_result,
        "gold_result": gold_result,
        "error": error,
    }


def verify_readonly_sql(sql: str) -> VerificationResult:
    stripped = sql.strip()
    if not stripped:
        return VerificationResult(is_valid=False, error="SQL is empty")
    if not is_safe_select(stripped):
        return VerificationResult(is_valid=False, error="Only safe read-only SELECT/WITH queries are allowed")
    return VerificationResult(is_valid=True)
