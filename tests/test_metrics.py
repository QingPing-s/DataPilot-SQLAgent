from __future__ import annotations

from eval.metrics import (
    accuracy,
    compute_average_judge_score,
    compute_average_retry_count,
    compute_exact_match_rate,
    compute_execution_accuracy,
    compute_hallucination_rate,
    compute_repair_success_rate,
    compute_sql_valid_rate,
    exact_match,
    summarize_metrics,
)


def test_exact_match_normalizes_sql():
    assert exact_match("SELECT * FROM sample;", "select * from sample")


def test_accuracy_empty():
    assert accuracy([]) == 0.0


def test_metrics_empty_results_do_not_error():
    assert summarize_metrics([]) == {
        "total_cases": 0,
        "sql_valid_rate": 0.0,
        "execution_accuracy": 0.0,
        "exact_match_rate": 0.0,
        "repair_success_rate": 0.0,
        "average_retry_count": 0.0,
        "average_judge_score": 0.0,
        "hallucination_rate": 0.0,
    }


def test_metric_functions_compute_rates_and_averages():
    results = [
        {
            "sql_valid": True,
            "execution_correct": True,
            "exact_match": True,
            "repaired": False,
            "retry_count": 0,
            "judge_result": {"overall_judge_score": 4.0, "has_hallucination": False},
        },
        {
            "sql_valid": True,
            "execution_correct": False,
            "exact_match": False,
            "repaired": True,
            "retry_count": 1,
            "judge_result": {"overall_judge_score": 2.0, "has_hallucination": True},
        },
        {
            "sql_valid": False,
            "execution_correct": False,
            "exact_match": False,
            "repaired": True,
            "retry_count": 2,
        },
    ]

    assert compute_sql_valid_rate(results) == 2 / 3
    assert compute_execution_accuracy(results) == 1 / 3
    assert compute_exact_match_rate(results) == 1 / 3
    assert compute_repair_success_rate(results) == 1 / 2
    assert compute_average_retry_count(results) == 1.0
    assert compute_average_judge_score(results) == 3.0
    assert compute_hallucination_rate(results) == 0.5


def test_summarize_metrics():
    results = [
        {
            "sql_valid": True,
            "execution_correct": True,
            "exact_match": False,
            "repaired": False,
            "retry_count": 0,
        }
    ]

    summary = summarize_metrics(results)

    assert summary["total_cases"] == 1
    assert summary["sql_valid_rate"] == 1.0
