from __future__ import annotations

import sqlite3

from src.sql_verifier import (
    compare_execution_results,
    compare_execution_values,
    exact_match_sql,
    normalize_sql,
    verify_readonly_sql,
    verify_sql_against_gold,
)


def test_verify_readonly_sql_allows_select():
    result = verify_readonly_sql("SELECT * FROM sample")

    assert result.is_valid


def test_verify_readonly_sql_rejects_delete():
    result = verify_readonly_sql("DELETE FROM sample")

    assert not result.is_valid


def test_normalize_and_exact_match_sql():
    assert normalize_sql(" SELECT  *  FROM sample; ") == "select * from sample"
    assert exact_match_sql("SELECT * FROM sample;", "select * from sample")


def test_compare_execution_results_strict_match():
    pred = {
        "success": True,
        "columns": ["name"],
        "rows": [{"name": "alpha"}],
    }
    gold = {
        "success": True,
        "columns": ["name"],
        "rows": [{"name": "alpha"}],
    }

    assert compare_execution_results(pred, gold)


def test_compare_execution_values_ignores_aliases_and_column_order():
    pred = {
        "success": True,
        "sql": "SELECT petType, MAX(weight) AS max_weight FROM pets GROUP BY petType",
        "columns": ["petType", "max_weight"],
        "rows": [{"petType": "cat", "max_weight": 10}],
    }
    gold = {
        "success": True,
        "sql": "SELECT MAX(weight), petType FROM pets GROUP BY petType",
        "columns": ["MAX(weight)", "petType"],
        "rows": [{"MAX(weight)": 10, "petType": "cat"}],
    }

    assert compare_execution_results(pred, gold) is False
    assert compare_execution_values(pred, gold) is True


def test_verify_sql_against_gold_execution_match(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO sample (name) VALUES ('alpha')")

    result = verify_sql_against_gold(
        str(db_path),
        "SELECT name FROM sample",
        "SELECT name FROM sample;",
    )

    assert result["sql_valid"] is True
    assert result["execution_correct"] is True
    assert result["exact_match"] is True
    assert result["error"] is None
