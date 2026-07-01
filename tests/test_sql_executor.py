from __future__ import annotations

import sqlite3

from src.sql_executor import execute_sql, is_safe_select


def test_execute_sql_returns_rows(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO sample (name) VALUES ('alpha')")

    result = execute_sql(db_path, "SELECT name FROM sample")

    assert result["success"] is True
    assert result["error"] is None
    assert result["columns"] == ["name"]
    assert result["rows"] == [{"name": "alpha"}]
    assert result["row_count"] == 1


def test_execute_sql_limits_rows(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
        conn.executemany("INSERT INTO sample (name) VALUES (?)", [("a",), ("b",), ("c",)])

    result = execute_sql(db_path, "SELECT name FROM sample ORDER BY id", max_rows=2)

    assert result["success"] is True
    assert result["row_count"] == 2
    assert result["rows"] == [{"name": "a"}, {"name": "b"}]


def test_non_select_is_rejected(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    db_path.write_bytes(b"")

    result = execute_sql(db_path, "UPDATE sample SET name = 'beta'")

    assert result["success"] is False
    assert "Unsafe SQL rejected" in result["error"]


def test_drop_is_rejected(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    db_path.write_bytes(b"")

    assert is_safe_select("DROP TABLE sample") is False
    result = execute_sql(db_path, "DROP TABLE sample")

    assert result["success"] is False
    assert "Unsafe SQL rejected" in result["error"]


def test_multiple_statements_are_rejected(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    db_path.write_bytes(b"")

    assert is_safe_select("SELECT 1; SELECT 2") is False


def test_bad_sql_returns_error(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")

    result = execute_sql(db_path, "SELECT missing_column FROM sample")

    assert result["success"] is False
    assert "missing_column" in result["error"]
