from __future__ import annotations

from src.report import build_markdown_report, save_report


def test_build_markdown_report_includes_core_sections_and_limits_rows():
    state = {
        "question": "List customers",
        "db_path": "data/northwind/northwind.db",
        "db_id": "northwind",
        "sql_plan": {"relevant_tables": ["customers"], "limit": 10},
        "generated_sql": "SELECT customer_id FROM customers",
        "sql_explanation": "Lists customer ids.",
        "execution_result": {
            "success": True,
            "row_count": 12,
            "columns": ["customer_id"],
            "rows": [{"customer_id": f"C{i}"} for i in range(12)],
        },
        "retry_count": 1,
        "repaired_sql": "SELECT customer_id FROM customers",
        "repair_reason": "Fixed column name.",
        "final_answer": {
            "answer": "The query returned customers.",
            "key_insights": ["Customer ids are shown."],
        },
        "judge_result": {
            "question_sql_alignment": 5,
            "answer_faithfulness": 5,
            "explanation_quality": 4,
            "result_usefulness": 4,
            "has_hallucination": False,
            "overall_judge_score": 4.5,
            "judge_reason": "Good.",
        },
        "trace": [{"node": "schema", "status": "end"}, {"node": "sql_execute", "status": "end"}],
    }

    report = build_markdown_report(state)

    assert "# DataPilot SQL Agent Report" in report
    assert "## User Question" in report
    assert "## SQL Execution Result" in report
    assert "| customer_id |" in report
    assert "C9" in report
    assert "C10" not in report
    assert "- schema: `end`" in report


def test_build_markdown_report_tolerates_missing_fields():
    report = build_markdown_report({})

    assert "# DataPilot SQL Agent Report" in report


def test_save_report(tmp_path):
    output_path = tmp_path / "report.md"

    save_report("# Report\n", str(output_path))

    assert output_path.read_text(encoding="utf-8") == "# Report\n"
