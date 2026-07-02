from __future__ import annotations

import itertools
import re
from collections import Counter
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


def compare_execution_values(pred_result: dict[str, Any], gold_result: dict[str, Any]) -> bool:
    """
    Compare result values while ignoring aliases and equivalent column ordering.
    """
    if not pred_result.get("success") or not gold_result.get("success"):
        return False

    pred_columns = pred_result.get("columns", [])
    gold_columns = gold_result.get("columns", [])
    if len(pred_columns) != len(gold_columns):
        return False

    pred_rows = pred_result.get("rows", [])
    gold_rows = gold_result.get("rows", [])
    gold_values = [tuple(row.get(column) for column in gold_columns) for row in gold_rows]
    order_matters = bool(re.search(r"\border\s+by\b", gold_result.get("sql", ""), re.IGNORECASE))

    permutations = (
        itertools.permutations(range(len(pred_columns)))
        if len(pred_columns) <= 8
        else [tuple(range(len(pred_columns)))]
    )
    for permutation in permutations:
        pred_values = [
            tuple(row.get(pred_columns[index]) for index in permutation)
            for row in pred_rows
        ]
        if order_matters:
            if pred_values == gold_values:
                return True
        elif Counter(pred_values) == Counter(gold_values):
            return True
    return False


def verify_sql_against_gold(db_path: str, pred_sql: str, gold_sql: str) -> dict[str, Any]:
    """
    Execute predicted and gold SQL, then compare normalized SQL and execution results.
    """
    pred_result = execute_sql(db_path, pred_sql)
    gold_result = execute_sql(db_path, gold_sql)
    sql_valid = bool(pred_result.get("success"))
    strict_execution_match = compare_execution_results(pred_result, gold_result)
    execution_correct = compare_execution_values(pred_result, gold_result)

    error = None
    if pred_result.get("error"):
        error = pred_result["error"]
    elif gold_result.get("error"):
        error = f"Gold SQL failed: {gold_result['error']}"

    return {
        "sql_valid": sql_valid,
        "execution_correct": execution_correct,
        "strict_execution_match": strict_execution_match,
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
