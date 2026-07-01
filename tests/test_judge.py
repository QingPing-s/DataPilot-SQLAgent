from __future__ import annotations

from src import judge


def test_judge_output_validates_llm_json(monkeypatch):
    def fake_call_llm_json(messages, temperature=0.2):
        return {
            "question_sql_alignment": 5,
            "answer_faithfulness": 5,
            "explanation_quality": 4,
            "result_usefulness": 4,
            "error_analysis_quality": 3,
            "has_hallucination": False,
            "issues": [],
            "overall_judge_score": 4.5,
            "judge_reason": "Faithful answer.",
        }

    monkeypatch.setattr(judge, "call_llm_json", fake_call_llm_json)

    result = judge.judge_output(
        question="How many customers?",
        schema_text="Table: customers",
        sql="SELECT COUNT(*) AS count FROM customers",
        execution_result={"success": True, "rows": [{"count": 8}]},
        final_answer={"answer": "There are 8 customers."},
    )

    assert result["overall_judge_score"] == 4.5
