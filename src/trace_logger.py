from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SENSITIVE_KEYWORDS = ("api_key", "apikey", "authorization", "token", "secret", "password")


class TraceLogger:
    def __init__(self):
        self.events = []

    def log_node_start(self, node_name: str, payload: dict | None = None):
        self._log(node_name=node_name, event_type="start", payload=payload)

    def log_node_end(self, node_name: str, payload: dict | None = None):
        self._log(node_name=node_name, event_type="end", payload=payload)

    def log_error(self, node_name: str, error: str, payload: dict | None = None):
        cleaned_payload = dict(payload or {})
        cleaned_payload["error"] = error
        self._log(node_name=node_name, event_type="error", payload=cleaned_payload)

    def save(self, path: str):
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.events, indent=2, ensure_ascii=False), encoding="utf-8")

    def _log(self, node_name: str, event_type: str, payload: dict | None = None):
        self.events.append(
            {
                "timestamp": _timestamp(),
                "node": node_name,
                "event_type": event_type,
                "payload": _sanitize_payload(payload or {}),
            }
        )


def append_trace(
    state: dict,
    node: str,
    status: str,
    message: str,
    payload: dict | None = None,
) -> dict:
    traces = state.setdefault("trace", [])
    traces.append(
        {
            "timestamp": _timestamp(),
            "node": node,
            "status": status,
            "message": message,
            "payload": _sanitize_payload(payload or {}),
        }
    )
    return state


def write_trace(event: dict[str, Any], trace_dir: str | Path = "traces") -> Path:
    Path(trace_dir).mkdir(parents=True, exist_ok=True)
    path = Path(trace_dir) / "trace.jsonl"
    payload = {"timestamp": _timestamp(), **_sanitize_payload(event)}
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        if _looks_like_database_schema(value):
            return _summarize_schema(value)

        sanitized = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(keyword in key_text for keyword in SENSITIVE_KEYWORDS):
                sanitized[key] = "[REDACTED]"
            elif key in {"schema", "schema_text"} and isinstance(item, str):
                sanitized[key] = _summarize_schema_text(item)
            elif key in {"result", "execution_result", "pred_result", "gold_result"} and isinstance(item, dict):
                sanitized[key] = _sanitize_sql_result(item)
            else:
                sanitized[key] = _sanitize_payload(item)
        return sanitized

    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]

    return value


def _sanitize_sql_result(result: dict[str, Any]) -> dict[str, Any]:
    sanitized = _sanitize_payload({key: value for key, value in result.items() if key != "rows"})
    rows = result.get("rows", [])
    if isinstance(rows, list):
        sanitized["rows"] = [_sanitize_payload(row) for row in rows[:5]]
        sanitized["rows_truncated"] = len(rows) > 5
        sanitized["original_row_count"] = len(rows)
    return sanitized


def _looks_like_database_schema(value: dict[str, Any]) -> bool:
    return "tables" in value and isinstance(value.get("tables"), list)


def _summarize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    table_names = []
    for table in schema.get("tables", []):
        if isinstance(table, dict):
            table_names.append(table.get("table_name"))
    table_names = [name for name in table_names if name]
    return {
        "db_path": schema.get("db_path"),
        "table_count": len(table_names),
        "tables": table_names,
    }


def _summarize_schema_text(schema_text: str) -> dict[str, Any]:
    table_names = []
    for line in schema_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Table:"):
            table_names.append(stripped.replace("Table:", "", 1).strip())
    return {
        "table_count": len(table_names),
        "tables": table_names,
    }


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
