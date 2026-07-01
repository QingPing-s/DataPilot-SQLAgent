from __future__ import annotations

try:
    from langgraph.graph import END, StateGraph
except ModuleNotFoundError:  # pragma: no cover - used when optional dependency is missing
    END = None
    StateGraph = None

from src.nodes import (
    answer_node,
    judge_node,
    report_node,
    schema_node,
    should_repair_sql,
    sql_execute_node,
    sql_generate_node,
    sql_plan_node,
    sql_repair_node,
)
from src.state import DataPilotState


def build_graph():
    if StateGraph is None:
        return _FallbackGraph()

    graph = StateGraph(DataPilotState)

    graph.add_node("schema", schema_node)
    graph.add_node("sql_plan", sql_plan_node)
    graph.add_node("sql_generate", sql_generate_node)
    graph.add_node("sql_execute", sql_execute_node)
    graph.add_node("sql_repair", sql_repair_node)
    graph.add_node("answer", answer_node)
    graph.add_node("judge", judge_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("schema")
    graph.add_edge("schema", "sql_plan")
    graph.add_edge("sql_plan", "sql_generate")
    graph.add_edge("sql_generate", "sql_execute")
    graph.add_conditional_edges(
        "sql_execute",
        should_repair_sql,
        {
            "repair": "sql_repair",
            "answer": "answer",
        },
    )
    graph.add_edge("sql_repair", "sql_execute")
    graph.add_edge("answer", "judge")
    graph.add_edge("judge", "report")
    graph.add_edge("report", END)

    return graph.compile()


def run_datapilot(initial_state: dict) -> dict:
    state = dict(initial_state)
    state.setdefault("retry_count", 0)
    state.setdefault("trace", [])
    state.setdefault("fallback_used", False)

    missing = [key for key in ("question", "db_path", "retry_count", "trace") if key not in state]
    if missing:
        raise ValueError(f"Missing required initial_state fields: {', '.join(missing)}")

    app = build_graph()
    return app.invoke(state)


class _FallbackGraph:
    def invoke(self, state: dict) -> dict:
        state = schema_node(state)
        state = sql_plan_node(state)
        state = sql_generate_node(state)
        state = sql_execute_node(state)
        while should_repair_sql(state) == "repair":
            state = sql_repair_node(state)
            state = sql_execute_node(state)
        state = answer_node(state)
        state = judge_node(state)
        state = report_node(state)
        return state
