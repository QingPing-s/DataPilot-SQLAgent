from __future__ import annotations

from typing import Any

from src.judge import judge_output
from src.llm_client import call_llm_json
from src.prompts import build_answer_prompt
from src.report import build_markdown_report
from src.schema_reader import format_schema_for_prompt, read_database_schema
from src.sql_executor import execute_sql
from src.sql_generator import (
    fallback_generate_sql,
    generate_sql,
    generate_sql_plan,
    is_unsupported_profit_question,
)
from src.sql_repair import repair_sql
from src.sql_verifier import verify_readonly_sql
from src.trace_logger import append_trace


def schema_node(state: dict) -> dict:
    try:
        append_trace(state, "schema", "start", "Reading database schema", {"db_path": state.get("db_path")})
        schema = read_database_schema(state["db_path"])
        schema_text = format_schema_for_prompt(schema)
        state["schema"] = schema
        state["schema_text"] = schema_text
        append_trace(state, "schema", "end", "Schema loaded", {"schema": schema})
    except Exception as exc:
        state["error"] = str(exc)
        append_trace(state, "schema", "error", str(exc))
    return state


def sql_plan_node(state: dict) -> dict:
    try:
        append_trace(state, "sql_plan", "start", "Generating SQL plan")
        if is_unsupported_profit_question(state.get("question", ""), state.get("schema", {})):
            state["fallback_used"] = True
            state["sql_plan"] = _fallback_plan(state)
        else:
            state["sql_plan"] = generate_sql_plan(state.get("question", ""), state.get("schema_text", ""))
        append_trace(state, "sql_plan", "end", "SQL plan generated", {"sql_plan": state["sql_plan"]})
    except Exception as exc:
        state["fallback_used"] = True
        state["sql_plan"] = _fallback_plan(state)
        state["error"] = str(exc)
        append_trace(state, "sql_plan", "error", str(exc), {"sql_plan": state["sql_plan"]})
    return state


def sql_generate_node(state: dict) -> dict:
    try:
        append_trace(state, "sql_generate", "start", "Generating SQL")
        if state.get("fallback_used") is True:
            result = fallback_generate_sql(state.get("question", ""), state.get("schema", {}))
        else:
            result = generate_sql(
                state.get("question", ""),
                state.get("schema_text", ""),
                state.get("sql_plan", {}),
            )
    except Exception as exc:
        state["fallback_used"] = True
        state["error"] = str(exc)
        append_trace(state, "sql_generate", "error", str(exc))
        result = fallback_generate_sql(state.get("question", ""), state.get("schema", {}))

    state["generated_sql"] = result.get("sql", "")
    state["sql_explanation"] = result.get("explanation", "")
    append_trace(
        state,
        "sql_generate",
        "end",
        "SQL generated",
        {
            "generated_sql": state["generated_sql"],
            "sql_explanation": state["sql_explanation"],
            "fallback_used": state.get("fallback_used", False),
        },
    )
    return state


def sql_execute_node(state: dict) -> dict:
    try:
        append_trace(state, "sql_execute", "start", "Executing SQL", {"sql": state.get("generated_sql")})
        result = execute_sql(state["db_path"], state.get("generated_sql", ""))
        state["execution_result"] = result
        state["error"] = result.get("error")
        append_trace(state, "sql_execute", "end", "SQL execution finished", {"execution_result": result})
    except Exception as exc:
        state["error"] = str(exc)
        state["execution_result"] = {
            "success": False,
            "sql": state.get("generated_sql", ""),
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": str(exc),
        }
        append_trace(state, "sql_execute", "error", str(exc), {"execution_result": state["execution_result"]})
    return state


def verify_sql_node(state: dict) -> dict:
    try:
        sql = state.get("generated_sql") or state.get("sql") or ""
        verification = verify_readonly_sql(sql)
        state["error"] = verification.error
        append_trace(state, "verify_sql", "end", "SQL verification finished", {"is_valid": verification.is_valid})
    except Exception as exc:
        state["error"] = str(exc)
        append_trace(state, "verify_sql", "error", str(exc))
    return state


def should_repair_sql(state: dict) -> str:
    execution_result = state.get("execution_result", {})
    if execution_result.get("success") is True:
        return "answer"
    retry_count = state.get("retry_count", 0)
    if execution_result.get("success") is False and retry_count < 2 and state.get("fallback_used") is not True:
        return "repair"
    return "answer"


def sql_repair_node(state: dict) -> dict:
    try:
        append_trace(state, "sql_repair", "start", "Repairing SQL")
        result = repair_sql(
            state.get("question", ""),
            state.get("schema_text", ""),
            state.get("generated_sql", ""),
            state.get("execution_result", {}).get("error") or state.get("error") or "",
        )
        state["repaired_sql"] = result.get("repaired_sql")
        state["repair_reason"] = result.get("repair_reason")
        state["generated_sql"] = state["repaired_sql"] or state.get("generated_sql", "")
        state["retry_count"] = state.get("retry_count", 0) + 1
        append_trace(state, "sql_repair", "end", "SQL repaired", result)
    except Exception as exc:
        state["error"] = str(exc)
        state["retry_count"] = state.get("retry_count", 0) + 1
        append_trace(state, "sql_repair", "error", str(exc))
    return state


def answer_node(state: dict) -> dict:
    try:
        append_trace(state, "answer", "start", "Generating final answer")
        execution_result = state.get("execution_result", {})
        if execution_result.get("success") is not True:
            state["final_answer"] = _failed_answer(state)
        else:
            try:
                state["final_answer"] = call_llm_json(
                    build_answer_prompt(
                        state.get("question", ""),
                        state.get("generated_sql", ""),
                        execution_result,
                    )
                )
            except Exception as exc:
                state["error"] = str(exc)
                state["final_answer"] = _fallback_answer(state)
                append_trace(state, "answer", "error", str(exc), {"final_answer": state["final_answer"]})
        append_trace(state, "answer", "end", "Final answer ready", {"final_answer": state.get("final_answer")})
    except Exception as exc:
        state["error"] = str(exc)
        state["final_answer"] = _failed_answer(state)
        append_trace(state, "answer", "error", str(exc), {"final_answer": state["final_answer"]})
    return state


def judge_node(state: dict) -> dict:
    try:
        append_trace(state, "judge", "start", "Judging final output")
        if state.get("final_answer"):
            try:
                state["judge_result"] = judge_output(
                    question=state.get("question", ""),
                    schema_text=state.get("schema_text", ""),
                    sql=state.get("generated_sql", ""),
                    execution_result=state.get("execution_result", {}),
                    final_answer=state.get("final_answer", {}),
                    gold_sql=state.get("gold_sql"),
                    gold_result=state.get("gold_result"),
                )
            except Exception as exc:
                state["error"] = str(exc)
                append_trace(state, "judge", "error", str(exc))
        append_trace(state, "judge", "end", "Judge step finished", {"judge_result": state.get("judge_result", {})})
    except Exception as exc:
        state["error"] = str(exc)
        append_trace(state, "judge", "error", str(exc))
    return state


def report_node(state: dict) -> dict:
    try:
        append_trace(state, "report", "start", "Building final report")
        state["final_report"] = build_markdown_report(state)
        append_trace(state, "report", "end", "Final report built", {"final_report": state["final_report"]})
    except Exception as exc:
        state["error"] = str(exc)
        append_trace(state, "report", "error", str(exc))
    return state


def _fallback_plan(state: dict) -> dict[str, Any]:
    schema = state.get("schema", {})
    table_names = [table.get("table_name") for table in schema.get("tables", []) if table.get("table_name")]
    return {
        "question": state.get("question", ""),
        "relevant_tables": table_names[:1],
        "relevant_columns": [],
        "join_keys": [],
        "filters": [],
        "aggregations": [],
        "order_by": [],
        "limit": 10,
        "reasoning": "Fallback plan generated locally because LLM planning failed.",
    }


def _fallback_answer(state: dict) -> dict[str, Any]:
    result = state.get("execution_result", {})
    rows = result.get("rows", [])
    if not rows:
        answer = "The query ran successfully but returned no rows."
        insights = ["No rows were returned."]
    elif rows[0].get("limitation"):
        answer = rows[0]["limitation"]
        insights = ["The requested metric is not available in the current database schema."]
    else:
        answer = f"The query returned {result.get('row_count', len(rows))} row(s)."
        insights = [f"Columns: {', '.join(result.get('columns', []))}"]
        insights.append(f"First row: {rows[0]}")
    return {
        "question": state.get("question", ""),
        "sql": state.get("generated_sql", ""),
        "answer": answer,
        "key_insights": insights[:5],
    }


def _failed_answer(state: dict) -> dict[str, Any]:
    error = state.get("execution_result", {}).get("error") or state.get("error") or "Unknown SQL execution error"
    return {
        "question": state.get("question", ""),
        "sql": state.get("generated_sql", ""),
        "answer": f"SQL execution failed: {error}",
        "key_insights": [error],
    }


load_schema_node = schema_node
generate_sql_node = sql_generate_node
execute_sql_node = sql_execute_node
