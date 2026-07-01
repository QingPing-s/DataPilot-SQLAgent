from __future__ import annotations

import json

from src.trace_logger import TraceLogger, append_trace


def test_trace_logger_sanitizes_payload_and_saves(tmp_path):
    logger = TraceLogger()
    logger.log_node_start(
        "load_schema",
        {
            "OPENAI_API_KEY": "secret",
            "schema": {
                "db_path": "demo.sqlite",
                "tables": [
                    {"table_name": "customers", "columns": [{"name": "customer_id"}]},
                    {"table_name": "orders", "columns": [{"name": "order_id"}]},
                ],
            },
            "execution_result": {
                "success": True,
                "columns": ["id"],
                "rows": [{"id": index} for index in range(8)],
            },
        },
    )
    output_path = tmp_path / "trace.json"
    logger.save(str(output_path))

    data = json.loads(output_path.read_text(encoding="utf-8"))
    payload = data[0]["payload"]

    assert payload["OPENAI_API_KEY"] == "[REDACTED]"
    assert payload["schema"] == {
        "db_path": "demo.sqlite",
        "table_count": 2,
        "tables": ["customers", "orders"],
    }
    assert len(payload["execution_result"]["rows"]) == 5
    assert payload["execution_result"]["rows_truncated"] is True
    assert payload["execution_result"]["original_row_count"] == 8


def test_append_trace_adds_simplified_trace():
    state = {}

    append_trace(state, "generate_sql", "ok", "Generated fallback SQL", {"api_key": "secret"})

    assert state["trace"][0]["node"] == "generate_sql"
    assert state["trace"][0]["status"] == "ok"
    assert state["trace"][0]["payload"]["api_key"] == "[REDACTED]"
