from __future__ import annotations

import json
import sqlite3

from eval import run_eval as run_eval_module


def test_run_eval_writes_results_and_report(tmp_path, monkeypatch):
    db_path = tmp_path / "demo.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE singer (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO singer (id) VALUES (1)")

    cases_path = tmp_path / "eval_cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "spider_001",
                    "db_id": "demo",
                    "db_path": str(db_path),
                    "question": "How many singers do we have?",
                    "gold_sql": "SELECT COUNT(*) AS count FROM singer",
                    "difficulty": "easy",
                }
            ]
        ),
        encoding="utf-8",
    )

    def fake_run_datapilot(initial_state):
        return {
            "generated_sql": "SELECT COUNT(*) AS count FROM singer",
            "retry_count": 0,
            "fallback_used": True,
            "judge_result": {"overall_judge_score": 4.0, "has_hallucination": False},
        }

    monkeypatch.setattr(run_eval_module, "run_datapilot", fake_run_datapilot)

    result = run_eval_module.run_eval(str(cases_path), limit=50, output_dir=str(tmp_path / "eval_out"))

    assert result["metrics"]["total_cases"] == 1
    assert result["metrics"]["execution_accuracy"] == 1.0
    assert result["results"][0]["fallback_used"] is True
    assert (tmp_path / "eval_out" / "eval_results.json").exists()
    report = (tmp_path / "eval_out" / "metrics_report.md").read_text(encoding="utf-8")
    assert "## Overall Metrics" in report
    assert "## Difficulty Breakdown" in report
    assert "Fallback Used" in report


def test_run_eval_records_missing_database(tmp_path):
    cases_path = tmp_path / "eval_cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "spider_001",
                    "db_id": "missing",
                    "db_path": str(tmp_path / "missing.sqlite"),
                    "question": "How many rows?",
                    "gold_sql": "SELECT COUNT(*) FROM sample",
                    "difficulty": "easy",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = run_eval_module.run_eval(str(cases_path), output_dir=str(tmp_path / "eval_out"))

    assert result["results"][0]["sql_valid"] is False
    assert result["results"][0]["skipped"] is True
    assert result["metrics"]["evaluated_cases"] == 0
    assert result["metrics"]["skipped_cases"] == 1
    assert "Database not found" in result["results"][0]["error"]
