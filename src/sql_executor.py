from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)


def is_safe_select(sql: str) -> bool:
    """
    Return True only for safe read-only SELECT or WITH queries.
    """
    stripped = sql.strip()
    if not stripped:
        return False

    if not stripped.lower().startswith(("select", "with")):
        return False

    if FORBIDDEN_SQL_PATTERN.search(stripped):
        return False

    if ";" in stripped:
        if not stripped.endswith(";"):
            return False
        without_final_semicolon = stripped[:-1]
        if ";" in without_final_semicolon:
            return False

    return True


def execute_sql(db_path: str | Path, sql: str, max_rows: int = 100) -> dict[str, Any]:
    """
    Execute a safe read-only SELECT query and return SQLExecutionResult-shaped data.
    """
    if max_rows < 0:
        return _error_result(sql, "max_rows must be non-negative")

    if not is_safe_select(sql):
        return _error_result(sql, "Unsafe SQL rejected. Only read-only SELECT/WITH queries are allowed.")

    path = Path(db_path)
    if not path.exists():
        return _error_result(sql, f"Database not found: {path}")

    query = sql.strip().rstrip(";")
    limited_query = f"SELECT * FROM ({query}) AS _datapilot_query LIMIT ?"

    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(limited_query, (max_rows,))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description or []]
            data = [dict(row) for row in rows]
        return {
            "success": True,
            "sql": sql,
            "columns": columns,
            "rows": data,
            "row_count": len(data),
            "error": None,
        }
    except sqlite3.Error as exc:
        return _error_result(sql, str(exc))


def _error_result(sql: str, error: str) -> dict[str, Any]:
    return {
        "success": False,
        "sql": sql,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "error": error,
    }
