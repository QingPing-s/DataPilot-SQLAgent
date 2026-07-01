from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient

from src import api


client = TestClient(api.app)


def test_health_does_not_expose_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["api_key_configured"] is True
    assert "api_key" not in response.json()
    assert "test-secret" not in response.text


def test_analyze_returns_agent_result(tmp_path, monkeypatch):
    db_path = tmp_path / "demo.sqlite"
    db_path.write_bytes(b"")
    expected_state = {
        "generated_sql": "SELECT 1 AS value",
        "sql_explanation": "Test query",
        "execution_result": {
            "success": True,
            "sql": "SELECT 1 AS value",
            "columns": ["value"],
            "rows": [{"value": 1}],
            "row_count": 1,
            "error": None,
        },
        "final_answer": {"answer": "The value is 1.", "key_insights": ["value=1"]},
        "judge_result": {},
        "trace": [],
        "fallback_used": False,
        "retry_count": 0,
        "error": None,
    }
    monkeypatch.setattr(api, "run_datapilot", lambda state: expected_state)

    response = client.post(
        "/api/analyze",
        json={"question": "Show one", "db_path": str(db_path), "db_id": "demo"},
    )

    assert response.status_code == 200
    assert response.json()["generated_sql"] == "SELECT 1 AS value"
    assert response.json()["execution_result"]["rows"] == [{"value": 1}]


def test_analyze_rejects_missing_database(tmp_path):
    response = client.post(
        "/api/analyze",
        json={"question": "Show data", "db_path": str(tmp_path / "missing.sqlite")},
    )

    assert response.status_code == 404
    assert "Database not found" in response.json()["detail"]


def test_database_info_returns_schema_details(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO customers VALUES ('C1', 'Demo')")

    response = client.get("/api/database-info", params={"db_path": str(db_path)})

    assert response.status_code == 200
    assert response.json()["table_count"] == 1
    assert response.json()["tables"][0]["table_name"] == "customers"
    assert response.json()["tables"][0]["row_count"] == 1
    assert response.json()["tables"][0]["columns"][0]["name"] == "customer_id"


def test_evaluation_marks_all_failed_cases_unavailable(tmp_path, monkeypatch):
    results_path = tmp_path / "eval_results.json"
    results_path.write_text(
        json.dumps(
            {
                "metrics": {"sql_valid_rate": 0.0},
                "results": [{"case_id": "case_1", "question": "Demo?", "error": "Database missing"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "EVAL_RESULTS_PATH", results_path)

    response = client.get("/api/evaluation")

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["metrics"] is None
    assert response.json()["failed_cases"][0]["case_id"] == "case_1"
