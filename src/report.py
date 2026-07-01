from __future__ import annotations

from pathlib import Path
from typing import Any


def build_markdown_report(state: dict) -> str:
    """
    Build a readable Markdown report from DataPilotState.
    """
    lines: list[str] = ["# DataPilot SQL Agent Report", ""]

    _add_section(lines, "User Question", state.get("question"))

    database_lines = []
    if state.get("db_path"):
        database_lines.append(f"- Database Path: `{state.get('db_path')}`")
    if state.get("db_id"):
        database_lines.append(f"- DB ID: `{state.get('db_id')}`")
    _add_section(lines, "Database Path / DB ID", "\n".join(database_lines) if database_lines else None)

    sql_plan = state.get("sql_plan")
    if sql_plan:
        _add_section(lines, "SQL Plan", _format_dict(sql_plan))

    generated_sql = state.get("generated_sql")
    if generated_sql:
        lines.extend(["## Generated SQL", "", "```sql", generated_sql, "```", ""])
        if state.get("sql_explanation"):
            lines.extend(["Explanation:", "", str(state.get("sql_explanation")), ""])
        if "fallback_used" in state:
            lines.extend([f"fallback_used: `{state.get('fallback_used')}`", ""])

    execution_result = state.get("execution_result")
    if isinstance(execution_result, dict):
        lines.extend(["## SQL Execution Result", ""])
        lines.append(f"- success: `{execution_result.get('success')}`")
        lines.append(f"- row_count: `{execution_result.get('row_count')}`")
        if execution_result.get("columns"):
            lines.append(f"- columns: `{', '.join(map(str, execution_result.get('columns', [])))}`")
        if execution_result.get("error"):
            lines.append(f"- error: `{execution_result.get('error')}`")
        lines.append("")

        table = _markdown_table(execution_result.get("rows", [])[:10], execution_result.get("columns", []))
        if table:
            lines.extend(["Result preview:", "", table, ""])

    repair_lines = []
    if "retry_count" in state:
        repair_lines.append(f"- retry_count: `{state.get('retry_count')}`")
    if state.get("repaired_sql"):
        repair_lines.extend(["- repaired_sql:", "", "```sql", str(state.get("repaired_sql")), "```"])
    if state.get("repair_reason"):
        repair_lines.append(f"- repair_reason: {state.get('repair_reason')}")
    _add_section(lines, "SQL Repair", "\n".join(repair_lines) if repair_lines else None)

    final_answer = state.get("final_answer")
    if isinstance(final_answer, dict):
        answer_lines = []
        if final_answer.get("answer"):
            answer_lines.append(str(final_answer.get("answer")))
        insights = final_answer.get("key_insights") or []
        if insights:
            answer_lines.extend(["", "Key insights:"])
            answer_lines.extend([f"- {insight}" for insight in insights])
        _add_section(lines, "Final Answer", "\n".join(answer_lines) if answer_lines else None)

    judge_result = state.get("judge_result")
    if isinstance(judge_result, dict):
        judge_fields = [
            "question_sql_alignment",
            "answer_faithfulness",
            "explanation_quality",
            "result_usefulness",
            "has_hallucination",
            "overall_judge_score",
            "judge_reason",
        ]
        judge_lines = [f"- {field}: `{judge_result.get(field)}`" for field in judge_fields if field in judge_result]
        _add_section(lines, "LLM-as-a-Judge", "\n".join(judge_lines) if judge_lines else None)

    trace = state.get("trace")
    if isinstance(trace, list) and trace:
        trace_lines = []
        for event in trace:
            if not isinstance(event, dict):
                continue
            node = event.get("node", "unknown")
            status = event.get("status") or event.get("event_type") or "unknown"
            trace_lines.append(f"- {node}: `{status}`")
        _add_section(lines, "Trace Summary", "\n".join(trace_lines) if trace_lines else None)

    return "\n".join(lines).rstrip() + "\n"


def save_report(report: str, path: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def write_markdown_report(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Evaluation Report", "", f"Total cases: {len(rows)}", ""]
    for row in rows:
        lines.append(f"- {row}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _add_section(lines: list[str], title: str, content: Any) -> None:
    if content is None or content == "":
        return
    lines.extend([f"## {title}", "", str(content), ""])


def _format_dict(value: dict[str, Any]) -> str:
    lines = []
    for key, item in value.items():
        if isinstance(item, list):
            rendered = ", ".join(map(str, item)) if item else "none"
            lines.append(f"- {key}: {rendered}")
        else:
            lines.append(f"- {key}: {item}")
    return "\n".join(lines)


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return ""
    if not columns:
        columns = list(rows[0].keys())
    header = "| " + " | ".join(_escape_cell(column) for column in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(_escape_cell(row.get(column, "")) for column in columns) + " |")
    return "\n".join([header, separator, *body])


def _escape_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
