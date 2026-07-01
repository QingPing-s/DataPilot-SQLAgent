from __future__ import annotations

from typing import Any, Optional

try:
    from typing import NotRequired, TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import NotRequired, TypedDict


class DataPilotState(TypedDict, total=False):
    question: str
    db_path: str
    db_id: NotRequired[Optional[str]]

    schema: dict[str, Any]
    schema_text: str

    sql_plan: dict[str, Any]
    generated_sql: str
    sql_explanation: str

    execution_result: dict[str, Any]

    repaired_sql: NotRequired[Optional[str]]
    repair_reason: NotRequired[Optional[str]]
    retry_count: int
    fallback_used: bool

    final_answer: dict[str, Any]
    judge_result: dict[str, Any]

    gold_sql: NotRequired[Optional[str]]
    gold_result: NotRequired[Optional[dict[str, Any]]]
    objective_metrics: dict[str, Any]

    trace: list[dict[str, Any]]
    error: NotRequired[Optional[str]]
    final_report: str


AgentState = DataPilotState
